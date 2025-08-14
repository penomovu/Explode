import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# --- Configuration ---
# The file client_secrets.json needs to be downloaded from the Google API Console.
# Instructions:
# 1. Go to https://console.developers.google.com/
# 2. Create a new project.
# 3. Enable the "YouTube Data API v3".
# 4. Create credentials for an "OAuth client ID".
# 5. Select "Desktop app" as the application type.
# 6. Download the JSON file and rename it to "client_secrets.json".
# 7. Place "client_secrets.json" in the `tiktok_game/` directory.
CLIENT_SECRETS_FILE = "client_secrets.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# File to store the user's access and refresh tokens.
CREDENTIALS_PICKLE_FILE = 'token.pickle'

def get_authenticated_service():
    """Get an authenticated YouTube API service instance."""
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists(CREDENTIALS_PICKLE_FILE):
        creds = Credentials.from_authorized_user_file(CREDENTIALS_PICKLE_FILE, SCOPES)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                print(f"ERROR: Please download your client_secrets.json from the Google API Console and place it in the root directory.")
                return None
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(CREDENTIALS_PICKLE_FILE, 'w') as token:
            token.write(creds.to_json())

    try:
        return googleapiclient.discovery.build(
            API_SERVICE_NAME, API_VERSION, credentials=creds)
    except Exception as e:
        print(f"Failed to build YouTube service: {e}")
        return None

def upload_video(youtube, file, title, description, tags, category_id="22", privacy_status="private"):
    """
    Upload a video to YouTube.

    Args:
        youtube: An authenticated YouTube API service object.
        file (str): Path to the video file.
        title (str): The video title.
        description (str): The video description.
        tags (list): A list of tags for the video.
        category_id (str): The category ID for the video.
        privacy_status (str): "public", "private", or "unlisted".
    """
    if not os.path.exists(file):
        print(f"Video file not found: {file}")
        return None

    body=dict(
        snippet=dict(
            title=title,
            description=description,
            tags=tags,
            categoryId=category_id
        ),
        status=dict(
            privacyStatus=privacy_status
        )
    )

    try:
        print(f"Uploading video '{title}'...")
        from googleapiclient.http import MediaFileUpload
        media = MediaFileUpload(file, chunksize=-1, resumable=True)

        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}%.")

        print(f"Upload successful! Video ID: {response.get('id')}")
        return response.get('id')

    except googleapiclient.errors.HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
        return None
    except Exception as e:
        print(f"An error occurred during upload: {e}")
        return None

if __name__ == '__main__':
    # This is an example of how to use the uploader.
    # It will be called from the GUI.

    # First, get authenticated
    youtube_service = get_authenticated_service()
    if youtube_service:
        # Example video details - replace with a real video file
        if not os.path.exists("tiktok_game/output/final_video_0.mp4"):
            print("Could not find 'tiktok_game/output/final_video_0.mp4'.")
            print("Please generate a video first before running this example.")
        else:
            video_file = "tiktok_game/output/final_video_0.mp4"
            video_title = "My Test Video from Python"
            video_description = "This is a test video uploaded via the TikTok game script."
            video_tags = ["python", "youtube api", "automation", "pygame"]

            # Upload the video
            upload_video(youtube_service, video_file, video_title, video_description, video_tags)
