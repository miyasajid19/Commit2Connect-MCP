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
        "api_url": "https://api.github.com",
        "headers": {
                "Authorization": f"Bearer {os.getenv('GITHUB_PERSONAL_ACCESS_TOKEN')}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2026-03-10",
            }
    }


@tool
async def get_file(repo: str,path: str,owner: str="miyasajid19",ref: str | None = None,tokens: dict = Depends(GitHubTokens)) -> dict:
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
    repo: str,
    path: str,
    content: str,
    message: str,
    owner: str="miyasajid19",
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
    repo: str,
    path: str,
    content: str,
    message: str,
    sha: str,
    owner: str="miyasajid19",
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
    repo: str,
    path: str,
    message: str,
    owner: str="miyasajid19",
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


@tool
async def push_files(
    repo: str,
    branch: str,
    files: list[dict],
    commit_message: str,
    owner: str="miyasajid19",
    author_name: str | None = None,
    author_email: str | None = None,
    tokens: dict = Depends(GitHubTokens),
) -> dict:
    """
    Push one or more local files to a GitHub branch in a single atomic commit.

    Mirrors what `git push` does under the hood, using the Git Data API:

        1. Resolve the current commit SHA at the tip of the branch.
        2. Read each local file and create a blob for its content.
        3. Build a new tree that points at those blobs.
        4. Create a commit on top of the current tip pointing at the new tree.
        5. Fast-forward the branch ref to the new commit.

    Args:
        owner: GitHub username or organization that owns the repository.
        repo: Repository name.
        branch: Target branch to push to (e.g. "main" or "feature/foo").
        files: List of file entries. Each entry is a dict with:

            - ``path`` (required): Path inside the repository (e.g.
              ``"src/foo.py"``).
            - ``local_path`` (optional): Absolute path on the local filesystem
              to read the file content from. Mutually exclusive with
              ``content``.
            - ``content`` (optional): Inline string content to push.
              Mutually exclusive with ``local_path``.

            Example::

                [
                    {"path": "src/foo.py", "local_path": "C:/work/foo.py"},
                    {"path": "README.md", "content": "# Hello"},
                ]

        commit_message: Commit message for the push.
        author_name: Optional git author name. Defaults to the authenticated
            GitHub user's name.
        author_email: Optional git author email. Defaults to the authenticated
            GitHub user's noreply email.
        tokens: Dependency-injected GitHub authentication settings.

    Returns:
        Dictionary containing the new commit SHA, list of pushed files, and
        a link to the commit on GitHub. Returns an error payload when
        validation fails, a local file cannot be read, or any Git Data API
        step fails.
    """

    ctx = get_context()
    access_token = tokens.get("access_token")

    if not access_token:
        await ctx.error("GITHUB_PERSONAL_ACCESS_TOKEN is missing")
        return {"success": False, "error": "GITHUB_PERSONAL_ACCESS_TOKEN is missing"}

    if not branch.strip():
        await ctx.error("Branch name cannot be empty.")
        return {"success": False, "error": "Branch name cannot be empty."}

    if not commit_message.strip():
        await ctx.error("Commit message cannot be empty.")
        return {"success": False, "error": "Commit message cannot be empty."}

    if not files:
        await ctx.error("At least one file must be provided to push.")
        return {"success": False, "error": "At least one file must be provided to push."}

    # Normalize and validate the file list up front so we fail fast on bad
    # input rather than mid-way through a multi-step push.
    normalized: list[dict] = []
    for index, entry in enumerate(files):
        if not isinstance(entry, dict):
            return {
                "success": False,
                "error": f"files[{index}] must be a dict, got {type(entry).__name__}.",
            }

        path = entry.get("path")
        local_path = entry.get("local_path")
        content = entry.get("content")

        if not path or not isinstance(path, str):
            return {
                "success": False,
                "error": f"files[{index}].path is required and must be a string.",
            }

        if local_path is not None and content is not None:
            return {
                "success": False,
                "error": (
                    f"files[{index}] cannot specify both local_path and content; "
                    "use exactly one."
                ),
            }

        if local_path is None and content is None:
            return {
                "success": False,
                "error": (
                    f"files[{index}] must specify either local_path or content."
                ),
            }

        # Read local content if needed, and validate that the file exists.
        if local_path is not None:
            if not os.path.isfile(local_path):
                return {
                    "success": False,
                    "error": f"files[{index}]: local file not found: {local_path}",
                }
            with open(local_path, "rb") as fh:
                raw = fh.read()
            normalized.append({
                "path": path,
                "content_bytes": raw,
            })
        else:
            if not isinstance(content, str):
                return {
                    "success": False,
                    "error": f"files[{index}].content must be a string.",
                }
            normalized.append({
                "path": path,
                "content_bytes": content.encode("utf-8"),
            })

    headers = tokens["headers"]
    api_url = tokens["api_url"]

    # ----------------------------------------------------------------
    # Step 1: resolve the current tip commit of the branch.
    # ----------------------------------------------------------------
    try:
        ref_response = requests.get(
            f"{api_url}/repos/{owner}/{repo}/git/ref/heads/{branch}",
            headers=headers,
            timeout=30,
        )
        ref_response.raise_for_status()
    except requests.RequestException as e:
        body = ""
        if e.response is not None:
            try:
                body = e.response.text
            except Exception:
                body = "<unreadable response body>"
        await ctx.error(
            f"Failed to resolve branch '{branch}' in {owner}/{repo}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "stage": "resolve_branch",
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    base_sha = ref_response.json()["object"]["sha"]

    # ----------------------------------------------------------------
    # Step 2: read its tree SHA so we can build on top of it.
    # ----------------------------------------------------------------
    try:
        commit_response = requests.get(
            f"{api_url}/repos/{owner}/{repo}/git/commits/{base_sha}",
            headers=headers,
            timeout=30,
        )
        commit_response.raise_for_status()
    except requests.RequestException as e:
        body = ""
        if e.response is not None:
            try:
                body = e.response.text
            except Exception:
                body = "<unreadable response body>"
        await ctx.error(
            f"Failed to read base commit {base_sha[:7]} for branch '{branch}' "
            f"in {owner}/{repo}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "stage": "read_base_commit",
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    base_tree_sha = commit_response.json()["tree"]["sha"]

    # ----------------------------------------------------------------
    # Step 3: create one blob per file.
    # ----------------------------------------------------------------
    tree_entries = []
    for entry in normalized:
        try:
            blob_response = requests.post(
                f"{api_url}/repos/{owner}/{repo}/git/blobs",
                headers=headers,
                json={
                    "content": base64.b64encode(entry["content_bytes"]).decode("utf-8"),
                    "encoding": "base64",
                },
                timeout=30,
            )
            blob_response.raise_for_status()
        except requests.RequestException as e:
            body = ""
            if e.response is not None:
                try:
                    body = e.response.text
                except Exception:
                    body = "<unreadable response body>"
            await ctx.error(
                f"Failed to create blob for '{entry['path']}' "
                f"in {owner}/{repo}: {e} | {body}"
            )
            return {
                "success": False,
                "error": str(e),
                "stage": "create_blob",
                "file": entry["path"],
                "status_code": e.response.status_code if e.response is not None else None,
                "github_response": body,
            }

        tree_entries.append({
            "path": entry["path"],
            "mode": "100644",
            "type": "blob",
            "sha": blob_response.json()["sha"],
        })

    # ----------------------------------------------------------------
    # Step 4: create a new tree on top of the base tree.
    # ----------------------------------------------------------------
    try:
        tree_response = requests.post(
            f"{api_url}/repos/{owner}/{repo}/git/trees",
            headers=headers,
            json={
                "base_tree": base_tree_sha,
                "tree": tree_entries,
            },
            timeout=60,
        )
        tree_response.raise_for_status()
    except requests.RequestException as e:
        body = ""
        if e.response is not None:
            try:
                body = e.response.text
            except Exception:
                body = "<unreadable response body>"
        await ctx.error(
            f"Failed to create tree in {owner}/{repo}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "stage": "create_tree",
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    new_tree_sha = tree_response.json()["sha"]

    # ----------------------------------------------------------------
    # Step 5: create a commit pointing at the new tree.
    # ----------------------------------------------------------------
    commit_payload: dict = {
        "message": commit_message,
        "tree": new_tree_sha,
        "parents": [base_sha],
    }

    if author_name or author_email:
        # Get the authenticated user so we have a sensible default.
        user_payload = None
        if not author_name or not author_email:
            try:
                user_resp = requests.get(
                    f"{api_url}/user",
                    headers=headers,
                    timeout=30,
                )
                user_resp.raise_for_status()
                user_payload = user_resp.json()
            except requests.RequestException:
                user_payload = None

        commit_payload["author"] = {
            "name": author_name or (user_payload or {}).get("name") or (user_payload or {}).get("login"),
            "email": (
                author_email
                or f"{(user_payload or {}).get('login', 'noreply')}@users.noreply.github.com"
            ),
        }

    try:
        new_commit_response = requests.post(
            f"{api_url}/repos/{owner}/{repo}/git/commits",
            headers=headers,
            json=commit_payload,
            timeout=30,
        )
        new_commit_response.raise_for_status()
    except requests.RequestException as e:
        body = ""
        if e.response is not None:
            try:
                body = e.response.text
            except Exception:
                body = "<unreadable response body>"
        await ctx.error(
            f"Failed to create commit in {owner}/{repo}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "stage": "create_commit",
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    new_commit_sha = new_commit_response.json()["sha"]

    # ----------------------------------------------------------------
    # Step 6: fast-forward the branch ref.
    # ----------------------------------------------------------------
    try:
        ref_update_response = requests.patch(
            f"{api_url}/repos/{owner}/{repo}/git/refs/heads/{branch}",
            headers=headers,
            json={"sha": new_commit_sha},
            timeout=30,
        )
        ref_update_response.raise_for_status()
    except requests.RequestException as e:
        body = ""
        if e.response is not None:
            try:
                body = e.response.text
            except Exception:
                body = "<unreadable response body>"
        await ctx.error(
            f"Failed to update branch '{branch}' in {owner}/{repo} "
            f"to {new_commit_sha[:7]}: {e} | {body}"
        )
        return {
            "success": False,
            "error": str(e),
            "stage": "update_ref",
            "commit_sha": new_commit_sha,
            "status_code": e.response.status_code if e.response is not None else None,
            "github_response": body,
        }

    await ctx.log(
        f"Pushed {len(normalized)} file(s) to {owner}/{repo}@{branch} "
        f"as commit {new_commit_sha[:7]}"
    )

    return {
        "success": True,
        "commit_sha": new_commit_sha,
        "branch": branch,
        "files": [entry["path"] for entry in normalized],
        "url": f"https://github.com/{owner}/{repo}/commit/{new_commit_sha}",
    }




