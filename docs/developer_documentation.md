# AccountME Discord Bot - Developer Documentation

This document provides comprehensive information for developers who will maintain or extend the AccountME Discord bot. It covers the project architecture, code organization, key components, database schema, extension points, testing approach, and common maintenance tasks.

## Table of Contents

1. [Project Architecture](#project-architecture)
2. [Code Organization](#code-organization)
3. [Key Components](#key-components)
4. [Database Schema](#database-schema)
5. [Extension Points](#extension-points)
6. [Testing Approach](#testing-approach)
7. [Common Maintenance Tasks](#common-maintenance-tasks)
8. [Troubleshooting Guide](#troubleshooting-guide)

## Project Architecture

The AccountME Discord bot is built using a modular architecture based on the Discord.py library. The architecture follows these key principles:

- **Separation of Concerns**: Each component has a specific responsibility
- **Modularity**: Features are organized into cogs for easy maintenance and extension
- **Data Abstraction**: Database operations are abstracted through a manager class
- **Event-Driven**: The bot responds to Discord events and user commands

### High-Level Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Discord API    │◄────┤  Bot Core       │◄────┤  Cogs          │
│                 │     │  (main.py)      │     │  (Feature      │
└─────────────────┘     └────────┬────────┘     │   Modules)     │
                                 │              └────────┬────────┘
                                 │                       │
                        ┌────────▼────────┐     ┌───────▼────────┐
                        │                 │     │                │
                        │  Utility        │◄────┤  Database      │
                        │  Classes        │     │  Manager       │
                        │                 │     │                │
                        └─────────────────┘     └────────┬───────┘
                                                         │
                                                ┌────────▼───────┐
                                                │                │
                                                │  SQLite        │
                                                │  Database      │
                                                │                │
                                                └────────────────┘
```

## Code Organization

The project follows a structured organization to maintain clarity and separation of concerns:

```
/
├── bot/                    # Core bot functionality
│   ├── __init__.py
│   ├── main.py             # Bot initialization and entry point
│   └── cogs/               # Feature modules
│       ├── __init__.py
│       ├── admin_cog.py    # Administrative commands
│       ├── backup_cog.py   # Backup functionality
│       ├── error_handler_cog.py  # Error handling
│       ├── event_logger_cog.py   # Event logging
│       ├── finance_cog.py  # Financial tracking
│       ├── help_cog.py     # Help command system
│       ├── inventory_cog.py # Inventory management
│       ├── system_monitor_cog.py # System monitoring
│       └── utility_cog.py  # Utility commands
├── data/                   # Data storage
│   └── database.db         # SQLite database
├── utils/                  # Utility classes
│   ├── __init__.py
│   ├── db_manager.py       # Database operations
│   ├── image_processor.py  # Image processing and OCR
│   └── report_generator.py # Report generation
├── tests/                  # Test suite
│   ├── conftest.py         # Test configuration
│   ├── performance_test.py # Performance testing
│   ├── test_config.py      # Configuration testing
│   ├── integration/        # Integration tests
│   │   └── test_db_integration.py
│   └── unit/               # Unit tests
│       ├── test_backup_cog.py
│       ├── test_bot.py
│       ├── test_db_manager.py
│       └── test_help_cog.py
├── docs/                   # Documentation
├── .env                    # Environment variables
├── .env.example            # Example environment variables
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose configuration
├── deploy.yaml             # Akash deployment manifest
└── README.md               # Project overview
```

## Key Components

### Bot Core (main.py)

The main.py file is the entry point for the bot. It handles:

- Bot initialization and configuration
- Loading cogs (feature modules)
- Event listeners for Discord events
- Error handling and logging setup
- Database connection management

Key functions:
- `setup()`: Initializes the bot and loads cogs
- `on_ready()`: Executes when the bot connects to Discord
- `main()`: Entry point that starts the bot

### Cogs (Feature Modules)

Cogs are modular components that encapsulate specific features:

- **admin_cog.py**: Administrative commands for bot management
- **backup_cog.py**: Database backup and restoration functionality
- **error_handler_cog.py**: Global error handling for commands
- **event_logger_cog.py**: Logging of Discord events
- **finance_cog.py**: Financial tracking (expenses, sales)
- **help_cog.py**: Custom help command system
- **inventory_cog.py**: Inventory management
- **system_monitor_cog.py**: System health monitoring
- **utility_cog.py**: General utility commands

Each cog follows a similar structure:
```python
class CogName(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Additional initialization
        
    # Command definitions
    @commands.command(name="command_name")
    async def command_name(self, ctx, *args):
        # Command implementation
        
    # Event listeners
    @commands.Cog.listener()
    async def on_event_name(self, *args):
        # Event handler implementation
```

### Utility Classes

- **db_manager.py**: Handles all database operations
- **image_processor.py**: Processes receipt images and extracts data
- **report_generator.py**: Generates financial and inventory reports

### Database Manager

The DatabaseManager class in db_manager.py provides an abstraction layer for all database operations:

- Connection management
- CRUD operations for all entities
- Transaction handling
- Migration management
- Backup and restore functionality

## Database Schema

The database uses SQLite with the following schema:

### Products Table
```sql
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL, -- 'blank', 'dtf', 'other'
    subcategory TEXT, -- 'for_pressing', 'ready_to_sell'
    manufacturer TEXT,
    vendor TEXT,
    style TEXT, -- manufacturer product ID
    color TEXT,
    size TEXT,
    sku TEXT UNIQUE,
    quantity INTEGER DEFAULT 0,
    cost_price REAL,
    selling_price REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### Expenses Table
```sql
CREATE TABLE expenses (
    expense_id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    vendor TEXT NOT NULL,
    amount REAL NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    receipt_url TEXT, -- Discord URL to receipt image
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### Customers Table
```sql
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    discord_id TEXT,
    name TEXT NOT NULL,
    contact_info TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### Sales Table
```sql
CREATE TABLE sales (
    sale_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    date TEXT NOT NULL,
    total_amount REAL NOT NULL,
    payment_method TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);
```

### Sale Items Table
```sql
CREATE TABLE sale_items (
    sale_item_id INTEGER PRIMARY KEY,
    sale_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    FOREIGN KEY (sale_id) REFERENCES sales(sale_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);
```

### Audit Log Table
```sql
CREATE TABLE audit_log (
    log_id INTEGER PRIMARY KEY,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    details TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### Backup Log Table
```sql
CREATE TABLE backup_log (
    backup_id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    location TEXT NOT NULL,
    size INTEGER NOT NULL,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### Inventory History Table
```sql
CREATE TABLE inventory_history (
    history_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    change_amount INTEGER NOT NULL,
    reason TEXT,
    user_id TEXT NOT NULL,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);
```

### Schema Version Table
```sql
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);
```

## Extension Points

The bot is designed to be easily extended. Here are the main extension points:

### Adding New Commands

To add new commands, create a new method in an existing cog or create a new cog:

1. Create a new command method with the `@commands.command()` decorator
2. Implement the command logic
3. Register the cog in main.py if it's a new cog

Example:
```python
@commands.command(name="newcommand")
async def new_command(self, ctx, arg1, arg2=None):
    """Command description for help text"""
    # Command implementation
    await ctx.send(f"Command executed with {arg1} and {arg2}")
```

### Adding New Database Functionality

To add new database functionality:

1. Add new methods to the DatabaseManager class in db_manager.py
2. Create database migrations if schema changes are needed
3. Update the relevant cogs to use the new functionality

Example migration:
```python
async def migrate_to_version_4(self):
    """Add new_table to the database"""
    await self.execute_query("""
        CREATE TABLE new_table (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            value TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    await self.execute_query("""
        INSERT INTO schema_version (version, description)
        VALUES (4, 'Added new_table');
    """)
```

### Adding New Report Types

To add new report types:

1. Add new methods to the ReportGenerator class in report_generator.py
2. Update the relevant cogs to use the new report types

Example:
```python
async def generate_new_report(self, start_date, end_date, filters=None):
    """Generate a new custom report"""
    # Report generation logic
    return {
        'title': 'New Report',
        'data': data,
        'summary': summary
    }
```

## Testing Approach

The project uses pytest for testing, with tests organized into unit and integration tests.

### Unit Tests

Unit tests focus on testing individual components in isolation:

- Located in tests/unit/
- Test individual functions and methods
- Use mocking to isolate components
- Fast execution for quick feedback

### Integration Tests

Integration tests verify that components work together correctly:

- Located in tests/integration/
- Test interactions between components
- Use a test database for database operations
- Verify end-to-end functionality

### Running Tests

To run the tests:

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run a specific test file
pytest tests/unit/test_db_manager.py

# Run with coverage report
pytest --cov=bot --cov=utils
```

### Test Fixtures

Common test fixtures are defined in conftest.py:

- `bot_fixture`: Creates a bot instance for testing
- `db_manager`: Creates a test database manager
- `test_db`: Sets up and tears down a test database

## Common Maintenance Tasks

### Adding a New Dependency

1. Add the dependency to requirements.txt
2. Update the Dockerfile if necessary
3. Update documentation if the dependency affects setup

### Database Migrations

To add a new database migration:

1. Add a new migration method in db_manager.py
2. Increment the schema version
3. Update the migration system to include the new migration

Example:
```python
async def migrate_to_version_5(self):
    """Add new_column to existing_table"""
    await self.execute_query("""
        ALTER TABLE existing_table
        ADD COLUMN new_column TEXT;
    """)
    await self.execute_query("""
        INSERT INTO schema_version (version, description)
        VALUES (5, 'Added new_column to existing_table');
    """)
```

### Updating Bot Permissions

If new features require additional Discord permissions:

1. Update the bot permissions in the Discord Developer Portal
2. Update the OAuth2 URL generation instructions in docs/discord_bot_setup.md
3. Update the README.md with the new permissions

### Deploying Updates

#### Local Deployment

1. Pull the latest code
2. Install any new dependencies
3. Restart the bot

```bash
git pull
pip install -r requirements.txt
python bot/main.py
```

#### Docker Deployment

1. Pull the latest code
2. Rebuild and restart the container

```bash
git pull
docker-compose down
docker-compose up -d --build
```

#### Akash Deployment

1. Update the deploy.yaml if necessary
2. Build and push the new Docker image
3. Update the deployment on Akash

See docs/akash_deployment.md for detailed instructions.

## Troubleshooting Guide

### Common Issues

#### Database Errors

**Issue**: "database is locked" error
**Solution**: This usually occurs when multiple connections try to write to the database simultaneously. The bot uses WAL journal mode to minimize this, but it can still happen. Check for long-running transactions or multiple bot instances.

**Issue**: "no such table" error
**Solution**: This indicates a migration issue. Check the schema_version table to see the current version and ensure all migrations have been applied.

#### Discord API Errors

**Issue**: "Forbidden" or "Missing Permissions" errors
**Solution**: The bot lacks the necessary permissions. Check the bot's role in the Discord server and ensure it has the required permissions.

**Issue**: Rate limiting errors
**Solution**: The bot is making too many requests to the Discord API. Implement rate limiting or add delays between operations.

#### Image Processing Errors

**Issue**: OCR fails to extract data from receipts
**Solution**: Check the image quality and ensure the X.AI API key is valid. You may need to adjust the confidence thresholds in image_processor.py.

### Debugging Techniques

#### Enabling Debug Logging

Set the LOG_LEVEL environment variable to DEBUG to enable detailed logging:

```
LOG_LEVEL=DEBUG
```

#### Database Inspection

Use the SQLite command-line tool to inspect the database:

```bash
sqlite3 data/database.db
```

Useful commands:
```sql
.tables                     -- List all tables
.schema table_name          -- Show table schema
SELECT * FROM schema_version; -- Check database version
```

#### Discord Event Debugging

Add temporary event listeners in main.py to debug specific Discord events:

```python
@bot.event
async def on_socket_response(payload):
    if payload.get('t') == 'EVENT_NAME':
        print(f"Received event: {payload}")
```

### Getting Help

If you encounter issues that aren't covered in this documentation:

1. Check the Discord.py documentation: https://discordpy.readthedocs.io/
2. Review the bot's logs for error messages
3. Check for similar issues in the project's issue tracker
4. Consult the Discord.py community for assistance

## Conclusion

This developer documentation provides a comprehensive overview of the AccountME Discord bot's architecture, code organization, and maintenance procedures. By following these guidelines, developers can effectively maintain and extend the bot's functionality.

For additional information, refer to the other documentation files in the docs/ directory, particularly the command reference guide and the Akash deployment guide.