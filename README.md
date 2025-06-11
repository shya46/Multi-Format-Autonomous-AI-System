# Multi-Format-Autonomous-AI-System
Intelligent Classification, Contextual Decisioning & Chained Actions

# Project Summary
This project implements a multi-agent AI system that can handle unstructured and semi-structured files such as Emails, PDFs, and JSON webhooks. It classifies each input’s format and intent, processes it using specialized agents, and triggers contextual follow-up actions (e.g., escalation or risk alerts). All decisions and extracted data are logged in a shared memory store (SQLite) for traceability.

 # Key Features
1. Format & Intent Classification: Automatically identifies file format and determines the business intent (e.g., invoice, complaint).

1. Agent-Based Processing: Separate agents for Email, PDF, and JSON, each with tailored logic.

3. Chained Action Triggering: Context-based actions like escalating to CRM or alerting risk systems.

4. Memory Store: All events logged with timestamp, decisions, and triggered actions.

# Technologies Used
1. Python 3.9

2. FastAPI for routing and simulation

3. SQLite for shared memory

4. pdfplumber for PDF parsing

5. Regex and native parsing for Emails & JSON

6 Simulated REST Actions using simple print or POST simulation

# How to Run the Project

1. Install dependencies
   
pip install -r requirements.txt

2. Start API Server

uvicorn ui:app --reload
Opens at: http://127.0.0.1:8000 (no UI included — used for simulation/API tests)

4. Run File Processing Manually

You can use the process_file() function directly:

from process import process_file
process_file("sample_inputs/sample_invoice.pdf")
process_file("sample_inputs/mail.txt")
process_file("sample_inputs/payload.json")

5. View Logs in Memory
All extracted fields, decisions, and triggered actions are stored in memory.db.
Use SQLite browser or CLI to view:
sqlite3 memory.db
SELECT * FROM traces;

# Sample Inputs
File Name              	 Type	           Intent	Notes
sample_invoice.pdf	      PDF	            Invoice	Total > ₹10,000, mentions GDPR
mail.txt	                Email	          Complaint	Angry tone, high urgency
payload.json	            JSON	           RFQ	Missing required field (flags anomaly)

# Example Console Output

[Classifier] Format: PDF | Intent: Invoice
[PDF Agent] Extracted total: ₹12,500.00
[PDF Agent] Found keywords: ['GDPR']
[Action Router] Triggered: POST /risk_alert
[Memory] Trace saved to memory.db

# Diagram of Agent Flow and Chaining 

📥 INPUT RECEIVED
   └──> Classifier Agent
         ├── Detects Format: [Email | PDF | JSON]
         └── Detects Intent: [Invoice | Complaint | RFQ | Regulation | Fraud Risk]

➡ Routed to Specialized Agent
   ├── Email Agent
   │     ├── Extract sender, urgency, tone
   │     └── Escalate or log based on tone + urgency
   ├── PDF Agent
   │     ├── Extract invoice total or regulation terms
   │     └── Flag if >10,000 or GDPR/FDA mentioned
   └── JSON Agent
         ├── Parse and validate schema
         └── Log alert if anomalies found

🧠 Shared Memory
   ├── Stores input metadata
   ├── Agent outputs and actions
   └── Decision trace

🔁 Action Router
   ├── Based on agent outputs:
   │     ├── POST /crm for escalation
   │     ├── POST /risk_alert for fraud/regulations
   │     └── Log for routine cases

✅ Final Output
   └── Stored + Action Logged

