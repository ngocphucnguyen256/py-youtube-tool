import os
from typing import List, Tuple
from datetime import datetime
from moviepy.editor import VideoFileClip, concatenate_videoclips

class VideoProcessor:
    """Handles video processing operations like clipping and merging."""
    
    def __init__(self, output_dir: str = "clips"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def clip_video(self, input_path: str, output_path: str, start_time: int, end_time: int) -> bool:
        """Create a clip from a video between start_time and end_time."""
        print(f"\nClipping video segment...")
        print(f"Time range: {start_time}s -> {end_time}s")
        print(f"Output: {output_path}")
        
        try:
            with VideoFileClip(input_path) as video:
                # Validate times
                video_duration = int(video.duration)
                if start_time >= video_duration:
                    print("Start time is beyond video duration")
                    return False
                
                # Adjust end time if needed
                actual_end = min(end_time, video_duration)
                duration = actual_end - start_time
                
                if duration <= 0:
                    print("Invalid duration")
                    return False
                
                print(f"Video duration: {video_duration}s")
                print(f"Actual clip duration will be: {duration}s")
                
                clip = video.subclip(start_time, actual_end)
                clip.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile='temp-audio.m4a',
                    remove_temp=True,
                    logger=None
                )
                print("Clipping complete!")
                return True
                
        except Exception as e:
            print(f"Error during clipping: {str(e)}")
            return False
    
    def merge_clips(self, clip_paths: List[str], output_filename: str = None) -> str:
        """Merge multiple clips into one video."""
        if not clip_paths:
            print("No clips to merge")
            return None
        
        if output_filename is None:
            output_filename = f"compilation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        
        output_path = os.path.join(self.output_dir, output_filename)
        print(f"\nMerging {len(clip_paths)} clips into: {output_path}")
        
        clips = []
        try:
            # Load all clips
            for path in clip_paths:
                clip = VideoFileClip(path)
                clips.append(clip)
            
            # Concatenate clips
            final_clip = concatenate_videoclips(clips)
            
            # Write final video
            final_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True
            )
            
            print("Compilation created successfully!")
            return output_path
            
        except Exception as e:
            print(f"Error creating compilation: {str(e)}")
            return None
            
        finally:
            # Clean up
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
            safe_desc = "".join(c if c.isalnum() else "_" for c in description[:30])
            output_filename = f"{video_id}_{start_time}_{safe_desc}.mp4"
            output_path = os.path.join(self.output_dir, output_filename)
            
            print(f"\nProcessing segment: {description}")
            if self.clip_video(video_path, output_path, start_time, end_time):
                clip_paths.append(output_path)
                print(f"Successfully created clip: {output_filename}")
            else:
                print(f"Failed to create clip for segment {start_time}-{end_time}")
        
        return clip_paths 