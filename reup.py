import os
from dotenv import load_dotenv
from src.youtube.api import YouTubeAPI
from src.video.downloader import VideoDownloader
from src.utils.logger import Logger

logger = Logger()

def extract_video_id(video_url: str) -> str:
    """Extract video ID from YouTube URL or return the ID if already an ID."""
    if not video_url:
        return None
        
    if len(video_url) == 11:  # Already a video ID
        return video_url
        
    # Try to find video ID in URL
    if 'youtu.be/' in video_url:
        return video_url.split('youtu.be/')[-1][:11]
    elif 'youtube.com/watch?v=' in video_url:
        return video_url.split('watch?v=')[-1][:11]
    else:
        return None

def process_video(video_url: str, youtube: YouTubeAPI, downloader: VideoDownloader) -> bool:
    """Process a single video for re-upload. Returns True if successful."""
    try:
        # Extract video ID
        video_id = extract_video_id(video_url)
        if not video_id:
            logger.log("Invalid YouTube URL format. Please enter a valid YouTube URL or video ID.")
            return False
            
        logger.log(f"Processing video ID: {video_id}")
        
        # Get video info
        logger.log("Fetching video information...")
        video_info = youtube.get_video_info(video_id)
        
        # Get upload settings
        privacy_status = os.getenv("REUP_PRIVACY", "private")
        video_prefix = os.getenv("REUP_PREFIX", "[Reup]").strip()
        video_tags = os.getenv("REUP_TAGS", "").split(",")
        video_tags = [tag.strip() for tag in video_tags if tag.strip()]
        reup_playlist_id = os.getenv("REUP_PLAYLIST_ID", "").strip()
        
        # Set video title
        upload_title = f"{video_prefix} {video_info['title']}"
        if len(upload_title) > 100:  # YouTube title length limit
            upload_title = upload_title[:97] + "..."
        
        # Download video
        logger.log("Downloading video...")
        video_path = downloader.download_video(video_id)
        if not video_path:
            logger.log("Failed to download video")
            return False
        
        logger.log("Download complete!")
        
        try:
            # Create description
            description = (
                f"Original video: https://youtu.be/{video_id}\n\n"
                "This is a re-upload of the original video."
            )
            
            # Upload video
            logger.log("\nStarting upload...")
            request = youtube.youtube.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": upload_title,
                        "description": description,
                        "tags": video_tags,
                        "categoryId": "22"  # People & Blogs
                    },
                    "status": {
                        "privacyStatus": privacy_status,
                        "selfDeclaredMadeForKids": False
                    }
                },
                media_body=video_path
            )
            
            response = request.execute()
            uploaded_video_id = response.get("id")
            
            if uploaded_video_id:
                logger.log(f"Upload complete! Video ID: {uploaded_video_id}")
                logger.log(f"Video URL: https://youtu.be/{uploaded_video_id}")
                
                # Add to reup playlist if configured
                if reup_playlist_id:
                    if youtube.add_to_playlist(uploaded_video_id, reup_playlist_id):
                        logger.log("Added video to reup playlist")
                    else:
                        logger.log("Failed to add video to playlist")
                
                return True
            else:
                logger.log("Upload failed - no video ID in response")
                return False
            
        finally:
            # Clean up downloaded video
            try:
                os.remove(video_path)
                logger.log("Cleaned up downloaded video")
            except Exception as e:
                logger.log(f"Failed to clean up video file: {e}")
    
    except Exception as e:
        logger.log(f"Error: {str(e)}")
        return False

def main():
    load_dotenv()
    
    # Initialize components
    logger.log("Initializing YouTube API...")
    youtube = YouTubeAPI(
        client_secrets_file="client_secrets.json",
        api_scopes=[
            "https://www.googleapis.com/auth/youtube.force-ssl",
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube.upload"
        ]
    )
    youtube.authenticate()
    
    downloader = VideoDownloader()
    
    logger.log("\nYouTube Re-upload Tool")
    logger.log("Enter 'exit' to quit the program")
    
    while True:
        logger.log("\nEnter YouTube URL or video ID (or 'exit' to quit):")
        video_url = input().strip()
        
        if video_url.lower() == 'exit':
            break
            
        if not video_url:
            continue
            
        success = process_video(video_url, youtube, downloader)
        if success:
            logger.log("\nVideo processed successfully!")
        else:
            logger.log("\nFailed to process video. Please try again.")
    
    logger.log("\nGoodbye!")

if __name__ == "__main__":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    main() 