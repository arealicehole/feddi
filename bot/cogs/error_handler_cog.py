"""
Enhanced error handling system for the AccountME Discord Bot
Provides user-friendly error messages with helpful guidance
"""

import discord
from discord.ext import commands
import logging
import traceback
import sys
import sqlite3
from datetime import datetime

logger = logging.getLogger("accountme_bot.error_handler")

class ErrorHandlerCog(commands.Cog, name="Error Handler"):
    """Enhanced global error handling for all commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.error_count = 0
        self.common_typos = {
            "inventry": "inventory",
            "inventroy": "inventory",
            "expence": "expense",
            "expens": "expense",
            "finacial": "financial",
            "finantial": "financial",
            "backup": "backup",
            "bakup": "backup",
            "reprot": "report",
            "raport": "report",
            "produt": "product",
            "pruduct": "product",
            "verfy": "verify",
            "ajust": "adjust",
            "adjst": "adjust",
            "delet": "delete",
            "dlt": "delete",
            "imprt": "import",
            "exprt": "export",
            "shedule": "schedule",
            "schedual": "schedule",
            "sistem": "system",
            "systm": "system",
            "hlth": "health",
            "healh": "health",
        }
    
    def _find_similar_command(self, command_name):
        """Find similar commands based on name similarity"""
        if not command_name:
            return []
        
        command_name = command_name.lower()
        all_commands = list(self.bot.commands)
        similar_commands = []
        
        # Check for common typos first
        for typo, correction in self.common_typos.items():
            if typo in command_name:
                corrected_name = command_name.replace(typo, correction)
                for cmd in all_commands:
                    if cmd.name.startswith(corrected_name) or corrected_name.startswith(cmd.name):
                        similar_commands.append(cmd.name)
        
        # Check for partial matches
        for cmd in all_commands:
            # Exact match but wrong case
            if cmd.name.lower() == command_name:
                return [cmd.name]
            
            # Partial match (command starts with input or input starts with command)
            if cmd.name.lower().startswith(command_name) or command_name.startswith(cmd.name.lower()):
                similar_commands.append(cmd.name)
            
            # Check aliases
            for alias in cmd.aliases:
                if alias.lower() == command_name:
                    return [cmd.name]
                if alias.lower().startswith(command_name) or command_name.startswith(alias.lower()):
                    similar_commands.append(cmd.name)
        
        # Return unique commands
        return list(set(similar_commands))
    
    def _get_command_examples(self, command):
        """Get examples for a command based on its name"""
        examples = {}
        
        # Inventory commands
        examples["inventory"] = [
            f"{command.prefix}inventory - Show inventory summary",
            f"{command.prefix}inventory TS001 - Show details for product with SKU TS001"
        ]
        examples["addproduct"] = [
            f"{command.prefix}addproduct - Start guided product creation",
            f"{command.prefix}addproduct blank - Create a blank clothing item"
        ]
        examples["updateproduct"] = [
            f"{command.prefix}updateproduct TS001 - Update product with SKU TS001"
        ]
        examples["adjustinventory"] = [
            f"{command.prefix}adjustinventory TS001 5 - Add 5 units to product TS001",
            f"{command.prefix}adjustinventory TS001 -3 Damaged - Remove 3 units with reason"
        ]
        examples["verifyinventory"] = [
            f"{command.prefix}verifyinventory - Start inventory verification process",
            f"{command.prefix}verifyinventory TS001 - Verify specific product"
        ]
        examples["inventoryreport"] = [
            f"{command.prefix}inventoryreport stock - Show current stock levels",
            f"{command.prefix}inventoryreport lowstock 10 - Show products with less than 10 units"
        ]
        
        # Finance commands
        examples["addexpense"] = [
            f"{command.prefix}addexpense - Start guided expense entry"
        ]
        examples["uploadreceipt"] = [
            f"{command.prefix}uploadreceipt - Upload and process a receipt image"
        ]
        examples["expenses"] = [
            f"{command.prefix}expenses - Show all expenses",
            f"{command.prefix}expenses month - Show expenses for current month"
        ]
        examples["addsale"] = [
            f"{command.prefix}addsale - Start guided sale entry"
        ]
        examples["sales"] = [
            f"{command.prefix}sales - Show all sales",
            f"{command.prefix}sales week - Show sales for current week"
        ]
        examples["financialreport"] = [
            f"{command.prefix}financialreport sales - Generate sales report",
            f"{command.prefix}financialreport expenses - Generate expense report"
        ]
        
        # Backup commands
        examples["backup"] = [
            f"{command.prefix}backup - Create a manual backup"
        ]
        examples["listbackups"] = [
            f"{command.prefix}listbackups - Show available backups"
        ]
        examples["restore"] = [
            f"{command.prefix}restore <backup_id> - Restore from a backup"
        ]
        
        # System commands
        examples["systemstatus"] = [
            f"{command.prefix}systemstatus - Show system status information"
        ]
        examples["healthcheck"] = [
            f"{command.prefix}healthcheck - Run a system health check"
        ]
        
        # Help command
        examples["help"] = [
            f"{command.prefix}help - Show all command categories",
            f"{command.prefix}help inventory - Show help for inventory category",
            f"{command.prefix}help addproduct - Show help for specific command"
        ]
        
        # Return examples for the command or empty list if none found
        return examples.get(command.name, [])
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """
        Enhanced global error handler for all command errors
        
        Args:
            ctx: Command context
            error: The error that was raised
        """
        # Get the original error if it's wrapped in a CommandInvokeError
        error = getattr(error, 'original', error)
        
        # Skip if the command has its own error handler
        if hasattr(ctx.command, 'on_error'):
            return
        
        # Skip if the cog has its own error handler
        if ctx.cog and ctx.cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
            return
        
        # Increment error count for tracking
        self.error_count += 1
        
        # Create embed for error response
        embed = discord.Embed(
            title="❌ Command Error",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        # Add command context when available
        if ctx.command:
            embed.set_footer(text=f"Command: {ctx.prefix}{ctx.command.qualified_name}")
        
        # Handle different types of errors with enhanced messages
        if isinstance(error, commands.CommandNotFound):
            command_name = ctx.message.content.split()[0][len(ctx.prefix):]
            similar_commands = self._find_similar_command(command_name)
            
            embed.description = f"Command `{command_name}` not found."
            
            if similar_commands:
                suggestions = "\n".join([f"• `{ctx.prefix}{cmd}`" for cmd in similar_commands[:3]])
                embed.add_field(
                    name="Did you mean?",
                    value=suggestions,
                    inline=False
                )
            
            embed.add_field(
                name="Available Commands",
                value=f"Use `{ctx.prefix}help` to see all available commands.",
                inline=False
            )
        
        elif isinstance(error, commands.DisabledCommand):
            embed.description = f"Command `{ctx.command}` is currently disabled."
            embed.add_field(
                name="Reason",
                value="This command may be under maintenance or temporarily unavailable.",
                inline=False
            )
        
        elif isinstance(error, commands.MissingRequiredArgument):
            embed.description = f"Missing required argument: `{error.param.name}`"
            
            # Add command usage
            embed.add_field(
                name="Correct Usage",
                value=f"`{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`",
                inline=False
            )
            
            # Add examples if available
            examples = self._get_command_examples(ctx.command)
            if examples:
                embed.add_field(
                    name="Examples",
                    value="\n".join(examples),
                    inline=False
                )
            
            # Add parameter-specific help
            param_help = ""
            if error.param.name == "sku":
                param_help = "SKU is a unique identifier for a product. You can find SKUs using the `inventory` command."
            elif error.param.name == "category":
                param_help = "Valid categories are: blank, dtf, other"
            elif error.param.name == "quantity":
                param_help = "Quantity must be a number. Use positive numbers to add, negative to remove."
            
            if param_help:
                embed.add_field(
                    name="Parameter Help",
                    value=param_help,
                    inline=False
                )
        
        elif isinstance(error, commands.BadArgument):
            embed.description = f"Invalid argument provided: {str(error)}"
            
            # Add command usage
            embed.add_field(
                name="Correct Usage",
                value=f"`{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`",
                inline=False
            )
            
            # Add examples if available
            examples = self._get_command_examples(ctx.command)
            if examples:
                embed.add_field(
                    name="Examples",
                    value="\n".join(examples),
                    inline=False
                )
            
            # Add specific guidance based on the error message
            if "Converting to" in str(error):
                if "int" in str(error):
                    embed.add_field(
                        name="Hint",
                        value="This parameter requires a whole number (e.g., 5, 10, -3).",
                        inline=False
                    )
                elif "float" in str(error):
                    embed.add_field(
                        name="Hint",
                        value="This parameter requires a number (e.g., 10.99, 5.50).",
                        inline=False
                    )
        
        elif isinstance(error, commands.MissingPermissions):
            embed.description = f"You don't have permission to use this command."
            missing_perms = [perm.replace('_', ' ').title() for perm in error.missing_permissions]
            embed.add_field(
                name="Missing Permissions",
                value=", ".join(missing_perms),
                inline=False
            )
            embed.add_field(
                name="What to do",
                value="Contact a server administrator to grant you the necessary permissions.",
                inline=False
            )
        
        elif isinstance(error, commands.BotMissingPermissions):
            embed.description = f"I don't have the necessary permissions to execute this command."
            missing_perms = [perm.replace('_', ' ').title() for perm in error.missing_permissions]
            embed.add_field(
                name="Missing Permissions",
                value=", ".join(missing_perms),
                inline=False
            )
            embed.add_field(
                name="How to fix",
                value="A server administrator needs to grant me these permissions in the server settings.",
                inline=False
            )
        
        elif isinstance(error, commands.CommandOnCooldown):
            embed.description = f"This command is on cooldown."
            embed.add_field(
                name="Try again in",
                value=f"{error.retry_after:.1f} seconds",
                inline=False
            )
            embed.add_field(
                name="Why cooldowns exist",
                value="Cooldowns prevent command spam and ensure the bot runs smoothly for everyone.",
                inline=False
            )
        
        elif isinstance(error, commands.NoPrivateMessage):
            embed.description = f"This command cannot be used in private messages."
            embed.add_field(
                name="How to use",
                value="Use this command in a server where the bot is present.",
                inline=False
            )
        
        elif isinstance(error, commands.PrivateMessageOnly):
            embed.description = f"This command can only be used in private messages."
            embed.add_field(
                name="How to use",
                value=f"Send a direct message to the bot with `{ctx.prefix}{ctx.command.qualified_name}`",
                inline=False
            )
        
        elif isinstance(error, commands.NotOwner):
            embed.description = f"This command can only be used by the bot owner."
            embed.add_field(
                name="Why this restriction exists",
                value="This command contains sensitive functionality that requires owner privileges.",
                inline=False
            )
        
        elif isinstance(error, sqlite3.Error):
            # Handle database errors
            embed.description = f"A database error occurred while processing your command."
            
            if "UNIQUE constraint failed" in str(error):
                embed.add_field(
                    name="Error Details",
                    value="A unique constraint was violated. This usually means an item with the same identifier already exists.",
                    inline=False
                )
                embed.add_field(
                    name="Suggestion",
                    value="Try using a different SKU or identifier.",
                    inline=False
                )
            elif "no such table" in str(error):
                embed.add_field(
                    name="Error Details",
                    value="The database structure appears to be incomplete or corrupted.",
                    inline=False
                )
                embed.add_field(
                    name="Suggestion",
                    value="Contact the bot administrator to check the database integrity.",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Error Details",
                    value=f"Database error: {str(error)}",
                    inline=False
                )
            
            # Log the error with traceback
            logger.error(f"Database error in command {ctx.command}: {str(error)}")
            logger.error(traceback.format_exception(type(error), error, error.__traceback__))
        
        elif isinstance(error, ValueError):
            # Handle value errors (often from user input)
            embed.description = f"Invalid value provided: {str(error)}"
            
            if "invalid literal for int" in str(error):
                embed.add_field(
                    name="Error Details",
                    value="A whole number was expected, but I received something else.",
                    inline=False
                )
                embed.add_field(
                    name="Example",
                    value=f"Try `{ctx.prefix}{ctx.command.qualified_name} 5` instead of using text or decimal numbers.",
                    inline=False
                )
            elif "could not convert string to float" in str(error):
                embed.add_field(
                    name="Error Details",
                    value="A number was expected, but I received something else.",
                    inline=False
                )
                embed.add_field(
                    name="Example",
                    value=f"Try `{ctx.prefix}{ctx.command.qualified_name} 10.99` for a price or quantity.",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Suggestion",
                    value="Check the command usage and try again with valid values.",
                    inline=False
                )
        
        else:
            # For unexpected errors, provide a generic message and log the error
            embed.description = f"An unexpected error occurred while processing your command."
            
            # Add error details in a separate field
            embed.add_field(
                name="Error Details",
                value=f"`{str(error)}`",
                inline=False
            )
            
            # Add command recovery suggestions
            embed.add_field(
                name="What you can try",
                value="• Check your command syntax and try again\n"
                      "• Wait a few moments and retry the command\n"
                      "• Try a different approach to accomplish your task",
                inline=False
            )
            
            # Log the error with traceback
            logger.error(f"Unhandled error in command {ctx.command}: {str(error)}")
            logger.error(traceback.format_exception(type(error), error, error.__traceback__))
            
            # Add a note about reporting the error
            embed.add_field(
                name="Note",
                value="This error has been logged. If the problem persists, please report this to the bot administrator.",
                inline=False
            )
        
        # Send the error message
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        """
        Enhanced global error handler for all events
        
        Args:
            event: The event that raised the error
            args: Arguments passed to the event
            kwargs: Keyword arguments passed to the event
        """
        # Get the error information
        error_type, error, error_traceback = sys.exc_info()
        
        # Log the error with detailed information
        logger.error(f"Unhandled error in event {event}: {str(error)}")
        logger.error(f"Error type: {error_type.__name__}")
        logger.error(f"Event args: {args}")
        logger.error(''.join(traceback.format_exception(error_type, error, error_traceback)))
        
        # Increment error count
        self.error_count += 1

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(ErrorHandlerCog(bot))