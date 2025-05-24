"""Spotify API utility functions for playlist management and track collection.

This module provides helper functions for working with the Spotify API,
specifically for retrieving tracks from artists, managing playlists,
and handling track data.
"""

import datetime
from typing import Dict, List, Optional, Tuple, Any
import dateutil.parser

class MultipleArtistsFoundError(Exception):
    """Raised when multiple artists are found with the same name."""
    pass

class NoArtistsFoundError(Exception):
    """Raised when no artists are found with the given name."""
    pass

def get_recent_track(sp: Any, artist: Dict[str, Any], n_days_ago: int) -> Tuple[List[Tuple[str, str, str, Optional[str], Optional[str]]], Optional[Tuple[str, str, str, Optional[str], Optional[str]]]]:
    """Get recent tracks from an artist released within a specified time period.
    
    Args:
        sp: Spotify API client instance
        artist: Artist information dictionary containing at least 'spotify_id' key
        n_days_ago: Number of days to look back for recent releases
    
    Returns:
        A tuple containing:
            - all_tracks: List of all tracks released this year
            - latest_track: The most recent track released in the last n_days_ago days,
                           or None if no tracks were found in that period
    
    Raises:
        KeyError: If the artist dictionary doesn't contain a 'spotify_id' key
    """
    # Validate artist has required spotify_id
    if 'spotify_id' not in artist:
        raise KeyError(f"Artist dictionary missing required 'spotify_id' key: {artist.get('name', 'Unknown')}")
    # Get the artist's albums and singles
    try:
        albums = sp.artist_albums(artist['spotify_id'], album_type='album,single', country='US')
    except Exception as e:
        print(f"Error fetching albums for artist {artist.get('name', 'Unknown')}: {e}")
        return [], None
    
    # Loop through the albums
    all_tracks = []
    latest_track = None
    today = datetime.date.today()
    day_n_days_ago = today - datetime.timedelta(days=n_days_ago)
    beginning_of_year = datetime.date(today.year, 1, 1)
    
    for album in albums['items']:
        # Get the album release date
        try:
            release_date = dateutil.parser.parse(album['release_date']).date()
        except TypeError as e:
            print(f"Error parsing release date for album {album.get('name', 'Unknown')}: {e}")
            continue
        
        # Check if the album was released in the relevant time period
        if day_n_days_ago <= release_date <= today:
            # Get the album tracks
            try:
                tracks = sp.album_tracks(album['id'])


                for track in tracks['items']:
                    # Store track info as a tuple
                    track_info = (
                        track['id'],
                        track['name'],
                        album['release_date'],
                        artist.get('threads'),
                        artist.get('name')
                    )
                    
                    # Save the first track as the latest track
                    if not latest_track:
                        latest_track = track_info
                        
                    all_tracks.append(track_info)
            except Exception as e:
                print(f"Error processing track from album {album.get('name', 'Unknown')}: {e}")
                continue
                
        elif beginning_of_year <= release_date <= day_n_days_ago:
            # For tracks released this year but before the recent period
            try:
                tracks = sp.album_tracks(album['id'])
                for track in tracks['items']:
                    all_tracks.append((
                        track['id'],
                        track['name'],
                        album['release_date'],
                        artist.get('threads'),
                        artist.get('name')
                    ))
            except Exception as e:
                print(f"Error processing track from album {album.get('name', 'Unknown')}: {e}")
                continue

    # Sort all tracks by release date (newest first) for consistency
    all_tracks.sort(key=lambda x: x[2], reverse=True)
    return all_tracks, latest_track

def get_playlist_tracks(sp: Any, playlist_id: str) -> List[Dict[str, Any]]:
    """Retrieves all tracks from a Spotify playlist.
    
    Args:
        sp: A Spotipy client instance
        playlist_id: The Spotify ID of the playlist
        
    Returns:
        A list of track items from the playlist
        
    Raises:
        ValueError: If the playlist_id is empty or None
    """
    if not playlist_id:
        raise ValueError("playlist_id cannot be empty or None")
    results = sp.playlist_tracks(playlist_id)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    return tracks

def deduplicate_track_list(tracks: List[Tuple[str, str, str, Optional[str], Optional[str]]]) -> List[Tuple[str, str, str, Optional[str], Optional[str]]]:
    """Remove duplicate tracks, keeping only the most recent version of each track.
    
    Args:
        tracks: A list of track tuples where each tuple contains:
               (track_id, name, release_date, artist_threads, artist_name)
    
    Returns:
        A list of unique tracks sorted by release date (oldest to newest).
        When multiple versions of a track exist, only the most recent is kept.
    """
    # Dictionary to store the most recent release for each track name
    track_dict = {}

    for track in tracks:
        if len(track) < 5:
            # Skip malformed track data
            continue
            
        track_id, name, release_date, artist, album = track
        # If the track is not in the dictionary or the new date is more recent, update it
        if name not in track_dict or release_date > track_dict[name][2]:
            track_dict[name] = track

    # Extract the values from the dictionary and convert them back to a list
    unique_tracks = list(track_dict.values())

    # Sort by release date for clarity (oldest first)
    unique_tracks.sort(key=lambda x: x[2])

    return unique_tracks
