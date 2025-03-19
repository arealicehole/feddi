"""
Admin commands for the AccountME Discord Bot
Includes system-level commands for bot management
"""

import discord
from discord.ext import commands
import logging
import os
from datetime import datetime

logger = logging.getLogger("accountme_bot.admin_cog")

class AdminCog(commands.Cog, name="Admin"):
    """Administrative commands for bot management"""
    
    def __init__(self, bot):
        self.bot = bot
        self._last_member = None
    
    @commands.command(name="status")
    @commands.has_permissions(administrator=True)
    async def status_command(self, ctx):
        """Display bot status information"""
        embed = discord.Embed(
            title="AccountME Bot Status",
            description="Current system status information",
            color=discord.Color.blue()
        )
        
        # Add bot information
        embed.add_field(
            name="Bot Info", 
            value=f"Name: {self.bot.user.name}\n"
                  f"ID: {self.bot.user.id}\n"
                  f"Latency: {round(self.bot.latency * 1000)}ms", 
            inline=False
        )
        
        # Add server information
        embed.add_field(
            name="Server Info", 
            value=f"Servers: {len(self.bot.guilds)}\n"
                  f"Users: {sum(g.member_count for g in self.bot.guilds)}", 
            inline=False
        )
        
        # Add uptime information (would need to track start time elsewhere)
        embed.add_field(
            name="System Info", 
            value=f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="backup")
    @commands.has_permissions(administrator=True)
    async def backup_command(self, ctx):
        """Manually trigger a database backup"""
        # This is a placeholder - actual backup functionality will be implemented later
        await ctx.send("⏳ Backup initiated... (This is a placeholder - actual backup functionality will be implemented in Phase 5)")
    
    @commands.command(name="shutdown")
    @commands.has_permissions(administrator=True)
    async def shutdown_command(self, ctx):
        """Shutdown the bot (admin only)"""
        await ctx.send("⚠️ Shutting down bot...")
        logger.info(f"Bot shutdown initiated by {ctx.author.name} (ID: {ctx.author.id})")
        await self.bot.close()
    
    @status_command.error
    @backup_command.error
    @shutdown_command.error
    async def admin_command_error(self, ctx, error):
        """Error handler for admin commands"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
        else:
            await ctx.send(f"❌ An error occurred: {str(error)}")
            logger.error(f"Error in admin command: {str(error)}")

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(AdminCog(bot))