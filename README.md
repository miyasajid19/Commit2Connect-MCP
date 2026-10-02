# commit2connect-mcp

> Bridge the places you **commit** code with the places you **connect** with people.

`commit2connect-mcp` is a single [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server built on [FastMCP](https://github.com/PrefectHQ/fastmcp) that exposes two complementary domains as MCP surfaces:

1. **GitHub repository management** — full CRUD over repositories, branches, commits, files, issues, and pull requests.
2. **LinkedIn posting** — publish, edit, and delete text, image, multi-image, video, document, article, and poll posts.

A client (CLI shell, LangChain agent, Claude Desktop, ChatGPT, etc.) connects to the server once and gets every tool, prompt, and resource from both surfaces — no separate integrations to maintain.

---

## Why

Most MCP servers cover one product. Working day-to-day as a developer on LinkedIn means *committing* code on GitHub and *connecting* with the professional network on LinkedIn — two tools, one workflow. `commit2connect-mcp` unifies them under one MCP server so an LLM agent can write code, push a branch, open a PR, merge it, and announce it on your feed without juggling multiple MCP installs.

---

## Features

- **~50 MCP tools** across both surfaces, each annotated with MCP `ToolAnnotations` (`readOnlyHint`, `destructiveHint`, `idempotentHint`) so clients can prompt for confirmation appropriately.
- **26 reusable prompts** — text/image/video/article/poll/document post authors on LinkedIn; PR review, issue response, commit-message, branch-name, and merge-message helpers on GitHub.
- **4 resources** for static context (server docstring, LinkedIn identity card, GitHub identity card, GitHub defaults).
- **Long-running task support** for video and multi-image uploads (`fastmcp-tasks`).
- **Response caching** for read-only operations (30s TTL) so agents don't blast the upstream APIs.
- **Rate limiting** to stay under LinkedIn / GitHub abuse thresholds.
- **Filesystem provider** auto-discovers every tool, prompt, and resource dropped into `app/`.

---

## Quick start

### Requirements

- Python **>= 3.11**
- [uv](https://docs.astral.sh/uv/) for dependency management

### Install

```bash
uv sync
```

### Configure

Copy the example env file and fill in real values:

```bash
cp .env.example .env
```

### Start

```bash
uv run main.py
```

The server binds to `http://localhost:8000` and exposes the MCP endpoint at `/mcp`.

---

## Configuration

All configuration is read from environment variables (loaded from `.env`):

| Variable    | Required for | Description |
| --- | --- | --- |
| `LINKEDIN_CLIENT_ID` | OAuth | LinkedIn app client ID. |
| `LINKEDIN_PRIMARY_CLIENT_SECRET` | OAuth | LinkedIn app client secret. |
| `LINKEDIN_ACCESS_TOKEN` | Posting | Bearer token used by posting tools (set after OAuth completes). |
| `LINKEDIN_REDIRECT_URI` | OAuth | Defaults to `http://localhost:8000/auth/linkedin/callback`. |
| `LINKEDIN_SCOPES` | OAuth | Space-separated OAuth scopes (default: `openid profile email w_member_social`). |
| `LINKEDIN_API_BASE` | Posting | Defaults to `https://api.linkedin.com`. |
| `LINKEDIN_API_VERSION` | Posting | Defaults to `202609`. |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub | Personal access token with `repo` scope. |
| `GITHUB_OWNER` | GitHub | Default repository owner. |
| `PORT` | Server | Defaults to `8000`. |
| `SECRET_KEY` | OAuth | Flask-style `itsdangerous` secret used to sign OAuth state. |

---

## LinkedIn OAuth setup

The `oauth.py` helper runs a one-shot OAuth Authorization Code flow against LinkedIn:

1. Reads `LINKEDIN_CLIENT_ID` and `LINKEDIN_PRIMARY_CLIENT_SECRET` from `.env`.
2. Spins up a local HTTP server on `localhost:8000` to receive the redirect.
3. Opens the user's browser to LinkedIn with the configured scopes and a CSRF-safe `state` token.
4. Exchanges the returned authorization code for an access token.
5. Prints the access token (which you can paste into `LINKEDIN_ACCESS_TOKEN` in `.env`).

Run it with:

```bash
python oauth.py
```

Required LinkedIn scopes for the posting tools: `w_member_social` (publish). The OIDC profile tools additionally need `openid`, `profile`, and `email`.

---

## Usage

### Option A — CLI client

`client.py` ships a tiny interactive REPL against the running server:

```bash
python client.py
```

Pick mode **`1`** for the CLI shell or **`2`** to spin up a LangChain agent backed by an OpenAI-compatible chat model.

In the CLI shell you can browse prompts, invoke tools, and read resources:

```
Enter your choice (1 for cli and 2 for LLm client): 1
Available tools: ['get_profile', 'create_text_post', ...]
enter index 0 - 53: 0
```

### Option B — any MCP-compatible host

Point Claude Desktop, ChatGPT, or any MCP-aware client at:

```
http://localhost:8000/mcp
```

The server will advertise every tool, prompt, and resource automatically.

---

## Tool versions

#### LinkedIn (10 tools)

| Tool | Description |
| --- | --- |
| `get_profile` | Fetch the authenticated member's OIDC profile. |
| `create_text_post` | Publish a public text-only post. |
| `create_image_post` | Upload one image and publish as a post. *(task)* |
| `create_multi_image_post` | Upload 2–20 images and publish as a post. *(task, 3s polling)* |
| `create_video_post` | Multi-part video upload, then publish. *(task, 30s polling)* |
| `create_document_post` | Upload a PDF/slides, then publish. *(task)* |
| `create_article_post` | Share an article / external URL with commentary. |
| `create_poll` | Publish a poll (≤140-char question, 2–4 options). |
| `update_post` | Patch the commentary of an existing post. |
| `delete_post` | Delete an existing post. |

#### GitHub (43 tools)

| Domain | Tools |
| --- | --- |
| **Repositories (8)** | `create_repository`, `get_repository`, `list_repositories`, `update_repository`, `delete_repository`, `search_repositories`, `search_code`, `search_users` |
| **Branches (5)** | `get_branch`, `get_branch_sha`, `create_branch`, `list_branches`, `delete_branch` |
| **Commits (3)** | `list_commits`, `get_commit`, `compare_commits` |
| **Files (5)** | `get_file`, `create_file`, `update_file`, `delete_file`, `push_files` *(atomic multi-file commit via Git Data API: blobs → tree → commit → fast-forward ref)* |
| **Issues (8)** | `create_issue`, `update_issue`, `close_issue`, `list_issues`, `reopen_issue`, `create_issue_comment`, `list_issue_comments`, `delete_issue_comment` |
| **Pull Requests (14)** | `create_pull_request`, `list_pull_requests`, `get_pull_request`, `update_pull_request`, `merge_pull_request`, `list_pull_request_files`, `get_pull_request_diff`, `list_pull_request_reviews`, `create_pull_request_review`, `update_pull_request_review`, `delete_pull_request_review`, `list_pull_request_comments`, `create_pull_request_comment`, `delete_pull_request_comment` |

---

## Prompts

#### LinkedIn (9)

- `linkedin_prompt` — generic post helper.
- `linkedin_post_prompt(commentry)` — structured system prompt with hooks, tone, hashtags.
- `linkedin_text_post_prompt(topic)` — text-only post.
- `linkedin_image_post_prompt(topic, image_description)` — single-image caption.
- `linkedin_multi_image_post_prompt(topic, image_descriptions)` — carousel caption.
- `linkedin_video_post_prompt(topic, video_description)` — native video caption.
- `linkedin_article_post_prompt(article_summary, commentary_intent)` — article / link commentary.
- `linkedin_poll_post_prompt(question_intent)` — poll JSON (`question`, `options`, `duration`, `commentary`).
- `linkedin_document_post_prompt(document_topic, document_description)` — document caption.

#### GitHub (17)

- `github_prompt` — generic GitHub helper.
- `github_pr_review_prompt(diff)` — Blocking / Suggestions / Nits + verdict.
- `github_issue_response_prompt(issue_title, issue_body)` — maintainer reply.
- `github_commit_message_prompt(changes_summary)` — Conventional Commits.
- `file_commit_message_prompt(file_path, action, content_summary)` — single-file commit.
- `push_files_commit_message_prompt(branch, file_summaries)` — atomic multi-file commit.
- `branch_name_prompt(intent, base_branch)` — conventional branch name.
- `issue_title_prompt(description)` — concise issue title.
- `issue_body_prompt(title, context)` — Markdown issue body.
- `issue_comment_prompt(issue_context, intent)` — maintainer comment.
- `pr_title_prompt(branch_name, change_summary)` — PR title.
- `pr_body_prompt(diff, commits_summary)` — Markdown PR body.
- `pr_review_body_prompt(review_points)` — review body grouped into Blocking / Suggestions / Nits.
- `pr_review_comment_prompt(code_snippet, concern)` — line-level review comment.
- `merge_commit_title_prompt(pr_title, pr_number)` — merge commit title.
- `merge_commit_message_prompt(pr_title, pr_number, pr_body)` — merge commit body.
- `repo_description_prompt(repo_name, summary)` — repository tagline (≤350 chars).

---

## Resources

| URI | Description |
| --- | --- |
| `data://info` | This server's documentation (auto-generated from the in-repo docstring). |
| `data://profile` | LinkedIn identity card (name, title, GitHub handle, website, email). |
| `data://github-profile` | GitHub identity card (username, name, bio, profile URL, cross-links). |
| `data://github-defaults` | Default GitHub owner, default branch, API base URL and version. |

---

## Architecture

```
commit2connect-mcp/
├── main.py                    # FastMCP server bootstrap + middleware wiring
├── oauth.py                   # Standalone LinkedIn OAuth helper
├── client.py                  # Interactive CLI + LangChain agent
├── pyproject.toml
├── uv.lock
├── .env                       # Local secrets (gitignored)
└── app/
    ├── prompts/
    │   ├── linkedin.py        # 9 LinkedIn prompts
    │   └── github.py          # 17 GitHub prompts
    ├── resources/
    │   ├── info.py            # data://info (server docstring)
    │   ├── linkedin.py        # data://profile
    │   └── github.py          # data://github-profile, data://github-defaults
    └── tools/
        ├── linkedin.py        # 10 LinkedIn tools
        └── github/
            ├── branches.py    #   5
            ├── commits.py     #   3
            ├── files.py       #   5  (incl. push_files)
            ├── issues.py      #   8
            ├── pull_request.py#  14
            └── repositories.py#  8
```

### Server bootstrap (`main.py`)

- **`FastMCP("commit2connect-mcp", providers=[FileSystemProvider(...)])`** — auto-discovers every `@tool`, `@prompt`, and `@resource` dropped into `app/`. `reload=True` watches the tree during development.
- **`CodeMode`** transform — collapses the entire MCP surface into a single code-execution tool. Disabled when long-running `@tool(task=...)` tools are present, because the sandbox can't poll them.
- **`ResourcesAsTools` / `PromptsAsTools`** — expose resources and prompts as tools so clients that don't natively support them can still use them.
- **`TasksExtension`** (`fastmcp-tasks`) — long-running task support for video and document uploads.
- **Middleware**:
  - `LoggingMiddleware`
  - `DetailedTimingMiddleware`
  - `ResponseCachingMiddleware` (30s TTL — see below)
  - `RateLimitingMiddleware`

### Adding a new tool, prompt, or resource

Drop a file into the right `app/` subfolder and decorate it:

```python
from fastmcp.tools import tool

@tool(tags={"github", "repositories", "read"}, version="1.0")
async def my_new_tool(repo: str) -> dict:
    """One-line summary of what the tool does."""
    ...
```

The `FileSystemProvider` will pick it up on next reload.

---

## Tool annotations

Every tool declares MCP `ToolAnnotations` so clients (Claude, ChatGPT, etc.) know how to handle them:

| Annotation | Meaning | Applied to |
| --- | --- | --- |
| `readOnlyHint=True` | Reads data only; safe to call without confirmation. | `get_*`, `list_*`, `search_*`, `compare_*` |
| `readOnlyHint=False` | Mutates external state; confirmation expected. | `create_*`, `close_issue`, `reopen_issue`, `push_files` |
| `destructiveHint=True` | Cannot be undone (or only with data loss). | `delete_*`, `merge_pull_request` |
| `idempotentHint=True` (paired with `readOnlyHint=False`) | Calling twice yields the same observable result. | `update_*`, `reopen_issue`, `close_issue` |

---

## Caching

`ResponseCachingMiddleware` is set to a 30-second TTL. It applies to:

- `list_tools` / `list_prompts` / `list_resources` — 30s.
- **21 read-only / idempotent tools** (`list_*`, `get_*`, `search_*`, `compare_*`) — 30s.
- **26 prompts** (every LinkedIn post-type prompt + the GitHub authoring helpers) — 30s.
- **4 resources** (`data://info`, `data://profile`, `data://github-profile`, `data://github-defaults`) — 30s.

Every mutating tool (`create_*`, `update_*`, `delete_*`, `merge_*`, `push_files`, `close_issue`, `reopen_issue`) bypasses the cache and always hits the live API.

## Rate limiting

`RateLimitingMiddleware` enforces:

- **10 requests per second** sustained
- **20 request burst capacity**

---

## Development

```bash
# Sync the environment
uv sync

# Run the server with auto-reload on file changes
uv run main.py

# Run the LinkedIn OAuth helper to mint a fresh access token
python oauth.py

# Drive the server interactively from a shell
python client.py            # pick option 1

# Or as a LangChain agent backed by an OpenAI-compatible model
MINIMAX_API_KEY=... MINIMAX_BASE_URL=... MINIMAX_MODEL=... python client.py   # pick option 2
```

### Project conventions

- All tools are async and follow a uniform `@tool + Depends(...) + try/except + structured error dict` pattern.
- Each tool declares `tags` and a `version="1.0"` for fast lookup and stable client-side binding.
- Mutating tools return `{"success": True, ...}` on success and `{"error": "..."}` on failure rather than raising — agents can dispatch on the shape directly.
- LinkedIn tools read credentials through a `Depends(LinkedInTokens)` injected dict, so swapping auth strategies is a one-line change.

---

## License

This project is private to its author.