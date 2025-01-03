from src.youtube.uploader import YouTubeUploader
from datetime import datetime
import os
from dotenv import load_dotenv
from typing import Optional
from src.utils.logger import Logger
from googleapiclient.http import MediaFileUpload

logger = Logger()

class UploadScheduler:
    """Handles video upload scheduling."""
    
    def __init__(self, youtube_api):
        """Initialize with YouTubeAPI instance"""
        self.youtube = youtube_api
        
        # Load scheduler-specific settings
        load_dotenv()
        self.upload_times = [
            datetime.strptime(t.strip(), '%H:%M').time() 
            for t in os.getenv('UPLOAD_TIMES', '9:00,15:00').split(',')
        ]
        self.playlist_id = os.getenv('UPLOAD_PLAYLIST_ID')

    def upload_video(self, file_path: str, title: str, description: str, privacy_status: str = "private", tags: Optional[list] = None):
        """Compatibility method for video uploads"""
        try:
            # Upload using YouTube API
            request = self.youtube.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": title,
                        "description": description,
                        "tags": tags or [],
                        "categoryId": "22"
                    },
                    "status": {
                        "privacyStatus": privacy_status,
                        "selfDeclaredMadeForKids": False
                    }
                },
                media_body=MediaFileUpload(
                    file_path,
                    chunksize=1024*1024,
                    resumable=True
                )
            )
            
            # Execute upload with progress tracking
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.progress(f"Upload progress: {progress}%")
            
            video_id = response['id']
            logger.log(f"Upload complete! Video ID: {video_id}")
            
            # Add to playlist if configured
            if self.playlist_id:
                self.youtube.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": self.playlist_id,
                            "resourceId": {
                                "kind": "youtube#video",
                                "videoId": video_id
                            }
                        }
                    }
                ).execute()
                logger.log(f"Added to playlist: {self.playlist_id}")
            
            return video_id
            
        except Exception as e:
            logger.log(f"Error uploading video: {str(e)}")
            return None

    def is_schedule_time(self) -> bool:
        """Check if current time matches any schedule time."""
        current_time = datetime.now()
        
        for upload_time in self.upload_times:
            if current_time.hour == upload_time.hour and current_time.minute == upload_time.minute:
                return True
        
        # Print current time and next schedule
        current_str = current_time.strftime("%H:%M:%S")
        next_time = None
        
        # Find next schedule time
        for upload_time in self.upload_times:
            schedule_time = current_time.replace(
                hour=upload_time.hour, 
                minute=upload_time.minute, 
                second=0, 
                microsecond=0
            )
            
            if schedule_time > current_time:
                if next_time is None or schedule_time < next_time:
                    next_time = schedule_time
        
        # If no time found today, use first time tomorrow
        if next_time is None and self.upload_times:
            next_time = current_time.replace(
                day=current_time.day + 1,
                hour=self.upload_times[0].hour,
                minute=self.upload_times[0].minute,
                second=0,
                microsecond=0
            )
        
        if next_time:
            waiting_minutes = int((next_time - current_time).total_seconds() / 60)
            waiting_hours = waiting_minutes // 60
            waiting_minutes = waiting_minutes % 60
            logger.progress(
                f"Current time: {current_str} | "
                f"Next schedule: {next_time.strftime('%H:%M')} | "
                f"Waiting: {waiting_hours}h {waiting_minutes}m"
            )
        
        return False