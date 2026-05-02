import pytest
from app.services.membership_service import (
    find_member_by_scan, update_member_usage, update_member_field,
    get_all_members, get_member_by_id, sanitize_input, parse_name
)
from app.database import get_connection

def test_sanitize_input_dangerous_prefixes():
    assert sanitize_input('=cmd') == "'=cmd"
    assert sanitize_input('+123') == "'+123"
    assert sanitize_input('-test') == "'-test"
    assert sanitize_input('@mention') == "'@mention"
    assert sanitize_input('safe text') == 'safe text'
    assert sanitize_input('') == ''

def test_parse_name_first_last():
    first, last = parse_name('John Doe')
    assert first == 'John'
    assert last == 'Doe'

def test_parse_name_last_first():
    first, last = parse_name('Doe, John')
    assert first == 'John'
    assert last == 'Doe'

def test_parse_name_single():
    first, last = parse_name('Cher')
    assert first is None
    assert last == 'Cher'

def test_find_member_by_scan_membership_number(conn):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO members (membership_number, name, email, membership_type) VALUES (?, ?, ?, ?)",
        ('MBR001', 'John Doe', 'john@example.com', 'Standard')
    )
    conn.commit()
    
    result = find_member_by_scan(conn, 'MBR001')
    assert result['status'] == 'verified'
    assert result['member']['membership_number'] == 'MBR001'

def test_find_member_by_scan_email(conn):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO members (membership_number, name, email, membership_type) VALUES (?, ?, ?, ?)",
        ('MBR001', 'John Doe', 'john@example.com', 'Standard')
    )
    conn.commit()
    
    result = find_member_by_scan(conn, 'john@example.com')
    assert result['status'] == 'verified'
    assert result['member']['email'] == 'john@example.com'

def test_find_member_by_scan_name(conn):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO members (membership_number, name, email, membership_type) VALUES (?, ?, ?, ?)",
        ('MBR001', 'John Doe', 'john@example.com', 'Standard')
    )
    conn.commit()
    
    result = find_member_by_scan(conn, 'John Doe')
    assert result['status'] == 'verified'
    assert result['member']['name'] == 'John Doe'

def test_find_member_multiple_matches(conn):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO members (membership_number, name, email, membership_type) VALUES (?, ?, ?, ?)",
        ('MBR001', 'John Doe', 'john@example.com', 'Standard')
    )
    cursor.execute(
        "INSERT INTO members (membership_number, name, email, membership_type) VALUES (?, ?, ?, ?)",
        ('MBR002', 'John Doe', 'john2@example.com', 'Premium')
    )
    conn.commit()
    
    result = find_member_by_scan(conn, 'John Doe')
    assert result['status'] == 'multiple_matches'
    assert len(result['multiple']) == 2

def test_find_member_not_found(conn):
    result = find_member_by_scan(conn, 'nonexistent')
    assert result['status'] == 'not_found'

def test_update_member_usage(conn):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO members (membership_number, name, amount_used) VALUES (?, ?, ?)",
        ('MBR001', 'John Doe', 0)
    )
    conn.commit()
    
    member_id = cursor.lastrowid
    update_member_usage(conn, member_id, 1.0)
    
    cursor.execute("SELECT amount_used FROM members WHERE id = ?", (member_id,))
    row = cursor.fetchone()
    assert row['amount_used'] == 1.0

def test_update_member_field(conn):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO members (membership_number, name, email) VALUES (?, ?, ?)",
        ('MBR001', 'John Doe', 'john@example.com')
    )
    conn.commit()
    
    member_id = cursor.lastrowid
    update_member_field(conn, member_id, 'email', 'new@example.com')
    
    cursor.execute("SELECT email FROM members WHERE id = ?", (member_id,))
    row = cursor.fetchone()
    assert row['email'] == 'new@example.com'

def test_update_member_field_blank_keeps_original(conn):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO members (membership_number, name, email) VALUES (?, ?, ?)",
        ('MBR001', 'John Doe', 'john@example.com')
    )
    conn.commit()
    
    member_id = cursor.lastrowid
    update_member_field(conn, member_id, 'email', '')
    
    cursor.execute("SELECT email FROM members WHERE id = ?", (member_id,))
    row = cursor.fetchone()
    assert row['email'] == 'john@example.com'

def test_get_all_members(conn):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO members (membership_number, name) VALUES (?, ?)",
        ('MBR001', 'John Doe')
    )
    cursor.execute(
        "INSERT INTO members (membership_number, name) VALUES (?, ?)",
        ('MBR002', 'Jane Smith')
    )
    conn.commit()
    
    members = get_all_members(conn)
    assert len(members) == 2

def test_get_member_by_id(conn):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO members (membership_number, name) VALUES (?, ?)",
        ('MBR001', 'John Doe')
    )
    conn.commit()
    
    member_id = cursor.lastrowid
    member = get_member_by_id(conn, member_id)
    assert member is not None
    assert member['name'] == 'John Doe'

def test_get_member_by_id_not_found(conn):
    member = get_member_by_id(conn, 999)
    assert member is None
