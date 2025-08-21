from collections import deque
import random

class Song:
    def __init__(self, title, url, duration=0, thumbnail=None, uploader="Unknown"):
        self.title = title
        self.url = url
        self.duration = duration  # Duration in seconds
        self.thumbnail = thumbnail
        self.uploader = uploader

    def format_duration(self):
        """Format duration from seconds to MM:SS"""
        if self.duration == 0:
            return "Unknown"
        
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes:02d}:{seconds:02d}"

class MusicQueue:
    def __init__(self):
        self.songs = deque()
        self.current = None

    def add(self, song):
        """Add a song to the queue"""
        self.songs.append(song)

    def get_next(self):
        """Get the next song from the queue"""
        if self.songs:
            return self.songs.popleft()
        return None

    def is_empty(self):
        """Check if the queue is empty"""
        return len(self.songs) == 0

    def clear(self):
        """Clear the entire queue"""
        self.songs.clear()
        self.current = None

    def shuffle(self):
        """Shuffle the queue"""
        songs_list = list(self.songs)
        random.shuffle(songs_list)
        self.songs = deque(songs_list)

    def __len__(self):
        return len(self.songs)