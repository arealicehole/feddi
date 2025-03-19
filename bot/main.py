#!/usr/bin/env python3
"""
Discord Accounting Bot for Trapper Dan Clothing
Main bot implementation file
"""

import os
import logging
import discord
from discord.ext import commands
import sqlite3
from dotenv import load_dotenv
import asyncio
from datetime import datetime
import sys

# Add the parent directory to sys.path to allow importing from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.image_processor import ImageProcessor
from utils.report_generator import ReportGenerator
from utils.db_manager import DatabaseManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("accountme_bot")

# Bot configuration
TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", "!")
ADMIN_USER_IDS = os.getenv("ADMIN_USER_IDS", "").split(",")

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True  # Needed to read message content
intents.members = True  # Needed for member-related events
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# Initialize components
image_processor = None
db_manager = None
report_generator = None

# Bot startup time
startup_time = None

# Method to get the image processor
def get_image_processor():
    """Get the image processor instance"""
    return image_processor
    
# Method to get the database manager
def get_db_manager():
    """Get the database manager instance"""
    return db_manager

# Method to get the report generator
def get_report_generator():
    """Get the report generator instance"""
    return report_generator
    
# Add the methods to the bot
bot.get_image_processor = get_image_processor
bot.db_manager = None  # Will be set in main()
bot.report_generator = None  # Will be set in main()

@bot.event
async def on_ready():
    """Event triggered when the bot is ready and connected to Discord"""
    global startup_time
    startup_time = datetime.now()
    
    logger.info(f"Bot connected as {bot.user.name} (ID: {bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guilds")
    
    # Log connected guilds
    for guild in bot.guilds:
        logger.info(f"Connected to guild: {guild.name} (ID: {guild.id}) with {guild.member_count} members")
    
    # Set bot presence
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening,
        name=f"{COMMAND_PREFIX}help"
    ))

@bot.event
async def on_disconnect():
    """Event triggered when the bot disconnects from Discord"""
    logger.warning("Bot disconnected from Discord")

@bot.event
async def on_resumed():
    """Event triggered when the bot reconnects after a disconnect"""
    logger.info("Bot connection resumed")

@bot.event
async def on_guild_join(guild):
    """Event triggered when the bot joins a new guild (server)"""
    logger.info(f"Bot joined new guild: {guild.name} (ID: {guild.id}) with {guild.member_count} members")
    
    # Find the system channel or the first text channel to send a welcome message
    target_channel = guild.system_channel or next((channel for channel in guild.text_channels
                                                if channel.permissions_for(guild.me).send_messages), None)
    
    if target_channel:
        embed = discord.Embed(
            title="AccountME Bot",
            description="Thanks for adding me to your server! I'm an accounting and inventory management bot for Trapper Dan Clothing.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Getting Started",
            value=f"Use `{COMMAND_PREFIX}help` to see available commands.",
            inline=False
        )
        embed.set_footer(text="AccountME Bot | Accounting & Inventory Management")
        
        await target_channel.send(embed=embed)

@bot.event
async def on_guild_remove(guild):
    """Event triggered when the bot is removed from a guild (server)"""
    logger.info(f"Bot removed from guild: {guild.name} (ID: {guild.id})")

@bot.event
async def on_message(message):
    """Event triggered when a message is sent in a channel the bot can see"""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Process commands if the message starts with the command prefix
    if message.content.startswith(COMMAND_PREFIX):
        await bot.process_commands(message)
        return
    
    # For now, we don't need to process other messages
    # This can be expanded later for natural language processing

# Load cogs (extensions)
async def load_extensions():
    """Load all cog extensions from the cogs directory"""
    logger.info("Loading extensions...")
    
    # Get the cogs directory path
    cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
    
    # Check if the directory exists
    if not os.path.exists(cogs_dir):
        logger.warning(f"Cogs directory not found: {cogs_dir}")
        return
    
    # Load all Python files in the cogs directory
    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and not filename.startswith("_"):
            extension_name = f"bot.cogs.{filename[:-3]}"
            try:
                await bot.load_extension(extension_name)
                logger.info(f"Loaded extension: {extension_name}")
            except Exception as e:
                logger.error(f"Failed to load extension {extension_name}: {e}")

async def graceful_shutdown():
    """Perform a graceful shutdown of the bot"""
    logger.info("Performing graceful shutdown...")
    
    # Close the bot connection
    if not bot.is_closed():
        await bot.close()
    
    # Clean up the image processor
    if image_processor:
        await image_processor.close()
        logger.info("Image processor closed")
    
    # Close the database manager
    if db_manager:
        db_manager.close()
        logger.info("Database manager closed")
    
    logger.info("Bot has been shut down")

async def main():
    """Main function to start the bot"""
    try:
        global image_processor, db_manager, report_generator
        
        logger.info("Starting AccountME Discord Bot...")
        
        # Ensure required environment variables are set
        if not TOKEN:
            logger.error("DISCORD_TOKEN environment variable is not set!")
            return
        
        # Ensure data directory exists
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f"Ensured data directory exists at {data_dir}")
        
        # Initialize database manager
        db_path = os.getenv("DATABASE_PATH", "data/database.db")
        db_manager = DatabaseManager(db_path)
        logger.info(f"Database manager initialized with database at {db_path}")
        
        # Make db_manager accessible to the bot
        bot.db_manager = db_manager
        
        # Initialize report generator
        reports_dir = os.getenv("REPORTS_DIR", "data/reports")
        reports_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), reports_dir)
        os.makedirs(reports_path, exist_ok=True)
        logger.info(f"Ensured reports directory exists at {reports_path}")
        report_generator = ReportGenerator(db_manager, reports_path)
        logger.info(f"Report generator initialized with reports directory at {reports_path}")
        
        # Make report_generator accessible to the bot
        bot.report_generator = report_generator
        
        # Initialize image processor
        image_processor = ImageProcessor()
        logger.info("Image processor initialized")
        
        # Load extensions (cogs)
        await load_extensions()
        
        # Set up signal handlers for graceful shutdown
        try:
            import signal
            
            # Define signal handlers
            def signal_handler(sig, frame):
                logger.info(f"Received signal {sig}, initiating shutdown...")
                asyncio.create_task(graceful_shutdown())
            
            # Register signal handlers
            for sig in (signal.SIGINT, signal.SIGTERM):
                signal.signal(sig, signal_handler)
                
            logger.info("Signal handlers registered for graceful shutdown")
        except (ImportError, AttributeError):
            logger.warning("Signal handling not available on this platform")
        
        # Start the bot
        logger.info("Connecting to Discord...")
        await bot.start(TOKEN)
    except Exception as e:
        logger.critical(f"Fatal error in main function: {str(e)}")
        logger.exception("Exception details:")
    finally:
        # Ensure we always attempt to close the bot connection
        if not bot.is_closed():
            await bot.close()
            logger.info("Bot connection closed")

# Entry point that handles running the async main function
def run_bot():
    """Run the bot using asyncio"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
    except Exception as e:
        logger.critical(f"Unhandled exception in run_bot: {str(e)}")
        logger.exception("Exception details:")

if __name__ == "__main__":
    run_bot()