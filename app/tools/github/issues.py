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
async def create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str = "",
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Create an issue in a GitHub repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        title: Issue title.
        body: Issue description.
        labels: Optional list of label names.
        assignees: Optional list of GitHub usernames.
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the created issue information, or an error
        payload when the access token is missing, the title is empty, or the
        request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if not title.strip():
        await ctx.error("Issue title cannot be empty.")
        return {"success": False, "error": "Issue title cannot be empty."}

    headers = tokens["headers"]

    payload = {
        "title": title,
        "body": body,
    }

    if labels:
        payload["labels"] = labels

    if assignees:
        payload["assignees"] = assignees

    try:
        response = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        await ctx.error(f"Failed to create issue in {owner}/{repo}: {e}")
        return {"success": False, "error": str(e)}

    data = response.json()

    await ctx.log(f"Created issue #{data['number']} in {owner}/{repo}")

    return {
        "success": True,
        "issue_number": data["number"],
        "title": data["title"],
        "state": data["state"],
        "body": data["body"],
        "url": data["html_url"],
        "created_at": data["created_at"],
        "user": data["user"]["login"],
    }



@tool
async def update_issue(
    owner: str,
    repo: str,
    issue_number: int,
    title: str | None = None,
    body: str | None = None,
    state: str | None = None,
    state_reason: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
    milestone: int | None = None,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Update an existing GitHub issue.

    Only fields explicitly provided will be updated.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        issue_number: Issue number.

        title:
            New issue title.

        body:
            New issue description.

        state:
            "open" or "closed".

        state_reason:
            Reason for the state.
            Supported values include:
            "completed", "not_planned", "reopened".

        labels:
            Replace existing labels with these labels.

        assignees:
            Replace existing assignees with these usernames.

        milestone:
            Milestone number. Use None to remove the milestone.

        tokens:
            Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the updated issue information, or an error
        payload when validation fails, the access token is missing, or the
        request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    headers = tokens["headers"]

    payload = {}

    if title is not None:
        if not title.strip():
            await ctx.error("Issue title cannot be empty.")
            return {"success": False, "error": "Issue title cannot be empty."}

        payload["title"] = title

    if body is not None:
        payload["body"] = body

    if state is not None:
        if state not in ["open", "closed"]:
            await ctx.error("state must be 'open' or 'closed'.")
            return {"success": False, "error": "state must be 'open' or 'closed'."}

        payload["state"] = state

    if state_reason is not None:
        allowed_reasons = [
            "completed",
            "not_planned",
            "reopened",
        ]

        if state_reason not in allowed_reasons:
            await ctx.error(f"state_reason must be one of: {allowed_reasons}")
            return {"success": False, "error": f"state_reason must be one of: {allowed_reasons}"}

        payload["state_reason"] = state_reason

    if labels is not None:
        payload["labels"] = labels

    if assignees is not None:
        payload["assignees"] = assignees

    if milestone is not None:
        payload["milestone"] = milestone

    if not payload:
        await ctx.error("At least one field must be provided to update the issue.")
        return {"success": False, "error": "At least one field must be provided to update the issue."}

    try:
        response = requests.patch(
            f"https://api.github.com/repos/"
            f"{owner}/{repo}/issues/{issue_number}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        await ctx.error(f"Failed to update issue #{issue_number} in {owner}/{repo}: {e}")
        return {"success": False, "error": str(e)}

    data = response.json()

    await ctx.log(f"Updated issue #{data['number']} in {owner}/{repo}")

    return {
        "success": True,
        "issue_number": data["number"],
        "title": data["title"],
        "body": data["body"],
        "state": data["state"],
        "state_reason": data.get("state_reason"),
        "labels": [
            label["name"]
            for label in data["labels"]
        ],
        "assignees": [
            user["login"]
            for user in data["assignees"]
        ],
        "milestone": (
            data["milestone"]["title"]
            if data["milestone"]
            else None
        ),
        "url": data["html_url"],
        "updated_at": data["updated_at"],
    }
    
@tool
async def close_issue(
    owner: str,
    repo: str,
    issue_number: int,
    state_reason: str = "completed",
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Close a GitHub issue.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        issue_number: Issue number.
        state_reason:
            "completed" or "not_planned".
        tokens:
            Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the closed issue information, or an error
        payload when validation fails, the access token is missing, or the
        request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if state_reason not in ["completed", "not_planned"]:
        await ctx.error("state_reason must be 'completed' or 'not_planned'.")
        return {"success": False, "error": "state_reason must be 'completed' or 'not_planned'."}

    headers = tokens["headers"]

    payload = {
        "state": "closed",
        "state_reason": state_reason,
    }

    try:
        response = requests.patch(
            f"https://api.github.com/repos/"
            f"{owner}/{repo}/issues/{issue_number}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        await ctx.error(f"Failed to close issue #{issue_number} in {owner}/{repo}: {e}")
        return {"success": False, "error": str(e)}

    data = response.json()

    await ctx.log(f"Closed issue #{data['number']} in {owner}/{repo}")

    return {
        "success": True,
        "issue_number": data["number"],
        "title": data["title"],
        "state": data["state"],
        "state_reason": data.get("state_reason"),
        "url": data["html_url"],
    }


@tool
async def list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    labels: str | None = None,
    assignee: str | None = None,
    creator: str | None = None,
    mentioned: str | None = None,
    sort: str = "created",
    direction: str = "desc",
    since: str | None = None,
    per_page: int = 30,
    page: int = 1,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    List issues in a GitHub repository.

    Pull requests are excluded by default — pass ``include_pulls=True`` to
    include them.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        state:
            Filter by state: "open", "closed", or "all".
        labels:
            Comma-separated list of label names (e.g. "bug,ui").
        assignee:
            GitHub username. Use ``"*"`` for issues assigned to any user, or
            ``"none"`` for unassigned issues.
        creator:
            Filter by the username that created the issues.
        mentioned:
            Filter by a username mentioned in the issues.
        sort:
            What to sort by: "created", "updated", or "comments".
        direction:
            Sort direction: "asc" or "desc".
        since:
            ISO 8601 timestamp. Only issues updated at or after this time are
            returned.
        per_page:
            Number of issues per page (1-100).
        page:
            Page number to retrieve.
        tokens:
            Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the list of issues with pagination metadata, or
        an error payload when validation fails, the access token is missing,
        or the request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if state not in ["open", "closed", "all"]:
        await ctx.error("state must be 'open', 'closed', or 'all'.")
        return {"success": False, "error": "state must be 'open', 'closed', or 'all'."}

    if sort not in ["created", "updated", "comments"]:
        await ctx.error("sort must be 'created', 'updated', or 'comments'.")
        return {"success": False, "error": "sort must be 'created', 'updated', or 'comments'."}

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

    params = {
        "state": state,
        "sort": sort,
        "direction": direction,
        "per_page": per_page,
        "page": page,
    }

    if labels:
        params["labels"] = labels
    if assignee:
        params["assignee"] = assignee
    if creator:
        params["creator"] = creator
    if mentioned:
        params["mentioned"] = mentioned
    if since:
        params["since"] = since

    try:
        response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/issues",
            headers=headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        await ctx.error(f"Failed to list issues in {owner}/{repo}: {e}")
        return {"success": False, "error": str(e)}

    raw_issues = response.json()

    # Exclude pull requests — they're returned by this endpoint too.
    issues = [
        issue for issue in raw_issues if "pull_request" not in issue
    ]
    pulls_excluded = len(raw_issues) - len(issues)

    await ctx.log(
        f"Retrieved {len(issues)} {state} issues from {owner}/{repo} "
        f"(page {page}, {pulls_excluded} pull requests excluded)"
    )

    return {
        "success": True,
        "count": len(issues),
        "page": page,
        "per_page": per_page,
        "pull_requests_excluded": pulls_excluded,
        "issues": [
            {
                "issue_number": issue["number"],
                "title": issue["title"],
                "state": issue["state"],
                "user": issue["user"]["login"] if issue.get("user") else None,
                "labels": [label["name"] for label in issue.get("labels", [])],
                "assignees": [
                    user["login"]
                    for user in issue.get("assignees", [])
                ],
                "comments": issue["comments"],
                "created_at": issue["created_at"],
                "updated_at": issue["updated_at"],
                "closed_at": issue.get("closed_at"),
                "url": issue["html_url"],
            }
            for issue in issues
        ],
    }
 
 

@tool
async def reopen_issue(
    owner: str,
    repo: str,
    issue_number: int,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Reopen a closed GitHub issue.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        issue_number: Issue number to reopen.
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the reopened issue information, or an error
        payload when validation fails, the access token is missing, or the
        request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if issue_number <= 0:
        await ctx.error("issue_number must be a positive integer.")
        return {"success": False, "error": "issue_number must be a positive integer."}

    headers = tokens["headers"]
    api_url = tokens["api_url"]

    payload = {
        "state": "open",
        "state_reason": "reopened",
    }

    try:
        response = requests.patch(
            f"{api_url}/repos/{owner}/{repo}/issues/{issue_number}",
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
            f"Failed to reopen issue #{issue_number} in {owner}/{repo}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    data = response.json()

    await ctx.log(f"Reopened issue #{data['number']} in {owner}/{repo}")

    return {
        "success": True,
        "issue_number": data["number"],
        "title": data["title"],
        "state": data["state"],
        "state_reason": data.get("state_reason"),
        "url": data["html_url"],
    }


@tool
async def create_issue_comment(
    owner: str,
    repo: str,
    issue_number: int,
    body: str,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Create a comment on a GitHub issue.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        issue_number: Issue number to comment on.
        body: Comment text (Markdown is supported).
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the created comment information, or an error
        payload when validation fails, the access token is missing, or the
        request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if issue_number <= 0:
        await ctx.error("issue_number must be a positive integer.")
        return {"success": False, "error": "issue_number must be a positive integer."}

    if not body.strip():
        await ctx.error("Comment body cannot be empty.")
        return {"success": False, "error": "Comment body cannot be empty."}

    headers = tokens["headers"]
    api_url = tokens["api_url"]

    payload = {"body": body}

    try:
        response = requests.post(
            f"{api_url}/repos/{owner}/{repo}/issues/{issue_number}/comments",
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
            f"Failed to create comment on issue #{issue_number} "
            f"in {owner}/{repo}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    data = response.json()

    await ctx.log(
        f"Created comment #{data['id']} on issue #{issue_number} in {owner}/{repo}"
    )

    return {
        "success": True,
        "id": data["id"],
        "body": data["body"],
        "user": data["user"]["login"] if data.get("user") else None,
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
        "url": data["html_url"],
    }


@tool
async def list_issue_comments(
    owner: str,
    repo: str,
    issue_number: int,
    per_page: int = 30,
    page: int = 1,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    List comments on a GitHub issue.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        issue_number: Issue number whose comments to list.
        per_page: Number of comments per page (1-100).
        page: Page number to retrieve.
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the list of comments with pagination metadata,
        or an error payload when validation fails, the access token is
        missing, or the request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if issue_number <= 0:
        await ctx.error("issue_number must be a positive integer.")
        return {"success": False, "error": "issue_number must be a positive integer."}

    if per_page < 1 or per_page > 100:
        await ctx.error("per_page must be between 1 and 100.")
        return {"success": False, "error": "per_page must be between 1 and 100."}

    if page < 1:
        await ctx.error("page must be >= 1.")
        return {"success": False, "error": "page must be >= 1."}

    headers = tokens["headers"]
    api_url = tokens["api_url"]

    params = {
        "per_page": per_page,
        "page": page,
    }

    try:
        response = requests.get(
            f"{api_url}/repos/{owner}/{repo}/issues/{issue_number}/comments",
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
            f"Failed to list comments on issue #{issue_number} "
            f"in {owner}/{repo}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    raw_comments = response.json()

    await ctx.log(
        f"Retrieved {len(raw_comments)} comment(s) on issue #{issue_number} "
        f"in {owner}/{repo} (page {page})"
    )

    return {
        "success": True,
        "issue_number": issue_number,
        "count": len(raw_comments),
        "page": page,
        "per_page": per_page,
        "comments": [
            {
                "id": comment["id"],
                "body": comment["body"],
                "user": comment["user"]["login"] if comment.get("user") else None,
                "created_at": comment["created_at"],
                "updated_at": comment["updated_at"],
                "url": comment["html_url"],
            }
            for comment in raw_comments
        ],
    }


@tool
async def delete_issue_comment(
    owner: str,
    repo: str,
    comment_id: int,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Delete a comment on a GitHub issue.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        comment_id: Numeric ID of the comment to delete.
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary confirming the deletion, or an error payload when the
        access token is missing, the comment ID is invalid, or the request
        fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if comment_id <= 0:
        await ctx.error("comment_id must be a positive integer.")
        return {"success": False, "error": "comment_id must be a positive integer."}

    headers = tokens["headers"]
    api_url = tokens["api_url"]

    try:
        response = requests.delete(
            f"{api_url}/repos/{owner}/{repo}/issues/comments/{comment_id}",
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
            f"Failed to delete comment #{comment_id} in {owner}/{repo}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    await ctx.log(f"Deleted comment #{comment_id} in {owner}/{repo}")

    return {
        "success": True,
        "comment_id": comment_id,
        "message": f"Comment #{comment_id} deleted successfully from {owner}/{repo}.",
    }
