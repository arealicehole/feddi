"""
Inventory management commands for the AccountME Discord Bot
Implementation for Phase 3
"""

import discord
from discord.ext import commands
import logging
from datetime import datetime, timedelta
import csv
import io
import os
import asyncio
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger("accountme_bot.inventory_cog")

# Valid product categories
PRODUCT_CATEGORIES = ['blank', 'dtf', 'other']

# Conversation state for multi-step commands
class ProductConversation:
    def __init__(self, ctx, category=None):
        self.ctx = ctx
        self.user_id = ctx.author.id
        self.channel_id = ctx.channel.id
        self.category = category
        self.data = {}
        self.current_step = None
        self.steps = []
        self.timeout = 300  # 5 minutes
        self.last_activity = datetime.now()
        self.message = None
    
    def update_activity(self):
        """Update the last activity timestamp"""
        self.last_activity = datetime.now()
    
    def is_expired(self):
        """Check if the conversation has expired"""
        elapsed = (datetime.now() - self.last_activity).total_seconds()
        return elapsed > self.timeout
    
    def is_complete(self):
        """Check if all required fields are filled"""
        return all(field in self.data for field in self.steps)

class InventoryCog(commands.Cog, name="Inventory"):
    """Inventory management commands for product and inventory tracking"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_conversations = {}
        self.bot.loop.create_task(self._cleanup_conversations())
    
    async def _cleanup_conversations(self):
        """Periodically clean up expired conversations"""
        while not self.bot.is_closed():
            # Find expired conversations
            expired = [user_id for user_id, conv in self.active_conversations.items()
                      if conv.is_expired()]
            
            # Remove expired conversations
            for user_id in expired:
                logger.info(f"Removing expired product conversation for user {user_id}")
                if user_id in self.active_conversations:
                    del self.active_conversations[user_id]
            
            await asyncio.sleep(60)  # Check every minute
    
    @commands.command(name="inventory", aliases=["inv", "stock"])
    async def inventory_command(self, ctx, sku=None):
        """
        View inventory information
        
        Usage:
        !inventory - Show inventory summary
        !inventory <sku> - Show details for a specific product
        
        Aliases: !inv, !stock
        """
        db = self.bot.db_manager
        
        if sku:
            # Look up specific product
            product = db.get_product_by_sku(sku)
            
            if product:
                embed = discord.Embed(
                    title=f"Product: {product['name']}",
                    description=f"SKU: {product['sku']}",
                    color=discord.Color.blue()
                )
                
                # Add product details
                embed.add_field(name="Category", value=product['category'].capitalize(), inline=True)
                if product['subcategory']:
                    embed.add_field(name="Subcategory", value=product['subcategory'].replace('_', ' ').capitalize(), inline=True)
                
                embed.add_field(name="Quantity", value=str(product['quantity']), inline=True)
                
                if product['cost_price']:
                    embed.add_field(name="Cost Price", value=f"${product['cost_price']:.2f}", inline=True)
                
                if product['selling_price']:
                    embed.add_field(name="Selling Price", value=f"${product['selling_price']:.2f}", inline=True)
                
                # Add category-specific details
                if product['category'] == 'blank':
                    if product['manufacturer']:
                        embed.add_field(name="Manufacturer", value=product['manufacturer'], inline=True)
                    if product['style']:
                        embed.add_field(name="Style", value=product['style'], inline=True)
                    if product['color']:
                        embed.add_field(name="Color", value=product['color'], inline=True)
                    if product['size']:
                        embed.add_field(name="Size", value=product['size'], inline=True)
                
                elif product['category'] == 'dtf':
                    if product['size']:
                        embed.add_field(name="Size", value=product['size'], inline=True)
                    if product['vendor']:
                        embed.add_field(name="Vendor", value=product['vendor'], inline=True)
                
                elif product['category'] == 'other':
                    if product['vendor']:
                        embed.add_field(name="Vendor", value=product['vendor'], inline=True)
                
                # Add timestamps
                embed.add_field(name="Created", value=product['created_at'].split('T')[0], inline=True)
                embed.add_field(name="Last Updated", value=product['updated_at'].split('T')[0], inline=True)
                
            else:
                embed = discord.Embed(
                    title="Product Not Found",
                    description=f"No product found with SKU: `{sku}`",
                    color=discord.Color.red()
                )
        else:
            # Show inventory summary
            products = db.list_products()
            
            embed = discord.Embed(
                title="Inventory Summary",
                description=f"Total Products: {len(products)}",
                color=discord.Color.blue()
            )
            
            # Group by category
            categories = {}
            for product in products:
                category = product['category']
                if category not in categories:
                    categories[category] = []
                categories[category].append(product)
            
            # Add category summaries
            for category, category_products in categories.items():
                total_quantity = sum(p['quantity'] for p in category_products)
                total_value = sum(p['quantity'] * (p['cost_price'] or 0) for p in category_products)
                
                embed.add_field(
                    name=f"{category.capitalize()} Items",
                    value=f"Count: {len(category_products)}\n"
                          f"Quantity: {total_quantity}\n"
                          f"Value: ${total_value:.2f}",
                    inline=True
                )
            
            # Add low stock warning
            low_stock = [p for p in products if p['quantity'] <= 5 and p['quantity'] > 0]
            out_of_stock = [p for p in products if p['quantity'] <= 0]
            
            if low_stock:
                low_stock_text = "\n".join([f"• {p['name']} ({p['sku']}): {p['quantity']}" for p in low_stock[:5]])
                if len(low_stock) > 5:
                    low_stock_text += f"\n... and {len(low_stock) - 5} more"
                
                embed.add_field(
                    name=f"Low Stock Items ({len(low_stock)})",
                    value=low_stock_text,
                    inline=False
                )
            
            if out_of_stock:
                embed.add_field(
                    name=f"Out of Stock Items ({len(out_of_stock)})",
                    value=f"Use `!inventory outofstock` to see details",
                    inline=False
                )
        
        embed.set_footer(text="AccountME Bot | Inventory Management")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="addproduct", aliases=["newproduct", "additem"])
    async def add_product_command(self, ctx, category=None):
        """
        Add a new product to inventory
        
        Usage:
        !addproduct - Start guided product creation
        !addproduct <category> - Start product creation for specific category (blank, dtf, other)
        
        Aliases: !newproduct, !additem
        """
        # Check if user already has an active conversation
        if ctx.author.id in self.active_conversations:
            await ctx.send("You already have an active product creation in progress. "
                          "Please finish or cancel it before starting a new one.")
            return
        
        # Validate category if provided
        if category and category.lower() not in PRODUCT_CATEGORIES:
            await ctx.send(f"Invalid category. Please use one of: {', '.join(PRODUCT_CATEGORIES)}")
            return
        
        # Start with category selection if not provided
        if not category:
            embed = discord.Embed(
                title="Add New Product",
                description="Please select a product category:",
                color=discord.Color.blue()
            )
            
            for cat in PRODUCT_CATEGORIES:
                if cat == 'blank':
                    description = "Blank clothing items (t-shirts, hoodies, etc.)"
                elif cat == 'dtf':
                    description = "DTF prints (transfers, designs)"
                else:
                    description = "Other products (accessories, equipment, etc.)"
                
                embed.add_field(
                    name=cat.capitalize(),
                    value=description,
                    inline=False
                )
            
            embed.set_footer(text="Type the category name to continue, or 'cancel' to exit")
            
            # Create conversation state
            conversation = ProductConversation(ctx)
            self.active_conversations[ctx.author.id] = conversation
            conversation.current_step = "category"
            conversation.message = await ctx.send(embed=embed)
            
        else:
            # Start with the provided category
            await self._start_product_creation(ctx, category.lower())
    
    async def _start_product_creation(self, ctx, category):
        """Start the product creation process for a specific category"""
        # Create conversation with the selected category
        conversation = ProductConversation(ctx, category)
        self.active_conversations[ctx.author.id] = conversation
        
        # Set up the steps based on category
        if category == 'blank':
            conversation.steps = [
                "name", "manufacturer", "style", "color", "size",
                "sku", "cost_price", "selling_price", "quantity"
            ]
        elif category == 'dtf':
            conversation.steps = [
                "name", "size", "vendor",
                "sku", "cost_price", "selling_price", "quantity"
            ]
        else:  # other
            conversation.steps = [
                "name", "vendor", "sku",
                "cost_price", "selling_price", "quantity"
            ]
        
        # Start with the first step
        conversation.current_step = conversation.steps[0]
        conversation.data['category'] = category
        
        # Send the first prompt
        await self._send_step_prompt(conversation)
    
    async def _send_step_prompt(self, conversation):
        """Send a prompt for the current step in the conversation"""
        step = conversation.current_step
        category = conversation.data['category']
        
        embed = discord.Embed(
            title=f"New {category.capitalize()} Product",
            description=f"Step {conversation.steps.index(step) + 1} of {len(conversation.steps)}",
            color=discord.Color.blue()
        )
        
        # Add prompt based on the current step
        if step == "name":
            embed.add_field(
                name="Product Name",
                value="Please enter the name of the product.",
                inline=False
            )
        
        elif step == "manufacturer":
            embed.add_field(
                name="Manufacturer",
                value="Please enter the manufacturer name.",
                inline=False
            )
        
        elif step == "vendor":
            embed.add_field(
                name="Vendor",
                value="Please enter the vendor or supplier name.",
                inline=False
            )
        
        elif step == "style":
            embed.add_field(
                name="Style",
                value="Please enter the manufacturer's style code or product ID.",
                inline=False
            )
        
        elif step == "color":
            embed.add_field(
                name="Color",
                value="Please enter the color of the item.",
                inline=False
            )
        
        elif step == "size":
            if category == 'blank':
                embed.add_field(
                    name="Size",
                    value="Please enter the size (XS, S, M, L, XL, etc.).",
                    inline=False
                )
            elif category == 'dtf':
                embed.add_field(
                    name="Size",
                    value="Please enter the dimensions of the print (e.g., '10x12 inches').",
                    inline=False
                )
        
        elif step == "sku":
            embed.add_field(
                name="SKU",
                value="Please enter a unique SKU (Stock Keeping Unit) for this product.",
                inline=False
            )
        
        elif step == "cost_price":
            embed.add_field(
                name="Cost Price",
                value="Please enter the cost price (what you paid for it).\n"
                      "Enter a number (e.g., 10.99) or 'skip' to leave blank.",
                inline=False
            )
        
        elif step == "selling_price":
            embed.add_field(
                name="Selling Price",
                value="Please enter the selling price.\n"
                      "Enter a number (e.g., 19.99) or 'skip' to leave blank.",
                inline=False
            )
        
        elif step == "quantity":
            embed.add_field(
                name="Initial Quantity",
                value="Please enter the initial quantity in stock.\n"
                      "Enter a number or 'skip' to default to 0.",
                inline=False
            )
        
        # Add current data summary
        if conversation.data:
            summary = []
            for key, value in conversation.data.items():
                if key != 'category':
                    summary.append(f"• {key.replace('_', ' ').capitalize()}: {value}")
            
            if summary:
                embed.add_field(
                    name="Current Information",
                    value="\n".join(summary),
                    inline=False
                )
        
        embed.set_footer(text="Type your response, 'back' to go back, or 'cancel' to exit")
        
        # Send or update the message
        if conversation.message:
            await conversation.message.edit(embed=embed)
        else:
            conversation.message = await conversation.ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle responses for active conversations"""
        # Ignore bot messages
        if message.author.bot:
            return
        
        # Check if user has an active conversation
        if message.author.id not in self.active_conversations:
            return
        
        conversation = self.active_conversations[message.author.id]
        
        # Make sure it's in the same channel
        if message.channel.id != conversation.channel_id:
            return
        
        # Update activity timestamp
        conversation.update_activity()
        
        # Get the response
        response = message.content.strip()
        
        # Handle cancellation
        if response.lower() == 'cancel':
            await message.channel.send("Operation cancelled.")
            del self.active_conversations[message.author.id]
            return
        
        # Check if this is an update operation (has product_id)
        is_update = 'product_id' in conversation.data
        
        # Handle category selection (only for new products)
        if conversation.current_step == "category":
            if response.lower() in PRODUCT_CATEGORIES:
                await self._start_product_creation(conversation.ctx, response.lower())
            else:
                await message.channel.send(f"Invalid category. Please select one of: {', '.join(PRODUCT_CATEGORIES)}")
            return
        
        # Handle update-specific commands
        if is_update:
            if response.lower() == 'skip':
                # Skip this field (keep current value)
                await self._advance_update_conversation(conversation, message.channel)
                return
            
            if response.lower() == 'clear':
                # Clear the field value
                conversation.data[conversation.current_step] = None
                await self._advance_update_conversation(conversation, message.channel)
                return
            
            if response.lower() == 'back':
                # Go back to previous step
                current_index = conversation.steps.index(conversation.current_step)
                if current_index > 0:
                    conversation.current_step = conversation.steps[current_index - 1]
                    await self._send_update_prompt(conversation)
                else:
                    await message.channel.send("You're already at the first field.")
                return
            
            # Validate and store the response
            valid, error_message = self._validate_step_response(
                conversation.current_step,
                response,
                is_update=True,
                current_sku=conversation.data.get('sku')
            )
            
            if valid:
                # Store the validated response
                if conversation.current_step in ['cost_price', 'selling_price']:
                    conversation.data[conversation.current_step] = float(response)
                elif conversation.current_step == 'quantity':
                    conversation.data[conversation.current_step] = int(response)
                else:
                    conversation.data[conversation.current_step] = response
                
                # Move to next step or finish
                await self._advance_update_conversation(conversation, message.channel)
            else:
                await message.channel.send(error_message)
            
            return
        
        # Handle 'back' command for product creation
        if response.lower() == 'back':
            current_index = conversation.steps.index(conversation.current_step)
            if current_index > 0:
                # Go back to previous step
                conversation.current_step = conversation.steps[current_index - 1]
                # Remove the data for the current step if it exists
                if conversation.current_step in conversation.data:
                    del conversation.data[conversation.current_step]
                await self._send_step_prompt(conversation)
            else:
                await message.channel.send("You're already at the first step.")
            return
        
        # Handle verification-specific commands
        if conversation.current_step == "count":
            if response.lower() == 'skip':
                # Skip this product
                if 'verification_type' in conversation.data and conversation.data['verification_type'] in ['category', 'all']:
                    # Move to next product
                    conversation.data['current_index'] += 1
                    await self._show_next_product_for_verification(conversation)
                else:
                    # Single product verification - just cancel
                    await message.channel.send("Verification cancelled.")
                    del self.active_conversations[message.author.id]
                return
            
            if response.lower() == 'same':
                # Physical count matches system
                if 'verification_type' in conversation.data and conversation.data['verification_type'] in ['category', 'all']:
                    # Get current product
                    product = conversation.data['current_product']
                    
                    # Add to verified products
                    conversation.data.setdefault('verified_products', []).append({
                        'product_id': product['product_id'],
                        'name': product['name'],
                        'sku': product['sku'],
                        'system_quantity': product['quantity'],
                        'actual_quantity': product['quantity'],
                        'difference': 0
                    })
                    
                    # Move to next product
                    conversation.data['current_index'] += 1
                    await self._show_next_product_for_verification(conversation)
                else:
                    # Single product verification
                    await message.channel.send("Verification complete. System quantity matches physical count.")
                    del self.active_conversations[message.author.id]
                return
            
            if response.lower() == 'stop':
                # Stop verification and show results
                if 'verification_type' in conversation.data and conversation.data['verification_type'] in ['category', 'all']:
                    await self._show_verification_summary(conversation)
                else:
                    # Single product verification - just cancel
                    await message.channel.send("Verification cancelled.")
                    del self.active_conversations[message.author.id]
                return
            
            # Try to parse count as integer
            try:
                count = int(response)
                
                if count < 0:
                    await message.channel.send("Count cannot be negative. Please enter a valid count.")
                    return
                
                # Handle based on verification type
                if 'verification_type' in conversation.data and conversation.data['verification_type'] in ['category', 'all']:
                    # Get current product
                    product = conversation.data['current_product']
                    system_quantity = product['quantity']
                    
                    # Calculate difference
                    difference = count - system_quantity
                    
                    # Add to appropriate list
                    if difference != 0:
                        conversation.data.setdefault('discrepancies', []).append({
                            'product_id': product['product_id'],
                            'name': product['name'],
                            'sku': product['sku'],
                            'system_quantity': system_quantity,
                            'actual_quantity': count,
                            'difference': difference
                        })
                    else:
                        conversation.data.setdefault('verified_products', []).append({
                            'product_id': product['product_id'],
                            'name': product['name'],
                            'sku': product['sku'],
                            'system_quantity': system_quantity,
                            'actual_quantity': count,
                            'difference': 0
                        })
                    
                    # Move to next product
                    conversation.data['current_index'] += 1
                    await self._show_next_product_for_verification(conversation)
                else:
                    # Single product verification
                    product_id = conversation.data['product_id']
                    system_quantity = conversation.data['system_quantity']
                    
                    # Calculate difference
                    difference = count - system_quantity
                    
                    if difference == 0:
                        await message.channel.send("Verification complete. System quantity matches physical count.")
                        del self.active_conversations[message.author.id]
                        return
                    
                    # Show discrepancy and ask for reconciliation
                    embed = discord.Embed(
                        title="Inventory Discrepancy",
                        description=f"Product: {conversation.data['name']} ({conversation.data['sku']})",
                        color=discord.Color.gold()
                    )
                    
                    embed.add_field(
                        name="System Quantity",
                        value=str(system_quantity),
                        inline=True
                    )
                    
                    embed.add_field(
                        name="Physical Count",
                        value=str(count),
                        inline=True
                    )
                    
                    embed.add_field(
                        name="Difference",
                        value=f"{'+' if difference > 0 else ''}{difference}",
                        inline=True
                    )
                    
                    embed.add_field(
                        name="Reconcile Inventory",
                        value="Would you like to update the system to match the physical count?",
                        inline=False
                    )
                    
                    # Store count in conversation
                    conversation.data['actual_quantity'] = count
                    conversation.data['difference'] = difference
                    conversation.current_step = "reconcile_single"
                    
                    # Update message
                    await conversation.message.edit(embed=embed)
                    
                    # Add reactions
                    await conversation.message.add_reaction("✅")  # Yes
                    await conversation.message.add_reaction("❌")  # No
                
                return
            except ValueError:
                await message.channel.send("Please enter a valid number for the count.")
                return
        
        # Handle category entry for verification
        if conversation.current_step == "category_entry":
            category = response.lower()
            
            if category not in PRODUCT_CATEGORIES:
                await message.channel.send(f"Invalid category. Please select one of: {', '.join(PRODUCT_CATEGORIES)}")
                return
            
            # Get products in this category
            products = self.bot.db_manager.list_products(category)
            
            if not products:
                await message.channel.send(f"No products found in category: {category}")
                del self.active_conversations[message.author.id]
                return
            
            # Store products in conversation
            conversation.data['products'] = products
            conversation.data['current_index'] = 0
            conversation.data['verified_products'] = []
            conversation.data['discrepancies'] = []
            conversation.data['category'] = category
            
            # Start with the first product
            await self._show_next_product_for_verification(conversation)
            return
        
        # Handle SKU entry for verification
        if conversation.current_step == "sku_entry":
            sku = response.strip()
            
            # Get product by SKU
            product = self.bot.db_manager.get_product_by_sku(sku)
            
            if not product:
                await message.channel.send(f"No product found with SKU: {sku}")
                return
            
            # Start verification for this product
            await self._start_single_product_verification(conversation.ctx, product)
            return
        
        # Handle 'skip' for optional fields in product creation
        if response.lower() == 'skip':
            if conversation.current_step in ['cost_price', 'selling_price', 'quantity',
                                           'manufacturer', 'vendor', 'style', 'color', 'size']:
                # These fields can be skipped
                if conversation.current_step in ['cost_price', 'selling_price']:
                    conversation.data[conversation.current_step] = None
                elif conversation.current_step == 'quantity':
                    conversation.data[conversation.current_step] = 0
                else:
                    conversation.data[conversation.current_step] = None
                
                # Move to next step or finish
                await self._advance_conversation(conversation, message.channel)
                return
            else:
                await message.channel.send(f"The {conversation.current_step} field cannot be skipped.")
                return
        
        # Validate and store the response for product creation
        valid, error_message = self._validate_step_response(conversation.current_step, response)
        
        if valid:
            # Store the validated response
            if conversation.current_step in ['cost_price', 'selling_price']:
                conversation.data[conversation.current_step] = float(response)
            elif conversation.current_step == 'quantity':
                conversation.data[conversation.current_step] = int(response)
            else:
                conversation.data[conversation.current_step] = response
            
            # Move to next step or finish
            await self._advance_conversation(conversation, message.channel)
        else:
            await message.channel.send(error_message)
    
    def _validate_step_response(self, step, response):
        """Validate a response for a specific step"""
        if step == "name":
            if len(response) < 2:
                return False, "Product name must be at least 2 characters long."
            return True, None
        
        elif step == "sku":
            if len(response) < 2:
                return False, "SKU must be at least 2 characters long."
            
            # Check if SKU already exists
            product = self.bot.db_manager.get_product_by_sku(response)
            if product:
                return False, f"A product with SKU '{response}' already exists."
            
            return True, None
        
        elif step in ["cost_price", "selling_price"]:
            try:
                value = float(response)
                if value < 0:
                    return False, f"{step.replace('_', ' ').capitalize()} cannot be negative."
                return True, None
            except ValueError:
                return False, f"{step.replace('_', ' ').capitalize()} must be a valid number."
        
        elif step == "quantity":
            try:
                value = int(response)
                if value < 0:
                    return False, "Quantity cannot be negative."
                return True, None
            except ValueError:
                return False, "Quantity must be a valid integer."
        
        # All other fields are considered valid
        return True, None
    
    async def _advance_conversation(self, conversation, channel):
        """Advance to the next step or finish the conversation"""
        current_index = conversation.steps.index(conversation.current_step)
        
        if current_index < len(conversation.steps) - 1:
            # Move to next step
            conversation.current_step = conversation.steps[current_index + 1]
            await self._send_step_prompt(conversation)
        else:
            # All steps completed, create the product
            await self._finish_product_creation(conversation, channel)
    
    async def _finish_product_creation(self, conversation, channel):
        """Finish the product creation process"""
        # Create confirmation embed
        embed = discord.Embed(
            title="Confirm Product Creation",
            description=f"Please review the product information below:",
            color=discord.Color.green()
        )
        
        # Add all product data
        for key, value in conversation.data.items():
            if value is not None:
                if key in ['cost_price', 'selling_price'] and value is not None:
                    value = f"${value:.2f}"
                embed.add_field(
                    name=key.replace('_', ' ').capitalize(),
                    value=str(value),
                    inline=True
                )
        
        embed.set_footer(text="Type 'confirm' to create the product, or 'cancel' to exit")
        
        # Update or send the message
        if conversation.message:
            await conversation.message.edit(embed=embed)
        else:
            conversation.message = await channel.send(embed=embed)
        
        # Wait for confirmation
        try:
            response_message = await self.bot.wait_for(
                'message',
                check=lambda m: m.author.id == conversation.user_id and
                               m.channel.id == conversation.channel_id and
                               m.content.lower() in ['confirm', 'cancel'],
                timeout=300
            )
            
            if response_message.content.lower() == 'confirm':
                # Add the product to the database
                product_id = self.bot.db_manager.add_product(conversation.data)
                
                # Log the action
                self.bot.db_manager.log_audit(
                    'create',
                    'product',
                    product_id,
                    str(conversation.user_id),
                    f"Created new {conversation.data['category']} product: {conversation.data['name']}"
                )
                
                # Send success message
                success_embed = discord.Embed(
                    title="Product Created",
                    description=f"Successfully created product: {conversation.data['name']}",
                    color=discord.Color.green()
                )
                success_embed.add_field(
                    name="SKU",
                    value=conversation.data['sku'],
                    inline=True
                )
                success_embed.add_field(
                    name="Category",
                    value=conversation.data['category'].capitalize(),
                    inline=True
                )
                success_embed.add_field(
                    name="ID",
                    value=str(product_id),
                    inline=True
                )
                
                await channel.send(embed=success_embed)
            else:
                await channel.send("Product creation cancelled.")
        
        except asyncio.TimeoutError:
            await channel.send("Product creation timed out due to inactivity.")
        
        # Clean up the conversation
        if conversation.user_id in self.active_conversations:
            del self.active_conversations[conversation.user_id]
    
    @commands.command(name="adjustinventory", aliases=["adjust", "updatestock"])
    async def adjust_inventory_command(self, ctx, sku=None, quantity=None, *, reason=None):
        """
        Adjust inventory quantities
        
        Usage:
        !adjustinventory <sku> <quantity_change> [reason]
        
        Examples:
        !adjustinventory TS001 5 - Increase by 5
        !adjustinventory TS001 -3 Damaged in shipping - Decrease by 3 with reason
        
        Aliases: !adjust, !updatestock
        """
        if not sku or quantity is None:
            embed = discord.Embed(
                title="Adjust Inventory",
                description="Adjust product quantities in inventory",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Usage",
                value="!adjustinventory <sku> <quantity_change> [reason]",
                inline=False
            )
            
            embed.add_field(
                name="Examples",
                value="!adjustinventory TS001 5 - Increase by 5\n"
                      "!adjustinventory TS001 -3 Damaged in shipping - Decrease by 3 with reason",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        # Validate quantity
        try:
            quantity_change = int(quantity)
        except ValueError:
            await ctx.send("Quantity must be a valid integer (positive to add, negative to remove).")
            return
        
        # Get the product
        product = self.bot.db_manager.get_product_by_sku(sku)
        if not product:
            await ctx.send(f"No product found with SKU: {sku}")
            return
        
        # Adjust the quantity
        success = self.bot.db_manager.adjust_product_quantity(
            product['product_id'],
            quantity_change,
            str(ctx.author.id),
            reason
        )
        
        if success:
            # Get updated product
            updated_product = self.bot.db_manager.get_product(product['product_id'])
            
            embed = discord.Embed(
                title="Inventory Adjusted",
                description=f"Successfully adjusted inventory for {product['name']}",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="SKU",
                value=product['sku'],
                inline=True
            )
            
            embed.add_field(
                name="Previous Quantity",
                value=str(product['quantity']),
                inline=True
            )
            
            embed.add_field(
                name="New Quantity",
                value=str(updated_product['quantity']),
                inline=True
            )
            
            embed.add_field(
                name="Change",
                value=f"{'+' if quantity_change > 0 else ''}{quantity_change}",
                inline=True
            )
            
            if reason:
                embed.add_field(
                    name="Reason",
                    value=reason,
                    inline=False
                )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("Failed to adjust inventory. Please try again.")

    @commands.command(name="updateproduct", aliases=["editproduct", "modifyproduct"])
    async def update_product_command(self, ctx, sku=None):
        """
        Update an existing product
        
        Usage:
        !updateproduct <sku> - Start guided product update
        
        Aliases: !editproduct, !modifyproduct
        """
        if not sku:
            await ctx.send("Please provide a SKU to update. Usage: !updateproduct <sku>")
            return
        
        # Check if user already has an active conversation
        if ctx.author.id in self.active_conversations:
            await ctx.send("You already have an active product operation in progress. "
                          "Please finish or cancel it before starting a new one.")
            return
        
        # Get the product
        product = self.bot.db_manager.get_product_by_sku(sku)
        if not product:
            await ctx.send(f"No product found with SKU: {sku}")
            return
        
        # Create conversation for update
        conversation = ProductConversation(ctx, product['category'])
        self.active_conversations[ctx.author.id] = conversation
        
        # Pre-fill with existing data
        for key, value in product.items():
            if key not in ['product_id', 'created_at', 'updated_at']:
                conversation.data[key] = value
        
        # Set up the steps based on category
        if product['category'] == 'blank':
            conversation.steps = [
                "name", "manufacturer", "style", "color", "size",
                "cost_price", "selling_price"
            ]
        elif product['category'] == 'dtf':
            conversation.steps = [
                "name", "size", "vendor",
                "cost_price", "selling_price"
            ]
        else:  # other
            conversation.steps = [
                "name", "vendor",
                "cost_price", "selling_price"
            ]
        
        # Start with the first step
        conversation.current_step = conversation.steps[0]
        
        # Store product ID for update
        conversation.data['product_id'] = product['product_id']
        
        # Send initial embed
        embed = discord.Embed(
            title=f"Update Product: {product['name']}",
            description=f"SKU: {product['sku']} (Category: {product['category'].capitalize()})",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Instructions",
            value="You'll be guided through updating each field.\n"
                  "For each field, you can:\n"
                  "• Enter a new value to change it\n"
                  "• Type 'skip' to keep the current value\n"
                  "• Type 'clear' to remove the value\n"
                  "• Type 'cancel' to exit without saving",
            inline=False
        )
        
        embed.set_footer(text="Type 'start' to begin, or 'cancel' to exit")
        
        conversation.message = await ctx.send(embed=embed)
        
        # Wait for confirmation to start
        try:
            response_message = await self.bot.wait_for(
                'message',
                check=lambda m: m.author.id == conversation.user_id and
                               m.channel.id == conversation.channel_id and
                               m.content.lower() in ['start', 'cancel'],
                timeout=300
            )
            
            if response_message.content.lower() == 'start':
                # Send the first prompt
                await self._send_update_prompt(conversation)
            else:
                await ctx.send("Product update cancelled.")
                del self.active_conversations[ctx.author.id]
        
        except asyncio.TimeoutError:
            await ctx.send("Product update timed out due to inactivity.")
            if ctx.author.id in self.active_conversations:
                del self.active_conversations[ctx.author.id]
    
    async def _send_update_prompt(self, conversation):
        """Send a prompt for the current update step"""
        step = conversation.current_step
        category = conversation.data['category']
        current_value = conversation.data.get(step)
        
        embed = discord.Embed(
            title=f"Update {category.capitalize()} Product",
            description=f"Step {conversation.steps.index(step) + 1} of {len(conversation.steps)}",
            color=discord.Color.blue()
        )
        
        # Format current value for display
        display_value = current_value
        if step in ['cost_price', 'selling_price'] and current_value is not None:
            display_value = f"${current_value:.2f}"
        elif current_value is None:
            display_value = "Not set"
        
        # Add prompt based on the current step
        embed.add_field(
            name=f"Update {step.replace('_', ' ').capitalize()}",
            value=f"Current value: {display_value}\n\n"
                  f"Enter a new value, or:\n"
                  f"• 'skip' to keep current value\n"
                  f"• 'clear' to remove the value\n"
                  f"• 'back' to go to previous field\n"
                  f"• 'cancel' to exit without saving",
            inline=False
        )
        
        # Update the message
        await conversation.message.edit(embed=embed)
    
    async def _advance_update_conversation(self, conversation, channel):
        """Advance to the next step or finish the update conversation"""
        current_index = conversation.steps.index(conversation.current_step)
        
        if current_index < len(conversation.steps) - 1:
            # Move to next step
            conversation.current_step = conversation.steps[current_index + 1]
            await self._send_update_prompt(conversation)
        else:
            # All steps completed, update the product
            await self._finish_product_update(conversation, channel)
    
    async def _finish_product_update(self, conversation, channel):
        """Finish the product update process"""
        # Create confirmation embed
        embed = discord.Embed(
            title="Confirm Product Update",
            description=f"Please review the updated product information below:",
            color=discord.Color.green()
        )
        
        # Add all product data
        for key, value in conversation.data.items():
            if key not in ['product_id', 'category', 'sku']:
                if value is not None:
                    if key in ['cost_price', 'selling_price'] and value is not None:
                        value = f"${value:.2f}"
                    embed.add_field(
                        name=key.replace('_', ' ').capitalize(),
                        value=str(value),
                        inline=True
                    )
        
        # Always show category and SKU
        embed.add_field(
            name="Category",
            value=conversation.data['category'].capitalize(),
            inline=True
        )
        
        embed.add_field(
            name="SKU",
            value=conversation.data['sku'],
            inline=True
        )
        
        embed.set_footer(text="Type 'confirm' to update the product, or 'cancel' to exit")
        
        # Update the message
        await conversation.message.edit(embed=embed)
        
        # Wait for confirmation
        try:
            response_message = await self.bot.wait_for(
                'message',
                check=lambda m: m.author.id == conversation.user_id and
                               m.channel.id == conversation.channel_id and
                               m.content.lower() in ['confirm', 'cancel'],
                timeout=300
            )
            
            if response_message.content.lower() == 'confirm':
                # Extract product_id and remove it from data
                product_id = conversation.data.pop('product_id')
                
                # Update the product in the database
                success = self.bot.db_manager.update_product(product_id, conversation.data)
                
                if success:
                    # Log the action
                    self.bot.db_manager.log_audit(
                        'update',
                        'product',
                        product_id,
                        str(conversation.user_id),
                        f"Updated {conversation.data['category']} product: {conversation.data['name']}"
                    )
                    
                    # Send success message
                    success_embed = discord.Embed(
                        title="Product Updated",
                        description=f"Successfully updated product: {conversation.data['name']}",
                        color=discord.Color.green()
                    )
                    success_embed.add_field(
                        name="SKU",
                        value=conversation.data['sku'],
                        inline=True
                    )
                    success_embed.add_field(
                        name="Category",
                        value=conversation.data['category'].capitalize(),
                        inline=True
                    )
                    
                    await channel.send(embed=success_embed)
                else:
                    await channel.send("Failed to update product. Please try again.")
            else:
                await channel.send("Product update cancelled.")
        
        except asyncio.TimeoutError:
            await channel.send("Product update timed out due to inactivity.")
        
        # Clean up the conversation
        if conversation.user_id in self.active_conversations:
            del self.active_conversations[conversation.user_id]
    
    @commands.command(name="deleteproduct", aliases=["removeproduct", "delproduct"])
    async def delete_product_command(self, ctx, sku=None):
        """
        Delete a product from inventory
        
        Usage:
        !deleteproduct <sku> - Delete a product by SKU
        
        Aliases: !removeproduct, !delproduct
        """
        if not sku:
            await ctx.send("Please provide a SKU to delete. Usage: !deleteproduct <sku>")
            return
        
        # Get the product
        product = self.bot.db_manager.get_product_by_sku(sku)
        if not product:
            await ctx.send(f"No product found with SKU: {sku}")
            return
        
        # Create confirmation embed
        embed = discord.Embed(
            title="Confirm Product Deletion",
            description=f"Are you sure you want to delete this product?",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="Product",
            value=product['name'],
            inline=True
        )
        
        embed.add_field(
            name="SKU",
            value=product['sku'],
            inline=True
        )
        
        embed.add_field(
            name="Category",
            value=product['category'].capitalize(),
            inline=True
        )
        
        if product['quantity'] > 0:
            embed.add_field(
                name="Warning",
                value=f"This product has {product['quantity']} units in stock!",
                inline=False
            )
        
        embed.set_footer(text="Type 'confirm' to delete, or 'cancel' to exit")
        
        confirmation_message = await ctx.send(embed=embed)
        
        # Wait for confirmation
        try:
            response_message = await self.bot.wait_for(
                'message',
                check=lambda m: m.author.id == ctx.author.id and
                               m.channel.id == ctx.channel.id and
                               m.content.lower() in ['confirm', 'cancel'],
                timeout=300
            )
            
            if response_message.content.lower() == 'confirm':
                # Delete the product
                success = self.bot.db_manager.delete('products', 'product_id = ?', (product['product_id'],))
                
                if success:
                    # Log the action
                    self.bot.db_manager.log_audit(
                        'delete',
                        'product',
                        product['product_id'],
                        str(ctx.author.id),
                        f"Deleted {product['category']} product: {product['name']} (SKU: {product['sku']})"
                    )
                    
                    # Send success message
                    success_embed = discord.Embed(
                        title="Product Deleted",
                        description=f"Successfully deleted product: {product['name']}",
                        color=discord.Color.green()
                    )
                    
                    await ctx.send(embed=success_embed)
                else:
                    await ctx.send("Failed to delete product. It may be referenced by sales records.")
            else:
                await ctx.send("Product deletion cancelled.")
        
        except asyncio.TimeoutError:
            await ctx.send("Product deletion timed out due to inactivity.")
    
    @commands.command(name="importproducts")
    async def import_products_command(self, ctx):
        """
        Import products from a CSV file
        
        Usage:
        !importproducts - Upload a CSV file with product data
        
        The CSV file should have headers matching the product fields:
        category,name,sku,manufacturer,vendor,style,color,size,cost_price,selling_price,quantity
        """
        embed = discord.Embed(
            title="Import Products",
            description="Please upload a CSV file with product data.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="CSV Format",
            value="The CSV file should have headers matching the product fields:\n"
                  "category,name,sku,manufacturer,vendor,style,color,size,cost_price,selling_price,quantity\n\n"
                  "The 'category' field must be one of: blank, dtf, other",
            inline=False
        )
        
        embed.add_field(
            name="Required Fields",
            value="category, name, and sku are required for all products.\n"
                  "Other fields can be left blank if not applicable.",
            inline=False
        )
        
        embed.add_field(
            name="Example",
            value="```\n"
                  "category,name,sku,manufacturer,vendor,style,color,size,cost_price,selling_price,quantity\n"
                  "blank,Basic T-Shirt,TS001,ABC Apparel,,101,Black,L,8.50,19.99,10\n"
                  "dtf,Logo Print,DP001,,XYZ Prints,,,10x12,5.25,12.99,5\n"
                  "```",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
        # Wait for file upload
        try:
            def check_file(message):
                return (message.author.id == ctx.author.id and
                        message.channel.id == ctx.channel.id and
                        len(message.attachments) > 0 and
                        message.attachments[0].filename.lower().endswith('.csv'))
            
            response_message = await self.bot.wait_for('message', check=check_file, timeout=300)
            
            # Get the attachment
            attachment = response_message.attachments[0]
            
            # Download the file content
            csv_content = await attachment.read()
            csv_text = csv_content.decode('utf-8')
            
            # Process the CSV
            results = await self._process_product_csv(ctx, csv_text)
            
            # Send results
            result_embed = discord.Embed(
                title="Import Results",
                description=f"Processed {results['total']} products",
                color=discord.Color.green() if results['success'] > 0 else discord.Color.red()
            )
            
            result_embed.add_field(
                name="Success",
                value=f"{results['success']} products imported successfully",
                inline=True
            )
            
            result_embed.add_field(
                name="Failed",
                value=f"{results['failed']} products failed to import",
                inline=True
            )
            
            if results['errors']:
                error_text = "\n".join([f"• Row {i+1}: {error}" for i, error in results['errors']])
                if len(error_text) > 1024:
                    error_text = error_text[:1021] + "..."
                
                result_embed.add_field(
                    name="Errors",
                    value=error_text,
                    inline=False
                )
            
            await ctx.send(embed=result_embed)
        
        except asyncio.TimeoutError:
            await ctx.send("Import timed out. Please try again.")
    
    async def _process_product_csv(self, ctx, csv_text):
        """Process a CSV file with product data"""
        results = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            # Parse CSV
            csv_reader = csv.DictReader(io.StringIO(csv_text))
            
            # Check required headers
            required_headers = ['category', 'name', 'sku']
            missing_headers = [h for h in required_headers if h not in csv_reader.fieldnames]
            
            if missing_headers:
                results['errors'].append(f"Missing required headers: {', '.join(missing_headers)}")
                return results
            
            # Process each row
            for i, row in enumerate(csv_reader):
                results['total'] += 1
                
                try:
                    # Validate required fields
                    if not row['category'] or not row['name'] or not row['sku']:
                        results['failed'] += 1
                        results['errors'].append(f"Missing required fields (category, name, or sku)")
                        continue
                    
                    # Validate category
                    if row['category'].lower() not in PRODUCT_CATEGORIES:
                        results['failed'] += 1
                        results['errors'].append(f"Invalid category: {row['category']}")
                        continue
                    
                    # Check if SKU already exists
                    existing_product = self.bot.db_manager.get_product_by_sku(row['sku'])
                    if existing_product:
                        results['failed'] += 1
                        results['errors'].append(f"SKU already exists: {row['sku']}")
                        continue
                    
                    # Prepare product data
                    product_data = {
                        'category': row['category'].lower(),
                        'name': row['name'],
                        'sku': row['sku'],
                        'manufacturer': row.get('manufacturer', ''),
                        'vendor': row.get('vendor', ''),
                        'style': row.get('style', ''),
                        'color': row.get('color', ''),
                        'size': row.get('size', ''),
                        'subcategory': row.get('subcategory', None)
                    }
                    
                    # Handle numeric fields
                    if row.get('cost_price'):
                        try:
                            product_data['cost_price'] = float(row['cost_price'])
                        except ValueError:
                            results['failed'] += 1
                            results['errors'].append(f"Invalid cost_price: {row['cost_price']}")
                            continue
                    
                    if row.get('selling_price'):
                        try:
                            product_data['selling_price'] = float(row['selling_price'])
                        except ValueError:
                            results['failed'] += 1
                            results['errors'].append(f"Invalid selling_price: {row['selling_price']}")
                            continue
                    
                    if row.get('quantity'):
                        try:
                            product_data['quantity'] = int(row['quantity'])
                        except ValueError:
                            results['failed'] += 1
                            results['errors'].append(f"Invalid quantity: {row['quantity']}")
                            continue
                    else:
                        product_data['quantity'] = 0
                    
                    # Add the product
                    product_id = self.bot.db_manager.add_product(product_data)
                    
                    if product_id:
                        results['success'] += 1
                        
                        # Log the action
                        self.bot.db_manager.log_audit(
                            'create',
                            'product',
                            product_id,
                            str(ctx.author.id),
                            f"Imported {product_data['category']} product: {product_data['name']} (CSV import)"
                        )
                    else:
                        results['failed'] += 1
                        results['errors'].append(f"Database error adding product: {row['sku']}")
                
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"Error processing row: {str(e)}")
        
        except Exception as e:
            results['errors'].append(f"Error parsing CSV: {str(e)}")
        
        return results
    
    @commands.command(name="verifyinventory")
    async def verify_inventory_command(self, ctx, sku=None):
        """
        Verify physical inventory counts against system records
        
        Usage:
        !verifyinventory - Start a guided inventory verification process
        !verifyinventory <sku> - Verify a specific product
        """
        # Check if user already has an active conversation
        if ctx.author.id in self.active_conversations:
            await ctx.send("You already have an active operation in progress. "
                          "Please finish or cancel it before starting a new one.")
            return
        
        db = self.bot.db_manager
        
        if sku:
            # Verify a specific product
            product = db.get_product_by_sku(sku)
            if not product:
                await ctx.send(f"No product found with SKU: {sku}")
                return
            
            # Start verification for this product
            await self._start_single_product_verification(ctx, product)
        else:
            # Start a guided verification process
            embed = discord.Embed(
                title="Inventory Verification",
                description="This process will help you verify physical inventory counts against system records.",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Options",
                value="1️⃣ Verify a single product by SKU\n"
                      "2️⃣ Verify products by category\n"
                      "3️⃣ Verify all products",
                inline=False
            )
            
            embed.set_footer(text="React with the number for your choice, or type 'cancel' to exit")
            
            # Create conversation state
            conversation = ProductConversation(ctx)
            conversation.current_step = "verification_type"
            self.active_conversations[ctx.author.id] = conversation
            
            # Send message with reactions
            message = await ctx.send(embed=embed)
            conversation.message = message
            
            # Add reactions
            await message.add_reaction("1️⃣")
            await message.add_reaction("2️⃣")
            await message.add_reaction("3️⃣")
            await message.add_reaction("❌")
    
    async def _start_single_product_verification(self, ctx, product):
        """Start verification for a single product"""
        # Create conversation for verification
        conversation = ProductConversation(ctx)
        conversation.data = {
            'product_id': product['product_id'],
            'sku': product['sku'],
            'name': product['name'],
            'category': product['category'],
            'system_quantity': product['quantity'],
            'verification_type': 'single'
        }
        conversation.current_step = "count"
        self.active_conversations[ctx.author.id] = conversation
        
        # Create embed for count entry
        embed = discord.Embed(
            title=f"Verify Inventory: {product['name']}",
            description=f"SKU: {product['sku']} | Category: {product['category'].capitalize()}",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="System Quantity",
            value=str(product['quantity']),
            inline=True
        )
        
        embed.add_field(
            name="Physical Count",
            value="Please enter the actual physical count you have on hand.",
            inline=False
        )
        
        embed.set_footer(text="Enter the count, or type 'cancel' to exit")
        
        # Send message
        conversation.message = await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle reactions for verification workflow"""
        # Ignore bot reactions
        if user.bot:
            return
        
        # Check if user has an active conversation
        if user.id not in self.active_conversations:
            return
        
        conversation = self.active_conversations[user.id]
        
        # Make sure it's the right message
        if reaction.message.id != conversation.message.id:
            return
        
        # Update activity timestamp
        conversation.update_activity()
        
        # Handle verification type selection
        if conversation.current_step == "verification_type":
            if str(reaction.emoji) == "1️⃣":
                # Single product verification
                await self._prompt_for_sku(conversation)
            elif str(reaction.emoji) == "2️⃣":
                # Category verification
                await self._prompt_for_category(conversation)
            elif str(reaction.emoji) == "3️⃣":
                # All products verification
                await self._start_all_products_verification(conversation)
            elif str(reaction.emoji) == "❌":
                # Cancel
                await conversation.ctx.send("Verification cancelled.")
                del self.active_conversations[user.id]
        
        # Handle reconciliation confirmation
        elif conversation.current_step == "reconcile":
            if str(reaction.emoji) == "✅":
                # Yes, reconcile inventory
                await self._reconcile_inventory(conversation)
            elif str(reaction.emoji) == "❌":
                # No, don't reconcile
                await conversation.ctx.send("Verification completed without reconciliation.")
                del self.active_conversations[user.id]
        
        # Handle single product reconciliation
        elif conversation.current_step == "reconcile_single":
            if str(reaction.emoji) == "✅":
                # Yes, reconcile this product
                product_id = conversation.data['product_id']
                difference = conversation.data['difference']
                
                # Update inventory
                reason = "Inventory verification adjustment"
                success = self.bot.db_manager.adjust_product_quantity(
                    product_id,
                    difference,  # This will be positive or negative as needed
                    str(user.id),
                    reason
                )
                
                if success:
                    await conversation.ctx.send(f"Inventory updated successfully. System quantity now matches physical count.")
                else:
                    await conversation.ctx.send("Failed to update inventory. Please try again.")
                
                # Clean up conversation
                del self.active_conversations[user.id]
            
            elif str(reaction.emoji) == "❌":
                # No, don't reconcile
                await conversation.ctx.send("Verification completed without updating inventory.")
                del self.active_conversations[user.id]
    
    async def _prompt_for_sku(self, conversation):
        """Prompt for SKU entry"""
        conversation.current_step = "sku_entry"
        conversation.data['verification_type'] = 'single'
        
        embed = discord.Embed(
            title="Enter Product SKU",
            description="Please enter the SKU of the product you want to verify.",
            color=discord.Color.blue()
        )
        
        embed.set_footer(text="Enter the SKU, or type 'cancel' to exit")
        
        await conversation.message.edit(embed=embed)
    
    async def _prompt_for_category(self, conversation):
        """Prompt for category selection"""
        conversation.current_step = "category_entry"
        conversation.data['verification_type'] = 'category'
        
        embed = discord.Embed(
            title="Select Product Category",
            description="Please enter the category of products you want to verify.",
            color=discord.Color.blue()
        )
        
        for cat in PRODUCT_CATEGORIES:
            if cat == 'blank':
                description = "Blank clothing items (t-shirts, hoodies, etc.)"
            elif cat == 'dtf':
                description = "DTF prints (transfers, designs)"
            else:
                description = "Other products (accessories, equipment, etc.)"
            
            embed.add_field(
                name=cat.capitalize(),
                value=description,
                inline=False
            )
        
        embed.set_footer(text="Enter the category name, or type 'cancel' to exit")
        
        await conversation.message.edit(embed=embed)
    
    async def _start_all_products_verification(self, conversation):
        """Start verification for all products"""
        conversation.data['verification_type'] = 'all'
        
        # Get all products
        products = self.bot.db_manager.list_products()
        
        if not products:
            await conversation.ctx.send("No products found in the system.")
            del self.active_conversations[conversation.user_id]
            return
        
        # Store products in conversation
        conversation.data['products'] = products
        conversation.data['current_index'] = 0
        conversation.data['verified_products'] = []
        conversation.data['discrepancies'] = []
        
        # Start with the first product
        await self._show_next_product_for_verification(conversation)
    
    async def _show_next_product_for_verification(self, conversation):
        """Show the next product for verification"""
        products = conversation.data['products']
        current_index = conversation.data['current_index']
        
        if current_index >= len(products):
            # All products verified, show summary
            await self._show_verification_summary(conversation)
            return
        
        # Get current product
        product = products[current_index]
        conversation.current_step = "count"
        conversation.data['current_product'] = product
        
        # Create embed for count entry
        embed = discord.Embed(
            title=f"Verify Inventory ({current_index + 1}/{len(products)})",
            description=f"Product: {product['name']}\nSKU: {product['sku']} | Category: {product['category'].capitalize()}",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="System Quantity",
            value=str(product['quantity']),
            inline=True
        )
        
        embed.add_field(
            name="Physical Count",
            value="Please enter the actual physical count you have on hand.",
            inline=False
        )
        
        embed.add_field(
            name="Options",
            value="• Enter the count number\n"
                  "• Type 'skip' to skip this product\n"
                  "• Type 'same' if physical count matches system\n"
                  "• Type 'stop' to end verification and see results\n"
                  "• Type 'cancel' to exit without saving",
            inline=False
        )
        
        # Update or send message
        if conversation.message:
            await conversation.message.edit(embed=embed)
        else:
            conversation.message = await conversation.ctx.send(embed=embed)
    
    async def _show_verification_summary(self, conversation):
        """Show verification summary"""
        verified_products = conversation.data.get('verified_products', [])
        discrepancies = conversation.data.get('discrepancies', [])
        
        embed = discord.Embed(
            title="Inventory Verification Summary",
            description=f"Verified {len(verified_products)} products",
            color=discord.Color.green()
        )
        
        if discrepancies:
            embed.add_field(
                name=f"Discrepancies Found ({len(discrepancies)})",
                value="The following products have count discrepancies:",
                inline=False
            )
            
            for disc in discrepancies[:10]:  # Show first 10 discrepancies
                embed.add_field(
                    name=f"{disc['name']} ({disc['sku']})",
                    value=f"System: {disc['system_quantity']} | Actual: {disc['actual_quantity']}\n"
                          f"Difference: {disc['difference']}",
                    inline=False
                )
            
            if len(discrepancies) > 10:
                embed.add_field(
                    name="More Discrepancies",
                    value=f"... and {len(discrepancies) - 10} more discrepancies",
                    inline=False
                )
            
            embed.add_field(
                name="Reconcile Inventory",
                value="Would you like to update the system to match physical counts?",
                inline=False
            )
            
            # Send message with reactions
            if conversation.message:
                await conversation.message.edit(embed=embed)
            else:
                conversation.message = await conversation.ctx.send(embed=embed)
            
            # Add reactions for reconciliation
            await conversation.message.add_reaction("✅")  # Yes
            await conversation.message.add_reaction("❌")  # No
            
            # Update step
            conversation.current_step = "reconcile"
        else:
            embed.add_field(
                name="No Discrepancies",
                value="All verified products match system quantities.",
                inline=False
            )
            
            # Send message
            if conversation.message:
                await conversation.message.edit(embed=embed)
            else:
                await conversation.ctx.send(embed=embed)
            
            # Clean up conversation
            del self.active_conversations[conversation.user_id]
    
    async def _reconcile_inventory(self, conversation):
        """Reconcile inventory discrepancies"""
        discrepancies = conversation.data.get('discrepancies', [])
        
        if not discrepancies:
            await conversation.ctx.send("No discrepancies to reconcile.")
            del self.active_conversations[conversation.user_id]
            return
        
        # Create embed for confirmation
        embed = discord.Embed(
            title="Reconciling Inventory",
            description="Updating system quantities to match physical counts...",
            color=discord.Color.gold()
        )
        
        await conversation.ctx.send(embed=embed)
        
        # Process each discrepancy
        db = self.bot.db_manager
        updated_count = 0
        
        for disc in discrepancies:
            product_id = disc['product_id']
            difference = disc['difference']
            
            # Skip if no difference
            if difference == 0:
                continue
            
            # Update inventory
            reason = "Inventory verification adjustment"
            success = db.adjust_product_quantity(
                product_id,
                difference,  # This will be positive or negative as needed
                str(conversation.user_id),
                reason
            )
            
            if success:
                updated_count += 1
        
        # Send completion message
        complete_embed = discord.Embed(
            title="Inventory Reconciliation Complete",
            description=f"Updated {updated_count} of {len(discrepancies)} products",
            color=discord.Color.green()
        )
        
        await conversation.ctx.send(embed=complete_embed)
        
        # Clean up conversation
        del self.active_conversations[conversation.user_id]
    
    @commands.command(name="inventoryhistory")
    async def inventory_history_command(self, ctx, sku=None, limit: int = 10):
        """
        View inventory history for a product or all products
        
        Usage:
        !inventoryhistory - Show recent inventory changes for all products
        !inventoryhistory <sku> - Show history for a specific product
        !inventoryhistory <sku> <limit> - Show specific number of history entries
        """
        db = self.bot.db_manager
        
        if sku:
            # Get product by SKU
            product = db.get_product_by_sku(sku)
            if not product:
                await ctx.send(f"No product found with SKU: {sku}")
                return
            
            # Get history for this product
            history = db.get_product_inventory_history(product['product_id'], limit)
            
            if not history:
                await ctx.send(f"No inventory history found for product with SKU: {sku}")
                return
            
            embed = discord.Embed(
                title=f"Inventory History: {product['name']}",
                description=f"SKU: {product['sku']} | Category: {product['category'].capitalize()}",
                color=discord.Color.blue()
            )
            
            for entry in history:
                change_text = f"{'+' if entry['change_amount'] > 0 else ''}{entry['change_amount']}"
                timestamp = entry['timestamp'].split('T')[0]  # Just get the date part
                
                reason = entry['reason'] if entry['reason'] else "No reason provided"
                
                embed.add_field(
                    name=f"{timestamp} | {change_text}",
                    value=f"From {entry['previous_quantity']} to {entry['new_quantity']}\nReason: {reason}",
                    inline=False
                )
            
            embed.set_footer(text=f"Showing {len(history)} of {limit} requested entries")
            
        else:
            # Get history for all products
            history = db.get_inventory_history(limit=limit)
            
            if not history:
                await ctx.send("No inventory history found.")
                return
            
            embed = discord.Embed(
                title="Recent Inventory Changes",
                description=f"Showing the {limit} most recent inventory changes",
                color=discord.Color.blue()
            )
            
            for entry in history:
                change_text = f"{'+' if entry['change_amount'] > 0 else ''}{entry['change_amount']}"
                timestamp = entry['timestamp'].split('T')[0]  # Just get the date part
                
                product_info = f"{entry['product_name']} ({entry['sku']})"
                reason = entry['reason'] if entry['reason'] else "No reason provided"
                
                embed.add_field(
                    name=f"{timestamp} | {product_info}",
                    value=f"Change: {change_text} (From {entry['previous_quantity']} to {entry['new_quantity']})\nReason: {reason}",
                    inline=False
                )
            
            embed.set_footer(text=f"Use !inventoryhistory <sku> for product-specific history")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="findproduct")
    async def find_product_command(self, ctx, *, search_term=None):
        """
        Find products by name, SKU, category, or other attributes
        
        Usage:
        !findproduct <search_term> - Search for products matching the term
        
        Examples:
        !findproduct shirt - Find products with "shirt" in the name
        !findproduct blue - Find products with "blue" in any field
        !findproduct L - Find products with size "L"
        """
        if not search_term:
            embed = discord.Embed(
                title="Find Products",
                description="Search for products by name, SKU, category, or other attributes",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Usage",
                value="!findproduct <search_term>",
                inline=False
            )
            
            embed.add_field(
                name="Examples",
                value="!findproduct shirt - Find products with 'shirt' in the name\n"
                      "!findproduct blue - Find products with 'blue' in any field\n"
                      "!findproduct L - Find products with size 'L'",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        # Get all products
        db = self.bot.db_manager
        all_products = db.list_products()
        
        # Filter products based on search term
        search_term = search_term.lower()
        matching_products = []
        
        for product in all_products:
            # Check various fields for matches
            if (search_term in product['name'].lower() or
                search_term in product['sku'].lower() or
                search_term in product['category'].lower() or
                (product['manufacturer'] and search_term in product['manufacturer'].lower()) or
                (product['vendor'] and search_term in product['vendor'].lower()) or
                (product['style'] and search_term in product['style'].lower()) or
                (product['color'] and search_term in product['color'].lower()) or
                (product['size'] and search_term in product['size'].lower()) or
                (product['subcategory'] and search_term in product['subcategory'].lower())):
                matching_products.append(product)
        
        if not matching_products:
            await ctx.send(f"No products found matching '{search_term}'.")
            return
        
        # Create embed for results
        embed = discord.Embed(
            title=f"Products Matching '{search_term}'",
            description=f"Found {len(matching_products)} matching products",
            color=discord.Color.blue()
        )
        
        # Show first 10 matches
        for i, product in enumerate(matching_products[:10]):
            embed.add_field(
                name=f"{i+1}. {product['name']} ({product['sku']})",
                value=f"Category: {product['category'].capitalize()}\n"
                      f"Quantity: {product['quantity']}\n"
                      f"{'Size: ' + product['size'] if product['size'] else ''}"
                      f"{' | Color: ' + product['color'] if product['color'] else ''}",
                inline=False
            )
        
        # Add note if there are more results
        if len(matching_products) > 10:
            embed.set_footer(text=f"Showing 10 of {len(matching_products)} matches. Refine your search for more specific results.")
        
        await ctx.send(embed=embed)
    @commands.command(name="exportproducts")
    async def export_products_command(self, ctx, category=None):
        """
        Export products to a CSV file
        
        Usage:
        !exportproducts - Export all products
        !exportproducts <category> - Export products in a specific category
        """
        # Get products
        db = self.bot.db_manager
        products = db.list_products(category)
        
        if not products:
            await ctx.send("No products found to export.")
            return
        
        # Create CSV content
        output = io.StringIO()
        fieldnames = [
            'product_id', 'category', 'name', 'sku', 'manufacturer', 'vendor',
            'style', 'color', 'size', 'subcategory', 'quantity',
            'cost_price', 'selling_price', 'created_at', 'updated_at'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for product in products:
            # Convert None values to empty strings
            row = {k: ('' if v is None else v) for k, v in product.items()}
            writer.writerow(row)
        
        # Create file
        csv_data = output.getvalue()
        file = discord.File(
            io.BytesIO(csv_data.encode('utf-8')),
            filename=f"products_{category or 'all'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        # Send file
        await ctx.send(
            f"Exported {len(products)} products" +
            (f" in category '{category}'" if category else ""),
            file=file
        )
        
    @commands.command(name="inventoryreport", aliases=["invreport", "stockreport"])
    async def inventory_report_command(self, ctx, report_type=None, category=None, threshold=None):
        """
        Generate inventory reports
        
        Usage:
        !inventoryreport - Show available report types
        !inventoryreport stock [category] - Current stock levels report
        !inventoryreport lowstock [threshold] - Low stock alerts report (default threshold: 5)
        !inventoryreport value [category] - Inventory value calculation report
        !inventoryreport movement [days] - Inventory movement history report (default: 30 days)
        !inventoryreport category - Category breakdown report
        
        Aliases: !invreport, !stockreport
        """
        if not report_type:
            # Show available report types
            embed = discord.Embed(
                title="Inventory Reports",
                description="Available report types:",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Stock Levels Report",
                value="```!inventoryreport stock [category]```\nShows current stock levels for all or specific category products.",
                inline=False
            )
            
            embed.add_field(
                name="Low Stock Alerts",
                value="```!inventoryreport lowstock [threshold]```\nShows products below the specified threshold (default: 5).",
                inline=False
            )
            
            embed.add_field(
                name="Inventory Value Report",
                value="```!inventoryreport value [category]```\nCalculates inventory value based on cost and selling prices.",
                inline=False
            )
            
            embed.add_field(
                name="Movement History Report",
                value="```!inventoryreport movement [days]```\nShows inventory changes over the specified number of days (default: 30).",
                inline=False
            )
            
            embed.add_field(
                name="Category Breakdown Report",
                value="```!inventoryreport category```\nBreaks down inventory by category with detailed statistics.",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        # Process based on report type
        report_type = report_type.lower()
        
        if report_type == "stock":
            await self._generate_stock_report(ctx, category)
        
        elif report_type == "lowstock":
            # Parse threshold
            try:
                threshold_value = int(threshold) if threshold else 5
                if threshold_value < 0:
                    await ctx.send("Threshold must be a positive number.")
                    return
            except ValueError:
                await ctx.send("Invalid threshold value. Please provide a number.")
                return
            
            await self._generate_low_stock_report(ctx, threshold_value)
        
        elif report_type == "value":
            await self._generate_value_report(ctx, category)
        
        elif report_type == "movement":
            # Parse days
            try:
                days = int(category) if category else 30
                if days <= 0:
                    await ctx.send("Days must be a positive number.")
                    return
            except ValueError:
                await ctx.send("Invalid days value. Please provide a number.")
                return
            
            await self._generate_movement_report(ctx, days)
        
        elif report_type == "category":
            await self._generate_category_report(ctx)
        
        else:
            await ctx.send(f"Unknown report type: {report_type}. Use `!inventoryreport` to see available report types.")
    
    async def _generate_stock_report(self, ctx, category=None):
        """Generate a stock levels report"""
        db = self.bot.db_manager
        
        # Get products
        products = db.list_products(category)
        
        if not products:
            await ctx.send(f"No products found{' in category: ' + category if category else ''}.")
            return
        
        # Create embed
        embed = discord.Embed(
            title="Stock Levels Report",
            description=f"Current inventory status{' for category: ' + category.capitalize() if category else ''}",
            color=discord.Color.blue()
        )
        
        # Add summary statistics
        total_items = sum(p['quantity'] for p in products)
        total_products = len(products)
        in_stock = sum(1 for p in products if p['quantity'] > 0)
        out_of_stock = total_products - in_stock
        
        embed.add_field(name="Total Products", value=str(total_products), inline=True)
        embed.add_field(name="Total Items", value=str(total_items), inline=True)
        embed.add_field(name="In Stock", value=f"{in_stock} ({in_stock/total_products*100:.1f}%)", inline=True)
        embed.add_field(name="Out of Stock", value=str(out_of_stock), inline=True)
        
        # Sort products by quantity (descending)
        products.sort(key=lambda p: p['quantity'], reverse=True)
        
        # Add top products by quantity
        top_products = products[:10]
        if top_products:
            top_text = "\n".join([
                f"{p['name']} ({p['sku']}): {p['quantity']}" for p in top_products
            ])
            embed.add_field(
                name="Top Products by Quantity",
                value=top_text,
                inline=False
            )
        
        # Generate CSV report
        report_generator = self.bot.report_generator
        csv_path, _ = await report_generator.generate_inventory_report(category)
        
        # Send embed and file
        file = discord.File(csv_path, filename=os.path.basename(csv_path))
        embed.set_footer(text="Full report attached as CSV file")
        
        await ctx.send(embed=embed, file=file)
    
    async def _generate_low_stock_report(self, ctx, threshold=5):
        """Generate a low stock alerts report"""
        db = self.bot.db_manager
        
        # Get all products
        products = db.list_products()
        
        # Filter low stock products
        low_stock = [p for p in products if 0 < p['quantity'] <= threshold]
        out_of_stock = [p for p in products if p['quantity'] <= 0]
        
        if not low_stock and not out_of_stock:
            await ctx.send(f"No products found below the threshold of {threshold}.")
            return
        
        # Create embed
        embed = discord.Embed(
            title="Low Stock Alerts",
            description=f"Products with stock levels at or below {threshold}",
            color=discord.Color.gold()
        )
        
        # Add summary statistics
        embed.add_field(name="Low Stock Items", value=str(len(low_stock)), inline=True)
        embed.add_field(name="Out of Stock Items", value=str(len(out_of_stock)), inline=True)
        embed.add_field(name="Total Items", value=str(len(low_stock) + len(out_of_stock)), inline=True)
        
        # Add low stock products
        if low_stock:
            # Sort by quantity (ascending)
            low_stock.sort(key=lambda p: p['quantity'])
            
            low_stock_text = "\n".join([
                f"{p['name']} ({p['sku']}): {p['quantity']}" for p in low_stock[:15]
            ])
            
            if len(low_stock) > 15:
                low_stock_text += f"\n... and {len(low_stock) - 15} more"
            
            embed.add_field(
                name="Low Stock Items",
                value=low_stock_text,
                inline=False
            )
        
        # Add out of stock products
        if out_of_stock:
            out_of_stock_text = "\n".join([
                f"{p['name']} ({p['sku']})" for p in out_of_stock[:15]
            ])
            
            if len(out_of_stock) > 15:
                out_of_stock_text += f"\n... and {len(out_of_stock) - 15} more"
            
            embed.add_field(
                name="Out of Stock Items",
                value=out_of_stock_text,
                inline=False
            )
        
        # Export low stock items to CSV
        if low_stock or out_of_stock:
            output = io.StringIO()
            fieldnames = [
                'product_id', 'name', 'sku', 'category', 'quantity',
                'cost_price', 'selling_price'
            ]
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for product in low_stock + out_of_stock:
                # Only write the fields we want
                row = {field: product.get(field) for field in fieldnames}
                writer.writerow(row)
            
            # Create file
            csv_data = output.getvalue()
            file = discord.File(
                io.BytesIO(csv_data.encode('utf-8')),
                filename=f"low_stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            embed.set_footer(text="Full report attached as CSV file")
            await ctx.send(embed=embed, file=file)
        else:
            await ctx.send(embed=embed)
    
    async def _generate_value_report(self, ctx, category=None):
        """Generate an inventory value report"""
        db = self.bot.db_manager
        
        # Get products
        products = db.list_products(category)
        
        if not products:
            await ctx.send(f"No products found{' in category: ' + category if category else ''}.")
            return
        
        # Create embed
        embed = discord.Embed(
            title="Inventory Value Report",
            description=f"Value analysis{' for category: ' + category.capitalize() if category else ''}",
            color=discord.Color.green()
        )
        
        # Calculate values
        total_cost_value = sum(p['quantity'] * (p['cost_price'] or 0) for p in products)
        total_selling_value = sum(p['quantity'] * (p['selling_price'] or 0) for p in products)
        potential_profit = total_selling_value - total_cost_value
        
        # Add summary statistics
        embed.add_field(name="Total Products", value=str(len(products)), inline=True)
        embed.add_field(name="Total Items", value=str(sum(p['quantity'] for p in products)), inline=True)
        embed.add_field(name="Cost Value", value=f"${total_cost_value:.2f}", inline=True)
        embed.add_field(name="Selling Value", value=f"${total_selling_value:.2f}", inline=True)
        embed.add_field(name="Potential Profit", value=f"${potential_profit:.2f}", inline=True)
        
        if total_cost_value > 0:
            margin = (potential_profit / total_cost_value) * 100
            embed.add_field(name="Profit Margin", value=f"{margin:.1f}%", inline=True)
        
        # Group by category
        if not category:
            category_values = {}
            for product in products:
                cat = product['category']
                if cat not in category_values:
                    category_values[cat] = {
                        'count': 0,
                        'quantity': 0,
                        'cost_value': 0,
                        'selling_value': 0
                    }
                
                category_values[cat]['count'] += 1
                category_values[cat]['quantity'] += product['quantity']
                category_values[cat]['cost_value'] += product['quantity'] * (product['cost_price'] or 0)
                category_values[cat]['selling_value'] += product['quantity'] * (product['selling_price'] or 0)
            
            # Add category breakdown
            category_text = ""
            for cat, values in category_values.items():
                profit = values['selling_value'] - values['cost_value']
                category_text += f"**{cat.capitalize()}**: {values['count']} products, {values['quantity']} items\n"
                category_text += f"Cost: ${values['cost_value']:.2f}, Selling: ${values['selling_value']:.2f}, Profit: ${profit:.2f}\n\n"
            
            if category_text:
                embed.add_field(
                    name="Category Breakdown",
                    value=category_text,
                    inline=False
                )
        
        # Find most valuable products (by cost)
        valuable_products = sorted(products, key=lambda p: p['quantity'] * (p['cost_price'] or 0), reverse=True)[:10]
        
        if valuable_products:
            valuable_text = "\n".join([
                f"{p['name']} ({p['sku']}): ${p['quantity'] * (p['cost_price'] or 0):.2f} ({p['quantity']} × ${p['cost_price'] or 0:.2f})"
                for p in valuable_products
            ])
            
            embed.add_field(
                name="Most Valuable Products (Cost)",
                value=valuable_text,
                inline=False
            )
        
        # Export to CSV
        output = io.StringIO()
        fieldnames = [
            'product_id', 'name', 'sku', 'category', 'quantity',
            'cost_price', 'selling_price', 'cost_value', 'selling_value', 'potential_profit'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for product in products:
            cost_price = product.get('cost_price') or 0
            selling_price = product.get('selling_price') or 0
            quantity = product.get('quantity') or 0
            
            cost_value = quantity * cost_price
            selling_value = quantity * selling_price
            
            # Create row with calculated values
            row = {
                'product_id': product.get('product_id'),
                'name': product.get('name'),
                'sku': product.get('sku'),
                'category': product.get('category'),
                'quantity': quantity,
                'cost_price': cost_price,
                'selling_price': selling_price,
                'cost_value': cost_value,
                'selling_value': selling_value,
                'potential_profit': selling_value - cost_value
            }
            
            writer.writerow(row)
        
        # Create file
        csv_data = output.getvalue()
        file = discord.File(
            io.BytesIO(csv_data.encode('utf-8')),
            filename=f"inventory_value_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        embed.set_footer(text="Full report attached as CSV file")
        await ctx.send(embed=embed, file=file)
    
    async def _generate_movement_report(self, ctx, days=30):
        """Generate an inventory movement history report"""
        db = self.bot.db_manager
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Format dates for query
        start_date_str = start_date.strftime("%Y-%m-%dT00:00:00")
        end_date_str = end_date.strftime("%Y-%m-%dT23:59:59")
        
        # Get inventory history
        history = db.get_inventory_history(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )
        
        if not history:
            await ctx.send(f"No inventory movements found in the last {days} days.")
            return
        
        # Create embed
        embed = discord.Embed(
            title="Inventory Movement Report",
            description=f"Changes in the last {days} days ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})",
            color=discord.Color.blue()
        )
        
        # Calculate summary statistics
        total_changes = len(history)
        increases = sum(1 for h in history if h['change_amount'] > 0)
        decreases = sum(1 for h in history if h['change_amount'] < 0)
        
        total_increase = sum(h['change_amount'] for h in history if h['change_amount'] > 0)
        total_decrease = sum(abs(h['change_amount']) for h in history if h['change_amount'] < 0)
        
        # Add summary fields
        embed.add_field(name="Total Changes", value=str(total_changes), inline=True)
        embed.add_field(name="Increases", value=f"{increases} (+{total_increase})", inline=True)
        embed.add_field(name="Decreases", value=f"{decreases} (-{total_decrease})", inline=True)
        
        # Group by product
        product_movements = {}
        for entry in history:
            product_id = entry['product_id']
            if product_id not in product_movements:
                product_movements[product_id] = {
                    'name': entry['product_name'],
                    'sku': entry['sku'],
                    'category': entry['category'],
                    'increases': 0,
                    'decreases': 0,
                    'net_change': 0,
                    'changes': []
                }
            
            change = entry['change_amount']
            product_movements[product_id]['net_change'] += change
            
            if change > 0:
                product_movements[product_id]['increases'] += change
            else:
                product_movements[product_id]['decreases'] += abs(change)
            
            product_movements[product_id]['changes'].append(entry)
        
        # Find most active products
        most_active = sorted(
            product_movements.items(),
            key=lambda x: x[1]['increases'] + x[1]['decreases'],
            reverse=True
        )[:10]
        
        if most_active:
            active_text = ""
            for _, product in most_active:
                active_text += f"**{product['name']} ({product['sku']})**\n"
                active_text += f"In: +{product['increases']}, Out: -{product['decreases']}, Net: {product['net_change']:+}\n"
            
            embed.add_field(
                name="Most Active Products",
                value=active_text,
                inline=False
            )
        
        # Find products with largest net changes
        largest_changes = sorted(
            product_movements.items(),
            key=lambda x: abs(x[1]['net_change']),
            reverse=True
        )[:10]
        
        if largest_changes:
            changes_text = ""
            for _, product in largest_changes:
                changes_text += f"**{product['name']} ({product['sku']})**\n"
                changes_text += f"Net change: {product['net_change']:+}\n"
            
            embed.add_field(
                name="Largest Net Changes",
                value=changes_text,
                inline=False
            )
        
        # Recent activity
        recent_history = sorted(history, key=lambda h: h['timestamp'], reverse=True)[:10]
        
        if recent_history:
            recent_text = ""
            for entry in recent_history:
                date = entry['timestamp'].split('T')[0]
                recent_text += f"{date}: {entry['product_name']} ({entry['sku']}): {entry['change_amount']:+}\n"
            
            embed.add_field(
                name="Recent Activity",
                value=recent_text,
                inline=False
            )
        
        # Export to CSV
        output = io.StringIO()
        fieldnames = [
            'timestamp', 'product_name', 'sku', 'category',
            'previous_quantity', 'new_quantity', 'change_amount', 'reason'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for entry in history:
            # Create row with selected fields
            row = {field: entry.get(field) for field in fieldnames}
            writer.writerow(row)
        
        # Create file
        csv_data = output.getvalue()
        file = discord.File(
            io.BytesIO(csv_data.encode('utf-8')),
            filename=f"inventory_movement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        embed.set_footer(text="Full report attached as CSV file")
        await ctx.send(embed=embed, file=file)
    
    async def _generate_category_report(self, ctx):
        """Generate a category breakdown report"""
        db = self.bot.db_manager
        
        # Get all products
        products = db.list_products()
        
        if not products:
            await ctx.send("No products found in the database.")
            return
        
        # Create embed
        embed = discord.Embed(
            title="Category Breakdown Report",
            description="Detailed analysis by product category",
            color=discord.Color.purple()
        )
        
        # Group by category
        categories = {}
        for product in products:
            category = product['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(product)
        
        # Add summary statistics
        embed.add_field(name="Total Categories", value=str(len(categories)), inline=True)
        embed.add_field(name="Total Products", value=str(len(products)), inline=True)
        embed.add_field(name="Total Items", value=str(sum(p['quantity'] for p in products)), inline=True)
        
        # Add category details
        for category, category_products in categories.items():
            # Calculate statistics
            product_count = len(category_products)
            item_count = sum(p['quantity'] for p in category_products)
            cost_value = sum(p['quantity'] * (p['cost_price'] or 0) for p in category_products)
            selling_value = sum(p['quantity'] * (p['selling_price'] or 0) for p in category_products)
            
            # Count products with and without stock
            in_stock = sum(1 for p in category_products if p['quantity'] > 0)
            out_of_stock = product_count - in_stock
            
            # Create category field
            field_value = (
                f"Products: {product_count}\n"
                f"Items: {item_count}\n"
                f"In stock: {in_stock} ({in_stock/product_count*100:.1f}%)\n"
                f"Out of stock: {out_of_stock}\n"
                f"Cost value: ${cost_value:.2f}\n"
                f"Selling value: ${selling_value:.2f}\n"
                f"Potential profit: ${selling_value - cost_value:.2f}"
            )
            
            embed.add_field(
                name=f"{category.capitalize()} Category",
                value=field_value,
                inline=True
            )
        
        # Add subcategory breakdown if any products have subcategories
        subcategory_products = [p for p in products if p.get('subcategory')]
        
        if subcategory_products:
            # Group by subcategory
            subcategories = {}
            for product in subcategory_products:
                key = f"{product['category']}/{product['subcategory']}"
                if key not in subcategories:
                    subcategories[key] = []
                subcategories[key].append(product)
            
            # Create subcategory text
            subcategory_text = ""
            for key, subcat_products in subcategories.items():
                product_count = len(subcat_products)
                item_count = sum(p['quantity'] for p in subcat_products)
                subcategory_text += f"**{key}**: {product_count} products, {item_count} items\n"
            
            if subcategory_text:
                embed.add_field(
                    name="Subcategory Breakdown",
                    value=subcategory_text,
                    inline=False
                )
        
        # Export to CSV
        output = io.StringIO()
        fieldnames = [
            'category', 'subcategory', 'product_count', 'item_count',
            'in_stock_count', 'out_of_stock_count', 'cost_value',
            'selling_value', 'potential_profit'
        ]
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        # Write category summary rows
        for category, category_products in categories.items():
            product_count = len(category_products)
            item_count = sum(p['quantity'] for p in category_products)
            in_stock = sum(1 for p in category_products if p['quantity'] > 0)
            out_of_stock = product_count - in_stock
            cost_value = sum(p['quantity'] * (p['cost_price'] or 0) for p in category_products)
            selling_value = sum(p['quantity'] * (p['selling_price'] or 0) for p in category_products)
            
            row = {
                'category': category,
                'subcategory': 'ALL',
                'product_count': product_count,
                'item_count': item_count,
                'in_stock_count': in_stock,
                'out_of_stock_count': out_of_stock,
                'cost_value': cost_value,
                'selling_value': selling_value,
                'potential_profit': selling_value - cost_value
            }
            
            writer.writerow(row)
            
            # Write subcategory rows if applicable
            subcategories = {}
            for product in category_products:
                if product.get('subcategory'):
                    subcategory = product['subcategory']
                    if subcategory not in subcategories:
                        subcategories[subcategory] = []
                    subcategories[subcategory].append(product)
            
            for subcategory, subcat_products in subcategories.items():
                sub_product_count = len(subcat_products)
                sub_item_count = sum(p['quantity'] for p in subcat_products)
                sub_in_stock = sum(1 for p in subcat_products if p['quantity'] > 0)
                sub_out_of_stock = sub_product_count - sub_in_stock
                sub_cost_value = sum(p['quantity'] * (p['cost_price'] or 0) for p in subcat_products)
                sub_selling_value = sum(p['quantity'] * (p['selling_price'] or 0) for p in subcat_products)
                
                row = {
                    'category': category,
                    'subcategory': subcategory,
                    'product_count': sub_product_count,
                    'item_count': sub_item_count,
                    'in_stock_count': sub_in_stock,
                    'out_of_stock_count': sub_out_of_stock,
                    'cost_value': sub_cost_value,
                    'selling_value': sub_selling_value,
                    'potential_profit': sub_selling_value - sub_cost_value
                }
                
                writer.writerow(row)
        
        # Create file
        csv_data = output.getvalue()
        file = discord.File(
            io.BytesIO(csv_data.encode('utf-8')),
            filename=f"category_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        
        embed.set_footer(text="Full report attached as CSV file")
        await ctx.send(embed=embed, file=file)

async def setup(bot):
    """Add the cog to the bot"""
    await bot.add_cog(InventoryCog(bot))