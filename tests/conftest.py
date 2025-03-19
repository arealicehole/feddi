"""
Pytest configuration for AccountME Discord Bot tests
"""

import os
import sys
import pytest
import sqlite3

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.db_manager import DatabaseManager

@pytest.fixture
def test_db_path(tmp_path):
    """
    Create a temporary database path for testing
    
    Returns:
        Path to the test database
    """
    db_path = tmp_path / "test_database.db"
    return str(db_path)

@pytest.fixture
def db_manager(test_db_path):
    """
    Create a database manager instance for testing
    
    Returns:
        DatabaseManager instance
    """
    manager = DatabaseManager(db_path=test_db_path)
    yield manager
    
    # Cleanup
    manager.close()
    if os.path.exists(test_db_path):
        os.remove(test_db_path)