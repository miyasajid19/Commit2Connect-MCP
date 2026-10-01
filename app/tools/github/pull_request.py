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
