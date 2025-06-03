import os
import sys
from flask import Flask, redirect, url_for, request
from flask_cors import CORS
from flask_session import Session

# Add the current directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv module not installed, but that's okay
    pass

# Create Flask app
app = Flask(__name__, 
           static_folder='Evaluation_System_APP/static',
           template_folder='Evaluation_System_APP/templates')
app.secret_key = os.getenv("SECRET_KEY", "scopebuilder_secret_key")

# Set session configuration to use filesystem storage
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(__file__), 'flask_session')
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to False for HTTP
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = int(os.getenv('SESSION_LIFETIME', '3600'))  # Session timeout in seconds (1 hour)

# Initialize Session
Session(app)

# Enable CORS for all routes
CORS(app, supports_credentials=True)

# Import blueprints
from Evaluation_System_APP.routes.auth import auth_bp
from Evaluation_System_APP.routes.project import project_bp
from Evaluation_System_APP.routes.pdf import pdf_bp
from Evaluation_System_APP.routes.admin import admin_bp
from Evaluation_System_APP.models.user import create_default_admin

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='')
app.register_blueprint(project_bp, url_prefix='')
app.register_blueprint(pdf_bp, url_prefix='')
app.register_blueprint(admin_bp, url_prefix='')

# Create default admin on startup
create_default_admin()

# Add a route for the root URL
@app.route('/')
def index():
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '9090'))  # Matches Docker exposed port
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    print(f"Starting Flask app on {host}:{port} with debug={debug}")
    app.run(host=host, port=port, debug=debug) 