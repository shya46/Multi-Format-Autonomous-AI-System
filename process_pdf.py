from pathlib import Path
from typing import List, Dict, Any
import re
import pdfplumber
# Adjust the import path to your project structure
from memory import insert_agent_trace

KEYWORDS = {"GDPR", "FDA", "HIPAA", "FCA"}


def _extract_line_items(pdf: pdfplumber.PDF) -> List[Dict[str, Any]]:
    """Parse tables and return a list of line‑item dicts."""
    items: List[Dict[str, Any]] = []
    for page in pdf.pages:
        for table in page.extract_tables():
            for row in table:
                # Strip None ➜ "" and whitespace
                row = [c.strip() if isinstance(c, str) else "" for c in row]
                if len(row) < 3:
                    continue
                # Expect: description | qty | price
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


def _sum_from_items(items: List[Dict[str, Any]]) -> float:
    return sum(i["quantity"] * i["price"] for i in items)


def process_pdf(text: str, filepath: str) -> Dict[str, Any]:
    """Advanced PDF agent.

    Args:
        text: Quick‑extracted text (already done in main.py).
        filepath: Absolute/relative path to the saved PDF file.
    Returns:
        Structured analysis dict and logs trace via insert_agent_trace().
    """
    # ── 1. Baseline extraction from provided text ───────────────────────────
    invoice_total = 0.0
    flagged_terms: List[str] = [kw for kw in KEYWORDS if kw.lower() in text.lower()]

    regex_total = re.search(r"total(?:\s+amount)?[:\s]*\$?([0-9,]+\.?[0-9]{0,2})",
                            text, re.IGNORECASE)
    if regex_total:
        try:
            invoice_total = float(regex_total.group(1).replace(",", ""))
        except ValueError:
            invoice_total = 0.0

    # ── 2. Open PDF for table parsing to refine totals ─────────────────────
    line_items: List[Dict[str, Any]] = []
    try:
        with pdfplumber.open(filepath) as pdf:
            line_items = _extract_line_items(pdf)
            if line_items:
                invoice_total = max(invoice_total, _sum_from_items(line_items))
    except Exception:
        # Non‑fatal – fall back to regex total only
        pass

    # ── 3. Risk logic ──────────────────────────────────────────────────────
    risk_flag = invoice_total > 10_000

    agent_result: Dict[str, Any] = {
        "invoice_total": invoice_total,
        "line_items"   : line_items,
        "flagged_terms": flagged_terms,
        "risk_flag"    : risk_flag,
    }

    # ── 4. Persist to shared memory ────────────────────────────────────────
    filename = Path(filepath).name
    insert_agent_trace(
    filename     = filename,      # reuse the variable
    file_type    = "PDF",
    intent       = "InvoiceAnalysis",
    agent_result = agent_result,
    action_taken = "risk_logged" if risk_flag else "log_only",
    )

    return agent_result
