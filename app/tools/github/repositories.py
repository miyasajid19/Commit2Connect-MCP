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





@tool
async def get_repository(owner: str, repo: str,tokens=Depends(GitHubTokens))-> dict:
    """
    Get information about a GitHub repository.

    Args:
        owner: GitHub username or organization name.
        repo: Repository name.

    Returns:
        Repository information.
    """

    ctx = get_context()
    access_token = tokens["access_token"]
    
    if not access_token:
        await ctx.error("GITHUB_TOKEN is missing")
        return {"success": False, "error": "GITHUB_TOKEN is missing"}

    headers = tokens["headers"]
    
    response = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()
    await ctx.log(f"Repository '{owner}/{repo}' information retrieved successfully.")
    return {
        "success": True,
        "id": data["id"],
        "name": data["name"],
        "full_name": data["full_name"],
        "description": data["description"],
        "private": data["private"],
        "default_branch": data["default_branch"],
        "html_url": data["html_url"],
        "clone_url": data["clone_url"],
        "ssh_url": data["ssh_url"],
        "language": data["language"],
        "fork": data["fork"],
        "archived": data["archived"],
        "visibility": data["visibility"],
        "created_at": data["created_at"],
        "updated_at": data["updated_at"],
        "pushed_at": data["pushed_at"],
        "stars": data["stargazers_count"],
        "forks": data["forks_count"],
        "open_issues": data["open_issues_count"],
    }
    



@tool
async def list_repositories(
    visibility: str = "all",
    affiliation: str = "owner,collaborator,organization_member",
    per_page: int = 30,
    page: int = 1,
    tokens: dict = Depends(GitHubTokens)
):
    """
    List repositories accessible to the authenticated GitHub user.

    Args:
        visibility:
            all, public, or private.

        affiliation:
            Comma-separated values:
            owner, collaborator, organization_member.

        per_page:
            Number of repositories to return (1-100).

        page:
            Page number.
        tokens: dict = Depends(GitHubTokens)

    Returns:
        List of repositories and pagination information.
    """

    ctx=get_context()
    accesss_token = tokens["access_token"]

    if not accesss_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if per_page < 1 or per_page > 100:
        await ctx.error("per_page must be between 1 and 100")
        return {"success": False, "error": "per_page must be between 1 and 100"}

    if page < 1:
        await ctx.error("page must be >= 1")
        return {"success": False, "error": "page must be >= 1"}

    headers = tokens["headers"]

    params = {
        "visibility": visibility,
        "affiliation": affiliation,
        "per_page": per_page,
        "page": page,
        "sort": "updated",
        "direction": "desc",
    }

    response = requests.get(
        "https://api.github.com/user/repos",
        headers=headers,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    repositories = response.json()
    await ctx.log(f"Retrieved {len(repositories)} repositories for user.")
    return {
        "success": True,
        "count": len(repositories),
        "page": page,
        "per_page": per_page,
        "repositories": [
            {
                "id": repo["id"],
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo["description"],
                "private": repo["private"],
                "visibility": repo["visibility"],
                "default_branch": repo["default_branch"],
                "html_url": repo["html_url"],
                "clone_url": repo["clone_url"],
                "ssh_url": repo["ssh_url"],
                "language": repo["language"],
                "fork": repo["fork"],
                "archived": repo["archived"],
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "open_issues": repo["open_issues_count"],
                "updated_at": repo["updated_at"],
            }
            for repo in repositories
        ],
    }
    
    
 
@tool
async def update_repository(
    owner: str,
    repo: str,
    name: str | None = None,
    description: str | None = None,
    private: bool | None = None,
    visibility: str | None = None,
    has_issues: bool | None = None,
    has_projects: bool | None = None,
    has_wiki: bool | None = None,
    is_template: bool | None = None,
    default_branch: str | None = None,
    tokens: dict = Depends(GitHubTokens)
):
    """
    Update an existing GitHub repository.

    Only fields explicitly provided will be updated.

    Args:
        owner: GitHub username or organization.
        repo: Repository name.

        name:
            New repository name.

        description:
            New repository description.

        private:
            Make repository private/public.

        visibility:
            Repository visibility:
            public, private, or internal.

        has_issues:
            Enable/disable Issues.

        has_projects:
            Enable/disable Projects.

        has_wiki:
            Enable/disable Wiki.

        is_template:
            Mark/unmark repository as a template.

        default_branch:
            Change the default branch.
    """
    ctx = get_context()
    access_token = tokens["access_token"]

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")  
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    headers = tokens["headers"]

    # Build payload only with values that were provided.
    payload = {}

    if name is not None:
        payload["name"] = name

    if description is not None:
        payload["description"] = description

    if private is not None:
        payload["private"] = private

    if visibility is not None:
        payload["visibility"] = visibility

    if has_issues is not None:
        payload["has_issues"] = has_issues

    if has_projects is not None:
        payload["has_projects"] = has_projects

    if has_wiki is not None:
        payload["has_wiki"] = has_wiki

    if is_template is not None:
        payload["is_template"] = is_template

    if default_branch is not None:
        payload["default_branch"] = default_branch

    if not payload:
        await ctx.error("At least one repository field must be provided.")
        return {"success": False, "error": "At least one repository field must be provided."}

    response = requests.patch(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=headers,
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()
    await ctx.log(f"Repository '{owner}/{repo}' updated successfully.")
    return {
        "success": True,
        "id": data["id"],
        "name": data["name"],
        "full_name": data["full_name"],
        "description": data["description"],
        "private": data["private"],
        "visibility": data["visibility"],
        "default_branch": data["default_branch"],
        "html_url": data["html_url"],
        "clone_url": data["clone_url"],
        "ssh_url": data["ssh_url"],
        "updated_at": data["updated_at"],
    }


@tool    
async def delete_repository(
    owner: str,
    repo: str,
    tokens: dict = Depends(GitHubTokens)
):
    """
    Delete a GitHub repository.

    This operation is permanent.
    """

    ctx = get_context()
    access_token = tokens["access_token"]


    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    headers =tokens["headers"]

    response = requests.delete(
        f"https://api.github.com/repos/{owner}/{repo}",
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()
    await ctx.log(f"Repository '{owner}/{repo}' deleted successfully.")
    return {
        "success": True,
        "message": f"Repository '{owner}/{repo}' deleted successfully.",
    }
