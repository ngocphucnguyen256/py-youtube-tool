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
        """Create a clip from a video using source video's quality settings."""
        try:
            # Get source video info
            probe_cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_format', '-show_streams',
                input_path
            ]
            probe_output = subprocess.check_output(probe_cmd).decode('utf-8')
            video_info = json.loads(probe_output)
            
            # Get video and audio stream info
            video_stream = next((s for s in video_info['streams'] if s['codec_type'] == 'video'), None)
            audio_stream = next((s for s in video_info['streams'] if s['codec_type'] == 'audio'), None)
            
            if video_stream:
                width = int(video_stream.get('width', 1920))
                height = int(video_stream.get('height', 1080))
                video_codec = video_stream.get('codec_name', 'h264')
                video_bitrate = video_stream.get('bit_rate')
                fps = eval(video_stream.get('r_frame_rate', '30/1'))  # Convert fraction to number
                
                print(f"\nSource video specs:")
                print(f"Resolution: {width}x{height}")
                print(f"Codec: {video_codec}")
                print(f"FPS: {fps:.2f}")
                if video_bitrate:
                    print(f"Video Bitrate: {int(int(video_bitrate)/1000)}kbps")
            
            if audio_stream:
                audio_codec = audio_stream.get('codec_name', 'aac')
                audio_bitrate = audio_stream.get('bit_rate', '192k')
                print(f"Audio: {audio_codec} @ {int(int(audio_bitrate)/1000)}kbps")
            
            # Build ffmpeg command using source settings
            ffmpeg_cmd = [
                'ffmpeg', '-i', input_path,
                '-ss', str(start_time),
                '-to', str(end_time)
            ]
            
            # Video settings
            if video_stream:
                ffmpeg_cmd.extend([
                    '-c:v', video_codec if video_codec != 'h264' else 'libx264',
                    '-preset', 'medium'  # Balance between speed and quality
                ])
                
                # Only set bitrate if we have it from source
                if video_bitrate:
                    ffmpeg_cmd.extend(['-b:v', str(video_bitrate)])
            
            # Audio settings
            if audio_stream:
                ffmpeg_cmd.extend([
                    '-c:a', audio_codec if audio_codec != 'aac' else 'aac',
                    '-b:a', str(audio_bitrate)
                ])
            
            # Add output file
            ffmpeg_cmd.extend(['-movflags', '+faststart', output_path])
            
            print("\nProcessing clip with source video settings...")
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
        """Merge multiple clips using source video settings."""
        if not clip_paths:
            print("No clips to merge")
            return None
        
        output_path = self.file_manager.get_compilation_path(video_id)
        print(f"\nCreating compilation with source video settings...")
        
        try:
            # Get settings from first clip
            probe_cmd = [
                'ffprobe', '-v', 'quiet',
                '-print_format', 'json',
                '-show_format', '-show_streams',
                clip_paths[0]
            ]
            probe_output = subprocess.check_output(probe_cmd).decode('utf-8')
            video_info = json.loads(probe_output)
            
            # Get video and audio stream info
            video_stream = next((s for s in video_info['streams'] if s['codec_type'] == 'video'), None)
            audio_stream = next((s for s in video_info['streams'] if s['codec_type'] == 'audio'), None)
            
            # Create concat file
            concat_file = f"temp_concat_{video_id}.txt"
            with open(concat_file, 'w') as f:
                for clip_path in clip_paths:
                    f.write(f"file '{os.path.abspath(clip_path)}'\n")
            
            # Build ffmpeg command using source settings
            ffmpeg_cmd = [
                'ffmpeg', '-f', 'concat',
                '-safe', '0',
                '-i', concat_file
            ]
            
            # Video settings
            if video_stream:
                video_codec = video_stream.get('codec_name', 'h264')
                video_bitrate = video_stream.get('bit_rate')
                
                ffmpeg_cmd.extend([
                    '-c:v', video_codec if video_codec != 'h264' else 'libx264',
                    '-preset', 'medium'
                ])
                
                if video_bitrate:
                    ffmpeg_cmd.extend(['-b:v', str(video_bitrate)])
            
            # Audio settings
            if audio_stream:
                audio_codec = audio_stream.get('codec_name', 'aac')
                audio_bitrate = audio_stream.get('bit_rate', '192k')
                
                ffmpeg_cmd.extend([
                    '-c:a', audio_codec if audio_codec != 'aac' else 'aac',
                    '-b:a', str(audio_bitrate)
                ])
            
            # Add output file
            ffmpeg_cmd.extend(['-movflags', '+faststart', output_path])
            
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