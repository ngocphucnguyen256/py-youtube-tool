import os
from typing import Tuple, List

class FileManager:
    """Manages file operations and directory structure."""
    
    def __init__(self, base_dir: str = "downloads", clips_dir: str = "clips"):
        self.base_dir = base_dir
        self.clips_dir = clips_dir
        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(clips_dir, exist_ok=True)
    
    def get_video_folder(self, video_id: str) -> str:
        """Get the folder path for a specific video."""
        return os.path.join(self.base_dir, video_id)
    
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
        existing_clips = []
        if os.path.exists(self.clips_dir):
            for filename in os.listdir(self.clips_dir):
                if filename.startswith(video_id) and filename.endswith(".mp4"):
                    clip_path = os.path.join(self.clips_dir, filename)
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
    
    def get_clip_path(self, video_id: str, start_time: int, description: str) -> str:
        """Generate path for a clip file."""
        safe_desc = "".join(c if c.isalnum() else "_" for c in description[:30])
        filename = f"{video_id}_{start_time}_{safe_desc}.mp4"
        return os.path.join(self.clips_dir, filename)
    
    def get_compilation_path(self, timestamp: str = None) -> str:
        """Generate path for a compilation file."""
        if timestamp is None:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"compilation_{timestamp}.mp4"
        return os.path.join(self.clips_dir, filename) 