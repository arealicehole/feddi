"""
Database Manager for AccountME Discord Bot
Handles all database operations including connection management and CRUD operations
"""

import os
import sqlite3
import logging
import json
import time
import functools
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

logger = logging.getLogger("accountme_bot.db_manager")

class DatabaseManager:
    """
    Database manager class for handling all database operations
    Implements connection pooling and CRUD operations for all tables
    """
    
    # Current database schema version
    CURRENT_VERSION = 3
    
    def __init__(self, db_path: str = "data/database.db"):
        """
        Initialize the database manager
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.connection = None
        
        # Initialize cache
        self.cache = {}
        self.cache_ttl = {}  # Time-to-live for cache entries
        self.default_ttl = 300  # Default TTL in seconds (5 minutes)
        self.max_cache_size = 100  # Maximum number of items in cache
        
        self._initialize_database()
        self._apply_migrations()
        
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a database connection, creating it if necessary
        
        Returns:
            sqlite3.Connection: Database connection object
        """
        if self.connection is None:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Create connection with row factory for dictionary-like results
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            
            # Enable foreign keys
            self.connection.execute("PRAGMA foreign_keys = ON")
            
            # Set journal mode to WAL for better concurrency
            self.connection.execute("PRAGMA journal_mode = WAL")
            
            # Set synchronous mode to NORMAL for better performance
            self.connection.execute("PRAGMA synchronous = NORMAL")
            
            # Set cache size to 10000 pages (about 40MB)
            self.connection.execute("PRAGMA cache_size = 10000")
        
        return self.connection
    
    def _initialize_database(self) -> None:
        """
        Initialize the database by creating tables if they don't exist
        """
        logger.info(f"Initializing database at {self.db_path}")
        
        # SQL for creating all tables
        create_tables_sql = """
        -- Schema Version Table for Migrations
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL,
            description TEXT
        );
        
        -- Products Table
        CREATE TABLE IF NOT EXISTS products (
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

        -- Expenses Table
        CREATE TABLE IF NOT EXISTS expenses (
            expense_id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            vendor TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            receipt_image TEXT, -- path or URL to receipt image
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- Customers Table
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY,
            discord_id TEXT,
            name TEXT NOT NULL,
            contact_info TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- Sales Table
        CREATE TABLE IF NOT EXISTS sales (
            sale_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            date TEXT NOT NULL,
            total_amount REAL NOT NULL,
            payment_method TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );

        -- Sale Items Table
        CREATE TABLE IF NOT EXISTS sale_items (
            sale_item_id INTEGER PRIMARY KEY,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales(sale_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );

        -- Audit Log Table
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id INTEGER PRIMARY KEY,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            details TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        );

        -- Backup Log Table
        CREATE TABLE IF NOT EXISTS backup_log (
            backup_id INTEGER PRIMARY KEY,
            filename TEXT NOT NULL,
            location TEXT NOT NULL,
            size INTEGER NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        );
        
        -- Inventory History Table
        CREATE TABLE IF NOT EXISTS inventory_history (
            history_id INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL,
            previous_quantity INTEGER NOT NULL,
            new_quantity INTEGER NOT NULL,
            change_amount INTEGER NOT NULL,
            reason TEXT,
            user_id TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
        """
        
        conn = self._get_connection()
        conn.executescript(create_tables_sql)
        conn.commit()
        logger.info("Database initialized successfully")
    
    def close(self) -> None:
        """
        Close the database connection
        """
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
    # Cache management
    
    def _cache_key(self, func_name: str, args: tuple, kwargs: Dict[str, Any]) -> str:
        """
        Generate a cache key from function name and arguments
        
        Args:
            func_name: Name of the function
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            Cache key as a string
        """
        # Convert args and kwargs to a string representation
        args_str = str(args)
        kwargs_str = str(sorted(kwargs.items()))
        return f"{func_name}:{args_str}:{kwargs_str}"
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache if it exists and is not expired
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if key in self.cache:
            # Check if the cache entry has expired
            if key in self.cache_ttl and self.cache_ttl[key] < time.time():
                # Remove expired entry
                del self.cache[key]
                del self.cache_ttl[key]
                return None
            
            return self.cache[key]
        
        return None
    
    def _set_in_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache with an optional TTL
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (optional)
        """
        # Manage cache size - remove oldest entry if cache is full
        if len(self.cache) >= self.max_cache_size:
            oldest_key = min(self.cache_ttl.keys(), key=lambda k: self.cache_ttl[k])
            del self.cache[oldest_key]
            del self.cache_ttl[oldest_key]
        
        # Set the value in cache
        self.cache[key] = value
        
        # Set TTL
        ttl_value = ttl if ttl is not None else self.default_ttl
        self.cache_ttl[key] = time.time() + ttl_value
    
    def _invalidate_cache(self, pattern: Optional[str] = None) -> None:
        """
        Invalidate cache entries matching a pattern
        
        Args:
            pattern: Pattern to match cache keys (optional)
        """
        if pattern is None:
            # Clear entire cache
            self.cache.clear()
            self.cache_ttl.clear()
            logger.debug("Cache cleared")
        else:
            # Clear entries matching pattern
            keys_to_remove = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self.cache[key]
                if key in self.cache_ttl:
                    del self.cache_ttl[key]
            
            logger.debug(f"Cache entries matching '{pattern}' cleared ({len(keys_to_remove)} entries)")
    
    def cached(self, ttl: Optional[int] = None):
        """
        Decorator for caching function results
        
        Args:
            ttl: Time-to-live in seconds (optional)
            
        Returns:
            Decorated function
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                key = self._cache_key(func.__name__, args, kwargs)
                
                # Try to get from cache
                cached_value = self._get_from_cache(key)
                if cached_value is not None:
                    logger.debug(f"Cache hit for {key}")
                    return cached_value
                
                # Call the function
                result = func(*args, **kwargs)
                
                # Cache the result
                self._set_in_cache(key, result, ttl)
                logger.debug(f"Cache miss for {key}, result cached")
                
                return result
            return wrapper
        return decorator
    
    # Generic CRUD operations
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return the results
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            List of dictionaries representing rows
        """
        conn = self._get_connection()
        cursor = conn.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        return results
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """
        Execute an UPDATE, INSERT, or DELETE query
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Number of rows affected
        """
        conn = self._get_connection()
        cursor = conn.execute(query, params)
        conn.commit()
        
        # Invalidate cache for affected table
        table_name = None
        if query.strip().upper().startswith("UPDATE "):
            table_name = query.strip().split()[1]
        elif query.strip().upper().startswith("INSERT INTO "):
            table_name = query.strip().split()[2]
        elif query.strip().upper().startswith("DELETE FROM "):
            table_name = query.strip().split()[2]
        
        if table_name:
            self._invalidate_cache(table_name)
        
        return cursor.rowcount
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """
        Insert a row into a table
        
        Args:
            table: Table name
            data: Dictionary of column names and values
            
        Returns:
            ID of the inserted row
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        conn = self._get_connection()
        cursor = conn.execute(query, tuple(data.values()))
        conn.commit()
        
        # Invalidate cache for this table
        self._invalidate_cache(table)
        
        return cursor.lastrowid
    
    def update(self, table: str, data: Dict[str, Any], condition: str, params: tuple) -> int:
        """
        Update rows in a table
        
        Args:
            table: Table name
            data: Dictionary of column names and values to update
            condition: WHERE clause
            params: Parameters for the WHERE clause
            
        Returns:
            Number of rows affected
        """
        set_clause = ', '.join([f"{key} = ?" for key in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {condition}"
        
        all_params = tuple(data.values()) + params
        
        conn = self._get_connection()
        cursor = conn.execute(query, all_params)
        conn.commit()
        
        # Invalidate cache for this table
        self._invalidate_cache(table)
        
        return cursor.rowcount
    
    def delete(self, table: str, condition: str, params: tuple) -> int:
        """
        Delete rows from a table
        
        Args:
            table: Table name
            condition: WHERE clause
            params: Parameters for the WHERE clause
            
        Returns:
            Number of rows affected
        """
        query = f"DELETE FROM {table} WHERE {condition}"
        
        conn = self._get_connection()
        cursor = conn.execute(query, params)
        conn.commit()
        
        # Invalidate cache for this table
        self._invalidate_cache(table)
        
        return cursor.rowcount
    
    def get_by_id(self, table: str, id_column: str, id_value: int) -> Optional[Dict[str, Any]]:
        """
        Get a row by its ID
        
        Args:
            table: Table name
            id_column: Name of the ID column
            id_value: ID value to look for
            
        Returns:
            Row as a dictionary, or None if not found
        """
        # Use the cached decorator for this frequently used method
        @self.cached()
        def _get_by_id_impl(table, id_column, id_value):
            query = f"SELECT * FROM {table} WHERE {id_column} = ?"
            results = self.execute_query(query, (id_value,))
            return results[0] if results else None
        
        return _get_by_id_impl(table, id_column, id_value)
    
    # Table-specific CRUD operations
    
    # Product operations
    
    def add_product(self, product_data: Dict[str, Any]) -> int:
        """
        Add a new product to the database
        
        Args:
            product_data: Dictionary containing product data
            
        Returns:
            ID of the new product
        """
        # Add updated_at timestamp
        product_data['updated_at'] = datetime.now().isoformat()
        
        return self.insert('products', product_data)
    
    def update_product(self, product_id: int, product_data: Dict[str, Any]) -> bool:
        """
        Update an existing product
        
        Args:
            product_id: ID of the product to update
            product_data: Dictionary containing updated product data
            
        Returns:
            True if successful, False if product not found
        """
        # Add updated_at timestamp
        product_data['updated_at'] = datetime.now().isoformat()
        
        # Explicitly invalidate cache for this specific product
        self._invalidate_cache(f"_get_product_by_sku_impl")
        self._invalidate_cache(f"_get_by_id_impl")
        
        rows_affected = self.update('products', product_data, 'product_id = ?', (product_id,))
        return rows_affected > 0
    
    def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a product by ID
        
        Args:
            product_id: ID of the product
            
        Returns:
            Product data as a dictionary, or None if not found
        """
        return self.get_by_id('products', 'product_id', product_id)
    
    def get_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """
        Get a product by SKU
        
        Args:
            sku: Product SKU
            
        Returns:
            Product data as a dictionary, or None if not found
        """
        # Use the cached decorator for this frequently used method
        @self.cached()
        def _get_product_by_sku_impl(sku):
            query = "SELECT * FROM products WHERE sku = ?"
            results = self.execute_query(query, (sku,))
            return results[0] if results else None
        
        return _get_product_by_sku_impl(sku)
    
    def list_products(self, category: Optional[str] = None,
                     subcategory: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List products with optional filtering
        
        Args:
            category: Filter by category (optional)
            subcategory: Filter by subcategory (optional)
            
        Returns:
            List of products as dictionaries
        """
        # Use the cached decorator for this frequently used method
        @self.cached()
        def _list_products_impl(category, subcategory):
            query = "SELECT * FROM products"
            params = []
            
            # Add filters if provided
            where_clauses = []
            if category:
                where_clauses.append("category = ?")
                params.append(category)
            
            if subcategory:
                where_clauses.append("subcategory = ?")
                params.append(subcategory)
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY name"
            
            return self.execute_query(query, tuple(params))
        
        return _list_products_impl(category, subcategory)
    
    def adjust_product_quantity(self, product_id: int, quantity_change: int,
                               user_id: str, reason: Optional[str] = None) -> bool:
        """
        Adjust the quantity of a product
        
        Args:
            product_id: ID of the product
            quantity_change: Amount to change (positive for increase, negative for decrease)
            user_id: Discord ID of the user making the change
            reason: Reason for the adjustment (optional)
            
        Returns:
            True if successful, False if product not found
        """
        conn = self._get_connection()
        
        try:
            # Get current quantity
            product = self.get_product(product_id)
            if not product:
                return False
            
            current_quantity = product['quantity']
            new_quantity = current_quantity + quantity_change
            
            # Update quantity
            self.update('products',
                       {'quantity': new_quantity, 'updated_at': datetime.now().isoformat()},
                       'product_id = ?',
                       (product_id,))
            
            # Log the adjustment in audit log
            details = f"Quantity changed from {current_quantity} to {new_quantity}"
            if reason:
                details += f". Reason: {reason}"
            
            self.log_audit('adjust_quantity', 'product', product_id, user_id, details)
            
            # Record in inventory history
            self.add_inventory_history(
                product_id,
                current_quantity,
                new_quantity,
                quantity_change,
                reason,
                user_id
            )
            
            return True
        except Exception as e:
            logger.error(f"Error adjusting product quantity: {str(e)}")
            conn.rollback()
            return False
            
    def add_inventory_history(self, product_id: int, previous_quantity: int,
                             new_quantity: int, change_amount: int,
                             reason: Optional[str], user_id: str) -> int:
        """
        Add an entry to the inventory history
        
        Args:
            product_id: ID of the product
            previous_quantity: Previous quantity before change
            new_quantity: New quantity after change
            change_amount: Amount of change (positive or negative)
            reason: Reason for the change (optional)
            user_id: Discord ID of the user making the change
            
        Returns:
            ID of the new history entry
        """
        data = {
            'product_id': product_id,
            'previous_quantity': previous_quantity,
            'new_quantity': new_quantity,
            'change_amount': change_amount,
            'reason': reason,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat()
        }
        
        return self.insert('inventory_history', data)
        
    def get_inventory_history(self, product_id: Optional[int] = None,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None,
                             limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get inventory history with optional filtering
        
        Args:
            product_id: Filter by product ID (optional)
            start_date: Filter by start date (YYYY-MM-DD) (optional)
            end_date: Filter by end date (YYYY-MM-DD) (optional)
            limit: Maximum number of records to return
            
        Returns:
            List of inventory history entries as dictionaries
        """
        # Use the cached decorator for this method with a shorter TTL
        @self.cached(ttl=60)  # 1 minute TTL
        def _get_inventory_history_impl(product_id, start_date, end_date, limit):
            query = """
            SELECT h.*, p.name as product_name, p.sku, p.category
            FROM inventory_history h
            JOIN products p ON h.product_id = p.product_id
            """
            params = []
            
            # Add filters if provided
            where_clauses = []
            if product_id:
                where_clauses.append("h.product_id = ?")
                params.append(product_id)
            
            if start_date:
                where_clauses.append("h.timestamp >= ?")
                params.append(f"{start_date}T00:00:00")
            
            if end_date:
                where_clauses.append("h.timestamp <= ?")
                params.append(f"{end_date}T23:59:59")
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY h.timestamp DESC LIMIT ?"
            params.append(limit)
            
            return self.execute_query(query, tuple(params))
        
        return _get_inventory_history_impl(product_id, start_date, end_date, limit)
        
    def get_product_inventory_history(self, product_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get inventory history for a specific product
        
        Args:
            product_id: Product ID
            limit: Maximum number of records to return
            
        Returns:
            List of inventory history entries for the product
        """
        return self.get_inventory_history(product_id=product_id, limit=limit)
    
    # Expense operations
    
    def add_expense(self, expense_data: Dict[str, Any]) -> int:
        """
        Add a new expense to the database
        
        Args:
            expense_data: Dictionary containing expense data
            
        Returns:
            ID of the new expense
        """
        return self.insert('expenses', expense_data)
    
    def update_expense(self, expense_id: int, expense_data: Dict[str, Any]) -> bool:
        """
        Update an existing expense
        
        Args:
            expense_id: ID of the expense to update
            expense_data: Dictionary containing updated expense data
            
        Returns:
            True if successful, False if expense not found
        """
        rows_affected = self.update('expenses', expense_data, 'expense_id = ?', (expense_id,))
        return rows_affected > 0
    
    def get_expense(self, expense_id: int) -> Optional[Dict[str, Any]]:
        """
        Get an expense by ID
        
        Args:
            expense_id: ID of the expense
            
        Returns:
            Expense data as a dictionary, or None if not found
        """
        return self.get_by_id('expenses', 'expense_id', expense_id)
    
    def list_expenses(self, start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List expenses with optional filtering
        
        Args:
            start_date: Filter by start date (YYYY-MM-DD) (optional)
            end_date: Filter by end date (YYYY-MM-DD) (optional)
            category: Filter by category (optional)
            
        Returns:
            List of expenses as dictionaries
        """
        # Use the cached decorator for this method with a shorter TTL
        @self.cached(ttl=60)  # 1 minute TTL
        def _list_expenses_impl(start_date, end_date, category):
            query = "SELECT * FROM expenses"
            params = []
            
            # Add filters if provided
            where_clauses = []
            if start_date:
                where_clauses.append("date >= ?")
                params.append(start_date)
            
            if end_date:
                where_clauses.append("date <= ?")
                params.append(end_date)
            
            if category:
                where_clauses.append("category = ?")
                params.append(category)
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY date DESC"
            
            return self.execute_query(query, tuple(params))
        
        return _list_expenses_impl(start_date, end_date, category)
    
    # Customer operations
    
    def add_customer(self, customer_data: Dict[str, Any]) -> int:
        """
        Add a new customer to the database
        
        Args:
            customer_data: Dictionary containing customer data
            
        Returns:
            ID of the new customer
        """
        return self.insert('customers', customer_data)
    
    def update_customer(self, customer_id: int, customer_data: Dict[str, Any]) -> bool:
        """
        Update an existing customer
        
        Args:
            customer_id: ID of the customer to update
            customer_data: Dictionary containing updated customer data
            
        Returns:
            True if successful, False if customer not found
        """
        rows_affected = self.update('customers', customer_data, 'customer_id = ?', (customer_id,))
        return rows_affected > 0
    
    def get_customer(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a customer by ID
        
        Args:
            customer_id: ID of the customer
            
        Returns:
            Customer data as a dictionary, or None if not found
        """
        return self.get_by_id('customers', 'customer_id', customer_id)
    
    def get_customer_by_discord_id(self, discord_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a customer by Discord ID
        
        Args:
            discord_id: Discord ID of the customer
            
        Returns:
            Customer data as a dictionary, or None if not found
        """
        # Use the cached decorator for this frequently used method
        @self.cached()
        def _get_customer_by_discord_id_impl(discord_id):
            query = "SELECT * FROM customers WHERE discord_id = ?"
            results = self.execute_query(query, (discord_id,))
            return results[0] if results else None
        
        return _get_customer_by_discord_id_impl(discord_id)
    
    def list_customers(self) -> List[Dict[str, Any]]:
        """
        List all customers
        
        Returns:
            List of customers as dictionaries
        """
        # Use the cached decorator for this frequently used method
        @self.cached()
        def _list_customers_impl():
            query = "SELECT * FROM customers ORDER BY name"
            return self.execute_query(query)
        
        return _list_customers_impl()
    
    # Sales operations
    
    def add_sale(self, sale_data: Dict[str, Any], sale_items: List[Dict[str, Any]]) -> int:
        """
        Add a new sale with items
        
        Args:
            sale_data: Dictionary containing sale data
            sale_items: List of dictionaries containing sale item data
            
        Returns:
            ID of the new sale
        """
        conn = self._get_connection()
        
        # Start transaction
        conn.execute("BEGIN")
        
        try:
            # Insert sale
            sale_id = self.insert('sales', sale_data)
            
            # Insert sale items
            for item in sale_items:
                item['sale_id'] = sale_id
                self.insert('sale_items', item)
                
                # Update product quantity
                product_id = item['product_id']
                quantity = item['quantity']
                
                # Decrease product quantity
                product = self.get_product(product_id)
                if product:
                    new_quantity = product['quantity'] - quantity
                    self.update('products',
                               {'quantity': new_quantity, 'updated_at': datetime.now().isoformat()},
                               'product_id = ?',
                               (product_id,))
            
            # Commit transaction
            conn.commit()
            
            # Invalidate relevant caches
            self._invalidate_cache('sales')
            self._invalidate_cache('sale_items')
            self._invalidate_cache('products')
            
            return sale_id
        except Exception as e:
            # Rollback on error
            conn.rollback()
            logger.error(f"Error adding sale: {str(e)}")
            raise
    
    def get_sale(self, sale_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a sale by ID
        
        Args:
            sale_id: ID of the sale
            
        Returns:
            Sale data as a dictionary, or None if not found
        """
        # Use the cached decorator for this method
        @self.cached()
        def _get_sale_impl(sale_id):
            sale = self.get_by_id('sales', 'sale_id', sale_id)
            
            if sale:
                # Get sale items
                query = """
                SELECT si.*, p.name as product_name, p.sku
                FROM sale_items si
                JOIN products p ON si.product_id = p.product_id
                WHERE si.sale_id = ?
                """
                sale_items = self.execute_query(query, (sale_id,))
                sale['items'] = sale_items
                
                # Get customer if available
                if sale['customer_id']:
                    sale['customer'] = self.get_customer(sale['customer_id'])
            
            return sale
        
        return _get_sale_impl(sale_id)
    
    def list_sales(self, start_date: Optional[str] = None,
                  end_date: Optional[str] = None,
                  customer_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List sales with optional filtering
        
        Args:
            start_date: Filter by start date (YYYY-MM-DD) (optional)
            end_date: Filter by end date (YYYY-MM-DD) (optional)
            customer_id: Filter by customer ID (optional)
            
        Returns:
            List of sales as dictionaries
        """
        # Use the cached decorator for this method with a shorter TTL
        @self.cached(ttl=60)  # 1 minute TTL
        def _list_sales_impl(start_date, end_date, customer_id):
            query = """
            SELECT s.*, c.name as customer_name
            FROM sales s
            LEFT JOIN customers c ON s.customer_id = c.customer_id
            """
            params = []
            
            # Add filters if provided
            where_clauses = []
            if start_date:
                where_clauses.append("s.date >= ?")
                params.append(start_date)
            
            if end_date:
                where_clauses.append("s.date <= ?")
                params.append(end_date)
            
            if customer_id:
                where_clauses.append("s.customer_id = ?")
                params.append(customer_id)
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " ORDER BY s.date DESC"
            
            return self.execute_query(query, tuple(params))
        
        return _list_sales_impl(start_date, end_date, customer_id)
    
    # Audit logging
    
    def log_audit(self, action: str, entity_type: str, entity_id: int,
                 user_id: str, details: Optional[str] = None) -> int:
        """
        Log an action in the audit log
        
        Args:
            action: Action performed (e.g., 'create', 'update', 'delete')
            entity_type: Type of entity (e.g., 'product', 'expense')
            entity_id: ID of the entity
            user_id: Discord ID of the user who performed the action
            details: Additional details about the action
            
        Returns:
            ID of the audit log entry
        """
        data = {
            'action': action,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'user_id': user_id,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        
        return self.insert('audit_log', data)
    
    def create_backup_record(self, filename: str, location: str, size: int,
                           checksum: str = None, compressed: bool = False,
                           metadata: str = None) -> int:
        """
        Create a record of a database backup with integrity information
        
        Args:
            filename: Name of the backup file
            location: Location where the backup is stored
            size: Size of the backup in bytes
            checksum: SHA-256 checksum of the backup file (optional)
            compressed: Whether the backup is compressed (optional)
            metadata: JSON string with additional backup metadata (optional)
            
        Returns:
            ID of the backup record
        """
        # First, we need to update the backup_log table schema if needed
        self._ensure_backup_log_extended_schema()
        
        data = {
            'filename': filename,
            'location': location,
            'size': size,
            'timestamp': datetime.now().isoformat(),
            'checksum': checksum,
            'compressed': 1 if compressed else 0,
            'metadata': metadata,
            'verified': 0  # Not verified yet
        }
        
        return self.insert('backup_log', data)
        
    def _ensure_backup_log_extended_schema(self):
        """
        Ensure the backup_log table has the extended schema for integrity verification
        """
        # Check if the checksum column exists
        check_query = "PRAGMA table_info(backup_log)"
        columns = self.execute_query(check_query)
        column_names = [col['name'] for col in columns]
        
        if 'checksum' not in column_names:
            # Add the new columns for backup integrity
            alter_queries = [
                "ALTER TABLE backup_log ADD COLUMN checksum TEXT",
                "ALTER TABLE backup_log ADD COLUMN compressed INTEGER DEFAULT 0",
                "ALTER TABLE backup_log ADD COLUMN metadata TEXT",
                "ALTER TABLE backup_log ADD COLUMN verified INTEGER DEFAULT 0",
                "ALTER TABLE backup_log ADD COLUMN verification_date TEXT",
                "ALTER TABLE backup_log ADD COLUMN cloud_url TEXT",
                "ALTER TABLE backup_log ADD COLUMN cloud_provider TEXT"
            ]
            
            conn = self._get_connection()
            for query in alter_queries:
                try:
                    conn.execute(query)
                except sqlite3.OperationalError as e:
                    # Column may already exist in some cases
                    logger.warning(f"Error executing {query}: {str(e)}")
            
            conn.commit()
            logger.info("Extended backup_log schema for integrity verification")
    
    # Migration System
    
    def _apply_migrations(self) -> None:
        """
        Apply database migrations based on the current schema version
        """
        conn = self._get_connection()
        
        # Check current version
        current_version = self._get_current_schema_version()
        
        if current_version < self.CURRENT_VERSION:
            logger.info(f"Upgrading database from version {current_version} to {self.CURRENT_VERSION}")
            
            # Apply migrations sequentially
            for version in range(current_version + 1, self.CURRENT_VERSION + 1):
                migration_sql = self._get_migration_sql(version)
                if migration_sql:
                    logger.info(f"Applying migration to version {version}")
                    conn.executescript(migration_sql)
                    
                    # Update schema version
                    self._update_schema_version(version, f"Migration to version {version}")
                    conn.commit()
            
            logger.info(f"Database successfully upgraded to version {self.CURRENT_VERSION}")
    
    def _get_current_schema_version(self) -> int:
        """
        Get the current database schema version
        
        Returns:
            Current schema version (0 if no version found)
        """
        conn = self._get_connection()
        
        try:
            cursor = conn.execute("SELECT MAX(version) FROM schema_version")
            result = cursor.fetchone()
            return result[0] if result and result[0] is not None else 0
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            return 0
    
    def _update_schema_version(self, version: int, description: str) -> None:
        """
        Update the schema version in the database
        
        Args:
            version: New schema version
            description: Description of the changes
        """
        data = {
            'version': version,
            'applied_at': datetime.now().isoformat(),
            'description': description
        }
        
        self.insert('schema_version', data)
    
    def _get_migration_sql(self, version: int) -> Optional[str]:
        """
        Get the SQL for a specific migration version
        
        Args:
            version: Migration version
            
        Returns:
            SQL string for the migration, or None if not found
        """
        # In a real implementation, these could be loaded from files
        migrations = {
            # Migration to add inventory_history table
            2: """
            CREATE TABLE IF NOT EXISTS inventory_history (
                history_id INTEGER PRIMARY KEY,
                product_id INTEGER NOT NULL,
                previous_quantity INTEGER NOT NULL,
                new_quantity INTEGER NOT NULL,
                change_amount INTEGER NOT NULL,
                reason TEXT,
                user_id TEXT NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            );
            """,
            
            # Migration to add indexes for performance optimization
            3: """
            -- Add indexes to products table
            CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
            CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
            CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
            CREATE INDEX IF NOT EXISTS idx_products_quantity ON products(quantity);
            
            -- Add indexes to expenses table
            CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);
            CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
            CREATE INDEX IF NOT EXISTS idx_expenses_vendor ON expenses(vendor);
            
            -- Add indexes to customers table
            CREATE INDEX IF NOT EXISTS idx_customers_discord_id ON customers(discord_id);
            CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);
            
            -- Add indexes to sales table
            CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(date);
            CREATE INDEX IF NOT EXISTS idx_sales_customer_id ON sales(customer_id);
            CREATE INDEX IF NOT EXISTS idx_sales_payment_method ON sales(payment_method);
            
            -- Add indexes to sale_items table
            CREATE INDEX IF NOT EXISTS idx_sale_items_sale_id ON sale_items(sale_id);
            CREATE INDEX IF NOT EXISTS idx_sale_items_product_id ON sale_items(product_id);
            
            -- Add indexes to inventory_history table
            CREATE INDEX IF NOT EXISTS idx_inventory_history_product_id ON inventory_history(product_id);
            CREATE INDEX IF NOT EXISTS idx_inventory_history_timestamp ON inventory_history(timestamp);
            CREATE INDEX IF NOT EXISTS idx_inventory_history_user_id ON inventory_history(user_id);
            
            -- Add indexes to audit_log table
            CREATE INDEX IF NOT EXISTS idx_audit_log_entity_type ON audit_log(entity_type);
            CREATE INDEX IF NOT EXISTS idx_audit_log_entity_id ON audit_log(entity_id);
            CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
            CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
            """
        }
        
        return migrations.get(version)
    
    # Database backup and restore
    
    def backup_database(self, backup_dir: str = "data/backups", compress: bool = True) -> str:
        """
        Create a backup of the database with integrity verification
        
        Args:
            backup_dir: Directory to store the backup
            compress: Whether to compress the backup (default: True)
            
        Returns:
            Path to the backup file
        """
        import hashlib
        import json
        import shutil
        import zipfile
        
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"accountme_backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        conn = self._get_connection()
        
        # Create a backup using SQLite's backup API
        backup_conn = sqlite3.connect(backup_path)
        conn.backup(backup_conn)
        backup_conn.close()
        
        # Calculate SHA-256 checksum for integrity verification
        sha256_hash = hashlib.sha256()
        with open(backup_path, "rb") as f:
            # Read and update hash in chunks of 4K
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        checksum = sha256_hash.hexdigest()
        
        # Create metadata file with backup information
        metadata = {
            "filename": backup_filename,
            "timestamp": datetime.now().isoformat(),
            "checksum": checksum,
            "db_version": self.CURRENT_VERSION,
            "compressed": compress,
            "tables": {}
        }
        
        # Add table statistics to metadata
        for table in ["products", "expenses", "customers", "sales", "sale_items", "audit_log", "backup_log", "inventory_history"]:
            try:
                count_query = f"SELECT COUNT(*) FROM {table}"
                result = self.execute_query(count_query)
                metadata["tables"][table] = result[0]["COUNT(*)"] if result else 0
            except Exception as e:
                logger.error(f"Error getting count for table {table}: {str(e)}")
                metadata["tables"][table] = -1
        
        metadata_filename = f"{backup_filename}.meta.json"
        metadata_path = os.path.join(backup_dir, metadata_filename)
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        final_backup_path = backup_path
        
        # Compress the backup if requested
        if compress:
            zip_filename = f"{backup_filename}.zip"
            zip_path = os.path.join(backup_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(backup_path, arcname=backup_filename)
                zipf.write(metadata_path, arcname=metadata_filename)
            
            # Remove the uncompressed files
            os.remove(backup_path)
            os.remove(metadata_path)
            
            final_backup_path = zip_path
        
        # Get file size
        file_size = os.path.getsize(final_backup_path)
        
        # Log the backup with additional metadata
        backup_id = self.create_backup_record(
            os.path.basename(final_backup_path),
            backup_dir,
            file_size,
            checksum=checksum,
            compressed=compress,
            metadata=json.dumps(metadata)
        )
        
        logger.info(f"Database backed up to {final_backup_path} ({file_size} bytes) with checksum {checksum}")
        return final_backup_path
    
    def verify_backup_integrity(self, backup_path: str) -> bool:
        """
        Verify the integrity of a backup file using its checksum
        
        Args:
            backup_path: Path to the backup file
            
        Returns:
            True if integrity check passes, False otherwise
        """
        import hashlib
        import json
        import zipfile
        import tempfile
        
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        # Check if this is a compressed backup
        is_compressed = backup_path.endswith('.zip')
        actual_db_path = backup_path
        metadata_path = None
        temp_dir = None
        
        try:
            if is_compressed:
                # Extract the zip file to a temporary directory
                temp_dir = tempfile.mkdtemp()
                with zipfile.ZipFile(backup_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Find the .db file and metadata file
                db_files = [f for f in os.listdir(temp_dir) if f.endswith('.db')]
                if not db_files:
                    logger.error(f"No database file found in backup: {backup_path}")
                    return False
                
                actual_db_path = os.path.join(temp_dir, db_files[0])
                
                # Look for metadata file
                meta_files = [f for f in os.listdir(temp_dir) if f.endswith('.meta.json')]
                if meta_files:
                    metadata_path = os.path.join(temp_dir, meta_files[0])
            else:
                # Check for metadata file alongside the backup
                metadata_path = f"{backup_path}.meta.json"
                if not os.path.exists(metadata_path):
                    logger.error(f"No metadata file found for backup: {backup_path}")
                    return False
            
            # Load metadata
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Calculate checksum of the database file
            sha256_hash = hashlib.sha256()
            with open(actual_db_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            actual_checksum = sha256_hash.hexdigest()
            
            # Compare checksums
            expected_checksum = metadata.get('checksum')
            if not expected_checksum:
                logger.error(f"No checksum found in metadata for backup: {backup_path}")
                return False
                
            if expected_checksum != actual_checksum:
                logger.error(f"Backup integrity check failed: {backup_path}")
                logger.error(f"Expected checksum: {expected_checksum}")
                logger.error(f"Actual checksum: {actual_checksum}")
                return False
            
            # Update backup record to mark as verified
            try:
                backup_filename = os.path.basename(backup_path)
                
                # Find the backup record
                query = "SELECT backup_id FROM backup_log WHERE filename = ? ORDER BY backup_id DESC LIMIT 1"
                result = self.execute_query(query, (backup_filename,))
                
                if result:
                    backup_id = result[0]['backup_id']
                    self.update('backup_log',
                              {'verified': 1, 'verification_date': datetime.now().isoformat()},
                              'backup_id = ?', (backup_id,))
                    logger.info(f"Marked backup {backup_id} as verified")
            except Exception as e:
                logger.warning(f"Could not update backup verification status: {str(e)}")
            
            logger.info(f"Backup integrity verified: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying backup integrity: {str(e)}")
            return False
            
        finally:
            # Clean up temporary directory if it was created
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)
    
    def upload_backup_to_cloud(self, backup_path: str, provider: str = "gdrive") -> Optional[str]:
        """
        Upload a backup file to cloud storage
        
        Args:
            backup_path: Path to the backup file
            provider: Cloud storage provider ('gdrive' or 'onedrive')
            
        Returns:
            URL of the uploaded file, or None if upload failed
        """
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return None
            
        try:
            cloud_url = None
            
            if provider == "gdrive":
                cloud_url = self._upload_to_gdrive(backup_path)
            elif provider == "onedrive":
                cloud_url = self._upload_to_onedrive(backup_path)
            else:
                logger.error(f"Unsupported cloud provider: {provider}")
                return None
                
            if cloud_url:
                # Update backup record with cloud URL
                try:
                    backup_filename = os.path.basename(backup_path)
                    
                    # Find the backup record
                    query = "SELECT backup_id FROM backup_log WHERE filename = ? ORDER BY backup_id DESC LIMIT 1"
                    result = self.execute_query(query, (backup_filename,))
                    
                    if result:
                        backup_id = result[0]['backup_id']
                        self.update('backup_log',
                                  {'cloud_url': cloud_url, 'cloud_provider': provider},
                                  'backup_id = ?', (backup_id,))
                        logger.info(f"Updated backup {backup_id} with cloud URL: {cloud_url}")
                except Exception as e:
                    logger.warning(f"Could not update backup cloud URL: {str(e)}")
                    
            return cloud_url
            
        except Exception as e:
            logger.error(f"Error uploading backup to cloud: {str(e)}")
            return None
            
    def _upload_to_gdrive(self, file_path: str) -> Optional[str]:
        """
        Upload a file to Google Drive
        
        Args:
            file_path: Path to the file to upload
            
        Returns:
            URL of the uploaded file, or None if upload failed
        """
        try:
            # This is a placeholder for actual Google Drive API implementation
            # In a real implementation, you would use the Google Drive API to upload the file
            # and return the URL of the uploaded file
            
            # For now, we'll just log a message and return a dummy URL
            logger.info(f"Uploading {file_path} to Google Drive (placeholder)")
            
            # In a real implementation, you would return the actual URL
            return f"https://drive.google.com/file/d/placeholder/{os.path.basename(file_path)}"
            
        except Exception as e:
            logger.error(f"Error uploading to Google Drive: {str(e)}")
            return None
            
    def _upload_to_onedrive(self, file_path: str) -> Optional[str]:
        """
        Upload a file to OneDrive
        
        Args:
            file_path: Path to the file to upload
            
        Returns:
            URL of the uploaded file, or None if upload failed
        """
        try:
            # This is a placeholder for actual OneDrive API implementation
            # In a real implementation, you would use the Microsoft Graph API to upload the file
            # and return the URL of the uploaded file
            
            # For now, we'll just log a message and return a dummy URL
            logger.info(f"Uploading {file_path} to OneDrive (placeholder)")
            
            # In a real implementation, you would return the actual URL
            return f"https://onedrive.live.com/placeholder/{os.path.basename(file_path)}"
            
        except Exception as e:
            logger.error(f"Error uploading to OneDrive: {str(e)}")
            return None
    
    def restore_database(self, backup_path: str, verify_integrity: bool = True) -> bool:
        """
        Restore the database from a backup with optional integrity verification
        
        Args:
            backup_path: Path to the backup file
            verify_integrity: Whether to verify backup integrity before restoring
            
        Returns:
            True if successful, False otherwise
        """
        import hashlib
        import json
        import zipfile
        import tempfile
        import shutil
        
        if not os.path.exists(backup_path):
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        # Check if this is a compressed backup
        is_compressed = backup_path.endswith('.zip')
        actual_db_path = backup_path
        metadata_path = None
        temp_dir = None
        
        try:
            if is_compressed:
                # Extract the zip file to a temporary directory
                temp_dir = tempfile.mkdtemp()
                with zipfile.ZipFile(backup_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Find the .db file and metadata file
                db_files = [f for f in os.listdir(temp_dir) if f.endswith('.db')]
                if not db_files:
                    logger.error(f"No database file found in backup: {backup_path}")
                    return False
                
                actual_db_path = os.path.join(temp_dir, db_files[0])
                
                # Look for metadata file
                meta_files = [f for f in os.listdir(temp_dir) if f.endswith('.meta.json')]
                if meta_files:
                    metadata_path = os.path.join(temp_dir, meta_files[0])
            else:
                # Check for metadata file alongside the backup
                metadata_path = f"{backup_path}.meta.json"
                if not os.path.exists(metadata_path):
                    metadata_path = None
            
            # Verify integrity if requested and metadata is available
            if verify_integrity and metadata_path:
                logger.info(f"Verifying backup integrity: {backup_path}")
                
                # Load metadata
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                # Calculate checksum of the database file
                sha256_hash = hashlib.sha256()
                with open(actual_db_path, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
                actual_checksum = sha256_hash.hexdigest()
                
                # Compare checksums
                expected_checksum = metadata.get('checksum')
                if expected_checksum and expected_checksum != actual_checksum:
                    logger.error(f"Backup integrity check failed: {backup_path}")
                    logger.error(f"Expected checksum: {expected_checksum}")
                    logger.error(f"Actual checksum: {actual_checksum}")
                    return False
                
                logger.info(f"Backup integrity verified: {backup_path}")
            
            # Close current connection
            self.close()
            
            try:
                # Create a new connection to the backup
                backup_conn = sqlite3.connect(actual_db_path)
                
                # Create a new connection to the target database
                conn = sqlite3.connect(self.db_path)
                
                # Restore using SQLite's backup API
                backup_conn.backup(conn)
                
                # Close connections
                backup_conn.close()
                conn.close()
                
                logger.info(f"Database successfully restored from {backup_path}")
                
                # Update backup record to mark as verified if we have a backup ID
                if metadata_path:
                    try:
                        backup_filename = os.path.basename(backup_path)
                        self._get_connection()  # Reconnect to the database
                        
                        # Find the backup record
                        query = "SELECT backup_id FROM backup_log WHERE filename = ? ORDER BY backup_id DESC LIMIT 1"
                        result = self.execute_query(query, (backup_filename,))
                        
                        if result:
                            backup_id = result[0]['backup_id']
                            self.update('backup_log',
                                      {'verified': 1, 'verification_date': datetime.now().isoformat()},
                                      'backup_id = ?', (backup_id,))
                            logger.info(f"Marked backup {backup_id} as verified")
                    except Exception as e:
                        logger.warning(f"Could not update backup verification status: {str(e)}")
                
                # Clear cache after restore
                self._invalidate_cache()
                
                return True
            except Exception as e:
                logger.error(f"Error restoring database: {str(e)}")
                return False
            finally:
                # Reconnect to the database
                self._get_connection()
        
        finally:
            # Clean up temporary directory if it was created
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)