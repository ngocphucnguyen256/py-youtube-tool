# YouTube ASMR Video Clipper

This application automatically clips and reuploads specific segments from ASMR videos based on timestamps in comments.

## Features
- Automatically fetches videos from specified YouTube playlist or channel
- Extracts timestamps from comments
- Creates high-quality compilations from selected segments
- Maintains original video quality settings
- Advanced keyword filtering with inclusion and exclusion
- Scheduled or immediate processing modes
- Smart duplicate detection using YouTube API
- Automatic cleanup of temporary files

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install FFmpeg (required for video processing):
```bash
# Windows (using chocolatey)
choco install ffmpeg

# Mac
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

3. Set up YouTube API credentials:
- Go to [Google Cloud Console](https://console.cloud.google.com)
- Create a new project
- Enable YouTube Data API v3
- Create OAuth 2.0 credentials
- Download the client secrets file and save it as `client_secrets.json`

4. Create `.env` file from template:
```bash
cp .env-example .env
```

5. Configure your `.env` file:
```env
# Source to process (choose one)
PLAYLIST_ID=              # YouTube playlist ID to fetch videos from
CHANNEL_ID=              # Optional: Channel ID or @handle (for --channel mode)

# Processing settings
TIMESTAMP_COMMENTERS=      # Users who post timestamps
KEYWORDS=                  # Keywords to look for in timestamps
KEYWORDS_EXCLUDE=          # Keywords to exclude from matched segments

# Upload settings
UPLOAD_PRIVACY=private     # private, unlisted, or public
VIDEO_NAME_PREFIX=[ASMR]   # Prefix for uploaded videos
VIDEO_TAGS=ASMR, relaxing  # Common tags for all videos

# Schedule settings
UPLOAD_TIMES=10:00,18:00  # When to check for new videos
```

## Usage

### Running Modes

1. Schedule Mode (default, using playlist):
```bash
python main.py
```
- Runs according to times in UPLOAD_TIMES
- Checks for new videos at scheduled times
- Processes and uploads automatically

2. Schedule Mode (using channel):
```bash
python main.py --channel
```
- Same as above but fetches from channel instead of playlist
- Note: Can only access public videos when using channel mode

3. Immediate Mode:
```bash
python main.py -i  # For playlist
python main.py -i --channel  # For channel
```
- Processes one video immediately
- Then switches to schedule mode
- Useful for testing or one-off processing

### Keyword Filtering

The application uses two levels of keyword filtering:
1. `KEYWORDS`: Segments must contain at least one of these keywords
2. `KEYWORDS_EXCLUDE`: Segments containing any of these keywords are excluded

This allows for precise control over which segments are included in the compilation.

## Process Flow
1. Fetches videos from specified playlist or channel
2. Checks for existing uploads on YouTube
3. Downloads video if new
4. Extracts timestamps from comments
5. Filters segments using keywords and exclusions
6. Creates clips based on filtered segments
7. Merges clips into compilation (preserving original quality)
8. Uploads to YouTube
9. Cleans up temporary files

## Shutdown
- Press Ctrl+C for graceful shutdown
- Current operations will complete before exit
- Temporary files are cleaned up automatically

## Files
- `main.py`: Main application script
- `.env`: Configuration file
- `client_secrets.json`: YouTube API credentials