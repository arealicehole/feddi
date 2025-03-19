"""
Test configuration for AccountME Discord Bot tests
"""

import os
import tempfile

# Test database configuration
TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "accountme_test.db")

# Test Discord bot configuration
TEST_BOT_TOKEN = "test_token"
TEST_COMMAND_PREFIX = "!"
TEST_ADMIN_USER_IDS = ["123456789"]

# Test backup directory
TEST_BACKUP_DIR = os.path.join(tempfile.gettempdir(), "accountme_test_backups")

# Create directories if they don't exist
os.makedirs(TEST_BACKUP_DIR, exist_ok=True)

# Clean up function to remove test files
def cleanup_test_files():
    """Remove test files after tests are complete"""
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    if os.path.exists(TEST_BACKUP_DIR):
        for file in os.listdir(TEST_BACKUP_DIR):
            os.remove(os.path.join(TEST_BACKUP_DIR, file))