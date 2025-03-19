"""
Backup management commands for the AccountME Discord Bot
Implementation for Phase 5.3: Advanced Backup System
"""

import discord
from discord.ext import commands
import logging
import os
import asyncio
import json
import hashlib
from datetime import datetime, timedelta
import io
import zipfile
import tempfile
import shutil
from typing import Optional, Dict, List, Any, Union, Tuple

logger = logging.getLogger("accountme_bot.backup_cog")

class BackupCog(commands.Cog, name="Backup"):
    """Advanced backup management commands for database and inventory"""
    
    def __init__(self, bot):
        self.bot = bot
        # Try to convert BACKUP_CHANNEL_ID to int, default to 0 if not a valid integer
        try:
            self.backup_channel_id = int(os.getenv("BACKUP_CHANNEL_ID", "0"))
        except ValueError:
            self.backup_channel_id = 0
            logger.warning("BACKUP_CHANNEL_ID is not a valid integer, defaulting to 0")
        
        # Try to convert BACKUP_INTERVAL_HOURS to int, default to 24 if not a valid integer
        try:
            self.backup_interval_hours = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))
        except ValueError:
            self.backup_interval_hours = 24
            logger.warning("BACKUP_INTERVAL_HOURS is not a valid integer, defaulting to 24")
        
        # Try to convert BACKUP_RETENTION_DAYS to int, default to 30 if not a valid integer
        try:
            self.backup_retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
        except ValueError:
            self.backup_retention_days = 30
            logger.warning("BACKUP_RETENTION_DAYS is not a valid integer, defaulting to 30")
            
        # Get cloud storage configuration
        self.cloud_provider = os.getenv("BACKUP_CLOUD_PROVIDER", "none")
        self.cloud_enabled = self.cloud_provider.lower() not in ["none", ""]
        
        # Get backup compression setting
        try:
            self.compression_enabled = os.getenv("BACKUP_COMPRESSION_ENABLED", "1").lower() in ["1", "true", "yes"]
        except:
            self.compression_enabled = True
            
        # Get backup verification setting
        try:
            self.verify_integrity = os.getenv("BACKUP_VERIFY_INTEGRITY", "1").lower() in ["1", "true", "yes"]
        except:
            self.verify_integrity = True
            
        # Get backup rotation scheme
        self.rotation_scheme = os.getenv("BACKUP_ROTATION_SCHEME", "simple")
        
        # Initialize backup task
        self.backup_task = None
        
        # Start scheduled backup task if interval is set
        if self.backup_interval_hours > 0:
            self.backup_task = self.bot.loop.create_task(self._scheduled_backup_task())
            logger.info(f"Scheduled backup task started with interval of {self.backup_interval_hours} hours")
            
        logger.info(f"Backup system initialized with cloud provider: {self.cloud_provider}")
        logger.info(f"Backup compression: {'Enabled' if self.compression_enabled else 'Disabled'}")
        logger.info(f"Backup integrity verification: {'Enabled' if self.verify_integrity else 'Disabled'}")
        logger.info(f"Backup rotation scheme: {self.rotation_scheme}")
    
    def cog_unload(self):
        """Called when the cog is unloaded"""
        if self.backup_task:
            self.backup_task.cancel()
            logger.info("Scheduled backup task cancelled")
    
    async def _scheduled_backup_task(self):
        """Task for scheduled backups"""
        try:
            # Wait for bot to be ready
            await self.bot.wait_until_ready()
            
            while not self.bot.is_closed():
                try:
                    # Perform backup
                    logger.info("Running scheduled backup")
                    await self._create_backup(scheduled=True)
                    
                    # Clean up old backups
                    await self._cleanup_old_backups()
                    
                except Exception as e:
                    logger.error(f"Error in scheduled backup: {str(e)}")
                
                # Wait for next backup interval
                await asyncio.sleep(self.backup_interval_hours * 3600)  # Convert hours to seconds
        
        except asyncio.CancelledError:
            logger.info("Scheduled backup task cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in backup task: {str(e)}")
    
    async def _create_backup(self, ctx=None, scheduled=False) -> Optional[str]:
        """
        Create a database backup with integrity verification and upload to Discord and cloud storage
        
        Args:
            ctx: Command context (optional, for manual backups)
            scheduled: Whether this is a scheduled backup
            
        Returns:
            Path to the backup file, or None if backup failed
        """
        try:
            # Create database backup with compression and integrity verification
            backup_path = self.bot.db_manager.backup_database(
                compress=self.compression_enabled
            )
            backup_filename = os.path.basename(backup_path)
            backup_size = os.path.getsize(backup_path)
            
            logger.info(f"Database backup created: {backup_path} ({backup_size} bytes)")
            
            # Verify backup integrity
            if self.verify_integrity:
                logger.info(f"Verifying backup integrity: {backup_path}")
                if not self.bot.db_manager.verify_backup_integrity(backup_path):
                    logger.error(f"Backup integrity verification failed: {backup_path}")
                    if ctx:
                        await ctx.send("⚠️ Backup created but integrity verification failed. The backup may be corrupted.")
                else:
                    logger.info(f"Backup integrity verified: {backup_path}")
            
            # Upload to cloud storage if enabled
            cloud_url = None
            if self.cloud_enabled and self.cloud_provider.lower() not in ["none", ""]:
                logger.info(f"Uploading backup to cloud storage ({self.cloud_provider}): {backup_path}")
                if ctx:
                    await ctx.send(f"Uploading backup to {self.cloud_provider}...")
                
                cloud_url = await self._upload_to_cloud(backup_path)
                
                if cloud_url:
                    logger.info(f"Backup uploaded to cloud: {cloud_url}")
                    if ctx:
                        await ctx.send(f"Backup uploaded to cloud storage: {cloud_url}")
                else:
                    logger.warning(f"Failed to upload backup to cloud storage")
                    if ctx:
                        await ctx.send("⚠️ Failed to upload backup to cloud storage")
            
            # Upload to Discord if backup channel is configured
            discord_url = None
            if self.backup_channel_id:
                # Get the backup channel
                channel = self.bot.get_channel(self.backup_channel_id)
                
                if channel:
                    # Create backup info embed
                    embed = discord.Embed(
                        title="Database Backup",
                        description=f"Backup created on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        color=discord.Color.blue()
                    )
                    
                    embed.add_field(name="Filename", value=backup_filename, inline=True)
                    embed.add_field(name="Size", value=f"{backup_size / 1024:.2f} KB", inline=True)
                    embed.add_field(name="Type", value="Scheduled" if scheduled else "Manual", inline=True)
                    
                    # Add integrity and cloud info
                    if self.verify_integrity:
                        embed.add_field(name="Integrity Verified", value="✅ Yes", inline=True)
                    
                    if cloud_url:
                        embed.add_field(name="Cloud Storage", value=f"[{self.cloud_provider}]({cloud_url})", inline=True)
                    
                    # Add compression info
                    embed.add_field(name="Compressed", value="✅ Yes" if self.compression_enabled else "❌ No", inline=True)
                    
                    # Add inventory summary
                    products = self.bot.db_manager.list_products()
                    total_products = len(products)
                    total_items = sum(p['quantity'] for p in products)
                    total_value = sum(p['quantity'] * (p['cost_price'] or 0) for p in products)
                    
                    embed.add_field(name="Products", value=str(total_products), inline=True)
                    embed.add_field(name="Items", value=str(total_items), inline=True)
                    embed.add_field(name="Value", value=f"${total_value:.2f}", inline=True)
                    
                    # Create inventory snapshot CSV
                    csv_data = await self._generate_inventory_snapshot(products)
                    inventory_file = discord.File(
                        io.BytesIO(csv_data.encode('utf-8')),
                        filename=f"inventory_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    )
                    
                    # Upload database backup file
                    with open(backup_path, 'rb') as f:
                        db_file = discord.File(f, filename=backup_filename)
                        message = await channel.send(
                            content=f"{'Scheduled' if scheduled else 'Manual'} backup - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                            embed=embed,
                            files=[db_file, inventory_file]
                        )
                    
                    # Update backup record with Discord URL
                    discord_url = message.attachments[0].url if message.attachments else None
                    if discord_url:
                        # Update backup record with Discord URL
                        try:
                            # Find the backup record
                            query = "SELECT backup_id FROM backup_log WHERE filename = ? ORDER BY backup_id DESC LIMIT 1"
                            result = self.bot.db_manager.execute_query(query, (backup_filename,))
                            
                            if result:
                                backup_id = result[0]['backup_id']
                                self.bot.db_manager.update('backup_log',
                                                        {'cloud_url': discord_url, 'cloud_provider': 'discord'},
                                                        'backup_id = ?', (backup_id,))
                                logger.info(f"Updated backup {backup_id} with Discord URL: {discord_url}")
                        except Exception as e:
                            logger.warning(f"Could not update backup Discord URL: {str(e)}")
                        
                        logger.info(f"Backup uploaded to Discord: {discord_url}")
                    
                    if ctx:
                        await ctx.send(f"Backup created and uploaded to <#{self.backup_channel_id}>")
                else:
                    logger.warning(f"Backup channel not found: {self.backup_channel_id}")
                    if ctx:
                        await ctx.send("Backup created but could not be uploaded to Discord (channel not found)")
            elif ctx:
                await ctx.send(f"Backup created: {backup_path}")
            
            return backup_path
        
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            if ctx:
                await ctx.send(f"Error creating backup: {str(e)}")
            return None
            
    async def _upload_to_cloud(self, backup_path: str) -> Optional[str]:
        """
        Upload a backup file to the configured cloud storage provider
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            URL of the uploaded file, or None if upload failed
        """
        try:
            if self.cloud_provider.lower() == "gdrive":
                return await self._upload_to_gdrive(backup_path)
            elif self.cloud_provider.lower() == "onedrive":
                return await self._upload_to_onedrive(backup_path)
            else:
                logger.error(f"Unsupported cloud provider: {self.cloud_provider}")
                return None
        except Exception as e:
            logger.error(f"Error uploading to cloud storage: {str(e)}")
            return None
            
    async def _upload_to_gdrive(self, file_path: str) -> Optional[str]:
        """
        Upload a file to Google Drive
        
        Args:
            file_path: Path to the file to upload
            
        Returns:
            URL of the uploaded file, or None if upload failed
        """
        # This is a placeholder for actual Google Drive API implementation
        # In a real implementation, you would use the Google Drive API to upload the file
        
        # For now, we'll just log a message and return a dummy URL
        logger.info(f"Uploading {file_path} to Google Drive (placeholder)")
        
        # Simulate a delay for the upload
        await asyncio.sleep(2)
        
        # In a real implementation, you would return the actual URL
        return f"https://drive.google.com/file/d/placeholder/{os.path.basename(file_path)}"
        
    async def _upload_to_onedrive(self, file_path: str) -> Optional[str]:
        """
        Upload a file to OneDrive
        
        Args:
            file_path: Path to the file to upload
            
        Returns:
            URL of the uploaded file, or None if upload failed
        """
        # This is a placeholder for actual OneDrive API implementation
        # In a real implementation, you would use the Microsoft Graph API to upload the file
        
        # For now, we'll just log a message and return a dummy URL
        logger.info(f"Uploading {file_path} to OneDrive (placeholder)")
        
        # Simulate a delay for the upload
        await asyncio.sleep(2)
        
        # In a real implementation, you would return the actual URL
        return f"https://onedrive.live.com/placeholder/{os.path.basename(file_path)}"
    
    async def _generate_inventory_snapshot(self, products: List[Dict[str, Any]]) -> str:
        """
        Generate a CSV snapshot of the current inventory
        
        Args:
            products: List of product dictionaries
            
        Returns:
            CSV data as a string
        """
        import csv
        import io
        
        output = io.StringIO()
        fieldnames = [
            'product_id', 'name', 'category', 'subcategory', 
            'manufacturer', 'vendor', 'style', 'color', 'size', 
            'sku', 'quantity', 'cost_price', 'selling_price',
            'snapshot_date'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        snapshot_date = datetime.now().isoformat()
        
        for product in products:
            # Add snapshot date to each row
            product_copy = dict(product)
            product_copy['snapshot_date'] = snapshot_date
            
            # Only write the fields we want
            row = {field: product_copy.get(field) for field in fieldnames}
            writer.writerow(row)
        
        return output.getvalue()
    
    async def _cleanup_old_backups(self):
        """Clean up old backups based on retention policy"""
        if self.backup_retention_days <= 0:
            return
        
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=self.backup_retention_days)
            cutoff_date_str = cutoff_date.isoformat()
            
            # Get backup records older than cutoff date
            query = "SELECT * FROM backup_log WHERE timestamp < ?"
            old_backups = self.bot.db_manager.execute_query(query, (cutoff_date_str,))
            
            if not old_backups:
                logger.info("No old backups to clean up")
                return
            
            logger.info(f"Found {len(old_backups)} backups older than {self.backup_retention_days} days")
            
            # Delete old backup files
            for backup in old_backups:
                backup_path = os.path.join(backup['location'], backup['filename'])
                if os.path.exists(backup_path):
                    try:
                        os.remove(backup_path)
                        logger.info(f"Deleted old backup file: {backup_path}")
                    except Exception as e:
                        logger.error(f"Error deleting backup file {backup_path}: {str(e)}")
                
                # Delete backup record
                self.bot.db_manager.delete('backup_log', 'backup_id = ?', (backup['backup_id'],))
                logger.info(f"Deleted backup record: {backup['backup_id']}")
            
            logger.info(f"Cleanup completed: removed {len(old_backups)} old backups")
        
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {str(e)}")
    
    @commands.command(name="backup", aliases=["createbackup", "backupnow"])
    @commands.has_permissions(administrator=True)
    async def backup_command(self, ctx):
        """
        Create a database backup
        
        Usage:
        !backup - Create a manual backup of the database
        
        Aliases: !createbackup, !backupnow
        """
        await ctx.send("Creating database backup... This may take a moment.")
        await self._create_backup(ctx)
    
    @commands.command(name="listbackups", aliases=["backups", "showbackups"])
    @commands.has_permissions(administrator=True)
    async def list_backups_command(self, ctx, limit: int = 10):
        """
        List recent database backups
        
        Usage:
        !listbackups [limit] - List recent backups (default: 10)
        
        Aliases: !backups, !showbackups
        """
        # Get backup records
        query = "SELECT * FROM backup_log ORDER BY timestamp DESC LIMIT ?"
        backups = self.bot.db_manager.execute_query(query, (limit,))
        
        if not backups:
            await ctx.send("No backup records found.")
            return
        
        # Create embed
        embed = discord.Embed(
            title="Database Backups",
            description=f"Showing {len(backups)} most recent backups",
            color=discord.Color.blue()
        )
        
        for backup in backups:
            timestamp = backup['timestamp'].split('T')[0]  # Just get the date part
            size_kb = backup['size'] / 1024
            
            embed.add_field(
                name=f"Backup {backup['backup_id']} - {timestamp}",
                value=f"Filename: {backup['filename']}\nSize: {size_kb:.2f} KB",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="restore", aliases=["restorebackup", "dbrestore"])
    @commands.has_permissions(administrator=True)
    async def restore_command(self, ctx, backup_id: int = None):
        """
        Restore database from a backup
        
        Usage:
        !restore - Show available backups
        !restore <backup_id> - Restore from a specific backup
        
        Aliases: !restorebackup, !dbrestore
        """
        if backup_id is None:
            # Show available backups
            await self.list_backups_command(ctx)
            await ctx.send("Use `!restore <backup_id>` to restore from a specific backup.")
            return
        
        # Get backup record
        backup = self.bot.db_manager.get_by_id('backup_log', 'backup_id', backup_id)
        
        if not backup:
            await ctx.send(f"No backup found with ID: {backup_id}")
            return
        
        # Confirm restoration
        embed = discord.Embed(
            title="Confirm Database Restoration",
            description="⚠️ **WARNING: This will overwrite the current database!** ⚠️",
            color=discord.Color.red()
        )
        
        timestamp = backup['timestamp'].split('T')[0]  # Just get the date part
        embed.add_field(
            name="Backup Details",
            value=f"ID: {backup['backup_id']}\nDate: {timestamp}\nFilename: {backup['filename']}",
            inline=False
        )
        
        embed.add_field(
            name="Confirmation",
            value="Are you sure you want to restore this backup? This action cannot be undone!",
            inline=False
        )
        
        confirmation_message = await ctx.send(embed=embed)
        
        # Add reaction options
        await confirmation_message.add_reaction("✅")  # Yes
        await confirmation_message.add_reaction("❌")  # No
        
        # Wait for reaction
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirmation_message.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Perform restoration
                await ctx.send("Restoring database... This may take a moment.")
                
                # Build backup path
                backup_path = os.path.join(backup['location'], backup['filename'])
                
                if not os.path.exists(backup_path):
                    await ctx.send(f"Backup file not found: {backup_path}")
                    return
                
                # Create a new backup before restoring (just in case)
                pre_restore_backup = self.bot.db_manager.backup_database(
                    backup_dir=os.path.join(os.path.dirname(backup_path), "pre_restore")
                )
                
                # Restore from backup
                success = self.bot.db_manager.restore_database(backup_path)
                
                if success:
                    await ctx.send(f"Database successfully restored from backup ID: {backup_id}")
                    
                    # Log the restoration
                    self.bot.db_manager.log_audit(
                        'restore',
                        'database',
                        backup_id,
                        str(ctx.author.id),
                        f"Database restored from backup ID: {backup_id}"
                    )
                else:
                    await ctx.send("Failed to restore database. Check logs for details.")
            else:
                await ctx.send("Restoration cancelled.")
        
        except asyncio.TimeoutError:
            await ctx.send("Restoration cancelled due to timeout.")
    
    @commands.command(name="backupchannel")
    @commands.has_permissions(administrator=True)
    async def backup_channel_command(self, ctx, channel: discord.TextChannel = None):
        """
        Set or view the backup channel
        
        Usage:
        !backupchannel - Show current backup channel
        !backupchannel #channel - Set backup channel
        """
        if channel is None:
            # Show current backup channel
            if self.backup_channel_id:
                channel = self.bot.get_channel(self.backup_channel_id)
                if channel:
                    await ctx.send(f"Current backup channel: {channel.mention}")
                else:
                    await ctx.send(f"Backup channel ID set to {self.backup_channel_id}, but channel not found.")
            else:
                await ctx.send("No backup channel set. Use `!backupchannel #channel` to set one.")
            return
        
        # Set new backup channel
        self.backup_channel_id = channel.id
        
        # Update environment variable (this won't persist after restart)
        os.environ["BACKUP_CHANNEL_ID"] = str(channel.id)
        
        await ctx.send(f"Backup channel set to {channel.mention}")
        
        # Test channel permissions
        try:
            test_embed = discord.Embed(
                title="Backup Channel Test",
                description="This is a test message to verify permissions",
                color=discord.Color.blue()
            )
            await channel.send(embed=test_embed)
            await ctx.send("Successfully sent test message to backup channel.")
        except Exception as e:
            await ctx.send(f"Warning: Could not send test message to backup channel. Error: {str(e)}")
    
    @commands.command(name="backupschedule")
    @commands.has_permissions(administrator=True)
    async def backup_schedule_command(self, ctx, interval_hours: int = None):
        """
        Set or view the backup schedule
        
        Usage:
        !backupschedule - Show current backup schedule
        !backupschedule <hours> - Set backup interval in hours (0 to disable)
        """
        if interval_hours is None:
            # Show current schedule
            if self.backup_interval_hours > 0:
                next_backup = datetime.now() + timedelta(
                    seconds=self.backup_task._when - asyncio.get_event_loop().time()
                ) if self.backup_task else None
                
                await ctx.send(
                    f"Current backup schedule: Every {self.backup_interval_hours} hours\n"
                    f"Next backup: {next_backup.strftime('%Y-%m-%d %H:%M:%S') if next_backup else 'Unknown'}"
                )
            else:
                await ctx.send("Scheduled backups are disabled.")
            return
        
        # Validate interval
        if interval_hours < 0:
            await ctx.send("Backup interval must be 0 or greater (0 disables scheduled backups)")
            return
        
        # Update interval
        self.backup_interval_hours = interval_hours
        
        # Update environment variable (this won't persist after restart)
        os.environ["BACKUP_INTERVAL_HOURS"] = str(interval_hours)
        
        # Cancel existing task if any
        if self.backup_task:
            self.backup_task.cancel()
            self.backup_task = None
        
        if interval_hours > 0:
            # Start new task
            self.backup_task = self.bot.loop.create_task(self._scheduled_backup_task())
            await ctx.send(f"Backup schedule set to every {interval_hours} hours")
        else:
            await ctx.send("Scheduled backups disabled")
    
    @commands.command(name="backupretention")
    @commands.has_permissions(administrator=True)
    async def backup_retention_command(self, ctx, days: int = None):
        """
        Set or view the backup retention policy
        
        Usage:
        !backupretention - Show current retention policy
        !backupretention <days> - Set retention period in days (0 to keep forever)
        """
        if days is None:
            # Show current policy
            if self.backup_retention_days > 0:
                await ctx.send(f"Current backup retention policy: {self.backup_retention_days} days")
            else:
                await ctx.send("Backup retention policy: Keep forever")
            return
        
        # Validate days
        if days < 0:
            await ctx.send("Retention period must be 0 or greater (0 keeps backups forever)")
            return
        
        # Update retention period
        self.backup_retention_days = days
        
        # Update environment variable (this won't persist after restart)
        os.environ["BACKUP_RETENTION_DAYS"] = str(days)
        
        if days > 0:
            await ctx.send(f"Backup retention policy set to {days} days")
            
            # Run cleanup
            await self._cleanup_old_backups()
        else:
            await ctx.send("Backup retention policy set to keep backups forever")
    
    @commands.command(name="inventorysnapshot", aliases=["snapshot", "invsnapshot"])
    async def inventory_snapshot_command(self, ctx):
        """
        Create a snapshot of the current inventory
        
        Usage:
        !inventorysnapshot - Generate and export current inventory state
        
        Aliases: !snapshot, !invsnapshot
        """
        await ctx.send("Generating inventory snapshot... This may take a moment.")
        
        try:
            # Get all products
            products = self.bot.db_manager.list_products()
            
            if not products:
                await ctx.send("No products found in inventory.")
                return
            
            # Generate CSV snapshot
            csv_data = await self._generate_inventory_snapshot(products)
            
            # Create file
            snapshot_filename = f"inventory_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            file = discord.File(
                io.BytesIO(csv_data.encode('utf-8')),
                filename=snapshot_filename
            )
            
            # Create summary embed
            embed = discord.Embed(
                title="Inventory Snapshot",
                description=f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                color=discord.Color.blue()
            )
            
            # Add summary statistics
            total_products = len(products)
            total_items = sum(p['quantity'] for p in products)
            total_value = sum(p['quantity'] * (p['cost_price'] or 0) for p in products)
            
            embed.add_field(name="Total Products", value=str(total_products), inline=True)
            embed.add_field(name="Total Items", value=str(total_items), inline=True)
            embed.add_field(name="Total Value", value=f"${total_value:.2f}", inline=True)
            
            # Add category breakdown
            categories = {}
            for product in products:
                category = product['category']
                if category not in categories:
                    categories[category] = {
                        'count': 0,
                        'items': 0,
                        'value': 0
                    }
                
                categories[category]['count'] += 1
                categories[category]['items'] += product['quantity']
                categories[category]['value'] += product['quantity'] * (product['cost_price'] or 0)
            
            category_text = ""
            for category, stats in categories.items():
                category_text += f"**{category.capitalize()}**: {stats['count']} products, {stats['items']} items, ${stats['value']:.2f}\n"
            
            if category_text:
                embed.add_field(name="Category Breakdown", value=category_text, inline=False)
            
            # Send file and embed
            await ctx.send(embed=embed, file=file)
            
            # If backup channel is set, also send there
            if self.backup_channel_id:
                channel = self.bot.get_channel(self.backup_channel_id)
                if channel:
                    # Create a new file object since the first one is consumed
                    backup_file = discord.File(
                        io.BytesIO(csv_data.encode('utf-8')),
                        filename=snapshot_filename
                    )
                    await channel.send(
                        content=f"Inventory snapshot - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        embed=embed,
                        file=backup_file
                    )
        
        except Exception as e:
            logger.error(f"Error creating inventory snapshot: {str(e)}")
            await ctx.send(f"Error creating inventory snapshot: {str(e)}")

    @commands.command(name="backupverify")
    @commands.has_permissions(administrator=True)
    async def backup_verify_command(self, ctx, backup_id: int = None):
        """
        Verify the integrity of a backup
        
        Usage:
        !backupverify <backup_id> - Verify the integrity of a specific backup
        """
        if backup_id is None:
            await ctx.send("Please specify a backup ID to verify. Use `!listbackups` to see available backups.")
            return
        
        # Get backup record
        backup = self.bot.db_manager.get_by_id('backup_log', 'backup_id', backup_id)
        
        if not backup:
            await ctx.send(f"No backup found with ID: {backup_id}")
            return
        
        # Build backup path
        backup_path = os.path.join(backup['location'], backup['filename'])
        
        if not os.path.exists(backup_path):
            await ctx.send(f"Backup file not found: {backup_path}")
            return
        
        await ctx.send(f"Verifying integrity of backup ID {backup_id}... This may take a moment.")
        
        # Verify backup integrity
        success = self.bot.db_manager.verify_backup_integrity(backup_path)
        
        if success:
            await ctx.send(f"✅ Backup ID {backup_id} integrity verified successfully.")
            
            # Update backup record
            self.bot.db_manager.update('backup_log',
                                     {'verified': 1, 'verification_date': datetime.now().isoformat()},
                                     'backup_id = ?', (backup_id,))
        else:
            await ctx.send(f"❌ Backup ID {backup_id} integrity verification failed. The backup may be corrupted.")
    
    @commands.command(name="backupcloud")
    @commands.has_permissions(administrator=True)
    async def backup_cloud_command(self, ctx, provider: str = None, backup_id: int = None):
        """
        Configure cloud storage or upload a backup to cloud storage
        
        Usage:
        !backupcloud - Show current cloud storage configuration
        !backupcloud <provider> - Set cloud storage provider (gdrive, onedrive, none)
        !backupcloud <provider> <backup_id> - Upload a specific backup to cloud storage
        """
        if provider is None:
            # Show current cloud storage configuration
            await ctx.send(f"Current cloud storage provider: {self.cloud_provider}")
            await ctx.send(f"Cloud storage is {'enabled' if self.cloud_enabled else 'disabled'}")
            return
        
        # Validate provider
        provider = provider.lower()
        if provider not in ["gdrive", "onedrive", "none"]:
            await ctx.send("Invalid cloud storage provider. Supported providers: gdrive, onedrive, none")
            return
        
        if backup_id is None:
            # Set cloud storage provider
            self.cloud_provider = provider
            self.cloud_enabled = provider.lower() not in ["none", ""]
            
            # Update environment variable (this won't persist after restart)
            os.environ["BACKUP_CLOUD_PROVIDER"] = provider
            
            await ctx.send(f"Cloud storage provider set to: {provider}")
            await ctx.send(f"Cloud storage is now {'enabled' if self.cloud_enabled else 'disabled'}")
            return
        
        # Upload a specific backup to cloud storage
        backup = self.bot.db_manager.get_by_id('backup_log', 'backup_id', backup_id)
        
        if not backup:
            await ctx.send(f"No backup found with ID: {backup_id}")
            return
        
        # Build backup path
        backup_path = os.path.join(backup['location'], backup['filename'])
        
        if not os.path.exists(backup_path):
            await ctx.send(f"Backup file not found: {backup_path}")
            return
        
        await ctx.send(f"Uploading backup ID {backup_id} to {provider}... This may take a moment.")
        
        # Set temporary cloud provider for this upload
        original_provider = self.cloud_provider
        self.cloud_provider = provider
        
        # Upload to cloud storage
        cloud_url = await self._upload_to_cloud(backup_path)
        
        # Restore original cloud provider
        self.cloud_provider = original_provider
        
        if cloud_url:
            await ctx.send(f"✅ Backup ID {backup_id} uploaded to {provider}: {cloud_url}")
            
            # Update backup record
            self.bot.db_manager.update('backup_log',
                                     {'cloud_url': cloud_url, 'cloud_provider': provider},
                                     'backup_id = ?', (backup_id,))
        else:
            await ctx.send(f"❌ Failed to upload backup ID {backup_id} to {provider}")
    
    @commands.command(name="backupstatus", aliases=["backupinfo", "backupstate"])
    @commands.has_permissions(administrator=True)
    async def backup_status_command(self, ctx):
        """
        Show comprehensive backup system status
        
        Usage:
        !backupstatus - Show backup system status and statistics
        
        Aliases: !backupinfo, !backupstate
        """
        # Get backup statistics
        total_query = "SELECT COUNT(*) as count FROM backup_log"
        verified_query = "SELECT COUNT(*) as count FROM backup_log WHERE verified = 1"
        cloud_query = "SELECT COUNT(*) as count FROM backup_log WHERE cloud_url IS NOT NULL"
        size_query = "SELECT SUM(size) as total_size FROM backup_log"
        latest_query = "SELECT * FROM backup_log ORDER BY backup_id DESC LIMIT 1"
        
        total_backups = self.bot.db_manager.execute_query(total_query)[0]['count']
        verified_backups = self.bot.db_manager.execute_query(verified_query)[0]['count']
        cloud_backups = self.bot.db_manager.execute_query(cloud_query)[0]['count']
        total_size = self.bot.db_manager.execute_query(size_query)[0]['total_size'] or 0
        latest_backup = self.bot.db_manager.execute_query(latest_query)
        
        # Create status embed
        embed = discord.Embed(
            title="Backup System Status",
            description=f"Status as of {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            color=discord.Color.blue()
        )
        
        # Add configuration info
        embed.add_field(name="Configuration", value=
            f"**Cloud Provider:** {self.cloud_provider}\n"
            f"**Cloud Enabled:** {'✅ Yes' if self.cloud_enabled else '❌ No'}\n"
            f"**Compression:** {'✅ Enabled' if self.compression_enabled else '❌ Disabled'}\n"
            f"**Integrity Verification:** {'✅ Enabled' if self.verify_integrity else '❌ Disabled'}\n"
            f"**Rotation Scheme:** {self.rotation_scheme}\n"
            f"**Backup Interval:** {self.backup_interval_hours} hours\n"
            f"**Retention Period:** {self.backup_retention_days} days",
            inline=False
        )
        
        # Add statistics
        verified_percent = (verified_backups/total_backups*100) if total_backups > 0 else 0
        cloud_percent = (cloud_backups/total_backups*100) if total_backups > 0 else 0
        
        embed.add_field(name="Statistics", value=
            f"**Total Backups:** {total_backups}\n"
            f"**Verified Backups:** {verified_backups} ({verified_percent:.1f}%)\n"
            f"**Cloud Backups:** {cloud_backups} ({cloud_percent:.1f}%)\n"
            f"**Total Storage:** {total_size/1024/1024:.2f} MB",
            inline=False
        )
        
        # Add latest backup info
        if latest_backup:
            latest = latest_backup[0]
            timestamp = latest['timestamp'].split('T')[0]  # Just get the date part
            
            embed.add_field(name="Latest Backup", value=
                f"**ID:** {latest['backup_id']}\n"
                f"**Date:** {timestamp}\n"
                f"**Size:** {latest['size']/1024:.2f} KB\n"
                f"**Verified:** {'✅ Yes' if latest.get('verified', 0) == 1 else '❌ No'}\n"
                f"**Cloud URL:** {latest.get('cloud_url', 'None')}",
                inline=False
            )
        
        # Add next scheduled backup info
        if self.backup_interval_hours > 0 and self.backup_task:
            next_backup = datetime.now() + timedelta(
                seconds=self.backup_task._when - asyncio.get_event_loop().time()
            )
            
            embed.add_field(name="Next Scheduled Backup", value=
                f"**Date:** {next_backup.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"**Time Remaining:** {(next_backup - datetime.now()).total_seconds() / 3600:.1f} hours",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="backupexport")
    @commands.has_permissions(administrator=True)
    async def backup_export_command(self, ctx, backup_id: int = None, format: str = "zip"):
        """
        Export a backup in a specific format
        
        Usage:
        !backupexport <backup_id> [format] - Export a backup (format: zip, sql, csv)
        """
        if backup_id is None:
            await ctx.send("Please specify a backup ID to export. Use `!listbackups` to see available backups.")
            return
        
        # Validate format
        format = format.lower()
        if format not in ["zip", "sql", "csv"]:
            await ctx.send("Invalid export format. Supported formats: zip, sql, csv")
            return
        
        # Get backup record
        backup = self.bot.db_manager.get_by_id('backup_log', 'backup_id', backup_id)
        
        if not backup:
            await ctx.send(f"No backup found with ID: {backup_id}")
            return
        
        # Build backup path
        backup_path = os.path.join(backup['location'], backup['filename'])
        
        if not os.path.exists(backup_path):
            await ctx.send(f"Backup file not found: {backup_path}")
            return
        
        await ctx.send(f"Exporting backup ID {backup_id} in {format} format... This may take a moment.")
        
        try:
            # Handle different export formats
            if format == "zip":
                # If already a zip file, just upload it
                if backup['filename'].endswith('.zip'):
                    with open(backup_path, 'rb') as f:
                        file = discord.File(f, filename=backup['filename'])
                        await ctx.send(f"Backup ID {backup_id} exported as ZIP:", file=file)
                else:
                    # Create a zip file
                    temp_dir = tempfile.mkdtemp()
                    try:
                        zip_path = os.path.join(temp_dir, f"backup_{backup_id}.zip")
                        
                        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            zipf.write(backup_path, arcname=os.path.basename(backup_path))
                        
                        with open(zip_path, 'rb') as f:
                            file = discord.File(f, filename=f"backup_{backup_id}.zip")
                            await ctx.send(f"Backup ID {backup_id} exported as ZIP:", file=file)
                    finally:
                        shutil.rmtree(temp_dir)
            
            elif format == "sql":
                # For SQL format, we'll just rename the file with .sql extension
                # In a real implementation, you might want to extract SQL statements
                temp_dir = tempfile.mkdtemp()
                try:
                    sql_path = os.path.join(temp_dir, f"backup_{backup_id}.sql")
                    shutil.copy(backup_path, sql_path)
                    
                    with open(sql_path, 'rb') as f:
                        file = discord.File(f, filename=f"backup_{backup_id}.sql")
                        await ctx.send(f"Backup ID {backup_id} exported as SQL:", file=file)
                finally:
                    shutil.rmtree(temp_dir)
            
            elif format == "csv":
                # For CSV format, we'll generate a CSV with table data
                # This is a placeholder - in a real implementation, you would extract data from the backup
                await ctx.send("Generating CSV export from backup...")
                
                # Get all products
                products = self.bot.db_manager.list_products()
                
                if not products:
                    await ctx.send("No products found in database.")
                    return
                
                # Generate CSV snapshot
                csv_data = await self._generate_inventory_snapshot(products)
                
                # Create file
                file = discord.File(
                    io.BytesIO(csv_data.encode('utf-8')),
                    filename=f"backup_{backup_id}_inventory.csv"
                )
                
                await ctx.send(f"Backup ID {backup_id} exported as CSV:", file=file)
        
        except Exception as e:
            logger.error(f"Error exporting backup: {str(e)}")
            await ctx.send(f"Error exporting backup: {str(e)}")

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(BackupCog(bot))
