import os
import requests
from dotenv import load_dotenv
load_dotenv()
from fastmcp.tools import tool
from fastmcp.dependencies import Depends
from fastmcp.server.dependencies import get_context
import base64

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
async def get_file(owner: str,repo: str,path: str,ref: str | None = None,tokens: dict = Depends(GitHubTokens)) -> dict:
    """
    Get a file from a GitHub repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        path: Path to the file inside the repository.
        ref: Optional branch, tag, or commit SHA.

    Returns:
        File metadata and decoded content.
    """

    ctx=get_context()
    
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    headers = tokens["headers"]

    params = {}

    if ref:
        params["ref"] = ref

    response = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
        headers=headers,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if isinstance(data, list):
        await ctx.error("The specified path is a directory, not a file.")
        return {"success": False, "error": "The specified path is a directory, not a file."}

    content = data.get("content", "")
    encoding = data.get("encoding")

    if encoding == "base64":
        decoded_content = base64.b64decode(
            content.replace("\n", "")
        ).decode("utf-8")
    else:
        decoded_content = content
        
    await ctx.log(f"Retrieved file: {data['name']} from {owner}/{repo} at path: {path}")
    return {
        "success": True,
        "name": data["name"],
        "path": data["path"],
        "sha": data["sha"],
        "size": data["size"],
        "url": data["html_url"],
        "download_url": data["download_url"],
        "content": decoded_content,
    }


@tool
async def create_file(
    owner: str,
    repo: str,
    path: str,
    content: str,
    message: str,
    branch: str | None = None,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Create a new file in a GitHub repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        path: File path inside the repository.
        content: File content as a string.
        message: Commit message.
        branch: Optional branch name.
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing file and commit information, or an error payload
        when the access token is missing or the request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    headers = tokens["headers"]

    payload = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
    }

    if branch:
        payload["branch"] = branch

    try:
        response = requests.put(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        await ctx.error(f"Failed to create file {path} in {owner}/{repo}: {e}")
        return {"success": False, "error": str(e)}

    data = response.json()

    await ctx.log(f"Created file {data['content']['path']} in {owner}/{repo}")

    return {
        "success": True,
        "message": message,
        "path": data["content"]["path"],
        "sha": data["content"]["sha"],
        "commit_sha": data["commit"]["sha"],
        "url": data["content"]["html_url"],
    }


@tool
async def update_file(
    owner: str,
    repo: str,
    path: str,
    content: str,
    message: str,
    sha: str,
    branch: str | None = None,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Update an existing file in a GitHub repository.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        path: File path inside the repository.
        content: New file content.
        message: Commit message.
        sha: Current SHA of the file being updated.
        branch: Optional branch name.
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing updated file and commit information, or an error
        payload when the access token is missing or the request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    headers = tokens["headers"]

    payload = {
        "message": message,
        "content": base64.b64encode(
            content.encode("utf-8")
        ).decode("utf-8"),
        "sha": sha,
    }

    if branch:
        payload["branch"] = branch

    try:
        response = requests.put(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        await ctx.error(f"Failed to update file {path} in {owner}/{repo}: {e}")
        return {"success": False, "error": str(e)}

    data = response.json()

    await ctx.log(f"Updated file {data['content']['path']} in {owner}/{repo}")

    return {
        "success": True,
        "message": message,
        "path": data["content"]["path"],
        "sha": data["content"]["sha"],
        "commit_sha": data["commit"]["sha"],
        "url": data["content"]["html_url"],
    }


@tool
async def delete_file(
    owner: str,
    repo: str,
    path: str,
    message: str,
    branch: str | None = None,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Delete a file from a GitHub repository.

    The current file SHA is looked up automatically before the delete call, so
    callers don't need to fetch it themselves.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.
        path: File path inside the repository.
        message: Commit message.
        branch: Optional branch name.
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the deletion commit SHA, or an error payload
        when the access token is missing, the path is a directory, or the
        request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    headers = tokens["headers"]

    # Get current file SHA
    params = {}

    if branch:
        params["ref"] = branch

    try:
        get_response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
            headers=headers,
            params=params,
            timeout=30,
        )
        get_response.raise_for_status()
    except requests.RequestException as e:
        await ctx.error(f"Failed to fetch SHA for {path} in {owner}/{repo}: {e}")
        return {"success": False, "error": str(e)}

    file_data = get_response.json()

    if isinstance(file_data, list):
        await ctx.error(f"{path} is a directory, not a file.")
        return {"success": False, "error": f"{path} is a directory, not a file."}

    sha = file_data["sha"]

    # Delete file
    payload = {
        "message": message,
        "sha": sha,
    }

    if branch:
        payload["branch"] = branch

    try:
        response = requests.delete(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        await ctx.error(f"Failed to delete {path} in {owner}/{repo}: {e}")
        return {"success": False, "error": str(e)}

    data = response.json()

    await ctx.log(f"Deleted {path} from {owner}/{repo}")

    return {
        "success": True,
        "message": message,
        "path": path,
        "commit_sha": data["commit"]["sha"],
    }




