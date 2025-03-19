"""
Unit tests for the HelpCog
"""

import pytest
import discord
from discord.ext import commands
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add the bot directory to the path so we can import the cog
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import the cog
from bot.cogs.help_cog import HelpCog

@pytest.fixture
def mock_bot():
    """Create a mock bot instance for testing"""
    bot = MagicMock(spec=commands.Bot)
    bot.remove_command = MagicMock()
    bot.commands = []
    bot.get_command = MagicMock()
    return bot

@pytest.fixture
def help_cog(mock_bot):
    """Create a HelpCog instance for testing"""
    return HelpCog(mock_bot)

@pytest.fixture
def mock_ctx():
    """Create a mock context for testing commands"""
    ctx = MagicMock()
    ctx.send = AsyncMock()
    ctx.prefix = "!"
    
    # Create a mock message
    message = MagicMock()
    message.content = "!help"
    ctx.message = message
    
    return ctx

@pytest.mark.asyncio
async def test_help_command_no_args(help_cog, mock_ctx, mock_bot):
    """Test the help command with no arguments"""
    # Create some mock commands
    admin_command = MagicMock(spec=commands.Command)
    admin_command.name = "admin"
    admin_command.hidden = False
    admin_command.cog_name = "Admin"
    
    inventory_command = MagicMock(spec=commands.Command)
    inventory_command.name = "inventory"
    inventory_command.hidden = False
    inventory_command.cog_name = "Inventory"
    
    hidden_command = MagicMock(spec=commands.Command)
    hidden_command.name = "hidden"
    hidden_command.hidden = True
    hidden_command.cog_name = "Admin"
    
    # Add commands to the bot
    mock_bot.commands = [admin_command, inventory_command, hidden_command]
    
    # Call the help command method directly
    await help_cog.help_command(help_cog, mock_ctx)
    
    # Verify that ctx.send was called with an embed
    mock_ctx.send.assert_called_once()
    args, kwargs = mock_ctx.send.call_args
    assert 'embed' in kwargs
    
    # Check the embed content
    embed = kwargs['embed']
    assert isinstance(embed, discord.Embed)
    assert "AccountME Bot Help" in embed.title
    
    # Check that the embed has fields for each category
    field_names = [field.name for field in embed.fields]
    assert "📁 Admin" in field_names
    assert "📁 Inventory" in field_names
    
    # Check that the hidden command is not included
    admin_field = next(field for field in embed.fields if field.name == "📁 Admin")
    assert "!hidden" not in admin_field.value
    assert "!admin" in admin_field.value

@pytest.mark.asyncio
async def test_help_command_with_command(help_cog, mock_ctx, mock_bot):
    """Test the help command with a specific command"""
    # Create a mock command
    command = MagicMock(spec=commands.Command)
    command.name = "test"
    command.hidden = False
    command.help = "Test command help text"
    command.signature = "<arg1> [arg2]"
    command.aliases = ["t", "tst"]
    command.cog_name = "Test"
    
    # Set up the mock bot to return our command
    mock_bot.get_command.return_value = command
    
    # Call the help command method directly with a command name
    mock_ctx.message.content = "!help test"
    await help_cog._show_command_help(mock_ctx, "test")
    
    # Verify that ctx.send was called with an embed
    mock_ctx.send.assert_called_once()
    args, kwargs = mock_ctx.send.call_args
    assert 'embed' in kwargs
    
    # Check the embed content
    embed = kwargs['embed']
    assert isinstance(embed, discord.Embed)
    assert "Command: !test" in embed.title
    assert "Test command help text" in embed.description
    
    # Check the usage field
    usage_field = next(field for field in embed.fields if field.name == "Usage")
    assert "!test <arg1> [arg2]" in usage_field.value
    
    # Check the aliases field
    aliases_field = next(field for field in embed.fields if field.name == "Aliases")
    assert "!t" in aliases_field.value
    assert "!tst" in aliases_field.value
    
    # Check the category field
    category_field = next(field for field in embed.fields if field.name == "Category")
    assert "Test" in category_field.value

@pytest.mark.asyncio
async def test_help_command_command_not_found(help_cog, mock_ctx, mock_bot):
    """Test the help command with a non-existent command"""
    # Set up the mock bot to return None for the command
    mock_bot.get_command.return_value = None
    
    # Call the help command method directly with a non-existent command name
    mock_ctx.message.content = "!help nonexistent"
    await help_cog._show_command_help(mock_ctx, "nonexistent")
    
    # Verify that ctx.send was called with an embed
    mock_ctx.send.assert_called_once()
    args, kwargs = mock_ctx.send.call_args
    assert 'embed' in kwargs
    
    # Check the embed content
    embed = kwargs['embed']
    assert isinstance(embed, discord.Embed)
    assert "Command Not Found" in embed.title
    assert "No command called `nonexistent` was found." in embed.description
    assert embed.color == discord.Color.red()

@pytest.mark.asyncio
async def test_help_command_hidden_command(help_cog, mock_ctx, mock_bot):
    """Test the help command with a hidden command"""
    # Create a mock hidden command
    command = MagicMock(spec=commands.Command)
    command.name = "hidden"
    command.hidden = True
    
    # Set up the mock bot to return our hidden command
    mock_bot.get_command.return_value = command
    
    # Call the help command method directly with a hidden command name
    mock_ctx.message.content = "!help hidden"
    await help_cog._show_command_help(mock_ctx, "hidden")
    
    # Verify that ctx.send was called with an embed
    mock_ctx.send.assert_called_once()
    args, kwargs = mock_ctx.send.call_args
    assert 'embed' in kwargs
    
    # Check the embed content
    embed = kwargs['embed']
    assert isinstance(embed, discord.Embed)
    assert "Command Not Found" in embed.title
    assert "No command called `hidden` was found." in embed.description
    assert embed.color == discord.Color.red()

@pytest.mark.asyncio
async def test_setup(mock_bot):
    """Test the setup function"""
    # Import the setup function
    from bot.cogs.help_cog import setup
    
    # Mock the add_cog method
    mock_bot.add_cog = AsyncMock()
    
    # Call the setup function
    await setup(mock_bot)
    
    # Verify that add_cog was called with a HelpCog instance
    mock_bot.add_cog.assert_called_once()
    args, kwargs = mock_bot.add_cog.call_args
    assert isinstance(args[0], HelpCog)