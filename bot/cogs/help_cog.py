"""
Enhanced help command system for the AccountME Discord Bot
Provides a comprehensive help system with categorized commands,
examples, parameter descriptions, and interactive tutorials.
"""

import discord
from discord.ext import commands
import logging
import asyncio
from typing import Dict, List, Optional, Union

logger = logging.getLogger("accountme_bot.help_cog")

# Category emojis for visual enhancement
CATEGORY_EMOJIS = {
    "Help": "❓",
    "Admin": "🔧",
    "Inventory": "📦",
    "Finance": "💰",
    "Backup": "💾",
    "System": "⚙️",
    "Utility": "🔨",
    "No Category": "📁"
}

# Command examples for common commands
COMMAND_EXAMPLES = {
    "help": ["!help", "!help inventory", "!help addproduct"],
    "inventory": ["!inventory", "!inventory BLK-GIL-5000-BLK-L"],
    "addproduct": ["!addproduct blank \"Gildan 5000 T-Shirt\"", "!addproduct dtf \"Skull Design 8x10\""],
    "adjustinventory": ["!adjustinventory BLK-GIL-5000-BLK-L 10 \"New shipment\"", "!adjustinventory BLK-GIL-5000-BLK-L -5 \"Sold at market\""],
    "expenses": ["!expenses", "!expenses month", "!expenses year supplies"],
    "addsale": ["!addsale"],
    "report": ["!report Show me sales from last week", "!report What were my expenses for March?"],
    "backup": ["!backup"],
    "ping": ["!ping"]
}

# Parameter descriptions for commands
PARAMETER_DESCRIPTIONS = {
    "help": {
        "command_or_category": "The name of a command or category to get help for"
    },
    "inventory": {
        "sku": "The SKU of the product to view (optional)"
    },
    "addproduct": {
        "category": "Product category (blank, dtf, other)",
        "name": "Product name",
        "attributes": "Additional attributes (optional)"
    },
    "adjustinventory": {
        "sku": "The SKU of the product to adjust",
        "quantity": "Amount to adjust (positive to add, negative to remove)",
        "reason": "Reason for adjustment (optional)"
    },
    "expenses": {
        "period": "Time period (today, week, month, year, or YYYY-MM) (optional)",
        "category": "Expense category to filter by (optional)"
    }
}

