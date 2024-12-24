import os
from dotenv import load_dotenv
from src.youtube.api import YouTubeAPI
from src.youtube.uploader import YouTubeUploader
from src.video.downloader import VideoDownloader
from src.video.processor import VideoProcessor
from src.utils.comment_parser import CommentParser
from src.utils.file_manager import FileManager
from src.utils.upload_scheduler import UploadScheduler
import threading
import time
import signal
import sys
from datetime import datetime, timedelta
import argparse
from typing import List
import glob

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

def get_next_schedule_time(upload_times_str: str) -> str:
    """Get the next scheduled upload time."""
    try:
        current_time = datetime.now()
        times = []
        for time_str in upload_times_str.split(','):
            hour, minute = map(int, time_str.strip().split(':'))
            schedule_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If this time is already past for today, schedule it for tomorrow
            if schedule_time <= current_time:
                schedule_time += timedelta(days=1)
            
            times.append(schedule_time)
        
        # Get the next closest time
        next_time = min(times)
        time_diff = next_time - current_time
        
        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        
        return f"Next upload scheduled in {hours}h {minutes}m (at {next_time.strftime('%H:%M')})"
    except:
        return "Schedule time calculation error"

def process_and_upload_video(video_id: str, youtube, scheduler, file_manager, downloader, 
                           processor, parser, allowed_commenters, keywords, exclude_keywords):
    """Process a single video and upload immediately if successful"""
    try:
        print("\nChecking video status...")
        
        # Check YouTube for existing upload first
        print("\nChecking if video was already processed...")
        if youtube.check_if_uploaded(video_id):
            print(f"\nVideo {video_id} was already processed, skipping...")
            return
        
        # Get video info
        print("\nFetching video information...")
        try:
            video_info = youtube.get_video_info(video_id)
            print(f"Video title: {video_info['title']}")
        except Exception as e:
            print(f"Error getting video info: {e}")
            video_info = {'title': f'Video_{video_id}'}

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
        segments = parser.find_continuous_segments(timestamps, keywords, exclude_keywords)
        
        if not segments:
            print("No segments found after filtering with keywords and exclusions")
            return
        
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
            if scheduler.upload_video(video_id, video_info['title'], compilation_path):
                print("Upload completed successfully")
                # Show next schedule time
                next_schedule = get_next_schedule_time(os.getenv('UPLOAD_TIMES', '10:00,18:00'))
                print(f"\n{next_schedule}")
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

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='YouTube video processor and uploader')
    parser.add_argument('-i', '--immediate', 
                       action='store_true',
                       help='Process one video immediately then wait for next schedule')
    parser.add_argument('--channel',
                       action='store_true',
                       help='Fetch videos from channel instead of playlist')
    return parser.parse_args()

def reload_env_variables():
    """Reload environment variables from .env file."""
    try:
        load_dotenv(override=True)
        print("\nReloaded environment variables")
        
        # Get and display current settings
        print("\nCurrent settings:")
        print(f"Channel ID: {os.getenv('CHANNEL_ID')}")
        print(f"Upload Privacy: {os.getenv('UPLOAD_PRIVACY', 'private')}")
        print(f"Schedule Times: {os.getenv('UPLOAD_TIMES', '10:00,18:00')}")
        print(f"Video Name Prefix: {os.getenv('VIDEO_NAME_PREFIX', '[ASMR]')}")
        
        keywords = get_keywords_from_env()
        exclude_keywords = [k.strip() for k in os.getenv("KEYWORDS_EXCLUDE", "").split(",") if k.strip()]
        print(f"Exclude Keywords: {', '.join(exclude_keywords)}")
        
        return True
    except Exception as e:
        print(f"\nError reloading environment variables: {e}")
        return False

def process_batch_of_videos(video_ids: List[str], start_index: int, youtube, scheduler, file_manager, 
                          downloader, processor, parser, allowed_commenters, 
                          keywords, exclude_keywords, shutdown_handler) -> bool:
    """Process a batch of videos and return True if any video was processed."""
    # Reload environment variables before processing
    reload_env_variables()
    
    processed_count = 0
    if video_ids:
        print(f"\nChecking videos {start_index+1} to {start_index+len(video_ids)}...")
        for video_id in video_ids:
            if shutdown_handler.shutdown:
                return False
                
            print(f"\nProcessing video {video_id}")
            process_and_upload_video(
                video_id, youtube, scheduler, file_manager, 
                downloader, processor, parser, allowed_commenters, 
                keywords, exclude_keywords
            )
            processed_count += 1
            return True  # Found and processed one video
    
    return False  # No videos were processed in this batch

def validate_env_variables():
    """Validate required environment variables."""
    required_vars = {
        "CHANNEL_ID": "Channel ID or username to process",
        "TIMESTAMP_COMMENTERS": "List of users who post timestamps",
        "KEYWORDS": "Keywords to look for in timestamps",
        "UPLOAD_TIMES": "Schedule times for processing",
        "UPLOAD_PRIVACY": "Privacy setting for uploaded videos",
        "VIDEO_NAME_PREFIX": "Prefix for uploaded video titles",
        "VIDEO_TAGS": "Default tags for uploaded videos"
    }
    
    missing = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing.append(f"{var} ({description})")
    
    if missing:
        print("\nError: Missing required environment variables:")
        for var in missing:
            print(f"- {var}")
        return False
    
    return True

