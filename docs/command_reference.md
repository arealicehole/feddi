# AccountME Discord Bot - Command Reference Guide

This guide provides a comprehensive reference for all commands available in the AccountME Discord bot. Commands are organized by category for easy reference.

## Command Format

Commands use the following format:
```
!command <required_parameter> [optional_parameter]
```

- The default prefix is `!`
- Parameters in `<angle brackets>` are required
- Parameters in `[square brackets]` are optional

## Table of Contents

1. [Basic Commands](#basic-commands)
2. [Inventory Management](#inventory-management)
3. [Expense Tracking](#expense-tracking)
4. [Sales Management](#sales-management)
5. [Financial Reporting](#financial-reporting)
6. [Backup and System](#backup-and-system)
7. [Help and Information](#help-and-information)

---

## Basic Commands

### ping
**Description:** Check if the bot is responsive
**Usage:** `!ping`
**Response:** Returns "Pong!" with the current latency
**Permissions:** Any user

### info
**Description:** Display bot information
**Usage:** `!info`
**Response:** Shows version, uptime, and system information
**Permissions:** Any user

---

## Inventory Management

### addproduct
**Description:** Add a new product to inventory
**Usage:** `!addproduct <category> <name> [attributes...]`
**Parameters:**
- `category`: Product category (blank, dtf, other)
- `name`: Product name
- `attributes`: Additional attributes (optional, bot will prompt for required ones)
**Examples:**
- `!addproduct blank "Gildan 5000 T-Shirt"`
- `!addproduct dtf "Skull Design 8x10"`
**Aliases:** `!newproduct`, `!additem`
**Permissions:** Any user

### inventory
**Description:** View inventory information
**Usage:** 
- `!inventory` - View summary of all inventory
- `!inventory <sku>` - View details for a specific product
**Parameters:**
- `sku`: Product SKU (optional)
**Examples:**
- `!inventory`
- `!inventory BLK-GIL-5000-BLK-L`
**Aliases:** `!inv`, `!stock`
**Permissions:** Any user

### adjustinventory
**Description:** Adjust product quantity
**Usage:** `!adjustinventory <sku> <quantity> [reason]`
**Parameters:**
- `sku`: Product SKU
- `quantity`: Amount to adjust (positive to add, negative to remove)
- `reason`: Reason for adjustment (optional)
**Examples:**
- `!adjustinventory BLK-GIL-5000-BLK-L 10 "New shipment"`
- `!adjustinventory BLK-GIL-5000-BLK-L -5 "Sold at market"`
**Aliases:** `!adjust`, `!updatestock`
**Permissions:** Any user

### updateproduct
**Description:** Update product information
**Usage:** `!updateproduct <sku>`
**Parameters:**
- `sku`: Product SKU
**Examples:**
- `!updateproduct BLK-GIL-5000-BLK-L`
**Aliases:** `!editproduct`, `!modifyproduct`
**Permissions:** Any user

### deleteproduct
**Description:** Delete a product from inventory
**Usage:** `!deleteproduct <sku>`
**Parameters:**
- `sku`: Product SKU
**Examples:**
- `!deleteproduct BLK-GIL-5000-BLK-L`
**Aliases:** `!removeproduct`, `!delproduct`
**Permissions:** Any user

### inventoryreport
**Description:** Generate inventory report
**Usage:** `!inventoryreport [category]`
**Parameters:**
- `category`: Product category to filter by (optional)
**Examples:**
- `!inventoryreport`
- `!inventoryreport blank`
**Aliases:** `!invreport`, `!stockreport`
**Permissions:** Any user

### importproducts
**Description:** Import products from CSV file
**Usage:** `!importproducts`
**Note:** Attach a CSV file to your message
**Permissions:** Any user

### exportproducts
**Description:** Export products to CSV file
**Usage:** `!exportproducts [category]`
**Parameters:**
- `category`: Product category to filter by (optional)
**Examples:**
- `!exportproducts`
- `!exportproducts blank`
**Permissions:** Any user

### verifyinventory
**Description:** Start inventory verification process
**Usage:** `!verifyinventory`
**Permissions:** Any user

### inventory_history
**Description:** View history of inventory changes
**Usage:** `!inventory_history <sku> [limit]`
**Parameters:**
- `sku`: Product SKU
- `limit`: Number of records to show (optional, default: 10)
**Examples:**
- `!inventory_history BLK-GIL-5000-BLK-L`
- `!inventory_history BLK-GIL-5000-BLK-L 20`
**Permissions:** Any user

---

## Expense Tracking

### addexpense
**Description:** Add a new expense
**Usage:** `!addexpense`
**Note:** Bot will guide you through the expense entry process
**Aliases:** `!newexpense`, `!expenseadd`
**Permissions:** Any user

### uploadreceipt
**Description:** Upload and process receipt image
**Usage:** `!uploadreceipt`
**Note:** Attach an image of the receipt to your message
**Aliases:** `!receipt`, `!scanreceipt`
**Permissions:** Any user

### expenses
**Description:** View expense records
**Usage:** `!expenses [period] [category]`
**Parameters:**
- `period`: Time period (today, week, month, year, or YYYY-MM) (optional)
- `category`: Expense category to filter by (optional)
**Examples:**
- `!expenses`
- `!expenses month`
- `!expenses year supplies`
- `!expenses 2025-03`
**Aliases:** `!exp`, `!viewexpenses`
**Permissions:** Any user

### editexpense
**Description:** Edit an existing expense
**Usage:** `!editexpense <expense_id>`
**Parameters:**
- `expense_id`: ID of the expense to edit
**Examples:**
- `!editexpense 42`
**Aliases:** `!updateexpense`, `!modifyexpense`
**Permissions:** Any user

### deleteexpense
**Description:** Delete an expense
**Usage:** `!deleteexpense <expense_id>`
**Parameters:**
- `expense_id`: ID of the expense to delete
**Examples:**
- `!deleteexpense 42`
**Aliases:** `!removeexpense`, `!delexpense`
**Permissions:** Any user

---

## Sales Management

### addsale
**Description:** Record a new sale
**Usage:** `!addsale`
**Note:** Bot will guide you through the sale entry process
**Aliases:** `!newsale`, `!recordsale`
**Permissions:** Any user

### sales
**Description:** View sales records
**Usage:** `!sales [period] [customer]`
**Parameters:**
- `period`: Time period (today, week, month, year, or YYYY-MM) (optional)
- `customer`: Customer name or ID to filter by (optional)
**Examples:**
- `!sales`
- `!sales month`
- `!sales week "John Doe"`
- `!sales 2025-03`
**Aliases:** `!viewsales`, `!salesreport`
**Permissions:** Any user

### addcustomer
**Description:** Add a new customer
**Usage:** `!addcustomer`
**Note:** Bot will guide you through the customer entry process
**Permissions:** Any user

### customer
**Description:** View customer information
**Usage:** `!customer <name or id>`
**Parameters:**
- `name or id`: Customer name or ID
**Examples:**
- `!customer "John Doe"`
- `!customer 42`
**Permissions:** Any user

### customers
**Description:** List all customers
**Usage:** `!customers`
**Permissions:** Any user

### editsale
**Description:** Edit an existing sale
**Usage:** `!editsale <sale_id>`
**Parameters:**
- `sale_id`: ID of the sale to edit
**Examples:**
- `!editsale 42`
**Permissions:** Any user

### deletesale
**Description:** Delete a sale
**Usage:** `!deletesale <sale_id>`
**Parameters:**
- `sale_id`: ID of the sale to delete
**Examples:**
- `!deletesale 42`
**Permissions:** Any user

---

## Financial Reporting

### financialreport
**Description:** Generate financial report
**Usage:** `!financialreport <report_type> [period]`
**Parameters:**
- `report_type`: Type of report (sales, expenses, profit)
- `period`: Time period (today, week, month, year, or YYYY-MM) (optional)
**Examples:**
- `!financialreport sales month`
- `!financialreport expenses year`
- `!financialreport profit week`
**Aliases:** `!finreport`, `!reportfinance`
**Permissions:** Any user

### exportdata
**Description:** Export financial data to CSV
**Usage:** `!exportdata <data_type> <start_date> <end_date>`
**Parameters:**
- `data_type`: Type of data (sales, expenses, inventory)
- `start_date`: Start date in YYYY-MM-DD format
- `end_date`: End date in YYYY-MM-DD format
**Examples:**
- `!exportdata sales 2025-01-01 2025-03-31`
- `!exportdata expenses 2025-03-01 2025-03-31`
**Aliases:** `!export`, `!dataexport`
**Permissions:** Any user

### report
**Description:** Generate report using natural language
**Usage:** `!report <query>`
**Parameters:**
- `query`: Natural language query
**Examples:**
- `!report Show me sales from last week`
- `!report What were my expenses for March?`
**Aliases:** `!query`, `!askfor`
**Permissions:** Any user

### schedulereport
**Description:** Schedule automated reports
**Usage:** `!schedulereport <report_type> <interval> [channel]`
**Parameters:**
- `report_type`: Type of report (weekly-summary, monthly-finance, etc.)
- `interval`: Frequency (daily, weekly, monthly)
- `channel`: Channel to send reports to (optional)
**Examples:**
- `!schedulereport weekly-summary weekly #reports`
- `!schedulereport monthly-finance monthly`
**Permissions:** Server administrator

### generatereport
**Description:** Generate on-demand report
**Usage:** `!generatereport <report_type>`
**Parameters:**
- `report_type`: Type of report (weekly-summary, monthly-finance, etc.)
**Examples:**
- `!generatereport weekly-summary`
**Permissions:** Any user

### setreportchannel
**Description:** Set default channel for reports
**Usage:** `!setreportchannel <channel>`
**Parameters:**
- `channel`: Channel to send reports to
**Examples:**
- `!setreportchannel #reports`
**Permissions:** Server administrator

---

## Backup and System

### backup
**Description:** Create manual backup
**Usage:** `!backup`
**Aliases:** `!createbackup`, `!backupnow`
**Permissions:** Server administrator

### listbackups
**Description:** List available backups
**Usage:** `!listbackups`
**Aliases:** `!backups`, `!showbackups`
**Permissions:** Server administrator

### restore
**Description:** Restore from backup
**Usage:** `!restore <backup_id>`
**Parameters:**
- `backup_id`: ID of the backup to restore
**Examples:**
- `!restore 42`
**Aliases:** `!restorebackup`, `!dbrestore`
**Permissions:** Server administrator

### inventorysnapshot
**Description:** Create inventory snapshot
**Usage:** `!inventorysnapshot`
**Aliases:** `!snapshot`, `!invsnapshot`
**Permissions:** Any user

### backupstatus
**Description:** View backup system status
**Usage:** `!backupstatus`
**Aliases:** `!backupinfo`, `!backupstate`
**Permissions:** Server administrator

### backupchannel
**Description:** Configure backup destination channel
**Usage:** `!backupchannel <channel>`
**Parameters:**
- `channel`: Channel to send backups to
**Examples:**
- `!backupchannel #backups`
**Permissions:** Server administrator

### backupschedule
**Description:** Set backup schedule
**Usage:** `!backupschedule <interval_hours>`
**Parameters:**
- `interval_hours`: Hours between backups
**Examples:**
- `!backupschedule 24`
**Permissions:** Server administrator

### backupretention
**Description:** Set backup retention policy
**Usage:** `!backupretention <days>`
**Parameters:**
- `days`: Number of days to keep backups
**Examples:**
- `!backupretention 30`
**Permissions:** Server administrator

### systemstatus
**Description:** Check system status
**Usage:** `!systemstatus`
**Permissions:** Server administrator

### databasecheck
**Description:** Check database integrity
**Usage:** `!databasecheck`
**Permissions:** Server administrator

### errorlog
**Description:** View error logs
**Usage:** `!errorlog [limit]`
**Parameters:**
- `limit`: Number of errors to show (optional, default: 10)
**Examples:**
- `!errorlog`
- `!errorlog 20`
**Permissions:** Server administrator

### adminnotify
**Description:** Configure admin notification channel
**Usage:** `!adminnotify <channel>`
**Parameters:**
- `channel`: Channel for admin notifications
**Examples:**
- `!adminnotify #admin-alerts`
**Permissions:** Server administrator

### healthcheck
**Description:** Perform system health check
**Usage:** `!healthcheck`
**Permissions:** Server administrator

### healthinterval
**Description:** Set health check interval
**Usage:** `!healthinterval <minutes>`
**Parameters:**
- `minutes`: Minutes between health checks
**Examples:**
- `!healthinterval 60`
**Permissions:** Server administrator

### backupcloud
**Description:** Configure cloud storage for backups
**Usage:** `!backupcloud <provider> <credentials>`
**Parameters:**
- `provider`: Cloud provider (google, onedrive)
- `credentials`: Authentication credentials
**Examples:**
- `!backupcloud google`
**Permissions:** Server administrator

### backupverify
**Description:** Verify backup integrity
**Usage:** `!backupverify <backup_id>`
**Parameters:**
- `backup_id`: ID of the backup to verify
**Examples:**
- `!backupverify 42`
**Permissions:** Server administrator

---

## Help and Information

### help
**Description:** Display help information
**Usage:** 
- `!help` - Show general help
- `!help <command>` - Show help for specific command
**Parameters:**
- `command`: Command name (optional)
**Examples:**
- `!help`
- `!help inventory`
**Permissions:** Any user

### tutorial
**Description:** Start interactive tutorial
**Usage:** `!tutorial [topic]`
**Parameters:**
- `topic`: Tutorial topic (optional)
**Examples:**
- `!tutorial`
- `!tutorial inventory`
**Permissions:** Any user

### aliases
**Description:** Show command aliases
**Usage:** `!aliases [command]`
**Parameters:**
- `command`: Command name (optional)
**Examples:**
- `!aliases`
- `!aliases inventory`
**Permissions:** Any user

---

## Permission Levels

- **Any user**: All server members can use these commands
- **Server administrator**: Only users with administrator permissions can use these commands

## Command Prefix

The default command prefix is `!`. All commands must be prefixed with this character.

## Additional Notes

- Commands that start conversations (like `!addproduct`, `!addsale`, etc.) will guide you through the process with a series of prompts
- Many commands support filtering by date ranges, categories, or other parameters
- Use `!help <command>` for detailed information about any command
- Command aliases provide alternative ways to invoke the same command