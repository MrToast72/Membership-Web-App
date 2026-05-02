import pytest
import sqlite3
import tempfile
import os
from pathlib import Path

@pytest.fixture(scope='function')
def db_path():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)

@pytest.fixture(scope='function')
def conn(db_path):
    os.environ['SQLITE_DB_PATH'] = db_path
    os.environ['BACKUP_DIR'] = tempfile.mkdtemp()
    
    from app.database import get_connection, init_db
    init_db()
    connection = get_connection()
    yield connection
    connection.close()
    if 'SQLITE_DB_PATH' in os.environ:
        del os.environ['SQLITE_DB_PATH']
    if 'BACKUP_DIR' in os.environ:
        del os.environ['BACKUP_DIR']

@pytest.fixture
def sample_member():
    return {
        'membership_number': 'MBR001',
        'name': 'John Doe',
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john@example.com',
        'membership_type': 'Standard',
        'amount_used': 0,
        'includes_cart': False,
        'includes_range': True
    }
