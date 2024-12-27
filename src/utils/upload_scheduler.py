import os
from datetime import datetime
from typing import Optional
from src.utils.logger import Logger

logger = Logger()

class UploadScheduler:
    """Handles video upload scheduling."""
    
    def __init__(self, youtube):
        self.youtube = youtube
    
    def is_schedule_time(self) -> bool:
        """Check if current time matches any schedule time."""
        try:
            current_time = datetime.now()
            schedule_times = os.getenv("UPLOAD_TIMES", "10:00,18:00").split(",")
            
            for time_str in schedule_times:
                hour, minute = map(int, time_str.strip().split(":"))
                if current_time.hour == hour and current_time.minute == minute:
                    return True
            
            # Print current time and next schedule
            current_str = current_time.strftime("%H:%M:%S")
            next_time = None
            next_hour = None
            next_minute = None
            
            # Find next schedule time
            for time_str in schedule_times:
                hour, minute = map(int, time_str.strip().split(":"))
                schedule_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                if schedule_time > current_time:
                    if next_time is None or schedule_time < next_time:
                        next_time = schedule_time
                        next_hour = hour
                        next_minute = minute
            
            # If no time found today, use first time tomorrow
            if next_time is None and schedule_times:
                hour, minute = map(int, schedule_times[0].strip().split(":"))
                next_hour = hour
                next_minute = minute
            
            if next_hour is not None:
                next_str = f"{next_hour:02d}:{next_minute:02d}"
                waiting_minutes = (next_hour * 60 + next_minute) - (current_time.hour * 60 + current_time.minute)
                if waiting_minutes < 0:
                    waiting_minutes += 24 * 60  # Add 24 hours
                waiting_hours = waiting_minutes // 60
                waiting_minutes = waiting_minutes % 60
                logger.progress(f"Current time: {current_str} | Next schedule: {next_str} | Waiting: {waiting_hours}h {waiting_minutes}m")
            
            return False
            
        except Exception as e:
            logger.log(f"Error checking schedule: {str(e)}")
            return False
    
    def upload_video(self, video_id: str, title: str, file_path: str) -> bool:
        """Upload a video."""
        try:
            # Get upload settings from environment
            privacy_status = os.getenv("UPLOAD_PRIVACY", "private")
            video_prefix = os.getenv("VIDEO_NAME_PREFIX", "[ASMR Clip]").strip()
            video_tags = os.getenv("VIDEO_TAGS", "ASMR,relaxing").split(",")
            video_tags = [tag.strip() for tag in video_tags if tag.strip()]
            upload_playlist_id = os.getenv("UPLOAD_PLAYLIST_ID", "").strip()
            
            # Create video title with prefix
            upload_title = f"{video_prefix} {title}"
            if len(upload_title) > 100:  # YouTube title length limit
                upload_title = upload_title[:97] + "..."
            
            # Create description
            description = (
                f"Original video: https://youtu.be/{video_id}\n\n"
                "support anchor on douyu: https://www.douyu.com/5092355"
            )
            
            # Upload video using the YouTube API instance
            request = self.youtube.youtube.videos().insert(
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
                media_body=file_path
            )
            
            logger.log("\nStarting upload...")
            response = request.execute()
            uploaded_video_id = response.get("id")
            
            if uploaded_video_id:
                logger.log(f"Upload complete! Video ID: {uploaded_video_id}")
                logger.log(f"Video URL: https://youtu.be/{uploaded_video_id}")
                
                # Add to playlist if configured
                if upload_playlist_id:
                    if self.youtube.add_to_playlist(uploaded_video_id, upload_playlist_id):
                        logger.log("Added video to playlist")
                    else:
                        logger.log("Failed to add video to playlist")
                
                return True
            else:
                logger.log("Upload failed - no video ID in response")
                return False
            
        except Exception as e:
            logger.log(f"Error uploading video: {str(e)}")
            return False