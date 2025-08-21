import discord
from discord.ext import commands
import os
import logging
from dotenv import load_dotenv
import asyncio

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot configuration
TOKEN = os.getenv('TOKEN')
PREFIX = os.getenv('PREFIX', '!')

if not TOKEN:
    logger.error("❌ No TOKEN found in environment variables!")
    exit(1)

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

@bot.event
async def on_ready():
    logger.info(f'🎵 {bot.user} is now playing music!')
    logger.info(f'🔧 Prefix: {PREFIX}')
    logger.info(f'🌐 Connected to {len(bot.guilds)} servers')
    
    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{PREFIX}help | Music Bot"
        )
    )

@bot.event
async def on_command_error(ctx, error):
    """Global error handler"""
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="❌ Command Not Found",
            description=f"Use `{PREFIX}help` to see available commands.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="❌ Missing Arguments",
            description=f"Please provide all required arguments.\nUse `{PREFIX}help {ctx.command}` for more info.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    else:
        logger.error(f"Unhandled error: {error}")
        embed = discord.Embed(
            title="❌ An Error Occurred",
            description="Something went wrong. Please try again later.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name='help')
async def help_command(ctx, command_name=None):
    """Custom help command"""
    if command_name:
        # Help for specific command
        command = bot.get_command(command_name)
        if command:
            embed = discord.Embed(
                title=f"Help: {PREFIX}{command.name}",
                description=command.help or "No description available.",
                color=discord.Color.blue()
            )
            if command.usage:
                embed.add_field(name="Usage", value=f"`{PREFIX}{command.usage}`", inline=False)
        else:
            embed = discord.Embed(
                title="❌ Command Not Found",
                description=f"Command `{command_name}` not found.",
                color=discord.Color.red()
            )
    else:
        # General help
        embed = discord.Embed(
            title="🎵 Music Bot Commands",
            description="Here are all available commands:",
            color=discord.Color.blue()
        )
        
        music_commands = [
            f"`{PREFIX}play <song/url>` - Play music from YouTube/Spotify/SoundCloud",
            f"`{PREFIX}pause` - Pause the current song",
            f"`{PREFIX}resume` - Resume playback",
            f"`{PREFIX}skip` - Skip to the next song",
            f"`{PREFIX}stop` - Stop playback and clear queue",
            f"`{PREFIX}queue` - Show the current queue",
            f"`{PREFIX}nowplaying` - Show current song info",
            f"`{PREFIX}volume <1-100>` - Set playback volume",
            f"`{PREFIX}shuffle` - Shuffle the queue",
            f"`{PREFIX}disconnect` - Disconnect from voice channel"
        ]
        
        embed.add_field(
            name="🎵 Music Commands",
            value="\n".join(music_commands),
            inline=False
        )
        
        embed.set_footer(text=f"Use {PREFIX}help <command> for detailed help on a command")
    
    await ctx.send(embed=embed)

async def load_cogs():
    """Load all cogs"""
    try:
        await bot.load_extension('cogs.music')
        logger.info("✅ Music cog loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load music cog: {e}")

async def main():
    """Main function to run the bot"""
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")