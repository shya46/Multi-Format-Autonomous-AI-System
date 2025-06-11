# main.py
# ------------------------------------------------------------------------------
# FastAPI entry-point for the Multi-Agent AI System
# ------------------------------------------------------------------------------

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
from datetime import datetime
import traceback
import sqlite3
import pdfplumber
import requests

# ──────────────────────────────────────────────────────────────────────────────
# Local imports
# ──────────────────────────────────────────────────────────────────────────────
from classifier import classify_format, classify_intent
from agents.email_agent import process_email
from agents.json_agent import process_json
from agents.pdf_agent import process_pdf
from memory import init_db, insert_agent_trace

# ──────────────────────────────────────────────────────────────────────────────
# Paths & constants
# ──────────────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH    = BASE_DIR / "memory.db"

UPLOAD_DIR.mkdir(exist_ok=True)
init_db()

app = FastAPI(title="Multi-Agent AI System")

@app.on_event("startup")
async def _startup():
    init_db()

# ──────────────────────────────────────────────────────────────────────────────
# Action Router
# ──────────────────────────────────────────────────────────────────────────────
def action_router(intent: str, format: str, result: dict) -> dict:
    try:
        if format == "Email" and intent == "Complaint":
            tone = result.get("tone", "").lower()
            urgency = result.get("urgency", "").lower()
            if tone == "angry" and urgency == "high":
                payload = {"type": "crm_escalation", "details": result}
                # Simulated POST
                requests.post("http://localhost:8000/crm/escalate", json=payload)
                return {
                    "action": "POST /crm/escalate",
                    "status": "success",
                    "details": "CRM escalation triggered"
                }
            return {"action": None, "status": "skipped", "details": "No escalation needed"}

        elif format == "PDF" and intent == "Invoice":
            if result.get("risk_flag"):
                payload = {"type": "invoice_risk", "details": result}
                # Simulated POST
                requests.post("http://localhost:8000/risk_alert", json=payload)
                return {
                    "action": "POST /risk_alert",
                    "status": "success",
                    "details": "Risk alert triggered"
                }
            return {"action": None, "status": "skipped", "details": "No action required"}

    except Exception as exc:
        return {"action": None, "status": "error", "details": str(exc)}

    return {"action": None, "status": "skipped", "details": "No matching rule"}

# ──────────────────────────────────────────────────────────────────────────────
# /upload – universal ingestion endpoint
# ──────────────────────────────────────────────────────────────────────────────
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    timestamp  = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    file_ext   = file.filename.split(".")[-1].lower()
    saved_name = f"{timestamp}_{file.filename}"
    saved_path = UPLOAD_DIR / saved_name

    # 1️⃣ Save file
    try:
        content = await file.read()
        saved_path.write_bytes(content)
    except Exception as exc:
        raise HTTPException(500, f"Unable to save file: {exc}")

    # 2️⃣ Extract text
    try:
        if file_ext == "pdf":
            with pdfplumber.open(saved_path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        elif file_ext == "json":
            text = saved_path.read_text(encoding="utf-8")
        else:
            text = content.decode("utf-8", errors="ignore")
    except Exception as exc:
        raise HTTPException(500, f"Text extraction failed: {exc}")

    # 3️⃣ Classify format + intent
    try:
        file_format = classify_format(file.filename)
        business_intent = classify_intent(text)
    except Exception as exc:
        raise HTTPException(500, f"Classification failed: {exc}")

    # 4️⃣ Agent routing
    try:
        if file_format == "Email":
            agent_result = process_email(text)
        elif file_format == "JSON":
            agent_result = process_json(text)
        elif file_format == "PDF":
            agent_result = process_pdf(text, filepath=str(saved_path))
            agent_result["valid"] = True
        else:
            agent_result = {"valid": False, "error": "Unsupported file format"}
    except Exception:
        agent_result = {
            "valid": False,
            "error": "Agent processing failed",
            "trace": traceback.format_exc()
        }

    # 5️⃣ Action routing
    router_result = action_router(business_intent, file_format, agent_result)

    # 6️⃣ Save trace
    insert_agent_trace(
        filename=saved_name,
        file_type=file_format,
        intent=business_intent,
        agent_result=agent_result,
        action_taken=router_result.get("action") or "log_only"
    )

    # 7️⃣ Return response
    return JSONResponse({
        "status": "success",
        "filename": file.filename,
        "saved_as": str(saved_path),
        "detected_format": file_format,
        "business_intent": business_intent,
        "agent_result": agent_result,
        "action_router": router_result
    })

# ──────────────────────────────────────────────────────────────────────────────
# /memory – audit endpoint
# ──────────────────────────────────────────────────────────────────────────────
@app.get("/memory")
async def read_memory(limit: int = 100):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM memory ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as exc:
        raise HTTPException(500, str(exc))
