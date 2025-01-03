from typing import Optional
import os
from dotenv import load_dotenv
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from datetime import datetime

class YouTubeUploader:
    """Handles uploading videos to YouTube."""
    
    def __init__(self, client_secrets_file: str):
        self.client_secrets_file = client_secrets_file
        self.youtube = None
        
        # Load environment variables
        load_dotenv()
        self.video_prefix = os.getenv("VIDEO_NAME_PREFIX", "[ASMR Clip]").strip()
        self.default_tags = [tag.strip() for tag in os.getenv("VIDEO_TAGS", "ASMR,relaxing").split(",")]
        
        # Required scopes for uploading videos
        self.scopes = [
            'https://www.googleapis.com/auth/youtube.upload',
            'https://www.googleapis.com/auth/youtube.force-ssl'
        ]
    
    def authenticate(self):
        """Authenticate with YouTube API."""
        print("Starting authentication for video upload...")
        flow = InstalledAppFlow.from_client_secrets_file(
            self.client_secrets_file, self.scopes
        )
        credentials = flow.run_local_server(port=0)
        print("Authentication successful!")
        
        self.youtube = build('youtube', 'v3', credentials=credentials)
    
    def get_content_title_from_filename(self, filename):
        """Extract the content title from filename (part after timestamps)"""
        # Skip date/time part for stream files
        if filename[:10].replace('-', '').isdigit():
            return None
        
        # For compilation files (format: videoId_timestamps_ContentTitle.mp4)
        parts = filename.split('_')
        if len(parts) < 4:  # Need at least videoId, start time, end time, and content
            return None
        
        # Join all parts after the timestamps, remove .mp4
        content_title = '_'.join(parts[3:]).replace('.mp4', '')
        return content_title

    def find_most_common_content(self, filenames):
        """Find the most common content title from a list of filenames"""
        content_titles = {}
        max_size = 0
        most_common_title = None

        for filename in filenames:
            content_title = self.get_content_title_from_filename(filename)
            if not content_title:
                continue
            
            # Get file size
            file_size = os.path.getsize(filename)
            
            if content_title not in content_titles:
                content_titles[content_title] = file_size
            else:
                content_titles[content_title] += file_size

            # Update most common based on total file size
            if content_titles[content_title] > max_size:
                max_size = content_titles[content_title]
                most_common_title = content_title

        return most_common_title

    def upload_video(
        self,
        file_path: str,
        title: str,
        description: str,
        privacy_status: str = "private",
        tags: Optional[list] = None
    ) -> Optional[str]:
        """Upload a video to YouTube.
        
        Args:
            file_path: Path to the video file
            title: Video title
            description: Video description
            privacy_status: private/unlisted/public
            tags: List of tags for the video
            
        Returns:
            Video ID if successful, None otherwise
        """
        if not self.youtube:
            print("YouTube API not authenticated. Call authenticate() first.")
            return None
        
        print(f"\nPreparing to upload: {title}")
        print(f"File: {file_path}")
        print(f"Privacy: {privacy_status}")
        
        try:
            # Format tags for description
            tags_str = ""
            if tags:
                tags_str = "\nTags: #" + " #".join(tag.replace(" ", "") for tag in tags if tag)
            
            # Add tags to description
            full_description = f"{description}\n{tags_str}"
            
            # Prepare video metadata
            body = {
                'snippet': {
                    'title': title,
                    'description': full_description,
                    'tags': tags or [],
                    'categoryId': '22'  # People & Blogs category
                },
                'status': {
                    'privacyStatus': privacy_status,
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # Prepare media file
            media = MediaFileUpload(
                file_path,
                mimetype='video/mp4',
                resumable=True,
                chunksize=1024*1024  # 1MB chunks
            )
            
            # Create upload request
            print("\nStarting upload...")
            request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Upload with progress tracking
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"Upload progress: {progress}%")
            
            video_id = response['id']
            print(f"\nUpload complete! Video ID: {video_id}")
            print(f"Video URL: https://youtu.be/{video_id}")
            return video_id
            
        except Exception as e:
            print(f"Error during upload: {str(e)}")
            return None
    
    def generate_video_details(self, original_video_id: str, segment_info: tuple) -> tuple:
        """Generate title and description for the uploaded clip."""
        start_time, end_time, description = segment_info
        
        # Format title with prefix
        title = f"{self.video_prefix} {description}"
        if len(title) > 100:  # YouTube title length limit
            title = title[:97] + "..."
        
        # Format description
        description_text = (
            f"{description}\n\n"
            f"Clip from original video: https://youtu.be/{original_video_id}\n"
            f"Time segment: {start_time}-{end_time}\n\n"
            "support anchor on douyu: douyu.com/5092355"
        )
        
        # Combine default tags with segment-specific tags
        segment_tags = [
            description.replace(" ", ""),  # Create hashtag from description
            f"ASMR{description.replace(' ', '')}"  # Create ASMR-prefixed hashtag
        ]
        
        # Combine and deduplicate tags
        all_tags = list(set(self.default_tags + segment_tags))
        
        return title, description_text, all_tags