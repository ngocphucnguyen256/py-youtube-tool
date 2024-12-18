import os
import yt_dlp
from typing import Optional, Dict, Any

class VideoDownloader:
    """Handles video downloading using yt-dlp."""
    
    def __init__(self, output_base_dir: str = "downloads"):
        self.output_base_dir = output_base_dir
        self.default_options = {
            # Format selection
            'format': 'bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/b',
            'merge_output_format': 'mp4',
            
            # Download settings
            'quiet': False,
            'no_warnings': False,
            'progress': True,
            
            # Network settings
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
            'retry_sleep_functions': {'fragment': lambda n: 5 * (n + 1)},
            
            # Workarounds
            'ignoreerrors': True,
            'no_check_certificates': True,
            'geo_bypass': True,
            'nocheckcertificate': True,
            
            # SSL settings
            'nocheckcertificate': True,
            'no_check_certificate': True,
            
            # Headers
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            }
        }
    
    def get_video_folder(self, video_id: str) -> str:
        """Get the folder path for a specific video."""
        return os.path.join(self.output_base_dir, video_id)
    
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get video information without downloading."""
        try:
            with yt_dlp.YoutubeDL(self.default_options) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            print(f"Error getting video info: {str(e)}")
            return None
    
    def save_video_info(self, info: Dict[str, Any], video_dir: str):
        """Save video information to a file."""
        info_file = os.path.join(video_dir, "video_info.txt")
        with open(info_file, "w", encoding="utf-8") as f:
            f.write(f"Title: {info.get('title')}\n")
            f.write(f"Duration: {info.get('duration')} seconds\n")
            f.write(f"Upload date: {info.get('upload_date')}\n")
            f.write(f"View count: {info.get('view_count')}\n")
            f.write(f"Like count: {info.get('like_count')}\n")
            f.write(f"Description:\n{info.get('description')}\n")
    
    def download_video(self, video_id: str) -> Optional[str]:
        """Download a YouTube video."""
        print(f"\nProcessing video {video_id}...")
        video_dir = self.get_video_folder(video_id)
        os.makedirs(video_dir, exist_ok=True)
        
        # Check for existing complete video
        for ext in ['mp4', 'mkv', 'webm']:
            complete_file = os.path.join(video_dir, f"{video_id}.{ext}")
            if os.path.exists(complete_file):
                print(f"Found existing complete video: {complete_file}")
                return complete_file
        
        # Check for existing parts
        video_part = os.path.join(video_dir, f"{video_id}.f612.mp4")
        audio_part = os.path.join(video_dir, f"{video_id}.f140.m4a")
        
        if os.path.exists(video_part) and os.path.exists(audio_part):
            print("Found existing video and audio parts, attempting to merge...")
            try:
                import ffmpeg
                output_file = os.path.join(video_dir, f"{video_id}.mp4")
                
                # Merge video and audio using ffmpeg
                video_stream = ffmpeg.input(video_part)
                audio_stream = ffmpeg.input(audio_part)
                stream = ffmpeg.output(video_stream, audio_stream, output_file, vcodec='copy', acodec='aac')
                ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
                
                print(f"Successfully merged parts into: {output_file}")
                return output_file
            except Exception as e:
                print(f"Failed to merge parts: {str(e)}")
                print("Will try downloading as single file...")
        
        # If no existing files or merge failed, download as single file
        url = f"https://www.youtube.com/watch?v={video_id}"
        output_template = os.path.join(video_dir, '%(id)s.%(ext)s')
        
        try:
            # Configure yt-dlp options
            options = {
                'format': 'best[height<=720][ext=mp4]/best[height<=720]',  # Simpler format selection
                'outtmpl': output_template,
                'quiet': False,
                'no_warnings': False,
                'nocheckcertificate': True,
                'ignoreerrors': True,
                'no_check_certificate': True,
                'prefer_insecure': True,
                'legacy_server_connect': True,
                'extract_flat': False,
                'concurrent_fragment_downloads': 1,
                'buffersize': 1024,
                'http_chunk_size': 10485760,
                'retries': 10,
                'fragment_retries': 10,
                'skip_download': False,
                'overwrites': True,
                'verbose': True
            }
            
            # Download video
            with yt_dlp.YoutubeDL(options) as ydl:
                error_code = ydl.download([url])
                if error_code != 0:
                    raise Exception(f"yt-dlp returned error code: {error_code}")
            
            # Find downloaded file
            for ext in ['mp4', 'mkv', 'webm']:
                file_path = os.path.join(video_dir, f"{video_id}.{ext}")
                if os.path.exists(file_path):
                    print(f"Video downloaded successfully to: {file_path}")
                    return file_path
            
            raise Exception("Downloaded file not found")
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error during download: {error_msg}")
            
            if "Video unavailable" in error_msg:
                print("Video is unavailable or private")
            elif "Sign in" in error_msg:
                print("Video requires authentication")
            elif "copyright" in error_msg.lower():
                print("Video blocked due to copyright")
            elif "certificate" in error_msg.lower():
                print("SSL certificate error - trying to proceed anyway")
            elif "ffmpeg" in error_msg.lower():
                print("FFmpeg is required but not installed. Please install FFmpeg to continue.")
            
            return None