import os
from dotenv import load_dotenv
from src.youtube.api import YouTubeAPI
from src.youtube.uploader import YouTubeUploader
from src.video.downloader import VideoDownloader
from src.video.processor import VideoProcessor
from src.utils.comment_parser import CommentParser
from src.utils.file_manager import FileManager
from src.utils.db_manager import DatabaseManager
from src.utils.upload_scheduler import UploadScheduler
import threading
import time
import signal
import sys

class GracefulShutdown:
    def __init__(self):
        self.shutdown = False
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signum, frame):
        print("\nShutdown requested...")
        self.shutdown = True

def get_keywords_from_env() -> list:
    """Get and process keywords from .env file."""
    keywords = os.getenv("KEYWORDS", "").split(",")
    # Clean up keywords and convert to lowercase
    keywords = [k.strip().lower() for k in keywords if k.strip()]
    print(f"Using keywords for filtering: {', '.join(keywords)}")
    return keywords

def process_and_upload_video(video_id: str, youtube, uploader, file_manager, downloader, 
                           processor, parser, db_manager, allowed_commenters, keywords):
    """Process a single video and upload immediately if successful"""
    try:
        # Check for existing files
        existing_video, existing_clips = file_manager.check_existing_files(video_id)
        
        # Get timestamps from comments
        comments = youtube.get_video_comments(video_id, allowed_commenters)
        timestamps = parser.extract_timestamps(comments)
        
        if not timestamps:
            print("No timestamps found in comments, skipping video")
            return
        
        # Save timestamps
        video_dir = file_manager.create_video_folder(video_id)
        parser.save_timestamps(video_id, timestamps, video_dir)
        
        # Download video if not already downloaded
        video_path = existing_video if existing_video else downloader.download_video(video_id)
        if not video_path:
            print("Failed to download video, skipping...")
            return
        
        # Find segments to clip
        segments = parser.find_continuous_segments(timestamps, keywords)
        
        # Process segments and create clips
        clip_paths, compilation_path = processor.process_segments(video_path, segments, video_id)
        
        if compilation_path:
            print(f"\nCreated compilation from {len(clip_paths)} clips")
            try:
                video_info = youtube.get_video_info(video_id)
            except Exception as e:
                print(f"Error getting video info: {e}")
                video_info = {'title': f'Video_{video_id}'}
            
            # Upload immediately
            if uploader.upload_video(video_id, video_info['title'], compilation_path):
                print("Upload completed successfully")
            else:
                print("Upload failed, will try again later")
            
            # Clean up individual clips
            for clip_path in clip_paths:
                try:
                    os.remove(clip_path)
                    print(f"Cleaned up clip: {os.path.basename(clip_path)}")
                except Exception as e:
                    print(f"Failed to remove clip {clip_path}: {e}")
        
        # Clean up downloaded video if we downloaded it
        if not existing_video:
            file_manager.cleanup_video(video_path)
        
    except Exception as e:
        print(f"Error processing video {video_id}: {str(e)}")

def get_min_schedule_gap(upload_times_str: str) -> int:
    """Calculate minimum gap between scheduled uploads in minutes"""
    try:
        # Parse upload times
        times = []
        for time_str in upload_times_str.split(','):
            hour, minute = map(int, time_str.strip().split(':'))
            times.append(hour * 60 + minute)  # Convert to minutes
        
        # Sort times
        times.sort()
        
        # Find minimum gap
        min_gap = 24 * 60  # Start with 24 hours in minutes
        for i in range(len(times)):
            next_i = (i + 1) % len(times)
            gap = times[next_i] - times[i] if next_i > i else (times[next_i] + 24 * 60) - times[i]
            min_gap = min(min_gap, gap)
        
        return max(30, min_gap // 2)  # Return half the minimum gap, but at least 30 minutes
    except:
        return 30  # Default to 30 minutes if there's any error

def main():
    shutdown_handler = GracefulShutdown()
    
    print("Starting application...")
    load_dotenv()
    print("Environment variables loaded")
    
    # Initialize components
    print("\nInitializing components...")
    youtube = YouTubeAPI(
        client_secrets_file="client_secrets.json",
        api_scopes=[
            "https://www.googleapis.com/auth/youtube.force-ssl",
            "https://www.googleapis.com/auth/youtube.readonly",
            "https://www.googleapis.com/auth/youtube.upload"
        ]
    )
    youtube.authenticate()
    
    file_manager = FileManager()
    downloader = VideoDownloader()
    processor = VideoProcessor()
    parser = CommentParser()
    db_manager = DatabaseManager(db_path="data/processed_videos.db")
    print("All components initialized")
    
    # Get configuration from env
    channel_id = os.getenv("CHANNEL_ID")
    allowed_commenters = os.getenv("TIMESTAMP_COMMENTERS", "").split(",")
    allowed_commenters = [c.strip() for c in allowed_commenters]
    keywords = get_keywords_from_env()
    privacy_status = os.getenv("UPLOAD_PRIVACY", "private")
    
    if not channel_id:
        print("Error: Please set CHANNEL_ID in .env file")
        return
    
    # Start scheduler for download timing only
    scheduler = UploadScheduler(youtube, db_manager)
    
    print("\nStarting schedule monitoring...")
    print(f"Configured schedule times: {os.getenv('UPLOAD_TIMES', '10:00,18:00')}")
    
    # Main processing loop
    while not shutdown_handler.shutdown:
        try:
            # Clear line for status update
            print('\r' + ' ' * 100, end='')  # Clear previous line
            
            # Wait for next schedule time
            if scheduler.is_schedule_time():
                print("\nSchedule time reached, starting video processing...")
                # Get videos
                video_ids = youtube.get_channel_videos(channel_id.strip(), max_results=1)
                
                if video_ids:
                    for video_id in video_ids:
                        if video_id not in db_manager.get_processed_video_ids():
                            print(f"\nProcessing new video {video_id}")
                            process_and_upload_video(
                                video_id, youtube, scheduler, file_manager, 
                                downloader, processor, parser, db_manager, 
                                allowed_commenters, keywords
                            )
                else:
                    print("\nNo new videos found")
                    
                # After processing, wait a bit to avoid immediate recheck
                time.sleep(300)  # 5 minutes
                
            # Short wait between checks
            time.sleep(30)
                
        except Exception as e:
            print(f"\nError in main loop: {str(e)}")
            if not shutdown_handler.shutdown:
                print("Waiting 30 minutes before retrying...")
                time.sleep(1800)
    
    print("Shutting down gracefully...")
    # Cleanup code here

if __name__ == "__main__":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    main() 