"""
System Monitoring and Health Checks for the AccountME Discord Bot
Implementation for Phase 5.4: System Monitoring & Health
"""

import discord
from discord.ext import commands
import logging
import os
import asyncio
import json
import sqlite3
import platform
import psutil
import time
from datetime import datetime, timedelta
import traceback
import sys
from typing import Dict, List, Any, Optional, Tuple, Union

logger = logging.getLogger("accountme_bot.system_monitor")

class SystemMonitorCog(commands.Cog, name="System Monitor"):
    """System monitoring and health check commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Load configuration from environment variables
        try:
            self.health_check_interval = int(os.getenv("HEALTH_CHECK_INTERVAL_MINUTES", "30"))
        except ValueError:
            self.health_check_interval = 30
            logger.warning("HEALTH_CHECK_INTERVAL_MINUTES is not a valid integer, defaulting to 30")
        
        try:
            self.error_threshold = int(os.getenv("ERROR_THRESHOLD", "5"))
        except ValueError:
            self.error_threshold = 5
            logger.warning("ERROR_THRESHOLD is not a valid integer, defaulting to 5")
        
        try:
            self.admin_notification_channel_id = int(os.getenv("ADMIN_NOTIFICATION_CHANNEL_ID", "0"))
        except ValueError:
            self.admin_notification_channel_id = 0
            logger.warning("ADMIN_NOTIFICATION_CHANNEL_ID is not a valid integer, defaulting to 0")
        
        # Initialize monitoring data
        self.start_time = datetime.now()
        self.error_count = 0
        self.error_history = []
        self.last_health_check = None
        self.health_check_results = {}
        self.recovery_attempts = {}
        
        # Start health check task
        if self.health_check_interval > 0:
            self.health_check_task = self.bot.loop.create_task(self._scheduled_health_check())
            logger.info(f"Scheduled health check task started with interval of {self.health_check_interval} minutes")
        
        # Register error handler
        self.bot.add_listener(self.on_command_error, "on_command_error")
        self.bot.add_listener(self.on_error, "on_error")
        
        logger.info("System monitoring initialized")
    
    def cog_unload(self):
        """Called when the cog is unloaded"""
        if hasattr(self, 'health_check_task'):
            self.health_check_task.cancel()
            logger.info("Scheduled health check task cancelled")
    
    async def _scheduled_health_check(self):
        """Task for scheduled health checks"""
        try:
            # Wait for bot to be ready
            await self.bot.wait_until_ready()
            
            while not self.bot.is_closed():
                try:
                    # Perform health check
                    logger.info("Running scheduled health check")
                    await self._perform_health_check()
                    
                    # Update last health check time
                    self.last_health_check = datetime.now()
                    
                except Exception as e:
                    logger.error(f"Error in scheduled health check: {str(e)}")
                    logger.error(traceback.format_exc())
                
                # Wait for next health check interval
                await asyncio.sleep(self.health_check_interval * 60)  # Convert minutes to seconds
        
        except asyncio.CancelledError:
            logger.info("Scheduled health check task cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in health check task: {str(e)}")
            logger.error(traceback.format_exc())
    
    async def _perform_health_check(self):
        """
        Perform a comprehensive health check of the system
        
        Checks:
        1. System resources (CPU, memory, disk)
        2. Database integrity
        3. Discord connection status
        4. Error rate
        5. Component status (image processor, report generator, etc.)
        """
        health_results = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",  # Will be set to "warning" or "critical" if issues are found
            "checks": {}
        }
        
        # Check system resources
        system_status = await self._check_system_resources()
        health_results["checks"]["system"] = system_status
        
        # Check database integrity
        db_status = await self._check_database_integrity()
        health_results["checks"]["database"] = db_status
        
        # Check Discord connection
        discord_status = await self._check_discord_connection()
        health_results["checks"]["discord"] = discord_status
        
        # Check error rate
        error_status = await self._check_error_rate()
        health_results["checks"]["errors"] = error_status
        
        # Check component status
        component_status = await self._check_component_status()
        health_results["checks"]["components"] = component_status
        
        # Determine overall status
        if any(check.get("status") == "critical" for check in health_results["checks"].values()):
            health_results["status"] = "critical"
        elif any(check.get("status") == "warning" for check in health_results["checks"].values()):
            health_results["status"] = "warning"
        
        # Store health check results
        self.health_check_results = health_results
        
        # Log health check results
        logger.info(f"Health check completed with status: {health_results['status']}")
        
        # Attempt recovery for any critical issues
        if health_results["status"] in ["warning", "critical"]:
            await self._attempt_recovery(health_results)
        
        # Send notification if there are issues
        if health_results["status"] in ["warning", "critical"]:
            await self._send_admin_notification(health_results)
        
        return health_results
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resources (CPU, memory, disk)"""
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Get disk usage for the database directory
            db_path = os.getenv("DATABASE_PATH", "data/database.db")
            db_dir = os.path.dirname(os.path.abspath(db_path))
            disk = psutil.disk_usage(db_dir)
            disk_percent = disk.percent
            
            # Determine status based on thresholds
            status = "healthy"
            warnings = []
            
            if cpu_percent > 90:
                status = "critical"
                warnings.append(f"CPU usage is very high: {cpu_percent}%")
            elif cpu_percent > 70:
                status = "warning"
                warnings.append(f"CPU usage is high: {cpu_percent}%")
            
            if memory_percent > 90:
                status = "critical"
                warnings.append(f"Memory usage is very high: {memory_percent}%")
            elif memory_percent > 70:
                status = "warning"
                warnings.append(f"Memory usage is high: {memory_percent}%")
            
            if disk_percent > 90:
                status = "critical"
                warnings.append(f"Disk usage is very high: {disk_percent}%")
            elif disk_percent > 70:
                status = "warning"
                warnings.append(f"Disk usage is high: {disk_percent}%")
            
            return {
                "status": status,
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "warnings": warnings
            }
        
        except Exception as e:
            logger.error(f"Error checking system resources: {str(e)}")
            return {
                "status": "warning",
                "error": str(e),
                "warnings": ["Failed to check system resources"]
            }
    
    async def _check_database_integrity(self) -> Dict[str, Any]:
        """Check database integrity"""
        try:
            db_path = os.getenv("DATABASE_PATH", "data/database.db")
            
            # Create a new connection for integrity check
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]
            
            # Run foreign key check
            cursor.execute("PRAGMA foreign_key_check")
            foreign_key_result = cursor.fetchall()
            
            # Close connection
            conn.close()
            
            # Determine status based on results
            status = "healthy"
            warnings = []
            
            if integrity_result != "ok":
                status = "critical"
                warnings.append(f"Database integrity check failed: {integrity_result}")
            
            if foreign_key_result:
                status = "warning"
                warnings.append(f"Foreign key constraints violated: {len(foreign_key_result)} violations")
            
            # Check database size
            db_size = os.path.getsize(db_path)
            db_size_mb = db_size / (1024 * 1024)
            
            if db_size_mb > 100:
                status = "warning"
                warnings.append(f"Database size is large: {db_size_mb:.2f} MB")
            
            return {
                "status": status,
                "integrity_result": integrity_result,
                "foreign_key_violations": len(foreign_key_result),
                "db_size_mb": db_size_mb,
                "warnings": warnings
            }
        
        except Exception as e:
            logger.error(f"Error checking database integrity: {str(e)}")
            return {
                "status": "warning",
                "error": str(e),
                "warnings": ["Failed to check database integrity"]
            }
    
    async def _check_discord_connection(self) -> Dict[str, Any]:
        """Check Discord connection status"""
        try:
            # Check if bot is connected
            is_connected = not self.bot.is_closed()
            
            # Check latency
            latency = self.bot.latency
            
            # Determine status based on results
            status = "healthy"
            warnings = []
            
            if not is_connected:
                status = "critical"
                warnings.append("Bot is not connected to Discord")
            
            if latency > 1.0:
                status = "critical"
                warnings.append(f"Discord latency is very high: {latency:.2f} seconds")
            elif latency > 0.5:
                status = "warning"
                warnings.append(f"Discord latency is high: {latency:.2f} seconds")
            
            # Check guild count
            guild_count = len(self.bot.guilds)
            if guild_count == 0:
                status = "warning"
                warnings.append("Bot is not connected to any guilds")
            
            return {
                "status": status,
                "connected": is_connected,
                "latency": latency,
                "guild_count": guild_count,
                "warnings": warnings
            }
        
        except Exception as e:
            logger.error(f"Error checking Discord connection: {str(e)}")
            return {
                "status": "warning",
                "error": str(e),
                "warnings": ["Failed to check Discord connection"]
            }
    
    async def _check_error_rate(self) -> Dict[str, Any]:
        """Check error rate"""
        try:
            # Calculate error rate (errors per hour)
            uptime_hours = (datetime.now() - self.start_time).total_seconds() / 3600
            error_rate = self.error_count / max(uptime_hours, 1)
            
            # Determine status based on results
            status = "healthy"
            warnings = []
            
            if error_rate > self.error_threshold:
                status = "critical"
                warnings.append(f"Error rate is very high: {error_rate:.2f} errors per hour")
            elif error_rate > self.error_threshold / 2:
                status = "warning"
                warnings.append(f"Error rate is high: {error_rate:.2f} errors per hour")
            
            # Check recent errors
            recent_errors = [e for e in self.error_history if e["timestamp"] > datetime.now() - timedelta(hours=1)]
            if len(recent_errors) > self.error_threshold:
                status = "critical"
                warnings.append(f"Many recent errors: {len(recent_errors)} in the last hour")
            
            return {
                "status": status,
                "error_count": self.error_count,
                "error_rate": error_rate,
                "recent_errors": len(recent_errors),
                "warnings": warnings
            }
        
        except Exception as e:
            logger.error(f"Error checking error rate: {str(e)}")
            return {
                "status": "warning",
                "error": str(e),
                "warnings": ["Failed to check error rate"]
            }
    
    async def _check_component_status(self) -> Dict[str, Any]:
        """Check status of bot components"""
        try:
            components = {}
            warnings = []
            overall_status = "healthy"
            
            # Check database manager
            try:
                # Simple query to test database connection
                self.bot.db_manager.execute_query("SELECT 1")
                components["database_manager"] = "healthy"
            except Exception as e:
                components["database_manager"] = "critical"
                warnings.append(f"Database manager is not functioning: {str(e)}")
                overall_status = "critical"
            
            # Check image processor
            try:
                # Check if image processor is initialized
                if self.bot.get_image_processor() is None:
                    components["image_processor"] = "warning"
                    warnings.append("Image processor is not initialized")
                    if overall_status == "healthy":
                        overall_status = "warning"
                else:
                    components["image_processor"] = "healthy"
            except Exception as e:
                components["image_processor"] = "warning"
                warnings.append(f"Error checking image processor: {str(e)}")
                if overall_status == "healthy":
                    overall_status = "warning"
            
            # Check report generator
            try:
                # Check if report generator is initialized
                if self.bot.report_generator is None:
                    components["report_generator"] = "warning"
                    warnings.append("Report generator is not initialized")
                    if overall_status == "healthy":
                        overall_status = "warning"
                else:
                    components["report_generator"] = "healthy"
            except Exception as e:
                components["report_generator"] = "warning"
                warnings.append(f"Error checking report generator: {str(e)}")
                if overall_status == "healthy":
                    overall_status = "warning"
            
            return {
                "status": overall_status,
                "components": components,
                "warnings": warnings
            }
        
        except Exception as e:
            logger.error(f"Error checking component status: {str(e)}")
            return {
                "status": "warning",
                "error": str(e),
                "warnings": ["Failed to check component status"]
            }
    
    async def _attempt_recovery(self, health_results: Dict[str, Any]):
        """Attempt to recover from issues identified in health check"""
        try:
            recovery_actions = []
            
            # Check database issues
            db_status = health_results["checks"].get("database", {})
            if db_status.get("status") in ["warning", "critical"]:
                # Attempt database recovery
                if await self._recover_database():
                    recovery_actions.append("Database recovery attempted")
            
            # Check Discord connection issues
            discord_status = health_results["checks"].get("discord", {})
            if discord_status.get("status") in ["warning", "critical"]:
                # Attempt to reconnect
                if await self._recover_discord_connection():
                    recovery_actions.append("Discord reconnection attempted")
            
            # Check component issues
            component_status = health_results["checks"].get("components", {})
            if component_status.get("status") in ["warning", "critical"]:
                # Attempt to reinitialize components
                if await self._recover_components():
                    recovery_actions.append("Component reinitialization attempted")
            
            # Log recovery actions
            if recovery_actions:
                logger.info(f"Recovery actions performed: {', '.join(recovery_actions)}")
            
            return recovery_actions
        
        except Exception as e:
            logger.error(f"Error attempting recovery: {str(e)}")
            return []
    
    async def _recover_database(self) -> bool:
        """Attempt to recover database from issues"""
        try:
            # Check if we've attempted recovery recently
            last_attempt = self.recovery_attempts.get("database")
            if last_attempt and (datetime.now() - last_attempt).total_seconds() < 3600:
                logger.info("Skipping database recovery - attempted recently")
                return False
            
            logger.info("Attempting database recovery")
            
            # Record recovery attempt
            self.recovery_attempts["database"] = datetime.now()
            
            # Close existing connection
            self.bot.db_manager.close()
            
            # Reopen connection
            db_path = os.getenv("DATABASE_PATH", "data/database.db")
            conn = sqlite3.connect(db_path)
            
            # Run VACUUM to rebuild the database
            conn.execute("VACUUM")
            conn.close()
            
            # Reconnect the database manager
            self.bot.db_manager._get_connection()
            
            logger.info("Database recovery completed")
            return True
        
        except Exception as e:
            logger.error(f"Error recovering database: {str(e)}")
            return False
    
    async def _recover_discord_connection(self) -> bool:
        """Attempt to recover Discord connection"""
        try:
            # Check if we've attempted recovery recently
            last_attempt = self.recovery_attempts.get("discord")
            if last_attempt and (datetime.now() - last_attempt).total_seconds() < 300:
                logger.info("Skipping Discord reconnection - attempted recently")
                return False
            
            logger.info("Attempting Discord reconnection")
            
            # Record recovery attempt
            self.recovery_attempts["discord"] = datetime.now()
            
            # We can't directly reconnect, but we can log the issue
            # In a production environment, this would trigger a restart mechanism
            logger.warning("Discord reconnection not implemented - would require bot restart")
            
            return False
        
        except Exception as e:
            logger.error(f"Error recovering Discord connection: {str(e)}")
            return False
    
    async def _recover_components(self) -> bool:
        """Attempt to recover bot components"""
        try:
            # Check if we've attempted recovery recently
            last_attempt = self.recovery_attempts.get("components")
            if last_attempt and (datetime.now() - last_attempt).total_seconds() < 1800:
                logger.info("Skipping component recovery - attempted recently")
                return False
            
            logger.info("Attempting component recovery")
            
            # Record recovery attempt
            self.recovery_attempts["components"] = datetime.now()
            
            # Reinitialize components as needed
            components_reinitialized = False
            
            # Check image processor
            if self.bot.get_image_processor() is None:
                from utils.image_processor import ImageProcessor
                self.bot.image_processor = ImageProcessor()
                logger.info("Reinitialized image processor")
                components_reinitialized = True
            
            # Check report generator
            if self.bot.report_generator is None:
                from utils.report_generator import ReportGenerator
                reports_dir = os.getenv("REPORTS_DIR", "data/reports")
                reports_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), reports_dir)
                os.makedirs(reports_path, exist_ok=True)
                self.bot.report_generator = ReportGenerator(self.bot.db_manager, reports_path)
                logger.info("Reinitialized report generator")
                components_reinitialized = True
            
            return components_reinitialized
        
        except Exception as e:
            logger.error(f"Error recovering components: {str(e)}")
            return False
    
    async def _send_admin_notification(self, health_results: Dict[str, Any]):
        """Send notification to admins about system issues"""
        try:
            # Check if admin notification channel is configured
            if not self.admin_notification_channel_id:
                logger.warning("Admin notification channel not configured")
                return
            
            # Get the notification channel
            channel = self.bot.get_channel(self.admin_notification_channel_id)
            if not channel:
                logger.warning(f"Admin notification channel not found: {self.admin_notification_channel_id}")
                return
            
            # Create notification embed
            embed = discord.Embed(
                title=f"System Health Alert: {health_results['status'].upper()}",
                description=f"Health check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} detected issues",
                color=discord.Color.red() if health_results["status"] == "critical" else discord.Color.gold()
            )
            
            # Add warnings from each check
            for check_name, check_data in health_results["checks"].items():
                if check_data.get("warnings"):
                    embed.add_field(
                        name=f"{check_name.capitalize()} Issues",
                        value="\n".join(f"• {warning}" for warning in check_data["warnings"]),
                        inline=False
                    )
            
            # Add recovery information
            if hasattr(self, 'last_recovery_actions') and self.last_recovery_actions:
                embed.add_field(
                    name="Recovery Actions",
                    value="\n".join(f"• {action}" for action in self.last_recovery_actions),
                    inline=False
                )
            
            # Add recommendation
            embed.add_field(
                name="Recommendation",
                value="Run `!systemstatus` for detailed system information",
                inline=False
            )
            
            # Send notification
            await channel.send(embed=embed)
            logger.info(f"Sent admin notification about {health_results['status']} status")
        
        except Exception as e:
            logger.error(f"Error sending admin notification: {str(e)}")
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """
        Error tracking for command errors
        This doesn't replace the main error handler, just tracks errors for monitoring
        """
        # Skip if the command has its own error handler
        if hasattr(ctx.command, 'on_error'):
            return
        
        # Skip if the cog has its own error handler
        if ctx.cog and ctx.cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
            return
        
        # Track the error
        self.error_count += 1
        
        # Get the original error if it's wrapped
        error = getattr(error, 'original', error)
        
        # Add to error history (keep last 100 errors)
        error_info = {
            "timestamp": datetime.now(),
            "command": ctx.command.qualified_name if ctx.command else "Unknown",
            "error_type": type(error).__name__,
            "error_message": str(error)
        }
        
        self.error_history.append(error_info)
        if len(self.error_history) > 100:
            self.error_history.pop(0)
        
        # Log the error
        logger.error(f"Command error in {error_info['command']}: {error_info['error_type']}: {error_info['error_message']}")
    
    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        """
        Error tracking for non-command errors
        This doesn't replace the main error handler, just tracks errors for monitoring
        """
        # Track the error
        self.error_count += 1
        
        # Get the error information
        error_type, error, error_traceback = sys.exc_info()
        
        # Add to error history (keep last 100 errors)
        error_info = {
            "timestamp": datetime.now(),
            "event": event,
            "error_type": error_type.__name__ if error_type else "Unknown",
            "error_message": str(error) if error else "Unknown"
        }
        
        self.error_history.append(error_info)
        if len(self.error_history) > 100:
            self.error_history.pop(0)
        
        # Log the error
        logger.error(f"Event error in {error_info['event']}: {error_info['error_type']}: {error_info['error_message']}")
    
    @commands.command(name="systemstatus")
    @commands.has_permissions(administrator=True)
    async def system_status_command(self, ctx):
        """
        Show detailed system status information
        
        Usage:
        !systemstatus - Show system status and health information
        """
        # Perform a health check
        health_results = await self._perform_health_check()
        
        # Create status embed
        embed = discord.Embed(
            title="System Status",
            description=f"Status as of {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            color=discord.Color.green() if health_results["status"] == "healthy" else 
                  discord.Color.gold() if health_results["status"] == "warning" else
                  discord.Color.red()
        )
        
        # Add system information
        system_info = platform.uname()
        embed.add_field(
            name="System Information",
            value=f"**OS:** {system_info.system} {system_info.release}\n"
                  f"**Python:** {platform.python_version()}\n"
                  f"**Discord.py:** {discord.__version__}\n"
                  f"**Uptime:** {self._format_timedelta(datetime.now() - self.start_time)}",
            inline=False
        )
        
        # Add resource usage
        system_status = health_results["checks"].get("system", {})
        embed.add_field(
            name="Resource Usage",
            value=f"**CPU:** {system_status.get('cpu_percent', 'N/A')}%\n"
                  f"**Memory:** {system_status.get('memory_percent', 'N/A')}%\n"
                  f"**Disk:** {system_status.get('disk_percent', 'N/A')}%",
            inline=True
        )
        
        # Add database status
        db_status = health_results["checks"].get("database", {})
        embed.add_field(
            name="Database Status",
            value=f"**Integrity:** {db_status.get('integrity_result', 'N/A')}\n"
                  f"**FK Violations:** {db_status.get('foreign_key_violations', 'N/A')}\n"
                  f"**Size:** {db_status.get('db_size_mb', 'N/A'):.2f} MB",
            inline=True
        )
        
        # Add Discord status
        discord_status = health_results["checks"].get("discord", {})
        embed.add_field(
            name="Discord Status",
            value=f"**Connected:** {'Yes' if discord_status.get('connected', False) else 'No'}\n"
                  f"**Latency:** {discord_status.get('latency', 'N/A'):.2f}s\n"
                  f"**Guilds:** {discord_status.get('guild_count', 'N/A')}",
            inline=True
        )
        
        # Add error statistics
        error_status = health_results["checks"].get("errors", {})
        embed.add_field(
            name="Error Statistics",
            value=f"**Total Errors:** {error_status.get('error_count', 'N/A')}\n"
                  f"**Error Rate:** {error_status.get('error_rate', 'N/A'):.2f}/hour\n"
                  f"**Recent Errors:** {error_status.get('recent_errors', 'N/A')} (last hour)",
            inline=True
        )
        
        # Add component status
        component_status = health_results["checks"].get("components", {})
        components = component_status.get("components", {})
        component_text = ""
        for component, status in components.items():
            emoji = "✅" if status == "healthy" else "⚠️" if status == "warning" else "❌"
            component_text += f"{emoji} **{component.replace('_', ' ').title()}**\n"
        
        embed.add_field(
            name="Component Status",
            value=component_text or "No components checked",
            inline=True
        )
        
        # Add health check information
        embed.add_field(
            name="Health Check",
            value=f"**Last Check:** {self.last_health_check.strftime('%Y-%m-%d %H:%M:%S') if self.last_health_check else 'Never'}\n"
                  f"**Status:** {health_results['status'].upper()}\n"
                  f"**Interval:** {self.health_check_interval} minutes",
            inline=True
        )
        
        # Add warnings if any
        all_warnings = []
        for check_name, check_data in health_results["checks"].items():
            if check_data.get("warnings"):
                all_warnings.extend(check_data["warnings"])
        
        if all_warnings:
            embed.add_field(
                name="⚠️ Warnings",
                value="\n".join(f"• {warning}" for warning in all_warnings),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="databasecheck")
    @commands.has_permissions(administrator=True)
    async def database_check_command(self, ctx):
        """
        Perform a comprehensive database integrity check
        
        Usage:
        !databasecheck - Check database integrity and structure
        """
        await ctx.send("Performing database integrity check... This may take a moment.")
        
        try:
            db_path = os.getenv("DATABASE_PATH", "data/database.db")
            
            # Create a new connection for integrity check
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]
            
            # Run foreign key check
            cursor.execute("PRAGMA foreign_key_check")
            foreign_key_result = cursor.fetchall()
            
            # Get table information
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall() if not row[0].startswith('sqlite_')]
            
            # Get table statistics
            table_stats = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cursor.fetchone()[0]
                table_stats[table] = row_count
            
            # Close connection
            conn.close()
            
            # Create embed
            embed = discord.Embed(
                title="Database Integrity Check",
                description=f"Check performed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                color=discord.Color.green() if integrity_result == "ok" and not foreign_key_result else discord.Color.red()
            )
            
            # Add integrity result
            embed.add_field(
                name="Integrity Check",
                value=f"**Result:** {integrity_result}",
                inline=False
            )
            
            # Add foreign key check result
            if foreign_key_result:
                fk_text = "Foreign key constraints violated:\n"
                for violation in foreign_key_result[:10]:  # Show first 10 violations
                    fk_text += f"• Table: {violation[0]}, Row: {violation[1]}, Parent: {violation[2]}\n"
                if len(foreign_key_result) > 10:
                    fk_text += f"...and {len(foreign_key_result) - 10} more violations"
                embed.add_field(
                    name="Foreign Key Check",
                    value=fk_text,
                    inline=False
                )
            else:
                embed.add_field(
                    name="Foreign Key Check",
                    value="No foreign key violations found",
                    inline=False
                )
            
            # Add table statistics
            table_text = ""
            for table, count in table_stats.items():
                table_text += f"**{table}:** {count} rows\n"
            
            embed.add_field(
                name="Table Statistics",
                value=table_text,
                inline=False
            )
            
            # Add database file info
            db_size = os.path.getsize(db_path)
            db_size_mb = db_size / (1024 * 1024)
            db_modified = datetime.fromtimestamp(os.path.getmtime(db_path))
            
            embed.add_field(
                name="Database File",
                value=f"**Path:** {db_path}\n"
                      f"**Size:** {db_size_mb:.2f} MB\n"
                      f"**Last Modified:** {db_modified.strftime('%Y-%m-%d %H:%M:%S')}",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
            # If there are issues, offer to attempt repair
            if integrity_result != "ok" or foreign_key_result:
                repair_msg = await ctx.send("Database issues detected. Would you like to attempt repair? (This will create a backup first)")
                
                # Add reaction options
                await repair_msg.add_reaction("✅")  # Yes
                await repair_msg.add_reaction("❌")  # No
                
                # Wait for reaction
                def check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == repair_msg.id
                
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                    
                    if str(reaction.emoji) == "✅":
                        await ctx.send("Creating database backup before repair...")
                        
                        # Create backup
                        backup_path = self.bot.db_manager.backup_database()
                        
                        await ctx.send(f"Backup created at {backup_path}. Attempting database repair...")
                        
                        # Attempt repair
                        if await self._recover_database():
                            await ctx.send("Database repair completed. Run `!databasecheck` again to verify.")
                        else:
                            await ctx.send("Database repair failed. Please check the logs for details.")
                    else:
                        await ctx.send("Repair cancelled.")
                
                except asyncio.TimeoutError:
                    await ctx.send("Repair option timed out.")
        
        except Exception as e:
            logger.error(f"Error performing database check: {str(e)}")
            await ctx.send(f"Error performing database check: {str(e)}")
    
    @commands.command(name="errorlog")
    @commands.has_permissions(administrator=True)
    async def error_log_command(self, ctx, limit: int = 10):
        """
        Show recent error log
        
        Usage:
        !errorlog [limit] - Show recent errors (default: 10)
        """
        if not self.error_history:
            await ctx.send("No errors have been recorded.")
            return
        
        # Sort errors by timestamp (newest first)
        sorted_errors = sorted(self.error_history, key=lambda e: e["timestamp"], reverse=True)
        
        # Limit the number of errors to show
        errors_to_show = sorted_errors[:min(limit, len(sorted_errors))]
        
        # Create embed
        embed = discord.Embed(
            title="Error Log",
            description=f"Showing {len(errors_to_show)} most recent errors",
            color=discord.Color.red()
        )
        
        for i, error in enumerate(errors_to_show):
            timestamp = error["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            if "command" in error:
                # Command error
                embed.add_field(
                    name=f"{i+1}. Command Error - {timestamp}",
                    value=f"**Command:** {error['command']}\n"
                          f"**Type:** {error['error_type']}\n"
                          f"**Message:** {error['error_message']}",
                    inline=False
                )
            else:
                # Event error
                embed.add_field(
                    name=f"{i+1}. Event Error - {timestamp}",
                    value=f"**Event:** {error['event']}\n"
                          f"**Type:** {error['error_type']}\n"
                          f"**Message:** {error['error_message']}",
                    inline=False
                )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="healthcheck")
    @commands.has_permissions(administrator=True)
    async def health_check_command(self, ctx):
        """
        Perform a manual health check
        
        Usage:
        !healthcheck - Run a comprehensive system health check
        """
        await ctx.send("Performing health check... This may take a moment.")
        
        # Perform health check
        health_results = await self._perform_health_check()
        
        # Create embed
        embed = discord.Embed(
            title="Health Check Results",
            description=f"Check performed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            color=discord.Color.green() if health_results["status"] == "healthy" else 
                  discord.Color.gold() if health_results["status"] == "warning" else
                  discord.Color.red()
        )
        
        # Add overall status
        embed.add_field(
            name="Overall Status",
            value=f"**{health_results['status'].upper()}**",
            inline=False
        )
        
        # Add individual check results
        for check_name, check_data in health_results["checks"].items():
            status_emoji = "✅" if check_data.get("status") == "healthy" else "⚠️" if check_data.get("status") == "warning" else "❌"
            
            # Format the check data
            check_text = f"**Status:** {status_emoji} {check_data.get('status', 'unknown').upper()}\n"
            
            # Add specific details based on check type
            if check_name == "system":
                check_text += f"**CPU:** {check_data.get('cpu_percent', 'N/A')}%\n"
                check_text += f"**Memory:** {check_data.get('memory_percent', 'N/A')}%\n"
                check_text += f"**Disk:** {check_data.get('disk_percent', 'N/A')}%\n"
            elif check_name == "database":
                check_text += f"**Integrity:** {check_data.get('integrity_result', 'N/A')}\n"
                check_text += f"**FK Violations:** {check_data.get('foreign_key_violations', 'N/A')}\n"
                check_text += f"**Size:** {check_data.get('db_size_mb', 'N/A'):.2f} MB\n"
            elif check_name == "discord":
                check_text += f"**Connected:** {'Yes' if check_data.get('connected', False) else 'No'}\n"
                check_text += f"**Latency:** {check_data.get('latency', 'N/A'):.2f}s\n"
                check_text += f"**Guilds:** {check_data.get('guild_count', 'N/A')}\n"
            elif check_name == "errors":
                check_text += f"**Total Errors:** {check_data.get('error_count', 'N/A')}\n"
                check_text += f"**Error Rate:** {check_data.get('error_rate', 'N/A'):.2f}/hour\n"
                check_text += f"**Recent Errors:** {check_data.get('recent_errors', 'N/A')} (last hour)\n"
            elif check_name == "components":
                components = check_data.get("components", {})
                for component, status in components.items():
                    component_emoji = "✅" if status == "healthy" else "⚠️" if status == "warning" else "❌"
                    check_text += f"{component_emoji} **{component.replace('_', ' ').title()}**\n"
            
            # Add warnings if any
            if check_data.get("warnings"):
                check_text += "\n**Warnings:**\n"
                for warning in check_data["warnings"]:
                    check_text += f"• {warning}\n"
            
            embed.add_field(
                name=f"{check_name.capitalize()} Check",
                value=check_text,
                inline=False
            )
        
        # Add recovery information if applicable
        if hasattr(self, 'last_recovery_actions') and self.last_recovery_actions:
            embed.add_field(
                name="Recovery Actions",
                value="\n".join(f"• {action}" for action in self.last_recovery_actions),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="adminnotify")
    @commands.has_permissions(administrator=True)
    async def admin_notify_command(self, ctx, channel: discord.TextChannel = None):
        """
        Set or view the admin notification channel
        
        Usage:
        !adminnotify - Show current notification channel
        !adminnotify #channel - Set notification channel
        """
        if channel is None:
            # Show current notification channel
            if self.admin_notification_channel_id:
                channel = self.bot.get_channel(self.admin_notification_channel_id)
                if channel:
                    await ctx.send(f"Current admin notification channel: {channel.mention}")
                else:
                    await ctx.send(f"Admin notification channel ID set to {self.admin_notification_channel_id}, but channel not found.")
            else:
                await ctx.send("No admin notification channel set. Use `!adminnotify #channel` to set one.")
            return
        
        # Set new notification channel
        self.admin_notification_channel_id = channel.id
        
        # Update environment variable (this won't persist after restart)
        os.environ["ADMIN_NOTIFICATION_CHANNEL_ID"] = str(channel.id)
        
        await ctx.send(f"Admin notification channel set to {channel.mention}")
        
        # Test channel permissions
        try:
            test_embed = discord.Embed(
                title="Admin Notification Test",
                description="This is a test message to verify permissions",
                color=discord.Color.blue()
            )
            await channel.send(embed=test_embed)
            await ctx.send("Successfully sent test message to notification channel.")
        except Exception as e:
            await ctx.send(f"Warning: Could not send test message to notification channel. Error: {str(e)}")
    
    @commands.command(name="healthinterval")
    @commands.has_permissions(administrator=True)
    async def health_interval_command(self, ctx, interval_minutes: int = None):
        """
        Set or view the health check interval
        
        Usage:
        !healthinterval - Show current health check interval
        !healthinterval <minutes> - Set health check interval in minutes (0 to disable)
        """
        if interval_minutes is None:
            # Show current interval
            if self.health_check_interval > 0:
                next_check = datetime.now() + timedelta(
                    seconds=self.health_check_task._when - asyncio.get_event_loop().time()
                ) if hasattr(self, 'health_check_task') else None
                
                await ctx.send(
                    f"Current health check interval: Every {self.health_check_interval} minutes\n"
                    f"Next check: {next_check.strftime('%Y-%m-%d %H:%M:%S') if next_check else 'Unknown'}"
                )
            else:
                await ctx.send("Scheduled health checks are disabled.")
            return
        
        # Validate interval
        if interval_minutes < 0:
            await ctx.send("Health check interval must be 0 or greater (0 disables scheduled checks)")
            return
        
        # Update interval
        self.health_check_interval = interval_minutes
        
        # Update environment variable (this won't persist after restart)
        os.environ["HEALTH_CHECK_INTERVAL_MINUTES"] = str(interval_minutes)
        
        # Cancel existing task if any
        if hasattr(self, 'health_check_task'):
            self.health_check_task.cancel()
            self.health_check_task = None
        
        if interval_minutes > 0:
            # Start new task
            self.health_check_task = self.bot.loop.create_task(self._scheduled_health_check())
            await ctx.send(f"Health check interval set to every {interval_minutes} minutes")
        else:
            await ctx.send("Scheduled health checks disabled")
    
    def _format_timedelta(self, td):
        """Format a timedelta into a readable string"""
        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
        
        return ", ".join(parts) if parts else "0 seconds"

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(SystemMonitorCog(bot))