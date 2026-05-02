import pytest
from app.services.scan_logger import log_scan, get_scan_history, get_scan_history_path
import tempfile
import os

def test_log_scan_verified(conn):
    log_scan(conn, 'MBR001', 'verified', 1, {'name': 'John Doe', 'membership_number': 'MBR001'})
    
    history = get_scan_history(conn, 10, 0)
    assert len(history) == 1
    assert history[0]['scan_value'] == 'MBR001'
    assert history[0]['result'] == 'verified'
    assert history[0]['matched_member_id'] == 1

def test_log_scan_not_found(conn):
    log_scan(conn, 'INVALID', 'not_found')
    
    history = get_scan_history(conn, 10, 0)
    assert len(history) == 1
    assert history[0]['scan_value'] == 'INVALID'
    assert history[0]['result'] == 'not_found'
    assert history[0]['matched_member_id'] is None

def test_log_scan_multiple_matches(conn):
    log_scan(conn, 'John', 'multiple_matches')
    
    history = get_scan_history(conn, 10, 0)
    assert len(history) == 1
    assert history[0]['result'] == 'multiple_matches'

def test_get_scan_history_pagination(conn):
    for i in range(20):
        log_scan(conn, f'SCAN{i}', 'verified', i+1)
    
    history = get_scan_history(conn, 5, 0)
    assert len(history) == 5
    
    history2 = get_scan_history(conn, 5, 5)
    assert len(history2) == 5
    assert history[0]['scan_value'] != history2[0]['scan_value']

def test_log_scan_csv_export(conn):
    from app.services.scan_logger import get_scan_history_path
    import csv
    
    csv_path = get_scan_history_path()
    if os.path.exists(csv_path):
        os.remove(csv_path)
    
    log_scan(conn, 'MBR001', 'verified', 1, {'name': 'John Doe'})
    
    assert os.path.exists(csv_path)
    
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)
        assert len(rows) >= 2
        assert rows[0] == ['timestamp', 'scan_value', 'result', 'member_id', 'member_summary']

def test_scan_history_path_creation():
    from app.services.scan_logger import get_scan_history_path
    path = get_scan_history_path()
    assert os.path.exists(os.path.dirname(path))
