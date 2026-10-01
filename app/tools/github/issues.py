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
