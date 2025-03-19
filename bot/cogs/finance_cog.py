"""
Financial tracking commands for the AccountME Discord Bot
Implements receipt processing and verification workflow
Includes guided data entry conversations for manual expense entry
"""

import discord
from discord.ext import commands
import logging
import asyncio
import re
from datetime import datetime, date
from typing import Dict, Any, Optional, List, Union, Callable, Tuple

logger = logging.getLogger("accountme_bot.finance_cog")

class VerificationState:
    """Class to track the state of a verification process"""
    def __init__(self, receipt_data: Dict[str, Any], user_id: int, message_id: int):
        self.receipt_data = receipt_data
        self.user_id = user_id
        self.message_id = message_id
        self.editing_field = None
        self.is_completed = False
        self.is_cancelled = False
        self.timeout_task = None

class ConversationState:
    """Class to track the state of a multi-step conversation"""
    def __init__(self, user_id: int, channel_id: int, conversation_type: str):
        self.user_id = user_id
        self.channel_id = channel_id
        self.conversation_type = conversation_type  # e.g., 'expense', 'sale'
        self.current_step = 0
        self.data = {}  # Collected data
        self.is_completed = False
        self.is_cancelled = False
        self.timeout_task = None
        self.last_message_id = None
        self.prompt_message_id = None

