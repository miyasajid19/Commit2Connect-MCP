import os
import token
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
async def create_repository(name: str,description: str = "",private: bool = False,auto_init: bool = False,tokens: dict = Depends(GitHubTokens))-> dict:
    """
    Create a new GitHub repository for the authenticated user.

    Args:
        name: Repository name.
        description: Optional repository description.
        private: Whether the repository should be private.
        auto_init: Initialize the repository with a README.

    Returns:
        Dictionary containing repository information.
    """
    ctx=get_context()
    token = tokens["access_token"]

    if not token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")  
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    headers = tokens["headers"]
    payload = {
        "name": name,
        "description": description,
        "private": private,
        "auto_init": auto_init,
    }

    response = requests.post(
        "https://api.github.com/user/repos",
        headers=headers,
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()
    await ctx.log(f"Repository '{name}' created successfully.")
    return {
        "success": True,
        "name": data["name"],
        "full_name": data["full_name"],
        "private": data["private"],
        "html_url": data["html_url"],
        "clone_url": data["clone_url"],
        "ssh_url": data["ssh_url"],
    }

