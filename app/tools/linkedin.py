import os
import requests
from dotenv import load_dotenv
from fastmcp.tools import tool
from fastmcp.dependencies import Depends
from fastmcp.server.dependencies import get_context
load_dotenv()

def LinkedInTokens()->dict:
    return {
        "access_token": os.getenv("LINKEDIN_ACCESS_TOKEN"),
        "version": os.getenv("LINKEDIN_API_VERSION", "202609"),
        "person_id":"HN5UaSrPTM"
    }

@tool
async def get_profile(tokens:dict=Depends(LinkedInTokens))->dict:
    '''
    Get the authenticated user's OpenID Connect profile information from LinkedIn.

    A successful response may include the user's subject identifier, email
    verification status, display name, given name, family name, locale, email
    address, and profile-picture URL. Typical response fields include ``sub``,
    ``email_verified``, ``name``, ``locale``, ``given_name``, ``family_name``,
    ``email``, and ``picture``.

    Response fields:
        ``sub``: LinkedIn's stable, unique identifier for the authenticated
            member (the OpenID Connect subject identifier).
        ``email_verified``: Whether LinkedIn has verified the member's email
            address.
        ``name``: The member's full display name.
        ``locale``: A dictionary containing the preferred ``language`` and
            ``country`` codes, such as ``en`` and ``US``.
        ``given_name``: The member's first or given name.
        ``family_name``: The member's last or family name.
        ``email``: The member's email address associated with the account.
        ``picture``: The URL of the member's profile picture, when available.

    Returns:
        dict: A dictionary containing the LinkedIn profile information. If the
            access token is missing or the request fails, returns a dictionary
            containing an ``error`` key with a description of the problem.
    '''
    access_token = tokens.get("access_token")
    ctx=get_context()
    if not access_token:
        await ctx.warning("LinkedIn access token is not set.")
        return {"error": "LinkedIn access token is not set."}
    
    response = requests.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            timeout=30,
        )
    
    try:
        response.raise_for_status()
        await ctx.info("Successfully fetched LinkedIn profile information.")
    except requests.RequestException as e:
        await ctx.error(f"Error occurred while fetching LinkedIn profile: {e}")
        return {"error": str(e)}

    return response.json()

