# Ausnya — local dev: contact form backend

This adds a tiny Flask backend to receive the contact form and send email via SMTP.

Files added
- `app.py` — Flask app exposing `POST /send` that accepts JSON payload and sends email using the SMTP server configured via environment variables.
- `requirements.txt` — required Python package(s).
- `.env.example` — example environment variables.

Setup (Windows PowerShell)

1. Create and activate a virtual environment (recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Configure environment variables (copy `.env.example` to `.env` or set in the shell):

```powershell
$env:SMTP_HOST = 'smtp.example.com'
$env:SMTP_PORT = '587'
$env:SMTP_USER = 'your-smtp-user@example.com'
$env:SMTP_PASS = 'your-smtp-password'
$env:MAIL_TO = 'reserve@ausnya.com'
```

4. Run the app:

```powershell
python app.py
```

This will start the server on port 5000. Update your front-end (contact form) to POST to `http://localhost:5000/send` (the repository changes already configure an AJAX POST to `/send`).

Security notes
- Do not commit real SMTP credentials. Use environment variables or a secret store.
- For production, run behind a proper WSGI server and use TLS/HTTPS.
