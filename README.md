# YouTube Video Manager

A Python application for managing YouTube videos, including compilation creation and video re-uploading.

## Features

### Main Script (main.py)
- Create compilations from videos with timestamps in comments
- Fetch videos from a channel or playlist
- Schedule uploads at specific times
- Filter content based on keywords
- Add uploaded videos to a playlist

### Re-upload Script (reup.py)
- Re-upload any YouTube video to your channel
- Customize title and privacy settings
- Automatically add to a designated playlist
- Preserve video quality and metadata

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up YouTube API:
- Create a project in Google Cloud Console
- Enable YouTube Data API v3
- Create OAuth 2.0 credentials
- Download client secrets file as `client_secrets.json`

3. Configure environment variables:
- Copy `.env-example` to `.env`
- Fill in your configuration values

## Configuration

### Main Compilation Settings
```env
# YouTube API Configuration
CHANNEL_ID=your_channel_id          # Channel to fetch videos from
PLAYLIST_ID=your_playlist_id        # Playlist to fetch videos from

# Compilation Settings
UPLOAD_PRIVACY=private              # private, unlisted, or public
UPLOAD_TIMES=10:00,18:00           # Schedule times
VIDEO_NAME_PREFIX=[ASMR]           # Prefix for uploaded videos
VIDEO_TAGS=ASMR,relaxing           # Tags for uploaded videos
TIMESTAMP_COMMENTERS=user1,user2    # Users who post timestamps
KEYWORDS=keyword1,keyword2         # Keywords to include
KEYWORDS_EXCLUDE=word1,word2       # Keywords to exclude
```

### Re-upload Settings
```env
# Re-upload Settings
REUP_PRIVACY=private               # Default privacy setting
REUP_PREFIX=[Reup]                # Prefix for re-uploaded videos
REUP_TAGS=reupload,video          # Tags for re-uploaded videos
REUP_PLAYLIST_ID=playlist_id      # Playlist for re-uploads
```

## Usage

### Main Compilation Script
```bash
# Process videos from playlist
python main.py

# Process videos from channel
python main.py --channel

# Process immediately without waiting for schedule
python main.py -i
```

### Re-upload Script
```bash
# Basic re-upload
python reup.py VIDEO_URL

# Re-upload with custom title
python reup.py VIDEO_URL --title "Custom Title"

# Re-upload with specific privacy
python reup.py VIDEO_URL --privacy unlisted
```

## Notes
- The application requires YouTube API authentication
- Respects YouTube's terms of service and API quotas
- Cleans up temporary files automatically
- Logs include timestamps for better tracking





for upload_streams:
-save format:

C:\Users\ngocp\Documents\Projects\youtube-reup\downloaded_streams\{owner}\{year}-{month}-{date} {hour}-{min}-{sec} {title}.mp4

