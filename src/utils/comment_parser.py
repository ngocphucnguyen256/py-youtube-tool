import re
from typing import List, Tuple

class CommentParser:
    """Parses YouTube comments to extract timestamps and descriptions."""
    
    @staticmethod
    def parse_timestamp(timestamp: str) -> int:
        """Convert timestamp string to seconds."""
        parts = timestamp.split(":")
        if len(parts) == 2:
            minutes, seconds = parts
            hours = 0
        else:
            hours, minutes, seconds = parts
        
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
    
    @staticmethod
    def extract_timestamps(comments: List[dict]) -> List[Tuple[int, str]]:
        """Extract timestamps and descriptions from comments."""
        timestamps = []
        # Pattern for YouTube link timestamps
        youtube_link_pattern = r't=(\d+)"[^>]*>([^<]+)</a>\s*([^<]*(?:<br>)?)'
        
        for comment in comments:
            text = comment['text']
            matches = re.finditer(youtube_link_pattern, text)
            
            for match in matches:
                seconds, time_str, description = match.groups()
                # Clean up the description
                description = description.replace("<br>", "").strip()
                if not description:
                    description = time_str.strip()
                timestamps.append((int(seconds), description))
        
        return sorted(timestamps)
    
    @staticmethod
    def find_continuous_segments(timestamps: List[Tuple[int, str]], keywords: List[str], exclude_keywords: List[str] = None) -> List[Tuple[int, int, str]]:
        """Find continuous segments that match keywords and don't contain excluded keywords.
        Returns list of (start_time, end_time, description) tuples."""
        segments = []
        matched_indices = []
        
        # Clean and prepare exclude keywords
        exclude_keywords = [k.strip().lower() for k in (exclude_keywords or [])]
        
        # First, find all timestamps that match keywords and don't contain excluded keywords
        for i, (time_sec, desc) in enumerate(timestamps):
            desc_lower = desc.lower()
            # Check if description matches any keyword
            if any(keyword in desc_lower for keyword in keywords):
                # Check if description contains any excluded keyword
                if not exclude_keywords or not any(ex_keyword in desc_lower for ex_keyword in exclude_keywords):
                    matched_indices.append(i)
        
        if not matched_indices:
            return segments
        
        # Process matched indices to find continuous segments
        current_start_idx = matched_indices[0]
        current_start_time = timestamps[current_start_idx][0]
        current_desc = timestamps[current_start_idx][1]
        
        for i in range(len(matched_indices) - 1):
            current_idx = matched_indices[i]
            next_idx = matched_indices[i + 1]
            
            # If next matched timestamp is not consecutive, end current segment
            if next_idx - current_idx > 1:
                end_time = timestamps[current_idx + 1][0]  # Use next timestamp as end
                segments.append((current_start_time, end_time, current_desc))
                # Start new segment
                current_start_idx = next_idx
                current_start_time = timestamps[next_idx][0]
                current_desc = timestamps[next_idx][1]
        
        # Handle last segment
        last_idx = matched_indices[-1]
        if last_idx < len(timestamps) - 1:
            end_time = timestamps[last_idx + 1][0]
        else:
            # If it's the last timestamp, add 60 seconds
            end_time = timestamps[last_idx][0] + 60
        
        segments.append((current_start_time, end_time, timestamps[last_idx][1]))
        
        return segments
    
    @staticmethod
    def save_timestamps(video_id: str, timestamps: List[Tuple[int, str]], output_dir: str):
        """Save timestamps to a file."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        timestamp_file = os.path.join(output_dir, "timestamps.txt")
        
        with open(timestamp_file, "w", encoding="utf-8") as f:
            f.write(f"Timestamps for video {video_id}\n")
            f.write("-" * 50 + "\n\n")
            
            for time_sec, desc in sorted(timestamps):
                minutes = time_sec // 60
                hours = minutes // 60
                minutes = minutes % 60
                seconds = time_sec % 60
                if hours > 0:
                    time_str = f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    time_str = f"{minutes}:{seconds:02d}"
                f.write(f"{time_str}: {desc}\n")
        
        print(f"Saved timestamps to: {timestamp_file}") 