import sqlite3
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

def sanitize_input(value: str) -> str:
    if not value:
        return value
    dangerous_prefixes = ['=', '+', '-', '@']
    if any(value.startswith(p) for p in dangerous_prefixes):
        return "'" + value
    return value

def sanitize_for_csv(value: str) -> str:
    if not value:
        return value
    dangerous_prefixes = ['=', '+', '-', '@']
    if any(value.startswith(p) for p in dangerous_prefixes):
        return "'" + value
    return value

def validate_field_not_blank(value: Any, current_value: Any) -> Any:
    if value is None or (isinstance(value, str) and value.strip() == ''):
        return current_value
    return value

def parse_name(name: str) -> Tuple[Optional[str], Optional[str]]:
    if not name:
        return None, None
    
    name = name.strip()
    
    if ',' in name:
        parts = name.split(',', 1)
        last = parts[0].strip()
        first = parts[1].strip()
        return first, last
    else:
        parts = name.split()
        if len(parts) >= 2:
            first = parts[0]
            last = ' '.join(parts[1:])
            return first, last
    
    return None, name

def find_member_by_scan(conn, scan_value: str) -> Dict[str, Any]:
    cursor = conn.cursor()
    results = []
    
    scan_value = sanitize_input(scan_value.strip())
    
    cursor.execute("SELECT * FROM members WHERE membership_number = ?", (scan_value,))
    row = cursor.fetchone()
    if row:
        return {"status": "verified", "member": dict(row), "multiple": []}
    
    cursor.execute("SELECT * FROM members WHERE email = ?", (scan_value,))
    row = cursor.fetchone()
    if row:
        return {"status": "verified", "member": dict(row), "multiple": []}
    
    cursor.execute("SELECT * FROM members WHERE name = ?", (scan_value,))
    rows = cursor.fetchall()
    if len(rows) == 1:
        return {"status": "verified", "member": dict(rows[0]), "multiple": []}
    elif len(rows) > 1:
        return {"status": "multiple_matches", "member": None, "multiple": [dict(r) for r in rows]}
    
    first, last = parse_name(scan_value)
    if first and last:
        cursor.execute("SELECT * FROM members WHERE first_name = ? AND last_name = ?", (first, last))
        rows = cursor.fetchall()
        if len(rows) == 1:
            return {"status": "verified", "member": dict(rows[0]), "multiple": []}
        elif len(rows) > 1:
            return {"status": "multiple_matches", "member": None, "multiple": [dict(r) for r in rows]}
    
    cursor.execute("SELECT * FROM members WHERE name LIKE ?", (f"%{scan_value}%",))
    rows = cursor.fetchall()
    if len(rows) == 1:
        return {"status": "verified", "member": dict(rows[0]), "multiple": []}
    elif len(rows) > 1:
        return {"status": "multiple_matches", "member": None, "multiple": [dict(r) for r in rows]}
    
    return {"status": "not_found", "member": None, "multiple": []}

def update_member_usage(conn, member_id: int, amount: float = 1.0):
    cursor = conn.cursor()
    cursor.execute("UPDATE members SET amount_used = amount_used + ?, last_updated = ? WHERE id = ?",
                   (amount, datetime.utcnow().isoformat(), member_id))
    conn.commit()

def update_member_field(conn, member_id: int, field: str, value: Any):
    allowed_fields = ['name', 'email', 'membership_number', 'first_name', 'last_name',
                     'membership_type', 'amount_used', 'includes_cart', 'includes_range']
    
    if field not in allowed_fields:
        raise ValueError(f"Field {field} not allowed")
    
    if field in ['includes_cart', 'includes_range']:
        value = bool(value)
    elif field in ['name', 'email', 'membership_number', 'first_name', 'last_name', 'membership_type']:
        value = sanitize_input(str(value)) if value else value
    
    cursor = conn.cursor()
    cursor.execute("SELECT " + field + " FROM members WHERE id = ?", (member_id,))
    current = cursor.fetchone()
    if current:
        value = validate_field_not_blank(value, current[field])
    
    cursor.execute(f"UPDATE members SET {field} = ?, last_updated = ? WHERE id = ?",
                   (value, datetime.now(timezone.utc).isoformat(), member_id))
    conn.commit()

def get_all_members(conn) -> List[Dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members ORDER BY name")
    return [dict(row) for row in cursor.fetchall()]

def get_member_by_id(conn, member_id: int) -> Optional[Dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE id = ?", (member_id,))
    row = cursor.fetchone()
    return dict(row) if row else None
