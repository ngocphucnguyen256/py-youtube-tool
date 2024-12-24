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
from datetime import datetime, timedelta
import argparse

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

def process_and_upload_video(video_id: str, youtube, uploader, file_manager, downloader, 
                           processor, parser, db_manager, allowed_commenters, keywords, exclude_keywords):
    """Process a single video and upload immediately if successful"""
    try:
        print("\nChecking video status...")
        # First check if video is already processed or uploaded to YouTube
        video_status = db_manager.get_video_status(video_id)
        if video_status:
            print(f"\nVideo {video_id} already processed:")
            print(f"Title: {video_status['title']}")
            print(f"Status: {video_status['status']}")
            print(f"Processed on: {video_status['processed_date']}")
            if video_status['uploaded_date']:
                print(f"Uploaded on: {video_status['uploaded_date']}")
            return

        # Get video info first
        print("\nFetching video information...")
        try:
            video_info = youtube.get_video_info(video_id)
            print(f"Video title: {video_info['title']}")
            
            # Check if title exists in database
            print("Checking database for existing title...")
            if db_manager.is_title_processed(video_info['title']):
                print(f"\nVideo with title '{video_info['title']}' already processed, skipping...")
                return
                
            # Also check YouTube for existing upload with same title
            print("\nChecking YouTube for existing upload...")
            compilation_title = f"[ASMR Compilation] {video_info['title']}"
            if youtube.check_if_uploaded(compilation_title):
                print(f"\nVideo already uploaded to YouTube, adding to database...")
                db_manager.add_processed_video(
                    video_id=video_id,
                    title=video_info['title'],
                    compilation_path=None
                )
                print("Added to database")
                db_manager.mark_as_uploaded(video_id)
                print("Marked as uploaded")
                print("\nWaiting for next schedule...")
                return
                
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
            if uploader.upload_video(video_id, video_info['title'], compilation_path):
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
    return parser.parse_args()

def main():
    args = parse_args()
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
    exclude_keywords = os.getenv("KEYWORDS_EXCLUDE", "").split(",")
    exclude_keywords = [k.strip() for k in exclude_keywords if k.strip()]
    privacy_status = os.getenv("UPLOAD_PRIVACY", "private")
    
    if not channel_id:
        print("Error: Please set CHANNEL_ID in .env file")
        return
    
    # Start scheduler for download timing only
    scheduler = UploadScheduler(youtube, db_manager)
    
    print("\nStarting schedule monitoring...")
    print(f"Configured schedule times: {os.getenv('UPLOAD_TIMES', '10:00,18:00')}")
    
    # Show initial next schedule time
    next_schedule = get_next_schedule_time(os.getenv('UPLOAD_TIMES', '10:00,18:00'))
    print(f"\n{next_schedule}")
    
    # Main processing loop
    try:
        if args.immediate:
            print("\nImmediate mode: Processing one video now...")
            processed_count = 0
            max_results = 5  # Check last 5 videos
            
            video_ids = youtube.get_channel_videos(channel_id.strip(), max_results=max_results)
            
            if video_ids:
                for video_id in video_ids:
                    if shutdown_handler.shutdown:
                        break
                        
                    if video_id not in db_manager.get_processed_video_ids():
                        print(f"\nProcessing new video {video_id}")
                        process_and_upload_video(
                            video_id, youtube, scheduler, file_manager, 
                            downloader, processor, parser, db_manager, 
                            allowed_commenters, keywords, exclude_keywords
                        )
                        processed_count += 1
                        break  # Process one video successfully then stop
                    else:
                        print(f"\nVideo {video_id} already processed, checking next video...")
                
                if processed_count == 0:
                    print(f"\nNo new videos found in the last {max_results} videos")
            else:
                print("\nNo videos found")
            
            print("\nImmediate processing complete. Switching to schedule mode...")
        
        # Regular schedule loop
        while not shutdown_handler.shutdown:
            try:
                # Check for shutdown request more frequently
                if shutdown_handler.shutdown:
                    break
                
                # Wait for next schedule time with frequent shutdown checks
                if scheduler.is_schedule_time():
                    print("\nSchedule time reached, starting video processing...")
                    # Get videos
                    video_ids = youtube.get_channel_videos(channel_id.strip(), max_results=1)
                    
                    if video_ids:
                        for video_id in video_ids:
                            # Check for shutdown request before processing each video
                            if shutdown_handler.shutdown:
                                break
                                
                            if video_id not in db_manager.get_processed_video_ids():
                                print(f"\nProcessing new video {video_id}")
                                process_and_upload_video(
                                    video_id, youtube, scheduler, file_manager, 
                                    downloader, processor, parser, db_manager, 
                                    allowed_commenters, keywords, exclude_keywords
                                )
                    else:
                        print("\nNo new videos found")
                        
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
        # Cleanup code here
        print("Cleanup complete. Goodbye!")

if __name__ == "__main__":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
    main() 