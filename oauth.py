import os
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, urlparse, parse_qs

import requests
from dotenv import load_dotenv


def get_linkedin_oauth_token():
    load_dotenv()

    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    client_secret = os.getenv("LINKEDIN_PRIMARY_CLIENT_SECRET")

    redirect_uri = "http://localhost:8000/auth/linkedin/callback"

    if not client_id or not client_secret:
        raise RuntimeError(
            "LINKEDIN_CLIENT_ID or LINKEDIN_PRIMARY_CLIENT_SECRET is missing"
        )

    state = secrets.token_urlsafe(32)
    result = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)

            result["code"] = query.get("code", [None])[0]
            result["state"] = query.get("state", [None])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()

            self.wfile.write(
                b"<h2>LinkedIn authentication successful.</h2>"
                b"<p>You can close this browser window.</p>"
            )

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("localhost", 8000), CallbackHandler)

    auth_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": "openid profile email w_member_social",
    }

    authorization_url = (
        "https://www.linkedin.com/oauth/v2/authorization?"
        + urlencode(auth_params)
    )

    print("Opening LinkedIn authorization...")
    webbrowser.open(authorization_url)

    # Wait for LinkedIn callback
    server.handle_request()

    if result.get("state") != state:
        raise RuntimeError("Invalid OAuth state")

    code = result.get("code")

    if not code:
        raise RuntimeError("LinkedIn authorization failed")

    # Exchange authorization code for access token
    response = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )

    response.raise_for_status()

    token_data = response.json()

    return token_data["access_token"]

token = get_linkedin_oauth_token()

print("Access token:")
print(token)