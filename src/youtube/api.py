import os
from typing import List, Optional
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

class YouTubeAPI:
    """Handles all interactions with YouTube API."""
    
    def __init__(self, client_secrets_file: str, api_scopes: List[str]):
        self.client_secrets_file = client_secrets_file
        self.api_scopes = api_scopes
        self.service = None
    
    def authenticate(self):
        """Authenticate with YouTube API."""
        print("Starting authentication process...")
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            self.client_secrets_file, self.api_scopes
        )
        credentials = flow.run_local_server(port=0)
        print("Authentication successful!")
        
        self.service = googleapiclient.discovery.build(
            "youtube", "v3", credentials=credentials
        )
    
    def get_channel_id_from_username(self, username: str) -> Optional[str]:
        """Get channel ID from username."""
        print(f"Looking up channel ID for username: {username}")
        try:
            request = self.service.channels().list(
                part="id",
                forUsername=username
            )
            response = request.execute()
            
            if 'items' in response and response['items']:
                channel_id = response['items'][0]['id']
                print(f"Found channel ID: {channel_id}")
                return channel_id
            else:
                print("Channel not found by username")
                return None
        except Exception as e:
            print(f"Error looking up channel: {str(e)}")
            return None
    
    def search_channel(self, query: str) -> Optional[str]:
        """Search for a channel by name or custom URL."""
        print(f"Searching for channel: {query}")
        try:
            request = self.service.search().list(
                part="id,snippet",
                q=query,
                type="channel",
                maxResults=1
            )
            response = request.execute()
            
            if 'items' in response and response['items']:
                channel_id = response['items'][0]['id']['channelId']
                channel_title = response['items'][0]['snippet']['title']
                print(f"Found channel: {channel_title} (ID: {channel_id})")
                return channel_id
            else:
                print("Channel not found")
                return None
        except Exception as e:
            print(f"Error searching for channel: {str(e)}")
            return None
    
    def get_channel_videos(self, channel_id: str, max_results: int = 10) -> List[str]:
        """Get recent videos from a channel."""
        print(f"\nFetching {max_results} most recent videos from channel {channel_id}...")
        try:
            request = self.service.search().list(
                part="id,snippet",
                channelId=channel_id,
                order="date",
                maxResults=max_results,
                type="video"
            )
            response = request.execute()
            
            if 'items' not in response:
                print("Error: No 'items' in response")
                print("Full response:", response)
                return []
                
            videos = []
            for item in response["items"]:
                video_id = item["id"]["videoId"]
                title = item["snippet"]["title"]
                videos.append(video_id)
                print(f"Found video: {title} (ID: {video_id})")
            
            print(f"Total videos found: {len(videos)}")
            return videos
        except Exception as e:
            print(f"Error fetching videos: {str(e)}")
            return []
    
    def get_video_comments(self, video_id: str, allowed_commenters: List[str]) -> List[dict]:
        """Get comments from specific commenters on a video."""
        print(f"\nFetching comments for video {video_id}...")
        
        request = self.service.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,
            order="relevance"
        )
        response = request.execute()
        
        comments = []
        for item in response["items"]:
            comment_data = item["snippet"]["topLevelComment"]["snippet"]
            author = comment_data["authorDisplayName"]
            
            if author in allowed_commenters:
                comments.append({
                    'author': author,
                    'text': comment_data["textDisplay"]
                })
        
        return comments 