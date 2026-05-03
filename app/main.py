from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import os
from pathlib import Path

from app.database import get_connection, init_db, create_backup, add_audit_entry, verify_audit_chain
from app.services.membership_service import (
    find_member_by_scan, update_member_usage, update_member_field,
    get_all_members, get_member_by_id, sanitize_input
)
from app.services.excel_import import import_excel_file
from app.services.scan_logger import log_scan, get_scan_history, get_scan_history_path

app = FastAPI(title="Membership Verifier")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.on_event("startup")
async def startup_event():
    init_db()
    conn = get_connection()
    try:
        if not verify_audit_chain(conn):
            print("WARNING: Audit chain verification failed! Data integrity may be compromised.")
        
        add_audit_entry(conn, "app_startup", {"event": "Application started"})
    finally:
        conn.close()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/verify")
async def verify_member(request: Request):
    form = await request.form()
    scan_value = form.get("scan_value", "").strip()
    
    if not scan_value:
        return JSONResponse({"status": "error", "message": "No scan value provided"})
    
    conn = get_connection()
    try:
        result = find_member_by_scan(conn, scan_value)
        
        if result["status"] == "verified":
            member = result["member"]
            update_member_usage(conn, member["id"])
            log_scan(conn, scan_value, "verified", member["id"], member)
            add_audit_entry(conn, "scan_verified", {"member_id": member["id"], "scan_value": scan_value})
            return JSONResponse({
                "status": "verified",
                "member": member
            })
        elif result["status"] == "multiple_matches":
            log_scan(conn, scan_value, "multiple_matches")
            return JSONResponse({
                "status": "multiple_matches",
                "members": result["multiple"]
            })
        else:
            log_scan(conn, scan_value, "not_found")
            return JSONResponse({"status": "not_found"})
    finally:
        conn.close()

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    conn = get_connection()
    try:
        members = get_all_members(conn)
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "members": members
        })
    finally:
        conn.close()

@app.get("/api/member/{member_id}")
async def get_member(member_id: int):
    conn = get_connection()
    try:
        member = get_member_by_id(conn, member_id)
        if member:
            return JSONResponse(member)
        return JSONResponse({"status": "error", "message": "Member not found"}, status_code=404)
    finally:
        conn.close()

@app.post("/api/member/{member_id}/edit")
async def edit_member(member_id: int, request: Request):
    form = await request.form()
    conn = get_connection()
    try:
        original_hash = acquire_change_lock()
        
        if not verify_change_lock(original_hash):
            release_change_lock()
            return JSONResponse({"status": "error", "message": "Database changed during operation"})
        
        for field in ['name', 'email', 'membership_number', 'membership_type', 'amount_used']:
            if field in form:
                value = sanitize_input(form[field])
                if field == 'amount_used':
                    value = float(value) if value else 0
                update_member_field(conn, member_id, field, value)
        
        for bool_field in ['includes_cart', 'includes_range']:
            value = bool(form.get(bool_field))
            update_member_field(conn, member_id, bool_field, value)
        
        add_audit_entry(conn, "member_edited", {"member_id": member_id, "changes": dict(form)})
        release_change_lock()
        return JSONResponse({"status": "success"})
    finally:
        conn.close()

@app.post("/api/import")
async def import_excel(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xlsm')):
        return JSONResponse({"status": "error", "message": "Invalid file type"})
    
    create_backup()
    
    temp_path = f"/tmp/temp_{file.filename}"
    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)
        print(f"Saved file to {temp_path}, size: {len(content)} bytes")
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"Failed to save file: {str(e)}"})
    
    conn = get_connection()
    try:
        try:
            results = import_excel_file(conn, temp_path)
            add_audit_entry(conn, "excel_import", {"filename": file.filename, "results": results})
            print(f"Import results: {results}")
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"Import error: {error_detail}")
            return JSONResponse({"status": "error", "message": f"Import failed: {str(e)}", "detail": error_detail})
        
        return JSONResponse({"status": "success", "results": results})
    finally:
        try:
            os.remove(temp_path)
        except:
            pass
        conn.close()

@app.get("/api/scan-history")
async def scan_history(limit: int = 100, offset: int = 0):
    conn = get_connection()
    try:
        history = get_scan_history(conn, limit, offset)
        return JSONResponse({"history": history})
    finally:
        conn.close()

@app.get("/admin/export-scan-history")
async def export_scan_history(request: Request):
    csv_path = get_scan_history_path()
    if not os.path.exists(csv_path):
        return HTMLResponse(content="No scan history found", status_code=404)
    return FileResponse(
        path=csv_path,
        filename="scan_history.csv",
        media_type="text/csv"
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/version")
async def version():
    return {"version": "2026-05-03-v3", "commit": "4262b11"}
