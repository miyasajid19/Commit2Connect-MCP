from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers import FileSystemProvider
fromfrom fastmcp.experimental.transforms.code_mode import CodeMode
from fastmcp.server.transforms import ResourcesAsTools,PromptsAsTools
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.server.middleware.timing import DetailedTimingMiddleware
from fastmcp.server.middleware.caching import (
    ResponseCachingMiddleware,
    CallToolSettings,
    ListToolsSettings,
    ListResourcesSettings,
    ReadResourceSettings,
    ListPromptsSettings,
    GetPromptSettings,
)
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
from fastmcp_tasks import TasksExtension
# mcp = FastMCP("commit2connect-mcp", providers=[FileSystemProvider(Path(__file__).parent / "app",reload=True)],transforms=[CodeMode()])
mcp = FastMCP("commit2connect-mcp", providers=[FileSystemProvider(Path(__file__).parent / "app", reload=True)])

mcp.add_transform(ResourcesAsTools(mcp))
mcp.add_transform(PromptsAsTools(mcp))
mcp.add_middleware(LoggingMiddleware())
mcp.add_middleware(DetailedTimingMiddleware())
mcp.add_middleware(ResponseCachingMiddleware(
    list_tools_settings=ListToolsSettings(ttl=30),
    list_prompts_settings=ListPromptsSettings(ttl=30),
    list_resources_settings=ListResourcesSettings(ttl=30),
    call_tool_settings=CallToolSettings(ttl=30, included_tools=[
        # GitHub — read-only / idempotent tools
        "list_commits",
        "get_commit",
        "compare_commits",
        "get_branch",
        "get_branch_sha",
        "list_branches",
        "get_file",
        "list_issues",
        "list_issue_comments",
        "list_pull_requests",
        "get_pull_request",
        "list_pull_request_files",
        "get_pull_request_diff",
        "list_pull_request_reviews",
        "list_pull_request_comments",
        "get_repository",
        "list_repositories",
        "search_repositories",
        "search_code",
        "search_users",
        # LinkedIn — read-only
        "get_profile",
    ]),
    get_prompt_settings=GetPromptSettings(ttl=30, included_prompts=[
        "linkedin_prompt",
        "linkedin_post_prompt",
        "linkedin_text_post_prompt",
        "linkedin_image_post_prompt",
        "linkedin_multi_image_post_prompt",
        "linkedin_video_post_prompt",
        "linkedin_article_post_prompt",
        "linkedin_poll_prompt",
        "linkedin_document_post_prompt",
        "github_prompt",
        "github_pr_review_prompt",
        "github_issue_response_prompt",
        "github_commit_message_prompt",
        "file_commit_message_prompt",
        "push_files_commit_message_prompt",
        "branch_name_prompt",
        "issue_title_prompt",
        "issue_body_prompt",
        "issue_comment_prompt",
        "pr_title_prompt",
        "pr_body_prompt",
        "pr_review_body_prompt",
        "pr_review_comment_prompt",
        "merge_commit_title_prompt",
        "merge_commit_message_prompt",
        "repo_description_prompt",
    ]),
    read_resource_settings=ReadResourceSettings(ttl=30, included_resources=[
        "data://info",
        "data://profile",
        "data://github-profile",
        "data://github-defaults",
    ]),
))
mcp.add_middleware(RateLimitingMiddleware(
    max_requests_per_second=10,
    burst_capacity=20,
))
if __name__ == "__main__":
    mcp.run(transport="http")