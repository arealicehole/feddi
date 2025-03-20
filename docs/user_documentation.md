# AccountME Discord Bot - User Documentation

This comprehensive guide will help you get the most out of the AccountME Discord bot for Trapper Dan Clothing. The bot is designed to help you manage your business finances, track inventory, record sales, and generate reports through an easy-to-use Discord interface.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Basic Commands](#basic-commands)
3. [Inventory Management](#inventory-management)
4. [Expense Tracking](#expense-tracking)
5. [Sales Recording](#sales-recording)
6. [Financial Reporting](#financial-reporting)
7. [System Management](#system-management)
8. [Conversational Reporting](#conversational-reporting)
9. [Tips and Best Practices](#tips-and-best-practices)
10. [Troubleshooting](#troubleshooting)

## Getting Started

### Bot Permissions

The AccountME bot requires certain permissions to function properly in your Discord server:

- Read Messages/View Channels
- Send Messages
- Embed Links
- Attach Files
- Read Message History
- Add Reactions

Ensure the bot has these permissions in the channels where you plan to use it.

### Command Prefix

The default command prefix is `!`. All commands should be prefixed with this character, for example: `!help`.

### Getting Help

To see a list of available commands, use:

```
!help
```

For detailed information about a specific command, use:

```
!help <command_name>
```

For example: `!help inventory` or `!help addexpense`

## Basic Commands

### Checking Bot Status

To check if the bot is responsive:

```
!ping
```

The bot should respond with "Pong!" and the current latency.

### Viewing Bot Information

To see information about the bot:

```
!info
```

This displays the bot version, uptime, and other system information.

## Inventory Management

The inventory management system allows you to track products across different categories (blanks, DTF prints, and other products).

### Adding Products

To add a new product to inventory:

```
!addproduct <category> <name> [attributes...]
```

The bot will guide you through the process with a series of questions based on the product category.

**Example:**
```
!addproduct blank "Gildan 5000 T-Shirt"
```

The bot will then ask for additional information such as:
- Size
- Color
- Manufacturer
- Style (manufacturer's product ID)
- Cost price
- Selling price
- Initial quantity

**Aliases:** `!newproduct`, `!additem`

### Viewing Inventory

To view details about a specific product:

```
!inventory <sku>
```

**Example:**
```
!inventory BLK-GIL-5000-BLK-L
```

To view a summary of all inventory:

```
!inventory
```

**Aliases:** `!inv`, `!stock`

### Adjusting Inventory

To adjust the quantity of a product:

```
!adjustinventory <sku> <quantity> [reason]
```

Use a positive number to add inventory, or a negative number to remove inventory.

**Example:**
```
!adjustinventory BLK-GIL-5000-BLK-L -5 "Sold at market"
```

**Aliases:** `!adjust`, `!updatestock`

### Updating Product Information

To update information about an existing product:

```
!updateproduct <sku>
```

The bot will guide you through the update process.

**Aliases:** `!editproduct`, `!modifyproduct`

### Deleting Products

To delete a product from inventory:

```
!deleteproduct <sku>
```

**Aliases:** `!removeproduct`, `!delproduct`

### Inventory Reports

To generate an inventory report:

```
!inventoryreport [category]
```

**Example:**
```
!inventoryreport blank
```

**Aliases:** `!invreport`, `!stockreport`

### Importing and Exporting Products

To import products from a CSV file:

```
!importproducts
```

Attach a CSV file to your message. The bot will provide the required format.

To export products to a CSV file:

```
!exportproducts [category]
```

## Expense Tracking

The expense tracking system allows you to record and categorize business expenses.

### Adding Expenses Manually

To add an expense manually:

```
!addexpense
```

The bot will guide you through the process with a series of questions:
- Date
- Vendor
- Amount
- Category
- Description (optional)

**Aliases:** `!newexpense`, `!expenseadd`

### Uploading Receipts

To upload a receipt image for automatic data extraction:

```
!uploadreceipt
```

Attach an image of the receipt to your message. The bot will extract information and ask you to verify it.

**Aliases:** `!receipt`, `!scanreceipt`

### Viewing Expenses

To view expenses:

```
!expenses [period] [category]
```

**Examples:**
```
!expenses month
!expenses year supplies
!expenses 2025-03
```

Valid periods: `today`, `week`, `month`, `year`, or a specific month in `YYYY-MM` format.

**Aliases:** `!exp`, `!viewexpenses`

### Editing Expenses

To edit an existing expense:

```
!editexpense <expense_id>
```

**Aliases:** `!updateexpense`, `!modifyexpense`

### Deleting Expenses

To delete an expense:

```
!deleteexpense <expense_id>
```

**Aliases:** `!removeexpense`, `!delexpense`

## Sales Recording

The sales recording system allows you to track sales transactions and customer information.

### Adding Sales

To record a new sale:

```
!addsale
```

The bot will guide you through the process:
1. Select or create a customer
2. Select products and quantities
3. Enter payment method
4. Add notes (optional)
5. Confirm the sale

**Aliases:** `!newsale`, `!recordsale`

### Viewing Sales

To view sales:

```
!sales [period] [customer]
```

**Examples:**
```
!sales week
!sales month "John Doe"
!sales 2025-03
```

Valid periods: `today`, `week`, `month`, `year`, or a specific month in `YYYY-MM` format.

**Aliases:** `!viewsales`, `!salesreport`

### Managing Customers

To add a new customer:

```
!addcustomer
```

To view customer information:

```
!customer <name or id>
```

To list all customers:

```
!customers
```

## Financial Reporting

The financial reporting system provides insights into your business finances.

### Financial Reports

To generate a financial report:

```
!financialreport <report_type> [period]
```

Report types:
- `sales` - Sales summary
- `expenses` - Expense breakdown
- `profit` - Profit and loss statement

**Examples:**
```
!financialreport sales month
!financialreport expenses year
!financialreport profit week
```

**Aliases:** `!finreport`, `!reportfinance`

### Exporting Data

To export financial data to a CSV file:

```
!exportdata <data_type> <start_date> <end_date>
```

Data types:
- `sales` - Sales transactions
- `expenses` - Expense records
- `inventory` - Current inventory

**Example:**
```
!exportdata sales 2025-01-01 2025-03-31
```

**Aliases:** `!export`, `!dataexport`

## System Management

The system management commands help you maintain the bot and its data.

### Backup Management

To create a manual backup:

```
!backup
```

**Aliases:** `!createbackup`, `!backupnow`

To list available backups:

```
!listbackups
```

**Aliases:** `!backups`, `!showbackups`

To restore from a backup:

```
!restore <backup_id>
```

**Aliases:** `!restorebackup`, `!dbrestore`

To create an inventory snapshot:

```
!inventorysnapshot
```

**Aliases:** `!snapshot`, `!invsnapshot`

To view backup status:

```
!backupstatus
```

**Aliases:** `!backupinfo`, `!backupstate`

### System Monitoring

To check system status:

```
!systemstatus
```

To check database integrity:

```
!databasecheck
```

To view error logs:

```
!errorlog
```

## Conversational Reporting

The conversational reporting feature allows you to request reports using natural language.

### Natural Language Queries

To generate a report using natural language:

```
!report <your question>
```

**Examples:**
```
!report Show me sales from last week
!report What were my expenses for March?
!report How much inventory do I have in the blank category?
!report What's my profit for this month?
```

**Aliases:** `!query`, `!askfor`

### Automated Reporting

To schedule automated reports:

```
!schedulereport <report_type> <interval> [channel]
```

**Example:**
```
!schedulereport weekly-summary weekly #reports
```

## Tips and Best Practices

### Inventory Management

- Use consistent naming conventions for products
- Regularly verify physical inventory against system records using `!verifyinventory`
- Use the notes field when adjusting inventory to maintain an audit trail
- Export inventory data regularly as a backup

### Expense Tracking

- Upload receipts as soon as possible after purchases
- Use consistent expense categories
- Add detailed descriptions for expenses when needed
- Verify AI-extracted data carefully before confirming

### Sales Recording

- Create customer profiles for repeat customers
- Record sales promptly to keep inventory accurate
- Use the notes field to record special circumstances
- Review sales reports weekly to identify trends

### System Maintenance

- Schedule regular backups
- Periodically check system status
- Keep the bot updated to the latest version
- Monitor disk space and database size

## Troubleshooting

### Common Issues

**Issue**: Command doesn't respond
**Solution**: Check if the bot is online with `!ping`. Ensure you're using the correct command prefix and syntax.

**Issue**: Receipt upload fails
**Solution**: Ensure the image is clear and well-lit. Try cropping the image to include only the receipt.

**Issue**: Inventory quantities are incorrect
**Solution**: Use `!verifyinventory` to reconcile system records with physical inventory.

**Issue**: Report generation is slow
**Solution**: Try narrowing the date range or adding more specific filters.

### Getting Help

If you encounter issues not covered in this documentation:

1. Use `!help <command>` for specific command help
2. Check the error message for guidance
3. Contact your system administrator for assistance

## Conclusion

The AccountME Discord bot provides a comprehensive solution for managing your business finances, inventory, and sales. By following this documentation, you'll be able to effectively use all the features the bot offers to streamline your business operations.

For developer documentation and technical details, please refer to the developer documentation.