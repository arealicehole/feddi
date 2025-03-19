"""
Event logging system for the AccountME Discord Bot
Logs important Discord events for monitoring and debugging
"""

import discord
from discord.ext import commands
import logging
from datetime import datetime

logger = logging.getLogger("accountme_bot.event_logger")

class EventLoggerCog(commands.Cog, name="Event Logger"):
    """Logs important Discord events for monitoring and debugging"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_command(self, ctx):
        """Log when a command is invoked"""
        logger.info(
            f"Command '{ctx.command.qualified_name}' invoked by {ctx.author} (ID: {ctx.author.id}) "
            f"in {ctx.guild.name if ctx.guild else 'DM'} "
            f"(Channel: {ctx.channel.name if hasattr(ctx.channel, 'name') else 'DM'})"
        )
    
    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        """Log when a command completes successfully"""
        logger.info(
            f"Command '{ctx.command.qualified_name}' completed successfully for {ctx.author} (ID: {ctx.author.id})"
        )
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """Log when a channel is created"""
        logger.info(
            f"Channel created: {channel.name} (ID: {channel.id}) in {channel.guild.name} (ID: {channel.guild.id})"
        )
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Log when a channel is deleted"""
        logger.info(
            f"Channel deleted: {channel.name} (ID: {channel.id}) in {channel.guild.name} (ID: {channel.guild.id})"
        )
    
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        """Log when a channel is updated"""
        if before.name != after.name:
            logger.info(
                f"Channel renamed: {before.name} -> {after.name} (ID: {after.id}) "
                f"in {after.guild.name} (ID: {after.guild.id})"
            )
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Log when a member joins a guild"""
        logger.info(
            f"Member joined: {member.name}#{member.discriminator} (ID: {member.id}) "
            f"joined {member.guild.name} (ID: {member.guild.id})"
        )
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Log when a member leaves a guild"""
        logger.info(
            f"Member left: {member.name}#{member.discriminator} (ID: {member.id}) "
            f"left {member.guild.name} (ID: {member.guild.id})"
        )
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        """Log when a role is created"""
        logger.info(
            f"Role created: {role.name} (ID: {role.id}) in {role.guild.name} (ID: {role.guild.id})"
        )
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        """Log when a role is deleted"""
        logger.info(
            f"Role deleted: {role.name} (ID: {role.id}) in {role.guild.name} (ID: {role.guild.id})"
        )
    
    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        """Log when a role is updated"""
        if before.name != after.name:
            logger.info(
                f"Role renamed: {before.name} -> {after.name} (ID: {after.id}) "
                f"in {after.guild.name} (ID: {after.guild.id})"
            )
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Log when a member's voice state changes"""
        if before.channel != after.channel:
            if after.channel:
                if not before.channel:
                    logger.info(
                        f"Member joined voice: {member.name}#{member.discriminator} (ID: {member.id}) "
                        f"joined voice channel {after.channel.name} (ID: {after.channel.id})"
                    )
                else:
                    logger.info(
                        f"Member moved voice: {member.name}#{member.discriminator} (ID: {member.id}) "
                        f"moved from {before.channel.name} to {after.channel.name}"
                    )
            else:
                logger.info(
                    f"Member left voice: {member.name}#{member.discriminator} (ID: {member.id}) "
                    f"left voice channel {before.channel.name} (ID: {before.channel.id})"
                )
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Log when a message is edited"""
        # Skip bot messages and when content didn't change
        if before.author.bot or before.content == after.content:
            return
            
        # Log the edit
        logger.info(
            f"Message edited: {before.author.name}#{before.author.discriminator} (ID: {before.author.id}) "
            f"in {before.guild.name if before.guild else 'DM'} "
            f"(Channel: {before.channel.name if hasattr(before.channel, 'name') else 'DM'})"
        )
    
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Log when a message is deleted"""
        # Skip bot messages
        if message.author.bot:
            return
            
        # Log the deletion
        logger.info(
            f"Message deleted: from {message.author.name}#{message.author.discriminator} (ID: {message.author.id}) "
            f"in {message.guild.name if message.guild else 'DM'} "
            f"(Channel: {message.channel.name if hasattr(message.channel, 'name') else 'DM'})"
        )

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(EventLoggerCog(bot))