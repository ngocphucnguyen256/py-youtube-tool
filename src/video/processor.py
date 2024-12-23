import os
from typing import List, Tuple
from datetime import datetime
import subprocess
from src.utils.file_manager import FileManager
import json

class VideoProcessor:
    """Handles video processing operations like clipping and merging."""
    
    def __init__(self):
        self.file_manager = FileManager()
    
    def clip_video(self, input_path: str, output_path: str, start_time: int, end_time: int) -> bool:
        """Create a clip from a video using stream copy when possible."""
        try:
            # First get video info
            probe_cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_format', '-show_streams',
                input_path
            ]
            probe_output = subprocess.check_output(probe_cmd).decode('utf-8')
            video_info = json.loads(probe_output)
            
            # Get video stream info
            video_stream = next((s for s in video_info['streams'] if s['codec_type'] == 'video'), None)
            if video_stream:
                width = int(video_stream.get('width', 1920))
                height = int(video_stream.get('height', 1080))
                bitrate = video_stream.get('bit_rate', '4M')
                
                print(f"\nOriginal video: {width}x{height} @ {int(int(bitrate)/1000000)}Mbps")
            
            # Use ffmpeg with high quality settings
            ffmpeg_cmd = [
                'ffmpeg', '-i', input_path,
                '-ss', str(start_time),
                '-to', str(end_time),
                '-c:v', 'libx264',  # Use x264 codec
                '-preset', 'slow',   # Slower encoding = better quality
                '-crf', '18',       # Lower CRF = higher quality (18-23 is visually lossless)
                '-c:a', 'aac',      # AAC audio codec
                '-b:a', '192k',     # Audio bitrate
                '-movflags', '+faststart',  # Enable streaming
                output_path
            ]
            
            print("\nProcessing clip with high quality settings...")
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
            print(f"Clip creation complete: {os.path.basename(output_path)}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error during clipping: {e.stderr.decode()}")
            return False
        except Exception as e:
            print(f"Error processing clip: {str(e)}")
            return False
    
    def merge_clips(self, clip_paths: List[str], video_id: str) -> str:
        """Merge multiple clips with high quality settings."""
        if not clip_paths:
            print("No clips to merge")
            return None
        
        output_path = self.file_manager.get_compilation_path(video_id)
        print(f"\nCreating high quality compilation...")
        
        try:
            # Create concat file
            concat_file = f"temp_concat_{video_id}.txt"
            with open(concat_file, 'w') as f:
                for clip_path in clip_paths:
                    f.write(f"file '{os.path.abspath(clip_path)}'\n")
            
            # Merge with high quality settings
            ffmpeg_cmd = [
                'ffmpeg', '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',
                '-preset', 'slow',
                '-crf', '18',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-movflags', '+faststart',
                output_path
            ]
            
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
            print(f"Compilation complete: {os.path.basename(output_path)}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            print(f"Error creating compilation: {e.stderr.decode()}")
            return None
        finally:
            if os.path.exists(concat_file):
                os.remove(concat_file)
    
    def process_segments(self, video_path: str, segments: List[Tuple[int, int, str]], video_id: str) -> Tuple[List[str], str]:
        """Process multiple segments with progress tracking.
        Returns (clip_paths, compilation_path)"""
        clip_paths = []
        total_segments = len(segments)
        compilation_path = None
        
        print(f"\nProcessing {total_segments} segments:")
        for i, (start_time, end_time, description) in enumerate(segments, 1):
            print(f"\nProgress: {i}/{total_segments} ({i/total_segments*100:.1f}%)")
            # Create a descriptive filename
            output_path = self.file_manager.get_clip_path(
                video_id=video_id,
                start_time=start_time,
                end_time=end_time,
                description=description
            )
            
            print(f"\nProcessing segment: {description}")
            if self.clip_video(video_path, output_path, start_time, end_time):
                clip_paths.append(output_path)
                print(f"Successfully created clip: {os.path.basename(output_path)}")
            else:
                print(f"Failed to create clip for segment {start_time}-{end_time}")
        
        # Create compilation if we have clips
        if clip_paths:
            compilation_path = self.merge_clips(clip_paths, video_id)
            if compilation_path:
                print(f"Created compilation: {os.path.basename(compilation_path)}")
        
        return clip_paths, compilation_path
    
    def process_video_segment(self, input_path, output_path, start_time, end_time, fps=60):
        """
        Process a video segment with optional fps conversion
        """
        try:
            # Cut the segment first
            temp_path = f"{output_path}_temp.mp4"
            
            ffmpeg_cmd = [
                'ffmpeg', '-i', input_path,
                '-ss', str(start_time),
                '-to', str(end_time),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                temp_path
            ]
            subprocess.run(ffmpeg_cmd, check=True)
            
            # Convert to 60fps using frame interpolation
            fps_cmd = [
                'ffmpeg', '-i', temp_path,
                '-filter:v', f'fps={fps}:interp_start=0:interp_end=255',
                '-c:v', 'libx264',
                '-c:a', 'copy',
                output_path
            ]
            subprocess.run(fps_cmd, check=True)
            
            # Clean up temp file
            os.remove(temp_path)
            
        except subprocess.CalledProcessError as e:
            print(f"Error processing video segment: {e}")
            raise