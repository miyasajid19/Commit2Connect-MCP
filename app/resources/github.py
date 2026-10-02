from fastmcp.resources import resource


@resource("data://github-profile", tags={"github", "identity"}, version="1.0")
def github_user_profile():
    return {
        "username": "miyasajid19",
        "name": "Sajid Miya",
        "title": "AI Engineer",
        "bio": "AI Engineer building agents, MCP servers, and applied LLM tooling.",
        "default_owner": "miyasajid19",
        "profile_url": "https://github.com/miyasajid19",
        "website": "https://sajidmiya.tech",
        "linkedin": "https://www.linkedin.com/in/sajidmiya",
        "email": "miyasajid19@gmail.com",
    }


@resource("data://github-defaults", tags={"github", "config"}, version="1.0")
def github_defaults():
    return {
        "owner": "miyasajid19",
        "default_branch": "main",
        "api_url": "https://api.github.com",
        "api_version": "2026-03-10",
    }