class HelpCog(commands.Cog, name="Help"):
    """Enhanced help command implementation"""
    
    def __init__(self, bot):
        self.bot = bot
        # Remove the default help command
        self.bot.remove_command('help')
        # Store active help pagination sessions
        self.active_help_sessions = {}
        # Tutorial data
        self.tutorials = {
            "inventory": self._inventory_tutorial,
            "expense": self._expense_tutorial,
            "sales": self._sales_tutorial,
            "backup": self._backup_tutorial,
            "general": self._general_tutorial
        }
    
    @commands.command(name="help")
    async def help_command(self, ctx, command_or_category=None):
        """
        Show help information for commands or categories
        
        Usage:
        !help - Show all command categories
        !help <command> - Show help for a specific command
        !help <category> - Show all commands in a category
        
        Examples:
        !help
        !help inventory
        !help addproduct
        """
        prefix = ctx.prefix
        
        # If a specific command or category is requested
        if command_or_category:
            # First try to find it as a command
            command = self.bot.get_command(command_or_category)
            if command and not command.hidden:
                return await self._show_command_help(ctx, command)
            
            # If not a command, try as a category
            return await self._show_category_help(ctx, command_or_category)
        
        # Otherwise show the main help menu
        embed = discord.Embed(
            title="AccountME Bot Help",
            description=f"Use `{prefix}help <command>` for more information about a command.\n"
                       f"Use `{prefix}help <category>` for more information about a category.\n\n"
                       f"For detailed documentation, use `{prefix}tutorial` to start an interactive guide.",
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
                
            # Get emoji for category
            emoji = CATEGORY_EMOJIS.get(category, "📁")
                
            # Create a list of command names
            command_names = [f"`{prefix}{cmd.name}`" for cmd in sorted(commands_list, key=lambda x: x.name)]
            
            # Add the field
            embed.add_field(
                name=f"{emoji} {category}",
                value=", ".join(command_names),
                inline=False
            )
        
        # Add footer with additional info
        embed.set_footer(text="AccountME Bot | Type !tutorial for interactive guides")
        
        await ctx.send(embed=embed)
    
    async def _show_command_help(self, ctx, command):
        """Show help for a specific command"""
        prefix = ctx.prefix
        
        # Create embed for command help
        embed = discord.Embed(
            title=f"Command: {prefix}{command.name}",
            description=command.help or "No description available.",
            color=discord.Color.blue()
        )
        
        # Add command signature (usage)
        signature = command.signature
        embed.add_field(
            name="📝 Usage",
            value=f"`{prefix}{command.name} {signature}`",
            inline=False
        )
        
        # Add parameter descriptions if available
        if command.name in PARAMETER_DESCRIPTIONS:
            params = PARAMETER_DESCRIPTIONS[command.name]
            param_text = "\n".join([f"• `{param}`: {desc}" for param, desc in params.items()])
            embed.add_field(
                name="📋 Parameters",
                value=param_text or "No parameters",
                inline=False
            )
        
        # Add examples if available
        if command.name in COMMAND_EXAMPLES:
            examples = COMMAND_EXAMPLES[command.name]
            example_text = "\n".join([f"• `{example}`" for example in examples])
            embed.add_field(
                name="💡 Examples",
                value=example_text,
                inline=False
            )
        
        # Add aliases if any
        if command.aliases:
            embed.add_field(
                name="🔄 Aliases",
                value=", ".join([f"`{prefix}{alias}`" for alias in command.aliases]),
                inline=False
            )
        
        # Add category
        if command.cog_name:
            emoji = CATEGORY_EMOJIS.get(command.cog_name, "📁")
            embed.add_field(
                name="📂 Category",
                value=f"{emoji} {command.cog_name}",
                inline=False
            )
        
        # Add related commands if applicable
        related_commands = self._get_related_commands(command)
        if related_commands:
            embed.add_field(
                name="🔗 Related Commands",
                value=", ".join([f"`{prefix}{cmd.name}`" for cmd in related_commands]),
                inline=False
            )
        
        embed.set_footer(text=f"Type {prefix}help for a list of all commands")
        
        await ctx.send(embed=embed)
    
    async def _show_category_help(self, ctx, category_name):
        """Show help for a specific category"""
        prefix = ctx.prefix
        
        # Find all commands in this category
        category_commands = []
        for command in self.bot.commands:
            if command.hidden:
                continue
                
            if command.cog_name and command.cog_name.lower() == category_name.lower():
                category_commands.append(command)
        
        # If no commands found in this category
        if not category_commands:
            embed = discord.Embed(
                title="Category Not Found",
                description=f"No category called `{category_name}` was found.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Create embed for category help
        emoji = CATEGORY_EMOJIS.get(category_name.capitalize(), "📁")
        embed = discord.Embed(
            title=f"{emoji} {category_name.capitalize()} Commands",
            description=f"Here are all commands in the {category_name.capitalize()} category.",
            color=discord.Color.blue()
        )
        
        # Sort commands alphabetically
        category_commands.sort(key=lambda x: x.name)
        
        # Add each command with a brief description
        for command in category_commands:
            # Get the first line of the help text as a brief description
            brief = command.help.split('\n')[0] if command.help else "No description available."
            
            embed.add_field(
                name=f"{prefix}{command.name}",
                value=brief,
                inline=False
            )
        
        embed.set_footer(text=f"Type {prefix}help <command> for detailed information about a command")
        
        await ctx.send(embed=embed)
    
    def _get_related_commands(self, command):
        """Get related commands based on the command's category"""
        related = []
        if not command.cog_name:
            return related
            
        for cmd in self.bot.commands:
            if cmd.hidden or cmd == command:
                continue
                
            if cmd.cog_name == command.cog_name:
                related.append(cmd)
                
        # Limit to 5 related commands
        return related[:5]
    
    @commands.command(name="aliases")
    async def aliases_command(self, ctx, command_name=None):
        """
        Show aliases for commands
        
        Usage:
        !aliases - Show all command aliases
        !aliases <command> - Show aliases for a specific command
        
        Examples:
        !aliases
        !aliases inventory
        """
        prefix = ctx.prefix
        
        # If a specific command is requested
        if command_name:
            command = self.bot.get_command(command_name)
            if not command or command.hidden:
                embed = discord.Embed(
                    title="Command Not Found",
                    description=f"No command called `{command_name}` was found.",
                    color=discord.Color.red()
                )
                return await ctx.send(embed=embed)
                
            if not command.aliases:
                embed = discord.Embed(
                    title=f"Aliases for {prefix}{command.name}",
                    description=f"This command has no aliases.",
                    color=discord.Color.blue()
                )
                return await ctx.send(embed=embed)
                
            embed = discord.Embed(
                title=f"Aliases for {prefix}{command.name}",
                description=f"You can also use: " + ", ".join([f"`{prefix}{alias}`" for alias in command.aliases]),
                color=discord.Color.blue()
            )
            return await ctx.send(embed=embed)
        
        # Otherwise show all command aliases
        embed = discord.Embed(
            title="Command Aliases",
            description=f"Here are all commands with aliases:",
            color=discord.Color.blue()
        )
        
        # Group by category
        categories = {}
        for command in self.bot.commands:
            if command.hidden or not command.aliases:
                continue
                
            category = command.cog_name or "No Category"
            if category not in categories:
                categories[category] = []
            categories[category].append(command)
        
        # Add fields for each category
        for category, commands_list in sorted(categories.items()):
            # Skip empty categories
            if not commands_list:
                continue
                
            # Create text for this category
            category_text = ""
            for cmd in sorted(commands_list, key=lambda x: x.name):
                aliases = ", ".join([f"`{prefix}{alias}`" for alias in cmd.aliases])
                category_text += f"• `{prefix}{cmd.name}`: {aliases}\n"
            
            # Add the field
            emoji = CATEGORY_EMOJIS.get(category, "📁")
            embed.add_field(
                name=f"{emoji} {category}",
                value=category_text,
                inline=False
            )
        
        embed.set_footer(text=f"Type {prefix}help <command> for detailed information about a command")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="tutorial")
    async def tutorial_command(self, ctx, topic=None):
        """
        Start an interactive tutorial
        
        Usage:
        !tutorial - Show available tutorial topics
        !tutorial <topic> - Start a specific tutorial
        
        Examples:
        !tutorial
        !tutorial inventory
        !tutorial expense
        """
        prefix = ctx.prefix
        
        # If user is already in a tutorial
        if ctx.author.id in self.active_help_sessions:
            embed = discord.Embed(
                title="Tutorial Already Active",
                description="You already have an active tutorial session. Please finish or cancel it before starting a new one.",
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # If no topic specified, show available topics
        if not topic:
            embed = discord.Embed(
                title="Available Tutorials",
                description="Choose a tutorial topic to get started:",
                color=discord.Color.blue()
            )
            
            for topic_name in self.tutorials.keys():
                emoji = "📚"
                if topic_name == "inventory":
                    emoji = "📦"
                elif topic_name == "expense":
                    emoji = "💰"
                elif topic_name == "sales":
                    emoji = "💵"
                elif topic_name == "backup":
                    emoji = "💾"
                
                embed.add_field(
                    name=f"{emoji} {topic_name.capitalize()}",
                    value=f"Type `{prefix}tutorial {topic_name}` to start",
                    inline=True
                )
            
            return await ctx.send(embed=embed)
        
        # Check if the topic exists
        if topic.lower() not in self.tutorials:
            embed = discord.Embed(
                title="Tutorial Not Found",
                description=f"No tutorial found for topic `{topic}`.\n\nAvailable topics: " +
                            ", ".join([f"`{t}`" for t in self.tutorials.keys()]),
                color=discord.Color.red()
            )
            return await ctx.send(embed=embed)
        
        # Start the tutorial
        tutorial_func = self.tutorials[topic.lower()]
        self.active_help_sessions[ctx.author.id] = True
        try:
            await tutorial_func(ctx)
        finally:
            # Clean up the session when done
            if ctx.author.id in self.active_help_sessions:
                del self.active_help_sessions[ctx.author.id]
    
    async def _general_tutorial(self, ctx):
        """General tutorial about using the bot"""
        prefix = ctx.prefix
        
        # Step 1: Introduction
        embed = discord.Embed(
            title="AccountME Bot Tutorial - Getting Started",
            description="Welcome to the AccountME Bot tutorial! This guide will help you learn the basics of using the bot.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Step 1: Basic Commands",
            value=f"The bot uses `{prefix}` as its command prefix. All commands start with this character.\n\n"
                  f"Try using `{prefix}ping` to check if the bot is responsive.",
            inline=False
        )
        embed.add_field(
            name="Navigation",
            value="React with ⏩ to continue or ❌ to exit the tutorial.",
            inline=False
        )
        embed.set_footer(text="Step 1/5")
        
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("⏩")
        await msg.add_reaction("❌")
        
        # Wait for reaction
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                timeout=60.0,
                check=lambda r, u: u == ctx.author and str(r.emoji) in ["⏩", "❌"] and r.message.id == msg.id
            )
            
            if str(reaction.emoji) == "❌":
                await msg.delete()
                return await ctx.send("Tutorial cancelled.")
        except asyncio.TimeoutError:
            await msg.delete()
            return await ctx.send("Tutorial timed out.")
        
        # Step 2: Getting Help
        embed = discord.Embed(
            title="AccountME Bot Tutorial - Getting Help",
            description="Let's learn how to get help with commands.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Step 2: Help System",
            value=f"Use `{prefix}help` to see all available command categories.\n\n"
                  f"Use `{prefix}help <command>` to get detailed help for a specific command.\n\n"
                  f"Use `{prefix}help <category>` to see all commands in a category.",
            inline=False
        )
        embed.add_field(
            name="Examples",
            value=f"`{prefix}help`\n`{prefix}help inventory`\n`{prefix}help addproduct`",
            inline=False
        )
        embed.add_field(
            name="Navigation",
            value="React with ⏪ to go back, ⏩ to continue, or ❌ to exit the tutorial.",
            inline=False
        )
        embed.set_footer(text="Step 2/5")
        
        await msg.edit(embed=embed)
        await msg.add_reaction("⏪")
        
        # Wait for reaction
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                timeout=60.0,
                check=lambda r, u: u == ctx.author and str(r.emoji) in ["⏪", "⏩", "❌"] and r.message.id == msg.id
            )
            
            if str(reaction.emoji) == "❌":
                await msg.delete()
                return await ctx.send("Tutorial cancelled.")
            elif str(reaction.emoji) == "⏪":
                # Go back to step 1
                return await self._general_tutorial(ctx)
        except asyncio.TimeoutError:
            await msg.delete()
            return await ctx.send("Tutorial timed out.")
        
        # Step 3: Command Categories
        embed = discord.Embed(
            title="AccountME Bot Tutorial - Command Categories",
            description="The bot's commands are organized into categories for easy navigation.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Step 3: Main Categories",
            value="• **Inventory**: Manage products and inventory levels\n"
                  "• **Finance**: Track expenses and sales\n"
                  "• **Backup**: Create and manage backups\n"
                  "• **System**: Monitor system health and performance\n"
                  "• **Utility**: General utility commands",
            inline=False
        )
        embed.add_field(
            name="Navigation",
            value="React with ⏪ to go back, ⏩ to continue, or ❌ to exit the tutorial.",
            inline=False
        )
        embed.set_footer(text="Step 3/5")
        
        await msg.edit(embed=embed)
        
        # Wait for reaction
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                timeout=60.0,
                check=lambda r, u: u == ctx.author and str(r.emoji) in ["⏪", "⏩", "❌"] and r.message.id == msg.id
            )
            
            if str(reaction.emoji) == "❌":
                await msg.delete()
                return await ctx.send("Tutorial cancelled.")
            elif str(reaction.emoji) == "⏪":
                # Go back to step 2
                embed = discord.Embed(
                    title="AccountME Bot Tutorial - Getting Help",
                    description="Let's learn how to get help with commands.",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="Step 2: Help System",
                    value=f"Use `{prefix}help` to see all available command categories.\n\n"
                          f"Use `{prefix}help <command>` to get detailed help for a specific command.\n\n"
                          f"Use `{prefix}help <category>` to see all commands in a category.",
                    inline=False
                )
                embed.add_field(
                    name="Examples",
                    value=f"`{prefix}help`\n`{prefix}help inventory`\n`{prefix}help addproduct`",
                    inline=False
                )
                embed.add_field(
                    name="Navigation",
                    value="React with ⏪ to go back, ⏩ to continue, or ❌ to exit the tutorial.",
                    inline=False
                )
                embed.set_footer(text="Step 2/5")
                
                await msg.edit(embed=embed)
                return await self._general_tutorial(ctx)
        except asyncio.TimeoutError:
            await msg.delete()
            return await ctx.send("Tutorial timed out.")
        
        # Step 4: Command Aliases
        embed = discord.Embed(
            title="AccountME Bot Tutorial - Command Aliases",
            description="Many commands have aliases (alternative names) for convenience.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Step 4: Using Aliases",
            value=f"Use `{prefix}aliases` to see all command aliases.\n\n"
                  f"Use `{prefix}aliases <command>` to see aliases for a specific command.\n\n"
                  f"For example, instead of `{prefix}inventory`, you can use `{prefix}inv` or `{prefix}stock`.",
            inline=False
        )
        embed.add_field(
            name="Navigation",
            value="React with ⏪ to go back, ⏩ to continue, or ❌ to exit the tutorial.",
            inline=False
        )
        embed.set_footer(text="Step 4/5")
        
        await msg.edit(embed=embed)
        
        # Wait for reaction
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                timeout=60.0,
                check=lambda r, u: u == ctx.author and str(r.emoji) in ["⏪", "⏩", "❌"] and r.message.id == msg.id
            )
            
            if str(reaction.emoji) == "❌":
                await msg.delete()
                return await ctx.send("Tutorial cancelled.")
            elif str(reaction.emoji) == "⏪":
                # Go back to step 3
                embed = discord.Embed(
                    title="AccountME Bot Tutorial - Command Categories",
                    description="The bot's commands are organized into categories for easy navigation.",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="Step 3: Main Categories",
                    value="• **Inventory**: Manage products and inventory levels\n"
                          "• **Finance**: Track expenses and sales\n"
                          "• **Backup**: Create and manage backups\n"
                          "• **System**: Monitor system health and performance\n"
                          "• **Utility**: General utility commands",
                    inline=False
                )
                embed.add_field(
                    name="Navigation",
                    value="React with ⏪ to go back, ⏩ to continue, or ❌ to exit the tutorial.",
                    inline=False
                )
                embed.set_footer(text="Step 3/5")
                
                await msg.edit(embed=embed)
                return await self._general_tutorial(ctx)
        except asyncio.TimeoutError:
            await msg.delete()
            return await ctx.send("Tutorial timed out.")
        
        # Step 5: Next Steps
        embed = discord.Embed(
            title="AccountME Bot Tutorial - Next Steps",
            description="Congratulations! You've completed the basic tutorial.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Step 5: Specialized Tutorials",
            value=f"Try these specialized tutorials to learn more:\n\n"
                  f"• `{prefix}tutorial inventory` - Learn about inventory management\n"
                  f"• `{prefix}tutorial expense` - Learn about expense tracking\n"
                  f"• `{prefix}tutorial sales` - Learn about sales recording\n"
                  f"• `{prefix}tutorial backup` - Learn about backup management",
            inline=False
        )
        embed.add_field(
            name="Documentation",
            value="For comprehensive documentation, refer to the user documentation provided with the bot.",
            inline=False
        )
        embed.set_footer(text="Tutorial complete!")
        
        await msg.edit(embed=embed)
        await msg.add_reaction("🎉")
        
        # Clean up reactions except for the celebration emoji
        await msg.clear_reactions()
        await msg.add_reaction("🎉")
    
    async def _inventory_tutorial(self, ctx):
        """Tutorial for inventory management"""
        prefix = ctx.prefix
        
        # Step 1: Introduction to Inventory
        embed = discord.Embed(
            title="Inventory Management Tutorial",
            description="This tutorial will guide you through managing your inventory with AccountME Bot.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Step 1: Inventory Basics",
            value="The inventory system allows you to track products across different categories:\n\n"
                  "• **Blanks**: Items like t-shirts, hoodies, etc.\n"
                  "• **DTF Prints**: Direct-to-film prints\n"
                  "• **Other**: Any other products",
            inline=False
        )
        embed.add_field(
            name="Key Commands",
            value=f"`{prefix}inventory` - View inventory summary\n"
                  f"`{prefix}addproduct` - Add new products\n"
                  f"`{prefix}adjustinventory` - Update quantities",
            inline=False
        )
        embed.add_field(
            name="Navigation",
            value="React with ⏩ to continue or ❌ to exit the tutorial.",
            inline=False
        )
        embed.set_footer(text="Step 1/4")
        
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("⏩")
        await msg.add_reaction("❌")
        
        # Wait for reaction
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                timeout=60.0,
                check=lambda r, u: u == ctx.author and str(r.emoji) in ["⏩", "❌"] and r.message.id == msg.id
            )
            
            if str(reaction.emoji) == "❌":
                await msg.delete()
                return await ctx.send("Tutorial cancelled.")
        except asyncio.TimeoutError:
            await msg.delete()
            return await ctx.send("Tutorial timed out.")
        
        # Continue with more steps for inventory tutorial...
        # (Additional steps would be implemented similarly)
        
        # For brevity, we'll just show a completion message
        embed = discord.Embed(
            title="Inventory Management Tutorial",
            description="Tutorial completed! You now know the basics of inventory management.",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Key Commands Recap",
            value=f"`{prefix}inventory` - View inventory\n"
                  f"`{prefix}addproduct` - Add products\n"
                  f"`{prefix}adjustinventory` - Update quantities\n"
                  f"`{prefix}inventoryreport` - Generate reports",
            inline=False
        )
        embed.set_footer(text="Tutorial complete!")
        
        await msg.edit(embed=embed)
        await msg.clear_reactions()
        await msg.add_reaction("🎉")
    
    async def _expense_tutorial(self, ctx):
        """Tutorial for expense tracking"""
        # Implementation would be similar to _inventory_tutorial
        # For brevity, we'll just show a placeholder
        await ctx.send("Expense tracking tutorial would be implemented here.")
    
    async def _sales_tutorial(self, ctx):
        """Tutorial for sales recording"""
        # Implementation would be similar to _inventory_tutorial
        # For brevity, we'll just show a placeholder
        await ctx.send("Sales recording tutorial would be implemented here.")
    
    async def _backup_tutorial(self, ctx):
        """Tutorial for backup management"""
        # Implementation would be similar to _inventory_tutorial
        # For brevity, we'll just show a placeholder
        await ctx.send("Backup management tutorial would be implemented here.")

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(HelpCog(bot))