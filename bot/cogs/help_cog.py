"""
Help command system for the AccountME Discord Bot
Provides a custom help command with categorized commands
"""

import discord
from discord.ext import commands
import logging

logger = logging.getLogger("accountme_bot.help_cog")

class HelpCog(commands.Cog, name="Help"):
    """Custom help command implementation"""
    
    def __init__(self, bot):
        self.bot = bot
        # Remove the default help command
        self.bot.remove_command('help')
    
    @commands.command(name="help")
    async def help_command(self, ctx, command_name=None):
        """
        Show help information for commands
        
        Usage:
        !help - Show all command categories
        !help <command> - Show help for a specific command
        """
        prefix = ctx.prefix
        
        # If a specific command is requested
        if command_name:
            return await self._show_command_help(ctx, command_name)
        
        # Otherwise show the main help menu
        embed = discord.Embed(
            title="AccountME Bot Help",
            description=f"Use `{prefix}help <command>` for more information about a command.\n"
                       f"Use `{prefix}help <category>` for more information about a category.",
            color=discord.Color.blue()
        )
        
        # Group commands by cog (category)
        command_categories = {}
        for command in self.bot.commands:
            if command.hidden:
                continue
                
            category = command.cog_name or "No Category"
            if category not in command_categories:
                command_categories[category] = []
            command_categories[category].append(command)
        
        # Add fields for each category
        for category, commands_list in sorted(command_categories.items()):
            # Skip empty categories
            if not commands_list:
                continue
                
            # Create a list of command names
            command_names = [f"`{prefix}{cmd.name}`" for cmd in commands_list]
            
            # Add the field
            embed.add_field(
                name=f"📁 {category}",
                value=", ".join(command_names),
                inline=False
            )
        
        # Add footer with additional info
        embed.set_footer(text="AccountME Bot | Accounting & Inventory Management")
        
        await ctx.send(embed=embed)
    
    async def _show_command_help(self, ctx, command_name):
        """Show help for a specific command"""
        prefix = ctx.prefix
        
        # Try to find the command
        command = self.bot.get_command(command_name)
        
        # If command not found
        if not command or command.hidden:
            embed = discord.Embed(
                title="Command Not Found",
                description=f"No command called `{command_name}` was found.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Create embed for command help
        embed = discord.Embed(
            title=f"Command: {prefix}{command.name}",
            description=command.help or "No description available.",
            color=discord.Color.blue()
        )
        
        # Add command signature (usage)
        signature = command.signature
        embed.add_field(
            name="Usage",
            value=f"`{prefix}{command.name} {signature}`",
            inline=False
        )
        
        # Add aliases if any
        if command.aliases:
            embed.add_field(
                name="Aliases",
                value=", ".join([f"`{prefix}{alias}`" for alias in command.aliases]),
                inline=False
            )
        
        # Add category
        if command.cog_name:
            embed.add_field(
                name="Category",
                value=command.cog_name,
                inline=False
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(HelpCog(bot))