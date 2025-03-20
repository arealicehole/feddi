# AccountME Discord Bot - Training Guide

This training guide is designed to help new users learn how to use the AccountME Discord bot effectively. It includes practical exercises, scenarios, and step-by-step instructions for common tasks.

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Basic Training Exercises](#basic-training-exercises)
4. [Inventory Management Training](#inventory-management-training)
5. [Expense Tracking Training](#expense-tracking-training)
6. [Sales Recording Training](#sales-recording-training)
7. [Reporting Training](#reporting-training)
8. [System Management Training](#system-management-training)
9. [Training Assessment](#training-assessment)
10. [Troubleshooting Practice](#troubleshooting-practice)

## Introduction

### About This Guide

This training guide is designed for trainers who are teaching new users how to use the AccountME Discord bot. It includes:

- **Practical Exercises**: Hands-on activities to reinforce learning
- **Scenarios**: Real-world situations to practice skills
- **Step-by-Step Instructions**: Detailed guidance for completing tasks
- **Assessment Questions**: To verify understanding

### Training Approach

We recommend the following approach for training:

1. **Demonstrate**: Show the trainee how to perform a task
2. **Guide**: Walk through the task together
3. **Observe**: Let the trainee perform the task independently
4. **Assess**: Verify understanding with assessment questions

### Training Environment Setup

Before beginning training, ensure:

1. The bot is properly installed and configured in a Discord server
2. The trainee has appropriate permissions in the server
3. You have sample data ready for training exercises
4. You have a dedicated channel for training to avoid disrupting production data

## Getting Started

### Exercise 1: Basic Bot Interaction

**Objective**: Familiarize the trainee with basic bot commands and responses.

**Steps**:

1. Have the trainee type `!ping` to check if the bot is responsive
2. Demonstrate the `!help` command to show available command categories
3. Show how to get help for a specific command with `!help inventory`
4. Explain the command prefix and basic syntax

**Assessment Questions**:
- What is the command prefix used by the bot?
- How do you get help for a specific command?
- How do you check if the bot is responsive?

### Exercise 2: Using the Help System

**Objective**: Teach the trainee how to effectively use the help system.

**Steps**:

1. Have the trainee explore different command categories with `!help`
2. Demonstrate how to get detailed help for a specific command
3. Show how to use the `!aliases` command to find alternative command names
4. Introduce the `!tutorial` command for interactive learning

**Assessment Questions**:
- How do you see all commands in the Inventory category?
- How do you find aliases for a command?
- How do you start an interactive tutorial?

## Basic Training Exercises

### Exercise 3: Command Navigation

**Objective**: Practice navigating between different commands and understanding their relationships.

**Scenario**: "You need to manage inventory for your clothing business."

**Steps**:

1. Have the trainee use `!help inventory` to see inventory-related commands
2. Ask them to get detailed help for the `!addproduct` command
3. Have them explore related commands mentioned in the help text
4. Discuss how these commands work together in a workflow

**Assessment Questions**:
- What commands would you use to add a new product and then adjust its quantity?
- How are inventory commands related to sales commands?
- What information do you need to provide when adding a new product?

## Inventory Management Training

### Exercise 4: Adding Products

**Objective**: Practice adding different types of products to inventory.

**Scenario**: "You've received a shipment of new t-shirts and need to add them to inventory."

**Steps**:

1. Demonstrate adding a blank product:
   ```
   !addproduct blank "Gildan 5000 T-Shirt"
   ```
2. Guide the trainee through the conversation flow, entering:
   - Size: L
   - Color: Black
   - Manufacturer: Gildan
   - Style: 5000
   - Cost price: 3.50
   - Selling price: 15.00
   - Initial quantity: 10

3. Have the trainee add another product independently:
   ```
   !addproduct blank "Bella Canvas 3001 T-Shirt"
   ```

**Assessment Questions**:
- What categories of products can you add to inventory?
- What information is required when adding a blank product?
- How would you add a DTF print to inventory?

### Exercise 5: Viewing and Adjusting Inventory

**Objective**: Practice viewing inventory and adjusting quantities.

**Scenario**: "You've sold 3 black Gildan t-shirts and need to update your inventory."

**Steps**:

1. Have the trainee view the current inventory:
   ```
   !inventory
   ```

2. Demonstrate looking up a specific product:
   ```
   !inventory BLK-GIL-5000-BLK-L
   ```

3. Guide the trainee through adjusting the inventory:
   ```
   !adjustinventory BLK-GIL-5000-BLK-L -3 "Sold at market"
   ```

4. Have them verify the updated quantity:
   ```
   !inventory BLK-GIL-5000-BLK-L
   ```

**Assessment Questions**:
- How do you check the current quantity of a product?
- How do you reduce inventory when products are sold?
- Why is it important to include a reason when adjusting inventory?

### Exercise 6: Inventory Reporting

**Objective**: Practice generating and interpreting inventory reports.

**Scenario**: "You need to check your current inventory levels for all blank products."

**Steps**:

1. Demonstrate generating an inventory report:
   ```
   !inventoryreport
   ```

2. Show how to filter by category:
   ```
   !inventoryreport blank
   ```

3. Explain how to interpret the report, including:
   - Current stock levels
   - Inventory value
   - Low stock warnings

4. Have the trainee generate a report for a different category

**Assessment Questions**:
- How do you generate a report for a specific product category?
- How can you identify products that are low in stock?
- What information is included in an inventory report?

## Expense Tracking Training

### Exercise 7: Manual Expense Entry

**Objective**: Practice entering expenses manually.

**Scenario**: "You've purchased supplies for $45.75 from Office Depot."

**Steps**:

1. Demonstrate starting the expense entry process:
   ```
   !addexpense
   ```

2. Guide the trainee through the conversation flow, entering:
   - Date: Today's date
   - Vendor: Office Depot
   - Amount: 45.75
   - Category: Supplies
   - Description: Printer ink and paper

3. Have the trainee add another expense independently

**Assessment Questions**:
- What information is required when adding an expense?
- What expense categories are available?
- How do you view expenses after adding them?

### Exercise 8: Receipt Processing

**Objective**: Practice uploading and processing receipt images.

**Scenario**: "You have a receipt from a recent purchase and want to add it to your expenses."

**Steps**:

1. Demonstrate uploading a receipt:
   ```
   !uploadreceipt
   ```
   (Attach a sample receipt image)

2. Show how to verify and correct the extracted information
3. Explain the verification process using reactions
4. Have the trainee upload and process another receipt

**Assessment Questions**:
- What types of information does the bot extract from receipts?
- How do you correct information if the bot makes a mistake?
- What should you do if the receipt image is unclear?

### Exercise 9: Viewing Expenses

**Objective**: Practice viewing and filtering expenses.

**Scenario**: "You need to review your expenses for the current month."

**Steps**:

1. Demonstrate viewing all expenses:
   ```
   !expenses
   ```

2. Show how to filter by period:
   ```
   !expenses month
   ```

3. Demonstrate filtering by category:
   ```
   !expenses month supplies
   ```

4. Have the trainee try different filtering combinations

**Assessment Questions**:
- How do you view expenses for a specific time period?
- How do you filter expenses by category?
- How would you view expenses from a specific vendor?

## Sales Recording Training

### Exercise 10: Recording Sales

**Objective**: Practice recording sales transactions.

**Scenario**: "A customer has purchased 2 t-shirts."

**Steps**:

1. Demonstrate starting the sale entry process:
   ```
   !addsale
   ```

2. Guide the trainee through the conversation flow:
   - Select or create a customer
   - Select products and quantities
   - Enter payment method
   - Add notes (optional)
   - Confirm the sale

3. Have the trainee record another sale independently

**Assessment Questions**:
- What information is required when recording a sale?
- How does recording a sale affect inventory?
- How do you add a new customer during the sale process?

### Exercise 11: Viewing Sales

**Objective**: Practice viewing and filtering sales records.

**Scenario**: "You need to review your sales for the current week."

**Steps**:

1. Demonstrate viewing all sales:
   ```
   !sales
   ```

2. Show how to filter by period:
   ```
   !sales week
   ```

3. Demonstrate filtering by customer:
   ```
   !sales week "John Doe"
   ```

4. Have the trainee try different filtering combinations

**Assessment Questions**:
- How do you view sales for a specific time period?
- How do you filter sales by customer?
- What information is shown in the sales summary?

## Reporting Training

### Exercise 12: Financial Reporting

**Objective**: Practice generating and interpreting financial reports.

**Scenario**: "You need to prepare a monthly financial report."

**Steps**:

1. Demonstrate generating a sales report:
   ```
   !financialreport sales month
   ```

2. Show how to generate an expense report:
   ```
   !financialreport expenses month
   ```

3. Demonstrate generating a profit and loss report:
   ```
   !financialreport profit month
   ```

4. Explain how to interpret each report
5. Have the trainee generate reports for different periods

**Assessment Questions**:
- What types of financial reports can you generate?
- How do you generate a report for a specific time period?
- What information is included in a profit and loss report?

### Exercise 13: Natural Language Reporting

**Objective**: Practice using the conversational reporting feature.

**Scenario**: "You want to know your sales performance for last week."

**Steps**:

1. Demonstrate using natural language queries:
   ```
   !report Show me sales from last week
   ```

2. Show how to ask about expenses:
   ```
   !report What were my expenses for this month?
   ```

3. Demonstrate asking about profit:
   ```
   !report What's my profit margin for March?
   ```

4. Have the trainee try their own natural language queries

**Assessment Questions**:
- How do you ask the bot for a custom report?
- What types of questions can you ask using the report command?
- How does the bot respond to ambiguous queries?

## System Management Training

### Exercise 14: Backup Management

**Objective**: Practice creating and managing backups.

**Scenario**: "You want to create a backup before making significant changes to your inventory."

**Steps**:

1. Demonstrate creating a manual backup:
   ```
   !backup
   ```

2. Show how to list available backups:
   ```
   !listbackups
   ```

3. Explain the backup rotation system and retention policy
4. Discuss when to create manual backups

**Assessment Questions**:
- How do you create a manual backup?
- How often are automatic backups created?
- How long are backups retained?

### Exercise 15: System Monitoring

**Objective**: Practice monitoring system health and performance.

**Scenario**: "You want to check the status of the bot and database."

**Steps**:

1. Demonstrate checking system status:
   ```
   !systemstatus
   ```

2. Show how to check database integrity:
   ```
   !databasecheck
   ```

3. Explain how to interpret the status information
4. Discuss what to do if issues are detected

**Assessment Questions**:
- How do you check if the bot is functioning properly?
- What information is shown in the system status?
- Who should you contact if you detect system issues?

## Training Assessment

### Comprehensive Assessment

Use these questions to assess the trainee's overall understanding of the AccountME bot:

1. **Basic Understanding**:
   - What is the purpose of the AccountME bot?
   - What are the main categories of commands?
   - How do you get help for a specific command?

2. **Inventory Management**:
   - How do you add a new product to inventory?
   - How do you adjust inventory quantities?
   - How do you generate an inventory report?

3. **Expense Tracking**:
   - How do you record a new expense?
   - How do you upload and process a receipt?
   - How do you view expenses for a specific period?

4. **Sales Recording**:
   - How do you record a new sale?
   - How does recording a sale affect inventory?
   - How do you view sales for a specific customer?

5. **Reporting**:
   - What types of reports can you generate?
   - How do you use natural language queries for reports?
   - How do you export data for external analysis?

6. **System Management**:
   - How do you create a backup?
   - How do you check system status?
   - What should you do if you encounter an error?

### Practical Assessment

Have the trainee complete these tasks independently:

1. Add a new product to inventory
2. Adjust the quantity of an existing product
3. Record a new expense
4. Record a new sale
5. Generate a financial report
6. Create a backup
7. Use a natural language query to get information

## Troubleshooting Practice

### Scenario 1: Command Not Working

**Scenario**: "You try to use a command, but the bot doesn't respond."

**Practice Steps**:
1. Check if the bot is online with `!ping`
2. Verify you're using the correct command syntax with `!help <command>`
3. Check if you have the necessary permissions
4. Try using an alias for the command

### Scenario 2: Incorrect Data Entry

**Scenario**: "You've entered incorrect information for a product."

**Practice Steps**:
1. Use `!inventory <sku>` to verify the current information
2. Use `!updateproduct <sku>` to update the information
3. Verify the changes with `!inventory <sku>`

### Scenario 3: Receipt Processing Issues

**Scenario**: "The bot is having trouble extracting information from a receipt."

**Practice Steps**:
1. Ensure the receipt image is clear and well-lit
2. Try cropping the image to include only the receipt
3. Use manual data entry as a fallback
4. Report the issue to the administrator for AI model improvement

## Conclusion

This training guide provides a structured approach to learning the AccountME Discord bot. By completing these exercises and scenarios, trainees will gain practical experience with all major features of the bot.

For additional information, refer to:
- User Documentation
- Command Reference Guide
- In-Discord help system (`!help`, `!tutorial`)

Remember that practice is key to becoming proficient with the bot. Encourage trainees to use the bot regularly and explore its features in a safe training environment before using it with production data.