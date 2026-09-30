import os
import requests
from dotenv import load_dotenv
from fastmcp.tools import tool
from fastmcp.dependencies import Depends
from fastmcp.server.dependencies import get_context
from typing import Literal
load_dotenv()


def api_headers():
    return 


def LinkedInTokens()->dict:
    return {
        "access_token": os.getenv("LINKEDIN_ACCESS_TOKEN"),
        "version": os.getenv("LINKEDIN_API_VERSION", "202609"),
        "person_id":"HN5UaSrPTM",
        "api_base": os.getenv("LINKEDIN_API_BASE", "https://api.linkedin.com"),
        "header":{
        "Authorization": f"Bearer {os.getenv('LINKEDIN_ACCESS_TOKEN')}",
        "Linkedin-Version": os.getenv("LINKEDIN_API_VERSION", "202609"),
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    
        }
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
        headers=tokens.get("header"),
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
    
    
def _initialize_video_upload(api_base, headers, author, file_size):
    response = requests.post(
        f"{api_base}/rest/videos?action=initializeUpload",
        headers=headers,
        json={"initializeUploadRequest": {
            "owner": author,
            "fileSizeBytes": file_size,
            "uploadCaptions": False,
            "uploadThumbnail": False,
        }},
        timeout=30,
    )
    response.raise_for_status()
    value = response.json()["value"]
    return value["video"], value.get("uploadToken", ""), value["uploadInstructions"]


def _upload_video_parts(file_path, file_size, instructions):
    part_ids = []
    with open(file_path, "rb") as video_file:
        for instruction in instructions:
            first = instruction["firstByte"]
            last = instruction["lastByte"]
            video_file.seek(first)
            response = requests.put(
                instruction["uploadUrl"],
                headers={
                    "Content-Type": "application/octet-stream",
                    "Content-Range": f"bytes {first}-{last}/{file_size}",
                },
                data=video_file.read(last - first + 1),
                timeout=300,
            )
            response.raise_for_status()
            etag = response.headers.get("ETag")
            if not etag:
                raise RuntimeError("LinkedIn did not return an ETag for an uploaded part")
            part_ids.append(etag.strip('"'))
    return part_ids


def _finalize_video_upload(api_base, headers, video_urn, upload_token, part_ids):
    response = requests.post(
        f"{api_base}/rest/videos?action=finalizeUpload",
        headers=headers,
        json={"finalizeUploadRequest": {
            "video": video_urn,
            "uploadToken": upload_token,
            "uploadedPartIds": part_ids,
        }},
        timeout=30,
    )
    response.raise_for_status()


def _create_video_post(api_base, headers, author, video_urn, commentary, title):
    response = requests.post(
        f"{api_base}/rest/posts",
        headers=headers,
        json={
            "author": author,
            "commentary": commentary,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {"media": {"title": title, "id": video_urn}},
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.headers.get("x-restli-id")


async def _upload_video_parts(ctx, file_path, instructions, file_size):
    uploaded_part_ids = []
    with open(file_path, "rb") as video_file:
        for index, instruction in enumerate(instructions, start=1):
            first_byte = instruction["firstByte"]
            last_byte = instruction["lastByte"]
            video_file.seek(first_byte)
            chunk = video_file.read(last_byte - first_byte + 1)

            await ctx.info(
                f"  Part {index}/{len(instructions)}: "
                f"{first_byte:,} - {last_byte:,}"
            )
            upload_response = requests.put(
                instruction["uploadUrl"],
                headers={
                    "Content-Type": "application/octet-stream",
                    "Content-Range": f"bytes {first_byte}-{last_byte}/{file_size}",
                },
                data=chunk,
                timeout=300,
            )
            if not upload_response.ok:
                await ctx.error("Status:", upload_response.status_code)
                await ctx.error("Response:", upload_response.text)
            upload_response.raise_for_status()

            etag = upload_response.headers.get("ETag")
            if not etag:
                await ctx.error(f"No ETag returned for part {index}")
                raise RuntimeError(f"No ETag returned for part {index}")
            etag = etag.strip('"')
            uploaded_part_ids.append(etag)
        await ctx.info(f"  Uploaded successfully (ETag: {etag})")
    return uploaded_part_ids


@tool
async def create_video_post(file_path:str,commentary:str="",title:str="Video",tokens:dict=Depends(LinkedInTokens))->dict:
    ctx=get_context()
    access_token=tokens.get("access_token")
    api_version=tokens.get("version","202609")
    person_id=tokens.get("person_id")
    author=f"urn:li:person:{person_id}"
    headers=tokens.get("header")
    api_base=tokens.get("api_base")
    if not access_token:
        await ctx.warning("LinkedIn access token is not set.")
        return {"error": "LinkedIn access token is not set."}
    
    if not api_version:
        await ctx.warning("LinkedIn API version is not set.")
        return {"error": "LinkedIn API version is not set."}
    
    if not os.path.isfile(file_path):
        await ctx.warning(f"File not found: {file_path}")
        return {"error": f"File not found: {file_path}"}
    
    file_size = os.path.getsize(file_path)
    await ctx.info(f"Video file size: {file_size/(1024*1024):.2f} MB")
    
    await ctx.info(f"[1/4] Uploading video file: {file_path}")
    video_urn, upload_token, instructions = _initialize_video_upload(
        api_base, headers, author, file_size
    )
    await ctx.info(f"Video upload initialized. Video URN: {video_urn}")

    await ctx.info("\n[2/4] Uploading video parts...")
    uploaded_part_ids = await _upload_video_parts(
        ctx, file_path, instructions, file_size
    )
    await ctx.info("All Parts Uploaded Successfully.")
    await ctx.info("\n[3/4] Finalizing video upload...")
    
    _finalize_video_upload(
        api_base, headers, video_urn, upload_token, uploaded_part_ids
    )
    await ctx.info("Video upload finalized successfully.")
    
    await ctx.info("\n[4/4] Creating LinkedIn video post...")
    
    
    post_urn = _create_video_post(
        api_base, headers, author, video_urn, commentary, title
    )

    await ctx.info(f"Video post created successfully. Post URN: {post_urn} with Video URN: {video_urn}")


    return {
        "success": True,
        "video_urn": video_urn,
        "post_urn": post_urn,
        "message": "Video post created successfully.",
    }


@tool
async def create_image_post(file_path: str,commentary: str = "",alt_text: str = "",tokens: dict = Depends(LinkedInTokens)) -> dict:
    """
    Upload an image to LinkedIn and publish it as a post.

    Parameters
    ----------
    file_path:
        Local path to JPG, PNG, or GIF image.

    commentary:
        Text accompanying the image.

    alt_text:
        Accessibility description for the image.
    """
    ctx=get_context()
    access_token = tokens.get("access_token")
    api_version = tokens.get("version","202609")
    person_id = tokens.get("person_id")
    author = f"urn:li:person:{person_id}"
    headers = tokens.get("header")
    api_base = tokens.get("api_base")
    
    if not access_token:
        await ctx.warning("LinkedIn access token is not set.")
        return {"error": "LinkedIn access token is not set."}
    if not api_version:
        await ctx.warning("LinkedIn API version is not set.")
        return {"error": "LinkedIn API version is not set."}
    if not os.path.isfile(file_path):
        await ctx.warning(f"File not found: {file_path}")
        return {"error": f"File not found: {file_path}"}
    file_size = os.path.getsize(file_path)
    if file_size<=0:
        await ctx.warning(f"File is empty: {file_path}")
        return {"error": f"File is empty: {file_path}"}
    await ctx.info(f"Image file size: {file_size/(1024*1024):.2f} MB")
    
    await ctx.info("\n[1/3] Uploading image...")
    image_urn = upload_image(file_path, headers, author, access_token)
    await ctx.info(f"Image uploaded successfully. Image URN: {image_urn}")

    # ========================================================
    # 5. Create LinkedIn post
    # ========================================================

    await ctx.info("[3/3] Creating LinkedIn post...")

    post_payload = {
        "author": author,
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "content": {
            "media": {
                "altText": alt_text,
                "id": image_urn,
            }
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    post_response = requests.post(
        f"{api_base}/rest/posts",
        headers=headers,
        json=post_payload,
        timeout=30, 
    )

    if not post_response.ok:
        await ctx.error(f"Post creation failed with status {post_response.status_code}: {post_response.text}")

    post_response.raise_for_status()

    post_urn = post_response.headers.get(
        "x-restli-id"
    )

    await ctx.info(f"LinkedIn post created successfully. Post URN: {post_urn} with Image URN: {image_urn}")

    await ctx.info(f"Post creation response: {post_response.status_code} - {post_response.text}")

    return {
        "success": True,
        "image_urn": image_urn,
        "post_urn": post_urn,
        "message": "Image post created successfully.",
    }
    
    
    
@tool
async def create_article_post(source_url: str,commentary: str,title: str,description: str = "",thumbnail_path: str | None = None,tokens: dict = Depends(LinkedInTokens)) -> dict:
    """
    Create a LinkedIn article/link post.

    Parameters
    ----------
    source_url:
        URL of the article/page being shared.

    commentary:
        Text shown above the article preview.

    title:
        Article preview title.

    description:
        Article preview description.

    thumbnail_path:
        Optional local path to an image file to use as the article thumbnail.
    """
    ctx=get_context()
    access_token = tokens.get("access_token")
    api_version = tokens.get("version", "202609")
    person_id = tokens.get("person_id")
    author = f"urn:li:person:{person_id}"
    headers = tokens.get("header")
    api_base = tokens.get("api_base")

    ctx.info("Creating LinkedIn article post...")

    if not access_token:
        ctx.warning("LinkedIn access token is not set.")
        return {"success": False, "message": "LinkedIn access token is not set."}
    if not api_version:
        ctx.warning("LinkedIn API version is not set.")
        return {"success": False, "message": "LinkedIn API version is not set."}
    
    article = {
        "title": title,
        "description": description,
        "source": source_url,
    }

    if thumbnail_path:
        if not os.path.isfile(thumbnail_path):
            ctx.warning(f"Thumbnail file not found: {thumbnail_path}")
            return {"success": False, "message": f"Thumbnail file not found: {thumbnail_path}"}
        image_urn = upload_image(thumbnail_path, headers, author, access_token)
        article["thumbnail"] = image_urn
        ctx.info(f"Thumbnail uploaded successfully. Image URN: {image_urn}")
        
    # --------------------------------------------------------
    # Build post
    # --------------------------------------------------------

    payload = {
        "author": author,
        "commentary": commentary,
        "visibility": "PUBLIC",

        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },

        "content": {
            "article": article
        },

        "lifecycleState": "PUBLISHED",

        "isReshareDisabledByAuthor": False,
    }

    # --------------------------------------------------------
    # Create post
    # --------------------------------------------------------

    await ctx.info("Creating article post...")

    response = requests.post(
        f"{api_base}/rest/posts",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if not response.ok:
        await ctx.error(f"Error creating article post: {response.status_code} - {response.text}")
    
    response.raise_for_status()

    post_urn = response.headers.get("x-restli-id")

    await ctx.info(f"Post URN: {post_urn}")

    return {
        "success": True,
        "post_urn": post_urn,
        "source_url": source_url,
        "message": "Article post created successfully.",
    }


@tool
async def update_post(post_urn: str, new_text: str, tokens: dict = Depends(LinkedInTokens)) -> dict:
    """
    Update the text of an existing LinkedIn post.

    Parameters
    ----------
    post_urn:
        The URN of the post to update (e.g., "urn:li:share:123456789").

    new_text:
        The new text content for the post.
    """
    ctx=get_context()
    access_token = tokens.get("access_token")
    api_version = tokens.get("version", "202609")
    headers = tokens.get("header")
    api_base = tokens.get("api_base")

    if not access_token:
        await ctx.warning("LinkedIn access token is not set.")
        return {"success": False, "message": "LinkedIn access token is not set."}
    
    if not api_version:
        await ctx.warning("LinkedIn API version is not set.")
        return {"success": False, "message": "LinkedIn API version is not set."}

    encoded_post_urn = requests.utils.quote(post_urn,safe="")
    
    url = (
        f"{api_base}/rest/posts/"
        f"{encoded_post_urn}"
    )
    payload = {
        "patch": {
            "$set": {
                "commentary": new_text
            }
        }
    }

    await ctx.info("UPDATING LINKEDIN POST")

    await ctx.info(f"Post: {post_urn}")
    await ctx.info(f"New text: {new_text}")

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=30,
    )

    if not response.ok:
        await ctx.error(f"UPDATE ERROR: Status: {response.status_code}, Response: {response.text}")
    response.raise_for_status()

    await ctx.info("Post updated successfully.")

    return {
        "success": True,
        "post_urn": post_urn,
        "status_code": response.status_code,
        "message": "Post updated successfully.",
    }
    


@tool
async def delete_post(post_urn: str,tokens: dict = Depends(LinkedInTokens)) -> dict:
    """
    Delete a LinkedIn post.

    Example:
        urn:li:share:123456789
        urn:li:ugcPost:123456789
    """
    ctx=get_context()
    access_token = tokens.get("access_token")
    api_version = tokens.get("version", "202609")
    headers = tokens.get("header")
    api_base = tokens.get("api_base")

    if not access_token:
        raise RuntimeError(
            "LINKEDIN_ACCESS_TOKEN is missing."
        )

    if not post_urn:
        raise ValueError(
            "post_urn is required."
        )

    # LinkedIn requires the URN to be URL encoded
    encoded_post_urn = requests.utils.quote(
        post_urn,
        safe=""
    )

    url = (
        f"{api_base}/rest/posts/"
        f"{encoded_post_urn}"
    )


    await ctx.info(f"Deleting LinkedIn post with URN: {post_urn}")
    response = requests.delete(
        url,
        headers=headers,
        timeout=30,
    )
    await ctx.info(f"DELETE REQUEST: {url}")

    if not response.ok:
        await ctx.error(f"DELETE ERROR: Status: {response.status_code}, Response: {response.text}")

    response.raise_for_status()

    await ctx.info(f"Post deleted successfully. Status: {response.status_code}")

    return {
        "success": True,
        "post_urn": post_urn,
        "status_code": response.status_code,
        "message": "Post deleted successfully.",
    }