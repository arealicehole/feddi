# AccountME Discord Bot

A Discord-based accounting bot for Trapper Dan Clothing. This bot processes expense receipts (via images and text), tracks inventory, manages sales, and generates reports through a conversational AI interface.

## Features

- **Expense Tracking**: Upload receipts as images for automatic data extraction or enter expenses manually
- **Inventory Management**: Track products across different categories (blanks, DTF prints, other)
- **Sales Recording**: Record sales transactions with customer information
- **Financial Reporting**: Generate reports for expenses, inventory, and sales
- **Data Backup**: Automatic backup of all data to a Discord channel

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Discord account with bot creation privileges
- Discord server where you have admin permissions

### Discord Bot Setup

For detailed instructions on setting up the Discord bot, please refer to the [Discord Bot Setup Guide](docs/discord_bot_setup.md).

Quick setup steps:

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application and add a bot
3. Enable required intents (Presence, Server Members, Message Content)
4. Copy your bot token and add it to the `.env` file
5. Set the required permissions:
   - Read Messages/View Channels
   - Send Messages
   - Embed Links
   - Attach Files
   - Read Message History
6. Generate an OAuth2 URL and use it to add the bot to your server

### Installation

#### Option 1: Standard Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/accountme-bot.git
   cd accountme-bot
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   ```

3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

4. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Copy the `.env.example` file to `.env` and update it with your Discord bot token and other settings:
   ```
   cp .env.example .env
   ```

6. Edit the `.env` file with your Discord bot token and other configuration values

#### Option 2: Docker Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/accountme-bot.git
   cd accountme-bot
   ```

2. Copy the `.env.example` file to `.env` and update it with your Discord bot token and other settings:
   ```
   cp .env.example .env
   ```

3. Build and run the Docker container:
   ```
   docker-compose up -d
   ```

#### Option 3: Akash Deployment

For detailed instructions on deploying the bot to Akash Network, please refer to the [Akash Deployment Guide](docs/akash_deployment.md).

### Running the Bot

#### Standard Installation
```
python bot/main.py
```

#### Docker Installation
```
docker-compose up -d
```

## Usage

### Basic Commands

- `!help` - Display help information
- `!ping` - Check if the bot is responsive

### Inventory Management

- `!addproduct <category> <name> [attributes...]` - Add a new product
- `!inventory <sku>` - View product details
- `!adjustinventory <sku> <quantity> [reason]` - Update inventory quantity
- `!inventoryreport [category]` - Generate inventory report

### Financial Management

- `!addexpense` - Start expense entry conversation
- `!uploadreceipt` - Upload and process receipt image
- `!expenses [period] [category]` - List expenses
- `!addsale` - Start sale entry conversation
- `!sales [period] [customer]` - List sales

### Reporting

- `!report <natural_language_query>` - Generate custom report
- `!export <report_type> <start_date> <end_date>` - Export data to CSV

### System Commands

- `!backup` - Manually trigger backup
- `!restore <backup_id>` - Restore from backup

## Development Phases

This project is being developed in multiple phases:

1. **Foundation Setup**: Basic bot structure, database design, and core framework
2. **Image Processing & OCR**: Receipt scanning and data extraction
3. **Inventory Management**: Product tracking and reporting
4. **Financial Tracking**: Expense and sales recording
5. **Conversational AI & Advanced Features**: Natural language reporting
6. **Optimization & Deployment**: Performance improvements and deployment to Akash

## Deployment Options

### Local Deployment

Run the bot directly on your local machine or server using Python or Docker.

### Akash Network Deployment

Deploy the bot to the Akash Network, a decentralized cloud computing marketplace, for 24/7 availability and cost-effective hosting. See the [Akash Deployment Guide](docs/akash_deployment.md) for detailed instructions.

Benefits of Akash deployment:
- 24/7 availability
- Cost-effective hosting
- Decentralized infrastructure
- Persistent storage for database and backups
- Automatic recovery from failures

## License

[MIT License](LICENSE)

## Contributors

- Your Name - Initial development