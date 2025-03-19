"""
Unit tests for the backup_cog.py module
"""

import pytest
import os
import discord
import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock, mock_open
import io

from bot.cogs.backup_cog import BackupCog

class TestBackupCog:
    """Test cases for the BackupCog class"""
    
    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot instance"""
        bot = MagicMock()
        bot.loop = asyncio.get_event_loop()
        bot.db_manager = MagicMock()
        bot.db_manager.backup_database.return_value = "test/path/backup.db"
        bot.db_manager.list_products.return_value = [
            {
                'product_id': 1,
                'name': 'Test Product',
                'category': 'blank',
                'quantity': 10,
                'cost_price': 5.0,
                'selling_price': 10.0,
                'sku': 'TP001'
            }
        ]
        bot.db_manager.execute_query.return_value = [
            {
                'backup_id': 1,
                'filename': 'backup_20250326.db',
                'location': 'data/backups',
                'size': 1024,
                'timestamp': datetime.now().isoformat()
            }
        ]
        bot.get_channel = MagicMock(return_value=MagicMock())
        return bot
    
    @pytest.fixture
    def backup_cog(self, mock_bot):
        """Create a BackupCog instance with a mock bot"""
        with patch.object(BackupCog, '_scheduled_backup_task', return_value=asyncio.Future()):
            cog = BackupCog(mock_bot)
            cog.backup_task = MagicMock()
            return cog
    
    @pytest.mark.asyncio
    async def test_create_backup(self, backup_cog, mock_bot):
        """Test the _create_backup method"""
        # Mock context
        ctx = MagicMock()
        ctx.send = AsyncMock()
        
        # Mock os.path functions to avoid file not found errors
        with patch('os.path.getsize', return_value=1024), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.basename', return_value='backup.db'):
            
            # Test with backup channel not set
            backup_cog.backup_channel_id = 0
            result = await backup_cog._create_backup(ctx)
            
            # Verify backup was created
            assert result == "test/path/backup.db"
            mock_bot.db_manager.backup_database.assert_called_once()
            ctx.send.assert_called_once()
            
            # Reset mocks
            mock_bot.db_manager.backup_database.reset_mock()
            ctx.send.reset_mock()
            
            # Test with backup channel set
            backup_cog.backup_channel_id = 123456789
            channel = mock_bot.get_channel.return_value
            channel.send = AsyncMock()
            
            # Mock open to avoid file not found
            with patch('builtins.open', mock_open(read_data=b'test data')):
                result = await backup_cog._create_backup(ctx)
                
                # Verify backup was created and uploaded
                assert result == "test/path/backup.db"
                mock_bot.db_manager.backup_database.assert_called_once()
                mock_bot.get_channel.assert_called_once_with(123456789)
                channel.send.assert_called_once()
                ctx.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_inventory_snapshot(self, backup_cog, mock_bot):
        """Test the _generate_inventory_snapshot method"""
        products = mock_bot.db_manager.list_products.return_value
        
        # Generate snapshot
        csv_data = await backup_cog._generate_inventory_snapshot(products)
        
        # Verify CSV format
        assert isinstance(csv_data, str)
        assert "product_id,name,category" in csv_data
        assert "Test Product,blank" in csv_data
        assert "snapshot_date" in csv_data
    
    @pytest.mark.asyncio
    async def test_backup_command(self, backup_cog):
        """Test the backup command"""
        # Mock context
        ctx = MagicMock()
        ctx.send = AsyncMock()
        
        # Mock _create_backup
        backup_cog._create_backup = AsyncMock()
        
        # Call the method directly (not through command decorator)
        await backup_cog.backup_command.callback(backup_cog, ctx)
        
        # Verify
        ctx.send.assert_called_once()
        backup_cog._create_backup.assert_called_once_with(ctx)
    @pytest.mark.asyncio
    async def test_list_backups_command(self, backup_cog, mock_bot):
        """Test the list_backups command"""
        # Mock context
        ctx = MagicMock()
        ctx.send = AsyncMock()
        
        # Call the method directly (not through command decorator)
        await backup_cog.list_backups_command.callback(backup_cog, ctx)
        
        # Verify
        mock_bot.db_manager.execute_query.assert_called_once()
        ctx.send.assert_called_once()
        
        # Verify embed was created
        args, kwargs = ctx.send.call_args
        assert 'embed' in kwargs
        embed = kwargs['embed']
        assert isinstance(embed, discord.Embed)
        assert "Database Backups" in embed.title
        assert "Database Backups" in embed.title
    
    @pytest.mark.asyncio
    async def test_inventory_snapshot_command(self, backup_cog, mock_bot):
        """Test the inventory_snapshot command"""
        # Mock context
        ctx = MagicMock()
        ctx.send = AsyncMock()
        
        # Call the method directly (not through command decorator)
        await backup_cog.inventory_snapshot_command.callback(backup_cog, ctx)
        
        # Verify
        mock_bot.db_manager.list_products.assert_called_once()
        ctx.send.assert_called()
        
        # Verify file was created
        args, kwargs = ctx.send.call_args_list[1]
        assert 'file' in kwargs
        assert isinstance(kwargs['file'], discord.File)
        assert 'embed' in kwargs
        assert isinstance(kwargs['embed'], discord.Embed)
    
    @pytest.mark.asyncio
    async def test_backup_channel_command(self, backup_cog):
        """Test the backup_channel command"""
        # Mock context
        ctx = MagicMock()
        ctx.send = AsyncMock()
        
        # Test with no channel provided
        await backup_cog.backup_channel_command.callback(backup_cog, ctx)
        ctx.send.assert_called_once()
        
        # Reset mock
        ctx.send.reset_mock()
        
        # Test with channel provided
        channel = MagicMock()
        channel.id = 123456789
        channel.mention = "#backup-channel"
        channel.send = AsyncMock()
        
        await backup_cog.backup_channel_command.callback(backup_cog, ctx, channel)
        
        # Verify channel was set
        assert backup_cog.backup_channel_id == 123456789
        ctx.send.assert_called()
        channel.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_backup_schedule_command(self, backup_cog):
        """Test the backup_schedule command"""
        # Mock context
        ctx = MagicMock()
        ctx.send = AsyncMock()
        
        # Mock backup_task._when to return a number
        backup_cog.backup_task._when = asyncio.get_event_loop().time() + 3600  # 1 hour from now
        
        # Test with no interval provided
        await backup_cog.backup_schedule_command.callback(backup_cog, ctx)
        ctx.send.assert_called_once()
        
        # Reset mock
        ctx.send.reset_mock()
        
        # Test with interval provided - disable backups
        with patch.object(backup_cog, '_scheduled_backup_task'):
            # Set new interval to 0 (disable backups)
            await backup_cog.backup_schedule_command.callback(backup_cog, ctx, 0)
            
            # Verify
            assert backup_cog.backup_interval_hours == 0
            ctx.send.assert_called_once()
            
        # Reset mock
        ctx.send.reset_mock()
        
        # Test with interval provided - enable backups
        with patch.object(backup_cog, '_scheduled_backup_task'), \
             patch.object(backup_cog.bot.loop, 'create_task', return_value=MagicMock()):
            # Ensure backup_task exists and has a cancel method
            backup_cog.backup_task = MagicMock()
            backup_cog.backup_task.cancel = MagicMock()
            
            # Set new interval
            await backup_cog.backup_schedule_command.callback(backup_cog, ctx, 12)
            
            # Verify
            assert backup_cog.backup_interval_hours == 12
            ctx.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_backup_retention_command(self, backup_cog):
        """Test the backup_retention command"""
        # Mock context
        ctx = MagicMock()
        ctx.send = AsyncMock()
        
        # Test with no days provided
        await backup_cog.backup_retention_command.callback(backup_cog, ctx)
        ctx.send.assert_called_once()
        
        # Reset mock
        ctx.send.reset_mock()
        
        # Test with days provided
        with patch.object(backup_cog, '_cleanup_old_backups', AsyncMock()):
            # Set new retention period
            await backup_cog.backup_retention_command.callback(backup_cog, ctx, 15)
            
            # Verify
            assert backup_cog.backup_retention_days == 15
            ctx.send.assert_called_once()
            backup_cog._cleanup_old_backups.assert_called_once()