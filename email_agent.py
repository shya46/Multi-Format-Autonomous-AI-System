def process_email(text: str) -> dict:
    # Dummy structured extraction logic
    sender = "unknown@example.com"
    urgency = "low"
    tone = "neutral"

    # Simple keyword-based detection (expand as needed)
    if "urgent" in text.lower():
        urgency = "high"
    if "complaint" in text.lower():
        tone = "angry"
    elif "thank you" in text.lower():
        tone = "polite"

    return {
        "sender": sender,
        "urgency": urgency,
        "tone": tone
    }
