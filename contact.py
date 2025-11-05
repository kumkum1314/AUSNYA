#!/usr/bin/python
import os
import sys
from flask import Flask, request, jsonify
from flask_compress import Compress
from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage
from datetime import datetime
import traceback

# Load environment variables from .env file
load_dotenv()
app = Flask(__name__, static_url_path='', static_folder='.')
Compress(app)

# Configuration from environment
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASS = os.environ.get('SMTP_PASS')
MAIL_TO = os.environ.get('MAIL_TO', 'kukki1314@gmail.com')

# Upload handling
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)
ALLOWED_EXT = {'pdf'}
MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', str(10 * 1024 * 1024)))

def sanitize_filename(filename: str) -> str:
    # keep only safe characters
    name = os.path.basename(filename)
    name = name.replace(' ', '_')
    return ''.join(ch for ch in name if ch.isalnum() or ch in ('-', '_', '.', '@'))

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def send_email(subject: str, body: str, reply_to: str = None, attachment_bytes: bytes = None, attachment_filename: str = None):
    # If SMTP credentials are not provided, skip sending and let caller decide
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        raise RuntimeError('SMTP configuration is incomplete.')

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SMTP_USER
    msg['To'] = MAIL_TO
    if reply_to:
        msg['Reply-To'] = reply_to
    msg.set_content(body)

    # Attach file if provided
    if attachment_bytes and attachment_filename:
        msg.add_attachment(attachment_bytes, maintype='application', subtype='pdf', filename=attachment_filename)

    # Use TLS on SMTP
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.ehlo()
        if SMTP_PORT == 587:
            smtp.starttls()
            smtp.ehlo()
        smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(msg)


# Health check endpoint
@app.route('/')
def index():
    # Serve the site homepage at root
    return app.send_static_file('index.html')

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    # Basic caching for static assets
    path = request.path or ''
    if any(path.endswith(ext) for ext in ('.css', '.js', '.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.woff2', '.woff', '.ttf')):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response


@app.route('/send', methods=['POST', 'OPTIONS'])
def send():
    # Handle preflight
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200

    try:
        # Support both JSON and form/multipart
        if request.is_json:
            data = request.get_json() or {}
            name = (data.get('name') or '').strip()
            email = (data.get('email') or '').strip()
            phone = (data.get('phone') or '').strip()
            subject = (data.get('subject') or 'Website contact').strip()
            message = (data.get('message') or '').strip()
            file_storage = None
        else:
            # form or multipart
            name = (request.form.get('name') or '').strip()
            email = (request.form.get('email') or '').strip()
            phone = (request.form.get('phone') or '').strip()
            subject = (request.form.get('subject') or 'Website contact').strip()
            message = (request.form.get('message') or '').strip()
            # common file field names
            file_storage = None
            for fn in ('resume', 'file', 'upload', 'attachment'):
                if fn in request.files:
                    file_storage = request.files.get(fn)
                    break

        print('Received contact:', name, email)

        if not name or not email:
            return jsonify({'ok': False, 'error': 'name and email are required'}), 400

        attachment_bytes = None
        attachment_filename = None
        saved_file = None
        if file_storage and getattr(file_storage, 'filename', None):
            orig_name = file_storage.filename
            if not allowed_file(orig_name):
                return jsonify({'ok': False, 'error': 'Only PDF files are allowed'}), 400
            file_data = file_storage.read()
            if len(file_data) > MAX_FILE_SIZE:
                return jsonify({'ok': False, 'error': f'File too large (max {MAX_FILE_SIZE} bytes)'}), 400

            clean_name = sanitize_filename(orig_name)
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            saved_file = f"{timestamp}_{clean_name}"
            save_path = os.path.join(UPLOAD_DIR, saved_file)
            with open(save_path, 'wb') as fout:
                fout.write(file_data)
            print('Saved upload to', save_path)

            attachment_bytes = file_data
            attachment_filename = saved_file

        body = f"Name: {name}\nEmail: {email}\nPhone: {phone}\n\nMessage:\n{message}\n\nSaved file: {saved_file or 'None'}"

        # Try SMTP first; if unavailable, provide a mailto fallback that the frontend can open
        try:
            send_email(subject=subject, body=body, reply_to=email, attachment_bytes=attachment_bytes, attachment_filename=attachment_filename)
            return jsonify({'ok': True, 'saved_file': saved_file}), 200
        except Exception as e:
            print('SMTP not configured or failed, falling back to mailto:', str(e))
            # Build a safe mailto URL
            from urllib.parse import quote
            mailto_subject = quote(subject)
            mailto_body = quote(body)
            mailto_url = f"mailto:{MAIL_TO}?subject={mailto_subject}&body={mailto_body}"
            return jsonify({'ok': True, 'fallback': 'mailto', 'mailto_url': mailto_url, 'saved_file': saved_file}), 200

    except Exception as outer:
        tb = traceback.format_exc()
        print('Unhandled error in /send:', str(outer))
        print(tb)
        return jsonify({'ok': False, 'error': 'internal error'}), 500


if __name__ == '__main__':
    # Development server. For production use uWSGI/gunicorn behind a reverse proxy.
    app.run(host='0.0.0.0', port=5000, debug=True)
