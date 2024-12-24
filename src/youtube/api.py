import os
from typing import List, Optional
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload

class YouTubeAPI:
    """Handles all interactions with YouTube API."""
    
    def __init__(self, client_secrets_file: str, api_scopes: List[str]):
        self.client_secrets_file = client_secrets_file
        self.api_scopes = api_scopes
        self.youtube = None
        self.credentials = None
    
    def authenticate(self):
        """Single authentication for all YouTube operations"""
        print("Starting authentication process...")
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            self.client_secrets_file, self.api_scopes
        )
        self.credentials = flow.run_local_server(port=0)
        self.youtube = googleapiclient.discovery.build(
            "youtube", "v3", credentials=self.credentials
        )
        print("Authentication successful!")
    
    def upload_video(self, video_path: str, title: str, description: str = "", 
                    privacy_status: str = "private", tags: List[str] = None):
        """Upload video using the same authenticated client"""
        if not self.youtube:
            raise Exception("YouTube API not authenticated")

        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags or [],
                'categoryId': '22'  # People & Blogs category
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }

        # Create upload request
        insert_request = self.youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=MediaFileUpload(
                video_path, 
                chunksize=1024*1024,  # 1MB chunks
                resumable=True,
                mimetype='video/mp4'
            )
        )

        print(f"\nStarting upload of {os.path.basename(video_path)}...")
        response = None
        while response is None:
            try:
                status, response = insert_request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    # Clear line and show progress
                    print(f"\rUploading... [{progress}%] {'=' * (progress//2)}>{' ' * (50-progress//2)}", end='')
            except Exception as e:
                print(f"\nError during upload: {str(e)}")
                return None

        if response:
            print(f"\nUpload complete! Video ID: {response['id']}")
            print(f"Video URL: https://youtu.be/{response['id']}")
            return response['id']
        else:
            print("\nUpload failed")
            return None
    
    def get_channel_id_from_username(self, username: str) -> Optional[str]:
        """Get channel ID from username."""
        print(f"Looking up channel ID for username: {username}")
        try:
            request = self.youtube.channels().list(
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
            # First try exact channel name
            request = self.youtube.search().list(
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
            
            # If not found, try with @handle
            if not query.startswith('@'):
                return self.search_channel(f"@{query}")
            
            print("Channel not found")
            return None
        except Exception as e:
            print(f"Error searching for channel: {str(e)}")
            return None
    
    def get_channel_videos(self, channel_id: str, max_results: int = 50, start_index: int = 0) -> List[str]:
        """Get recent videos from a channel.
        
        Args:
            channel_id: The channel ID or username
            max_results: Maximum number of videos to return
            start_index: Skip this many videos before starting to return results
        """
        print(f"\nFetching videos from channel {channel_id}...")
        try:
            # First try with uploads playlist
            channel_request = self.youtube.channels().list(
                part="contentDetails",
                id=channel_id
            ).execute()

            if not channel_request.get('items'):
                # Try with channel username
                channel_request = self.youtube.channels().list(
                    part="contentDetails",
                    forUsername=channel_id
                ).execute()

            if not channel_request.get('items'):
                print(f"No channel found with ID or username: {channel_id}")
                return []

            # Get uploads playlist ID
            uploads_playlist_id = channel_request['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            # Get videos from uploads playlist with pagination
            all_videos = []
            next_page_token = None
            
            # First, collect enough videos to reach start_index + max_results
            target_count = start_index + max_results
            
            while len(all_videos) < target_count:
                playlist_request = self.youtube.playlistItems().list(
                    part="snippet",
                    playlistId=uploads_playlist_id,
                    maxResults=50,  # Maximum allowed by API
                    pageToken=next_page_token
                ).execute()
                
                for item in playlist_request['items']:
                    video_id = item['snippet']['resourceId']['videoId']
                    title = item['snippet']['title']
                    all_videos.append((video_id, title))
                
                next_page_token = playlist_request.get('nextPageToken')
                if not next_page_token:
                    break
            
            # Return the requested slice
            result_videos = []
            for video_id, title in all_videos[start_index:start_index + max_results]:
                result_videos.append(video_id)
                print(f"Found video: {title} (ID: {video_id})")
            
            print(f"Total videos in this batch: {len(result_videos)}")
            return result_videos
            
        except Exception as e:
            print(f"Error fetching videos: {str(e)}")
            return []
    
    def get_video_comments(self, video_id: str, allowed_commenters: List[str]) -> List[dict]:
        """Get comments from specific commenters on a video."""
        print(f"\nFetching comments for video {video_id}...")
        
        request = self.youtube.commentThreads().list(
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
    
    def get_video_info(self, video_id: str) -> dict:
        """Get video details including title, description, etc."""
        try:
            request = self.youtube.videos().list(
                part="snippet",
                id=video_id
            )
            response = request.execute()
            
            if not response.get('items'):
                print(f"No video found with ID: {video_id}")
                return {
                    'title': f'Video_{video_id}',
                    'description': ''
                }
            
            return response['items'][0]['snippet']
        except Exception as e:
            print(f"Error getting video info: {str(e)}")
            return {
                'title': f'Video_{video_id}',
                'description': ''
            }
    
    def check_if_uploaded(self, video_id: str) -> bool:
        """Check if we've already uploaded a compilation for this video ID.
        
        Args:
            video_id: The original video ID to check
        """
        try:
            print(f"Checking if video {video_id} was already processed...")
            # Search for videos on your channel that mention this ID in description
            request = self.youtube.search().list(
                part="snippet",
                q=f"Original video: https://youtu.be/{video_id}",
                type="video",
                forMine=True,
                maxResults=50  # Check more videos to be sure
            )
            response = request.execute()
            
            if response.get('items'):
                for item in response['items']:
                    # Get full video details to check description
                    video_request = self.youtube.videos().list(
                        part="snippet",
                        id=item['id']['videoId']
                    ).execute()
                    
                    if video_request['items']:
                        description = video_request['items'][0]['snippet']['description']
                        if f"Original video: https://youtu.be/{video_id}" in description:
                            print(f"Found existing compilation for video {video_id}")
                            return True
            
            print("No existing compilation found")
            return False
            
        except Exception as e:
            print(f"Error checking for existing upload: {e}")
            return False
    
    def get_playlist_videos(self, playlist_id: str, max_results: int = 50, start_index: int = 0) -> List[str]:
        """Get videos from a playlist.
        
        Args:
            playlist_id: The playlist ID
            max_results: Maximum number of videos to return
            start_index: Skip this many videos before starting to return results
        """
        print(f"\nFetching videos from playlist {playlist_id}...")
        try:
            # Get videos from playlist with pagination
            all_videos = []
            next_page_token = None
            
            # First, collect enough videos to reach start_index + max_results
            target_count = start_index + max_results
            
            while len(all_videos) < target_count:
                playlist_request = self.youtube.playlistItems().list(
                    part="snippet",
                    playlistId=playlist_id,
                    maxResults=50,  # Maximum allowed by API
                    pageToken=next_page_token
                ).execute()
                
                for item in playlist_request['items']:
                    video_id = item['snippet']['resourceId']['videoId']
                    title = item['snippet']['title']
                    all_videos.append((video_id, title))
                    print(f"Found video: {title} (ID: {video_id})")
                
                next_page_token = playlist_request.get('nextPageToken')
                if not next_page_token:
                    break
            
            # Return the requested slice
            result_videos = []
            for video_id, title in all_videos[start_index:start_index + max_results]:
                result_videos.append(video_id)
            
            print(f"Total videos found in this batch: {len(result_videos)}")
            return result_videos
            
        except Exception as e:
            print(f"Error fetching videos from playlist: {str(e)}")
            return []