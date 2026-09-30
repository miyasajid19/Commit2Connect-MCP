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
    }

@tool
async def get_profile(tokens:dict=Depends(LinkedInTokens))->dict:
    '''
    Get the profile information of the authenticated user from LinkedIn.
    Returns:
        dict: A dictionary containing the user's profile information or an error message.
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

