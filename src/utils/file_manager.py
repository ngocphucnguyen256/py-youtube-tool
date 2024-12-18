import os
from typing import Tuple, List

class FileManager:
    """Manages file operations and directory structure."""
    
    def __init__(self, base_dir: str = "downloads"):
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
    
    def get_video_folder(self, video_id: str) -> str:
        """Get the folder path for a specific video."""
        return os.path.join(self.base_dir, video_id)
    
    def get_clips_folder(self, video_id: str) -> str:
        """Get the clips folder path for a specific video."""
        clips_folder = os.path.join(self.get_video_folder(video_id), "parts")
        os.makedirs(clips_folder, exist_ok=True)
        return clips_folder
    
    def check_existing_files(self, video_id: str) -> Tuple[str, List[str]]:
        """Check if video or its clips already exist.
        Returns (existing_video_path, list_of_existing_clips)"""
        # Check video-specific folder in downloads
        video_dir = self.get_video_folder(video_id)
        if os.path.exists(video_dir):
            for ext in ['mp4', 'mkv', 'webm']:
                video_path = os.path.join(video_dir, f"{video_id}.{ext}")
                if os.path.exists(video_path):
                    print(f"Found existing downloaded video: {video_path}")
                    return video_path, []
        
        # Check clips folder for existing clips from this video
        clips_folder = self.get_clips_folder(video_id)
        existing_clips = []
        if os.path.exists(clips_folder):
            for filename in os.listdir(clips_folder):
                if filename.startswith(video_id) and filename.endswith(".mp4"):
                    clip_path = os.path.join(clips_folder, filename)
                    existing_clips.append(clip_path)
        
        if existing_clips:
            print(f"Found {len(existing_clips)} existing clips for video {video_id}")
            for clip in existing_clips:
                print(f"  - {clip}")
        
        return None, existing_clips
    
    def cleanup_video(self, video_path: str):
        """Clean up downloaded video file."""
        if video_path and os.path.exists(video_path):
            print(f"\nCleaning up downloaded video: {video_path}")
            try:
                os.remove(video_path)
                print("Cleanup complete")
            except Exception as e:
                print(f"Error during cleanup: {str(e)}")
    
    def create_video_folder(self, video_id: str) -> str:
        """Create and return path to video-specific folder."""
        folder_path = self.get_video_folder(video_id)
        os.makedirs(folder_path, exist_ok=True)
        return folder_path
    
    def format_time(self, seconds: int) -> str:
        """Convert seconds to MM:SS format."""
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes:02d}m{remaining_seconds:02d}s"
    
    def get_clip_path(self, video_id: str, start_time: int, description: str, end_time: int = None) -> str:
        """Generate path for a clip file."""
        # Convert times to readable format
        start_time_str = self.format_time(start_time)
        time_str = start_time_str
        
        if end_time is not None:
            end_time_str = self.format_time(end_time)
            time_str = f"{start_time_str}_to_{end_time_str}"
        
        # Clean up description
        safe_desc = "".join(c if c.isalnum() else "_" for c in description[:30])
        filename = f"{video_id}_{time_str}_{safe_desc}.mp4"
        return os.path.join(self.get_clips_folder(video_id), filename)
    
    def get_compilation_path(self, video_id: str, timestamp: str = None) -> str:
        """Generate path for a compilation file."""
        if timestamp is None:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"compilation_{timestamp}.mp4"
        return os.path.join(self.get_video_folder(video_id), filename) 