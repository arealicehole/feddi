# Command Aliases Documentation

This document provides a comprehensive list of all command aliases implemented in the AccountME Discord Bot.

## Inventory Management Commands

| Primary Command | Aliases |
|----------------|---------|
| `!inventory` | `!inv`, `!stock` |
| `!addproduct` | `!newproduct`, `!additem` |
| `!adjustinventory` | `!adjust`, `!updatestock` |
| `!updateproduct` | `!editproduct`, `!modifyproduct` |
| `!deleteproduct` | `!removeproduct`, `!delproduct` |
| `!inventoryreport` | `!invreport`, `!stockreport` |

## Financial Commands

| Primary Command | Aliases |
|----------------|---------|
| `!expenses` | `!exp`, `!viewexpenses` |
| `!addexpense` | `!newexpense`, `!expenseadd` |
| `!uploadreceipt` | `!receipt`, `!scanreceipt` |
| `!editexpense` | `!updateexpense`, `!modifyexpense` |
| `!deleteexpense` | `!removeexpense`, `!delexpense` |
| `!addsale` | `!newsale`, `!recordsale` |
| `!sales` | `!viewsales`, `!salesreport` |
| `!financialreport` | `!finreport`, `!reportfinance` |
| `!exportdata` | `!export`, `!dataexport` |
| `!report` | `!query`, `!askfor` |

## Backup Commands

| Primary Command | Aliases |
|----------------|---------|
| `!backup` | `!createbackup`, `!backupnow` |
| `!listbackups` | `!backups`, `!showbackups` |
| `!restore` | `!restorebackup`, `!dbrestore` |
| `!inventorysnapshot` | `!snapshot`, `!invsnapshot` |
| `!backupstatus` | `!backupinfo`, `!backupstate` |

## Usage

All aliases function exactly the same as their primary command counterparts. Users can use whichever form they find most intuitive or easiest to remember.

For example:
- `!inv TS001` works the same as `!inventory TS001`
- `!exp month` works the same as `!expenses month`
- `!backups` works the same as `!listbackups`

## Implementation Details

Aliases are implemented using Discord.py's command decorator:

```python
@commands.command(name="primarycommand", aliases=["alias1", "alias2"])
async def command_function(self, ctx, ...):
    # Command implementation
```

This allows for multiple ways to invoke the same command functionality.