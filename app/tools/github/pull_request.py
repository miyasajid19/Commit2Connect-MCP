import os
import requests
from dotenv import load_dotenv
load_dotenv()
from fastmcp.tools import tool
from fastmcp.dependencies import Depends
from fastmcp.server.dependencies import get_context

def GitHubTokens()->dict:
    return {
        "access_token": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
        "owner": os.getenv("GITHUB_OWNER"),
        "api_url": "https://api.github.com",
        "headers": {
                "Authorization": f"Bearer {os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN')}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2026-03-10",
            }
    }
    
@tool
async def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str,
    body: str = "",
    draft: bool = False,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Create a pull request in a GitHub repository.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        title: Pull request title.
        head: The name of the branch containing the changes you want to merge.
        base: The name of the branch you want the changes pulled into.
        body: Optional pull request description.
        draft: Whether to create the pull request as a draft.
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the created pull request information, or an
        error payload when validation fails, the access token is missing, or
        the request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if not title.strip():
        await ctx.error("Pull request title cannot be empty.")
        return {"success": False, "error": "Pull request title cannot be empty."}

    if not head.strip() or not base.strip():
        await ctx.error("Both head and base branches are required.")
        return {"success": False, "error": "Both head and base branches are required."}

    headers = tokens["headers"]
    api_url = tokens["api_url"]

    payload = {
        "title": title,
        "head": head,
        "base": base,
        "body": body,
        "draft": draft,
    }

    try:
        response = requests.post(
            f"{api_url}/repos/{owner}/{repo}/pulls",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        body = ""
        if e.response is not None:
            try:
                body = e.response.text
            except Exception:
                body = "<unreadable response body>"
        await ctx.error(
            f"Failed to create pull request in {owner}/{repo} "
            f"({head} -> {base}): {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    data = response.json()

    await ctx.log(
        f"Created pull request #{data['number']} in {owner}/{repo} "
        f"({head} -> {base})"
    )

    return {
        "success": True,
        "number": data["number"],
        "title": data["title"],
        "state": data["state"],
        "draft": data["draft"],
        "head": data["head"]["ref"],
        "base": data["base"]["ref"],
        "url": data["html_url"],
    }


@tool
async def list_pull_requests(
    owner: str,
    repo: str,
    state: str = "open",
    head: str | None = None,
    base: str | None = None,
    sort: str = "created",
    direction: str = "desc",
    per_page: int = 30,
    page: int = 1,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    List pull requests for a GitHub repository.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        state: Filter by state — "open", "closed", or "all".
        head: Filter by head branch (e.g. "feature/login" or "owner:branch").
        base: Filter by base branch (e.g. "main").
        sort: Sort field — "created", "updated", "popularity" (comment count),
            or "long-running" (age, oldest first).
        direction: Sort direction — "asc" or "desc".
        per_page: Number of pull requests per page (1-100).
        page: Page number to retrieve.
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the list of pull requests with pagination
        metadata, or an error payload when validation fails, the access token
        is missing, or the request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if state not in ["open", "closed", "all"]:
        await ctx.error("state must be 'open', 'closed', or 'all'.")
        return {"success": False, "error": "state must be 'open', 'closed', or 'all'."}

    if sort not in ["created", "updated", "popularity", "long-running"]:
        await ctx.error("sort must be one of: created, updated, popularity, long-running.")
        return {
            "success": False,
            "error": "sort must be one of: created, updated, popularity, long-running.",
        }

    if direction not in ["asc", "desc"]:
        await ctx.error("direction must be 'asc' or 'desc'.")
        return {"success": False, "error": "direction must be 'asc' or 'desc'."}

    if per_page < 1 or per_page > 100:
        await ctx.error("per_page must be between 1 and 100.")
        return {"success": False, "error": "per_page must be between 1 and 100."}

    if page < 1:
        await ctx.error("page must be >= 1.")
        return {"success": False, "error": "page must be >= 1."}

    headers = tokens["headers"]
    api_url = tokens["api_url"]

    params = {
        "state": state,
        "sort": sort,
        "direction": direction,
        "per_page": per_page,
        "page": page,
    }

    if head:
        params["head"] = head
    if base:
        params["base"] = base

    try:
        response = requests.get(
            f"{api_url}/repos/{owner}/{repo}/pulls",
            headers=headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        body = ""
        if e.response is not None:
            try:
                body = e.response.text
            except Exception:
                body = "<unreadable response body>"
        await ctx.error(
            f"Failed to list pull requests in {owner}/{repo}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    raw_prs = response.json()

    await ctx.log(
        f"Retrieved {len(raw_prs)} {state} pull requests from {owner}/{repo} "
        f"(page {page})"
    )

    return {
        "success": True,
        "count": len(raw_prs),
        "page": page,
        "per_page": per_page,
        "state": state,
        "pull_requests": [
            {
                "number": pr["number"],
                "title": pr["title"],
                "state": pr["state"],
                "draft": pr["draft"],
                "head": pr["head"]["ref"],
                "base": pr["base"]["ref"],
                "user": pr["user"]["login"] if pr.get("user") else None,
                "labels": [label["name"] for label in pr.get("labels", [])],
                "created_at": pr["created_at"],
                "updated_at": pr["updated_at"],
                "closed_at": pr.get("closed_at"),
                "merged_at": pr.get("merged_at"),
                "mergeable": pr.get("mergeable"),
                "url": pr["html_url"],
            }
            for pr in raw_prs
        ],
    }



@tool
async def get_pull_request(
    owner: str,
    repo: str,
    pull_number: int,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Get details of a GitHub pull request.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        pull_number: Pull request number.
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the pull request details (state, mergeability,
        head/base branch info, commit/file stats, timestamps, and links), or
        an error payload when the access token is missing, the pull request
        number is invalid, or the request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if pull_number <= 0:
        await ctx.error("pull_number must be a positive integer.")
        return {"success": False, "error": "pull_number must be a positive integer."}

    headers = tokens["headers"]
    api_url = tokens["api_url"]

    try:
        response = requests.get(
            f"{api_url}/repos/{owner}/{repo}/pulls/{pull_number}",
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        body = ""
        if e.response is not None:
            try:
                body = e.response.text
            except Exception:
                body = "<unreadable response body>"
        await ctx.error(
            f"Failed to get pull request #{pull_number} in {owner}/{repo}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    data = response.json()

    await ctx.log(
        f"Retrieved pull request #{data['number']} in {owner}/{repo} "
        f"(state={data.get('state')})"
    )

    return {
        "success": True,
        "number": data["number"],
        "title": data["title"],
        "body": data["body"],
        "state": data["state"],
        "draft": data["draft"],
        "merged": data["merged"],
        "mergeable": data["mergeable"],
        "mergeable_state": data["mergeable_state"],
        "head": {
            "branch": data["head"]["ref"],
            "sha": data["head"]["sha"],
            "repo": data["head"]["repo"]["full_name"]
            if data["head"]["repo"]
            else None,
        },
        "base": {
            "branch": data["base"]["ref"],
            "sha": data["base"]["sha"],
            "repo": data["base"]["repo"]["full_name"]
            if data["base"]["repo"]
            else None,
        },
        "author": data["user"]["login"] if data.get("user") else None,
        "labels": [label["name"] for label in data.get("labels", [])],
        "url": data["html_url"],
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
        "closed_at": data.get("closed_at"),
        "merged_at": data.get("merged_at"),
        "commits": data["commits"],
        "changed_files": data["changed_files"],
        "additions": data["additions"],
        "deletions": data["deletions"],
    }

@tool
async def update_pull_request(
    owner: str,
    repo: str,
    pull_number: int,
    title: str | None = None,
    body: str | None = None,
    state: str | None = None,
    base: str | None = None,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Update an existing GitHub pull request.

    Only fields explicitly provided will be updated.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        pull_number: Pull request number.
        title: New pull request title.
        body: New pull request description.
        state: "open" or "closed".
        base: Branch to merge the pull request into.
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the updated pull request information, or an
        error payload when validation fails, the access token is missing,
        or the request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if pull_number <= 0:
        await ctx.error("pull_number must be a positive integer.")
        return {"success": False, "error": "pull_number must be a positive integer."}

    if state is not None and state not in ["open", "closed"]:
        await ctx.error("state must be 'open' or 'closed'.")
        return {"success": False, "error": "state must be 'open' or 'closed'."}

    headers = tokens["headers"]
    api_url = tokens["api_url"]

    payload = {}

    if title is not None:
        if not title.strip():
            await ctx.error("Pull request title cannot be empty.")
            return {"success": False, "error": "Pull request title cannot be empty."}

        payload["title"] = title

    if body is not None:
        payload["body"] = body

    if state is not None:
        payload["state"] = state

    if base is not None:
        if not base.strip():
            await ctx.error("Base branch cannot be empty.")
            return {"success": False, "error": "Base branch cannot be empty."}

        payload["base"] = base

    if not payload:
        await ctx.error("At least one field must be provided.")
        return {"success": False, "error": "At least one field must be provided."}

    try:
        response = requests.patch(
            f"{api_url}/repos/{owner}/{repo}/pulls/{pull_number}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        body = ""
        if e.response is not None:
            try:
                body = e.response.text
            except Exception:
                body = "<unreadable response body>"
        await ctx.error(
            f"Failed to update pull request #{pull_number} in {owner}/{repo}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    data = response.json()

    await ctx.log(
        f"Updated pull request #{data['number']} in {owner}/{repo} "
        f"(state={data.get('state')})"
    )

    return {
        "success": True,
        "number": data["number"],
        "title": data["title"],
        "body": data["body"],
        "state": data["state"],
        "draft": data["draft"],
        "head": data["head"]["ref"],
        "base": data["base"]["ref"],
        "merged": data.get("merged", False),
        "url": data["html_url"],
        "updated_at": data["updated_at"],
    }
