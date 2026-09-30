import os
import requests
from dotenv import load_dotenv
from fastmcp.tools import tool
from fastmcp.dependencies import Depends
from fastmcp.server.dependencies import get_context
from typing import Literal
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
    


@tool
# async def create_poll(question: str,options: list[str],duration: Literal["ONE_DAY", "THREE_DAYS", "SEVEN_DAYS", "FOURTEEN_DAYS"]="THREE_DAYS",commentary: str = "", tokens:dict=Depends(LinkedInTokens))->dict:
async def create_poll(question: str,options: list[str],duration: Literal["ONE_DAY", "THREE_DAYS", "SEVEN_DAYS", "FOURTEEN_DAYS"]="THREE_DAYS",commentary: str = "", tokens:dict=Depends(LinkedInTokens))->dict:
    """
    Create a LinkedIn poll post for the authenticated member.

    This tool validates the poll configuration, fetches the authenticated
    member's LinkedIn person URN from the OpenID Connect profile endpoint, and
    publishes a poll to the LinkedIn REST Posts API with the supplied question,
    options, duration, and optional commentary.

    LinkedIn poll constraints enforced here:
        - Question length must be 140 characters or fewer.
        - Poll must include between 2 and 4 options.
        - Each option text must be 30 characters or fewer.
        - The poll duration must be one of the supported LinkedIn values:
          "ONE_DAY", "THREE_DAYS", "SEVEN_DAYS", or "FOURTEEN_DAYS".

    Args:
        question (str): The poll question to display to viewers. Must be 140
            characters or fewer.
        options (list[str]): A list of poll answer choices. Must contain 2 to 4
            values, and each value must be 30 characters or fewer.
        duration (Literal[...], optional): How long the poll should remain open.
            Defaults to "THREE_DAYS".
        commentary (str, optional): Optional text to accompany the poll post.
            This is the post body text shown alongside the poll.
        tokens (dict, optional): Dependency-injected LinkedIn authentication
            settings. Expected to contain an ``access_token`` and optional
            ``version`` values.

    Returns:
        dict: A dictionary containing:
            - ``success``: True if the poll was published successfully.
            - ``post_urn``: The LinkedIn REST post ID / URN returned by the API.
            - ``question``: The original poll question.
            - ``options``: The original list of answer choices.
            - ``duration``: The selected poll duration.

        If validation fails or the access token is missing, the function returns
        a dictionary with an ``error`` key describing the problem.

    Notes:
        - The function calls ``https://api.linkedin.com/v2/userinfo`` to resolve
          the authenticated member ID.
        - The poll is published to ``https://api.linkedin.com/rest/posts`` using
          the owner's person URN and LinkedIn's required POST payload schema.
        - Any HTTP errors raised by LinkedIn are surfaced via
          ``response.raise_for_status()``.
    """
    ctx=get_context()
    access_token = tokens.get("access_token")
    api_version = tokens.get("version", "202609")
    
    if not access_token:
        await ctx.warning("LinkedIn access token is not set.")
        return {"error": "LinkedIn access token is not set."}
    
    if not api_version:
        await ctx.warning("LinkedIn API version is not set.")
        return {"error": "LinkedIn API version is not set."}
    
    if len(options) < 2 or len(options) > 4:
        await ctx.warning("Poll must have between 2 and 4 options.")
        return {"error": "Poll must have between 2 and 4 options."}
    
    for option in options:
        if len(option) > 30:
            await ctx.warning("Each poll option must be 30 characters or fewer.")
            return {"error": "Each poll option must be 30 characters or fewer."}
        
    if len(question) > 140:
        await ctx.warning("Poll question must be 140 characters or fewer.")
        return {"error": "Poll question must be 140 characters or fewer."}
    
    
    person_id = tokens.get("person_id") 
    author = f"urn:li:person:{person_id}"

    payload = {
        "author": author,
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
        "content": {
            "poll": {
                "question": question,
                "options": [
                    {"text": option}
                    for option in options
                ],
                "settings": {
                    "duration": duration,
                    "voteSelectionType": "SINGLE_VOTE",
                    "isVoterVisibleToAuthor": True,
                },
            }
        },
    }

    response = requests.post(
        "https://api.linkedin.com/rest/posts",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Linkedin-Version": api_version,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )

    await ctx.info(f"LinkedIn poll creation response: {response.status_code} - {response.text}")
    response.raise_for_status()

    return {
        "success": True,
        "post_urn": response.headers.get("x-restli-id"),
        "question": question,
        "options": options,
        "duration": duration,
    }
    



def upload_document(file_path:str,headers:dict,author:str,access_token:str)->str:
    init_payload = {
        "initializeUploadRequest": {
            "owner": author
        }
    }

    init_response = requests.post(
        "https://api.linkedin.com/rest/documents?action=initializeUpload",
        headers=headers,
        json=init_payload,
        timeout=30,
    )
    init_response.raise_for_status()

    init_data = init_response.json()
    upload_url = init_data["value"]["uploadUrl"]
    document_urn = init_data["value"]["document"]

    with open(file_path, "rb") as file:
        upload_response = requests.put(
            upload_url,
            headers={"Authorization": f"Bearer {access_token}"},
            data=file,
            timeout=120,
        )
    upload_response.raise_for_status()

    return document_urn

@tool
async def create_document_post(file_path:str, content:str, title:str="Document",tokens:dict=Depends(LinkedInTokens))->dict:
    ctx=get_context()
    access_token=tokens.get("access_token")
    api_version=tokens.get("version","202609")
    person_id=tokens.get("person_id")
    author=f"urn:li:person:{person_id}"
    if not access_token:
        await ctx.warning("LinkedIn access token is not set.")
        return {"error": "LinkedIn access token is not set."}
    
    if not api_version:
        await ctx.warning("LinkedIn API version is not set.")
        return {"error": "LinkedIn API version is not set."}
    
    if not os.path.isfile(file_path):
        await ctx.warning(f"File not found: {file_path}")
        return {"error": f"File not found: {file_path}"}
    
    headers = {
            "Authorization": f"Bearer {access_token}",
            "Linkedin-Version": api_version,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }
    
    # ---------------------------------------------------------
    # 2. Initialize document upload and upload document bytes
    # ---------------------------------------------------------

    document_urn = upload_document(file_path, headers, author, access_token)

    # ---------------------------------------------------------
    # 4. Create LinkedIn document post
    # ---------------------------------------------------------

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
            "media": {
                "title": title,
                "id": document_urn,
            }
        },
    }

    post_response = requests.post(
        "https://api.linkedin.com/rest/posts",
        headers=headers,
        json=post_payload,
        timeout=30,
    )

    ctx.info(f"LinkedIn document post creation response: {post_response.status_code} - {post_response.text}")
    
    post_response.raise_for_status()

    return {
        "success": True,
        "post_urn": post_response.headers.get("x-restli-id"),
        "document_urn": document_urn,
    }