from fastmcp.resources import resource


@resource("data://info", tags={"server", "documentation"}, version="1.0")
def server_info():
    return """
commit2connect-mcp
==================

A bridge between the places you **commit** code and the places you
**connect** with people: full GitHub repository management + full
LinkedIn posting, exposed as a single Model Context Protocol (MCP) server.

A Model Context Protocol (MCP) server built on FastMCP that exposes two
domain surfaces as MCP tools, prompts, and resources:

  1. LinkedIn posting — publish, edit, and delete posts on LinkedIn via
     the official Share on LinkedIn REST API (v202609).
  2. GitHub repository management — full CRUD over repositories, branches,
     commits, files, issues, and pull requests via the GitHub REST API
     (X-GitHub-Api-Version: 2026-03-10).

The server auto-discovers components from the `app/` directory tree:
    app/prompts/<domain>.py     -> MCP prompts
    app/resources/<domain>.py   -> MCP resources
    app/tools/<domain>.py       -> MCP tools
    app/tools/<domain>/*.py     -> MCP tools (per-domain subfolders)

LinkedIn Surface
----------------

Scopes requested at OAuth: openid, profile, email, w_member_social,
r_member_social.

Tools (10):
    get_profile
        Fetch the authenticated member's OIDC profile (sub, name, email,
        locale, picture).

    create_text_post(content)
        Publish a public text-only post on the main feed.

    create_image_post(file_path, commentary, alt_text)
        Upload a single image and attach it to a new post.

    create_multi_image_post(content, image_paths)
        Upload 2-20 images and attach them to a new post.

    create_video_post(file_path, commentary, title)
        Multi-part upload of a video, then publish as a post. Runs as a
        long-running task with 30s polling.

    create_document_post(file_path, content, title)
        Upload a PDF/document and publish as a new post. Runs as a task.

    create_article_post(source_url, commentary, title, description, thumbnail_path)
        Share an article / external link with optional thumbnail.

    create_poll(question, options, duration, commentary)
        Publish a poll post (question <=140 chars, 2-4 options, <=30 chars each).

    update_post(post_urn, new_text)
        Patch the commentary of an existing post.

    delete_post(post_urn)
        Delete an existing post.

Prompts:
    linkedin_prompt
        Generic helper for generating LinkedIn posts.

    linkedin_post_prompt(commentry)
        Structured system prompt with hooks, tone, hashtag, length rules.

GitHub Surface
--------------

Auth: a personal access token in env var GITHUB_PERSONAL_ACCESS_TOKEN.
Default owner: env var GITHUB_OWNER (defaults to "miyasajid19").

Tools (40, grouped by domain):

    Repositories (8)
        create_repository, get_repository, list_repositories,
        update_repository, delete_repository, search_repositories,
        search_code, search_users

    Branches (5)
        get_branch, get_branch_sha, create_branch, list_branches,
        delete_branch

    Commits (3)
        list_commits, get_commit, compare_commits

    Files (5)
        get_file, create_file, update_file, delete_file, push_files
        (push_files mirrors `git push` via the Git Data API: blobs ->
        tree -> commit -> fast-forward ref)

    Issues (8)
        create_issue, update_issue, close_issue, list_issues,
        reopen_issue, create_issue_comment, list_issue_comments,
        delete_issue_comment

    Pull Requests (14)
        create_pull_request, list_pull_requests, get_pull_request,
        update_pull_request, merge_pull_request, list_pull_request_files,
        get_pull_request_diff, list_pull_request_reviews,
        create_pull_request_review, update_pull_request_review,
        delete_pull_request_review, list_pull_request_comments,
        create_pull_request_comment, delete_pull_request_comment

Prompts:
    github_prompt
        Generic helper for any GitHub task.

    github_pr_review_prompt(diff)
        Generate a structured PR review (Blocking / Suggestions / Nits
        plus a verdict line).

    github_issue_response_prompt(issue_title, issue_body)
        Generate a maintainer-style reply to an issue with labels.

    github_commit_message_prompt(changes_summary)
        Generate a Conventional Commits message.

Resources
---------

    data://info
        This document.

    data://profile
        LinkedIn user identity card (name, title, github, website,
        linkedin, email).

    data://github-profile
        GitHub identity card (username, name, title, bio, profile URL,
        cross-links to LinkedIn and website).

    data://github-defaults
        Default owner, default branch, GitHub API base URL, API version.

Caching & Rate Limiting
-----------------------

The server installs:
    * ResponseCachingMiddleware
        - list_tools / list_prompts / list_resources: cached 30s.
        - 21 read-only / idempotent tools (get_*, list_*, search_*): cached 30s.
        - 6 prompts (LinkedIn + GitHub authoring helpers): cached 30s.
        - 3 resources (profile, github-profile, github-defaults): cached 30s.
        - All mutating tools (create_*, update_*, delete_*, merge_*,
          push_files, close_issue, reopen_issue) bypass the cache and
          always hit the live API.

    * RateLimitingMiddleware
        - 100 requests per 60-second window.

Tool Annotations
----------------

Every tool carries an MCP `ToolAnnotations` hint picked up by clients like
Claude and ChatGPT:

    readOnlyHint=True
        Reads data only; safe to call without confirmation.
        (get_*, list_*, search_*, compare_*)

    readOnlyHint=False
        Mutates external state; confirmation expected.
        (create_*, update_*, close_issue, reopen_issue, push_files)

    destructiveHint=True
        Operation cannot be undone (or only with loss).
        (delete_*, merge_pull_request)

    idempotentHint=True (paired with readOnlyHint=False)
        Calling twice with the same payload yields the same observable
        result. (update_*, reopen_issue, close_issue, update_pull_request,
        update_pull_request_review, update_repository)

Configuration
-------------

Environment variables (loaded from .env):

    LINKEDIN_CLIENT_ID
    LINKEDIN_PRIMARY_CLIENT_SECRET
    LINKEDIN_ACCESS_TOKEN
    LINKEDIN_REDIRECT_URI
    LINKEDIN_SCOPES
    LINKEDIN_API_BASE
    LINKEDIN_API_VERSION
    PORT
    SECRET_KEY
    GITHUB_PERSONAL_ACCESS_TOKEN
    GITHUB_OWNER

Run
---

    uv run main.py

The server binds to PORT (default 8000) over HTTP transport. The MCP
endpoint is exposed at /mcp.
"""