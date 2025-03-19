"""
Unit tests for the DatabaseManager class
"""

import os
import pytest
import sqlite3
from datetime import datetime
from utils.db_manager import DatabaseManager

class TestDatabaseManager:
    """
    Test cases for the DatabaseManager class
    """
    
    def test_initialization(self, db_manager, test_db_path):
        """Test database initialization"""
        # Check that the database file was created
        assert os.path.exists(test_db_path)
        
        # Check that the connection is valid
        assert db_manager.connection is not None
        
        # Check that tables were created
        tables = db_manager.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        table_names = [table['name'] for table in tables]
        
        # Verify essential tables exist
        assert 'products' in table_names
        assert 'expenses' in table_names
        assert 'customers' in table_names
        assert 'sales' in table_names
        assert 'sale_items' in table_names
        assert 'audit_log' in table_names
        assert 'backup_log' in table_names
        assert 'schema_version' in table_names
    
    def test_execute_query(self, db_manager):
        """Test execute_query method"""
        # Insert test data
        db_manager.execute_update(
            "INSERT INTO products (name, category, sku) VALUES (?, ?, ?)",
            ("Test Product", "blank", "TEST-001")
        )
        
        # Query the data
        results = db_manager.execute_query(
            "SELECT * FROM products WHERE sku = ?",
            ("TEST-001",)
        )
        
        # Verify results
        assert len(results) == 1
        assert results[0]['name'] == "Test Product"
        assert results[0]['category'] == "blank"
    
    def test_execute_update(self, db_manager):
        """Test execute_update method"""
        # Insert test data
        rows_affected = db_manager.execute_update(
            "INSERT INTO products (name, category, sku) VALUES (?, ?, ?)",
            ("Test Product", "blank", "TEST-001")
        )
        
        # Verify row was inserted
        assert rows_affected == 1
        
        # Update the data
        rows_affected = db_manager.execute_update(
            "UPDATE products SET name = ? WHERE sku = ?",
            ("Updated Product", "TEST-001")
        )
        
        # Verify row was updated
        assert rows_affected == 1
        
        # Verify the update
        results = db_manager.execute_query(
            "SELECT name FROM products WHERE sku = ?",
            ("TEST-001",)
        )
        assert results[0]['name'] == "Updated Product"
    
    def test_insert(self, db_manager):
        """Test insert method"""
        # Insert a product
        product_data = {
            'name': 'Test Product',
            'category': 'blank',
            'sku': 'TEST-001',
            'quantity': 10,
            'cost_price': 15.99,
            'selling_price': 29.99
        }
        
        product_id = db_manager.insert('products', product_data)
        
        # Verify product was inserted
        assert product_id > 0
        
        # Verify the product data
        product = db_manager.get_by_id('products', 'product_id', product_id)
        assert product['name'] == 'Test Product'
        assert product['category'] == 'blank'
        assert product['sku'] == 'TEST-001'
        assert product['quantity'] == 10
        assert product['cost_price'] == 15.99
        assert product['selling_price'] == 29.99
    
    def test_update(self, db_manager):
        """Test update method"""
        # Insert a product
        product_data = {
            'name': 'Test Product',
            'category': 'blank',
            'sku': 'TEST-001',
            'quantity': 10
        }
        
        product_id = db_manager.insert('products', product_data)
        
        # Update the product
        update_data = {
            'name': 'Updated Product',
            'quantity': 20
        }
        
        rows_affected = db_manager.update(
            'products', update_data, 'product_id = ?', (product_id,)
        )
        
        # Verify row was updated
        assert rows_affected == 1
        
        # Verify the update
        product = db_manager.get_by_id('products', 'product_id', product_id)
        assert product['name'] == 'Updated Product'
        assert product['quantity'] == 20
        assert product['category'] == 'blank'  # Unchanged field
    
    def test_delete(self, db_manager):
        """Test delete method"""
        # Insert a product
        product_data = {
            'name': 'Test Product',
            'category': 'blank',
            'sku': 'TEST-001'
        }
        
        product_id = db_manager.insert('products', product_data)
        
        # Verify product exists
        product = db_manager.get_by_id('products', 'product_id', product_id)
        assert product is not None
        
        # Delete the product
        rows_affected = db_manager.delete('products', 'product_id = ?', (product_id,))
        
        # Verify row was deleted
        assert rows_affected == 1
        
        # Verify product no longer exists
        product = db_manager.get_by_id('products', 'product_id', product_id)
        assert product is None
    
    def test_get_by_id(self, db_manager):
        """Test get_by_id method"""
        # Insert a product
        product_data = {
            'name': 'Test Product',
            'category': 'blank',
            'sku': 'TEST-001'
        }
        
        product_id = db_manager.insert('products', product_data)
        
        # Get the product by ID
        product = db_manager.get_by_id('products', 'product_id', product_id)
        
        # Verify product data
        assert product['name'] == 'Test Product'
        assert product['category'] == 'blank'
        assert product['sku'] == 'TEST-001'
        
        # Test non-existent ID
        non_existent = db_manager.get_by_id('products', 'product_id', 9999)
        assert non_existent is None
    
    def test_add_product(self, db_manager):
        """Test add_product method"""
        # Add a product
        product_data = {
            'name': 'Test T-Shirt',
            'category': 'blank',
            'subcategory': 'for_pressing',
            'manufacturer': 'Test Brand',
            'style': 'TB-100',
            'color': 'Black',
            'size': 'L',
            'sku': 'TB-BLK-L',
            'quantity': 25,
            'cost_price': 8.50,
            'selling_price': 15.00
        }
        
        product_id = db_manager.add_product(product_data)
        
        # Verify product was added
        assert product_id > 0
        
        # Verify product data
        product = db_manager.get_product(product_id)
        assert product['name'] == 'Test T-Shirt'
        assert product['category'] == 'blank'
        assert product['subcategory'] == 'for_pressing'
        assert product['quantity'] == 25
        assert product['updated_at'] is not None  # Should have a timestamp
    
    def test_update_product(self, db_manager):
        """Test update_product method"""
        # Add a product
        product_data = {
            'name': 'Test T-Shirt',
            'category': 'blank',
            'sku': 'TB-BLK-L',
            'quantity': 25
        }
        
        product_id = db_manager.add_product(product_data)
        
        # Update the product
        update_data = {
            'name': 'Updated T-Shirt',
            'quantity': 30
        }
        
        success = db_manager.update_product(product_id, update_data)
        
        # Verify update was successful
        assert success is True
        
        # Verify product data
        product = db_manager.get_product(product_id)
        assert product['name'] == 'Updated T-Shirt'
        assert product['quantity'] == 30
        assert product['category'] == 'blank'  # Unchanged field
    
    def test_get_product_by_sku(self, db_manager):
        """Test get_product_by_sku method"""
        # Add a product
        product_data = {
            'name': 'Test T-Shirt',
            'category': 'blank',
            'sku': 'TB-BLK-L',
            'quantity': 25
        }
        
        product_id = db_manager.add_product(product_data)
        
        # Get product by SKU
        product = db_manager.get_product_by_sku('TB-BLK-L')
        
        # Verify product data
        assert product['product_id'] == product_id
        assert product['name'] == 'Test T-Shirt'
        assert product['category'] == 'blank'
        
        # Test non-existent SKU
        non_existent = db_manager.get_product_by_sku('NON-EXISTENT')
        assert non_existent is None
    
    def test_list_products(self, db_manager):
        """Test list_products method"""
        # Add multiple products
        products = [
            {
                'name': 'T-Shirt Black L',
                'category': 'blank',
                'subcategory': 'for_pressing',
                'sku': 'TS-BLK-L',
                'quantity': 25
            },
            {
                'name': 'T-Shirt White M',
                'category': 'blank',
                'subcategory': 'ready_to_sell',
                'sku': 'TS-WHT-M',
                'quantity': 15
            },
            {
                'name': 'DTF Print Logo',
                'category': 'dtf',
                'sku': 'DTF-LOGO-001',
                'quantity': 50
            }
        ]
        
        for product in products:
            db_manager.add_product(product)
        
        # List all products
        all_products = db_manager.list_products()
        assert len(all_products) == 3
        
        # List by category
        blank_products = db_manager.list_products(category='blank')
        assert len(blank_products) == 2
        assert all(p['category'] == 'blank' for p in blank_products)
        
        dtf_products = db_manager.list_products(category='dtf')
        assert len(dtf_products) == 1
        assert dtf_products[0]['category'] == 'dtf'
        
        # List by subcategory
        for_pressing = db_manager.list_products(subcategory='for_pressing')
        assert len(for_pressing) == 1
        assert for_pressing[0]['subcategory'] == 'for_pressing'
        
        # List by category and subcategory
        blank_ready = db_manager.list_products(category='blank', subcategory='ready_to_sell')
        assert len(blank_ready) == 1
        assert blank_ready[0]['category'] == 'blank'
        assert blank_ready[0]['subcategory'] == 'ready_to_sell'
    
    def test_adjust_product_quantity(self, db_manager):
        """Test adjust_product_quantity method"""
        # Add a product
        product_data = {
            'name': 'Test T-Shirt',
            'category': 'blank',
            'sku': 'TB-BLK-L',
            'quantity': 25
        }
        
        product_id = db_manager.add_product(product_data)
        
        # Increase quantity
        success = db_manager.adjust_product_quantity(
            product_id, 5, 'test_user', 'Received new stock'
        )
        
        # Verify adjustment was successful
        assert success is True
        
        # Verify quantity was updated
        product = db_manager.get_product(product_id)
        assert product['quantity'] == 30
        
        # Decrease quantity
        success = db_manager.adjust_product_quantity(
            product_id, -10, 'test_user', 'Removed damaged items'
        )
        
        # Verify adjustment was successful
        assert success is True
        
        # Verify quantity was updated
        product = db_manager.get_product(product_id)
        assert product['quantity'] == 20
        
        # Check audit log
        audit_logs = db_manager.execute_query(
            "SELECT * FROM audit_log WHERE entity_id = ? AND entity_type = 'product'",
            (product_id,)
        )
        
        # Verify audit logs were created
        assert len(audit_logs) == 2
        assert any('30' in log['details'] for log in audit_logs)
        assert any('20' in log['details'] for log in audit_logs)
    
    def test_add_expense(self, db_manager):
        """Test add_expense method"""
        # Add an expense
        expense_data = {
            'date': '2025-03-18',
            'vendor': 'Test Supplier',
            'amount': 150.75,
            'category': 'inventory',
            'description': 'Blank t-shirts purchase'
        }
        
        expense_id = db_manager.add_expense(expense_data)
        
        # Verify expense was added
        assert expense_id > 0
        
        # Verify expense data
        expense = db_manager.get_expense(expense_id)
        assert expense['date'] == '2025-03-18'
        assert expense['vendor'] == 'Test Supplier'
        assert expense['amount'] == 150.75
        assert expense['category'] == 'inventory'
        assert expense['description'] == 'Blank t-shirts purchase'
    
    def test_update_expense(self, db_manager):
        """Test update_expense method"""
        # Add an expense
        expense_data = {
            'date': '2025-03-18',
            'vendor': 'Test Supplier',
            'amount': 150.75,
            'category': 'inventory'
        }
        
        expense_id = db_manager.add_expense(expense_data)
        
        # Update the expense
        update_data = {
            'amount': 175.50,
            'description': 'Updated description'
        }
        
        success = db_manager.update_expense(expense_id, update_data)
        
        # Verify update was successful
        assert success is True
        
        # Verify expense data
        expense = db_manager.get_expense(expense_id)
        assert expense['amount'] == 175.50
        assert expense['description'] == 'Updated description'
        assert expense['vendor'] == 'Test Supplier'  # Unchanged field
    
    def test_list_expenses(self, db_manager):
        """Test list_expenses method"""
        # Add multiple expenses
        expenses = [
            {
                'date': '2025-03-15',
                'vendor': 'Supplier A',
                'amount': 100.00,
                'category': 'inventory'
            },
            {
                'date': '2025-03-16',
                'vendor': 'Supplier B',
                'amount': 75.50,
                'category': 'inventory'
            },
            {
                'date': '2025-03-18',
                'vendor': 'Utility Company',
                'amount': 200.00,
                'category': 'utilities'
            }
        ]
        
        for expense in expenses:
            db_manager.add_expense(expense)
        
        # List all expenses
        all_expenses = db_manager.list_expenses()
        assert len(all_expenses) == 3
        
        # List by date range
        date_range = db_manager.list_expenses(start_date='2025-03-16', end_date='2025-03-18')
        assert len(date_range) == 2
        
        # List by category
        inventory = db_manager.list_expenses(category='inventory')
        assert len(inventory) == 2
        assert all(e['category'] == 'inventory' for e in inventory)
        
        utilities = db_manager.list_expenses(category='utilities')
        assert len(utilities) == 1
        assert utilities[0]['category'] == 'utilities'
        
        # List by date range and category
        filtered = db_manager.list_expenses(
            start_date='2025-03-15',
            end_date='2025-03-16',
            category='inventory'
        )
        assert len(filtered) == 2
        assert all(e['category'] == 'inventory' for e in filtered)