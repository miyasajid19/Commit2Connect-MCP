import os
import token
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
