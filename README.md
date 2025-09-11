# MedicalDocAI

A PyQt-based clinical assistant with NLP, voice input (Whisper), structured extraction, and PDF/JSON reporting.

## Quick Start
```bash
# macOS / Linux
./scripts/dev_run.sh

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Build
- macOS: `./scripts/build_mac.sh`
- Windows: `powershell -ExecutionPolicy Bypass -File scripts/build_win.ps1`
- 
# SmartDoctorOrganizer

A clinical assistant desktop application that helps doctors:
- Extract patient information from free text/voice.
- Manage appointments and billing.
- Generate reports and statistics.

⚠️ Clinical Compliance:
- All patient data is encrypted at rest (SQLCipher).
- Role-based authentication is enforced.
- This software must run in a GDPR/HIPAA-compliant environment.
