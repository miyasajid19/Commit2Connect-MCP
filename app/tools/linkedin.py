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

@tool
async def create_text_post(content:str, tokens:dict=Depends(LinkedInTokens))->dict:
    '''
    Create a new post on LinkedIn with only text content.

    Args:
        content (str): The content of the post to be created.
        tokens (dict): A dictionary containing the LinkedIn access token and API version.

    Returns:
        dict: A dictionary containing the response from the LinkedIn API. If the
            access token is missing or the request fails, returns a dictionary
            containing an ``error`` key with a description of the problem.
    '''
    access_token = tokens.get("access_token")
    version = tokens.get("version", "202609")
    person_id = tokens.get("person_id")

    ctx=get_context()
    if not access_token:
        await ctx.warning("LinkedIn access token is not set.")
        return {"error": "LinkedIn access token is not set."}
    
    response = requests.post(
        "https://api.linkedin.com/rest/posts",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Linkedin-Version": version,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        },
        json={
            "author": f"urn:li:person:{person_id}",
            "commentary": content,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        },
        timeout=30,
    )
    ctx.info(f"LinkedIn post creation response: {response.status_code} - {response.text}")
    
    response.raise_for_status()
    return {
        "status_code": response.status_code,
        "response": response.headers.get("x-restli-id"),
    }

def upload_image(image_path:str,headers:dict,author:str,access_token:str)->str:
    ctx=get_context()
    # Initialize image upload
    initialize_response = requests.post(
        "https://api.linkedin.com/rest/images?action=initializeUpload",
        headers={
            **headers,
            "Content-Type": "application/json",
        },
        json={
            "initializeUploadRequest": {
                "owner": author
            }
        },
        timeout=30,
    )

    initialize_response.raise_for_status()
    upload_data = initialize_response.json()["value"]
    image_urn = upload_data["image"]
    upload_url = upload_data["uploadUrl"]
    
    # Upload actual image bytes
    with open(image_path, "rb") as image_file:
        upload_response = requests.put(
            upload_url,
            headers={
                "Authorization": f"Bearer {access_token}"
            },
            data=image_file,
            timeout=60,
        )

    upload_response.raise_for_status()


    return image_urn


@tool
async def create_multi_image_post(
    content: str,
    image_paths:list[str],
):
    """Create a LinkedIn post containing multiple images.

    Args:
        content: The text commentary to publish with the images.
        image_paths: Local file paths for 2 to 20 images. Images are uploaded
            in the order provided.

    Returns:
        A dictionary containing the created post details, or an error message
        when the number of images is outside the supported range.
    """
    ctx=get_context()
    if len(image_paths) < 2:
        await ctx.warning("A multi-image post requires at least 2 images.")  
        return {"error": "A multi-image post requires at least 2 images."}

    if len(image_paths) > 20:
        await ctx.warning("A multi-image post supports at most 20 images.")
        return {"error": "A multi-image post supports at most 20 images."}
    access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    api_version = os.getenv("LINKEDIN_API_VERSION", "202609")
    if not access_token:
        raise RuntimeError("LINKEDIN_ACCESS_TOKEN is missing")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Linkedin-Version": api_version,
        "X-Restli-Protocol-Version": "2.0.0",
    }

    # ---------------------------------------------------------
    # 1. Get authenticated member ID
    # ---------------------------------------------------------

    profile_response = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        timeout=30,
    )

    profile_response.raise_for_status()

    member_id = profile_response.json()["sub"]
    author = f"urn:li:person:{member_id}"

    # ---------------------------------------------------------
    # 2. Upload all images
    # ---------------------------------------------------------

    image_urns = []

    for image_path in image_paths:

        image_urn = upload_image(image_path, headers, author, access_token)
        await ctx.info(f"Uploaded image {image_path} with URN: {image_urn}")
        image_urns.append(image_urn)

    # ---------------------------------------------------------
    # 3. Create multi-image post
    # ---------------------------------------------------------

    images = [
        {
            "id": image_urn,
        }
        for image_urn in image_urns
    ]

    post_payload = {
        "author": author,
        "commentary": content,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
        "content": {
            "multiImage": {
                "images": images
            }
        },
    }

    post_response = requests.post(
        "https://api.linkedin.com/rest/posts",
        headers={
            **headers,
            "Content-Type": "application/json",
        },
        json=post_payload,
        timeout=30,
    )

    post_response.raise_for_status()
    await ctx.info(f"Created multi-image post with ID: {post_response.headers.get('x-restli-id')}")
    return {
        "success": True,
        "post_id": post_response.headers.get("x-restli-id"),
        "images": image_urns,
    }
    