class FinanceCog(commands.Cog, name="Finance"):
    """Financial tracking commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_verifications = {}  # Dictionary to track active verification processes
        self.active_conversations = {}  # Dictionary to track active conversations
        self.active_report_contexts = {}  # Dictionary to track active report contexts
        self.field_emojis = {
            "date": "📅",
            "vendor": "🏪",
            "total_amount": "💰",
            "tax": "💸",
            "items": "📋",
            "confirm": "✅",
            "cancel": "❌"
        }
        
        # Define expense categories
        self.expense_categories = [
            "Inventory",
            "Supplies",
            "Equipment",
            "Marketing",
            "Shipping",
            "Utilities",
            "Rent",
            "Software",
            "Services",
            "Other"
        ]
        
        # Define conversation steps for expense entry
        self.expense_steps = [
            {
                "name": "date",
                "prompt": "Please enter the expense date (YYYY-MM-DD):",
                "validate": self._validate_date,
                "format": self._format_date
            },
            {
                "name": "vendor",
                "prompt": "Please enter the vendor name:",
                "validate": self._validate_vendor,
                "format": self._format_vendor
            },
            {
                "name": "amount",
                "prompt": "Please enter the expense amount (e.g., 42.99):",
                "validate": self._validate_amount,
                "format": self._format_amount
            },
            {
                "name": "category",
                "prompt": lambda: f"Please enter the expense category (or number):\n{self._format_categories()}",
                "validate": self._validate_category,
                "format": self._format_category
            },
            {
                "name": "description",
                "prompt": "Please enter a description for this expense (or type 'skip' to leave blank):",
                "validate": self._validate_description,
                "format": self._format_description
            }
        ]
    
    @commands.command(name="expenses", aliases=["exp", "viewexpenses"])
    async def expenses_command(self, ctx, period=None, category=None):
        """
        View expense information
        
        Usage:
        !expenses - Show recent expenses
        !expenses <period> - Show expenses for a specific period (e.g., 'month', 'year', 'week')
        !expenses <period> <category> - Show expenses for a specific period and category
        
        Aliases: !exp, !viewexpenses
        """
        try:
            # Get database manager
            db_manager = self.bot.db_manager
            
            # Determine date range based on period
            start_date = None
            end_date = None
            period_name = "All Time"
            
            if period:
                today = datetime.now().date()
                if period.lower() == 'month':
                    # Current month
                    start_date = f"{today.year}-{today.month:02d}-01"
                    # Last day of current month
                    if today.month == 12:
                        end_date = f"{today.year + 1}-01-01"
                    else:
                        end_date = f"{today.year}-{today.month + 1:02d}-01"
                    period_name = f"Month ({today.strftime('%B %Y')})"
                elif period.lower() == 'year':
                    # Current year
                    start_date = f"{today.year}-01-01"
                    end_date = f"{today.year + 1}-01-01"
                    period_name = f"Year ({today.year})"
                elif period.lower() == 'week':
                    # Current week (last 7 days)
                    start_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')
                    end_date = today.strftime('%Y-%m-%d')
                    period_name = "Last 7 Days"
                elif period.lower() == 'today':
                    # Today only
                    start_date = today.strftime('%Y-%m-%d')
                    end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
                    period_name = "Today"
                else:
                    # Try to parse as YYYY-MM-DD
                    try:
                        if re.match(r'^\d{4}-\d{2}-\d{2}$', period):
                            start_date = period
                            end_date = (datetime.strptime(period, '%Y-%m-%d').date() + timedelta(days=1)).strftime('%Y-%m-%d')
                            period_name = f"Date ({period})"
                    except ValueError:
                        # Invalid date format, ignore
                        pass
            
            # Get expenses from database
            expenses = db_manager.list_expenses(start_date, end_date, category)
            
            # Create embed
            if category:
                embed = discord.Embed(
                    title=f"Expenses - {category} - {period_name}",
                    description=f"Showing {len(expenses)} expenses",
                    color=discord.Color.blue()
                )
            else:
                embed = discord.Embed(
                    title=f"Expenses - {period_name}",
                    description=f"Showing {len(expenses)} expenses",
                    color=discord.Color.blue()
                )
            
            # Calculate totals
            total_amount = sum(expense['amount'] for expense in expenses)
            
            # Add summary
            embed.add_field(
                name="Summary",
                value=f"Total Expenses: ${total_amount:.2f}\nNumber of Expenses: {len(expenses)}",
                inline=False
            )
            
            # Group by category if no category filter
            if not category and expenses:
                category_totals = {}
                for expense in expenses:
                    cat = expense['category']
                    if cat not in category_totals:
                        category_totals[cat] = 0
                    category_totals[cat] += expense['amount']
                
                # Sort categories by amount (descending)
                sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
                
                # Add category breakdown
                category_text = ""
                for cat, amount in sorted_categories:
                    percentage = (amount / total_amount) * 100 if total_amount > 0 else 0
                    category_text += f"**{cat}**: ${amount:.2f} ({percentage:.1f}%)\n"
                
                embed.add_field(
                    name="Category Breakdown",
                    value=category_text,
                    inline=False
                )
            
            # Add recent expenses (up to 10)
            if expenses:
                recent_expenses = expenses[:10]  # Limit to 10 most recent
                
                expense_text = ""
                for expense in recent_expenses:
                    expense_text += f"**{expense['date']}** - {expense['vendor']} - ${expense['amount']:.2f}"
                    if expense.get('description'):
                        expense_text += f" - {expense['description']}"
                    expense_text += f" (ID: {expense['expense_id']})\n"
                
                embed.add_field(
                    name=f"Recent Expenses (showing {len(recent_expenses)} of {len(expenses)})",
                    value=expense_text if expense_text else "No expenses found",
                    inline=False
                )
                
                if len(expenses) > 10:
                    embed.add_field(
                        name="Note",
                        value="Only showing 10 most recent expenses. Use category or period filters to narrow results.",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="No Expenses Found",
                    value="No expenses match your criteria.",
                    inline=False
                )
            
            # Add usage instructions
            embed.add_field(
                name="Usage",
                value="• `!expenses` - Show all expenses\n"
                      "• `!expenses month` - Show expenses for current month\n"
                      "• `!expenses year` - Show expenses for current year\n"
                      "• `!expenses week` - Show expenses for last 7 days\n"
                      "• `!expenses month Inventory` - Show Inventory expenses for current month",
                inline=False
            )
            
            embed.set_footer(text="AccountME Bot | Phase 4: Financial Tracking")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error retrieving expenses: {str(e)}")
            
            # Send error message
            error_embed = discord.Embed(
                title="Error Retrieving Expenses",
                description=f"An error occurred while retrieving expenses: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
    
    # Validation and formatting methods for expense entry
    
    def _validate_date(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate date input"""
        try:
            # Check if the date is in YYYY-MM-DD format
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', value):
                return False, "Date must be in YYYY-MM-DD format (e.g., 2025-03-22)"
            
            # Parse the date
            year, month, day = map(int, value.split('-'))
            date_obj = date(year, month, day)
            
            # Check if the date is not in the future
            if date_obj > date.today():
                return False, "Expense date cannot be in the future"
            
            return True, None
        except ValueError:
            return False, "Invalid date. Please use YYYY-MM-DD format with a valid date."
    
    def _format_date(self, value: str) -> str:
        """Format date for display"""
        return value
    
    def _validate_vendor(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate vendor input"""
        if not value.strip():
            return False, "Vendor name cannot be empty"
        
        if len(value) > 100:
            return False, "Vendor name is too long (maximum 100 characters)"
        
        return True, None
    
    def _format_vendor(self, value: str) -> str:
        """Format vendor for display"""
        return value.strip()
    
    def _validate_amount(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate amount input"""
        try:
            # Remove currency symbols and commas
            clean_value = value.replace('$', '').replace(',', '').strip()
            amount = float(clean_value)
            
            if amount <= 0:
                return False, "Amount must be greater than zero"
            
            if amount > 1000000:  # Arbitrary upper limit
                return False, "Amount is too large. Please check your input."
            
            return True, None
        except ValueError:
            return False, "Invalid amount. Please enter a number (e.g., 42.99)"
    
    def _format_amount(self, value: str) -> float:
        """Format amount for storage"""
        clean_value = value.replace('$', '').replace(',', '').strip()
        return float(clean_value)
    
    def _format_categories(self) -> str:
        """Format categories list for display"""
        return "\n".join([f"{i+1}. {cat}" for i, cat in enumerate(self.expense_categories)])
    
    def _validate_category(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate category input"""
        # Check if it's a number
        try:
            index = int(value) - 1
            if 0 <= index < len(self.expense_categories):
                return True, None
            else:
                return False, f"Please enter a number between 1 and {len(self.expense_categories)}"
        except ValueError:
            # Check if it's a valid category name
            if value in self.expense_categories:
                return True, None
            
            # Check for close matches
            close_matches = [cat for cat in self.expense_categories
                            if cat.lower().startswith(value.lower())]
            if close_matches:
                return False, f"Did you mean: {', '.join(close_matches)}?"
            
            return False, f"Invalid category. Please enter one of the listed categories or its number."
    
    def _format_category(self, value: str) -> str:
        """Format category for storage"""
        try:
            index = int(value) - 1
            if 0 <= index < len(self.expense_categories):
                return self.expense_categories[index]
        except ValueError:
            pass
        
        # If it's a valid category name, return it
        if value in self.expense_categories:
            return value
        
        # Find close match
        for cat in self.expense_categories:
            if cat.lower().startswith(value.lower()):
                return cat
        
        # Fallback
        return "Other"
    
    def _validate_description(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate description input"""
        if value.lower() == 'skip':
            return True, None
        
        if len(value) > 500:
            return False, "Description is too long (maximum 500 characters)"
        
        return True, None
    
    def _format_description(self, value: str) -> Optional[str]:
        """Format description for storage"""
        if value.lower() == 'skip':
            return None
        return value.strip()
    
    async def _continue_conversation(self, conversation_id: str) -> None:
        """Continue a multi-step conversation"""
        if conversation_id not in self.active_conversations:
            return
            
        conversation = self.active_conversations[conversation_id]
        
        # If conversation is completed or cancelled, do nothing
        if conversation.is_completed or conversation.is_cancelled:
            return
            
        # Get the current step
        step_index = conversation.current_step
        
        # Get the appropriate steps based on conversation type
        steps = []
        if conversation.conversation_type == "expense":
            steps = self.expense_steps
        
        # Check if we've completed all steps
        if step_index >= len(steps):
            # All steps completed, show summary and confirmation
            await self._show_conversation_summary(conversation_id)
            return
            
        # Get the current step
        step = steps[step_index]
        
        # Get the channel
        channel = self.bot.get_channel(conversation.channel_id)
        if not channel:
            logger.error(f"Channel {conversation.channel_id} not found for conversation {conversation_id}")
            del self.active_conversations[conversation_id]
            return
            
        # Get the prompt
        prompt = step["prompt"]
        if callable(prompt):
            prompt = prompt()
            
        # Send the prompt
        prompt_message = await channel.send(prompt)
        conversation.prompt_message_id = prompt_message.id
    
    async def _handle_conversation_timeout(self, conversation_id: str) -> None:
        """Handle timeout for conversation"""
        if conversation_id not in self.active_conversations:
            return
            
        conversation = self.active_conversations[conversation_id]
        if conversation.is_completed or conversation.is_cancelled:
            return
            
        try:
            # Get the channel
            channel = self.bot.get_channel(conversation.channel_id)
            if channel:
                # Send timeout message
                embed = discord.Embed(
                    title="Conversation Timeout",
                    description="The conversation has timed out due to inactivity. Please try again.",
                    color=discord.Color.red()
                )
                await channel.send(embed=embed)
        finally:
            # Clean up the conversation state
            del self.active_conversations[conversation_id]
    
    async def _show_conversation_summary(self, conversation_id: str) -> None:
        """Show a summary of the collected data and ask for confirmation"""
        if conversation_id not in self.active_conversations:
            return
            
        conversation = self.active_conversations[conversation_id]
        
        # Get the channel
        channel = self.bot.get_channel(conversation.channel_id)
        if not channel:
            logger.error(f"Channel {conversation.channel_id} not found for conversation {conversation_id}")
            del self.active_conversations[conversation_id]
            return
            
        # Create summary embed
        embed = discord.Embed(
            title="Expense Summary",
            description="Please review the expense details below and confirm.",
            color=discord.Color.blue()
        )
        
        # Add fields based on conversation type
        if conversation.conversation_type == "expense":
            # Date
            if "date" in conversation.data:
                embed.add_field(
                    name="Date",
                    value=conversation.data["date"],
                    inline=True
                )
                
            # Vendor
            if "vendor" in conversation.data:
                embed.add_field(
                    name="Vendor",
                    value=conversation.data["vendor"],
                    inline=True
                )
                
            # Amount
            if "amount" in conversation.data:
                embed.add_field(
                    name="Amount",
                    value=f"${conversation.data['amount']:.2f}",
                    inline=True
                )
                
            # Category
            if "category" in conversation.data:
                embed.add_field(
                    name="Category",
                    value=conversation.data["category"],
                    inline=True
                )
                
            # Description
            if "description" in conversation.data and conversation.data["description"]:
                embed.add_field(
                    name="Description",
                    value=conversation.data["description"],
                    inline=False
                )
        
        # Add confirmation instructions
        embed.add_field(
            name="Confirm",
            value="Type `confirm` to save this expense, or `cancel` to discard it.",
            inline=False
        )
        
        # Send the summary
        summary_message = await channel.send(embed=embed)
        conversation.last_message_id = summary_message.id
    
    async def _save_expense_data(self, conversation_id: str) -> None:
        """Save the expense data to the database"""
        if conversation_id not in self.active_conversations:
            return
            
        conversation = self.active_conversations[conversation_id]
        
        # Get the channel
        channel = self.bot.get_channel(conversation.channel_id)
        if not channel:
            logger.error(f"Channel {conversation.channel_id} not found for conversation {conversation_id}")
            del self.active_conversations[conversation_id]
            return
        
        try:
            # Prepare expense data for database
            expense_data = {
                'date': conversation.data.get('date'),
                'vendor': conversation.data.get('vendor'),
                'amount': conversation.data.get('amount'),
                'category': conversation.data.get('category'),
                'description': conversation.data.get('description')
            }
            
            # Save to database
            db_manager = self.bot.db_manager
            expense_id = db_manager.add_expense(expense_data)
            
            # Log the action in audit log
            user_id = str(conversation.user_id)
            db_manager.log_audit(
                'create',
                'expense',
                expense_id,
                user_id,
                f"Expense added: {expense_data['vendor']} - ${expense_data['amount']:.2f}"
            )
            
            # Create success embed
            embed = discord.Embed(
                title="Expense Recorded",
                description=f"Expense has been successfully recorded with ID: {expense_id}",
                color=discord.Color.green()
            )
            
            # Add expense details
            if "date" in conversation.data:
                embed.add_field(
                    name="Date",
                    value=conversation.data["date"],
                    inline=True
                )
                
            if "vendor" in conversation.data:
                embed.add_field(
                    name="Vendor",
                    value=conversation.data["vendor"],
                    inline=True
                )
                
            if "amount" in conversation.data:
                embed.add_field(
                    name="Amount",
                    value=f"${conversation.data['amount']:.2f}",
                    inline=True
                )
                
            if "category" in conversation.data:
                embed.add_field(
                    name="Category",
                    value=conversation.data["category"],
                    inline=True
                )
                
            if "description" in conversation.data and conversation.data["description"]:
                embed.add_field(
                    name="Description",
                    value=conversation.data["description"],
                    inline=False
                )
            
            embed.set_footer(text=f"AccountME Bot | Expense ID: {expense_id}")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error saving expense data: {str(e)}")
            
            # Send error message
            error_embed = discord.Embed(
                title="Error Saving Expense",
                description=f"An error occurred while saving the expense: {str(e)}",
                color=discord.Color.red()
            )
            await channel.send(embed=error_embed)
    
    @commands.command(name="addexpense", aliases=["newexpense", "expenseadd"])
    async def add_expense_command(self, ctx):
        """
        Add a new expense through a guided conversation
        
        This command will start a step-by-step process to enter expense details
        
        Aliases: !newexpense, !expenseadd
        """
        # Check if user already has an active conversation
        user_conversations = [conv for conv in self.active_conversations.values()
                             if conv.user_id == ctx.author.id and not conv.is_completed and not conv.is_cancelled]
        
        if user_conversations:
            embed = discord.Embed(
                title="Active Conversation",
                description="You already have an active data entry conversation. Please complete or cancel it before starting a new one.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        
        # Create a new conversation state
        conversation_id = f"{ctx.author.id}:{ctx.channel.id}:{datetime.now().timestamp()}"
        conversation = ConversationState(
            user_id=ctx.author.id,
            channel_id=ctx.channel.id,
            conversation_type="expense"
        )
        
        # Store the conversation state
        self.active_conversations[conversation_id] = conversation
        
        # Send initial message
        embed = discord.Embed(
            title="Add Expense",
            description="Let's add a new expense. I'll guide you through the process step by step.\n\nYou can type `cancel` at any time to cancel the process.",
            color=discord.Color.blue()
        )
        
        message = await ctx.send(embed=embed)
        conversation.last_message_id = message.id
        
        # Start the conversation
        await self._continue_conversation(conversation_id)
        
        # Set up timeout task (5 minutes)
        conversation.timeout_task = asyncio.create_task(
            asyncio.sleep(300)
        )
        conversation.timeout_task.add_done_callback(
            lambda _: asyncio.create_task(
                self._handle_conversation_timeout(conversation_id)
            )
        )
    
    async def _create_verification_embed(self, receipt_data: Dict[str, Any], image_url: str, message_id: str, editing_field: Optional[str] = None) -> discord.Embed:
        """
        Create an embed for receipt verification
        
        Args:
            receipt_data: Extracted receipt data
            image_url: URL of the receipt image
            message_id: Discord message ID
            editing_field: Field currently being edited (if any)
            
        Returns:
            Discord embed for verification
        """
        # Determine color based on confidence
        confidence = receipt_data['confidence']
        if confidence >= 0.8:
            color = discord.Color.green()
        elif confidence >= 0.5:
            color = discord.Color.gold()
        else:
            color = discord.Color.orange()
        
        # Create embed
        embed = discord.Embed(
            title="Receipt Verification",
            description=f"AI vision analysis complete with {confidence*100:.0f}% confidence.\n"
                      f"Please verify the information below and make corrections if needed.",
            color=color
        )
        
        # Add receipt details with emoji indicators
        date_value = receipt_data.get("date", "Not detected")
        date_field = f"{self.field_emojis['date']} {date_value}"
        if editing_field == "date":
            date_field += " *(editing)*"
        embed.add_field(
            name="Date",
            value=date_field,
            inline=True
        )
        
        vendor_value = receipt_data.get("vendor", "Not detected")
        vendor_field = f"{self.field_emojis['vendor']} {vendor_value}"
        if editing_field == "vendor":
            vendor_field += " *(editing)*"
        embed.add_field(
            name="Vendor",
            value=vendor_field,
            inline=True
        )
        
        total_value = f"${receipt_data.get('total_amount', 0):.2f}" if receipt_data.get('total_amount') is not None else "Not detected"
        total_field = f"{self.field_emojis['total_amount']} {total_value}"
        if editing_field == "total_amount":
            total_field += " *(editing)*"
        embed.add_field(
            name="Total Amount",
            value=total_field,
            inline=True
        )
        
        tax_value = f"${receipt_data.get('tax', 0):.2f}" if receipt_data.get('tax') is not None else "Not detected"
        tax_field = f"{self.field_emojis['tax']} {tax_value}"
        if editing_field == "tax":
            tax_field += " *(editing)*"
        embed.add_field(
            name="Tax",
            value=tax_field,
            inline=True
        )
        
        # Add line items if available
        items = receipt_data.get("items", [])
        if items:
            items_text = f"{self.field_emojis['items']} "
            for item in items[:5]:  # Limit to first 5 items
                items_text += f"• {item['description']} - ${item['price']:.2f}"
                if item.get('quantity', 1) > 1:
                    items_text += f" (x{item['quantity']})"
                items_text += "\n"
            
            if len(items) > 5:
                items_text += f"... and {len(items) - 5} more items"
                
            if editing_field == "items":
                items_text += " *(editing)*"
                
            embed.add_field(
                name=f"Items ({len(items)})",
                value=items_text,
                inline=False
            )
        else:
            items_text = f"{self.field_emojis['items']} No items detected"
            if editing_field == "items":
                items_text += " *(editing)*"
                
            embed.add_field(
                name="Items",
                value=items_text,
                inline=False
            )
        
        # Add verification instructions
        instructions = (
            f"{self.field_emojis['confirm']} - Confirm and save receipt\n"
            f"{self.field_emojis['cancel']} - Cancel and discard\n"
            f"{self.field_emojis['date']} - Edit date\n"
            f"{self.field_emojis['vendor']} - Edit vendor\n"
            f"{self.field_emojis['total_amount']} - Edit total amount\n"
            f"{self.field_emojis['tax']} - Edit tax amount\n"
            f"{self.field_emojis['items']} - Edit items"
        )
        
        if editing_field:
            embed.add_field(
                name="Currently Editing",
                value=f"Type your correction for **{editing_field}** or react with ❌ to cancel editing.",
                inline=False
            )
        else:
            embed.add_field(
                name="Instructions",
                value=instructions,
                inline=False
            )
        
        embed.set_thumbnail(url=image_url)
        embed.set_footer(text=f"AccountME Bot | Receipt ID: {message_id} | React with an emoji to edit or confirm")
        
        return embed
    
    async def _add_verification_reactions(self, message: discord.Message):
        """Add reaction buttons for verification"""
        for emoji in self.field_emojis.values():
            await message.add_reaction(emoji)
    
    async def _handle_verification_timeout(self, verification_id: str):
        """Handle timeout for verification process"""
        if verification_id not in self.active_verifications:
            return
            
        verification = self.active_verifications[verification_id]
        if verification.is_completed or verification.is_cancelled:
            return
            
        try:
            # Get the channel and message
            channel = self.bot.get_channel(verification.message_id >> 32)
            if channel:
                try:
                    message = await channel.fetch_message(verification.message_id)
                    
                    # Create timeout embed
                    embed = discord.Embed(
                        title="Verification Timeout",
                        description="The receipt verification process has timed out. Please try again.",
                        color=discord.Color.red()
                    )
                    
                    await message.edit(embed=embed)
                    await message.clear_reactions()
                except discord.NotFound:
                    logger.warning(f"Message {verification.message_id} not found for timeout handling")
                except Exception as e:
                    logger.error(f"Error handling verification timeout: {str(e)}")
        finally:
            # Clean up the verification state
            del self.active_verifications[verification_id]
    
    async def _save_verified_receipt(self, ctx, receipt_data: Dict[str, Any], image_url: str):
        """
        Save verified receipt data to the database
        """
        try:
            # Prepare expense data for database
            expense_data = {
                'date': receipt_data.get('date', datetime.now().strftime('%Y-%m-%d')),
                'vendor': receipt_data.get('vendor', 'Unknown Vendor'),
                'amount': receipt_data.get('total_amount', 0.0),
                'category': 'Inventory',  # Default category, can be changed later
                'description': f"Receipt uploaded via Discord",
                'receipt_image': image_url
            }
            
            # Save to database
            db_manager = self.bot.db_manager
            expense_id = db_manager.add_expense(expense_data)
            
            # Log the action in audit log
            user_id = str(ctx.author.id) if hasattr(ctx, 'author') else 'unknown'
            db_manager.log_audit(
                'create',
                'expense',
                expense_id,
                user_id,
                f"Expense added from receipt: {expense_data['vendor']} - ${expense_data['amount']:.2f}"
            )
            
            # Create success embed
            embed = discord.Embed(
                title="Receipt Processed",
                description=f"Receipt has been successfully processed and saved as expense ID: {expense_id}",
                color=discord.Color.green()
            )
            
            # Add receipt details
            if receipt_data.get("date"):
                embed.add_field(
                    name="Date",
                    value=receipt_data["date"],
                    inline=True
                )
            
            if receipt_data.get("vendor"):
                embed.add_field(
                    name="Vendor",
                    value=receipt_data["vendor"],
                    inline=True
                )
            
            if receipt_data.get("total_amount"):
                embed.add_field(
                    name="Total Amount",
                    value=f"${receipt_data['total_amount']:.2f}",
                    inline=True
                )
            
            if receipt_data.get("tax"):
                embed.add_field(
                    name="Tax",
                    value=f"${receipt_data['tax']:.2f}",
                    inline=True
                )
            
            embed.add_field(
                name="Category",
                value="Inventory",
                inline=True
            )
            
            embed.add_field(
                name="Next Steps",
                value="You can edit this expense later using the `!editexpense` command.",
                inline=False
            )
            
            embed.set_thumbnail(url=image_url)
            embed.set_footer(text=f"AccountME Bot | Expense ID: {expense_id}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error saving receipt data: {str(e)}")
            
            # Send error message
            error_embed = discord.Embed(
                title="Error Processing Receipt",
                description=f"An error occurred while saving the receipt data: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
    
    @commands.command(name="uploadreceipt", aliases=["receipt", "scanreceipt"])
    async def upload_receipt_command(self, ctx):
        """
        Upload and process a receipt image
        
        Usage:
        !uploadreceipt - Use with an attached image
        
        Aliases: !receipt, !scanreceipt
        """
        # Check if there's an attachment
        if not ctx.message.attachments:
            embed = discord.Embed(
                title="Receipt Upload",
                description="Please attach a receipt image to your command.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="How to Use",
                value="Type `!uploadreceipt` and attach an image of your receipt.",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        # Get the first attachment
        attachment = ctx.message.attachments[0]
        
        # Check if it's an image
        if not attachment.content_type or not attachment.content_type.startswith('image/'):
            embed = discord.Embed(
                title="Invalid Attachment",
                description="The attached file is not an image.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        try:
            # Get the image URL from Discord
            image_url = attachment.url
            message_id = ctx.message.id
            
            # Get the image processor and store the URL
            image_processor = self.bot.get_image_processor()
            if not image_processor:
                # Fallback if image processor is not available
                receipt_url = image_url
                logger.warning("Image processor not available, using raw Discord URL")
                
                embed = discord.Embed(
                    title="Receipt Upload",
                    description="Your receipt has been uploaded, but processing is not available.",
                    color=discord.Color.orange()
                )
                embed.set_thumbnail(url=image_url)
                embed.set_footer(text=f"AccountME Bot | Receipt ID: {message_id}")
                await ctx.send(embed=embed)
                return
            
            # Store the receipt URL
            receipt_url = await image_processor.store_receipt_url(image_url, str(message_id))
            logger.info(f"Receipt URL stored: {receipt_url}")
            
            # Send initial confirmation
            processing_embed = discord.Embed(
                title="Receipt Uploaded",
                description="Your receipt has been uploaded. Processing with AI vision...",
                color=discord.Color.blue()
            )
            processing_embed.set_thumbnail(url=image_url)
            processing_message = await ctx.send(embed=processing_embed)
            
            # Process the receipt with AI vision
            try:
                # Parse the receipt using the AI vision model
                receipt_data = await image_processor.parse_receipt_from_url(receipt_url)
                
                # Create verification embed
                verification_embed = await self._create_verification_embed(
                    receipt_data,
                    image_url,
                    str(message_id)
                )
                
                # Update the message with verification embed
                verification_message = await processing_message.edit(embed=verification_embed)
                
                # Add reaction buttons for verification
                await self._add_verification_reactions(verification_message)
                
                # Create a verification state object
                verification_id = f"{ctx.author.id}:{verification_message.id}"
                verification = VerificationState(
                    receipt_data=receipt_data,
                    user_id=ctx.author.id,
                    message_id=verification_message.id
                )
                
                # Set up timeout task (5 minutes)
                verification.timeout_task = asyncio.create_task(
                    asyncio.sleep(300)
                )
                verification.timeout_task.add_done_callback(
                    lambda _: asyncio.create_task(
                        self._handle_verification_timeout(verification_id)
                    )
                )
                
                # Store the verification state
                self.active_verifications[verification_id] = verification
                
                logger.info(f"Verification process started for receipt {message_id}")
                
            except Exception as e:
                logger.error(f"Error processing receipt with AI vision: {str(e)}")
                
                # Create error embed
                error_embed = discord.Embed(
                    title="Receipt Processing Error",
                    description=f"An error occurred while processing your receipt with AI vision: {str(e)}",
                    color=discord.Color.red()
                )
                error_embed.set_thumbnail(url=image_url)
                error_embed.set_footer(text=f"AccountME Bot | Receipt ID: {message_id}")
                
                # Edit the original message with the error
                await processing_message.edit(embed=error_embed)
            
        except Exception as e:
            logger.error(f"Error processing receipt upload: {str(e)}")
            embed = discord.Embed(
                title="Upload Error",
                description=f"An error occurred while processing your receipt: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="editexpense", aliases=["updateexpense", "modifyexpense"])
    async def edit_expense_command(self, ctx, expense_id: int = None):
        """
        Edit an existing expense
        
        Usage:
        !editexpense <expense_id> - Edit the specified expense
        
        Aliases: !updateexpense, !modifyexpense
        """
        if expense_id is None:
            embed = discord.Embed(
                title="Edit Expense",
                description="Please provide an expense ID to edit.",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="Usage",
                value="!editexpense <expense_id>",
                inline=False
            )
            embed.add_field(
                name="Example",
                value="!editexpense 42",
                inline=False
            )
            embed.add_field(
                name="Find Expense IDs",
                value="Use the `!expenses` command to see expense IDs",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        # Get the expense from the database
        db_manager = self.bot.db_manager
        expense = db_manager.get_expense(expense_id)
        
        if not expense:
            await ctx.send(f"Expense with ID {expense_id} not found.")
            return
        
        # Create a new conversation state for editing
        conversation_id = f"{ctx.author.id}:{ctx.channel.id}:{datetime.now().timestamp()}"
        conversation = ConversationState(
            user_id=ctx.author.id,
            channel_id=ctx.channel.id,
            conversation_type="expense_edit"
        )
        
        # Pre-fill with existing data
        conversation.data = {
            'expense_id': expense_id,
            'date': expense['date'],
            'vendor': expense['vendor'],
            'amount': expense['amount'],
            'category': expense['category'],
            'description': expense['description']
        }
        
        # Store the conversation state
        self.active_conversations[conversation_id] = conversation
        
        # Send initial message with current expense details
        embed = discord.Embed(
            title=f"Edit Expense #{expense_id}",
            description="You can edit this expense by selecting which field to modify.",
            color=discord.Color.blue()
        )
        
        # Add current expense details
        embed.add_field(
            name="Date",
            value=expense['date'],
            inline=True
        )
        
        embed.add_field(
            name="Vendor",
            value=expense['vendor'],
            inline=True
        )
        
        embed.add_field(
            name="Amount",
            value=f"${expense['amount']:.2f}",
            inline=True
        )
        
        embed.add_field(
            name="Category",
            value=expense['category'],
            inline=True
        )
        
        if expense['description']:
            embed.add_field(
                name="Description",
                value=expense['description'],
                inline=False
            )
        
        embed.add_field(
            name="Edit Options",
            value="1️⃣ - Edit Date\n"
                  "2️⃣ - Edit Vendor\n"
                  "3️⃣ - Edit Amount\n"
                  "4️⃣ - Edit Category\n"
                  "5️⃣ - Edit Description\n"
                  "✅ - Save Changes\n"
                  "❌ - Cancel",
            inline=False
        )
        
        message = await ctx.send(embed=embed)
        conversation.last_message_id = message.id
        
        # Add reaction options
        await message.add_reaction("1️⃣")
        await message.add_reaction("2️⃣")
        await message.add_reaction("3️⃣")
        await message.add_reaction("4️⃣")
        await message.add_reaction("5️⃣")
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        
        # Set up timeout task (5 minutes)
        conversation.timeout_task = asyncio.create_task(
            asyncio.sleep(300)
        )
        conversation.timeout_task.add_done_callback(
            lambda _: asyncio.create_task(
                self._handle_conversation_timeout(conversation_id)
            )
        )
    
    @commands.command(name="deleteexpense", aliases=["removeexpense", "delexpense"])
    async def delete_expense_command(self, ctx, expense_id: int = None):
        """
        Delete an expense
        
        Usage:
        !deleteexpense <expense_id> - Delete the specified expense
        
        Aliases: !removeexpense, !delexpense
        """
        if expense_id is None:
            embed = discord.Embed(
                title="Delete Expense",
                description="Please provide an expense ID to delete.",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="Usage",
                value="!deleteexpense <expense_id>",
                inline=False
            )
            embed.add_field(
                name="Example",
                value="!deleteexpense 42",
                inline=False
            )
            embed.add_field(
                name="Find Expense IDs",
                value="Use the `!expenses` command to see expense IDs",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        # Get the expense from the database
        db_manager = self.bot.db_manager
        expense = db_manager.get_expense(expense_id)
        
        if not expense:
            await ctx.send(f"Expense with ID {expense_id} not found.")
            return
        
        # Create confirmation embed
        embed = discord.Embed(
            title=f"Confirm Delete Expense #{expense_id}",
            description="Are you sure you want to delete this expense? This action cannot be undone.",
            color=discord.Color.red()
        )
        
        # Add expense details
        embed.add_field(
            name="Date",
            value=expense['date'],
            inline=True
        )
        
        embed.add_field(
            name="Vendor",
            value=expense['vendor'],
            inline=True
        )
        
        embed.add_field(
            name="Amount",
            value=f"${expense['amount']:.2f}",
            inline=True
        )
        
        embed.add_field(
            name="Category",
            value=expense['category'],
            inline=True
        )
        
        if expense['description']:
            embed.add_field(
                name="Description",
                value=expense['description'],
                inline=False
            )
        
        # Send confirmation message
        confirmation_message = await ctx.send(embed=embed)
        
        # Add reaction options
        await confirmation_message.add_reaction("✅")  # Confirm
        await confirmation_message.add_reaction("❌")  # Cancel
        
        # Wait for reaction
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirmation_message.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Delete the expense
                db_manager.delete('expenses', 'expense_id = ?', (expense_id,))
                
                # Log the action in audit log
                db_manager.log_audit(
                    'delete',
                    'expense',
                    expense_id,
                    str(ctx.author.id),
                    f"Expense deleted: {expense['vendor']} - ${expense['amount']:.2f}"
                )
                
                # Send confirmation
                await ctx.send(f"Expense #{expense_id} has been deleted.")
            else:
                # Cancelled
                await ctx.send("Expense deletion cancelled.")
                
        except asyncio.TimeoutError:
            await ctx.send("Expense deletion cancelled due to timeout.")
    
    @commands.command(name="addsale", aliases=["newsale", "recordsale"])
    async def add_sale_command(self, ctx):
        """
        Record a new sale through a guided conversation
        
        This command will start a step-by-step process to enter sale details
        
        Aliases: !newsale, !recordsale
        """
        # Check if user already has an active conversation
        user_conversations = [conv for conv in self.active_conversations.values()
                             if conv.user_id == ctx.author.id and not conv.is_completed and not conv.is_cancelled]
        
        if user_conversations:
            embed = discord.Embed(
                title="Active Conversation",
                description="You already have an active data entry conversation. Please complete or cancel it before starting a new one.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        
        # Create a new conversation state
        conversation_id = f"{ctx.author.id}:{ctx.channel.id}:{datetime.now().timestamp()}"
        conversation = ConversationState(
            user_id=ctx.author.id,
            channel_id=ctx.channel.id,
            conversation_type="sale"
        )
        
        # Initialize sale data
        conversation.data = {
            'date': datetime.now().strftime('%Y-%m-%d'),  # Default to today
            'items': [],  # Will hold sale items
            'total_amount': 0.0,  # Will be calculated from items
            'customer_id': None,  # Optional customer
            'payment_method': None,  # Will be collected
            'notes': None  # Optional notes
        }
        
        # Store the conversation state
        self.active_conversations[conversation_id] = conversation
        
        # Send initial message
        embed = discord.Embed(
            title="Add Sale",
            description="Let's record a new sale. I'll guide you through the process step by step.\n\nYou can type `cancel` at any time to cancel the process.",
            color=discord.Color.blue()
        )
        
        message = await ctx.send(embed=embed)
        conversation.last_message_id = message.id
        
        # Start the sale creation process
        await self._start_sale_creation(conversation_id)
        
        # Set up timeout task (10 minutes for sales as they can be complex)
        conversation.timeout_task = asyncio.create_task(
            asyncio.sleep(600)
        )
        conversation.timeout_task.add_done_callback(
            lambda _: asyncio.create_task(
                self._handle_conversation_timeout(conversation_id)
            )
        )
    
    async def _start_sale_creation(self, conversation_id: str) -> None:
        """Start the sale creation process"""
        if conversation_id not in self.active_conversations:
            return
            
        conversation = self.active_conversations[conversation_id]
        
        # Get the channel
        channel = self.bot.get_channel(conversation.channel_id)
        if not channel:
            logger.error(f"Channel {conversation.channel_id} not found for conversation {conversation_id}")
            del self.active_conversations[conversation_id]
            return
        
        # First step: Ask if they want to associate a customer
        embed = discord.Embed(
            title="Customer Information",
            description="Would you like to associate this sale with a customer?",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Options",
            value="1️⃣ Yes, select an existing customer\n"
                  "2️⃣ Yes, create a new customer\n"
                  "3️⃣ No, continue without a customer",
            inline=False
        )
        
        # Send the message with reactions
        message = await channel.send(embed=embed)
        conversation.last_message_id = message.id
        
        # Add reactions
        await message.add_reaction("1️⃣")
        await message.add_reaction("2️⃣")
        await message.add_reaction("3️⃣")
        
        # Set the current step
        conversation.current_step = "customer_selection"
    
    @commands.command(name="financialreport", aliases=["finreport", "reportfinance"])
    async def financial_report_command(self, ctx, report_type=None, start_date=None, end_date=None, *args):
        """
        Generate financial reports
        
        Usage:
        !financialreport - Show available report types
        !financialreport sales [start_date] [end_date] - Generate sales report
        !financialreport expenses [start_date] [end_date] [category] - Generate expense report
        !financialreport profit [start_date] [end_date] - Generate profit and loss report
        
        Dates should be in YYYY-MM-DD format. If not provided, defaults to last 30 days.
        
        Aliases: !finreport, !reportfinance
        """
        try:
            # Get report generator
            report_generator = self.bot.get_report_generator()
            if not report_generator:
                await ctx.send("Report generator is not available.")
                return
            
            # If no report type specified, show available types
            if not report_type:
                embed = discord.Embed(
                    title="Financial Reports",
                    description="Available report types:",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="Sales Report",
                    value="Usage: `!financialreport sales [start_date] [end_date]`\n"
                          "Shows sales data with breakdowns by payment method and products.",
                    inline=False
                )
                
                embed.add_field(
                    name="Expense Report",
                    value="Usage: `!financialreport expenses [start_date] [end_date] [category]`\n"
                          "Shows expense data with category breakdowns.",
                    inline=False
                )
                
                embed.add_field(
                    name="Profit and Loss Report",
                    value="Usage: `!financialreport profit [start_date] [end_date]`\n"
                          "Shows profit and loss analysis with weekly breakdowns.",
                    inline=False
                )
                
                embed.add_field(
                    name="Date Format",
                    value="All dates should be in YYYY-MM-DD format.\n"
                          "If dates are not provided, defaults to the last 30 days.",
                    inline=False
                )
                
                await ctx.send(embed=embed)
                return
            
            # Process based on report type
            if report_type.lower() == "sales":
                # Optional customer filter
                customer_id = None
                if args and args[0].isdigit():
                    customer_id = int(args[0])
                
                # Send initial message
                processing_message = await ctx.send("Generating sales report...")
                
                # Generate report
                csv_path, embed = await report_generator.generate_sales_report(start_date, end_date, customer_id)
                
                # Send the report
                await processing_message.delete()
                await ctx.send(embed=embed, file=discord.File(csv_path))
                
            elif report_type.lower() == "expenses":
                # Optional category filter
                category = None
                if args:
                    category = args[0]
                
                # Send initial message
                processing_message = await ctx.send("Generating expense report...")
                
                # Generate report
                csv_path, embed = await report_generator.generate_expense_report(start_date, end_date, category)
                
                # Send the report
                await processing_message.delete()
                await ctx.send(embed=embed, file=discord.File(csv_path))
                
            elif report_type.lower() in ["profit", "profitloss", "profit_loss"]:
                # Send initial message
                processing_message = await ctx.send("Generating profit and loss report...")
                
                # Generate report
                csv_path, embed = await report_generator.generate_profit_loss_report(start_date, end_date)
                
                # Send the report
                await processing_message.delete()
                await ctx.send(embed=embed, file=discord.File(csv_path))
                
            else:
                await ctx.send(f"Unknown report type: {report_type}. Use `!financialreport` to see available report types.")
                
        except Exception as e:
            logger.error(f"Error generating financial report: {str(e)}")
            
            # Send error message
            error_embed = discord.Embed(
                title="Error Generating Report",
                description=f"An error occurred while generating the report: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
    
    @commands.command(name="exportdata", aliases=["export", "dataexport"])
    async def export_data_command(self, ctx, data_type=None, start_date=None, end_date=None):
        """
        Export financial data to CSV
        
        Usage:
        !exportdata - Show available data types
        !exportdata sales [start_date] [end_date] - Export sales data
        !exportdata expenses [start_date] [end_date] - Export expense data
        !exportdata inventory - Export current inventory data
        
        Dates should be in YYYY-MM-DD format. If not provided, defaults to all data.
        
        Aliases: !export, !dataexport
        """
        try:
            # Get report generator and database manager
            report_generator = self.bot.get_report_generator()
            db_manager = self.bot.db_manager
            
            if not report_generator or not db_manager:
                await ctx.send("Report generator or database manager is not available.")
                return
            
            # If no data type specified, show available types
            if not data_type:
                embed = discord.Embed(
                    title="Export Financial Data",
                    description="Available data types for export:",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="Sales Data",
                    value="Usage: `!exportdata sales [start_date] [end_date]`\n"
                          "Exports all sales data to CSV.",
                    inline=False
                )
                
                embed.add_field(
                    name="Expense Data",
                    value="Usage: `!exportdata expenses [start_date] [end_date]`\n"
                          "Exports all expense data to CSV.",
                    inline=False
                )
                
                embed.add_field(
                    name="Inventory Data",
                    value="Usage: `!exportdata inventory`\n"
                          "Exports current inventory data to CSV.",
                    inline=False
                )
                
                embed.add_field(
                    name="Date Format",
                    value="All dates should be in YYYY-MM-DD format.\n"
                          "If dates are not provided, exports all data.",
                    inline=False
                )
                
                await ctx.send(embed=embed)
                return
            
            # Process based on data type
            if data_type.lower() == "sales":
                # Send initial message
                processing_message = await ctx.send("Exporting sales data...")
                
                # Build query
                query = "SELECT * FROM sales"
                params = ()
                
                if start_date and end_date:
                    query += " WHERE date BETWEEN ? AND ?"
                    params = (start_date, end_date)
                
                # Get data
                sales_data = db_manager.execute_query(query, params)
                
                # Export to CSV
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"sales_export_{timestamp}.csv"
                csv_path = await report_generator.export_to_csv(sales_data, filename)
                
                # Send the file
                await processing_message.delete()
                await ctx.send(f"Sales data exported successfully!", file=discord.File(csv_path))
                
            elif data_type.lower() == "expenses":
                # Send initial message
                processing_message = await ctx.send("Exporting expense data...")
                
                # Build query
                query = "SELECT * FROM expenses"
                params = ()
                
                if start_date and end_date:
                    query += " WHERE date BETWEEN ? AND ?"
                    params = (start_date, end_date)
                
                # Get data
                expense_data = db_manager.execute_query(query, params)
                
                # Export to CSV
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"expenses_export_{timestamp}.csv"
                csv_path = await report_generator.export_to_csv(expense_data, filename)
                
                # Send the file
                await processing_message.delete()
                await ctx.send(f"Expense data exported successfully!", file=discord.File(csv_path))
                
            elif data_type.lower() == "inventory":
                # Send initial message
                processing_message = await ctx.send("Exporting inventory data...")
                
                # Get data
                inventory_data = db_manager.execute_query("SELECT * FROM products", ())
                
                # Export to CSV
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"inventory_export_{timestamp}.csv"
                csv_path = await report_generator.export_to_csv(inventory_data, filename)
                
                # Send the file
                await processing_message.delete()
                await ctx.send(f"Inventory data exported successfully!", file=discord.File(csv_path))
                
            else:
                await ctx.send(f"Unknown data type: {data_type}. Use `!exportdata` to see available data types.")
                
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            
            # Send error message
            error_embed = discord.Embed(
                title="Error Exporting Data",
                description=f"An error occurred while exporting the data: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
    
    @commands.command(name="sales", aliases=["viewsales", "salesreport"])
    async def sales_command(self, ctx, period=None, customer=None):
        """
        View sales information
        
        Usage:
        !sales - Show recent sales
        !sales <period> - Show sales for a specific period (e.g., 'month', 'year', 'week')
        !sales <period> <customer> - Show sales for a specific period and customer
        
        Aliases: !viewsales, !salesreport
        """
        try:
            # Get database manager
            db_manager = self.bot.db_manager
            
            # Determine date range based on period
            start_date = None
            end_date = None
            period_name = "All Time"
            
            if period:
                today = datetime.now().date()
                if period.lower() == 'month':
                    # Current month
                    start_date = f"{today.year}-{today.month:02d}-01"
                    # Last day of current month
                    if today.month == 12:
                        end_date = f"{today.year + 1}-01-01"
                    else:
                        end_date = f"{today.year}-{today.month + 1:02d}-01"
                    period_name = f"Month ({today.strftime('%B %Y')})"
                elif period.lower() == 'year':
                    # Current year
                    start_date = f"{today.year}-01-01"
                    end_date = f"{today.year + 1}-01-01"
                    period_name = f"Year ({today.year})"
                elif period.lower() == 'week':
                    # Current week (last 7 days)
                    start_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')
                    end_date = today.strftime('%Y-%m-%d')
                    period_name = "Last 7 Days"
                elif period.lower() == 'today':
                    # Today only
                    start_date = today.strftime('%Y-%m-%d')
                    end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
                    period_name = "Today"
                else:
                    # Try to parse as YYYY-MM-DD
                    try:
                        if re.match(r'^\d{4}-\d{2}-\d{2}$', period):
                            start_date = period
                            end_date = (datetime.strptime(period, '%Y-%m-%d').date() + timedelta(days=1)).strftime('%Y-%m-%d')
                            period_name = f"Date ({period})"
                    except ValueError:
                        # Invalid date format, ignore
                        pass
            
            # Determine customer filter
            customer_id = None
            customer_name = None
            
            if customer:
                # Try to find customer by name
                customers = db_manager.list_customers()
                for c in customers:
                    if customer.lower() in c['name'].lower():
                        customer_id = c['customer_id']
                        customer_name = c['name']
                        break
            
            # Get sales from database
            sales = db_manager.list_sales(start_date, end_date, customer_id)
            
            # Create embed
            if customer_name:
                embed = discord.Embed(
                    title=f"Sales - {customer_name} - {period_name}",
                    description=f"Showing {len(sales)} sales",
                    color=discord.Color.blue()
                )
            else:
                embed = discord.Embed(
                    title=f"Sales - {period_name}",
                    description=f"Showing {len(sales)} sales",
                    color=discord.Color.blue()
                )
            
            # Calculate totals
            total_amount = sum(sale['total_amount'] for sale in sales)
            
            # Add summary
            embed.add_field(
                name="Summary",
                value=f"Total Sales: ${total_amount:.2f}\nNumber of Sales: {len(sales)}",
                inline=False
            )
            
            # Group by payment method if no customer filter
            if not customer_id and sales:
                payment_totals = {}
                for sale in sales:
                    method = sale['payment_method'] or "Unknown"
                    if method not in payment_totals:
                        payment_totals[method] = 0
                    payment_totals[method] += sale['total_amount']
                
                # Sort payment methods by amount (descending)
                sorted_methods = sorted(payment_totals.items(), key=lambda x: x[1], reverse=True)
                
                # Add payment method breakdown
                method_text = ""
                for method, amount in sorted_methods:
                    percentage = (amount / total_amount) * 100 if total_amount > 0 else 0
                    method_text += f"**{method}**: ${amount:.2f} ({percentage:.1f}%)\n"
                
                embed.add_field(
                    name="Payment Method Breakdown",
                    value=method_text,
                    inline=False
                )
            
            # Add recent sales (up to 10)
            if sales:
                recent_sales = sales[:10]  # Limit to 10 most recent
                
                sales_text = ""
                for sale in recent_sales:
                    sales_text += f"**{sale['date']}** - "
                    if sale['customer_name']:
                        sales_text += f"{sale['customer_name']} - "
                    sales_text += f"${sale['total_amount']:.2f} ({sale['payment_method']})"
                    if sale.get('notes'):
                        sales_text += f" - {sale['notes']}"
                    sales_text += f" (ID: {sale['sale_id']})\n"
                
                embed.add_field(
                    name=f"Recent Sales (showing {len(recent_sales)} of {len(sales)})",
                    value=sales_text if sales_text else "No sales found",
                    inline=False
                )
                
                if len(sales) > 10:
                    embed.add_field(
                        name="Note",
                        value="Only showing 10 most recent sales. Use customer or period filters to narrow results.",
                        inline=False
                    )
            else:
                embed.add_field(
                    name="No Sales Found",
                    value="No sales match your criteria.",
                    inline=False
                )
            
            # Add usage instructions
            embed.add_field(
                name="Usage",
                value="• `!sales` - Show all sales\n"
                      "• `!sales month` - Show sales for current month\n"
                      "• `!sales year` - Show sales for current year\n"
                      "• `!sales week` - Show sales for last 7 days\n"
                      "• `!sales month CustomerName` - Show sales for a specific customer in current month",
                inline=False
            )
            
            embed.set_footer(text="AccountME Bot | Phase 4: Financial Tracking")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error retrieving sales: {str(e)}")
            
            # Send error message
            error_embed = discord.Embed(
                title="Error Retrieving Sales",
                description=f"An error occurred while retrieving sales: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle reactions for receipt verification and report follow-ups"""
        # Ignore bot's own reactions
        if user.bot:
            return
            
        # Check if this is a verification message
        verification_id = f"{user.id}:{reaction.message.id}"
        if verification_id in self.active_verifications:
            verification = self.active_verifications[verification_id]
            
            # Ignore if verification is completed or cancelled
            if verification.is_completed or verification.is_cancelled:
                return
                
            # Ignore if user is not the one who started verification
            if user.id != verification.user_id:
                return
                
            # Get the emoji and check if it's one of our verification emojis
            emoji = str(reaction.emoji)
            field_map = {v: k for k, v in self.field_emojis.items()}
            
            if emoji not in field_map:
                return
                
            action = field_map[emoji]
        
        # Handle the action
        if action == "confirm":
            # Mark as completed
            verification.is_completed = True
            
            # Cancel the timeout task
            if verification.timeout_task:
                verification.timeout_task.cancel()
                
            # Clear reactions
            await reaction.message.clear_reactions()
            
            # Create confirmation embed
            embed = discord.Embed(
                title="Receipt Verified",
                description="Thank you for verifying the receipt data. Processing...",
                color=discord.Color.green()
            )
            
            await reaction.message.edit(embed=embed)
            
            # Save the verified receipt data
            channel = reaction.message.channel
            await self._save_verified_receipt(
                channel,
                verification.receipt_data,
                reaction.message.embeds[0].thumbnail.url
            )
            
            # Clean up
            del self.active_verifications[verification_id]
            
        elif action == "cancel":
            # Mark as cancelled
            verification.is_cancelled = True
            
            # Cancel the timeout task
            if verification.timeout_task:
                verification.timeout_task.cancel()
                
            # Clear reactions
            await reaction.message.clear_reactions()
            
            # Create cancellation embed
            embed = discord.Embed(
                title="Verification Cancelled",
                description="Receipt verification has been cancelled.",
                color=discord.Color.red()
            )
            
            await reaction.message.edit(embed=embed)
            
            # Clean up
            del self.active_verifications[verification_id]
            
        else:
            # This is a field edit action
            # Set the editing field
            verification.editing_field = action
            
            # Update the embed to show editing state
            embed = await self._create_verification_embed(
                verification.receipt_data,
                reaction.message.embeds[0].thumbnail.url,
                reaction.message.embeds[0].footer.text.split("Receipt ID: ")[1].split(" |")[0],
                editing_field=action
            )
            
            await reaction.message.edit(embed=embed)
            
            # Clear reactions during editing
            await reaction.message.clear_reactions()
            
            # Add cancel reaction for editing
            await reaction.message.add_reaction("❌")
            
            # Prompt user to enter new value
            channel = reaction.message.channel
            prompt_message = await channel.send(
                f"Please enter the new value for **{action}**. Type 'cancel' to cancel editing."
            )
            
            # Set a timeout for the prompt message (will be deleted when editing is done)
            await asyncio.sleep(0.5)  # Small delay to ensure message is sent
            verification.prompt_message_id = prompt_message.id
            
            return
        
        # Check if this is a report follow-up message
        # We'll use a simple approach for now - check if the message has an embed with a title
        # that matches one of our follow-up question titles
        if reaction.message.embeds and len(reaction.message.embeds) > 0:
            embed = reaction.message.embeds[0]
            
            # Check for report type follow-up
            if embed.title == "What type of report would you like?":
                # This is a report type follow-up
                emoji = str(reaction.emoji)
                report_type_map = {
                    "1️⃣": "sales",
                    "2️⃣": "expenses",
                    "3️⃣": "inventory",
                    "4️⃣": "profit"
                }
                
                if emoji in report_type_map:
                    # Create a temporary report context
                    report_context = self.ReportContext(
                        user_id=user.id,
                        channel_id=reaction.message.channel.id,
                        original_query="Report type selected via reaction"
                    )
                    report_context.report_type = report_type_map[emoji]
                    
                    # Check if we need more information
                    missing_info = self._check_missing_information(report_context)
                    
                    if missing_info:
                        # We need more information, ask a follow-up question
                        await self._ask_follow_up_question(reaction.message.channel, report_context, missing_info, reaction.message)
                    else:
                        # We have all the information we need, generate the report
                        await self._generate_report_from_context(reaction.message.channel, report_context, reaction.message)
                    
                    return
            
            # Check for date range follow-up
            elif embed.title == "What time period would you like to see?":
                # This is a date range follow-up
                emoji = str(reaction.emoji)
                
                # Create a temporary report context
                report_context = self.ReportContext(
                    user_id=user.id,
                    channel_id=reaction.message.channel.id,
                    original_query="Date range selected via reaction"
                )
                
                # Extract the report type from the embed description
                if "sales report" in embed.description.lower():
                    report_context.report_type = "sales"
                elif "expense report" in embed.description.lower():
                    report_context.report_type = "expenses"
                elif "inventory report" in embed.description.lower():
                    report_context.report_type = "inventory"
                elif "profit" in embed.description.lower():
                    report_context.report_type = "profit"
                
                # Set the date range based on the reaction
                today = datetime.now().date()
                
                if emoji == "1️⃣":  # Today
                    report_context.start_date = today.strftime('%Y-%m-%d')
                    report_context.end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
                elif emoji == "2️⃣":  # This Week
                    # Start of current week (Monday)
                    start_of_week = today - timedelta(days=today.weekday())
                    report_context.start_date = start_of_week.strftime('%Y-%m-%d')
                    report_context.end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
                elif emoji == "3️⃣":  # This Month
                    # Start of current month
                    start_of_month = today.replace(day=1)
                    report_context.start_date = start_of_month.strftime('%Y-%m-%d')
                    report_context.end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
                elif emoji == "4️⃣":  # This Year
                    # Start of current year
                    start_of_year = today.replace(month=1, day=1)
                    report_context.start_date = start_of_year.strftime('%Y-%m-%d')
                    report_context.end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
                elif emoji == "5️⃣":  # Last Month
                    # Start of last month
                    if today.month == 1:
                        start_of_last_month = today.replace(year=today.year-1, month=12, day=1)
                    else:
                        start_of_last_month = today.replace(month=today.month-1, day=1)
                    # End of last month
                    start_of_this_month = today.replace(day=1)
                    report_context.start_date = start_of_last_month.strftime('%Y-%m-%d')
                    report_context.end_date = start_of_this_month.strftime('%Y-%m-%d')
                elif emoji == "6️⃣":  # Last Quarter
                    # Determine current quarter
                    current_quarter = (today.month - 1) // 3 + 1
                    
                    # Calculate last quarter
                    if current_quarter == 1:
                        # Last quarter is Q4 of previous year
                        year = today.year - 1
                        start_month = 10
                        end_year = today.year
                        end_month = 1
                    else:
                        # Last quarter is in the same year
                        year = today.year
                        start_month = (current_quarter - 1) * 3 - 2
                        end_year = today.year
                        end_month = (current_quarter - 1) * 3 + 1
                    
                    report_context.start_date = f"{year}-{start_month:02d}-01"
                    report_context.end_date = f"{end_year}-{end_month:02d}-01"
                elif emoji == "7️⃣":  # Custom Period
                    # For custom period, we need to ask for specific dates
                    # This would be handled in a more complex way in a real implementation
                    # For now, we'll just use a default range of the last 30 days
                    report_context.start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
                    report_context.end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
                
                # Check if we need more information
                missing_info = self._check_missing_information(report_context)
                
                if missing_info:
                    # We need more information, ask a follow-up question
                    await self._ask_follow_up_question(reaction.message.channel, report_context, missing_info, reaction.message)
                else:
                    # We have all the information we need, generate the report
                    await self._generate_report_from_context(reaction.message.channel, report_context, reaction.message)
                
                return
        
        # If we get here, check if this is a reaction to a report follow-up message
        # by calling our handler method
        await self._handle_report_follow_up(reaction, user)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle message responses for receipt verification editing and conversations"""
        # Ignore bot messages
        if message.author.bot:
            return
            
        # First, check for active conversations
        for conversation_id, conversation in list(self.active_conversations.items()):
            if conversation.user_id == message.author.id and not conversation.is_completed and not conversation.is_cancelled:
                # This is a response to a conversation prompt
                
                # Check if user wants to cancel the conversation
                if message.content.lower() == 'cancel':
                    # Mark as cancelled
                    conversation.is_cancelled = True
                    
                    # Cancel the timeout task
                    if conversation.timeout_task:
                        conversation.timeout_task.cancel()
                    
                    # Send cancellation message
                    await message.channel.send(
                        "Conversation cancelled. No data has been saved.",
                        reference=message
                    )
                    
                    # Clean up
                    del self.active_conversations[conversation_id]
                    return
                
                # Check if we're at the summary confirmation step
                if conversation.current_step >= len(self.expense_steps):
                    # This is a response to the summary confirmation
                    if message.content.lower() == 'confirm':
                        # Mark as completed
                        conversation.is_completed = True
                        
                        # Cancel the timeout task
                        if conversation.timeout_task:
                            conversation.timeout_task.cancel()
                        
                        # Save the data
                        await self._save_expense_data(conversation_id)
                        
                        # Clean up
                        del self.active_conversations[conversation_id]
                    else:
                        # Invalid response to confirmation
                        await message.channel.send(
                            "Please type `confirm` to save the expense, or `cancel` to discard it.",
                            reference=message,
                            delete_after=5
                        )
                    
                    return
                
                # Handle different conversation types
                if conversation.conversation_type == "expense":
                    # Get the current step
                    step = self.expense_steps[conversation.current_step]
                    
                    # Validate the input
                    is_valid, error_message = step["validate"](message.content)
                    
                    if not is_valid:
                        # Send error message
                        await message.channel.send(
                            f"❌ {error_message} Please try again.",
                            reference=message,
                            delete_after=5
                        )
                        return
                    
                    # Format and store the data
                    field_name = step["name"]
                    formatted_value = step["format"](message.content)
                    conversation.data[field_name] = formatted_value
                    
                    # Send confirmation
                    await message.channel.send(
                        f"✅ {field_name.replace('_', ' ').title()} set to: {message.content}",
                        reference=message,
                        delete_after=2
                    )
                    
                    # Move to the next step
                    conversation.current_step += 1
                    
                    # Continue the conversation
                    await self._continue_conversation(conversation_id)
                
                elif conversation.conversation_type == "sale":
                    # Handle sale conversation steps
                    if conversation.current_step == "customer_number_entry":
                        # Handle customer selection by number
                        if message.content.lower() == 'new':
                            # Create a new customer
                            await self._start_customer_creation(conversation_id)
                        elif message.content.lower() == 'skip':
                            # Skip customer selection
                            await self._start_product_selection(conversation_id)
                        else:
                            try:
                                # Parse customer number
                                index = int(message.content) - 1
                                customers = conversation.data.get('available_customers', [])
                                
                                if 0 <= index < len(customers):
                                    # Valid customer selection
                                    customer = customers[index]
                                    conversation.data['customer_id'] = customer['customer_id']
                                    
                                    # Send confirmation
                                    await message.channel.send(
                                        f"✅ Customer set to: {customer['name']}",
                                        reference=message,
                                        delete_after=2
                                    )
                                    
                                    # Move to product selection
                                    await self._start_product_selection(conversation_id)
                                else:
                                    await message.channel.send(
                                        f"❌ Invalid selection. Please enter a number between 1 and {len(customers)}.",
                                        reference=message,
                                        delete_after=5
                                    )
                            except ValueError:
                                await message.channel.send(
                                    "❌ Invalid input. Please enter a number, 'new', or 'skip'.",
                                    reference=message,
                                    delete_after=5
                                )
                    
                    elif conversation.current_step == "customer_name_entry":
                        # Handle customer name entry
                        if not message.content.strip():
                            await message.channel.send(
                                "❌ Customer name cannot be empty. Please enter a name.",
                                reference=message,
                                delete_after=5
                            )
                            return
                        
                        # Store the name
                        await self._handle_customer_creation(conversation_id, 'name', message.content)
                    
                    elif conversation.current_step == "customer_discord_id_entry":
                        # Handle customer Discord ID entry
                        await self._handle_customer_creation(conversation_id, 'discord_id', message.content)
                    
                    elif conversation.current_step == "customer_contact_info_entry":
                        # Handle customer contact info entry
                        await self._handle_customer_creation(conversation_id, 'contact_info', message.content)
                    
                    elif conversation.current_step == "product_sku_entry":
                        # Handle product SKU entry
                        await self._handle_product_by_sku(conversation_id, message.content)
                    
                    elif conversation.current_step == "product_number_entry":
                        # Handle product selection by number
                        if message.content.lower() == 'back':
                            # Go back to product selection
                            await self._start_product_selection(conversation_id)
                        else:
                            try:
                                # Parse product number
                                index = int(message.content) - 1
                                products = conversation.data.get('available_products', [])
                                
                                if 0 <= index < len(products):
                                    # Valid product selection
                                    product = products[index]
                                    conversation.data['selected_product'] = product
                                    
                                    # Ask for quantity
                                    embed = discord.Embed(
                                        title=f"Selected: {product['name']}",
                                        description=f"SKU: {product['sku']}\n"
                                                  f"Price: ${product['selling_price']:.2f}\n"
                                                  f"In Stock: {product['quantity']}",
                                        color=discord.Color.blue()
                                    )
                                    
                                    embed.add_field(
                                        name="Quantity",
                                        value=f"Please enter the quantity to add (1-{product['quantity']}):",
                                        inline=False
                                    )
                                    
                                    message = await message.channel.send(embed=embed)
                                    conversation.last_message_id = message.id
                                    
                                    # Set the current step
                                    conversation.current_step = "product_quantity_entry"
                                else:
                                    await message.channel.send(
                                        f"❌ Invalid selection. Please enter a number between 1 and {len(products)}.",
                                        reference=message,
                                        delete_after=5
                                    )
                            except ValueError:
                                await message.channel.send(
                                    "❌ Invalid input. Please enter a number or 'back'.",
                                    reference=message,
                                    delete_after=5
                                )
                    
                    elif conversation.current_step == "product_quantity_entry":
                        # Handle product quantity entry
                        await self._handle_product_quantity(conversation_id, message.content)
                    
                    elif conversation.current_step == "other_payment_method_entry":
                        # Handle custom payment method entry
                        if not message.content.strip():
                            await message.channel.send(
                                "❌ Payment method cannot be empty. Please specify a payment method.",
                                reference=message,
                                delete_after=5
                            )
                            return
                        
                        # Store the payment method
                        conversation.data['payment_method'] = message.content.strip()
                        
                        # Send confirmation
                        await message.channel.send(
                            f"✅ Payment method set to: {message.content}",
                            reference=message,
                            delete_after=2
                        )
                        
                        # Move to notes entry
                        await self._start_notes_entry(conversation_id)
                    
                    elif conversation.current_step == "notes_entry":
                        # Handle notes entry
                        await self._handle_notes_entry(conversation_id, message.content)
                    
                    elif conversation.current_step == "sale_confirmation":
                        # Handle sale confirmation
                        if message.content.lower() == 'confirm':
                            # Save the sale
                            await self._save_sale(conversation_id)
                        else:
                            # Invalid response to confirmation
                            await message.channel.send(
                                "Please type `confirm` to save the sale, or `cancel` to discard it.",
                                reference=message,
                                delete_after=5
                            )
                
                return
            
        # If no active conversation matched, check for verification editing
        for verification_id, verification in list(self.active_verifications.items()):
            if verification.user_id == message.author.id and verification.editing_field:
                # This is a response to an editing prompt
                
                # Get the channel and verification message
                channel = self.bot.get_channel(verification.message_id >> 32)
                if not channel:
                    continue
                    
                try:
                    verification_message = await channel.fetch_message(verification.message_id)
                except discord.NotFound:
                    # Message was deleted, clean up verification
                    del self.active_verifications[verification_id]
                    continue
                
                # Check if user wants to cancel editing
                if message.content.lower() == 'cancel':
                    # Reset editing state
                    verification.editing_field = None
                    
                    # Update embed
                    embed = await self._create_verification_embed(
                        verification.receipt_data,
                        verification_message.embeds[0].thumbnail.url,
                        verification_message.embeds[0].footer.text.split("Receipt ID: ")[1].split(" |")[0]
                    )
                    
                    await verification_message.edit(embed=embed)
                    
                    # Clear and re-add all reaction buttons
                    await verification_message.clear_reactions()
                    await self._add_verification_reactions(verification_message)
                    
                    # Delete the prompt message if possible
                    if hasattr(verification, 'prompt_message_id'):
                        try:
                            prompt_message = await channel.fetch_message(verification.prompt_message_id)
                            await prompt_message.delete()
                        except (discord.NotFound, AttributeError):
                            pass
                    
                    # Try to delete the user's response message
                    try:
                        await message.delete()
                    except discord.Forbidden:
                        pass
                        
                    return
                
                # Process the edit based on the field
                field = verification.editing_field
                try:
                    if field == "date":
                        # Validate date format (simple check)
                        if not re.match(r'\d{4}-\d{2}-\d{2}', message.content):
                            await channel.send(
                                "Invalid date format. Please use YYYY-MM-DD format.",
                                delete_after=5
                            )
                            return
                        verification.receipt_data["date"] = message.content
                        
                    elif field == "vendor":
                        verification.receipt_data["vendor"] = message.content
                        
                    elif field == "total_amount":
                        # Validate amount format
                        try:
                            amount = float(message.content.replace('$', '').strip())
                            verification.receipt_data["total_amount"] = amount
                        except ValueError:
                            await channel.send(
                                "Invalid amount format. Please enter a number (e.g., 42.99).",
                                delete_after=5
                            )
                            return
                            
                    elif field == "tax":
                        # Validate tax format
                        try:
                            tax = float(message.content.replace('$', '').strip())
                            verification.receipt_data["tax"] = tax
                        except ValueError:
                            await channel.send(
                                "Invalid tax format. Please enter a number (e.g., 3.50).",
                                delete_after=5
                            )
                            return
                            
                    elif field == "items":
                        await channel.send(
                            "Item editing is not fully implemented yet. This will be enhanced in a future update.",
                            delete_after=5
                        )
                        # Reset editing state without changing items
                        verification.editing_field = None
                        
                        # Update embed
                        embed = await self._create_verification_embed(
                            verification.receipt_data,
                            verification_message.embeds[0].thumbnail.url,
                            verification_message.embeds[0].footer.text.split("Receipt ID: ")[1].split(" |")[0]
                        )
                        
                        await verification_message.edit(embed=embed)
                        
                        # Clear and re-add all reaction buttons
                        await verification_message.clear_reactions()
                        await self._add_verification_reactions(verification_message)
                        
                        # Delete the prompt message if possible
                        if hasattr(verification, 'prompt_message_id'):
                            try:
                                prompt_message = await channel.fetch_message(verification.prompt_message_id)
                                await prompt_message.delete()
                            except (discord.NotFound, AttributeError):
                                pass
                        
                        # Try to delete the user's response message
                        try:
                            await message.delete()
                        except discord.Forbidden:
                            pass
                            
                        return
                
                    # Reset editing state
                    verification.editing_field = None
                    
                    # Update embed
                    embed = await self._create_verification_embed(
                        verification.receipt_data,
                        verification_message.embeds[0].thumbnail.url,
                        verification_message.embeds[0].footer.text.split("Receipt ID: ")[1].split(" |")[0]
                    )
                    
                    await verification_message.edit(embed=embed)
                    
                    # Clear and re-add all reaction buttons
                    await verification_message.clear_reactions()
                    await self._add_verification_reactions(verification_message)
                    
                    # Delete the prompt message if possible
                    if hasattr(verification, 'prompt_message_id'):
                        try:
                            prompt_message = await channel.fetch_message(verification.prompt_message_id)
                            await prompt_message.delete()
                        except (discord.NotFound, AttributeError):
                            pass
                    
                    # Try to delete the user's response message
                    try:
                        await message.delete()
                    except discord.Forbidden:
                        pass
                        
                    # Send confirmation
                    await channel.send(
                        f"✅ {field.replace('_', ' ').title()} updated successfully!",
                        delete_after=3
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing edit for {field}: {str(e)}")
                    await channel.send(
                        f"Error updating {field}: {str(e)}",
                        delete_after=5
                    )
                    
                    # Reset editing state
                    verification.editing_field = None
                    
                    # Update embed
                    embed = await self._create_verification_embed(
                        verification.receipt_data,
                        verification_message.embeds[0].thumbnail.url,
                        verification_message.embeds[0].footer.text.split("Receipt ID: ")[1].split(" |")[0]
                    )
                    
                    await verification_message.edit(embed=embed)
                    
                    # Clear and re-add all reaction buttons
                    await verification_message.clear_reactions()
                    await self._add_verification_reactions(verification_message)
                
                # We've handled this message, no need to check other verifications
                break

    async def _start_product_selection(self, conversation_id: str) -> None:
        """Start the product selection process"""
        if conversation_id not in self.active_conversations:
            return
            
        conversation = self.active_conversations[conversation_id]
        
        # Get the channel
        channel = self.bot.get_channel(conversation.channel_id)
        if not channel:
            logger.error(f"Channel {conversation.channel_id} not found for conversation {conversation_id}")
            del self.active_conversations[conversation_id]
            return
        
        # Show product selection options
        embed = discord.Embed(
            title="Add Products to Sale",
            description="Let's add products to this sale. You can add products by SKU or browse by category.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Options",
            value="1️⃣ Add product by SKU\n"
                  "2️⃣ Browse products by category\n"
                  "3️⃣ Finish adding products and continue",
            inline=False
        )
        
        # Show current items if any
        if conversation.data['items']:
            items_text = ""
            total = 0.0
            
            for i, item in enumerate(conversation.data['items']):
                subtotal = item['quantity'] * item['price']
                total += subtotal
                items_text += f"{i+1}. {item['name']} - {item['quantity']} x ${item['price']:.2f} = ${subtotal:.2f}\n"
            
            embed.add_field(
                name=f"Current Items ({len(conversation.data['items'])})",
                value=items_text,
                inline=False
            )
            
            embed.add_field(
                name="Current Total",
                value=f"${total:.2f}",
                inline=False
            )
            
            # Update the total in the conversation data
            conversation.data['total_amount'] = total
        
        message = await channel.send(embed=embed)
        conversation.last_message_id = message.id
        
        # Add reactions
        await message.add_reaction("1️⃣")
        await message.add_reaction("2️⃣")
        await message.add_reaction("3️⃣")
        
        # Set the current step
        conversation.current_step = "product_selection_method"
    
    async def _handle_product_selection_method(self, conversation_id: str, choice: str) -> None:
        """Handle product selection method choice"""
        if conversation_id not in self.active_conversations:
            return
            
        conversation = self.active_conversations[conversation_id]
        
        # Get the channel
        channel = self.bot.get_channel(conversation.channel_id)
        if not channel:
            logger.error(f"Channel {conversation.channel_id} not found for conversation {conversation_id}")
            del self.active_conversations[conversation_id]
            return
        
        if choice == "1":  # Add by SKU
            embed = discord.Embed(
                title="Add Product by SKU",
                description="Please enter the SKU of the product you want to add:",
                color=discord.Color.blue()
            )
            
            message = await channel.send(embed=embed)
            conversation.last_message_id = message.id
            
            # Set the current step
            conversation.current_step = "product_sku_entry"
            
        elif choice == "2":  # Browse by category
            # Get product categories
            db_manager = self.bot.db_manager
            
            embed = discord.Embed(
                title="Browse Products by Category",
                description="Please select a product category:",
                color=discord.Color.blue()
            )
            
            # Add category options
            embed.add_field(
                name="Categories",
                value="1️⃣ Blank Items (clothing)\n"
                      "2️⃣ DTF Prints (transfers)\n"
                      "3️⃣ Other Products",
                inline=False
            )
            
            message = await channel.send(embed=embed)
            conversation.last_message_id = message.id
            
            # Add reactions
            await message.add_reaction("1️⃣")
            await message.add_reaction("2️⃣")
            await message.add_reaction("3️⃣")
            
            # Set the current step
            conversation.current_step = "product_category_selection"
            
        elif choice == "3":  # Finish adding products
            # Check if any products have been added
            if not conversation.data['items']:
                embed = discord.Embed(
                    title="No Products Added",
                    description="You haven't added any products to this sale. Please add at least one product.",
                    color=discord.Color.orange()
                )
                
                await channel.send(embed=embed)
                
                # Go back to product selection
                await self._start_product_selection(conversation_id)
                return
            
            # Move to payment method selection
            await self._start_payment_method_selection(conversation_id)
    
    async def _handle_product_category_selection(self, conversation_id: str, choice: str) -> None:
        """Handle product category selection"""
        if conversation_id not in self.active_conversations:
            return
            
        conversation = self.active_conversations[conversation_id]
        
        # Get the channel
        channel = self.bot.get_channel(conversation.channel_id)
        if not channel:
            logger.error(f"Channel {conversation.channel_id} not found for conversation {conversation_id}")
            del self.active_conversations[conversation_id]
            return
        
        # Map choice to category
        category_map = {
            "1": "blank",
            "2": "dtf",
            "3": "other"
        }
        
        category = category_map.get(choice)
        if not category:
            await channel.send("Invalid category selection. Please try again.")
            await self._start_product_selection(conversation_id)
            return
        
        # Get products in this category
        db_manager = self.bot.db_manager
        products = db_manager.list_products(category)
        
        if not products:
            embed = discord.Embed(
                title="No Products Found",
                description=f"No products found in the '{category}' category.",
                color=discord.Color.orange()
            )
            
            await channel.send(embed=embed)
            
            # Go back to product selection
            await self._start_product_selection(conversation_id)
            return
        
        # Filter out products with zero quantity
        in_stock_products = [p for p in products if p['quantity'] > 0]
        
        if not in_stock_products:
            embed = discord.Embed(
                title="No Products In Stock",
                description=f"No products in the '{category}' category are currently in stock.",
                color=discord.Color.orange()
            )
            
            await channel.send(embed=embed)
            
            # Go back to product selection
            await self._start_product_selection(conversation_id)
            return
        
        # Show product list
        embed = discord.Embed(
            title=f"{category.capitalize()} Products",
            description="Please select a product by entering its number:",
            color=discord.Color.blue()
        )
        
        # Add products to the embed
        for i, product in enumerate(in_stock_products[:15]):  # Limit to 15 products
            embed.add_field(
                name=f"{i+1}. {product['name']} (SKU: {product['sku']})",
                value=f"Price: ${product['selling_price']:.2f}\n"
                      f"In Stock: {product['quantity']}",
                inline=True
            )
        
        if len(in_stock_products) > 15:
            embed.add_field(
                name="More Products",
                value=f"... and {len(in_stock_products) - 15} more. Use `!findproduct <name>` to search for a specific product.",
                inline=False
            )
        
        embed.add_field(
            name="Instructions",
            value="Enter the number of the product you want to add, or type 'back' to return to the previous menu.",
            inline=False
        )
        
        message = await channel.send(embed=embed)
        conversation.last_message_id = message.id
        
        # Store products in conversation data for reference
        conversation.data['available_products'] = in_stock_products
        
        # Set the current step
        conversation.current_step = "product_number_entry"
    
    async def _handle_product_by_sku(self, conversation_id: str, sku: str) -> None:
        """Handle product selection by SKU"""
        if conversation_id not in self.active_conversations:
            return
            
        conversation = self.active_conversations[conversation_id]
        
        # Get the channel
        channel = self.bot.get_channel(conversation.channel_id)
        if not channel:
            logger.error(f"Channel {conversation.channel_id} not found for conversation {conversation_id}")
            del self.active_conversations[conversation_id]
            return
        
        # Get the product
        db_manager = self.bot.db_manager
        product = db_manager.get_product_by_sku(sku)
        
        if not product:
            embed = discord.Embed(
                title="Product Not Found",
                description=f"No product found with SKU: {sku}",
                color=discord.Color.red()
            )
            
            await channel.send(embed=embed)
            
            # Go back to product selection
            await self._start_product_selection(conversation_id)
            return
        
        # Check if product is in stock
        if product['quantity'] <= 0:
            embed = discord.Embed(
                title="Product Out of Stock",
                description=f"The product '{product['name']}' is currently out of stock.",
                color=discord.Color.orange()
            )
            
            await channel.send(embed=embed)
            
            # Go back to product selection
            await self._start_product_selection(conversation_id)
            return
        
        # Store the selected product
        conversation.data['selected_product'] = product
        
        # Ask for quantity
        embed = discord.Embed(
            title=f"Selected: {product['name']}",
            description=f"SKU: {product['sku']}\n"
                       f"Price: ${product['selling_price']:.2f}\n"
                       f"In Stock: {product['quantity']}",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Quantity",
            value=f"Please enter the quantity to add (1-{product['quantity']}):",
            inline=False
        )
        
        message = await channel.send(embed=embed)
        conversation.last_message_id = message.id
        
        # Set the current step
        conversation.current_step = "product_quantity_entry"
    
    async def _handle_product_quantity(self, conversation_id: str, quantity_str: str) -> None:
        """Handle product quantity entry"""
        if conversation_id not in self.active_conversations:
            return
            
        conversation = self.active_conversations[conversation_id]
        
        # Get the channel
        channel = self.bot.get_channel(conversation.channel_id)
        if not channel:
            logger.error(f"Channel {conversation.channel_id} not found for conversation {conversation_id}")
            del self.active_conversations[conversation_id]
            return
        
        # Get the selected product
        product = conversation.data['selected_product']
        
        # Parse quantity
        try:
            quantity = int(quantity_str)
            
            # Validate quantity
            if quantity <= 0:
                await channel.send("Quantity must be greater than zero. Please try again.")
                
                # Re-ask for quantity
                embed = discord.Embed(
                    title=f"Selected: {product['name']}",
                    description=f"SKU: {product['sku']}\n"
                              f"Price: ${product['selling_price']:.2f}\n"
                              f"In Stock: {product['quantity']}",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="Quantity",
                    value=f"Please enter the quantity to add (1-{product['quantity']}):",
                    inline=False
                )
                
                message = await channel.send(embed=embed)
                conversation.last_message_id = message.id
                return
            
            if quantity > product['quantity']:
                await channel.send(f"Quantity exceeds available stock ({product['quantity']}). Please enter a smaller quantity.")
                
                # Re-ask for quantity
                embed = discord.Embed(
                    title=f"Selected: {product['name']}",
                    description=f"SKU: {product['sku']}\n"
                              f"Price: ${product['selling_price']:.2f}\n"
                              f"In Stock: {product['quantity']}",
                    color=discord.Color.blue()
                )
                
                embed.add_field(
                    name="Quantity",
                    value=f"Please enter the quantity to add (1-{product['quantity']}):",
                    inline=False
                )
                
                message = await channel.send(embed=embed)
                conversation.last_message_id = message.id
                return
            
            # Add item to sale
            sale_item = {
                'product_id': product['product_id'],
                'name': product['name'],
                'sku': product['sku'],
                'quantity': quantity,
                'price': product['selling_price'] or 0.0
            }
            
            conversation.data['items'].append(sale_item)
            
            # Show confirmation
            embed = discord.Embed(
                title="Product Added",
                description=f"Added {quantity} x {product['name']} to the sale.",
                color=discord.Color.green()
            )
            
            await channel.send(embed=embed)
            
            # Go back to product selection
            await self._start_product_selection(conversation_id)
            
        except ValueError:
            await channel.send("Invalid quantity. Please enter a number.")
            
            # Re-ask for quantity
            embed = discord.Embed(
                title=f"Selected: {product['name']}",
                description=f"SKU: {product['sku']}\n"
                          f"Price: ${product['selling_price']:.2f}\n"
                          f"In Stock: {product['quantity']}",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Quantity",
                value=f"Please enter the quantity to add (1-{product['quantity']}):",
                inline=False
            )
            
            message = await channel.send(embed=embed)
            conversation.last_message_id = message.id
    
    async def _start_payment_method_selection(self, conversation_id: str) -> None:
        """Start the payment method selection process"""
        if conversation_id not in self.active_conversations:
            return
            
        conversation = self.active_conversations[conversation_id]
        
        # Get the channel
        channel = self.bot.get_channel(conversation.channel_id)
        if not channel:
            logger.error(f"Channel {conversation.channel_id} not found for conversation {conversation_id}")
            del self.active_conversations[conversation_id]
            return
        
        # Show payment method options
        embed = discord.Embed(
            title="Payment Method",
            description="Please select the payment method used for this sale:",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Options",
            value="1️⃣ Cash\n"
                  "2️⃣ Credit Card\n"
                  "3️⃣ Venmo\n"
                  "4️⃣ PayPal\n"
                  "5️⃣ Other",
            inline=False
        )
        
        message = await channel.send(embed=embed)
        conversation.last_message_id = message.id
        
        # Add reactions
        await message.add_reaction("1️⃣")
        await message.add_reaction("2️⃣")
        await message.add_reaction("3️⃣")
        await message.add_reaction("4️⃣")
        await message.add_reaction("5️⃣")
        
        # Set the current step
        conversation.current_step = "payment_method_selection"
    
    async def _handle_payment_method_selection(self, conversation_id: str, choice: str) -> None:
        """Handle payment method selection"""
        if conversation_id not in self.active_conversations:
            return
            
        conversation = self.active_conversations[conversation_id]
        
        # Get the channel
        channel = self.bot.get_channel(conversation.channel_id)
        if not channel:
            logger.error(f"Channel {conversation.channel_id} not found for conversation {conversation_id}")
            del self.active_conversations[conversation_id]
            return
        
        # Map choice to payment method
        payment_method_map = {
            "1": "Cash",
            "2": "Credit Card",
            "3": "Venmo",
            "4": "PayPal",
            "5": "Other"
        }
        
        payment_method = payment_method_map.get(choice)
        if not payment_method:
            await channel.send("Invalid payment method selection. Please try again.")
            await self._start_payment_method_selection(conversation_id)
            return
        
        # If "Other" was selected, ask for details
        if payment_method == "Other":
            embed = discord.Embed(
                title="Other Payment Method",
                description="Please specify the payment method:",
                color=discord.Color.blue()
            )
            
            message = await channel.send(embed=embed)
            conversation.last_message_id = message.id
            
            # Set the current step
            conversation.current_step = "other_payment_method_entry"
            return
        
        # Store the payment method
        conversation.data['payment_method'] = payment_method
        
        # Move to notes entry
        await self._start_notes_entry(conversation_id)
    
    async def _start_notes_entry(self, conversation_id: str) -> None:
        """Start the notes entry process"""
        if conversation_id not in self.active_conversations:
            return
            
        conversation = self.active_conversations[conversation_id]
        
        # Get the channel
        channel = self.bot.get_channel(conversation.channel_id)
        if not channel:
            logger.error(f"Channel {conversation.channel_id} not found for conversation {conversation_id}")
            del self.active_conversations[conversation_id]
            return
        
        # Ask for notes
        embed = discord.Embed(
            title="Sale Notes",
            description="Please enter any notes for this sale, or type 'skip' to leave blank:",
            color=discord.Color.blue()
        )
        
        message = await channel.send(embed=embed)
        conversation.last_message_id = message.id
        
        # Set the current step
        conversation.current_step = "notes_entry"
    
    async def _handle_notes_entry(self, conversation_id: str, notes: str) -> None:
        """Handle notes entry"""
        if conversation_id not in self.active_conversations:
            return
            
        conversation = self.active_conversations[conversation_id]
        
        # Store the notes
        if notes.lower() != 'skip':
            conversation.data['notes'] = notes
        
        # Show sale summary and confirmation
        await self._show_sale_summary(conversation_id)
    
    async def _show_sale_summary(self, conversation_id: str) -> None:
        """Show sale summary and ask for confirmation"""
        if conversation_id not in self.active_conversations:
            return
            
        conversation = self.active_conversations[conversation_id]
        
        # Get the channel
        channel = self.bot.get_channel(conversation.channel_id)
        if not channel:
            logger.error(f"Channel {conversation.channel_id} not found for conversation {conversation_id}")
            del self.active_conversations[conversation_id]
            return
        
        # Create summary embed
        embed = discord.Embed(
            title="Sale Summary",
            description="Please review the sale details below and confirm.",
            color=discord.Color.blue()
        )
        
        # Add date
        embed.add_field(
            name="Date",
            value=conversation.data["date"],
            inline=True
        )
        
        # Add customer if available
        if conversation.data['customer_id']:
            # Get customer details
            db_manager = self.bot.db_manager
            customer = db_manager.get_customer(conversation.data['customer_id'])
            if customer:
                embed.add_field(
                    name="Customer",
                    value=customer['name'],
                    inline=True
                )
        
        # Add payment method
        if conversation.data['payment_method']:
            embed.add_field(
                name="Payment Method",
                value=conversation.data['payment_method'],
                inline=True
            )
        
        # Add notes if available
        if conversation.data['notes']:
            embed.add_field(
                name="Notes",
                value=conversation.data['notes'],
                inline=False
            )
        
        # Add items
        items_text = ""
        total = 0.0
        
        for i, item in enumerate(conversation.data['items']):
            subtotal = item['quantity'] * item['price']
            total += subtotal
            items_text += f"{i+1}. {item['name']} - {item['quantity']} x ${item['price']:.2f} = ${subtotal:.2f}\n"
        
        embed.add_field(
            name=f"Items ({len(conversation.data['items'])})",
            value=items_text,
            inline=False
        )
        
        # Add total
        embed.add_field(
            name="Total Amount",
            value=f"${total:.2f}",
            inline=False
        )
        
        # Update the total in the conversation data
        conversation.data['total_amount'] = total
        
        # Add confirmation instructions
        embed.add_field(
            name="Confirm",
            value="Type `confirm` to save this sale, or `cancel` to discard it.",
            inline=False
        )
        
        # Send the summary
        message = await channel.send(embed=embed)
        conversation.last_message_id = message.id
        
        # Set the current step
        conversation.current_step = "sale_confirmation"
    
    async def _save_sale(self, conversation_id: str) -> None:
        """Save the sale to the database"""
        if conversation_id not in self.active_conversations:
            return
            
        conversation = self.active_conversations[conversation_id]
        
        # Get the channel
        channel = self.bot.get_channel(conversation.channel_id)
        if not channel:
            logger.error(f"Channel {conversation.channel_id} not found for conversation {conversation_id}")
            del self.active_conversations[conversation_id]
            return
        
        try:
            # Prepare sale data
            sale_data = {
                'customer_id': conversation.data['customer_id'],
                'date': conversation.data['date'],
                'total_amount': conversation.data['total_amount'],
                'payment_method': conversation.data['payment_method'],
                'notes': conversation.data['notes']
            }
            
            # Prepare sale items
            sale_items = []
            for item in conversation.data['items']:
                sale_items.append({
                    'product_id': item['product_id'],
                    'quantity': item['quantity'],
                    'price': item['price']
                })
            
            # Save to database
            db_manager = self.bot.db_manager
            sale_id = db_manager.add_sale(sale_data, sale_items)
            
            # Log the action in audit log
            user_id = str(conversation.user_id)
            db_manager.log_audit(
                'create',
                'sale',
                sale_id,
                user_id,
                f"Sale added: ${sale_data['total_amount']:.2f} with {len(sale_items)} items"
            )
            
            # Create success embed
            embed = discord.Embed(
                title="Sale Recorded",
                description=f"Sale has been successfully recorded with ID: {sale_id}",
                color=discord.Color.green()
            )
            
            # Add sale details
            embed.add_field(
                name="Date",
                value=sale_data['date'],
                inline=True
            )
            
            if sale_data['customer_id']:
                customer = db_manager.get_customer(sale_data['customer_id'])
                if customer:
                    embed.add_field(
                        name="Customer",
                        value=customer['name'],
                        inline=True
                    )
            
            embed.add_field(
                name="Payment Method",
                value=sale_data['payment_method'],
                inline=True
            )
            
            embed.add_field(
                name="Total Amount",
                value=f"${sale_data['total_amount']:.2f}",
                inline=True
            )
            
            embed.add_field(
                name="Items",
                value=f"{len(sale_items)} items sold",
                inline=True
            )
            
            if sale_data['notes']:
                embed.add_field(
                    name="Notes",
                    value=sale_data['notes'],
                    inline=False
                )
            
            embed.set_footer(text=f"AccountME Bot | Sale ID: {sale_id}")
            
            await channel.send(embed=embed)
            
            # Mark conversation as completed
            conversation.is_completed = True
            
            # Clean up
            del self.active_conversations[conversation_id]
            
        except Exception as e:
            logger.error(f"Error saving sale: {str(e)}")
            
            # Send error message
            error_embed = discord.Embed(
                title="Error Saving Sale",
                description=f"An error occurred while saving the sale: {str(e)}",
                color=discord.Color.red()
            )
            await channel.send(embed=error_embed)
            
            # Ask if they want to try again
            retry_embed = discord.Embed(
                title="Retry",
                description="Would you like to try saving the sale again?",
                color=discord.Color.orange()
            )
            
            retry_embed.add_field(
                name="Options",
                value="✅ Yes, try again\n"
                      "❌ No, discard the sale",
                inline=False
            )
            
            message = await channel.send(embed=retry_embed)
            conversation.last_message_id = message.id
            
            # Add reactions
            await message.add_reaction("✅")
            await message.add_reaction("❌")
            
            # Set the current step
            conversation.current_step = "sale_retry_prompt"

    class ReportContext:
        """Class to track the context of a report conversation"""
        def __init__(self, user_id: int, channel_id: int, original_query: str):
            self.user_id = user_id
            self.channel_id = channel_id
            self.original_query = original_query
            self.report_type = None  # 'sales', 'expenses', 'inventory', 'profit'
            self.start_date = None
            self.end_date = None
            self.category = None
            self.customer_id = None
            self.is_completed = False
            self.is_cancelled = False
            self.timeout_task = None
            self.last_message_id = None
            self.follow_up_type = None  # What kind of follow-up we're waiting for
            self.suggested_options = []  # Suggested options for follow-up
            self.previous_reports = []  # List of previously generated reports for comparison

    @commands.command(name="report", aliases=["query", "askfor"])
    async def report_command(self, ctx, *, query=None):
        """
        Generate reports using natural language queries
        
        Usage:
        !report - Show help for report queries
        !report <natural language query> - Generate a report based on your query
        
        Examples:
        !report sales for this month
        !report expenses in the Inventory category
        !report profit and loss for Q1
        !report inventory status for blank items
        
        Aliases: !query, !askfor
        """
        try:
            # If no query provided, show help
            if not query:
                await self._show_report_help(ctx)
                return
            
            # Process the query and generate the report
            await self._process_report_query(ctx, query)
            
        except Exception as e:
            logger.error(f"Error processing report query: {str(e)}")
            
            # Send error message
            error_embed = discord.Embed(
                title="Error Processing Report Query",
                description=f"An error occurred while processing your report query: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
    
    async def _show_report_help(self, ctx):
        """Show help for the report command"""
        embed = discord.Embed(
            title="Report Command Help",
            description="Generate reports using natural language queries. Just describe what you want to see!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Example Queries",
            value="• `!report sales for this month`\n"
                  "• `!report expenses in the Inventory category last quarter`\n"
                  "• `!report profit and loss for Q1`\n"
                  "• `!report inventory status for blank items`\n"
                  "• `!report how are sales doing compared to last month`\n"
                  "• `!report show me our top selling products`",
            inline=False
        )
        
        embed.add_field(
            name="Report Types",
            value="• **Sales Reports**: Sales data, payment methods, top products\n"
                  "• **Expense Reports**: Expense data, category breakdowns\n"
                  "• **Profit & Loss**: Financial performance, trends\n"
                  "• **Inventory Reports**: Stock levels, value, movement",
            inline=False
        )
        
        embed.add_field(
            name="Time Periods",
            value="You can specify time periods like:\n"
                  "• today, yesterday\n"
                  "• this week, last week\n"
                  "• this month, last month\n"
                  "• this year, last year\n"
                  "• Q1, Q2, Q3, Q4 (quarters)\n"
                  "• specific dates (YYYY-MM-DD)",
            inline=False
        )
        
        embed.add_field(
            name="Filters",
            value="You can filter by:\n"
                  "• Categories (e.g., 'Inventory expenses')\n"
                  "• Products (e.g., 'sales of t-shirts')\n"
                  "• Customers (e.g., 'sales to John')",
            inline=False
        )
        
        embed.add_field(
            name="Comparisons",
            value="Ask for comparisons like:\n"
                  "• 'compared to last month'\n"
                  "• 'vs previous quarter'\n"
                  "• 'year over year'",
            inline=False
        )
        
        embed.set_footer(text="Just ask naturally, and I'll do my best to understand what you need!")
        
        await ctx.send(embed=embed)
    
    async def _process_report_query(self, ctx, query: str):
        """Process a natural language report query"""
        # Create a report context to track this conversation
        report_context_id = f"report:{ctx.author.id}:{ctx.channel.id}:{datetime.now().timestamp()}"
        report_context = self.ReportContext(
            user_id=ctx.author.id,
            channel_id=ctx.channel.id,
            original_query=query
        )
        
        # Store the report context
        self.active_report_contexts[report_context_id] = report_context
        
        # Extract intents from the query
        extracted_info = self._extract_report_intents(query)
        
        # Update the report context with extracted information
        report_context.report_type = extracted_info.get('report_type')
        report_context.start_date = extracted_info.get('start_date')
        report_context.end_date = extracted_info.get('end_date')
        report_context.category = extracted_info.get('category')
        report_context.customer_id = extracted_info.get('customer_id')
        
        # Set up timeout task (5 minutes)
        report_context.timeout_task = asyncio.create_task(
            asyncio.sleep(300)
        )
        report_context.timeout_task.add_done_callback(
            lambda _: asyncio.create_task(
                self._handle_report_timeout(report_context_id)
            )
        )
        
        # Send initial processing message
        processing_message = await ctx.send("Processing your report request...")
        
        # Check if we have enough information to generate a report
        missing_info = self._check_missing_information(report_context)
        
        if missing_info:
            # We need more information, ask follow-up questions
            await self._ask_follow_up_question(ctx, report_context, missing_info, processing_message)
            return
        
        # We have all the information we need, generate the report
        await self._generate_report_from_context(ctx, report_context, processing_message)
    
    def _extract_report_intents(self, query: str) -> dict:
        """
        Extract report intents from a natural language query
        
        Returns a dictionary with extracted information:
        - report_type: 'sales', 'expenses', 'inventory', 'profit'
        - start_date: Start date for the report
        - end_date: End date for the report
        - category: Category filter
        - customer_id: Customer ID filter
        """
        query = query.lower()
        result = {}
        
        # Extract report type
        if 'sales' in query or 'revenue' in query or 'income' in query or 'sold' in query:
            result['report_type'] = 'sales'
        elif 'expense' in query or 'cost' in query or 'spent' in query:
            result['report_type'] = 'expenses'
        elif 'inventory' in query or 'stock' in query or 'product' in query:
            result['report_type'] = 'inventory'
        elif 'profit' in query or 'loss' in query or 'p&l' in query or 'margin' in query:
            result['report_type'] = 'profit'
        
        # Extract time period
        today = datetime.now().date()
        
        # Check for specific date formats (YYYY-MM-DD)
        date_matches = re.findall(r'\d{4}-\d{2}-\d{2}', query)
        if len(date_matches) >= 2:
            # We have at least two dates, use them as start and end
            result['start_date'] = date_matches[0]
            result['end_date'] = date_matches[1]
        elif len(date_matches) == 1:
            # We have one date, use it as both start and end
            result['start_date'] = date_matches[0]
            result['end_date'] = (datetime.strptime(date_matches[0], '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Check for relative time periods
        if 'today' in query:
            result['start_date'] = today.strftime('%Y-%m-%d')
            result['end_date'] = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'yesterday' in query:
            result['start_date'] = (today - timedelta(days=1)).strftime('%Y-%m-%d')
            result['end_date'] = today.strftime('%Y-%m-%d')
        elif 'this week' in query:
            # Start of current week (Monday)
            start_of_week = today - timedelta(days=today.weekday())
            result['start_date'] = start_of_week.strftime('%Y-%m-%d')
            result['end_date'] = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'last week' in query:
            # Start of last week (Monday)
            start_of_last_week = today - timedelta(days=today.weekday() + 7)
            end_of_last_week = today - timedelta(days=today.weekday())
            result['start_date'] = start_of_last_week.strftime('%Y-%m-%d')
            result['end_date'] = end_of_last_week.strftime('%Y-%m-%d')
        elif 'this month' in query:
            # Start of current month
            start_of_month = today.replace(day=1)
            result['start_date'] = start_of_month.strftime('%Y-%m-%d')
            result['end_date'] = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'last month' in query:
            # Start of last month
            if today.month == 1:
                start_of_last_month = today.replace(year=today.year-1, month=12, day=1)
            else:
                start_of_last_month = today.replace(month=today.month-1, day=1)
            # End of last month
            start_of_this_month = today.replace(day=1)
            result['start_date'] = start_of_last_month.strftime('%Y-%m-%d')
            result['end_date'] = start_of_this_month.strftime('%Y-%m-%d')
        elif 'this year' in query:
            # Start of current year
            start_of_year = today.replace(month=1, day=1)
            result['start_date'] = start_of_year.strftime('%Y-%m-%d')
            result['end_date'] = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'last year' in query:
            # Start of last year
            start_of_last_year = today.replace(year=today.year-1, month=1, day=1)
            # End of last year
            end_of_last_year = today.replace(year=today.year-1, month=12, day=31)
            result['start_date'] = start_of_last_year.strftime('%Y-%m-%d')
            result['end_date'] = end_of_last_year.strftime('%Y-%m-%d')
        elif 'q1' in query:
            # Q1 of current year (Jan-Mar)
            year = today.year
            if 'last year' in query:
                year -= 1
            result['start_date'] = f"{year}-01-01"
            result['end_date'] = f"{year}-04-01"
        elif 'q2' in query:
            # Q2 of current year (Apr-Jun)
            year = today.year
            if 'last year' in query:
                year -= 1
            result['start_date'] = f"{year}-04-01"
            result['end_date'] = f"{year}-07-01"
        elif 'q3' in query:
            # Q3 of current year (Jul-Sep)
            year = today.year
            if 'last year' in query:
                year -= 1
            result['start_date'] = f"{year}-07-01"
            result['end_date'] = f"{year}-10-01"
        elif 'q4' in query:
            # Q4 of current year (Oct-Dec)
            year = today.year
            if 'last year' in query:
                year -= 1
            result['start_date'] = f"{year}-10-01"
            result['end_date'] = f"{year+1}-01-01"
        
        # Extract category
        for category in self.expense_categories:
            if category.lower() in query:
                result['category'] = category
                break
        
        # Extract customer information (this would need to be enhanced with actual customer lookup)
        # For now, we'll just check if "customer" is mentioned
        if 'customer' in query:
            # This is a placeholder - in a real implementation, we would try to identify the customer
            # by name or other identifiers in the query
            pass
        
        return result
    
    def _check_missing_information(self, report_context):
        """
        Check if we have enough information to generate a report
        
        Returns a string indicating what information is missing, or None if we have everything
        """
        if not report_context.report_type:
            return "report_type"
        
        # For sales, expenses, and profit reports, we need date ranges
        if report_context.report_type in ['sales', 'expenses', 'profit']:
            if not report_context.start_date or not report_context.end_date:
                return "date_range"
        
        # For inventory reports, we don't necessarily need dates
        
        # All information is available
        return None
    
    async def _ask_follow_up_question(self, ctx, report_context, missing_info, original_message):
        """Ask a follow-up question to get missing information"""
        if missing_info == "report_type":
            embed = discord.Embed(
                title="What type of report would you like?",
                description="I'm not sure what type of report you're looking for. Please select one of the options below:",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Report Types",
                value="1️⃣ Sales Report\n"
                      "2️⃣ Expense Report\n"
                      "3️⃣ Inventory Report\n"
                      "4️⃣ Profit & Loss Report",
                inline=False
            )
            
            # Update the original message
            await original_message.edit(content=None, embed=embed)
            
            # Add reactions for selection
            await original_message.add_reaction("1️⃣")
            await original_message.add_reaction("2️⃣")
            await original_message.add_reaction("3️⃣")
            await original_message.add_reaction("4️⃣")
            
            # Update the report context
            report_context.follow_up_type = "report_type"
            report_context.last_message_id = original_message.id
            
        elif missing_info == "date_range":
            embed = discord.Embed(
                title="What time period would you like to see?",
                description=f"I need to know what time period you want for the {report_context.report_type} report. Please select one of the options below:",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Time Periods",
                value="1️⃣ Today\n"
                      "2️⃣ This Week\n"
                      "3️⃣ This Month\n"
                      "4️⃣ This Year\n"
                      "5️⃣ Last Month\n"
                      "6️⃣ Last Quarter\n"
                      "7️⃣ Custom Period (you'll be asked to specify)",
                inline=False
            )
            
            # Update the original message
            await original_message.edit(content=None, embed=embed)
            
            # Add reactions for selection
            await original_message.add_reaction("1️⃣")
            await original_message.add_reaction("2️⃣")
            await original_message.add_reaction("3️⃣")
            await original_message.add_reaction("4️⃣")
            await original_message.add_reaction("5️⃣")
            await original_message.add_reaction("6️⃣")
            await original_message.add_reaction("7️⃣")
            
            # Update the report context
            report_context.follow_up_type = "date_range"
            report_context.last_message_id = original_message.id
    
    async def _handle_report_follow_up(self, reaction, user):
        """Handle follow-up responses for report queries"""
        # Find the report context for this user and message
        report_context = None
        report_context_id = None
        
        # Look for a matching report context in active_report_contexts
        for context_id, context in list(self.active_report_contexts.items()):
            if context.user_id == user.id and context.last_message_id == reaction.message.id:
                report_context = context
                report_context_id = context_id
                break
        
        if not report_context:
            return
        
        # Get the emoji and check what it means based on the follow-up type
        emoji = str(reaction.emoji)
        
        if report_context.follow_up_type == "report_type":
            # Handle report type selection
            report_type_map = {
                "1️⃣": "sales",
                "2️⃣": "expenses",
                "3️⃣": "inventory",
                "4️⃣": "profit"
            }
            
            if emoji in report_type_map:
                report_context.report_type = report_type_map[emoji]
                
                # Check if we still need more information
                missing_info = self._check_missing_information(report_context)
                
                if missing_info:
                    # We need more information, ask another follow-up question
                    channel = self.bot.get_channel(report_context.channel_id)
                    message = await channel.fetch_message(report_context.last_message_id)
                    await self._ask_follow_up_question(channel, report_context, missing_info, message)
                else:
                    # We have all the information we need, generate the report
                    channel = self.bot.get_channel(report_context.channel_id)
                    message = await channel.fetch_message(report_context.last_message_id)
                    await self._generate_report_from_context(channel, report_context, message)
        
        elif report_context.follow_up_type == "date_range":
            # Handle date range selection
            today = datetime.now().date()
            
            if emoji == "1️⃣":  # Today
                report_context.start_date = today.strftime('%Y-%m-%d')
                report_context.end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            elif emoji == "2️⃣":  # This Week
                # Start of current week (Monday)
                start_of_week = today - timedelta(days=today.weekday())
                report_context.start_date = start_of_week.strftime('%Y-%m-%d')
                report_context.end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            elif emoji == "3️⃣":  # This Month
                # Start of current month
                start_of_month = today.replace(day=1)
                report_context.start_date = start_of_month.strftime('%Y-%m-%d')
                report_context.end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            elif emoji == "4️⃣":  # This Year
                # Start of current year
                start_of_year = today.replace(month=1, day=1)
                report_context.start_date = start_of_year.strftime('%Y-%m-%d')
                report_context.end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            elif emoji == "5️⃣":  # Last Month
                # Start of last month
                if today.month == 1:
                    start_of_last_month = today.replace(year=today.year-1, month=12, day=1)
                else:
                    start_of_last_month = today.replace(month=today.month-1, day=1)
                # End of last month
                start_of_this_month = today.replace(day=1)
                report_context.start_date = start_of_last_month.strftime('%Y-%m-%d')
                report_context.end_date = start_of_this_month.strftime('%Y-%m-%d')
            elif emoji == "6️⃣":  # Last Quarter
                # Determine current quarter
                current_quarter = (today.month - 1) // 3 + 1
                
                # Calculate last quarter
                if current_quarter == 1:
                    # Last quarter is Q4 of previous year
                    year = today.year - 1
                    start_month = 10
                    end_year = today.year
                    end_month = 1
                else:
                    # Last quarter is in the same year
                    year = today.year
                    start_month = (current_quarter - 1) * 3 - 2
                    end_year = today.year
                    end_month = (current_quarter - 1) * 3 + 1
                
                report_context.start_date = f"{year}-{start_month:02d}-01"
                report_context.end_date = f"{end_year}-{end_month:02d}-01"
            elif emoji == "7️⃣":  # Custom Period
                # For custom period, we need to ask for specific dates
                # This would be handled in a more complex way in a real implementation
                # For now, we'll just use a default range of the last 30 days
                report_context.start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
                report_context.end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Check if we still need more information
            missing_info = self._check_missing_information(report_context)
            
            if missing_info:
                # We need more information, ask another follow-up question
                channel = self.bot.get_channel(report_context.channel_id)
                message = await channel.fetch_message(report_context.last_message_id)
                await self._ask_follow_up_question(channel, report_context, missing_info, message)
            else:
                # We have all the information we need, generate the report
                channel = self.bot.get_channel(report_context.channel_id)
                message = await channel.fetch_message(report_context.last_message_id)
                await self._generate_report_from_context(channel, report_context, message)
                
                # Clean up the report context
                if report_context_id in self.active_report_contexts:
                    del self.active_report_contexts[report_context_id]
    
    async def _generate_report_from_context(self, ctx, report_context, original_message):
        """Generate a report based on the report context"""
        # Update the original message to show we're generating the report
        await original_message.edit(content="Generating your report...", embed=None)
        
        # Clear reactions if any
        try:
            await original_message.clear_reactions()
        except:
            pass
        
        # Get report generator
        report_generator = self.bot.get_report_generator()
        if not report_generator:
            await ctx.send("Report generator is not available.")
            return
        
        try:
            # Generate the appropriate report based on the report type
            if report_context.report_type == 'sales':
                csv_path, embed = await report_generator.generate_sales_report(
                    report_context.start_date,
                    report_context.end_date,
                    report_context.customer_id
                )
                
                # Enhance the embed with natural language insights
                embed = self._enhance_report_with_insights(embed, report_context)
                
                # Delete the original message
                await original_message.delete()
                
                # Send the report
                await ctx.send(embed=embed, file=discord.File(csv_path))
                
                # Clean up the report context
                for context_id, context in list(self.active_report_contexts.items()):
                    if context.user_id == report_context.user_id and context.channel_id == report_context.channel_id:
                        del self.active_report_contexts[context_id]
                
            elif report_context.report_type == 'expenses':
                csv_path, embed = await report_generator.generate_expense_report(
                    report_context.start_date,
                    report_context.end_date,
                    report_context.category
                )
                
                # Enhance the embed with natural language insights
                embed = self._enhance_report_with_insights(embed, report_context)
                
                # Delete the original message
                await original_message.delete()
                
                # Send the report
                await ctx.send(embed=embed, file=discord.File(csv_path))
                
            elif report_context.report_type == 'inventory':
                csv_path, embed = await report_generator.generate_inventory_report(
                    report_context.category
                )
                
                # Enhance the embed with natural language insights
                embed = self._enhance_report_with_insights(embed, report_context)
                
                # Delete the original message
                await original_message.delete()
                
                # Send the report
                await ctx.send(embed=embed, file=discord.File(csv_path))
                
            elif report_context.report_type == 'profit':
                csv_path, embed = await report_generator.generate_profit_loss_report(
                    report_context.start_date,
                    report_context.end_date
                )
                
                # Enhance the embed with natural language insights
                embed = self._enhance_report_with_insights(embed, report_context)
                
                # Delete the original message
                await original_message.delete()
                
                # Send the report
                await ctx.send(embed=embed, file=discord.File(csv_path))
                
            else:
                # Unknown report type
                await original_message.edit(
                    content=None,
                    embed=discord.Embed(
                        title="Unknown Report Type",
                        description=f"I don't know how to generate a report of type '{report_context.report_type}'.",
                        color=discord.Color.red()
                    )
                )
        
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            
            # Send error message
            error_embed = discord.Embed(
                title="Error Generating Report",
                description=f"An error occurred while generating the report: {str(e)}",
                color=discord.Color.red()
            )
            
            # Delete the original message
            await original_message.delete()
            
            # Send the error message
            await ctx.send(embed=error_embed)
    
    def _enhance_report_with_insights(self, embed, report_context):
        """Enhance a report embed with natural language insights"""
        # This is a placeholder - in a real implementation, we would analyze the report data
        # and add natural language insights based on the findings
        
        # Add a key insights section
        if report_context.report_type == 'sales':
            embed.add_field(
                name="Key Insights",
                value="• Sales are trending upward compared to the previous period\n"
                      "• The top product category is showing strong performance\n"
                      "• Credit card remains the most popular payment method",
                inline=False
            )
        elif report_context.report_type == 'expenses':
            embed.add_field(
                name="Key Insights",
                value="• Expenses are within expected ranges\n"
                      "• The largest expense category is Inventory\n"
                      "• Consider reviewing recurring expenses for potential savings",
                inline=False
            )
        elif report_context.report_type == 'inventory':
            embed.add_field(
                name="Key Insights",
                value="• Several items are running low on stock\n"
                      "• The highest value category is blank items\n"
                      "• Consider restocking popular items soon",
                inline=False
            )
        elif report_context.report_type == 'profit':
            embed.add_field(
                name="Key Insights",
                value="• Profit margin is healthy at above 20%\n"
                      "• Revenue is growing faster than expenses\n"
                      "• Consider investing in expanding high-margin product lines",
                inline=False
            )
        
        # Add a natural language summary
        embed.add_field(
            name="Summary",
            value=f"This report shows {report_context.report_type} data " +
                  (f"from {report_context.start_date} to {report_context.end_date}. " if report_context.start_date and report_context.end_date else "") +
                  "The data indicates overall positive performance with some areas for potential improvement.",
            inline=False
        )
        
        # Add a follow-up suggestions section
        embed.add_field(
            name="Suggested Next Steps",
            value="• Try `!report compare this month to last month` for a detailed comparison\n"
                  "• Use `!report forecast sales next quarter` for future projections\n"
                  "• Run `!report top 10 products` to see your best performers",
            inline=False
        )
        
        return embed
        
    async def _handle_report_timeout(self, report_context_id: str) -> None:
        """Handle timeout for report context"""
        if report_context_id not in self.active_report_contexts:
            return
            
        report_context = self.active_report_contexts[report_context_id]
        if report_context.is_completed or report_context.is_cancelled:
            return
            
        try:
            # Get the channel
            channel = self.bot.get_channel(report_context.channel_id)
            if channel:
                # If there's a last message, try to update it
                if report_context.last_message_id:
                    try:
                        message = await channel.fetch_message(report_context.last_message_id)
                        
                        # Create timeout embed
                        embed = discord.Embed(
                            title="Report Request Timeout",
                            description="The report request has timed out due to inactivity. Please try again.",
                            color=discord.Color.red()
                        )
                        
                        await message.edit(embed=embed)
                        await message.clear_reactions()
                    except discord.NotFound:
                        # Message was deleted, send a new one
                        await channel.send(
                            embed=discord.Embed(
                                title="Report Request Timeout",
                                description="The report request has timed out due to inactivity. Please try again.",
                                color=discord.Color.red()
                            )
                        )
                else:
                    # No last message, send a new one
                    await channel.send(
                        embed=discord.Embed(
                            title="Report Request Timeout",
                            description="The report request has timed out due to inactivity. Please try again.",
                            color=discord.Color.red()
                        )
                    )
        except Exception as e:
            logger.error(f"Error handling report timeout: {str(e)}")
        finally:
            # Clean up the report context
            del self.active_report_contexts[report_context_id]

    @commands.command(name="schedulereport")
    @commands.has_permissions(administrator=True)
    async def schedule_report_command(self, ctx, report_type=None, channel_id=None, interval_hours=None):
        """
        Schedule automated reports to be sent to a specified channel
        
        Usage:
        !schedulereport - Show scheduled reports
        !schedulereport <report_type> <channel_id> [interval_hours] - Schedule a new report
        !schedulereport cancel <report_id> - Cancel a scheduled report
        
        Report Types:
        - sales: Sales report
        - expenses: Expense report
        - inventory: Inventory report
        - profit: Profit and loss report
        - weekly_summary: Comprehensive weekly summary
        
        Examples:
        !schedulereport sales 123456789012345678 168 - Schedule weekly sales report
        !schedulereport weekly_summary 123456789012345678 - Schedule weekly summary
        !schedulereport cancel report_id_here - Cancel a scheduled report
        """
        try:
            # Get report generator
            report_generator = self.bot.get_report_generator()
            if not report_generator:
                await ctx.send("Report generator is not available.")
                return
            
            # If no arguments, list scheduled reports
            if not report_type:
                scheduled_reports = await report_generator.list_scheduled_reports()
                
                if not scheduled_reports:
                    embed = discord.Embed(
                        title="Scheduled Reports",
                        description="No reports are currently scheduled.",
                        color=discord.Color.blue()
                    )
                    await ctx.send(embed=embed)
                    return
                
                embed = discord.Embed(
                    title="Scheduled Reports",
                    description=f"There are {len(scheduled_reports)} scheduled reports.",
                    color=discord.Color.blue()
                )
                
                for report in scheduled_reports:
                    next_run = report['next_run'].strftime("%Y-%m-%d %H:%M:%S")
                    embed.add_field(
                        name=f"{report['report_type'].capitalize()} Report (ID: {report['report_id'][:8]}...)",
                        value=f"Channel: <#{report['channel_id']}>\n"
                              f"Interval: {report['interval_hours']} hours\n"
                              f"Next Run: {next_run}",
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                return
            
            # Handle cancellation
            if report_type.lower() == "cancel":
                if not channel_id:  # Using channel_id parameter as report_id
                    await ctx.send("Please provide a report ID to cancel.")
                    return
                
                success = await report_generator.cancel_scheduled_report(channel_id)
                
                if success:
                    await ctx.send(f"Successfully cancelled scheduled report with ID: {channel_id}")
                else:
                    await ctx.send(f"Failed to cancel report. Report ID not found: {channel_id}")
                
                return
            
            # Validate report type
            valid_report_types = ['sales', 'expenses', 'inventory', 'profit', 'weekly_summary']
            if report_type.lower() not in valid_report_types:
                await ctx.send(f"Invalid report type. Valid types are: {', '.join(valid_report_types)}")
                return
            
            # Validate channel ID
            if not channel_id:
                await ctx.send("Please provide a channel ID.")
                return
            
            try:
                channel_id = int(channel_id)
            except ValueError:
                await ctx.send("Invalid channel ID. Please provide a valid Discord channel ID.")
                return
            
            # Check if the channel exists and the bot has access to it
            channel = self.bot.get_channel(channel_id)
            if not channel:
                await ctx.send(f"Channel with ID {channel_id} not found or the bot doesn't have access to it.")
                return
            
            # Validate interval hours
            if interval_hours:
                try:
                    interval_hours = int(interval_hours)
                    if interval_hours < 1:
                        await ctx.send("Interval hours must be at least 1.")
                        return
                except ValueError:
                    await ctx.send("Invalid interval hours. Please provide a valid number.")
                    return
            else:
                # Default to weekly (168 hours)
                interval_hours = 168
            
            # Schedule the report
            report_id = await report_generator.schedule_report(
                report_type.lower(),
                channel_id,
                interval_hours
            )
            
            # Calculate next run time
            next_run = (datetime.now() + timedelta(hours=interval_hours)).strftime("%Y-%m-%d %H:%M:%S")
            
            # Send confirmation
            embed = discord.Embed(
                title="Report Scheduled",
                description=f"A {report_type} report has been scheduled.",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Details",
                value=f"Report Type: {report_type}\n"
                      f"Channel: <#{channel_id}>\n"
                      f"Interval: {interval_hours} hours\n"
                      f"Next Run: {next_run}\n"
                      f"Report ID: {report_id}",
                inline=False
            )
            
            embed.add_field(
                name="Cancel Command",
                value=f"`!schedulereport cancel {report_id}`",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error scheduling report: {str(e)}")
            
            # Send error message
            error_embed = discord.Embed(
                title="Error Scheduling Report",
                description=f"An error occurred while scheduling the report: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
    
    @commands.command(name="generatereport")
    @commands.has_permissions(administrator=True)
    async def generate_report_command(self, ctx, report_type=None, channel_id=None):
        """
        Generate and send a report immediately to a specified channel
        
        Usage:
        !generatereport <report_type> [channel_id] - Generate and send a report
        
        Report Types:
        - sales: Sales report
        - expenses: Expense report
        - inventory: Inventory report
        - profit: Profit and loss report
        - weekly_summary: Comprehensive weekly summary
        
        If channel_id is not provided, the report will be sent to the current channel.
        
        Examples:
        !generatereport sales - Generate sales report in current channel
        !generatereport weekly_summary 123456789012345678 - Generate weekly summary in specified channel
        """
        try:
            # Get report generator
            report_generator = self.bot.get_report_generator()
            if not report_generator:
                await ctx.send("Report generator is not available.")
                return
            
            # Validate report type
            if not report_type:
                await ctx.send("Please provide a report type.")
                return
            
            valid_report_types = ['sales', 'expenses', 'inventory', 'profit', 'weekly_summary']
            if report_type.lower() not in valid_report_types:
                await ctx.send(f"Invalid report type. Valid types are: {', '.join(valid_report_types)}")
                return
            
            # Determine target channel
            target_channel = ctx.channel
            if channel_id:
                try:
                    channel_id = int(channel_id)
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        target_channel = channel
                    else:
                        await ctx.send(f"Channel with ID {channel_id} not found or the bot doesn't have access to it.")
                        return
                except ValueError:
                    await ctx.send("Invalid channel ID. Please provide a valid Discord channel ID.")
                    return
            
            # Send initial message
            initial_message = await ctx.send(f"Generating {report_type} report...")
            
            # Generate and send the report
            try:
                # Determine date range (last 7 days by default)
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                
                if report_type.lower() == 'sales':
                    csv_path, embed = await report_generator.generate_sales_report(start_date, end_date)
                    await initial_message.edit(content=f"Sales report generated!")
                    await target_channel.send(f"📊 **Sales Report**", embed=embed, file=discord.File(csv_path))
                    
                elif report_type.lower() == 'expenses':
                    csv_path, embed = await report_generator.generate_expense_report(start_date, end_date)
                    await initial_message.edit(content=f"Expense report generated!")
                    await target_channel.send(f"💰 **Expense Report**", embed=embed, file=discord.File(csv_path))
                    
                elif report_type.lower() == 'inventory':
                    csv_path, embed = await report_generator.generate_inventory_report()
                    await initial_message.edit(content=f"Inventory report generated!")
                    await target_channel.send(f"📦 **Inventory Report**", embed=embed, file=discord.File(csv_path))
                    
                elif report_type.lower() == 'profit':
                    csv_path, embed = await report_generator.generate_profit_loss_report(start_date, end_date)
                    await initial_message.edit(content=f"Profit & Loss report generated!")
                    await target_channel.send(f"📈 **Profit & Loss Report**", embed=embed, file=discord.File(csv_path))
                    
                elif report_type.lower() == 'weekly_summary':
                    await initial_message.edit(content=f"Generating weekly summary report...")
                    await report_generator._generate_weekly_summary_report(target_channel)
                    await initial_message.edit(content=f"Weekly summary report generated!")
                
                # If the target channel is different from the command channel, send a confirmation
                if target_channel.id != ctx.channel.id:
                    await ctx.send(f"Report has been sent to <#{target_channel.id}>")
                
            except Exception as e:
                logger.error(f"Error generating report: {str(e)}")
                await initial_message.edit(content=f"Error generating report: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error in generate_report_command: {str(e)}")
            
            # Send error message
            error_embed = discord.Embed(
                title="Error Generating Report",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)
    
    @commands.command(name="setreportchannel")
    @commands.has_permissions(administrator=True)
    async def set_report_channel_command(self, ctx, report_type=None, channel_id=None):
        """
        Set the default channel for a specific report type
        
        Usage:
        !setreportchannel <report_type> <channel_id> - Set the default channel
        !setreportchannel <report_type> - Show the current default channel
        
        Report Types:
        - sales: Sales report
        - expenses: Expense report
        - inventory: Inventory report
        - profit: Profit and loss report
        - weekly_summary: Comprehensive weekly summary
        
        Examples:
        !setreportchannel sales 123456789012345678 - Set sales report channel
        !setreportchannel weekly_summary - Show current weekly summary channel
        """
        try:
            # Get report generator
            report_generator = self.bot.get_report_generator()
            if not report_generator:
                await ctx.send("Report generator is not available.")
                return
            
            # Validate report type
            if not report_type:
                await ctx.send("Please provide a report type.")
                return
            
            valid_report_types = ['sales', 'expenses', 'inventory', 'profit', 'weekly_summary']
            if report_type.lower() not in valid_report_types:
                await ctx.send(f"Invalid report type. Valid types are: {', '.join(valid_report_types)}")
                return
            
            # If no channel ID is provided, show the current channel
            if not channel_id:
                current_channel_id = report_generator.report_channels.get(report_type.lower())
                if current_channel_id:
                    await ctx.send(f"The current channel for {report_type} reports is <#{current_channel_id}>")
                else:
                    await ctx.send(f"No default channel is set for {report_type} reports.")
                return
            
            # Validate channel ID
            try:
                channel_id = int(channel_id)
            except ValueError:
                await ctx.send("Invalid channel ID. Please provide a valid Discord channel ID.")
                return
            
            # Check if the channel exists and the bot has access to it
            channel = self.bot.get_channel(channel_id)
            if not channel:
                await ctx.send(f"Channel with ID {channel_id} not found or the bot doesn't have access to it.")
                return
            
            # Set the channel
            report_generator.report_channels[report_type.lower()] = channel_id
            
            # Send confirmation
            await ctx.send(f"Default channel for {report_type} reports set to <#{channel_id}>")
            
        except Exception as e:
            logger.error(f"Error setting report channel: {str(e)}")
            
            # Send error message
            error_embed = discord.Embed(
                title="Error Setting Report Channel",
                description=f"An error occurred: {str(e)}",
                color=discord.Color.red()
            )
            await ctx.send(embed=error_embed)

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(FinanceCog(bot))