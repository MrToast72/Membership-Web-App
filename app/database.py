import sqlite3
import os
import hashlib
import json
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

DB_PATH = os.getenv("SQLITE_DB_PATH", "data/membership.db")
BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")
_change_lock_hash = None

def get_db_path():
    return os.getenv("SQLITE_DB_PATH", DB_PATH)

def ensure_data_dir():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)

def get_db_hash() -> str:
    db_path = get_db_path()
    if not os.path.exists(db_path):
        return ""
    try:
        with open(db_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except:
        return ""

def acquire_change_lock():
    global _change_lock_hash
    _change_lock_hash = get_db_hash()
    return _change_lock_hash

def verify_change_lock(original_hash: str) -> bool:
    current_hash = get_db_hash()
    return current_hash == original_hash or original_hash == ""

def release_change_lock():
    global _change_lock_hash
    _change_lock_hash = None

def atomic_write_sqlite(operation_func, *args, **kwargs):
    ensure_data_dir()
    temp_dir = Path(DB_PATH).parent / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    temp_db = temp_dir / f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.db"
    
    try:
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, temp_db)
        
        conn = sqlite3.connect(str(temp_db))
        conn.row_factory = sqlite3.Row
        
        try:
            result = operation_func(conn, *args, **kwargs)
            conn.commit()
            
            shutil.move(str(temp_db), DB_PATH)
            return result
        except Exception as e:
            conn.close()
            if temp_db.exists():
                temp_db.unlink()
            raise e
    except Exception as e:
        if temp_db.exists():
            temp_db.unlink()
        raise e

def get_connection():
    ensure_data_dir()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        membership_number TEXT UNIQUE,
        name TEXT,
        first_name TEXT,
        last_name TEXT,
        email TEXT,
        membership_type TEXT,
        price_paid REAL,
        paid_via TEXT,
        amount_used REAL DEFAULT 0,
        includes_cart INTEGER DEFAULT 0,
        includes_range INTEGER DEFAULT 0,
        source_sheet TEXT,
        last_updated TEXT
    )
    """)

    cursor.execute("PRAGMA table_info(members)")
    existing_columns = {row["name"] for row in cursor.fetchall()}
    if "price_paid" not in existing_columns:
        cursor.execute("ALTER TABLE members ADD COLUMN price_paid REAL")
    if "paid_via" not in existing_columns:
        cursor.execute("ALTER TABLE members ADD COLUMN paid_via TEXT")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_membership_number ON members(membership_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_email ON members(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_name ON members(name)")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scan_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        scan_value TEXT,
        result TEXT,
        matched_member_id INTEGER,
        metadata_json TEXT,
        FOREIGN KEY (matched_member_id) REFERENCES members(id)
    )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_timestamp ON scan_log(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_result ON scan_log(result)")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        event_type TEXT,
        hash_chain_value TEXT,
        previous_hash TEXT,
        payload_json TEXT
    )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
    
    conn.commit()
    conn.close()

def compute_hash(payload: str, previous_hash: Optional[str] = None) -> str:
    if previous_hash:
        data = f"{previous_hash}{payload}"
    else:
        data = payload
    return hashlib.sha256(data.encode()).hexdigest()

def get_last_audit_hash(conn) -> Optional[str]:
    cursor = conn.cursor()
    cursor.execute("SELECT hash_chain_value FROM audit_log ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    return row["hash_chain_value"] if row else None

def add_audit_entry(conn, event_type: str, payload: Dict[str, Any]):
    timestamp = datetime.now(timezone.utc).isoformat()
    payload_str = json.dumps(payload, sort_keys=True)
    previous_hash = get_last_audit_hash(conn)
    hash_value = compute_hash(payload_str, previous_hash)
    
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO audit_log (timestamp, event_type, hash_chain_value, previous_hash, payload_json)
    VALUES (?, ?, ?, ?, ?)
    """, (timestamp, event_type, hash_value, previous_hash, payload_str))
    conn.commit()

def verify_audit_chain(conn) -> bool:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_log ORDER BY id ASC")
    entries = cursor.fetchall()
    
    for entry in entries:
        payload = entry["payload_json"]
        hash_value = entry["hash_chain_value"]
        previous_hash = entry["previous_hash"]
        
        computed = compute_hash(payload, previous_hash)
        if computed != hash_value:
            return False
    
    return True

def create_backup():
    ensure_data_dir()
    if not os.path.exists(DB_PATH):
        return None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"membership_{timestamp}.db")
    
    shutil.copy2(DB_PATH, backup_path)
    return backup_path
