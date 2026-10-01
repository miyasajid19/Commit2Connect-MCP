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
        "api_url": "https://api.github.com",
        "headers": {
            "Authorization": f"Bearer {os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN')}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2026-03-10",
        },
    }


@tool
async def list_commits(
    owner: str,
    repo: str,
    branch: str | None = None,
    author: str | None = None,
    since: str | None = None,
    until: str | None = None,
    path: str | None = None,
    per_page: int = 30,
    page: int = 1,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    List commits in a GitHub repository.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        branch: Optional branch, tag, or commit SHA to scope the listing to
            (passed to GitHub as the ``sha`` query parameter).
        author: Optional GitHub username or email address to filter by.
        since: Optional ISO 8601 timestamp; only commits after this are
            returned.
        until: Optional ISO 8601 timestamp; only commits before this are
            returned.
        path: Optional file path to restrict the listing to commits that
            touch that path.
        per_page: Number of commits per page (1-100).
        page: Page number to retrieve.
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the list of commits with pagination metadata,
        or an error payload when validation fails, the access token is
        missing, or the request fails.
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

    if branch:
        params["sha"] = branch
    if author:
        params["author"] = author
    if since:
        params["since"] = since
    if until:
        params["until"] = until
    if path:
        params["path"] = path

    try:
        response = requests.get(
            f"{api_url}/repos/{owner}/{repo}/commits",
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
        await ctx.error(
            f"Failed to list commits in {owner}/{repo}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    raw_commits = response.json()

    await ctx.log(
        f"Retrieved {len(raw_commits)} commit(s) from {owner}/{repo} "
        f"(page {page}, branch={branch or 'default'})"
    )

    return {
        "success": True,
        "count": len(raw_commits),
        "page": page,
        "per_page": per_page,
        "branch": branch,
        "commits": [
            {
                "sha": commit["sha"],
                "message": commit["commit"]["message"],
                "author": (commit.get("commit", {}).get("author") or {}).get("name"),
                "date": (commit.get("commit", {}).get("author") or {}).get("date"),
                "committer": (
                    commit.get("commit", {}).get("committer") or {}
                ).get("name"),
                "url": commit["html_url"],
            }
            for commit in raw_commits
        ],
    }


@tool
async def get_commit(
    owner: str,
    repo: str,
    commit_sha: str,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Get details of a single commit, including files changed and stats.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        commit_sha: SHA of the commit to retrieve.
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing commit metadata (author, committer, parents,
        files changed with diff stats, and the overall commit stats), or an
        error payload when the access token is missing, the SHA is empty,
        or the request fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if not commit_sha.strip():
        await ctx.error("commit_sha cannot be empty.")
        return {"success": False, "error": "commit_sha cannot be empty."}

    headers = tokens["headers"]
    api_url = tokens["api_url"]

    try:
        response = requests.get(
            f"{api_url}/repos/{owner}/{repo}/commits/{commit_sha}",
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
            f"Failed to get commit {commit_sha[:7]} in {owner}/{repo}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    data = response.json()

    author = data.get("commit", {}).get("author") or {}
    committer = data.get("commit", {}).get("committer") or {}

    await ctx.log(
        f"Retrieved commit {data.get('sha', commit_sha)[:7]} in {owner}/{repo}"
    )

    return {
        "success": True,
        "sha": data["sha"],
        "message": data["commit"]["message"],
        "author": {
            "name": author.get("name"),
            "email": author.get("email"),
            "date": author.get("date"),
        },
        "committer": {
            "name": committer.get("name"),
            "email": committer.get("email"),
            "date": committer.get("date"),
        },
        "parents": [
            parent["sha"]
            for parent in data.get("parents", [])
        ],
        "files": [
            {
                "filename": file["filename"],
                "status": file["status"],
                "additions": file["additions"],
                "deletions": file["deletions"],
                "changes": file["changes"],
            }
            for file in data.get("files", [])
        ],
        "stats": data.get("stats"),
        "url": data["html_url"],
    }


@tool
async def compare_commits(
    owner: str,
    repo: str,
    base: str,
    head: str,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Compare two commits, branches, or tags using a three-dot comparison.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        base: Base ref (branch, tag, or commit SHA).
        head: Head ref (branch, tag, or commit SHA).
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the comparison result (status, ahead/behind
        counts, merge base, commits, and file changes), or an error payload
        when validation fails, the access token is missing, or the request
        fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if not base.strip() or not head.strip():
        await ctx.error("Both base and head are required.")
        return {"success": False, "error": "Both base and head are required."}

    headers = tokens["headers"]
    api_url = tokens["api_url"]

    try:
        response = requests.get(
            f"{api_url}/repos/{owner}/{repo}/compare/{base}...{head}",
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
            f"Failed to compare {base}...{head} in {owner}/{repo}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    data = response.json()

    await ctx.log(
        f"Compared {base}...{head} in {owner}/{repo}: "
        f"{data.get('status')} ({data.get('total_commits', 0)} commits)"
    )

    return {
        "success": True,
        "status": data.get("status"),
        "ahead_by": data.get("ahead_by"),
        "behind_by": data.get("behind_by"),
        "total_commits": data.get("total_commits"),
        "base_commit": (data.get("base_commit") or {}).get("sha"),
        "merge_base_commit": (data.get("merge_base_commit") or {}).get("sha"),
        "commits": [
            {
                "sha": commit["sha"],
                "message": commit["commit"]["message"],
                "author": (commit.get("commit", {}).get("author") or {}).get("name"),
                "date": (commit.get("commit", {}).get("author") or {}).get("date"),
                "url": commit["html_url"],
            }
            for commit in data.get("commits", [])
        ],
        "files": [
            {
                "filename": file["filename"],
                "status": file["status"],
                "additions": file["additions"],
                "deletions": file["deletions"],
                "changes": file["changes"],
                "patch": file.get("patch"),
            }
            for file in data.get("files", [])
        ],
        "url": data.get("html_url"),
    }