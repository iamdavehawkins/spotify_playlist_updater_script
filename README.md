# Threads Updater Script

This script automatically updates Spotify playlists with tracks from artists on Threads. It maintains two playlists:

1. **Recent Releases**: Tracks released in the last 14 days (configurable)
2. **All Tracks**: All tracks released since the beginning of the current year

## Setup

1. Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Create a `.env` file based on the provided `.env.example`:

```bash
cp .env.example .env
```

3. Edit the `.env` file with your Spotify API credentials and playlist IDs:

```
# Spotify API credentials
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here

# Playlist IDs
SPOTIFY_RR_PLAYLIST_ID=your_release_radar_playlist_id_here
SPOTIFY_ALL_PLAYLIST_ID=your_all_tracks_playlist_id_here

# Configuration
DAYS_LOOKBACK=14
ARTISTS_FILE=artists.json
```

4. Create your `artists.json` file based on the provided example:

```bash
cp artists.example.json artists.json
```

5. Edit the `artists.json` file to include the artists you want to track. Make sure the file is in the correct location as specified in your `.env` file.

## Usage

Run the script with:

```bash
python update_spotify_playlists.py
```

### Configuration

All configuration is managed through the `.env` file. This includes:

- Spotify API credentials
- Playlist IDs
- Number of days to look back for recent releases
- Path to the artists JSON file

### Command Line Arguments

The script relies on the `.env` file for configuration, with only one command-line argument available:

- `--dry-run`: Run without making changes to playlists (preview mode)

### Examples

**Standard run** (updates playlists based on `.env` configuration):
```bash
python update_spotify_playlists.py
```

**Dry run** (shows what would be updated without making changes):
```bash
python update_spotify_playlists.py --dry-run
```

## Artists JSON Format

The `artists.json` file should contain an array of artist objects with the following format:

```json
[
    {
        "name": "Artist Name",
        "spotify_id": "SpotifyArtistID",
        "threads": "ThreadsUsername",
        "bandcamp_domain": "BandcampDomain"
    },
    ...
]
```

Only the `name` and `spotify_id` fields are required for the script to function. The `threads` field is used in the social summary output.

An example file `artists.example.json` is provided with the repository to help you get started.

## Authentication

When you run the script, it will provide a URL for authentication with Spotify. Open this URL in your browser, log in to your Spotify account, and authorize the application. After authorization, you will be redirected to a URL that you should copy and paste back into the terminal when prompted.
