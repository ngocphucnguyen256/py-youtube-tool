from datetime import datetime, timedelta
import time
import os
import threading
from typing import List
from src.youtube.api import YouTubeAPI
from src.utils.db_manager import DatabaseManager

class UploadScheduler:
    def __init__(self, youtube_api: YouTubeAPI, db_manager: DatabaseManager):
        self.youtube_api = youtube_api
        self.db_manager = db_manager
        self.upload_times = self._parse_upload_times()
        self.upload_lock = threading.Lock()
        self.current_upload = None
        
    def _parse_upload_times(self) -> List[tuple]:
        """Parse upload times from environment variable"""
        times_str = os.getenv('UPLOAD_TIMES', '10:00,18:00')
        upload_times = []
        
        for time_str in times_str.split(','):
            try:
                hour, minute = map(int, time_str.strip().split(':'))
                if 0 <= hour < 24 and 0 <= minute < 60:
                    upload_times.append((hour, minute))
                else:
                    print(f"Invalid time format: {time_str}. Using default times.")
            except ValueError:
                print(f"Invalid time format: {time_str}. Using default times.")
                return [(10, 0), (18, 0)]  # Default times
                
        if not upload_times:
            print("No valid upload times found. Using default times.")
            return [(10, 0), (18, 0)]  # Default times
            
        # Sort times chronologically
        upload_times.sort()
        return upload_times
        
    def get_next_upload_time(self) -> datetime:
        """Calculate the next optimal upload time"""
        now = datetime.now()
        
        for hour, minute in self.upload_times:
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target > now:
                return target
                
        # If we've passed all upload times today, schedule for tomorrow
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(
            hour=self.upload_times[0][0],
            minute=self.upload_times[0][1],
            second=0,
            microsecond=0
        )

    def is_schedule_time(self) -> bool:
        """Check if current time matches any schedule time"""
        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute
        
        # Print current status and next schedule
        next_schedule = None
        min_wait = float('inf')
        
        for hour, minute in self.upload_times:
            schedule_minutes = hour * 60 + minute
            wait_minutes = schedule_minutes - current_minutes
            
            # If time has passed today, add 24 hours
            if wait_minutes < 0:
                wait_minutes += 24 * 60
                
            if wait_minutes < min_wait:
                min_wait = wait_minutes
                next_schedule = f"{hour:02d}:{minute:02d}"
            
            # Check if we're within the 5-minute window
            if abs(current_minutes - schedule_minutes) <= 5:
                return True
        
        # Print waiting status
        hours = min_wait // 60
        minutes = min_wait % 60
        print(f"\rCurrent time: {now.strftime('%H:%M:%S')} | Next schedule: {next_schedule} | Waiting: {int(hours)}h {int(minutes)}m", end='')
        return False

    def schedule_uploads(self):
        while True:
            pending_uploads = self.db_manager.get_pending_uploads()
            if not pending_uploads:
                print("No pending uploads found")
                time.sleep(3600)  # Check again in an hour
                continue

            next_upload_time = self.get_next_upload_time()
            wait_time = (next_upload_time - datetime.now()).total_seconds()
            
            if wait_time > 0:
                print(f"Waiting until {next_upload_time.strftime('%Y-%m-%d %H:%M:%S')} for next upload")
                time.sleep(wait_time)

            # Try to acquire lock for upload
            if self.upload_lock.acquire(blocking=False):
                try:
                    # Upload the video
                    video_id, title, compilation_path = pending_uploads[0]
                    self.current_upload = title
                    print(f"Starting upload for compilation: {title}")
                    
                    if not os.path.exists(compilation_path):
                        print(f"Compilation file not found: {compilation_path}")
                        continue
                    
                    self.youtube_api.upload_video(
                        video_path=compilation_path,
                        title=f"[ASMR Compilation] {title}",
                        description=f"Compilation from original video: {title}"
                    )
                    self.db_manager.mark_as_uploaded(video_id)
                    print(f"Successfully uploaded compilation: {title}")
                    
                    # Clean up compilation file after successful upload
                    try:
                        os.remove(compilation_path)
                    except:
                        print(f"Failed to remove compilation file: {compilation_path}")
                    
                except Exception as e:
                    print(f"Failed to upload compilation {title}: {str(e)}")
                finally:
                    self.current_upload = None
                    self.upload_lock.release()
            else:
                print(f"Previous upload still in progress: {self.current_upload}")
                print("Will try again in 5 minutes")
                time.sleep(300)

            # Short wait before checking again
            time.sleep(300)

    def upload_video(self, video_id: str, title: str, compilation_path: str) -> bool:
        """Upload a video immediately"""
        if self.upload_lock.acquire(blocking=False):
            try:
                self.current_upload = title
                print(f"Starting upload for compilation: {title}")
                
                if not os.path.exists(compilation_path):
                    print(f"Compilation file not found: {compilation_path}")
                    return False
                
                self.youtube_api.upload_video(
                    video_path=compilation_path,
                    title=f"[ASMR Compilation] {title}",
                    description=f"Compilation from original video: {title}"
                )
                self.db_manager.mark_as_uploaded(video_id)
                print(f"Successfully uploaded compilation: {title}")
                
                # Clean up compilation file after successful upload
                try:
                    os.remove(compilation_path)
                except:
                    print(f"Failed to remove compilation file: {compilation_path}")
                
                return True
                
            except Exception as e:
                print(f"Failed to upload compilation {title}: {str(e)}")
                return False
            finally:
                self.current_upload = None
                self.upload_lock.release()
        else:
            print(f"Previous upload still in progress: {self.current_upload}")
            return False