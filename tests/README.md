# AccountME Discord Bot Tests

This directory contains tests for the AccountME Discord Bot. The tests are organized into unit tests and integration tests.

## Test Structure

- `unit/`: Contains unit tests for individual components
  - `test_db_manager.py`: Tests for the DatabaseManager class
  - `test_bot.py`: Tests for the main bot functionality
  - `test_help_cog.py`: Tests for the HelpCog
- `integration/`: Contains integration tests that test the interaction between components
  - `test_db_integration.py`: Tests for database operations with the bot
- `conftest.py`: Contains pytest fixtures used across multiple test files
- `test_config.py`: Contains configuration for tests

## Running Tests

To run all tests:

```bash
pytest
```

To run unit tests only:

```bash
pytest tests/unit/
```

To run integration tests only:

```bash
pytest tests/integration/
```

To run a specific test file:

```bash
pytest tests/unit/test_db_manager.py
```

To run a specific test:

```bash
pytest tests/unit/test_db_manager.py::TestDatabaseManager::test_initialization
```

## Test Coverage

To run tests with coverage:

```bash
pytest --cov=bot --cov=utils
```

To generate a coverage report:

```bash
pytest --cov=bot --cov=utils --cov-report=html
```

This will generate a coverage report in the `htmlcov` directory.

## Test Environment

The tests use a separate test database to avoid affecting the production database. The test database is created in a temporary directory and is deleted after the tests are complete.

## Adding New Tests

When adding new tests:

1. For unit tests, create a new file in the `unit/` directory
2. For integration tests, create a new file in the `integration/` directory
3. Use the existing fixtures in `conftest.py` where possible
4. Follow the naming convention: `test_*.py` for test files, `Test*` for test classes, and `test_*` for test functions