def cleanup_temp_files():
    """Clean up temporary files and directories."""
    temp_patterns = [
        "temp_concat_*.txt",
        "temp-audio.m4a",
        "*.temp.*"
    ]
    
    print("\nCleaning up temporary files...")
    for pattern in temp_patterns:
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
                print(f"Removed: {file_path}")
            except Exception as e:
                print(f"Failed to remove {file_path}: {e}")

def main():
    args = parse_args()
    shutdown_handler = GracefulShutdown()
    
    print("Starting application...")
    load_dotenv()
    print("Environment variables loaded")
    
    # Validate environment variables
    if not validate_env_variables():
        print("\nPlease set all required variables in .env file")
        return
    
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
    print("All components initialized")
    
    # Get configuration from env
    channel_id = os.getenv("CHANNEL_ID")
    playlist_id = os.getenv("PLAYLIST_ID")
    allowed_commenters = os.getenv("TIMESTAMP_COMMENTERS", "").split(",")
    allowed_commenters = [c.strip() for c in allowed_commenters]
    keywords = get_keywords_from_env()
    exclude_keywords = os.getenv("KEYWORDS_EXCLUDE", "").split(",")
    exclude_keywords = [k.strip() for k in exclude_keywords if k.strip()]
    privacy_status = os.getenv("UPLOAD_PRIVACY", "private")
    
    if args.channel and not channel_id:
        print("Error: Please set CHANNEL_ID in .env file when using --channel flag")
        return
    elif not args.channel and not playlist_id:
        print("Error: Please set PLAYLIST_ID in .env file")
        return
    
    # Start scheduler for download timing only
    scheduler = UploadScheduler(youtube)
    
    print("\nStarting schedule monitoring...")
    print(f"Configured schedule times: {os.getenv('UPLOAD_TIMES', '10:00,18:00')}")
    
    # Show initial next schedule time
    next_schedule = get_next_schedule_time(os.getenv('UPLOAD_TIMES', '10:00,18:00'))
    print(f"\n{next_schedule}")
    
    # Main processing loop
    try:
        if args.immediate:
            print("\nImmediate mode: Processing one video now...")
            batch_size = 50
            start_index = 0
            found_unprocessed = False
            
            while not found_unprocessed and not shutdown_handler.shutdown:
                print(f"\nFetching videos {start_index+1} to {start_index+batch_size}...")
                if args.channel:
                    video_ids = youtube.get_channel_videos(
                        channel_id.strip(), 
                        max_results=batch_size,
                        start_index=start_index
                    )
                else:
                    video_ids = youtube.get_playlist_videos(
                        playlist_id.strip(),
                        max_results=batch_size,
                        start_index=start_index
                    )
                
                if not video_ids:
                    print("\nNo more videos found")
                    break
                    
                print(f"\nFound {len(video_ids)} videos, checking for unprocessed ones...")
                found_unprocessed = process_batch_of_videos(
                    video_ids, start_index, youtube, scheduler, file_manager,
                    downloader, processor, parser, allowed_commenters, 
                    keywords, exclude_keywords, shutdown_handler
                )
                
                if not found_unprocessed:
                    start_index += batch_size
                    print(f"\nAll videos in current batch are processed, fetching next {batch_size} videos...")
            
            print("\nImmediate processing complete. Switching to schedule mode...")
        
        # Regular schedule loop
        while not shutdown_handler.shutdown:
            try:
                if shutdown_handler.shutdown:
                    break
                
                if scheduler.is_schedule_time():
                    print("\nSchedule time reached, starting video processing...")
                    batch_size = 50
                    start_index = 0
                    found_unprocessed = False
                    
                    while not found_unprocessed and not shutdown_handler.shutdown:
                        print(f"\nFetching videos {start_index+1} to {start_index+batch_size}...")
                        if args.channel:
                            video_ids = youtube.get_channel_videos(
                                channel_id.strip(), 
                                max_results=batch_size,
                                start_index=start_index
                            )
                        else:
                            video_ids = youtube.get_playlist_videos(
                                playlist_id.strip(),
                                max_results=batch_size,
                                start_index=start_index
                            )
                        
                        if not video_ids:
                            print("\nNo more videos found")
                            break
                            
                        print(f"\nFound {len(video_ids)} videos, checking for unprocessed ones...")
                        found_unprocessed = process_batch_of_videos(
                            video_ids, start_index, youtube, scheduler, file_manager,
                            downloader, processor, parser, allowed_commenters, 
                            keywords, exclude_keywords, shutdown_handler
                        )
                        
                        if not found_unprocessed:
                            start_index += batch_size
                            print(f"\nAll videos in current batch are processed, fetching next {batch_size} videos...")
                    
                    # After processing, wait a bit to avoid immediate recheck
                    for _ in range(30):  # 5 minutes with checks every 10 seconds
                        if shutdown_handler.shutdown:
                            break
                        time.sleep(10)
                
                # Short wait between checks with frequent shutdown checks
                for _ in range(3):  # 30 seconds with checks every 10 seconds
                    if shutdown_handler.shutdown:
                        break
                    time.sleep(10)
                    
            except Exception as e:
                print(f"\nError in main loop: {str(e)}")
                if not shutdown_handler.shutdown:
                    # Wait with shutdown checks
                    for _ in range(180):  # 30 minutes with checks every 10 seconds
                        if shutdown_handler.shutdown:
                            break
                        time.sleep(10)
    
    finally:
        print("\nShutting down gracefully...")
        cleanup_temp_files()
        print("Cleanup complete. Goodbye!")

if __name__ == "__main__":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    main() 