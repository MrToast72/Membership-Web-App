import pytest
from app.database import (
    init_db, get_connection, add_audit_entry, verify_audit_chain,
    compute_hash, get_db_hash, create_backup
)
import tempfile
import os

def test_audit_chain_integrity(conn):
    entry1_hash = None
    
    add_audit_entry(conn, "test_event1", {"data": "test1"})
    
    entry1 = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
    entry1_hash = entry1['hash_chain_value']
    
    add_audit_entry(conn, "test_event2", {"data": "test2"})
    
    assert verify_audit_chain(conn) == True

def test_audit_chain_broken(conn):
    add_audit_entry(conn, "test_event1", {"data": "test1"})
    add_audit_entry(conn, "test_event2", {"data": "test2"})
    
    cursor = conn.cursor()
    cursor.execute("UPDATE audit_log SET hash_chain_value = 'tampered' WHERE id = 1")
    conn.commit()
    
    assert verify_audit_chain(conn) == False

def test_compute_hash_first_entry():
    payload = '{"test": "data"}'
    hash_value = compute_hash(payload, None)
    assert hash_value is not None
    assert len(hash_value) == 64

def test_compute_hash_chained():
    payload = '{"test": "data"}'
    prev_hash = 'previous_hash_value'
    hash_value = compute_hash(payload, prev_hash)
    assert hash_value is not None
    assert len(hash_value) == 64

def test_create_backup(db_path):
    from app.database import DB_PATH, BACKUP_DIR
    import tempfile
    
    original_db_path = DB_PATH
    original_backup_dir = BACKUP_DIR
    
    temp_dir = tempfile.mkdtemp()
    backup_dir = os.path.join(temp_dir, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    os.environ['SQLITE_DB_PATH'] = db_path
    os.environ['BACKUP_DIR'] = backup_dir
    
    init_db()
    
    backup_path = create_backup()
    assert backup_path is not None
    assert os.path.exists(backup_path)
    
    os.unsetenv('SQLITE_DB_PATH')
    os.unsetenv('BACKUP_DIR')

def test_get_db_hash(db_path):
    from app.database import DB_PATH
    os.environ['SQLITE_DB_PATH'] = db_path
    init_db()
    
    hash1 = get_db_hash()
    assert hash1 != ""
    assert len(hash1) == 64
    
    os.unsetenv('SQLITE_DB_PATH')

def test_get_db_hash_no_file():
    from app.database import DB_PATH
    os.environ['SQLITE_DB_PATH'] = '/nonexistent/path/db.db'
    
    hash_value = get_db_hash()
    assert hash_value == ""
    
    os.unsetenv('SQLITE_DB_PATH')
