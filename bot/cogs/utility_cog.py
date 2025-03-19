"""
Utility commands for the AccountME Discord Bot
Includes general-purpose commands for all users
"""

import discord
from discord.ext import commands
import logging
import platform
import time
from datetime import datetime

logger = logging.getLogger("accountme_bot.utility_cog")

class UtilityCog(commands.Cog, name="Utility"):
    """General utility commands for all users"""
    
    def __init__(self, bot):
        self.bot = bot
        self.start_time = datetime.now()
    
    @commands.command(name="ping")
    async def ping_command(self, ctx):
        """Check the bot's response time"""
        start_time = time.time()
        message = await ctx.send("Pinging...")
        end_time = time.time()
        
        api_latency = round(self.bot.latency * 1000)
        response_time = round((end_time - start_time) * 1000)
        
        embed = discord.Embed(
            title="🏓 Pong!",
            color=discord.Color.green()
        )
        embed.add_field(name="API Latency", value=f"{api_latency}ms", inline=True)
        embed.add_field(name="Response Time", value=f"{response_time}ms", inline=True)
        
        await message.edit(content=None, embed=embed)
    
    @commands.command(name="info")
    async def info_command(self, ctx):
        """Display information about the bot"""
        embed = discord.Embed(
            title="AccountME Bot Information",
            description="A Discord-based accounting bot for Trapper Dan Clothing",
            color=discord.Color.blue()
        )
        
        # Bot information
        embed.add_field(
            name="Bot Info",
            value=f"**Name:** {self.bot.user.name}\n"
                  f"**ID:** {self.bot.user.id}\n"
                  f"**Created:** {self.bot.user.created_at.strftime('%Y-%m-%d')}\n"
                  f"**Uptime:** {self._get_uptime()}",
            inline=False
        )
        
        # System information
        embed.add_field(
            name="System Info",
            value=f"**Python:** {platform.python_version()}\n"
                  f"**discord.py:** {discord.__version__}\n"
                  f"**Platform:** {platform.system()} {platform.release()}",
            inline=False
        )
        
        # Usage information
        embed.add_field(
            name="Usage",
            value=f"Use `{ctx.prefix}help` to see available commands",
            inline=False
        )
        
        # Set footer
        embed.set_footer(text="AccountME Bot | Accounting & Inventory Management")
        
        # Set thumbnail to bot's avatar if available
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="invite")
    async def invite_command(self, ctx):
        """Get an invite link for the bot"""
        # This assumes the bot has the applications.commands scope as well
        permissions = discord.Permissions(
            read_messages=True,
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True
        )
        
        invite_url = discord.utils.oauth_url(
            client_id=self.bot.user.id,
            permissions=permissions,
            scopes=("bot", "applications.commands")
        )
        
        embed = discord.Embed(
            title="Invite AccountME Bot",
            description="Use the link below to add the bot to your server:",
            color=discord.Color.blue()
        )
        embed.add_field(name="Invite Link", value=f"[Click Here]({invite_url})", inline=False)
        
        await ctx.send(embed=embed)
    
    def _get_uptime(self):
        """Calculate and format the bot's uptime"""
        delta = datetime.now() - self.start_time
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{days}d {hours}h {minutes}m {seconds}s"

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(UtilityCog(bot))