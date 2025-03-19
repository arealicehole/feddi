"""
Performance test script for the AccountME Discord Bot
Tests the performance of database operations with and without optimizations
"""

import os
import sys
import time
import random
import sqlite3
from datetime import datetime, timedelta

# Add the parent directory to sys.path to allow importing from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db_manager import DatabaseManager

def generate_test_data(db_manager, num_products=100, num_customers=20, num_sales=50, num_expenses=30):
    """Generate test data for performance testing"""
    print(f"Generating test data: {num_products} products, {num_customers} customers, {num_sales} sales, {num_expenses} expenses")
    
    # Generate products
    categories = ['blank', 'dtf', 'other']
    subcategories = ['for_pressing', 'ready_to_sell', None]
    manufacturers = ['Gildan', 'Hanes', 'Fruit of the Loom', 'Next Level', 'Bella+Canvas']
    colors = ['Black', 'White', 'Red', 'Blue', 'Green', 'Yellow', 'Purple', 'Orange', 'Grey']
    sizes = ['XS', 'S', 'M', 'L', 'XL', '2XL', '3XL']
    
    for i in range(num_products):
        category = random.choice(categories)
        product_data = {
            'name': f"Test Product {i+1}",
            'category': category,
            'subcategory': random.choice(subcategories),
            'manufacturer': random.choice(manufacturers),
            'vendor': f"Vendor {random.randint(1, 5)}",
            'style': f"Style-{random.randint(1000, 9999)}",
            'color': random.choice(colors),
            'size': random.choice(sizes),
            'sku': f"SKU-{i+1:04d}",
            'quantity': random.randint(0, 100),
            'cost_price': round(random.uniform(5.0, 30.0), 2),
            'selling_price': round(random.uniform(10.0, 60.0), 2)
        }
        db_manager.add_product(product_data)
    
    # Generate customers
    for i in range(num_customers):
        customer_data = {
            'name': f"Customer {i+1}",
            'discord_id': f"discord_{i+1:04d}",
            'contact_info': f"customer{i+1}@example.com"
        }
        db_manager.add_customer(customer_data)
    
    # Get all products and customers for sales
    products = db_manager.list_products()
    customers = db_manager.list_customers()
    
    # Generate sales
    for i in range(num_sales):
        # Random date in the last 90 days
        sale_date = (datetime.now() - timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d")
        customer = random.choice(customers) if customers else None
        
        # Create sale data
        sale_data = {
            'customer_id': customer['customer_id'] if customer else None,
            'date': sale_date,
            'total_amount': 0,  # Will be calculated from items
            'payment_method': random.choice(['Cash', 'Credit Card', 'PayPal', 'Venmo']),
            'notes': f"Test sale {i+1}"
        }
        
        # Create sale items
        num_items = random.randint(1, 5)
        sale_items = []
        total_amount = 0
        
        for _ in range(num_items):
            product = random.choice(products)
            quantity = random.randint(1, 3)
            price = product['selling_price']
            item_total = quantity * price
            total_amount += item_total
            
            sale_items.append({
                'product_id': product['product_id'],
                'quantity': quantity,
                'price': price
            })
        
        sale_data['total_amount'] = round(total_amount, 2)
        
        # Add sale with items
        try:
            db_manager.add_sale(sale_data, sale_items)
        except Exception as e:
            print(f"Error adding sale: {e}")
    
    # Generate expenses
    expense_categories = ['Supplies', 'Rent', 'Utilities', 'Marketing', 'Shipping', 'Inventory']
    
    for i in range(num_expenses):
        # Random date in the last 90 days
        expense_date = (datetime.now() - timedelta(days=random.randint(0, 90))).strftime("%Y-%m-%d")
        
        expense_data = {
            'date': expense_date,
            'vendor': f"Vendor {random.randint(1, 10)}",
            'amount': round(random.uniform(10.0, 500.0), 2),
            'category': random.choice(expense_categories),
            'description': f"Test expense {i+1}",
            'receipt_image': f"https://example.com/receipts/receipt_{i+1}.jpg"
        }
        
        db_manager.add_expense(expense_data)
    
    print("Test data generation complete")

def run_performance_tests(db_path="data/performance_test.db"):
    """Run performance tests on the database manager"""
    # Create a fresh database for testing
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Initialize database manager
    db_manager = DatabaseManager(db_path)
    
    # Generate test data
    generate_test_data(db_manager)
    
    # Run tests
    print("\nRunning performance tests...")
    
    # Test 1: Product lookup by SKU (cached vs. uncached)
    print("\nTest 1: Product lookup by SKU")
    skus = [f"SKU-{i:04d}" for i in range(1, 11)]  # Get 10 random SKUs
    
    # First run - uncached
    start_time = time.time()
    for sku in skus:
        product = db_manager.get_product_by_sku(sku)
    uncached_time = time.time() - start_time
    print(f"  Uncached lookup time: {uncached_time:.6f} seconds")
    
    # Second run - should be cached
    start_time = time.time()
    for sku in skus:
        product = db_manager.get_product_by_sku(sku)
    cached_time = time.time() - start_time
    print(f"  Cached lookup time: {cached_time:.6f} seconds")
    
    # Avoid division by zero
    if cached_time > 0:
        print(f"  Speedup factor: {uncached_time / cached_time:.2f}x")
    else:
        print(f"  Speedup factor: ∞ (cached time too small to measure)")
    
    # Test 2: List products by category
    print("\nTest 2: List products by category")
    categories = ['blank', 'dtf', 'other']
    
    # First run - uncached
    start_time = time.time()
    for category in categories:
        products = db_manager.list_products(category=category)
    uncached_time = time.time() - start_time
    print(f"  Uncached list time: {uncached_time:.6f} seconds")
    
    # Second run - should be cached
    start_time = time.time()
    for category in categories:
        products = db_manager.list_products(category=category)
    cached_time = time.time() - start_time
    print(f"  Cached list time: {cached_time:.6f} seconds")
    
    # Avoid division by zero
    if cached_time > 0:
        print(f"  Speedup factor: {uncached_time / cached_time:.2f}x")
    else:
        print(f"  Speedup factor: ∞ (cached time too small to measure)")
    
    # Test 3: Sales reporting with date filtering
    print("\nTest 3: Sales reporting with date filtering")
    
    # Generate date ranges for the last 3 months
    end_date = datetime.now()
    date_ranges = []
    for i in range(3):
        start_date = (end_date - timedelta(days=30)).strftime("%Y-%m-%d")
        date_ranges.append((start_date, end_date.strftime("%Y-%m-%d")))
        end_date = end_date - timedelta(days=30)
    
    # First run - uncached
    start_time = time.time()
    for start_date, end_date in date_ranges:
        sales = db_manager.list_sales(start_date=start_date, end_date=end_date)
    uncached_time = time.time() - start_time
    print(f"  Uncached sales report time: {uncached_time:.6f} seconds")
    
    # Second run - should be cached
    start_time = time.time()
    for start_date, end_date in date_ranges:
        sales = db_manager.list_sales(start_date=start_date, end_date=end_date)
    cached_time = time.time() - start_time
    print(f"  Cached sales report time: {cached_time:.6f} seconds")
    
    # Avoid division by zero
    if cached_time > 0:
        print(f"  Speedup factor: {uncached_time / cached_time:.2f}x")
    else:
        print(f"  Speedup factor: ∞ (cached time too small to measure)")
    
    # Test 4: Cache invalidation on data modification
    print("\nTest 4: Cache invalidation on data modification")
    
    # Get a product and cache it
    sku = "SKU-0001"
    product = db_manager.get_product_by_sku(sku)
    print(f"  Initial product quantity: {product['quantity']}")
    
    # Modify the product
    new_quantity = product['quantity'] + 10
    db_manager.update_product(product['product_id'], {'quantity': new_quantity})
    
    # Get the product again - should reflect the new quantity
    updated_product = db_manager.get_product_by_sku(sku)
    print(f"  Updated product quantity: {updated_product['quantity']}")
    
    if updated_product['quantity'] == new_quantity:
        print("  Cache invalidation working correctly")
    else:
        print("  Cache invalidation failed")
    
    # Test 5: Database query with and without indexes
    print("\nTest 5: Database query with indexes")
    
    # Create a connection to run raw SQL
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Query with indexes (already created by migrations)
    start_time = time.time()
    cursor.execute("""
    SELECT p.*, COUNT(si.sale_item_id) as sales_count
    FROM products p
    LEFT JOIN sale_items si ON p.product_id = si.product_id
    WHERE p.category = 'blank'
    GROUP BY p.product_id
    ORDER BY sales_count DESC
    """)
    results = cursor.fetchall()
    with_indexes_time = time.time() - start_time
    print(f"  Query time with indexes: {with_indexes_time:.6f} seconds")
    
    # Close connection
    conn.close()
    
    # Clean up
    db_manager.close()
    print("\nPerformance tests completed")

if __name__ == "__main__":
    run_performance_tests()