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

@tool
async def search_repositories(
    query: str,
    sort: str | None = None,
    order: str = "desc",
    per_page: int = 30,
    page: int = 1,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Search for GitHub repositories matching a query string.

    Uses GitHub's repository search syntax. Common qualifiers:
        - ``user:username`` — limit to a user's repos.
        - ``org:orgname`` — limit to an org's repos.
        - ``language:python`` — filter by language.
        - ``stars:>1000`` — minimum star count.
        - ``topic:topic-name`` — filter by topic.
        - ``in:name`` / ``in:description`` / ``in:readme`` — which field to search.
        - ``archived:false`` — exclude archived repos.

    Args:
        query: Search query string (may include GitHub qualifiers).
        sort: Optional sort field: "stars", "forks", "help-wanted-issues",
            "updated", or "best-match" (default if not provided).
        order: Sort direction: "asc" or "desc".
        per_page: Number of results per page (1-100).
        page: Page number to retrieve.
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the search results with pagination metadata, or
        an error payload when the access token is missing, the query is
        empty, sort/order/per_page/page validation fails, or the request
        fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if not query.strip():
        await ctx.error("Search query cannot be empty.")
        return {"success": False, "error": "Search query cannot be empty."}

    if sort is not None and sort not in [
        "stars",
        "forks",
        "help-wanted-issues",
        "updated",
        "best-match",
    ]:
        await ctx.error(
            "sort must be one of: stars, forks, help-wanted-issues, "
            "updated, best-match."
        )
        return {
            "success": False,
            "error": (
                "sort must be one of: stars, forks, help-wanted-issues, "
                "updated, best-match."
            ),
        }

    if order not in ["asc", "desc"]:
        await ctx.error("order must be 'asc' or 'desc'.")
        return {"success": False, "error": "order must be 'asc' or 'desc'."}

    if per_page < 1 or per_page > 100:
        await ctx.error("per_page must be between 1 and 100.")
        return {"success": False, "error": "per_page must be between 1 and 100."}

    if page < 1:
        await ctx.error("page must be >= 1.")
        return {"success": False, "error": "page must be >= 1."}

    headers = tokens["headers"]
    api_url = tokens["api_url"]

    params = {
        "q": query,
        "per_page": per_page,
        "page": page,
        "order": order,
    }

    if sort:
        params["sort"] = sort

    try:
        response = requests.get(
            f"{api_url}/search/repositories",
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
        await ctx.error(f"Repository search failed for query '{query}': {e} | {body}")
        return {
            "success": False,
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    data = response.json()
    items = data.get("items", [])

    await ctx.log(
        f"Repository search for '{query}' returned {len(items)} result(s) "
        f"(page {page}, {data.get('total_count', 0)} total)"
    )

    return {
        "success": True,
        "query": query,
        "total_count": data.get("total_count", 0),
        "incomplete_results": data.get("incomplete_results", False),
        "page": page,
        "per_page": per_page,
        "count": len(items),
        "repositories": [
            {
                "id": repo["id"],
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo["description"],
                "private": repo["private"],
                "language": repo["language"],
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "default_branch": repo["default_branch"],
                "owner": repo["owner"]["login"],
                "url": repo["html_url"],
            }
            for repo in items
        ],
    }



@tool
async def search_code(
    query: str,
    sort: str | None = None,
    order: str = "desc",
    per_page: int = 30,
    page: int = 1,
    include_text_matches: bool = False,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Search code across GitHub.

    The GitHub Code Search API requires at least one qualifier in the query
    string — a bare keyword like ``"foo"`` returns 422. Common qualifiers:

        - ``repo:owner/name`` — restrict to one repository (required if your
          token can't access all of GitHub's code).
        - ``user:username`` — restrict to a user's repos.
        - ``org:orgname`` — restrict to an org's repos.
        - ``language:python`` — filter by language.
        - ``path:src/`` — restrict to files under a path.
        - ``extension:py`` — restrict to a file extension.
        - ``filename:foo`` — match by filename.

    Args:
        query: Code search query string. Must include at least one qualifier.
        sort: Optional sort field: "indexed" (only valid sort for code search).
        order: Sort direction: "asc" or "desc".
        per_page: Number of results per page (1-100).
        page: Page number to retrieve.
        include_text_matches: When True, fetches each result's text-match
            fragments via the GitHub text-match media type
            (``application/vnd.github.text-match+json``) and includes them
            in the response. Adds extra round trips.
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the search results with pagination metadata, or
        an error payload when the access token is missing, the query is
        empty, sort/order/per_page/page validation fails, or the request
        fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if not query.strip():
        await ctx.error("Search query cannot be empty.")
        return {"success": False, "error": "Search query cannot be empty."}

    if sort is not None and sort not in ["indexed"]:
        await ctx.error("sort must be 'indexed' for code search.")
        return {"success": False, "error": "sort must be 'indexed' for code search."}

    if order not in ["asc", "desc"]:
        await ctx.error("order must be 'asc' or 'desc'.")
        return {"success": False, "error": "order must be 'asc' or 'desc'."}

    if per_page < 1 or per_page > 100:
        await ctx.error("per_page must be between 1 and 100.")
        return {"success": False, "error": "per_page must be between 1 and 100."}

    if page < 1:
        await ctx.error("page must be >= 1.")
        return {"success": False, "error": "page must be >= 1."}

    headers = dict(tokens["headers"])
    api_url = tokens["api_url"]

    # The text-match media type returns highlighted fragments per result;
    # opt-in to keep default responses small.
    if include_text_matches:
        headers["Accept"] = "application/vnd.github.text-match+json"

    params = {
        "q": query,
        "per_page": per_page,
        "page": page,
    }

    if sort:
        params["sort"] = sort
        params["order"] = order

    try:
        response = requests.get(
            f"{api_url}/search/code",
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
        await ctx.error(f"Code search failed for query '{query}': {e} | {body}")
        return {
            "success": False,
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    data = response.json()
    items = data.get("items", [])

    await ctx.log(
        f"Code search for '{query}' returned {len(items)} result(s) "
        f"(page {page}, {data.get('total_count', 0)} total)"
    )

    results = []
    for item in items:
        entry = {
            "name": item["name"],
            "path": item["path"],
            "sha": item["sha"],
            "repository": item["repository"]["full_name"],
            "url": item["html_url"],
            "git_url": item["git_url"],
        }

        if include_text_matches and "text_matches" in item:
            entry["text_matches"] = [
                {
                    "fragment": match.get("fragment"),
                    "matches": [
                        {
                            "text": m.get("text"),
                            "indices": m.get("indices"),
                        }
                        for m in match.get("matches", [])
                    ],
                }
                for match in item["text_matches"]
            ]

        results.append(entry)

    return {
        "success": True,
        "query": query,
        "total_count": data.get("total_count", 0),
        "incomplete_results": data.get("incomplete_results", False),
        "page": page,
        "per_page": per_page,
        "count": len(items),
        "results": results,
    }
