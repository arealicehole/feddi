"""
Unit tests for the Discord bot functionality
"""

import os
import pytest
import discord
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from discord.ext import commands
import sys
import importlib

# Add the bot directory to the path so we can import the main module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import the bot module
from bot import main

@pytest.fixture
def mock_bot():
    """Create a mock bot instance for testing"""
    # Create a mock bot with the same attributes as the real bot
    bot = MagicMock(spec=commands.Bot)
    bot.user = MagicMock()
    bot.user.name = "TestBot"
    bot.user.id = 123456789
    bot.guilds = []
    bot.is_closed = MagicMock(return_value=False)
    bot.close = AsyncMock()
    bot.start = AsyncMock()
    bot.load_extension = AsyncMock()
    bot.change_presence = AsyncMock()
    
    return bot

@pytest.mark.asyncio
async def test_on_ready(mock_bot):
    """Test the on_ready event handler"""
    # Create a test guild
    guild = MagicMock()
    guild.name = "Test Guild"
    guild.id = 987654321
    guild.member_count = 10
    mock_bot.guilds = [guild]
    
    # Call the on_ready event handler
    with patch('bot.main.bot', mock_bot):
        await main.on_ready()
    
    # Verify that the bot's presence was changed
    mock_bot.change_presence.assert_called_once()
    
    # Verify that startup_time was set
    assert main.startup_time is not None

@pytest.mark.asyncio
async def test_on_guild_join(mock_bot):
    """Test the on_guild_join event handler"""
    # Create a test guild
    guild = MagicMock()
    guild.name = "Test Guild"
    guild.id = 987654321
    guild.member_count = 10
    
    # Create a mock system channel
    system_channel = AsyncMock()
    system_channel.send = AsyncMock()
    guild.system_channel = system_channel
    
    # Mock the bot's permissions in the guild
    guild.me = MagicMock()
    
    # Call the on_guild_join event handler
    with patch('bot.main.bot', mock_bot):
        await main.on_guild_join(guild)
    
    # Verify that a welcome message was sent
    system_channel.send.assert_called_once()
    
    # Check that the sent message was an embed
    args, kwargs = system_channel.send.call_args
    assert 'embed' in kwargs
    embed = kwargs['embed']
    assert isinstance(embed, discord.Embed)
    assert "AccountME Bot" in embed.title

@pytest.mark.asyncio
async def test_on_message(mock_bot):
    """Test the on_message event handler"""
    # Create a mock message
    message = MagicMock()
    message.author = MagicMock()
    message.content = "!help"
    
    # Set up the mock bot to process commands
    mock_bot.process_commands = AsyncMock()
    
    # Test case 1: Message from the bot itself
    message.author = mock_bot.user
    with patch('bot.main.bot', mock_bot):
        await main.on_message(message)
    
    # Verify that process_commands was not called
    mock_bot.process_commands.assert_not_called()
    
    # Test case 2: Message from another user with command prefix
    message.author = MagicMock()  # Different from bot.user
    message.content = "!help"
    with patch('bot.main.bot', mock_bot):
        with patch('bot.main.COMMAND_PREFIX', "!"):
            await main.on_message(message)
    
    # Verify that process_commands was called
    mock_bot.process_commands.assert_called_once_with(message)
    
    # Reset the mock
    mock_bot.process_commands.reset_mock()
    
    # Test case 3: Message from another user without command prefix
    message.content = "Hello bot"
    with patch('bot.main.bot', mock_bot):
        with patch('bot.main.COMMAND_PREFIX', "!"):
            await main.on_message(message)
    
    # Verify that process_commands was not called
    mock_bot.process_commands.assert_not_called()

@pytest.mark.asyncio
async def test_load_extensions(mock_bot):
    """Test the load_extensions function"""
    # Create a mock for os.path.exists and os.listdir
    with patch('os.path.exists', return_value=True), \
         patch('os.listdir', return_value=['admin_cog.py', 'help_cog.py', '_ignored.py']), \
         patch('bot.main.bot', mock_bot):
        
        await main.load_extensions()
    
    # Verify that load_extension was called for each valid cog
    assert mock_bot.load_extension.call_count == 2
    mock_bot.load_extension.assert_any_call('bot.cogs.admin_cog')
    mock_bot.load_extension.assert_any_call('bot.cogs.help_cog')

@pytest.mark.asyncio
async def test_graceful_shutdown(mock_bot):
    """Test the graceful_shutdown function"""
    with patch('bot.main.bot', mock_bot):
        await main.graceful_shutdown()
    
    # Verify that bot.close was called
    mock_bot.close.assert_called_once()

@pytest.mark.asyncio
async def test_main_function(mock_bot):
    """Test the main function"""
    # Mock the environment variables
    with patch('bot.main.TOKEN', 'fake_token'), \
         patch('bot.main.bot', mock_bot), \
         patch('bot.main.load_extensions', AsyncMock()), \
         patch('bot.main.graceful_shutdown', AsyncMock()):
        
        # Call the main function
        await main.main()
    
    # Verify that the bot was started
    mock_bot.start.assert_called_once_with('fake_token')