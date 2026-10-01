import os
import requests
from dotenv import load_dotenv
load_dotenv()
from fastmcp.tools import tool
from fastmcp.dependencies import Depends
from fastmcp.server.dependencies import get_context

GITHUB_API = os.getenv("GITHUB_API_URL", "https://api.github.com")


def GitHubTokens() -> dict:
    return {
        "access_token": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"),
        "owner": os.getenv("GITHUB_OWNER"),
        "headers": {
            "Authorization": f"Bearer {os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN')}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        },
        "api_url": GITHUB_API,
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
    owner: str,
    repo: str,
    branch: str,
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