import os
import json
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import hashlib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube'
]

HISTORY_FILE = 'upload_history.json'
CLIENT_SECRETS_FILE = 'client_secrets.json'  # Download this from Google Cloud Console

# Get settings from environment variables
YOUTUBE_PLAYLIST_ID = os.getenv('YOUTUBE_PLAYLIST_ID')
YOUTUBE_PRIVACY_STATUS = os.getenv('YOUTUBE_PRIVACY_STATUS', 'private')
VIDEO_NAME_PREFIX = os.getenv('VIDEO_NAME_PREFIX', '[ASMR Erdaiju]')  # Default if not set

def get_authenticated_service():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    credentials = flow.run_local_server(port=0)
    return build('youtube', 'v3', credentials=credentials)

def generate_video_fingerprint(filepath, title, stream_date):
    """Generate a unique fingerprint for the video based on stream date and title"""
    content = f"{title}_{stream_date}".encode('utf-8')
    return hashlib.md5(content).hexdigest()

def parse_filename(filename):
    """Parse the filename to extract date, time, and title"""
    # Format: YYYY-MM-DD HH-MM-SS title.mp4
    date_time = filename[:19]
    title = filename[20:-4]  # Remove .mp4 extension
    
    dt = datetime.strptime(date_time, '%Y-%m-%d %H-%M-%S')
    return dt, title

def check_if_uploaded(youtube, fingerprint):
    """Check if video with given fingerprint exists in channel uploads"""
    try:
        # Get channel uploads
        request = youtube.search().list(
            part="snippet",
            maxResults=50,
            q=f"Fingerprint: {fingerprint}",
            type="video",
            forMine=True
        )
        response = request.execute()

        # Check if any video has our fingerprint in description
        for item in response.get('items', []):
            video_id = item['id']['videoId']
            video_response = youtube.videos().list(
                part="snippet",
                id=video_id
            ).execute()
            
            if video_response['items']:
                description = video_response['items'][0]['snippet']['description']
                if f"Fingerprint: {fingerprint}" in description:
                    return True, video_id
                    
        return False, None

    except HttpError as e:
        print(f"Error checking upload history: {e}")
        return False, None

def add_to_playlist(youtube, video_id, playlist_id):
    """Add video to specified playlist"""
    try:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
        ).execute()
        print(f"Added video {video_id} to playlist {playlist_id}")
    except HttpError as e:
        print(f"Error adding to playlist: {e}")

def upload_video(youtube, filepath, owner):
    filename = os.path.basename(filepath)
    stream_date, title = parse_filename(filename)
    
    # Generate video fingerprint
    fingerprint = generate_video_fingerprint(filepath, title, stream_date.strftime('%Y-%m-%d_%H-%M-%S'))
    
    # Check if already uploaded by searching YouTube
    already_uploaded, video_id = check_if_uploaded(youtube, fingerprint)
    if already_uploaded:
        print(f"Video already uploaded: {filename} (YouTube ID: {video_id})")
        return None
    
    # Create upload metadata with detailed description
    upload_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    body = {
        'snippet': {
            'title': f"{VIDEO_NAME_PREFIX} - {stream_date.strftime('%Y-%m-%d')}",
            'description': (
                f"Original Stream: {owner}\n"
                f"Stream Date: {stream_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Upload Date: {upload_time}\n"
                f"Filename: {filename}\n"
                f"Fingerprint: {fingerprint}\n"
            ),
            'tags': ['douyu', owner, 'stream', 'archive'],
            'categoryId': '22'
        },
        'status': {
            'privacyStatus': YOUTUBE_PRIVACY_STATUS,
            'selfDeclaredMadeForKids': False,
        }
    }

    try:
        # Create media file upload
        media = MediaFileUpload(filepath, 
                              chunksize=1024*1024, 
                              resumable=True,
                              mimetype='video/mp4')

        # Upload the video
        print(f"Starting upload: {filename}")
        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded {int(status.progress() * 100)}%")

        print(f"Upload Complete! Video ID: {response['id']}")

        # Add to playlist if playlist ID is configured
        if YOUTUBE_PLAYLIST_ID:
            add_to_playlist(youtube, response['id'], YOUTUBE_PLAYLIST_ID)

        return response['id']

    except HttpError as e:
        print(f"An HTTP error {e.resp.status} occurred: {e.content}")
        return None

def main():
    youtube = get_authenticated_service()
    base_dir = r'C:\Users\ngocp\Documents\Projects\youtube-reup\downloaded_streams'
    
    for owner in os.listdir(base_dir):
        owner_dir = os.path.join(base_dir, owner)
        if not os.path.isdir(owner_dir):
            continue
            
        print(f"\nProcessing streams for: {owner}")
        
        # Get all MP4 files in the owner's directory
        videos = [f for f in os.listdir(owner_dir) if f.endswith('.mp4')]
        videos.sort()  # Process oldest first
        
        for video in videos:
            video_path = os.path.join(owner_dir, video)
            print(f"\nProcessing: {video}")
            upload_video(youtube, video_path, owner)

if __name__ == '__main__':
    main() 