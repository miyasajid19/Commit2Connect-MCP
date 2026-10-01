import os
import requests
from dotenv import load_dotenv
load_dotenv()
from fastmcp.tools import tool
from fastmcp.dependencies import Depends
from fastmcp.server.dependencies import get_context



def GitHubTokens() -> dict:
    return {
        "access_token": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
        "owner": os.getenv("GITHUB_OWNER"),
        "headers": {
            "Authorization": f"Bearer {os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN')}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        },
        "api_url": "https://api.github.com",
    }


@tool
async def get_branch(
    owner: str,
    repo: str,
    branch: str,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Get information about a single GitHub branch.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        branch: Branch name (e.g. "main" or "feature/contributing-guide").
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing branch metadata including the commit SHA at the
        tip of the branch, the protected-branch flag, and a link to the
        branch on GitHub. Returns an error payload when the access token is
        missing or the request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if not branch.strip():
        await ctx.error("Branch name cannot be empty.")
        return {"success": False, "error": "Branch name cannot be empty."}

    headers = tokens["headers"]
    api_url = tokens["api_url"]

    try:
        response = requests.get(
            f"{api_url}/repos/{owner}/{repo}/branches/{branch}",
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
        await ctx.error(f"Failed to get branch '{branch}' in {owner}/{repo}: {e} | {body}")
        return {
            "success": False,
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    data = response.json()

    commit = data.get("commit", {})

    await ctx.log(
        f"Fetched branch '{data.get('name')}' in {owner}/{repo} "
        f"(sha {commit.get('sha', '')[:7]})"
    )

    return {
        "success": True,
        "name": data["name"],
        "sha": commit.get("sha"),
        "protected": data.get("protected", False),
        "url": f"https://github.com/{owner}/{repo}/tree/{data['name']}",
        "commit": {
            "sha": commit.get("sha"),
            "url": commit.get("html_url"),
            "message": commit.get("commit", {}).get("message"),
            "author": (commit.get("commit", {}).get("author") or {}).get("name"),
            "date": (commit.get("commit", {}).get("author") or {}).get("date"),
        },
    }


@tool
async def get_branch_sha(
    repo: str,
    branch: str,
    owner: str="miyasajid19",
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Get the commit SHA at the tip of a GitHub branch.

    Useful when you need the SHA to pass to the Git Data API (refs/heads,
    trees, commits).

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        branch: Branch name (e.g. "main").
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the branch SHA, or an error payload when the
        access token is missing or the request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if not branch.strip():
        await ctx.error("Branch name cannot be empty.")
        return {"success": False, "error": "Branch name cannot be empty."}

    headers = tokens["headers"]
    api_url = tokens["api_url"]

    try:
        response = requests.get(
            f"{api_url}/repos/{owner}/{repo}/git/ref/heads/{branch}",
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
        await ctx.error(f"Failed to get SHA for branch '{branch}' in {owner}/{repo}: {e} | {body}")
        return {
            "success": False,
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    data = response.json()

    sha = data["object"]["sha"]

    await ctx.log(f"Branch '{branch}' in {owner}/{repo} is at {sha[:7]}")

    return {
        "success": True,
        "branch": branch,
        "sha": sha,
    }
    

@tool
async def create_branch(
    repo: str,
    branch: str,
    source_branch: str,
    owner: str="miyasajid19",
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Create a new GitHub branch from an existing branch.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        branch: Name of the new branch to create (e.g. "feature/contributing-guide").
        source_branch: Name of the existing branch to branch from (e.g. "main").
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the new branch ref details, or an error payload
        when the access token is missing, the source branch cannot be
        resolved, the new branch name is empty, or the request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if not branch.strip():
        await ctx.error("New branch name cannot be empty.")
        return {"success": False, "error": "New branch name cannot be empty."}

    if not source_branch.strip():
        await ctx.error("Source branch name cannot be empty.")
        return {"success": False, "error": "Source branch name cannot be empty."}

    headers = tokens["headers"]
    api_url = tokens["api_url"]

    # Step 1: look up the SHA of the source branch.
    try:
        sha_response = requests.get(
            f"{api_url}/repos/{owner}/{repo}/git/ref/heads/{source_branch}",
            headers=headers,
            timeout=30,
        )
        sha_response.raise_for_status()
    except requests.RequestException as e:
        body = ""
        if e.response is not None:
            try:
                body = e.response.text
            except Exception:
                body = "<unreadable response body>"
        await ctx.error(
            f"Failed to resolve SHA for source branch '{source_branch}' "
            f"in {owner}/{repo}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "stage": "resolve_source_sha",
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    source_sha = sha_response.json()["object"]["sha"]

    # Step 2: create the new branch ref pointing at that SHA.
    payload = {
        "ref": f"refs/heads/{branch}",
        "sha": source_sha,
    }

    try:
        response = requests.post(
            f"{api_url}/repos/{owner}/{repo}/git/refs",
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
            f"Failed to create branch '{branch}' from '{source_branch}' "
            f"in {owner}/{repo}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "stage": "create_ref",
            "source_sha": source_sha,
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    data = response.json()

    await ctx.log(
        f"Created branch '{branch}' from '{source_branch}' "
        f"in {owner}/{repo} (sha {data['object']['sha'][:7]})"
    )

    return {
        "success": True,
        "branch": branch,
        "source_branch": source_branch,
        "source_sha": source_sha,
        "ref": data.get("ref"),
        "sha": data["object"]["sha"],
        "url": data["object"].get("url"),
    }




@tool
async def list_branches(
    repo: str,
    owner: str="miyasajid19",
    protected_only: bool = False,
    per_page: int = 30,
    page: int = 1,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    List branches in a GitHub repository.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        protected_only: When True, only return protected branches.
        per_page: Number of branches per page (1-100).
        page: Page number to retrieve.
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the list of branches with pagination metadata,
        or an error payload when the access token is missing, pagination
        parameters are invalid, or the request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

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

    if protected_only:
        params["protected"] = "true"

    try:
        response = requests.get(
            f"{api_url}/repos/{owner}/{repo}/branches",
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
        await ctx.error(f"Failed to list branches in {owner}/{repo}: {e} | {body}")
        return {
            "success": False,
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    raw_branches = response.json()

    await ctx.log(
        f"Retrieved {len(raw_branches)} branches from {owner}/{repo} "
        f"(page {page}, protected_only={protected_only})"
    )

    return {
        "success": True,
        "count": len(raw_branches),
        "page": page,
        "per_page": per_page,
        "protected_only": protected_only,
        "branches": [
            {
                "name": branch["name"],
                "protected": branch["protected"],
                "sha": branch["commit"]["sha"],
                "url": f"https://github.com/{owner}/{repo}/tree/{branch['name']}",
            }
            for branch in raw_branches
        ],
    }


@tool
async def delete_branch(
    repo: str,
    branch: str,
    owner: str="miyasajid19",
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Delete a GitHub branch.

    Deleting a branch deletes the ref pointing at its tip commit. The commits
    themselves are not removed from the repository unless garbage-collected.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        branch: Branch name to delete (e.g. "feature/contributing-guide").
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary confirming the deletion, or an error payload when the
        access token is missing, the branch name is empty, the branch is the
        repository's default branch, the branch is protected, or the request
        fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if not branch.strip():
        await ctx.error("Branch name cannot be empty.")
        return {"success": False, "error": "Branch name cannot be empty."}

    headers = tokens["headers"]
    api_url = tokens["api_url"]

    try:
        response = requests.delete(
            f"{api_url}/repos/{owner}/{repo}/git/refs/heads/{branch}",
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
            f"Failed to delete branch '{branch}' in {owner}/{repo}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    await ctx.log(f"Deleted branch '{branch}' from {owner}/{repo}")

    return {
        "success": True,
        "branch": branch,
        "message": f"Branch '{branch}' deleted successfully from {owner}/{repo}.",
    }
