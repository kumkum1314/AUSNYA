import sys
import os

# Add the directory containing your app.py to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import your Flask app
from app import app as application

# This is what Bluehost will use
application.secret_key = 'your-secret-key-here'