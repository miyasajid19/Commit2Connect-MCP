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