#!/usr/bin/env python3
"""
Threads Updater Script

This script updates Spotify playlists with recent tracks from artists on Threads.
It maintains two playlists:
1. Recent releases (last 14 days)
2. All releases from the current year
"""

import os
import json
import datetime
import argparse

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

from spotipy_utils import (
    get_recent_track,
    get_playlist_tracks,
    deduplicate_track_list
)

# Load environment variables from .env file
load_dotenv(override=True)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Update Spotify playlists with tracks from Threads artists')
    parser.add_argument('--dry-run', action='store_true',
                        help='Run without making changes to playlists')
    
    return parser.parse_args()

def get_config(args):
    """Get configuration from arguments and environment variables."""
    # Configuration from .env file with some defaults for non-sensitive values
    config = {
        'client_id': os.environ.get('SPOTIFY_CLIENT_ID'),
        'client_secret': os.environ.get('SPOTIFY_CLIENT_SECRET'),
        'rr_playlist_id': os.environ.get('SPOTIFY_RR_PLAYLIST_ID'),
        'all_playlist_id': os.environ.get('SPOTIFY_ALL_PLAYLIST_ID'),
        'n_days_ago': int(os.environ.get('DAYS_LOOKBACK', 13)),
        'artists_file': os.environ.get('ARTISTS_FILE', 'artists.json'),
        'dry_run': args.dry_run,
        'exclude_ai': os.environ.get('EXCLUDE_AI', True)
    }

    # Validate required configuration
    missing_config = [key for key, value in config.items() 
                     if value is None and key not in ['dry_run']]
    
    if missing_config:
        print(f"Error: Missing required configuration: {', '.join(missing_config)}")
        print("Please set these values in your .env file or provide them as arguments.")
        exit(1)
    return config

def load_artists(file_path, exclude_ai):
    """Load artists from JSON file."""
    try:
        with open(file_path, 'r') as f:
            artists = json.load(f)
        print(f"Loaded {len(artists)} artists from {file_path}")
        # remove artists with heavy ai_usage
        if exclude_ai:
            artists = [artist for artist in artists if not artist.get('ai_usage') or artist['ai_usage'] != 'heavy']
        return artists
    except FileNotFoundError:
        print(f"Error: Artists file not found at {file_path}")
        exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in artists file {file_path}")
        exit(1)

def initialize_spotify_client(client_id, client_secret):
    """Initialize Spotify client with OAuth for playlist modification."""
    try:
        # Create an OAuth manager with the necessary scope for playlist modification
        auth_manager = SpotifyOAuth(
            scope='playlist-modify-public',
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri='https://google.com',  # This can be any URL, we'll manually copy the response
            open_browser=False,
            cache_path='.spotify_token_cache'  # Store the token for reuse
        )
        
        # Create the Spotify client with the auth manager
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        # Check if authentication is needed
        try:
            # Try to get the current user to test authentication
            sp.current_user()
        except:
            # If authentication is needed, provide instructions
            print("\n" + "=" * 80)
            print("Spotify Authentication Required")
            print("=" * 80)
            print("1. Visit the following URL in your browser:")
            print(auth_manager.get_authorize_url())
            print("\n2. After logging in, you'll be redirected to a URL.")
            print("3. Copy the ENTIRE URL from your browser's address bar.")
            print("4. Paste it below:")
            
            # Get the URL from the user
            response_url = input("Enter the URL you were redirected to: ")
            
            # Extract the code from the URL and get the token
            code = auth_manager.parse_response_code(response_url)
            auth_manager.get_access_token(code)
            
            print("Authentication successful! Token has been cached for future use.")
        
        return sp
    except Exception as e:
        print(f"Error initializing Spotify client: {e}")
        exit(1)

def collect_tracks(sp, artists, n_days_ago):
    """Collect tracks from artists."""
    all_playlist_tracks = []
    rr_playlist_tracks = []
    
    print(f"Collecting tracks from {len(artists)} artists...")
    
    for artist in artists:
        if not artist.get('spotify_id'):
            print(f"Skipping artist without Spotify ID: {artist.get('name', 'Unknown')}")
            continue
            
        try:
            all_tracks, recent_track = get_recent_track(sp, artist, n_days_ago)
            
            if recent_track:
                rr_playlist_tracks.append(recent_track)
                
            all_playlist_tracks.extend(all_tracks)
        except Exception as e:
            print(f"Error processing artist {artist.get('name')}: {e}")
    
    # Sort tracks by release date (newest first)
    rr_playlist_tracks.sort(key=lambda x: x[2], reverse=True)
    all_playlist_tracks.sort(key=lambda x: x[2], reverse=True)
    
    # Deduplicate all tracks
    all_playlist_tracks = deduplicate_track_list(all_playlist_tracks)
    
    print(f"Found {len(rr_playlist_tracks)} tracks released in the last {n_days_ago} days")
    print(f"Found {len(all_playlist_tracks)} tracks released this year")
    
    return rr_playlist_tracks, all_playlist_tracks

