import discord
from discord.ext import commands
import yt_dlp
import asyncio
from collections import deque
import random
import logging
from utils.music_utils import MusicQueue, Song

logger = logging.getLogger(__name__)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}  # Guild ID -> MusicQueue
        self.voice_clients = {}  # Guild ID -> VoiceClient
        
        # YT-DLP options - Updated for better compatibility
        self.ytdl_format_options = {
            'format': 'bestaudio/best',
            'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': False,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'logtostderr': False,
            'quiet': True,
            'no_warnings': True,
            'default_search': 'ytsearch',
            'source_address': '0.0.0.0',
            'extractaudio': True,
            'audioformat': 'mp3',
            'embed_subs': False,
            'writesubtitles': False
        }
        
        # FFmpeg options - Enhanced for Railway
        self.ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -b:a 128k'
        }
        
        self.ytdl = yt_dlp.YoutubeDL(self.ytdl_format_options)

    def get_queue(self, guild_id):
        """Get or create queue for guild"""
        if guild_id not in self.queues:
            self.queues[guild_id] = MusicQueue()
        return self.queues[guild_id]

    async def search_song(self, query):
        """Search for a song and return Song object"""
        try:
            # Extract info without downloading
            info = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.ytdl.extract_info(query, download=False)
            )
            
            if 'entries' in info:
                # Playlist
                songs = []
                for entry in info['entries'][:50]:  # Limit to 50 songs
                    if entry:
                        song = Song(
                            title=entry.get('title', 'Unknown'),
                            url=entry.get('url'),
                            duration=entry.get('duration', 0),
                            thumbnail=entry.get('thumbnail'),
                            uploader=entry.get('uploader', 'Unknown')
                        )
                        songs.append(song)
                return songs
            else:
                # Single song
                song = Song(
                    title=info.get('title', 'Unknown'),
                    url=info.get('url'),
                    duration=info.get('duration', 0),
                    thumbnail=info.get('thumbnail'),
                    uploader=info.get('uploader', 'Unknown')
                )
                return [song]
                
        except Exception as e:
            logger.error(f"Error searching for song: {e}")
            raise e

    async def play_next(self, guild_id):
        """Play the next song in queue"""
        queue = self.get_queue(guild_id)
        
        if queue.is_empty():
            # Auto-disconnect after 5 minutes of inactivity
            await asyncio.sleep(300)
            if queue.is_empty() and guild_id in self.voice_clients:
                await self.voice_clients[guild_id].disconnect()
                del self.voice_clients[guild_id]
            return
        
        song = queue.get_next()
        voice_client = self.voice_clients.get(guild_id)
        
        if voice_client and not voice_client.is_playing():
            try:
                source = discord.FFmpegPCMAudio(song.url, **self.ffmpeg_options)
                voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(
                    self.play_next(guild_id), self.bot.loop
                ))
                queue.current = song
                logger.info(f"Now playing: {song.title}")
            except Exception as e:
                logger.error(f"Error playing song: {e}")
                await self.play_next(guild_id)

    @commands.command(name='play', aliases=['p'])
    async def play(self, ctx, *, query=None):
        """Play music from YouTube, Spotify, or SoundCloud"""
        if not query:
            embed = discord.Embed(
                title="❌ No Query Provided",
                description="Please provide a song name or URL to search for.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        # Check if user is in voice channel
        if not ctx.author.voice:
            embed = discord.Embed(
                title="❌ Not in Voice Channel",
                description="You must be in a voice channel to use this command!",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        # Join voice channel if not already connected
        if ctx.guild.id not in self.voice_clients:
            voice_channel = ctx.author.voice.channel
            voice_client = await voice_channel.connect()
            self.voice_clients[ctx.guild.id] = voice_client

        # Search for song
        embed = discord.Embed(
            title="🔍 Searching...",
            description=f"Searching for: `{query}`",
            color=discord.Color.blue()
        )
        message = await ctx.send(embed=embed)

        try:
            songs = await self.search_song(query)
            queue = self.get_queue(ctx.guild.id)
            
            if len(songs) == 1:
                # Single song
                song = songs[0]
                queue.add(song)
                
                embed = discord.Embed(
                    title="✅ Added to Queue",
                    description=f"**{song.title}**\nBy: {song.uploader}",
                    color=discord.Color.green()
                )
                if song.thumbnail:
                    embed.set_thumbnail(url=song.thumbnail)
                embed.add_field(name="Duration", value=song.format_duration(), inline=True)
                embed.add_field(name="Position in Queue", value=str(len(queue.songs)), inline=True)
                
            else:
                # Playlist
                for song in songs:
                    queue.add(song)
                
                embed = discord.Embed(
                    title="✅ Playlist Added to Queue",
                    description=f"Added **{len(songs)}** songs to the queue",
                    color=discord.Color.green()
                )

            await message.edit(embed=embed)
            
            # Start playing if not already playing
            voice_client = self.voice_clients[ctx.guild.id]
            if not voice_client.is_playing():
                await self.play_next(ctx.guild.id)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Search Failed",
                description=f"Could not find or play the requested song.\nError: {str(e)}",
                color=discord.Color.red()
            )
            await message.edit(embed=embed)

    @commands.command(name='pause')
    async def pause(self, ctx):
        """Pause the current song"""
        voice_client = self.voice_clients.get(ctx.guild.id)
        
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            embed = discord.Embed(
                title="⏸️ Paused",
                description="Playback has been paused.",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="❌ Nothing Playing",
                description="There's nothing currently playing to pause.",
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='resume')
    async def resume(self, ctx):
        """Resume playback"""
        voice_client = self.voice_clients.get(ctx.guild.id)
        
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            embed = discord.Embed(
                title="▶️ Resumed",
                description="Playback has been resumed.",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Nothing Paused",
                description="There's nothing currently paused to resume.",
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='skip', aliases=['s'])
    async def skip(self, ctx):
        """Skip the current song"""
        voice_client = self.voice_clients.get(ctx.guild.id)
        queue = self.get_queue(ctx.guild.id)
        
        if voice_client and voice_client.is_playing():
            voice_client.stop()  # This will trigger play_next
            embed = discord.Embed(
                title="⏭️ Skipped",
                description="Skipped to the next song.",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="❌ Nothing Playing",
                description="There's nothing currently playing to skip.",
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='stop')
    async def stop(self, ctx):
        """Stop playback and clear the queue"""
        voice_client = self.voice_clients.get(ctx.guild.id)
        queue = self.get_queue(ctx.guild.id)
        
        if voice_client:
            voice_client.stop()
            queue.clear()
            embed = discord.Embed(
                title="⏹️ Stopped",
                description="Playback stopped and queue cleared.",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="❌ Not Connected",
                description="Bot is not connected to a voice channel.",
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='queue', aliases=['q'])
    async def show_queue(self, ctx):
        """Show the current queue"""
        queue = self.get_queue(ctx.guild.id)
        
        if queue.is_empty() and not queue.current:
            embed = discord.Embed(
                title="📝 Queue is Empty",
                description="Add some songs with the play command!",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="📝 Music Queue",
            color=discord.Color.blue()
        )
        
        # Current song
        if queue.current:
            embed.add_field(
                name="🎵 Now Playing",
                value=f"**{queue.current.title}**\nBy: {queue.current.uploader}",
                inline=False
            )
        
        # Upcoming songs
        if not queue.is_empty():
            upcoming = []
            for i, song in enumerate(list(queue.songs)[:10]):  # Show first 10
                upcoming.append(f"`{i+1}.` **{song.title}** - {song.format_duration()}")
            
            embed.add_field(
                name="⏭️ Up Next",
                value="\n".join(upcoming),
                inline=False
            )
            
            if len(queue.songs) > 10:
                embed.add_field(
                    name="➕ More",
                    value=f"And {len(queue.songs) - 10} more songs...",
                    inline=False
                )
        
        await ctx.send(embed=embed)

    @commands.command(name='nowplaying', aliases=['np'])
    async def now_playing(self, ctx):
        """Show information about the currently playing song"""
        queue = self.get_queue(ctx.guild.id)
        
        if not queue.current:
            embed = discord.Embed(
                title="❌ Nothing Playing",
                description="No song is currently playing.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        song = queue.current
        embed = discord.Embed(
            title="🎵 Now Playing",
            description=f"**{song.title}**",
            color=discord.Color.green()
        )
        
        embed.add_field(name="👤 Uploader", value=song.uploader, inline=True)
        embed.add_field(name="⏱️ Duration", value=song.format_duration(), inline=True)
        
        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)
        
        await ctx.send(embed=embed)

    @commands.command(name='volume', aliases=['vol'])
    async def set_volume(self, ctx, volume: int = None):
        """Set the playback volume (1-100)"""
        if volume is None:
            embed = discord.Embed(
                title="🔊 Volume Control",
                description="Please specify a volume level between 1-100.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        if volume < 1 or volume > 100:
            embed = discord.Embed(
                title="❌ Invalid Volume",
                description="Volume must be between 1 and 100.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        voice_client = self.voice_clients.get(ctx.guild.id)
        
        if voice_client and voice_client.source:
            voice_client.source.volume = volume / 100
            embed = discord.Embed(
                title="🔊 Volume Set",
                description=f"Volume set to {volume}%",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="❌ Nothing Playing",
                description="No audio is currently playing.",
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='shuffle')
    async def shuffle_queue(self, ctx):
        """Shuffle the current queue"""
        queue = self.get_queue(ctx.guild.id)
        
        if queue.is_empty():
            embed = discord.Embed(
                title="❌ Queue is Empty",
                description="Add some songs to shuffle!",
                color=discord.Color.red()
            )
        else:
            queue.shuffle()
            embed = discord.Embed(
                title="🔀 Queue Shuffled",
                description=f"Shuffled {len(queue.songs)} songs.",
                color=discord.Color.green()
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='disconnect', aliases=['dc', 'leave'])
    async def disconnect(self, ctx):
        """Disconnect the bot from the voice channel"""
        voice_client = self.voice_clients.get(ctx.guild.id)
        
        if voice_client:
            await voice_client.disconnect()
            del self.voice_clients[ctx.guild.id]
            
            # Clear queue
            queue = self.get_queue(ctx.guild.id)
            queue.clear()
            
            embed = discord.Embed(
                title="👋 Disconnected",
                description="Disconnected from voice channel and cleared queue.",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="❌ Not Connected",
                description="Bot is not connected to a voice channel.",
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Music(bot))