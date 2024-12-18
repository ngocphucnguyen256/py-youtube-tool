# YouTube ASMR Video Clipper

This application automatically clips and reuploads specific segments from ASMR videos based on timestamps in comments.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up YouTube API credentials:
- Go to [Google Cloud Console](https://console.cloud.google.com)
- Create a new project
- Enable YouTube Data API v3
- Create OAuth 2.0 credentials
- Download the client secrets file and save it as `client_secrets.json`

3. Create a `.env` file with the following:
```
CHANNEL_ID=your_target_channel_id
```

## Usage

Run the main script:
```bash
python main.py
```

The script will:
1. Fetch videos from the specified channel
2. Extract timestamps from comments
3. Download and clip the videos
4. Upload clips to your YouTube channel 