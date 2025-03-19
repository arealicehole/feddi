"""
Report Generator for AccountME Discord Bot
Handles generation of financial and inventory reports
Includes automated reporting functionality
"""

import os
import logging
import csv
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
import discord
from utils.db_manager import DatabaseManager

logger = logging.getLogger("accountme_bot.report_generator")

class ReportGenerator:
    """
    Report generator class for creating financial and inventory reports
    Includes automated reporting functionality for scheduled reports
    """
    
    def __init__(self, db_manager: DatabaseManager, reports_dir: str = "data/reports"):
        """
        Initialize the report generator
        
        Args:
            db_manager: Database manager instance
            reports_dir: Directory to store generated reports
        """
        self.db_manager = db_manager
        self.reports_dir = reports_dir
        os.makedirs(reports_dir, exist_ok=True)
        logger.info(f"Report generator initialized with reports directory: {reports_dir}")
        
        # Scheduled reports configuration
        self.scheduled_reports = {}  # Dictionary to store scheduled report tasks
        self.report_channels = {}    # Dictionary to map report types to Discord channels
    
    async def generate_inventory_report(self, category: Optional[str] = None) -> Tuple[str, discord.Embed]:
        """
        Generate an inventory report
        
        Args:
            category: Optional category filter
            
        Returns:
            Tuple of (csv_path, discord_embed)
        """
        # Build query
        query = "SELECT * FROM products"
        params = ()
        
        if category:
            query += " WHERE category = ?"
            params = (category,)
        
        # Execute query
        products = self.db_manager.execute_query(query, params)
        
        # Generate CSV report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"inventory_report_{timestamp}.csv"
        csv_path = os.path.join(self.reports_dir, filename)
        
        with open(csv_path, 'w', newline='') as csvfile:
            fieldnames = [
                'product_id', 'name', 'category', 'subcategory', 
                'manufacturer', 'vendor', 'style', 'color', 'size', 
                'sku', 'quantity', 'cost_price', 'selling_price'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for product in products:
                # Only write the fields we want
                row = {field: product.get(field) for field in fieldnames}
                writer.writerow(row)
        
        # Calculate summary statistics
        total_items = sum(p.get('quantity', 0) for p in products)
        total_value = sum(p.get('quantity', 0) * p.get('cost_price', 0) for p in products)
        
        # Create Discord embed
        embed = discord.Embed(
            title="Inventory Report",
            description=f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Total Products", value=str(len(products)), inline=True)
        embed.add_field(name="Total Items", value=str(total_items), inline=True)
        embed.add_field(name="Total Value", value=f"${total_value:.2f}", inline=True)
        
        # Add category breakdown
        category_counts = {}
        for product in products:
            cat = product.get('category', 'unknown')
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        category_summary = "\n".join([f"{cat}: {count}" for cat, count in category_counts.items()])
        embed.add_field(name="Category Breakdown", value=category_summary or "No data", inline=False)
        
        # Add low stock warning
        low_stock = [p for p in products if p.get('quantity', 0) < 5 and p.get('quantity', 0) > 0]
        if low_stock:
            low_stock_text = "\n".join([f"{p['name']} ({p['sku']}): {p['quantity']}" for p in low_stock[:5]])
            if len(low_stock) > 5:
                low_stock_text += f"\n...and {len(low_stock) - 5} more"
            embed.add_field(name="Low Stock Warning", value=low_stock_text, inline=False)
        
        # Add out of stock warning
        out_of_stock = [p for p in products if p.get('quantity', 0) == 0]
        if out_of_stock:
            out_of_stock_text = "\n".join([f"{p['name']} ({p['sku']})" for p in out_of_stock[:5]])
            if len(out_of_stock) > 5:
                out_of_stock_text += f"\n...and {len(out_of_stock) - 5} more"
            embed.add_field(name="Out of Stock", value=out_of_stock_text, inline=False)
        
        embed.set_footer(text=f"Full report saved as {filename}")
        
        logger.info(f"Inventory report generated and saved to {csv_path}")
        return csv_path, embed
    
    async def generate_expense_report(self, 
                                     start_date: Optional[str] = None, 
                                     end_date: Optional[str] = None,
                                     category: Optional[str] = None) -> Tuple[str, discord.Embed]:
        """
        Generate an expense report
        
        Args:
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            category: Optional category filter
            
        Returns:
            Tuple of (csv_path, discord_embed)
        """
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        if not start_date:
            # Default to 30 days before end date
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            start_date_obj = end_date_obj - timedelta(days=30)
            start_date = start_date_obj.strftime("%Y-%m-%d")
        
        # Build query
        query = "SELECT * FROM expenses WHERE date BETWEEN ? AND ?"
        params = (start_date, end_date)
        
        if category:
            query += " AND category = ?"
            params = params + (category,)
        
        # Execute query
        expenses = self.db_manager.execute_query(query, params)
        
        # Generate CSV report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"expense_report_{timestamp}.csv"
        csv_path = os.path.join(self.reports_dir, filename)
        
        with open(csv_path, 'w', newline='') as csvfile:
            fieldnames = [
                'expense_id', 'date', 'vendor', 'amount', 
                'category', 'description', 'receipt_image'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for expense in expenses:
                # Only write the fields we want
                row = {field: expense.get(field) for field in fieldnames}
                writer.writerow(row)
        
        # Calculate summary statistics
        total_amount = sum(e.get('amount', 0) for e in expenses)
        
        # Create category breakdown
        category_totals = {}
        for expense in expenses:
            cat = expense.get('category', 'unknown')
            category_totals[cat] = category_totals.get(cat, 0) + expense.get('amount', 0)
        
        # Create Discord embed
        embed = discord.Embed(
            title="Expense Report",
            description=f"Period: {start_date} to {end_date}",
            color=discord.Color.red()
        )
        
        embed.add_field(name="Total Expenses", value=f"${total_amount:.2f}", inline=True)
        embed.add_field(name="Number of Transactions", value=str(len(expenses)), inline=True)
        
        # Add category breakdown
        if category_totals:
            category_summary = "\n".join([f"{cat}: ${amount:.2f}" for cat, amount in category_totals.items()])
            embed.add_field(name="Category Breakdown", value=category_summary, inline=False)
        
        # Add recent expenses
        if expenses:
            recent_expenses = sorted(expenses, key=lambda e: e.get('date', ''), reverse=True)[:5]
            recent_text = "\n".join([
                f"{e['date']} - {e['vendor']}: ${e['amount']:.2f}" for e in recent_expenses
            ])
            embed.add_field(name="Recent Expenses", value=recent_text, inline=False)
        
        embed.set_footer(text=f"Full report saved as {filename}")
        
        logger.info(f"Expense report generated and saved to {csv_path}")
        return csv_path, embed
    
    async def generate_sales_report(self,
                                   start_date: Optional[str] = None,
                                   end_date: Optional[str] = None,
                                   customer_id: Optional[int] = None) -> Tuple[str, discord.Embed]:
        """
        Generate a sales report
        
        Args:
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            customer_id: Optional customer filter
            
        Returns:
            Tuple of (csv_path, discord_embed)
        """
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        if not start_date:
            # Default to 30 days before end date
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            start_date_obj = end_date_obj - timedelta(days=30)
            start_date = start_date_obj.strftime("%Y-%m-%d")
        
        # Build query for sales
        query = """
            SELECT s.*, c.name as customer_name
            FROM sales s
            LEFT JOIN customers c ON s.customer_id = c.customer_id
            WHERE s.date BETWEEN ? AND ?
        """
        params = (start_date, end_date)
        
        if customer_id:
            query += " AND s.customer_id = ?"
            params = params + (customer_id,)
        
        # Execute query
        sales = self.db_manager.execute_query(query, params)
        
        # Get sale items for each sale
        for sale in sales:
            items_query = """
                SELECT si.*, p.name, p.sku
                FROM sale_items si
                JOIN products p ON si.product_id = p.product_id
                WHERE si.sale_id = ?
            """
            sale['items'] = self.db_manager.execute_query(items_query, (sale['sale_id'],))
        
        # Generate CSV report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sales_report_{timestamp}.csv"
        csv_path = os.path.join(self.reports_dir, filename)
        
        with open(csv_path, 'w', newline='') as csvfile:
            # Main sales data
            fieldnames = [
                'sale_id', 'date', 'customer_id', 'customer_name',
                'total_amount', 'payment_method', 'notes'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for sale in sales:
                # Only write the fields we want
                row = {field: sale.get(field) for field in fieldnames}
                writer.writerow(row)
            
            # Add a separator
            writer.writerow({field: "" for field in fieldnames})
            writer.writerow({field: field if field == 'sale_id' else "" for field in fieldnames})
            
            # Add item details
            item_fieldnames = [
                'sale_id', 'product_id', 'name', 'sku', 'quantity', 'price'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=item_fieldnames)
            
            writer.writeheader()
            for sale in sales:
                for item in sale.get('items', []):
                    item['sale_id'] = sale['sale_id']
                    row = {field: item.get(field) for field in item_fieldnames}
                    writer.writerow(row)
        
        # Calculate summary statistics
        total_amount = sum(s.get('total_amount', 0) for s in sales)
        total_items = sum(len(s.get('items', [])) for s in sales)
        
        # Create payment method breakdown
        payment_totals = {}
        for sale in sales:
            method = sale.get('payment_method', 'Unknown')
            payment_totals[method] = payment_totals.get(method, 0) + sale.get('total_amount', 0)
        
        # Create product breakdown
        product_totals = {}
        for sale in sales:
            for item in sale.get('items', []):
                product_id = item.get('product_id')
                name = item.get('name', f"Product {product_id}")
                if name not in product_totals:
                    product_totals[name] = {
                        'quantity': 0,
                        'revenue': 0
                    }
                product_totals[name]['quantity'] += item.get('quantity', 0)
                product_totals[name]['revenue'] += item.get('quantity', 0) * item.get('price', 0)
        
        # Sort products by revenue
        sorted_products = sorted(
            product_totals.items(),
            key=lambda x: x[1]['revenue'],
            reverse=True
        )
        
        # Create Discord embed
        customer_name = None
        if customer_id and sales:
            customer_name = sales[0].get('customer_name')
        
        if customer_name:
            title = f"Sales Report - {customer_name}"
        else:
            title = "Sales Report"
        
        embed = discord.Embed(
            title=title,
            description=f"Period: {start_date} to {end_date}",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Total Sales", value=f"${total_amount:.2f}", inline=True)
        embed.add_field(name="Number of Transactions", value=str(len(sales)), inline=True)
        embed.add_field(name="Items Sold", value=str(total_items), inline=True)
        
        # Add payment method breakdown
        if payment_totals:
            payment_text = ""
            for method, amount in sorted(payment_totals.items(), key=lambda x: x[1], reverse=True):
                percentage = (amount / total_amount) * 100 if total_amount > 0 else 0
                payment_text += f"{method}: ${amount:.2f} ({percentage:.1f}%)\n"
            
            embed.add_field(name="Payment Methods", value=payment_text, inline=False)
        
        # Add top products
        if sorted_products:
            products_text = ""
            for name, data in sorted_products[:5]:  # Top 5 products
                percentage = (data['revenue'] / total_amount) * 100 if total_amount > 0 else 0
                products_text += f"{name}: {data['quantity']} units, ${data['revenue']:.2f} ({percentage:.1f}%)\n"
            
            if len(sorted_products) > 5:
                products_text += f"... and {len(sorted_products) - 5} more products"
                
            embed.add_field(name="Top Products", value=products_text, inline=False)
        
        # Add recent sales
        if sales:
            recent_sales = sorted(sales, key=lambda s: s.get('date', ''), reverse=True)[:5]
            recent_text = ""
            for sale in recent_sales:
                customer = sale.get('customer_name', 'No customer')
                recent_text += f"{sale['date']} - {customer}: ${sale['total_amount']:.2f}\n"
            
            embed.add_field(name="Recent Sales", value=recent_text, inline=False)
        
        embed.set_footer(text=f"Full report saved as {filename}")
        
        logger.info(f"Sales report generated and saved to {csv_path}")
        return csv_path, embed
    
    async def generate_profit_loss_report(self,
                                         start_date: Optional[str] = None,
                                         end_date: Optional[str] = None) -> Tuple[str, discord.Embed]:
        """
        Generate a profit and loss report
        
        Args:
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            
        Returns:
            Tuple of (csv_path, discord_embed)
        """
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        if not start_date:
            # Default to 30 days before end date
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            start_date_obj = end_date_obj - timedelta(days=30)
            start_date = start_date_obj.strftime("%Y-%m-%d")
        
        # Get sales data
        sales_query = """
            SELECT date, total_amount
            FROM sales
            WHERE date BETWEEN ? AND ?
        """
        sales = self.db_manager.execute_query(sales_query, (start_date, end_date))
        
        # Get expense data
        expenses_query = """
            SELECT date, amount, category
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """
        expenses = self.db_manager.execute_query(expenses_query, (start_date, end_date))
        
        # Calculate totals
        total_sales = sum(sale.get('total_amount', 0) for sale in sales)
        total_expenses = sum(expense.get('amount', 0) for expense in expenses)
        net_profit = total_sales - total_expenses
        
        # Group expenses by category
        expense_categories = {}
        for expense in expenses:
            category = expense.get('category', 'Uncategorized')
            expense_categories[category] = expense_categories.get(category, 0) + expense.get('amount', 0)
        
        # Group data by date for time series
        date_range = []
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        
        while current_date <= end_date_obj:
            date_range.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)
        
        daily_data = {date: {'sales': 0, 'expenses': 0} for date in date_range}
        
        for sale in sales:
            sale_date = sale.get('date')
            if sale_date in daily_data:
                daily_data[sale_date]['sales'] += sale.get('total_amount', 0)
        
        for expense in expenses:
            expense_date = expense.get('date')
            if expense_date in daily_data:
                daily_data[expense_date]['expenses'] += expense.get('amount', 0)
        
        # Generate CSV report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"profit_loss_report_{timestamp}.csv"
        csv_path = os.path.join(self.reports_dir, filename)
        
        with open(csv_path, 'w', newline='') as csvfile:
            # Summary section
            writer = csv.writer(csvfile)
            writer.writerow(["Profit and Loss Report"])
            writer.writerow([f"Period: {start_date} to {end_date}"])
            writer.writerow([])
            writer.writerow(["Summary"])
            writer.writerow(["Total Sales", f"${total_sales:.2f}"])
            writer.writerow(["Total Expenses", f"${total_expenses:.2f}"])
            writer.writerow(["Net Profit/Loss", f"${net_profit:.2f}"])
            writer.writerow([])
            
            # Expense breakdown
            writer.writerow(["Expense Breakdown"])
            for category, amount in sorted(expense_categories.items(), key=lambda x: x[1], reverse=True):
                writer.writerow([category, f"${amount:.2f}"])
            writer.writerow([])
            
            # Daily breakdown
            writer.writerow(["Daily Breakdown"])
            writer.writerow(["Date", "Sales", "Expenses", "Net"])
            
            for date in date_range:
                sales_amount = daily_data[date]['sales']
                expenses_amount = daily_data[date]['expenses']
                net = sales_amount - expenses_amount
                writer.writerow([date, f"${sales_amount:.2f}", f"${expenses_amount:.2f}", f"${net:.2f}"])
        
        # Create Discord embed
        embed = discord.Embed(
            title="Profit and Loss Report",
            description=f"Period: {start_date} to {end_date}",
            color=discord.Color.gold()
        )
        
        # Add summary
        embed.add_field(name="Total Sales", value=f"${total_sales:.2f}", inline=True)
        embed.add_field(name="Total Expenses", value=f"${total_expenses:.2f}", inline=True)
        
        # Calculate profit margin
        profit_margin = (net_profit / total_sales) * 100 if total_sales > 0 else 0
        profit_color = "🟢" if net_profit >= 0 else "🔴"
        
        embed.add_field(
            name="Net Profit/Loss",
            value=f"{profit_color} ${net_profit:.2f} ({profit_margin:.1f}%)",
            inline=True
        )
        
        # Add expense breakdown
        if expense_categories:
            expense_text = ""
            for category, amount in sorted(expense_categories.items(), key=lambda x: x[1], reverse=True)[:5]:
                percentage = (amount / total_expenses) * 100 if total_expenses > 0 else 0
                expense_text += f"{category}: ${amount:.2f} ({percentage:.1f}%)\n"
            
            if len(expense_categories) > 5:
                expense_text += f"... and {len(expense_categories) - 5} more categories"
                
            embed.add_field(name="Top Expenses", value=expense_text, inline=False)
        
        # Add time period analysis
        # Group by week for better visualization in text
        weekly_data = {}
        for date, data in daily_data.items():
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            week_num = date_obj.strftime("%U")  # Week number
            week_key = f"Week {week_num}"
            
            if week_key not in weekly_data:
                weekly_data[week_key] = {'sales': 0, 'expenses': 0}
            
            weekly_data[week_key]['sales'] += data['sales']
            weekly_data[week_key]['expenses'] += data['expenses']
        
        if weekly_data:
            time_text = ""
            for week, data in sorted(weekly_data.items()):
                net = data['sales'] - data['expenses']
                indicator = "📈" if net >= 0 else "📉"
                time_text += f"{week}: {indicator} Sales: ${data['sales']:.2f}, Expenses: ${data['expenses']:.2f}, Net: ${net:.2f}\n"
            
            embed.add_field(name="Weekly Breakdown", value=time_text, inline=False)
        
        embed.set_footer(text=f"Full report saved as {filename}")
        
        logger.info(f"Profit and loss report generated and saved to {csv_path}")
        return csv_path, embed
        
    async def export_to_csv(self, data: List[Dict[str, Any]], filename: str) -> str:
        """
        Export data to a CSV file
        
        Args:
            data: List of dictionaries to export
            filename: Name of the CSV file
            
        Returns:
            Path to the CSV file
        """
        if not data:
            logger.warning("Attempted to export empty data to CSV")
            return ""
        
        # Ensure filename has .csv extension
        if not filename.lower().endswith('.csv'):
            filename += '.csv'
        
        csv_path = os.path.join(self.reports_dir, filename)
        
        with open(csv_path, 'w', newline='') as csvfile:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        
        logger.info(f"Data exported to CSV: {csv_path}")
        return csv_path
        
    async def schedule_report(self, report_type: str, channel_id: int,
                             interval_hours: int = 168, # Default to weekly (7 days)
                             callback: Optional[Callable] = None) -> str:
        """
        Schedule a recurring report
        
        Args:
            report_type: Type of report ('sales', 'expenses', 'inventory', 'profit', 'weekly_summary')
            channel_id: Discord channel ID to send the report to
            interval_hours: Interval in hours between reports (default: 168 hours/weekly)
            callback: Optional callback function to execute after sending the report
            
        Returns:
            ID of the scheduled report
        """
        # Generate a unique ID for this scheduled report
        report_id = f"{report_type}_{channel_id}_{datetime.now().timestamp()}"
        
        # Store the channel ID for this report type
        self.report_channels[report_type] = channel_id
        
        # Create and store the task
        task = asyncio.create_task(
            self._run_scheduled_report(report_id, report_type, channel_id, interval_hours, callback)
        )
        
        self.scheduled_reports[report_id] = {
            'task': task,
            'report_type': report_type,
            'channel_id': channel_id,
            'interval_hours': interval_hours,
            'next_run': datetime.now() + timedelta(hours=interval_hours),
            'created_at': datetime.now()
        }
        
        logger.info(f"Scheduled {report_type} report (ID: {report_id}) to run every {interval_hours} hours")
        return report_id
    
    async def cancel_scheduled_report(self, report_id: str) -> bool:
        """
        Cancel a scheduled report
        
        Args:
            report_id: ID of the scheduled report to cancel
            
        Returns:
            True if the report was cancelled, False otherwise
        """
        if report_id not in self.scheduled_reports:
            logger.warning(f"Attempted to cancel non-existent scheduled report: {report_id}")
            return False
        
        # Cancel the task
        self.scheduled_reports[report_id]['task'].cancel()
        
        # Remove from scheduled reports
        del self.scheduled_reports[report_id]
        
        logger.info(f"Cancelled scheduled report: {report_id}")
        return True
    
    async def list_scheduled_reports(self) -> List[Dict[str, Any]]:
        """
        List all scheduled reports
        
        Returns:
            List of dictionaries with scheduled report information
        """
        reports = []
        for report_id, report_info in self.scheduled_reports.items():
            reports.append({
                'report_id': report_id,
                'report_type': report_info['report_type'],
                'channel_id': report_info['channel_id'],
                'interval_hours': report_info['interval_hours'],
                'next_run': report_info['next_run'],
                'created_at': report_info['created_at']
            })
        
        return reports
    
    async def _run_scheduled_report(self, report_id: str, report_type: str,
                                   channel_id: int, interval_hours: int,
                                   callback: Optional[Callable] = None) -> None:
        """
        Run a scheduled report at the specified interval
        
        Args:
            report_id: ID of the scheduled report
            report_type: Type of report
            channel_id: Discord channel ID to send the report to
            interval_hours: Interval in hours between reports
            callback: Optional callback function to execute after sending the report
        """
        try:
            while True:
                # Wait for the specified interval
                await asyncio.sleep(interval_hours * 3600)  # Convert hours to seconds
                
                try:
                    # Generate and send the report
                    await self._generate_and_send_scheduled_report(report_type, channel_id)
                    
                    # Update next run time
                    if report_id in self.scheduled_reports:
                        self.scheduled_reports[report_id]['next_run'] = datetime.now() + timedelta(hours=interval_hours)
                    
                    # Execute callback if provided
                    if callback:
                        await callback(report_id, report_type, channel_id)
                        
                except Exception as e:
                    logger.error(f"Error running scheduled report {report_id}: {str(e)}")
                    
        except asyncio.CancelledError:
            logger.info(f"Scheduled report {report_id} was cancelled")
        except Exception as e:
            logger.error(f"Unexpected error in scheduled report {report_id}: {str(e)}")
    
    async def _generate_and_send_scheduled_report(self, report_type: str, channel_id: int) -> None:
        """
        Generate and send a scheduled report to a Discord channel
        
        Args:
            report_type: Type of report
            channel_id: Discord channel ID to send the report to
        """
        # Get the bot instance (this will be set when the bot calls this method)
        bot = self._get_bot_instance()
        if not bot:
            logger.error("Cannot send scheduled report: Bot instance not available")
            return
        
        # Get the channel
        channel = bot.get_channel(channel_id)
        if not channel:
            logger.error(f"Cannot send scheduled report: Channel {channel_id} not found")
            return
        
        # Determine date range (last 7 days by default)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        try:
            # Send a message indicating that the report is being generated
            message = await channel.send(f"Generating scheduled {report_type} report...")
            
            # Generate the appropriate report based on type
            if report_type == 'sales':
                csv_path, embed = await self.generate_sales_report(start_date, end_date)
                await message.delete()
                await channel.send(f"📊 **Scheduled Sales Report**", embed=embed, file=discord.File(csv_path))
                
            elif report_type == 'expenses':
                csv_path, embed = await self.generate_expense_report(start_date, end_date)
                await message.delete()
                await channel.send(f"💰 **Scheduled Expense Report**", embed=embed, file=discord.File(csv_path))
                
            elif report_type == 'inventory':
                csv_path, embed = await self.generate_inventory_report()
                await message.delete()
                await channel.send(f"📦 **Scheduled Inventory Report**", embed=embed, file=discord.File(csv_path))
                
            elif report_type == 'profit':
                csv_path, embed = await self.generate_profit_loss_report(start_date, end_date)
                await message.delete()
                await channel.send(f"📈 **Scheduled Profit & Loss Report**", embed=embed, file=discord.File(csv_path))
                
            elif report_type == 'weekly_summary':
                # Generate a comprehensive weekly summary report
                await message.delete()
                await self._generate_weekly_summary_report(channel)
                
            else:
                await message.edit(content=f"Unknown report type: {report_type}")
                
            logger.info(f"Successfully sent scheduled {report_type} report to channel {channel_id}")
            
        except Exception as e:
            logger.error(f"Error generating scheduled {report_type} report: {str(e)}")
            await channel.send(f"Error generating scheduled {report_type} report: {str(e)}")
    
    async def _generate_weekly_summary_report(self, channel) -> None:
        """
        Generate and send a comprehensive weekly summary report
        
        Args:
            channel: Discord channel to send the report to
        """
        # Determine date range (last 7 days)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        # Create the main embed for the weekly summary
        embed = discord.Embed(
            title="Weekly Business Summary",
            description=f"Summary for period: {start_date} to {end_date}",
            color=discord.Color.gold()
        )
        
        # Add timestamp
        embed.timestamp = datetime.now()
        
        try:
            # Get sales data
            sales_query = """
                SELECT date, total_amount
                FROM sales
                WHERE date BETWEEN ? AND ?
            """
            sales = self.db_manager.execute_query(sales_query, (start_date, end_date))
            
            # Get expense data
            expenses_query = """
                SELECT date, amount, category
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """
            expenses = self.db_manager.execute_query(expenses_query, (start_date, end_date))
            
            # Get inventory data
            inventory_query = """
                SELECT category, COUNT(*) as count, SUM(quantity) as total_quantity,
                       SUM(quantity * cost_price) as total_value
                FROM products
                GROUP BY category
            """
            inventory = self.db_manager.execute_query(inventory_query, ())
            
            # Calculate key metrics
            total_sales = sum(sale.get('total_amount', 0) for sale in sales)
            total_expenses = sum(expense.get('amount', 0) for expense in expenses)
            net_profit = total_sales - total_expenses
            profit_margin = (net_profit / total_sales) * 100 if total_sales > 0 else 0
            
            # Get previous period data for comparison
            prev_start_date = (datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
            prev_end_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
            
            prev_sales = self.db_manager.execute_query(sales_query, (prev_start_date, prev_end_date))
            prev_expenses = self.db_manager.execute_query(expenses_query, (prev_start_date, prev_end_date))
            
            prev_total_sales = sum(sale.get('total_amount', 0) for sale in prev_sales)
            prev_total_expenses = sum(expense.get('amount', 0) for expense in prev_expenses)
            prev_net_profit = prev_total_sales - prev_total_expenses
            
            # Calculate changes
            sales_change = ((total_sales - prev_total_sales) / prev_total_sales) * 100 if prev_total_sales > 0 else 0
            expenses_change = ((total_expenses - prev_total_expenses) / prev_total_expenses) * 100 if prev_total_expenses > 0 else 0
            profit_change = ((net_profit - prev_net_profit) / prev_net_profit) * 100 if prev_net_profit > 0 else 0
            
            # Add financial summary
            sales_indicator = "📈" if sales_change >= 0 else "📉"
            expenses_indicator = "📉" if expenses_change <= 0 else "📈"
            profit_indicator = "📈" if profit_change >= 0 else "📉"
            
            embed.add_field(
                name="Financial Summary",
                value=f"{sales_indicator} Sales: ${total_sales:.2f} ({sales_change:+.1f}%)\n"
                      f"{expenses_indicator} Expenses: ${total_expenses:.2f} ({expenses_change:+.1f}%)\n"
                      f"{profit_indicator} Net Profit: ${net_profit:.2f} ({profit_change:+.1f}%)\n"
                      f"Profit Margin: {profit_margin:.1f}%",
                inline=False
            )
            
            # Add inventory summary
            inventory_text = ""
            total_inventory_value = 0
            
            for category in inventory:
                cat_name = category.get('category', 'Unknown')
                cat_count = category.get('count', 0)
                cat_quantity = category.get('total_quantity', 0)
                cat_value = category.get('total_value', 0)
                total_inventory_value += cat_value
                
                inventory_text += f"**{cat_name}**: {cat_count} products, {cat_quantity} units, ${cat_value:.2f}\n"
            
            embed.add_field(
                name="Inventory Summary",
                value=f"Total Value: ${total_inventory_value:.2f}\n{inventory_text}",
                inline=False
            )
            
            # Add expense breakdown
            expense_categories = {}
            for expense in expenses:
                category = expense.get('category', 'Uncategorized')
                expense_categories[category] = expense_categories.get(category, 0) + expense.get('amount', 0)
            
            expense_text = ""
            for category, amount in sorted(expense_categories.items(), key=lambda x: x[1], reverse=True)[:5]:
                percentage = (amount / total_expenses) * 100 if total_expenses > 0 else 0
                expense_text += f"**{category}**: ${amount:.2f} ({percentage:.1f}%)\n"
            
            if expense_text:
                embed.add_field(
                    name="Top Expense Categories",
                    value=expense_text,
                    inline=False
                )
            
            # Get top selling products
            top_products_query = """
                SELECT p.name, SUM(si.quantity) as total_quantity,
                       SUM(si.quantity * si.price) as total_revenue
                FROM sale_items si
                JOIN products p ON si.product_id = p.product_id
                JOIN sales s ON si.sale_id = s.sale_id
                WHERE s.date BETWEEN ? AND ?
                GROUP BY p.product_id
                ORDER BY total_revenue DESC
                LIMIT 5
            """
            top_products = self.db_manager.execute_query(top_products_query, (start_date, end_date))
            
            if top_products:
                products_text = ""
                for product in top_products:
                    name = product.get('name', 'Unknown')
                    quantity = product.get('total_quantity', 0)
                    revenue = product.get('total_revenue', 0)
                    percentage = (revenue / total_sales) * 100 if total_sales > 0 else 0
                    
                    products_text += f"**{name}**: {quantity} units, ${revenue:.2f} ({percentage:.1f}%)\n"
                
                embed.add_field(
                    name="Top Selling Products",
                    value=products_text,
                    inline=False
                )
            
            # Add low stock warning
            low_stock_query = """
                SELECT name, sku, quantity
                FROM products
                WHERE quantity > 0 AND quantity <= 5
                ORDER BY quantity ASC
                LIMIT 10
            """
            low_stock = self.db_manager.execute_query(low_stock_query, ())
            
            if low_stock:
                low_stock_text = ""
                for product in low_stock:
                    name = product.get('name', 'Unknown')
                    sku = product.get('sku', 'N/A')
                    quantity = product.get('quantity', 0)
                    
                    low_stock_text += f"**{name}** (SKU: {sku}): {quantity} units\n"
                
                embed.add_field(
                    name="⚠️ Low Stock Warning",
                    value=low_stock_text,
                    inline=False
                )
            
            # Add out of stock warning
            out_of_stock_query = """
                SELECT name, sku
                FROM products
                WHERE quantity = 0
                LIMIT 10
            """
            out_of_stock = self.db_manager.execute_query(out_of_stock_query, ())
            
            if out_of_stock:
                out_of_stock_text = ""
                for product in out_of_stock:
                    name = product.get('name', 'Unknown')
                    sku = product.get('sku', 'N/A')
                    
                    out_of_stock_text += f"**{name}** (SKU: {sku})\n"
                
                if len(out_of_stock) > 10:
                    out_of_stock_text += f"...and {len(out_of_stock) - 10} more products"
                
                embed.add_field(
                    name="🚫 Out of Stock Products",
                    value=out_of_stock_text,
                    inline=False
                )
            
            # Add recommendations based on data
            recommendations = []
            
            # Check profit margin
            if profit_margin < 15:
                recommendations.append("Consider reviewing pricing strategy to improve profit margins")
            
            # Check inventory levels
            if low_stock:
                recommendations.append("Restock low inventory items soon to avoid stockouts")
            
            # Check expense categories
            largest_expense_category = max(expense_categories.items(), key=lambda x: x[1])[0] if expense_categories else None
            if largest_expense_category:
                recommendations.append(f"Review {largest_expense_category} expenses for potential cost savings")
            
            # Add sales trend recommendation
            if sales_change < 0:
                recommendations.append("Investigate declining sales trend and consider marketing initiatives")
            
            if recommendations:
                embed.add_field(
                    name="💡 Recommendations",
                    value="\n".join(f"• {rec}" for rec in recommendations),
                    inline=False
                )
            
            # Set footer
            embed.set_footer(text="AccountME Bot | Weekly Business Summary")
            
            # Send the report
            await channel.send(embed=embed)
            
            # Generate and send individual reports
            sales_csv, sales_embed = await self.generate_sales_report(start_date, end_date)
            await channel.send(file=discord.File(sales_csv))
            
            expense_csv, expense_embed = await self.generate_expense_report(start_date, end_date)
            await channel.send(file=discord.File(expense_csv))
            
            profit_csv, profit_embed = await self.generate_profit_loss_report(start_date, end_date)
            await channel.send(file=discord.File(profit_csv))
            
            inventory_csv, inventory_embed = await self.generate_inventory_report()
            await channel.send(file=discord.File(inventory_csv))
            
            logger.info(f"Successfully sent weekly summary report")
            
        except Exception as e:
            logger.error(f"Error generating weekly summary report: {str(e)}")
            await channel.send(f"Error generating weekly summary report: {str(e)}")
    
    def _get_bot_instance(self):
        """
        Get the bot instance
        
        This is a helper method to get the bot instance from the current context
        The bot instance will be set when the bot calls methods on this class
        """
        import sys
        for module in sys.modules.values():
            if hasattr(module, 'bot') and hasattr(module.bot, 'get_channel'):
                return module.bot
        return None