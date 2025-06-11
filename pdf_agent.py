from pathlib import Path
from typing import Dict, List, Any
import re
import pdfplumber
from memory import insert_agent_trace

# -----------------------------
# PDF Agent – full pipeline
# -----------------------------
# • Opens the PDF via pdfplumber
# • Extracts raw text for keyword search
# • Parses tables for line‑item invoices (description | qty | price)
# • Calculates invoice total (table sum vs regex fallback)
# • Flags compliance keywords (GDPR, FDA, HIPAA, FCA)
# • Flags high‑value invoices > 10_000
# • Persists full trace to SQLite shared memory
# -----------------------------

KEYWORDS = {"GDPR", "FDA", "HIPAA", "FCA"}
TOTAL_REGEX = re.compile(r"total(?:\s+amount)?[:\s]*\$?([0-9,]+\.?[0-9]{0,2})", re.IGNORECASE)


def _extract_tables(pdf: pdfplumber.PDF) -> List[List[List[str]]]:
    """Return all tables on every page (raw)."""
    all_tables: List[List[List[str]]] = []
    for page in pdf.pages:
        tables = page.extract_tables() or []
        all_tables.extend(tables)
    return all_tables


def _parse_line_items(tables: List[List[List[str]]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for tbl in tables:
        for row in tbl:
            # Clean each cell
            row = [c.strip() if isinstance(c, str) else "" for c in row]
            if len(row) < 3:
                continue
            desc, qty_raw, price_raw = row[:3]
            qty   = re.sub(r"[^0-9]", "", qty_raw)
            price = re.sub(r"[^0-9.]", "", price_raw)
            if not desc or not qty or not price:
                continue
            try:
                items.append({
                    "description": desc,
                    "quantity"   : int(qty),
                    "price"      : float(price)
                })
            except ValueError:
                continue
    return items


def _sum_items(items: List[Dict[str, Any]]) -> float:
    return sum(i["quantity"] * i["price"] for i in items)


def process_pdf(filepath: str) -> Dict[str, Any]:
    """Main entry: filepath → structured analysis dict."""
    path = Path(filepath)
    text = ""
    line_items: List[Dict[str, Any]] = []
    invoice_total = 0.0

    # 1) Extract text + tables via pdfplumber
    try:
        with pdfplumber.open(path) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            tbls = _extract_tables(pdf)
            line_items = _parse_line_items(tbls)
    except Exception:
        # If pdfplumber fails, keep line_items empty and text=""
        pass

    # 2) Determine invoice total
    if line_items:
        invoice_total = _sum_items(line_items)
    if invoice_total == 0.0 and text:
        m = TOTAL_REGEX.search(text)
        if m:
            try:
                invoice_total = float(m.group(1).replace(",", ""))
            except ValueError:
                invoice_total = 0.0

    # 3) Keyword flagging
    flagged_terms = [kw for kw in KEYWORDS if kw.lower() in text.lower()] if text else []

    # 4) Risk flag
    risk_flag = invoice_total > 10_000

    agent_result: Dict[str, Any] = {
        "invoice_total": invoice_total,
        "line_items"   : line_items,
        "flagged_terms": flagged_terms,
        "risk_flag"    : risk_flag,
        "valid"        : True if text else False
    }

    # 5) Persist trace
    insert_agent_trace(
        filename     = path.name,
        file_type    = "PDF",
        intent       = "InvoiceAnalysis" if "invoice" in text.lower() else "RegulationCheck",
        agent_result = agent_result,
        action_taken = "risk_logged" if risk_flag else "log_only",
    )

    return agent_result

# Quick CLI test
if __name__ == "__main__":
    import sys, json
    if len(sys.argv) != 2:
        print("Usage: python pdf_agent.py <file.pdf>")
        sys.exit(1)
    result = process_pdf(sys.argv[1])
    print(json.dumps(result, indent=2))
