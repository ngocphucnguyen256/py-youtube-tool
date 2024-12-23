import os
from typing import List, Tuple
from datetime import datetime
import subprocess
from src.utils.file_manager import FileManager

class VideoProcessor:
    """Handles video processing operations like clipping and merging."""
    
    def __init__(self):
        self.file_manager = FileManager()
    
    def clip_video(self, input_path: str, output_path: str, start_time: int, end_time: int) -> bool:
        """Create a clip from a video using stream copy when possible."""
        print(f"\nClipping video segment...")
        print(f"Input file: {input_path}")
        print(f"Output file: {output_path}")
        print(f"Time range: {self.file_manager.format_time(start_time)} -> {self.file_manager.format_time(end_time)}")
        
        try:
            # Use ffmpeg directly for faster clipping without re-encoding
            ffmpeg_cmd = [
                'ffmpeg', '-i', input_path,
                '-ss', str(start_time),
                '-to', str(end_time),
                '-c', 'copy',  # Copy streams without re-encoding
                '-avoid_negative_ts', 'make_zero',
                output_path
            ]
            
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
            print("\nClip creation complete!")
            print(f"Saved to: {output_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Error during clipping: {e.stderr.decode()}")
            print(f"Failed to create clip: {os.path.basename(output_path)}")
            return False
    
    def merge_clips(self, clip_paths: List[str], video_id: str) -> str:
        """Merge multiple clips using concat demuxer to avoid re-encoding."""
        if not clip_paths:
            print("No clips to merge")
            return None
        
        output_path = self.file_manager.get_compilation_path(video_id)
        print(f"\nCreating compilation video...")
        print(f"Number of clips to merge: {len(clip_paths)}")
        print(f"Output file: {output_path}")
        
        try:
            # Create a temporary file listing all clips
            concat_file = f"temp_concat_{video_id}.txt"
            with open(concat_file, 'w') as f:
                for clip_path in clip_paths:
                    f.write(f"file '{os.path.abspath(clip_path)}'\n")
            
            # Use ffmpeg concat demuxer
            ffmpeg_cmd = [
                'ffmpeg', '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',  # Copy streams without re-encoding
                output_path
            ]
            
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
            print("\nCompilation complete!")
            print(f"Saved to: {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            print(f"Error creating compilation: {e.stderr.decode()}")
            return None
            
        finally:
            # Clean up concat file
            try:
                os.remove(concat_file)
            except:
                pass
    
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