def update_playlists(sp, config, rr_playlist_tracks, all_playlist_tracks):
    """Update Spotify playlists with collected tracks."""
    # Get existing tracks from playlists
    existing_rr_playlist_tracks = sp.playlist_tracks(config['rr_playlist_id'])['items']
    existing_all_playlist_tracks = get_playlist_tracks(sp, config['all_playlist_id'])
    
    # Find new tracks to add
    new_rr_tracks = [track for track in rr_playlist_tracks 
                     if track[0] not in [existing_track['track']['id'] 
                                         for existing_track in existing_rr_playlist_tracks]]
    
    new_all_tracks = [track for track in all_playlist_tracks 
                      if track[0] not in [existing_track['track']['id'] 
                                          for existing_track in existing_all_playlist_tracks]]
    
    print(f"{len(new_rr_tracks)} tracks will be added to the recent releases playlist")
    print(f"{len(new_all_tracks)} tracks will be added to the all tracks playlist")
    
    if config['dry_run']:
        print("DRY RUN: No changes will be made to playlists")
        return new_rr_tracks, new_all_tracks
    
    # Find tracks to remove from recent releases playlist
    old_rr_track_ids = [track['track']['id'] for track in existing_rr_playlist_tracks 
                        if track['track']['id'] not in [track[0] for track in rr_playlist_tracks]]
    
    # Remove old tracks from the recent releases playlist
    if old_rr_track_ids:
        print(f"Removing {len(old_rr_track_ids)} tracks from the recent releases playlist")
        sp.playlist_remove_all_occurrences_of_items(config['rr_playlist_id'], old_rr_track_ids)
    
    # Add new tracks to the recent releases playlist
    if new_rr_tracks:
        print(f"Adding {len(new_rr_tracks)} tracks to the recent releases playlist")
        sp.playlist_add_items(config['rr_playlist_id'], [track[0] for track in new_rr_tracks], position=0)
        print("Recent releases playlist updated successfully!")
    
    # Add new tracks to the all tracks playlist
    if new_all_tracks:
        print(f"Adding {len(new_all_tracks)} tracks to the all tracks playlist")
        # Split the new_all_tracks and upload 50 at a time (Spotify API limit)
        for i in range(0, len(new_all_tracks), 50):
            sp.playlist_add_items(
                config['all_playlist_id'], 
                [track[0] for track in new_all_tracks[i:i+50]], 
                position=0
            )
        print("All tracks playlist updated successfully!")
    
    return new_rr_tracks, new_all_tracks

def generate_summary(sp, config, rr_playlist_tracks, new_rr_tracks):
    """Generate a summary of the playlist update."""
    # Calculate total duration of the recent releases playlist
    total_duration = sum([sp.track(track[0])['duration_ms'] for track in rr_playlist_tracks])
    total_duration_string = str(datetime.timedelta(milliseconds=total_duration)).split('.')[0]
    total_tracks = len(rr_playlist_tracks)
    
    # Format current time
    mountain_time = datetime.datetime.now().strftime("%m/%d/%y %H:%M:%S")
    
    print("\n" + "="*50)
    print(f"Threads Release Radar updated at {mountain_time} MT 🏔")
    print(f"Playlist duration: {total_tracks} tracks, {total_duration_string}")
    
    if new_rr_tracks:
        print(f"New tracks added from: @{', @'.join([a[3] or '' for a in new_rr_tracks])}")
    else:
        print("No new tracks added today!")
    
    print("")
    print(f"Threads Release Radar features new music released from musicians of threads in the last {config['n_days_ago']} days")
    print("")
    print(f"https://open.spotify.com/playlist/{config['rr_playlist_id']}")
    print("="*50)

def main():
    """Main function to run the script."""
    args = parse_arguments()
    config = get_config(args)
    
    # Load artists from JSON file
    artists = load_artists(config['artists_file'], config['exclude_ai'])
    
    # Initialize Spotify client
    sp = initialize_spotify_client(config['client_id'], config['client_secret'])
    
    # Only print authentication URL if needed (handled in initialize_spotify_client)
    
    # Collect tracks from artists
    rr_playlist_tracks, all_playlist_tracks = collect_tracks(sp, artists, config['n_days_ago'])
    
    # Update playlists
    new_rr_tracks, new_all_tracks = update_playlists(sp, config, rr_playlist_tracks, all_playlist_tracks)
    
    # Generate summary
    generate_summary(sp, config, rr_playlist_tracks, new_rr_tracks)

if __name__ == "__main__":
    main()
