import sqlite3
import csv
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.services.membership_service import sanitize_for_csv

def get_scan_history_path() -> str:
    if os.name == 'nt':
        base = os.environ.get('LOCALAPPDATA', '')
        path = Path(base) / 'MembershipVerifier' / 'scan_history.csv'
    elif os.name == 'posix':
        if 'darwin' in os.sys.platform:
            path = Path.home() / 'Library' / 'Application Support' / 'MembershipVerifier' / 'scan_history.csv'
        else:
            path = Path.home() / '.local' / 'share' / 'MembershipVerifier' / 'scan_history.csv'
    else:
        path = Path('data') / 'scan_history.csv'
    
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)

def log_scan(conn, scan_value: str, result: str, member_id: Optional[int] = None, 
             member_summary: Optional[Dict] = None):
    timestamp = datetime.now(timezone.utc).isoformat()
    metadata = {}
    
    if member_summary:
        metadata = {
            'name': member_summary.get('name'),
            'membership_number': member_summary.get('membership_number'),
            'email': member_summary.get('email')
        }
    
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO scan_log (timestamp, scan_value, result, matched_member_id, metadata_json)
    VALUES (?, ?, ?, ?, ?)
    """, (timestamp, scan_value, result, member_id, str(metadata) if metadata else None))
    conn.commit()
    
    csv_path = get_scan_history_path()
    file_exists = os.path.exists(csv_path)
    
    with open(csv_path, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['timestamp', 'scan_value', 'result', 'member_id', 'member_summary'])
        writer.writerow([
            sanitize_for_csv(timestamp),
            sanitize_for_csv(scan_value),
            sanitize_for_csv(result), 
            member_id or '', 
            sanitize_for_csv(str(metadata)) if metadata else ''
        ])

def get_scan_history(conn, limit: int = 100, offset: int = 0) -> List[Dict]:
    cursor = conn.cursor()
    cursor.execute("""
    SELECT sl.*, m.name as matched_name, m.membership_number
    FROM scan_log sl
    LEFT JOIN members m ON sl.matched_member_id = m.id
    ORDER BY sl.timestamp DESC
    LIMIT ? OFFSET ?
    """, (limit, offset))
    return [dict(row) for row in cursor.fetchall()]
