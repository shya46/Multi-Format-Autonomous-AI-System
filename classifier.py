# classifier.py

def classify_format(filename: str) -> str:
    ext = filename.lower().split('.')[-1]
    if ext == 'pdf':
        return 'PDF'
    elif ext == 'json':
        return 'JSON'
    elif ext in ['txt', 'eml']:
        return 'Email'
    else:
        return 'Unknown'

def classify_intent(text: str) -> str:
    text = text.lower()
    if "invoice" in text:
        return "Invoice"
    elif "rfq" in text or "quote" in text:
        return "RFQ"
    elif "complaint" in text or "issue" in text:
        return "Complaint"
    elif "gdpr" in text or "fda" in text or "regulation" in text:
        return "Regulation"
    elif "fraud" in text or "suspicious" in text:
        return "Fraud Risk"
    else:
        return "Unknown"
