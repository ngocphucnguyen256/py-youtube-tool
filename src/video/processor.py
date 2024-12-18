import os
from typing import List, Tuple
from datetime import datetime
from moviepy.editor import VideoFileClip, concatenate_videoclips

class VideoProcessor:
    """Handles video processing operations like clipping and merging."""
    
    def __init__(self):
        from src.utils.file_manager import FileManager
        self.file_manager = FileManager()
    
    def clip_video(self, input_path: str, output_path: str, start_time: int, end_time: int) -> bool:
        """Create a clip from a video between start_time and end_time."""
        print(f"\nClipping video segment...")
        print(f"Input file: {input_path}")
        print(f"Output file: {output_path}")
        print(f"Time range: {self.file_manager.format_time(start_time)} -> {self.file_manager.format_time(end_time)}")
        
        try:
            print("Loading video file...")
            with VideoFileClip(input_path) as video:
                # Validate times
                video_duration = int(video.duration)
                print(f"Video loaded. Duration: {self.file_manager.format_time(video_duration)}")
                
                if start_time >= video_duration:
                    print("Start time is beyond video duration")
                    return False
                
                # Adjust end time if needed
                actual_end = min(end_time, video_duration)
                duration = actual_end - start_time
                
                if duration <= 0:
                    print("Invalid duration")
                    return False
                
                print(f"Creating clip with duration: {self.file_manager.format_time(duration)}")
                print("Extracting segment...")
                clip = video.subclip(start_time, actual_end)
                
                print("\nWriting clip to file...")
                print("This may take a while depending on the clip duration.")
                print("Progress will be shown below:")
                
                clip.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile='temp-audio.m4a',
                    remove_temp=True,
                    logger=None,
                    verbose=True,
                    fps=24  # Explicitly set FPS to avoid warning
                )
                
                print("\nClip creation complete!")
                print(f"Saved to: {output_path}")
                return True
                
        except Exception as e:
            print(f"Error during clipping: {str(e)}")
            print(f"Failed to create clip: {os.path.basename(output_path)}")
            return False
    
    def merge_clips(self, clip_paths: List[str], video_id: str) -> str:
        """Merge multiple clips into one video."""
        if not clip_paths:
            print("No clips to merge")
            return None
        
        output_path = self.file_manager.get_compilation_path(video_id)
        print(f"\nCreating compilation video...")
        print(f"Number of clips to merge: {len(clip_paths)}")
        print(f"Output file: {output_path}")
        
        clips = []
        total_duration = 0
        try:
            # Load all clips
            print("\nLoading clips:")
            for i, path in enumerate(clip_paths, 1):
                print(f"Loading clip {i}/{len(clip_paths)}: {os.path.basename(path)}")
                clip = VideoFileClip(path)
                clips.append(clip)
                total_duration += clip.duration
            
            print(f"\nTotal compilation duration will be: {self.file_manager.format_time(int(total_duration))}")
            
            # Concatenate clips
            print("\nMerging clips...")
            final_clip = concatenate_videoclips(clips)
            
            # Write final video
            print("\nWriting compilation to file...")
            print("This may take a while depending on the total duration.")
            print("Progress will be shown below:")
            
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                verbose=True,
                fps=24  # Explicitly set FPS to avoid warning
            )
            
            print("\nCompilation complete!")
            print(f"Saved to: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Error creating compilation: {str(e)}")
            return None
            
        finally:
            # Clean up
            print("\nCleaning up resources...")
            for clip in clips:
                try:
                    clip.close()
                except:
                    pass
    
    def process_segments(self, video_path: str, segments: List[Tuple[int, int, str]], video_id: str) -> List[str]:
        """Process multiple segments from a video.
        Returns list of created clip paths."""
        clip_paths = []
        
        for start_time, end_time, description in segments:
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
        
        return clip_paths