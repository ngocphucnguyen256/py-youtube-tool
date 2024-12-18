import os
from dotenv import load_dotenv
from src.youtube.api import YouTubeAPI
from src.video.downloader import VideoDownloader
from src.video.processor import VideoProcessor
from src.utils.comment_parser import CommentParser
from src.utils.file_manager import FileManager

def get_keywords_from_env() -> list:
    """Get and process keywords from .env file."""
    keywords = os.getenv("KEYWORDS", "").split(",")
    # Clean up keywords and convert to lowercase
    keywords = [k.strip().lower() for k in keywords if k.strip()]
    print(f"Using keywords for filtering: {', '.join(keywords)}")
    return keywords

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize components
    youtube = YouTubeAPI(
        client_secrets_file="client_secrets.json",
        api_scopes=["https://www.googleapis.com/auth/youtube.force-ssl"]
    )
    youtube.authenticate()
    
    file_manager = FileManager()
    downloader = VideoDownloader()
    processor = VideoProcessor()
    parser = CommentParser()
    
    # Get channel ID and allowed commenters from env
    channel_id = os.getenv("CHANNEL_ID")
    allowed_commenters = os.getenv("TIMESTAMP_COMMENTERS", "").split(",")
    allowed_commenters = [c.strip() for c in allowed_commenters]
    keywords = get_keywords_from_env()
    
    if not channel_id:
        print("Error: Please set CHANNEL_ID in .env file")
        return
    
    # Try to get videos directly with channel ID
    video_ids = youtube.get_channel_videos(channel_id.strip(), max_results=2)
    
    if not video_ids:
        print("\nNo videos found with channel ID, trying alternative methods...")
        # Try to get channel ID from username
        new_channel_id = youtube.get_channel_id_from_username("daidaiasmr")
        if new_channel_id:
            video_ids = youtube.get_channel_videos(new_channel_id, max_results=2)
        
        # If still no videos, try searching for the channel
        if not video_ids:
            print("\nTrying to search for the channel...")
            new_channel_id = youtube.search_channel("daidaiasmr")
            if new_channel_id:
                video_ids = youtube.get_channel_videos(new_channel_id, max_results=2)
    
    if not video_ids:
        print("\nFailed to fetch any videos. Please verify the channel ID/username and API permissions.")
        return
    
    all_clip_paths = []
    for video_id in video_ids:
        print(f"\nProcessing video {video_id}")
        
        try:
            # Check for existing files
            existing_video, existing_clips = file_manager.check_existing_files(video_id)
            
            if existing_clips:
                print("Using existing clips for this video")
                all_clip_paths.extend(existing_clips)
                continue
            
            # Get timestamps from comments
            comments = youtube.get_video_comments(video_id, allowed_commenters)
            timestamps = parser.extract_timestamps(comments)
            
            if not timestamps:
                print("No timestamps found in comments, skipping video")
                continue
            
            # Save timestamps
            video_dir = file_manager.create_video_folder(video_id)
            parser.save_timestamps(video_id, timestamps, video_dir)
            
            # Download video if not already downloaded
            video_path = existing_video if existing_video else downloader.download_video(video_id)
            if not video_path:
                print("Failed to download video, skipping...")
                continue
            
            # Find segments to clip
            segments = parser.find_continuous_segments(timestamps, keywords)
            
            # Process segments and create clips
            clip_paths = processor.process_segments(video_path, segments, video_id)
            all_clip_paths.extend(clip_paths)
            
            print(f"\nCreated {len(clip_paths)} clips from this video")
            
            # Clean up downloaded video if we downloaded it
            if not existing_video:
                file_manager.cleanup_video(video_path)
            
        except Exception as e:
            print(f"Error processing video {video_id}: {str(e)}")
            print("Skipping to next video...")
            continue
    
    # Create compilation from all clips
    if all_clip_paths:
        compilation_path = processor.merge_clips(all_clip_paths)
        if compilation_path:
            print(f"\nCompilation saved to: {compilation_path}")
    
    print(f"\nProcessing complete! Total clips created: {len(all_clip_paths)}")

if __name__ == "__main__":
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    main() 