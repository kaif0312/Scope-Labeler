import os, time, json
from uuid import uuid4
from flask import (
    Flask, request, redirect, url_for,
    send_from_directory, render_template_string, jsonify,
    session, flash
)
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from ultralytics import YOLO
from pdf2image import convert_from_path
from datetime import datetime

from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "scopebuilder_secret_key")  # For session management

# -----------------------------
# Configuration
# -----------------------------
# Absolute path to uploads
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

THUMBNAILS_FOLDER = os.path.join(app.root_path, 'thumbnails')
os.makedirs(THUMBNAILS_FOLDER, exist_ok=True)

ANNOTATIONS_FOLDER = os.path.join(app.root_path, 'annotated_data')
os.makedirs(ANNOTATIONS_FOLDER, exist_ok=True)

PROJECTS_FOLDER = os.path.join(app.root_path, 'projects')
os.makedirs(PROJECTS_FOLDER, exist_ok=True)

USERS_FOLDER = os.path.join(app.root_path, 'users')
os.makedirs(USERS_FOLDER, exist_ok=True)

# Azure credentials (set these env-vars in your shell!)
AZURE_ENDPOINT = os.getenv("AZURE_VISION_ENDPOINT","https://scopebuilder.cognitiveservices.azure.com")
AZURE_KEY = os.getenv("AZURE_VISION_KEY","75gzAOgClEIGv8CxaYZcre8X04QxJZGE256MK4y7dMaL1sfLtnHdJQQJ99BEACYeBjFXJ3w3AAAFACOGeQxC")
cv_client = ComputerVisionClient(
    AZURE_ENDPOINT,
    CognitiveServicesCredentials(AZURE_KEY)
)

YOLO_WEIGHTS = os.getenv("YOLO_WEIGHTS", "/home/kaifu10/Desktop/wyreai intern/YOLO TRAINING/165images_trained/detect/train/weights/best.pt")
yolo = YOLO(YOLO_WEIGHTS)
PDF_DPI = 100  # Reduced from 150 to lower memory usage
METADATA_DPI = 72  # Lower DPI just for counting pages
THUMBNAIL_DPI = 72  # Low DPI for thumbnails

SCOPES = [
    "Acoustic Treatment",
    "Acoustical Ceilings",
    "Architectural Concrete",
    "Architectural Woodwork",
    "Art",
    "Casework",
    "Commercial Equipment",
    "Common Work Results for Equipment",
    "Common Work Results for Finishes",
    "Common Work Results for Furnishings",
    "Common Work Results for Openings",
    "Common Work Results for Special Construction",
    "Communications",
    "Composite Fabrications",
    "Concrete",
    "Concrete Cutting and Boring",
    "Conveying Equipment",
    "Dampproofing and Waterproofing",
    "Doors, Frames & Hardware",
    "Drywall",
    "Earthwork",
    "Educational and Scientific Equipment",
    "Electrical",
    "Electrical Power Generation",
    "Electronic Safety and Security",
    "Entertainment and Recreation Equipment",
    "Entrances",
    "Existing Conditions",
    "Exterior Specialties",
    "Facility Maintenance and Operation Equipment",
    "Finish Carpentry",
    "Fire Suppression",
    "Fire and Smoke Protection",
    "Fireplaces",
    "Flashing and Sheet Metal",
    "Flooring",
    "Foodservice Equipment",
    "Furnishings and Accessories",
    "Furniture",
    "General Requirements",
    "Glazing",
    "Gypcrete",
    "Healthcare Equipment",
    "Industry-Specific Manufacturing Equipment",
    "Information Specialties",
    "Integrated Automation",
    "Integrated Construction",
    "Interior Specialties",
    "Irrigation",
    "Joint Sealants",
    "Louvers and Vents",
    "Masonry",
    "Material Processing and Handling Equipment",
    "Mechanical",
    "Membrane Roofing",
    "Miscelleaneous Metals",
    "Multiple Seating",
    "Other Equipment",
    "Other Furnishings",
    "Other Specialties",
    "Painting and Coating",
    "Paving",
    "Planting",
    "Plumbing",
    "Pollution and Waste Control Equipment",
    "Precast Concrete",
    "Process Gas and Liquid Handling, Purification, and Storage Equipment",
    "Process Heating",
    "Process Interconnections",
    "Procurement & Contracting Requirements",
    "Residential Equipment",
    "Roof Windows and Skylights",
    "Roof and Wall Specialties and Accessories",
    "Roofing and Siding Panels",
    "Rough Carpentry",
    "Safety Specialties",
    "Site Improvements",
    "Special Facility Components",
    "Special Instrumentation",
    "Special Purpose Rooms",
    "Special Structures",
    "Specialty Doors and Frames",
    "Steep Slope Roofing",
    "Storage Specialties",
    "Structural Composites",
    "Structural Plastics",
    "Structural Steel",
    "Thermal Protection",
    "Tiling",
    "Transportation",
    "Utilities",
    "Vehicle and Pedestrian Equipment",
    "Visual Display Units",
    "Wall Finishes",
    "Water and Wastewater Equipment",
    "Waterway and Marine Construction",
    "Wetlands",
    "Window Treatments",
    "Windows"
]


# ————————————————
# User Management
# ————————————————
def get_users():
    """Load all users from the users folder"""
    users = {}
    users_file = os.path.join(USERS_FOLDER, 'users.json')
    if os.path.exists(users_file):
        with open(users_file) as f:
            users = json.load(f)
    return users

def save_users(users):
    """Save users to file"""
    with open(os.path.join(USERS_FOLDER, 'users.json'), 'w') as f:
        json.dump(users, f, indent=2)

def create_default_admin():
    """Create a default admin user if no users exist"""
    users = get_users()
    if not users:
        admin_id = str(uuid4())
        users[admin_id] = {
            'id': admin_id,
            'username': 'admin',
            'password': generate_password_hash('admin'),
            'role': 'admin',
            'created_date': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
        save_users(users)
        print("Created default admin user (username: admin, password: admin)")

# Create default admin on startup
create_default_admin()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        
        users = get_users()
        user = users.get(session['user_id'])
        
        if not user or user['role'] != 'admin':
            return 'Access denied: Admin privileges required', 403
            
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        users = get_users()
        user = None
        
        # Find user by username
        for user_id, user_data in users.items():
            if user_data['username'] == username:
                user = user_data
                break
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            error = 'Invalid username or password'
    
    return render_template_string("""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Login - Scope Builder</title>
        <style>
            body {
                font-family: system-ui, -apple-system, sans-serif;
                max-width: 400px;
                margin: 0 auto;
                padding: 40px 20px;
                background: #f5f5f5;
            }
            .login-form {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                text-align: center;
                margin-bottom: 30px;
                color: #2c3e50;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 8px;
                color: #2c3e50;
                font-weight: 500;
            }
            .form-group input {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 16px;
            }
            .btn {
                display: block;
                width: 100%;
                padding: 12px;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                font-weight: 500;
                cursor: pointer;
                text-align: center;
            }
            .btn:hover {
                background: #43a047;
            }
            .error {
                color: #f44336;
                margin-bottom: 20px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div class="login-form">
            <h1>Scope Builder Login</h1>
            
            {% if error %}
            <div class="error">{{ error }}</div>
            {% endif %}
            
            <form method="post">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <button type="submit" class="btn">Login</button>
            </form>
        </div>
    </body>
    </html>
    """, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/user_management')
@admin_required
def user_management():
    users = get_users()
    return render_template_string("""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>User Management - Scope Builder</title>
        <style>
            body {
                font-family: system-ui, -apple-system, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .header {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 30px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .header-left {
                flex: 1;
            }
            .header h1 {
                margin: 0;
                color: #2c3e50;
            }
            .users-list {
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .user-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px;
                border-bottom: 1px solid #eee;
            }
            .user-item:last-child {
                border-bottom: none;
            }
            .user-info {
                flex: 1;
            }
            .user-name {
                font-weight: 500;
                color: #2c3e50;
            }
            .user-role {
                font-size: 0.9em;
                color: #666;
                margin-top: 4px;
            }
            .user-date {
                font-size: 0.9em;
                color: #666;
            }
            .btn {
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-weight: 500;
                transition: background-color 0.2s;
                text-decoration: none;
                text-align: center;
                margin-left: 8px;
            }
            .btn-primary {
                background: #4CAF50;
                color: white;
            }
            .btn-primary:hover {
                background: #43a047;
            }
            .btn-danger {
                background: #f44336;
                color: white;
            }
            .btn-danger:hover {
                background: #d32f2f;
            }
            .create-form {
                margin-bottom: 20px;
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .form-row {
                display: flex;
                gap: 15px;
                margin-bottom: 15px;
            }
            .form-group {
                flex: 1;
            }
            .form-group label {
                display: block;
                margin-bottom: 8px;
                color: #2c3e50;
                font-weight: 500;
            }
            .form-group input, .form-group select {
                width: 100%;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            .nav-link {
                color: #4CAF50;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 5px;
                margin-bottom: 20px;
            }
            .nav-link:hover {
                text-decoration: underline;
            }
            .modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                justify-content: center;
                align-items: center;
                z-index: 1000;
            }
            .modal-content {
                background: white;
                padding: 20px;
                border-radius: 8px;
                width: 400px;
                text-align: center;
            }
            .modal-actions {
                display: flex;
                justify-content: center;
                gap: 10px;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-left">
                <a href="{{ url_for('index') }}" class="nav-link">← Back to Projects</a>
                <h1>User Management</h1>
            </div>
            <div>
                <a href="{{ url_for('logout') }}" class="btn btn-secondary">Logout</a>
            </div>
        </div>

        <div class="create-form">
            <h2>Create New User</h2>
            <form action="{{ url_for('create_user') }}" method="post">
                <div class="form-row">
                    <div class="form-group">
                        <label for="username">Username</label>
                        <input type="text" id="username" name="username" required>
                    </div>
                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" required>
                    </div>
                    <div class="form-group">
                        <label for="role">Role</label>
                        <select id="role" name="role" required>
                            <option value="worker">Worker</option>
                            <option value="admin">Admin</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn btn-primary">Create User</button>
            </form>
        </div>

        <div class="users-list">
            <h2>Users</h2>
            {% for user_id, user in users.items() %}
            <div class="user-item">
                <div class="user-info">
                    <div class="user-name">{{ user.username }}</div>
                    <div class="user-role">Role: {{ user.role|capitalize }}</div>
                    <div class="user-date">Created: {{ user.created_date }}</div>
                </div>
                <div>
                    <button class="btn btn-danger" 
                            onclick="confirmDelete('{{ user.id }}', '{{ user.username }}')">
                        Delete
                    </button>
                </div>
            </div>
            {% endfor %}
        </div>
        
        <!-- Delete Confirmation Modal -->
        <div id="deleteModal" class="modal">
            <div class="modal-content">
                <h3>Confirm Delete</h3>
                <p id="deleteMessage">Are you sure you want to delete this user?</p>
                <div class="modal-actions">
                    <form id="deleteForm" method="post">
                        <button type="submit" class="btn btn-danger">Delete</button>
                    </form>
                    <button class="btn btn-secondary" onclick="hideDeleteModal()">Cancel</button>
                </div>
            </div>
        </div>

        <script>
            function confirmDelete(userId, username) {
                document.getElementById('deleteMessage').textContent = 
                    `Are you sure you want to delete user "${username}"?`;
                document.getElementById('deleteForm').action = 
                    "{{ url_for('delete_user') }}?user_id=" + userId;
                document.getElementById('deleteModal').style.display = 'flex';
            }
            
            function hideDeleteModal() {
                document.getElementById('deleteModal').style.display = 'none';
            }
            
            // Close modal when clicking outside
            window.onclick = function(event) {
                if (event.target == document.getElementById('deleteModal')) {
                    hideDeleteModal();
                }
            }
        </script>
    </body>
    </html>
    """, users=users)

@app.route('/create_user', methods=['POST'])
@admin_required
def create_user():
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')
    
    if not username or not password or not role:
        return 'All fields are required', 400
    
    if role not in ['admin', 'worker']:
        return 'Invalid role', 400
    
    users = get_users()
    
    # Check if username already exists
    for user in users.values():
        if user['username'] == username:
            return 'Username already exists', 400
    
    # Create new user
    user_id = str(uuid4())
    users[user_id] = {
        'id': user_id,
        'username': username,
        'password': generate_password_hash(password),
        'role': role,
        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M')
    }
    
    save_users(users)
    return redirect(url_for('user_management'))

@app.route('/delete_user', methods=['POST'])
@admin_required
def delete_user():
    user_id = request.args.get('user_id')
    if not user_id:
        return 'User ID is required', 400
    
    # Get users
    users = get_users()
    
    # Check if user exists
    if user_id not in users:
        return 'User not found', 404
    
    # Check if trying to delete self
    if user_id == session['user_id']:
        return 'Cannot delete your own account', 400
    
    # Delete user
    del users[user_id]
    save_users(users)
    
    return redirect(url_for('user_management'))

# ————————————————
# Project Management
# ————————————————
def get_projects():
    """Load all projects from the projects folder"""
    projects = []
    if os.path.exists(os.path.join(PROJECTS_FOLDER, 'projects.json')):
        with open(os.path.join(PROJECTS_FOLDER, 'projects.json')) as f:
            projects = json.load(f)
    return projects

def save_projects(projects):
    """Save projects list to file"""
    with open(os.path.join(PROJECTS_FOLDER, 'projects.json'), 'w') as f:
        json.dump(projects, f)

@app.route('/')
@login_required
def index():
    projects = get_projects()
    return render_template_string("""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Scope Builder Projects</title>
        <style>
            body {
                font-family: system-ui, -apple-system, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .header {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 30px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .header-left {
                flex: 1;
            }
            .header h1 {
                margin: 0;
                color: #2c3e50;
            }
            .user-info {
                text-align: right;
                margin-bottom: 10px;
            }
            .projects-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }
            .project-card {
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                transition: all 0.3s ease;
            }
            .project-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            .project-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 15px;
            }
            .project-title {
                font-size: 1.2em;
                font-weight: 600;
                color: #2c3e50;
                margin: 0;
            }
            .project-date {
                color: #666;
                font-size: 0.9em;
            }
            .project-stats {
                background: #f8f9fa;
                padding: 10px;
                border-radius: 6px;
                margin: 10px 0;
            }
            .project-actions {
                display: flex;
                gap: 10px;
                margin-top: 15px;
            }
            .btn {
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-weight: 500;
                transition: background-color 0.2s;
                text-decoration: none;
                text-align: center;
            }
            .btn-primary {
                background: #4CAF50;
                color: white;
            }
            .btn-primary:hover {
                background: #43a047;
            }
            .btn-secondary {
                background: #e9ecef;
                color: #2c3e50;
            }
            .btn-secondary:hover {
                background: #dee2e6;
            }
            .create-project {
                margin-bottom: 30px;
            }
            .modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                justify-content: center;
                align-items: center;
            }
            .modal-content {
                background: white;
                padding: 30px;
                border-radius: 10px;
                width: 90%;
                max-width: 500px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 8px;
                color: #2c3e50;
                font-weight: 500;
            }
            .form-group input {
                width: 100%;
                padding: 8px;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-size: 1em;
            }
            .empty-state {
                text-align: center;
                padding: 40px;
                background: white;
                border-radius: 10px;
                color: #666;
            }
            .nav-links { 
                margin-bottom: 20px; 
                display: flex;
                gap: 20px;
            }
            .nav-links a { 
                color: #4CAF50;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                padding: 5px 10px;
                border-radius: 4px;
                background-color: #f0f8f0;
                transition: background-color 0.2s;
            }
            .nav-links a:hover {
                background-color: #e0f0e0;
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-left">
                <h1>Scope Builder Projects</h1>
            </div>
            <div>
                <div class="user-info">
                    Logged in as: <strong>{{ session.username }}</strong> ({{ session.role }})
                </div>
                <div class="nav-links">
                    {% if session.role == 'admin' %}
                    <a href="{{ url_for('admin_dashboard') }}">Admin Dashboard</a>
                    <a href="{{ url_for('user_management') }}">User Management</a>
                    {% endif %}
                    <a href="{{ url_for('logout') }}">Logout</a>
                </div>
            </div>
        </div>
        
        <button class="btn btn-primary" onclick="showCreateProjectModal()">+ Create New Project</button>

        {% if projects %}
        <div class="projects-grid">
            {% for project in projects %}
            <div class="project-card">
                <div class="project-header">
                    <h2 class="project-title">{{ project.name }}</h2>
                    <span class="project-date">{{ project.created_date }}</span>
                </div>
                <div class="project-stats">
                    <div>PDFs: {{ project.pdfs|length }}</div>
                    {% if project.pdfs %}
                    <div>Latest: {{ project.pdfs[-1].filename }}</div>
                    {% endif %}
                </div>
                <div class="project-actions">
                    <a href="{{ url_for('view_project', project_id=project.id) }}" 
                       class="btn btn-primary">View Project</a>
                </div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="empty-state">
            <h2>No projects yet</h2>
            <p>Create your first project to get started!</p>
        </div>
        {% endif %}

        <!-- Create Project Modal -->
        <div id="createProjectModal" class="modal">
            <div class="modal-content">
                <h2>Create New Project</h2>
                <form action="{{ url_for('create_project') }}" method="post">
                    <div class="form-group">
                        <label for="projectName">Project Name</label>
                        <input type="text" id="projectName" name="name" required
                               placeholder="Enter project name">
                    </div>
                    <div class="form-group">
                        <label for="projectDescription">Description (optional)</label>
                        <input type="text" id="projectDescription" name="description"
                               placeholder="Enter project description">
                    </div>
                    <div class="project-actions">
                        <button type="submit" class="btn btn-primary">Create Project</button>
                        <button type="button" class="btn btn-secondary" 
                                onclick="hideCreateProjectModal()">Cancel</button>
                    </div>
                </form>
            </div>
        </div>

        <script>
            function showCreateProjectModal() {
                document.getElementById('createProjectModal').style.display = 'flex';
            }
            
            function hideCreateProjectModal() {
                document.getElementById('createProjectModal').style.display = 'none';
            }

            // Close modal when clicking outside
            window.onclick = function(event) {
                if (event.target == document.getElementById('createProjectModal')) {
                    hideCreateProjectModal();
                }
            }
        </script>
    </body>
    </html>
    """, projects=projects, session=session)

@app.route('/create_project', methods=['POST'])
def create_project():
    name = request.form.get('name')
    description = request.form.get('description', '')
    
    if not name:
        return 'Project name is required', 400
    
    projects = get_projects()
    new_project = {
        'id': str(uuid4()),
        'name': name,
        'description': description,
        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'pdfs': []
    }
    projects.append(new_project)
    save_projects(projects)
    
    return redirect(url_for('view_project', project_id=new_project['id']))

@app.route('/project/<project_id>')
def view_project(project_id):
    projects = get_projects()
    project = next((p for p in projects if p['id'] == project_id), None)
    if not project:
        return 'Project not found', 404

    return render_template_string("""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{{ project.name }} - Scope Builder</title>
        <style>
            body {
                font-family: system-ui, -apple-system, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .header {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 30px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .header-left {
                flex: 1;
            }
            .header h1 {
                margin: 0;
                color: #2c3e50;
            }
            .header p {
                margin: 5px 0 0;
                color: #666;
            }
            .pdfs-list {
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .pdf-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px;
                border-bottom: 1px solid #eee;
            }
            .pdf-item:last-child {
                border-bottom: none;
            }
            .pdf-info {
                flex: 1;
            }
            .pdf-name {
                font-weight: 500;
                color: #2c3e50;
            }
            .pdf-date {
                font-size: 0.9em;
                color: #666;
            }
            .btn {
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-weight: 500;
                transition: background-color 0.2s;
                text-decoration: none;
                text-align: center;
                margin-left: 8px;
            }
            .btn-primary {
                background: #4CAF50;
                color: white;
            }
            .btn-primary:hover {
                background: #43a047;
            }
            .btn-secondary {
                background: #e9ecef;
                color: #2c3e50;
            }
            .btn-secondary:hover {
                background: #dee2e6;
            }
            .btn-danger {
                background: #f44336;
                color: white;
            }
            .btn-danger:hover {
                background: #d32f2f;
            }
            .btn-info {
                background: #2196F3;
                color: white;
            }
            .btn-info:hover {
                background: #1976D2;
            }
            .pdf-actions {
                display: flex;
                align-items: center;
            }
            .upload-form {
                margin-bottom: 20px;
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .empty-state {
                text-align: center;
                padding: 40px;
                color: #666;
            }
            .nav-link {
                color: #4CAF50;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 5px;
            }
            .nav-link:hover {
                text-decoration: underline;
            }
            .modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                justify-content: center;
                align-items: center;
                z-index: 1000;
            }
            .modal-content {
                background: white;
                padding: 20px;
                border-radius: 8px;
                width: 400px;
                text-align: center;
            }
            .modal-actions {
                display: flex;
                justify-content: center;
                gap: 10px;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-left">
                <a href="{{ url_for('index') }}" class="nav-link">← Back to Projects</a>
                <h1>{{ project.name }}</h1>
                {% if project.description %}
                <p>{{ project.description }}</p>
                {% endif %}
            </div>
        </div>

        <div class="upload-form">
            <h2>Upload New PDF</h2>
            <form action="{{ url_for('upload_pdf', project_id=project.id) }}" 
                  method="post" enctype="multipart/form-data">
                <input type="file" name="file" accept="application/pdf" required>
                <button type="submit" class="btn btn-primary">Upload PDF</button>
            </form>
        </div>

        <div class="pdfs-list">
            <h2>Project PDFs</h2>
            {% if project.pdfs %}
                {% for pdf in project.pdfs %}
                <div class="pdf-item">
                    <div class="pdf-info">
                        <div class="pdf-name">{{ pdf.filename }}</div>
                        <div class="pdf-date">Uploaded: {{ pdf.upload_date }}</div>
                    </div>
                    <div class="pdf-actions">
                        <a href="{{ url_for('select_sheet', upload_id=pdf.upload_id) }}" 
                           class="btn btn-primary">Process PDF</a>
                        {% if session.role == 'admin' %}
                        <a href="{{ url_for('download_annotations', upload_id=pdf.upload_id) }}" 
                           class="btn btn-info">Download Annotations</a>
                        <button class="btn btn-danger" 
                                onclick="confirmDelete('{{ pdf.upload_id }}', '{{ pdf.filename }}')">
                            Delete
                        </button>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="empty-state">
                    <p>No PDFs uploaded yet. Upload your first PDF to get started!</p>
                </div>
            {% endif %}
        </div>
        
        <!-- Delete Confirmation Modal -->
        <div id="deleteModal" class="modal">
            <div class="modal-content">
                <h3>Confirm Delete</h3>
                <p id="deleteMessage">Are you sure you want to delete this PDF?</p>
                <div class="modal-actions">
                    <form id="deleteForm" method="post">
                        <button type="submit" class="btn btn-danger">Delete</button>
                    </form>
                    <button class="btn btn-secondary" onclick="hideDeleteModal()">Cancel</button>
                </div>
            </div>
        </div>

        <script>
            function confirmDelete(uploadId, filename) {
                document.getElementById('deleteMessage').textContent = 
                    `Are you sure you want to delete "${filename}"?`;
                document.getElementById('deleteForm').action = 
                    "{{ url_for('delete_pdf', project_id=project.id) }}?upload_id=" + uploadId;
                document.getElementById('deleteModal').style.display = 'flex';
            }
            
            function hideDeleteModal() {
                document.getElementById('deleteModal').style.display = 'none';
            }
            
            // Close modal when clicking outside
            window.onclick = function(event) {
                if (event.target == document.getElementById('deleteModal')) {
                    hideDeleteModal();
                }
            }
        </script>
    </body>
    </html>
    """, project=project)

@app.route('/project/<project_id>/delete_pdf', methods=['POST'])
@admin_required
def delete_pdf(project_id):
    upload_id = request.args.get('upload_id')
    if not upload_id:
        return 'Upload ID is required', 400
    
    # Get project
    projects = get_projects()
    project = next((p for p in projects if p['id'] == project_id), None)
    if not project:
        return 'Project not found', 404
    
    # Find the PDF in the project
    pdf_to_delete = next((pdf for pdf in project['pdfs'] if pdf['upload_id'] == upload_id), None)
    if not pdf_to_delete:
        return 'PDF not found in project', 404
    
    # Remove the PDF from the project
    project['pdfs'] = [pdf for pdf in project['pdfs'] if pdf['upload_id'] != upload_id]
    save_projects(projects)
    
    # Delete the PDF file
    pdf_path = os.path.join(UPLOAD_FOLDER, f"{upload_id}.pdf")
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    
    # Delete metadata file
    meta_path = os.path.join(UPLOAD_FOLDER, f"{upload_id}_metadata.json")
    if os.path.exists(meta_path):
        os.remove(meta_path)
    
    # Delete thumbnail directory
    thumbs_dir = os.path.join(THUMBNAILS_FOLDER, upload_id)
    if os.path.exists(thumbs_dir):
        for file in os.listdir(thumbs_dir):
            os.remove(os.path.join(thumbs_dir, file))
        os.rmdir(thumbs_dir)
    
    # Delete all crop directories and files
    for page_num in range(1, 1000):  # Use a reasonable upper limit
        crops_dir = os.path.join(UPLOAD_FOLDER, f"{upload_id}_page{page_num}_crops")
        if os.path.exists(crops_dir):
            for file in os.listdir(crops_dir):
                os.remove(os.path.join(crops_dir, file))
            os.rmdir(crops_dir)
        else:
            break  # No more pages
    
    # Delete annotation files
    for file in os.listdir(ANNOTATIONS_FOLDER):
        if file.startswith(f"{upload_id}_"):
            os.remove(os.path.join(ANNOTATIONS_FOLDER, file))
    
    return redirect(url_for('view_project', project_id=project_id))

@app.route('/project/<project_id>/upload', methods=['POST'])
def upload_pdf(project_id):
    projects = get_projects()
    project = next((p for p in projects if p['id'] == project_id), None)
    if not project:
        return 'Project not found', 404

    file = request.files.get('file')
    if not file or not file.filename.lower().endswith('.pdf'):
        return 'Please upload a PDF', 400

    try:
        upload_id = uuid4().hex
        pdf_path = os.path.join(UPLOAD_FOLDER, f"{upload_id}.pdf")
        file.save(pdf_path)

        # Create thumbnails directory
        thumbs_dir = os.path.join(THUMBNAILS_FOLDER, upload_id)
        os.makedirs(thumbs_dir, exist_ok=True)
        
        # Get total pages and generate thumbnails
        try:
            # Use a lower DPI for thumbnails
            pages = convert_from_path(pdf_path, dpi=THUMBNAIL_DPI)
            total_pages = len(pages)
            
            # Generate thumbnails
            page_thumbs = []
            for i, page in enumerate(pages):
                thumb_path = os.path.join(thumbs_dir, f"page_{i+1}.png")
                page.save(thumb_path, "PNG")
                page_thumbs.append(f"page_{i+1}.png")
            
            # Free memory
            pages = None
        except Exception as e:
            print(f"Error converting PDF: {e}")
            return f"Error processing PDF: {str(e)}", 500

        # Save metadata
        meta = {
            'upload_id': upload_id,
            'filename': file.filename,
            'total_pages': total_pages,
            'processed_pages': [],
            'thumbnails': page_thumbs
        }
        
        # Create metadata file
        meta_path = os.path.join(UPLOAD_FOLDER, f"{upload_id}_metadata.json")
        with open(meta_path, 'w') as f:
            json.dump(meta, f, indent=2)

        # Update project information
        project['pdfs'].append({
            'upload_id': upload_id,
            'filename': file.filename,
            'upload_date': datetime.now().strftime('%Y-%m-%d %H:%M')
        })
        save_projects(projects)

        return redirect(url_for('select_sheet', upload_id=upload_id))
    
    except Exception as e:
        print(f"Unexpected error during PDF upload: {e}")
        return f"Error uploading PDF: {str(e)}", 500

@app.route('/select_sheet/<upload_id>')
def select_sheet(upload_id):
    # Load metadata
    meta_path = os.path.join(UPLOAD_FOLDER, f"{upload_id}_metadata.json")
    if not os.path.exists(meta_path):
        print(f"Metadata file not found at: {meta_path}")  # Debug print
        return 'Invalid upload ID', 404
    
    with open(meta_path) as f:
        meta = json.load(f)

    # Calculate completion percentage for each page
    page_progress = {}
    for page_num in range(1, meta['total_pages'] + 1):
        crops_dir = os.path.join(UPLOAD_FOLDER, f"{upload_id}_page{page_num}_crops")
        crops_meta_path = os.path.join(crops_dir, 'crops.json')
        
        # Check if page needs processing
        needs_processing = not os.path.exists(crops_meta_path)
        
        if os.path.exists(crops_meta_path):
            with open(crops_meta_path) as f:
                crops_meta = json.load(f)
                total = len(crops_meta['crops'])
                completed = len(crops_meta.get('completed_crops', []))
                page_progress[page_num] = {
                    'percent': int((completed / total) * 100) if total > 0 else 0,
                    'completed': completed,
                    'total': total,
                    'needs_processing': False
                }
        else:
            page_progress[page_num] = {
                'percent': 0, 
                'completed': 0, 
                'total': 0,
                'needs_processing': True
            }

    return render_template_string("""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Select Sheet to Process - {{ meta.filename }}</title>
        <style>
            body { font-family: sans-serif; padding: 20px; }
            .sheets-container {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 20px;
                padding: 20px 0;
            }
            .sheet-card {
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 10px;
                cursor: pointer;
                transition: all 0.3s;
                position: relative;
            }
            .sheet-card:hover {
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            .sheet-card.processed {
                border-color: #4CAF50;
            }
            .sheet-card img {
                width: 100%;
                height: 200px;
                object-fit: contain;
                margin-bottom: 10px;
            }
            .sheet-info {
                text-align: center;
            }
            .progress-bar {
                width: 100%;
                height: 5px;
                background-color: #f0f0f0;
                border-radius: 3px;
                margin: 5px 0;
                overflow: hidden;
            }
            .progress-fill {
                height: 100%;
                background-color: #4CAF50;
                transition: width 0.3s ease;
            }
            h1 { margin-bottom: 20px; }
            .progress { color: #666; margin-bottom: 20px; }
            .nav-link {
                color: #4CAF50;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 5px;
                margin-bottom: 20px;
            }
            .nav-link:hover {
                text-decoration: underline;
            }
            .process-btn {
                display: inline-block;
                padding: 8px 16px;
                background: #4CAF50;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                margin-top: 10px;
            }
            .process-btn:hover {
                background: #43a047;
            }
            .process-btn.processing {
                background: #FFA726;
            }
            .status-badge {
                position: absolute;
                top: 10px;
                right: 10px;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                color: white;
            }
            .status-badge.needs-processing {
                background: #FFA726;
            }
            .status-badge.processed {
                background: #4CAF50;
            }
        </style>
    </head>
    <body>
        <a href="{{ url_for('index') }}" class="nav-link">← Back to Projects</a>
        <h1>{{ meta.filename }} - Select Sheet to Process</h1>
        <div class="sheets-container">
            {% for i in range(meta.total_pages) %}
            {% set progress = page_progress[i+1] %}
            <div class="sheet-card {% if progress.percent == 100 %}processed{% endif %}">
                <img src="{{ url_for('thumbnails', filename=meta.upload_id + '/' + meta.thumbnails[i]) }}" 
                     alt="Sheet {{ i+1 }}">
                <div class="sheet-info">
                    <strong>Sheet {{ i+1 }}</strong>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {{ progress.percent }}%"></div>
                    </div>
                    <div>{{ progress.completed }}/{{ progress.total }} figures</div>
                    <div>{{ progress.percent }}% complete</div>
                    {% if progress.needs_processing %}
                        <div class="status-badge needs-processing">Needs Processing</div>
                        <a href="{{ url_for('process_sheet', upload_id=meta.upload_id, page_num=i+1) }}" 
                           class="process-btn">Process Sheet</a>
                    {% else %}
                        <div class="status-badge processed">Completed</div>
                        <a href="{{ url_for('sheet_progress', upload_id=meta.upload_id, page_num=i+1) }}" 
                           class="process-btn">View Progress</a>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """, meta=meta, page_progress=page_progress)

@app.route('/process_sheet/<upload_id>/<int:page_num>')
def process_sheet(upload_id, page_num):
    # Load metadata
    meta_path = os.path.join(UPLOAD_FOLDER, f"{upload_id}_metadata.json")
    if not os.path.exists(meta_path):
        print(f"Metadata file not found at: {meta_path}")  # Debug print
        return 'Invalid upload ID', 404
    
    with open(meta_path) as f:
        meta = json.load(f)
    
    if page_num < 1 or page_num > meta['total_pages']:
        return 'Invalid page number', 404

    try:
        # Convert specific page to image
        pdf_path = os.path.join(UPLOAD_FOLDER, f"{upload_id}.pdf")
        pil_img = convert_from_path(
            pdf_path, dpi=PDF_DPI,
            first_page=page_num, last_page=page_num,
            fmt='PNG', thread_count=1
        )[0]

        # Create crops directory for this page
        crops_dir = os.path.join(UPLOAD_FOLDER, f"{upload_id}_page{page_num}_crops")
        os.makedirs(crops_dir, exist_ok=True)

        # Run YOLO detection and save detection coordinates
        dets = yolo(pil_img)[0]
        crop_list = []
        yolo_boxes = []  # Store YOLO detection coordinates
        
        for i, box in enumerate(dets.boxes.xyxy.cpu().numpy().astype(int)):
            x1,y1,x2,y2 = box.tolist()
            crop = pil_img.crop((x1,y1,x2,y2))
            fn = f"crop_{i}.png"
            crop.save(os.path.join(crops_dir, fn))
            crop_list.append(fn)
            yolo_boxes.append({
                'crop_id': i,
                'x1': int(x1),
                'y1': int(y1),
                'x2': int(x2),
                'y2': int(y2)
            })

        # Save crops metadata with completion tracking and YOLO boxes
        crops_meta = {
            'upload_id': upload_id,
            'page_num': page_num,
            'crops': crop_list,
            'completed_crops': [],  # Track which crops are completed
            'yolo_boxes': yolo_boxes,  # Save YOLO detection coordinates
            'total_figures': len(crop_list)  # Add total figures count
        }
        
        # Save the metadata
        meta_file = os.path.join(crops_dir, 'crops.json')
        with open(meta_file, 'w') as f:
            json.dump(crops_meta, f, indent=2)

        # Free memory
        pil_img = None
        dets = None
        
        return redirect(url_for('sheet_progress', upload_id=upload_id, page_num=page_num))
        
    except Exception as e:
        print(f"Error processing sheet {page_num}: {e}")
        return f"Error processing sheet: {str(e)}", 500

@app.route('/sheet_progress/<upload_id>/<int:page_num>')
def sheet_progress(upload_id, page_num):
    # Load metadata
    crops_dir = os.path.join(UPLOAD_FOLDER, f"{upload_id}_page{page_num}_crops")
    meta_path = os.path.join(crops_dir, 'crops.json')
    
    # If the sheet hasn't been processed yet, process it first
    if not os.path.exists(meta_path):
        return redirect(url_for('process_sheet', upload_id=upload_id, page_num=page_num))
        
    with open(meta_path) as f:
        meta = json.load(f)
    
    # Ensure all required keys exist
    if not all(key in meta for key in ['crops', 'completed_crops', 'total_figures']):
        # If metadata is incomplete, reprocess the sheet
        return redirect(url_for('process_sheet', upload_id=upload_id, page_num=page_num))
    
    # Calculate completion percentage
    total_figures = meta['total_figures']
    completed_figures = len(meta.get('completed_crops', []))
    completion_percent = int((completed_figures / total_figures) * 100) if total_figures > 0 else 0

    return render_template_string("""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Sheet {{page_num}} Progress</title>
        <style>
            body { font-family: sans-serif; padding: 20px; max-width: 800px; margin: 0 auto; }
            .progress-bar {
                width: 100%;
                height: 20px;
                background-color: #f0f0f0;
                border-radius: 10px;
                margin: 20px 0;
                overflow: hidden;
            }
            .progress-fill {
                height: 100%;
                background-color: #4CAF50;
                width: {{ completion_percent }}%;
                transition: width 0.3s ease;
            }
            .figures-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }
            .figure-card {
                border: 1px solid #ccc;
                padding: 10px;
                border-radius: 5px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s;
            }
            .figure-card:hover {
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .figure-card.completed {
                background-color: #e8f5e9;
                border-color: #4CAF50;
            }
            .figure-card.incomplete {
                background-color: #fff;
            }
            .nav-links { margin-bottom: 20px; }
            .nav-links a { margin-right: 15px; }
            .status-text { color: #666; }
            .quick-nav {
                margin: 20px 0;
                padding: 15px;
                background: #f8f8f8;
                border-radius: 5px;
            }
        </style>
    </head>
    <body>
        <div class="nav-links">
            <a href="{{ url_for('select_sheet', upload_id=upload_id) }}">← Back to Sheet Selection</a>
            <a href="{{ url_for('sheet_progress', upload_id=upload_id, page_num=page_num) }}">← Back to Sheet Figures</a>
        </div>
        
        <h1>Sheet {{page_num}} Progress</h1>
        
        <div class="progress-bar">
            <div class="progress-fill"></div>
        </div>
        <div class="status-text">
            Completed {{ completed_figures }} of {{ total_figures }} figures ({{ completion_percent }}%)
        </div>

        {% if incomplete_figures %}
        <div class="quick-nav">
            <h3>Quick Navigation</h3>
            <p>Incomplete figures: 
            {% for idx in incomplete_figures %}
                <a href="{{ url_for('annotate_crop', upload_id=upload_id, page_num=page_num, crop_idx=idx) }}">
                    Figure {{idx + 1}}
                </a>{% if not loop.last %}, {% endif %}
            {% endfor %}
            </p>
        </div>
        {% endif %}

        <div class="figures-grid">
            {% for idx in range(total_figures) %}
            <div class="figure-card {{ 'completed' if idx in completed_crops else 'incomplete' }}"
                 onclick="window.location.href='{{ url_for('annotate_crop', upload_id=upload_id, page_num=page_num, crop_idx=idx) }}'">
                <strong>Figure {{ idx + 1 }}</strong><br>
                {% if idx in completed_crops %}
                    <span style="color: #4CAF50">✓ Complete</span>
                {% else %}
                    <span>Incomplete</span>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """, 
    upload_id=upload_id,
    page_num=page_num,
    total_figures=total_figures,
    completed_figures=completed_figures,
    completion_percent=completion_percent,
    completed_crops=meta.get('completed_crops', []),
    incomplete_figures=[i for i in range(total_figures) if i not in meta.get('completed_crops', [])]
    )

@app.route('/thumbnails/<path:filename>')
def thumbnails(filename):
    return send_from_directory(THUMBNAILS_FOLDER, filename)

# ————————————————
# 2) Serve uploaded files
# ————————————————
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ————————————————
# 3) Annotate page (runs OCR + UI)
# ————————————————
@app.route('/annotate_crop/<upload_id>/<int:page_num>/<int:crop_idx>')
def annotate_crop(upload_id, page_num, crop_idx):
    # Locate crops folder & metadata
    crops_dir = os.path.join(UPLOAD_FOLDER, f"{upload_id}_page{page_num}_crops")
    meta_path = os.path.join(crops_dir, 'crops.json')
    if not os.path.isfile(meta_path):
        return redirect(url_for('process_sheet', upload_id=upload_id, page_num=page_num))

    # Load crop filenames and previous annotations
    with open(meta_path) as f:
        meta = json.load(f)
    crop_list = meta['crops']
    yolo_boxes = meta['yolo_boxes']  # Get YOLO detection coordinates
    current_box = next(box for box in yolo_boxes if box['crop_id'] == crop_idx)
    
    total = len(crop_list)
    if crop_idx >= total:
        return redirect(url_for('select_sheet', upload_id=upload_id))

    # Pick this crop
    img_fn = crop_list[crop_idx]
    image_url = url_for('uploaded_file', filename=f"{upload_id}_page{page_num}_crops/{img_fn}")

    # Load previous annotations if they exist
    annotation_file = os.path.join(ANNOTATIONS_FOLDER, f"{upload_id}_page{page_num}_crop{crop_idx}.json")
    previous_regions = []
    if os.path.exists(annotation_file):
        with open(annotation_file) as f:
            previous_data = json.load(f)
            previous_regions = previous_data.get('regions', [])

    # Find all existing tags for this upload_id to enable auto-tagging
    existing_tags = {}
    try:
        # Search for all annotation files for this upload
        for file in os.listdir(ANNOTATIONS_FOLDER):
            if file.startswith(f"{upload_id}_") and file.endswith(".json"):
                with open(os.path.join(ANNOTATIONS_FOLDER, file)) as f:
                    file_data = json.load(f)
                    if 'regions' in file_data:
                        for region in file_data['regions']:
                            if region.get('tag') and region.get('text'):
                                # Store the tag and bid item for each unique text
                                text = region['text'].strip().lower()
                                if text and len(text) > 2:  # Ignore very short text
                                    existing_tags[text] = {
                                        'tag': region['tag'],
                                        'bidItem': region['bidItem'],
                                        'reason': region.get('reason', '')
                                    }
    except Exception as e:
        print(f"Error loading existing tags: {e}")

    # Run OCR if no previous annotations
    boxes = []
    if not previous_regions:
        with open(os.path.join(crops_dir, img_fn), 'rb') as f:
            resp = cv_client.read_in_stream(f, raw=True)
        op_id = resp.headers['Operation-Location'].split('/')[-1]
        while True:
            result = cv_client.get_read_result(op_id)
            if result.status not in ('notStarted', 'running'):
                break
            time.sleep(1)

        if result.status == OperationStatusCodes.succeeded:
            idx = 0
            for page in result.analyze_result.read_results:
                for line in page.lines:
                    bb = line.bounding_box
                    # Keep coordinates relative to the crop for display
                    pts = list(zip(bb[0::2], bb[1::2]))
                    
                    # Convert quad points to sheet coordinates
                    sheet_coords = []
                    for idx_pt in range(0, len(bb), 2):
                        x = bb[idx_pt] + current_box['x1']  # Add crop's x offset
                        y = bb[idx_pt+1] + current_box['y1']  # Add crop's y offset
                        sheet_coords.extend([x, y])
                    
                    text = line.text
                    
                    # Check if this text has been tagged before
                    auto_tag = None
                    auto_bid_item = None
                    auto_reason = None
                    text_lower = text.strip().lower()
                    if text_lower in existing_tags:
                        auto_tag = existing_tags[text_lower]['tag']
                        auto_bid_item = existing_tags[text_lower]['bidItem']
                        auto_reason = existing_tags[text_lower].get('reason', '')
                    
                    boxes.append({
                        'id': idx,
                        'pts': pts,  # Crop-relative coordinates for display
                        'sheet_pts': list(zip(sheet_coords[0::2], sheet_coords[1::2])),  # Sheet-relative coordinates for storage
                        'tag': auto_tag,  # Auto-tag if text matches
                        'bidItem': auto_bid_item,  # Auto-set bid item
                        'reason': auto_reason,  # Auto-set reason
                        'crop_box': current_box,
                        'text': text,
                        'auto_tagged': True if auto_tag else False  # Flag for UI to show auto-tagged
                    })
                    idx += 1
    else:
        # Convert sheet coordinates back to crop coordinates for display
        boxes = []
        for region in previous_regions:
            crop_relative_pts = []
            for pt in region['sheet_pts']:  # Use sheet_pts for stored coordinates
                x = pt[0] - current_box['x1']  # Subtract crop's x offset
                y = pt[1] - current_box['y1']  # Subtract crop's y offset
                crop_relative_pts.append([x, y])
            
            boxes.append({
                'id': region['id'],
                'pts': crop_relative_pts,  # Crop-relative for display
                'sheet_pts': region['sheet_pts'],  # Keep sheet coordinates
                'tag': region['tag'],
                'bidItem': region['bidItem'],
                'reason': region.get('reason', ''),  # Get reason if it exists
                'crop_box': region['crop_box'],
                'text': region.get('text', ''),
                'auto_tagged': region.get('auto_tagged', False)
            })

    all_scopes = SCOPES + ['Others']

    return render_template_string("""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
      <title>Sheet {{page_num}} - Figure {{crop_idx+1}}/{{total}}</title>
  <style>
    body { font-family:sans-serif; display:flex; flex-direction:column;
           align-items:center; padding:20px; }
    #canvas { border:1px solid #444; cursor:pointer; margin-bottom:10px; }
    #controls { margin-bottom:20px; }
        #scopeInput, #bidInput, #reasonInput { 
            position: fixed;
            display: none;
            z-index: 10; 
            font-size: 14px; 
            padding: 4px;
            background: white;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        #reasonInput {
            width: 300px;
            height: 100px;
            resize: vertical;
        }
        .nav-links { 
            margin-bottom: 20px; 
            display: flex;
            gap: 20px;
        }
        .nav-links a { 
            color: #4CAF50;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            padding: 5px 10px;
            border-radius: 4px;
            background-color: #f0f8f0;
            transition: background-color 0.2s;
        }
        .nav-links a:hover {
            background-color: #e0f0e0;
            text-decoration: underline;
        }
        .tag-list {
            margin-top: 20px;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 8px;
            width: 100%;
            max-width: 800px;
        }
        .tag-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px;
            margin: 4px 0;
            background: white;
            border-radius: 4px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .tag-text {
            color: #666;
            font-style: italic;
            margin-top: 4px;
            font-size: 0.9em;
        }
        .tag-reason {
            color: #666;
            margin-top: 4px;
            font-size: 0.9em;
            border-top: 1px dashed #eee;
            padding-top: 4px;
        }
        .delete-tag-btn {
            background-color: #f44336;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 4px 8px;
            cursor: pointer;
            font-size: 12px;
            transition: background-color 0.2s;
        }
        .delete-tag-btn:hover {
            background-color: #d32f2f;
        }
        .debug-info {
            position: fixed;
            bottom: 10px;
            right: 10px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 12px;
            display: none;
        }
        .auto-tagged {
            background-color: #e3f2fd;
        }
        .auto-tag-badge {
            background: #2196F3;
            color: white;
            font-size: 10px;
            padding: 2px 6px;
            border-radius: 10px;
            margin-left: 8px;
        }
        .stats {
            margin-bottom: 15px;
            background: #f9f9f9;
            padding: 10px;
            border-radius: 4px;
            font-size: 14px;
        }
  </style>
</head>
<body>
      <div class="nav-links">
        <a href="{{ url_for('select_sheet', upload_id=upload_id) }}">← Back to Sheet Selection</a>
        <a href="{{ url_for('sheet_progress', upload_id=upload_id, page_num=page_num) }}">← Back to Sheet Figures</a>
      </div>
      <h1>Sheet {{page_num}} - Figure {{crop_idx+1}} of {{total}}</h1>
      
      <div class="stats">
        <div>Auto-tagged regions: {{ auto_tagged_count }}</div>
        <div>Total regions: {{ boxes|length }}</div>
      </div>
      
  <canvas id="canvas"></canvas>
  <div id="controls">
    <button id="prevFigureBtn">Previous Figure (P)</button>
    <button id="resetBtn">Reset Selected (R)</button>
    <button id="saveBtn">Save & Next (S)</button>
    <button id="saveOnlyBtn">Save Only</button>
        <button id="toggleDebug">Toggle Debug Info</button>
    <span style="margin-left:1em;">(U=Undo, T=Tag)</span>
  </div>

      <input id="scopeInput" list="scopesList" placeholder="Type or select a scope…">
  <datalist id="scopesList">
    {% for s in all_scopes %}<option value="{{ s }}">{% endfor %}
  </datalist>

      <input id="bidInput" type="text" placeholder="Bid item? (y/n)">
      <textarea id="reasonInput" placeholder="Enter reason for this tag (optional, press Enter to skip)"></textarea>

      <div class="tag-list">
        <h3>Previous Tags</h3>
        <div id="previousTags"></div>
      </div>

      <div id="debugInfo" class="debug-info"></div>

  <script>
    const IMAGE_URL = "{{ image_url }}",
          REGIONS   = {{ boxes|tojson }},
          SCOPES    = {{ all_scopes|tojson }},
          UPLOAD_ID = "{{ upload_id }}",
              PAGE_NUM  = {{ page_num }},
          CROP_IDX  = {{ crop_idx }},
          TOTAL     = {{ total }};

    const canvas     = document.getElementById('canvas'),
          ctx        = canvas.getContext('2d'),
          img        = new Image(),
          scopeInput = document.getElementById('scopeInput'),
              bidInput   = document.getElementById('bidInput'),
              reasonInput = document.getElementById('reasonInput'),
              previousTags = document.getElementById('previousTags'),
              debugInfo = document.getElementById('debugInfo');

    let selected     = new Set(),
        historyStack = [],
            pendingTag   = null,
            lastScrollY  = 0,
            debugMode    = false;

        img.onload = () => { 
            canvas.width = img.width; 
            canvas.height = img.height; 
            redraw(); 
            updatePreviousTagsDisplay();
        };
    img.src = IMAGE_URL;

        function updateDebugInfo(x, y) {
            if (!debugMode) return;
            debugInfo.innerHTML = `
                Mouse: (${x}, ${y})<br>
                Regions: ${REGIONS.length}<br>
                Selected: ${selected.size}<br>
                ${Array.from(selected).map(id => {
                    const r = REGIONS.find(rr => rr.id === id);
                    return `Region ${id}: ${JSON.stringify(r.pts)}`;
                }).join('<br>')}
            `;
        }

        function updatePreviousTagsDisplay() {
            previousTags.innerHTML = '';
            REGIONS.filter(r => r.tag).forEach(r => {
                const div = document.createElement('div');
                div.className = 'tag-item' + (r.auto_tagged ? ' auto-tagged' : '');
                const tagText = typeof r.tag === 'string' ? r.tag : r.tag.value;
                div.innerHTML = `
                    <div>
                        <span class="tag-scope">${tagText}</span>
                        <span class="tag-bid">Bid Item: ${r.bidItem}</span>
                        ${r.auto_tagged ? '<span class="auto-tag-badge">Auto-tagged</span>' : ''}
                        <div class="tag-text">Text: "${r.text || 'N/A'}"</div>
                        ${r.reason ? `<div class="tag-reason">Reason: ${r.reason}</div>` : ''}
                    </div>
                    <div>
                        <button class="delete-tag-btn" data-region-id="${r.id}">Delete</button>
                    </div>
                `;
                previousTags.appendChild(div);
            });
            
            // Add event listeners to delete buttons
            document.querySelectorAll('.delete-tag-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const regionId = parseInt(this.getAttribute('data-region-id'));
                    deleteTag(regionId);
                });
            });
        }
        
        function deleteTag(regionId) {
            // Save current state for undo
            historyStack.push({
                selected: new Set(selected),
                regions: JSON.parse(JSON.stringify(REGIONS))
            });
            
            // Find the region and remove its tag
            const region = REGIONS.find(r => r.id === regionId);
            if (region) {
                region.tag = null;
                region.bidItem = null;
                region.reason = null;
                region.auto_tagged = false;
            }
            
            // Update the display
            redraw();
            updatePreviousTagsDisplay();
        }

    function redraw() {
      ctx.clearRect(0,0,canvas.width,canvas.height);
      ctx.drawImage(img,0,0);
          
          // Draw debug grid
          if (debugMode) {
              ctx.strokeStyle = 'rgba(200,200,200,0.3)';
              ctx.beginPath();
              for(let x = 0; x < canvas.width; x += 50) {
                  ctx.moveTo(x, 0);
                  ctx.lineTo(x, canvas.height);
              }
              for(let y = 0; y < canvas.height; y += 50) {
                  ctx.moveTo(0, y);
                  ctx.lineTo(canvas.width, y);
              }
              ctx.stroke();
          }

      REGIONS.forEach(r => {
        const xs = r.pts.map(p=>p[0]), ys = r.pts.map(p=>p[1]),
              xMin = Math.min(...xs), yMin = Math.min(...ys);
            
            // Draw region background if tagged
        if (r.tag) {
              // Use different colors for auto-tagged vs manually tagged
              ctx.fillStyle = r.auto_tagged ? 'rgba(33,150,243,0.2)' : 'rgba(255,0,0,0.2)';
              ctx.beginPath();
              r.pts.forEach((p,i)=> i? ctx.lineTo(p[0],p[1]) : ctx.moveTo(p[0],p[1]));
              ctx.closePath();
              ctx.fill();
            }

            // Draw region outline
        ctx.strokeStyle = selected.has(r.id)? 'lime':'blue';
            ctx.lineWidth = selected.has(r.id)? 3:2;
            ctx.beginPath();
            r.pts.forEach((p,i)=> i? ctx.lineTo(p[0],p[1]) : ctx.moveTo(p[0],p[1]));
            ctx.closePath();
            ctx.stroke();

            // Draw text and tag if present
            if (r.tag || debugMode) {
              ctx.fillStyle = r.auto_tagged ? '#2196F3' : 'red';
              ctx.font = '14px sans-serif';
              let label = r.tag ? `${typeof r.tag==='string'? r.tag : r.tag.value}(${r.bidItem === 'Yes' ? 'yes' : 'no'})` : '';
              if (r.auto_tagged) {
                label = '🔄 ' + label;  // Add auto-tag indicator
              }
              if (debugMode) {
                  label = `${label} [${r.id}]`;
              }
              ctx.fillText(label, xMin, yMin - 2);

              // Draw OCR text in debug mode
              if (debugMode) {
                  ctx.fillStyle = '#666';
                  ctx.font = '12px sans-serif';
                  ctx.fillText(r.text || '', xMin, yMin + 12);
              }
        }
      });
    }

    // Select/deselect regions
    canvas.addEventListener('click', e => {
      const rect = canvas.getBoundingClientRect(),
                cx = e.clientX - rect.left,
                cy = e.clientY - rect.top;
          
          updateDebugInfo(cx, cy);
          
          let found = false;
      REGIONS.forEach(r => {
            const xs = r.pts.map(p=>p[0]), ys = r.pts.map(p=>p[1]),
                  xMin = Math.min(...xs), xMax = Math.max(...xs),
                  yMin = Math.min(...ys), yMax = Math.max(...ys);
            
            if (cx >= xMin && cx <= xMax && cy >= yMin && cy <= yMax) {
              found = true;
              if (selected.has(r.id)) {
                  selected.delete(r.id);
              } else {
                  selected.add(r.id);
              }
            }
          });
          
          if (found) {
          redraw();
        }
        });

        // Toggle debug mode
        document.getElementById('toggleDebug').onclick = () => {
            debugMode = !debugMode;
            debugInfo.style.display = debugMode ? 'block' : 'none';
            redraw();
        };

    // Keyboard shortcuts
    document.addEventListener('keydown', e => {
          // Don't process keyboard shortcuts when typing in inputs or textarea
          if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
          }
          
          const key = e.key.toUpperCase();
          
          if (key === 'T' && selected.size > 0) {
            e.preventDefault(); // Prevent 'T' from appearing in input
            // Save current state for undo
            historyStack.push({
              selected: new Set(selected),
              regions: JSON.parse(JSON.stringify(REGIONS))
            });
            
            // Show scope input near first selected region
            const firstRegion = REGIONS.find(r => selected.has(r.id));
            const xs = firstRegion.pts.map(p=>p[0]);
            const ys = firstRegion.pts.map(p=>p[1]);
            const xMin = Math.min(...xs);
            const yMin = Math.min(...ys);
            
            const rect = canvas.getBoundingClientRect();
            scopeInput.style.left = (rect.left + xMin) + 'px';
            scopeInput.style.top = (rect.top + window.scrollY + yMin - 30) + 'px';
            scopeInput.style.display = 'block';
            scopeInput.value = '';  // Ensure input is empty
            scopeInput.focus();
            
            pendingTag = {
              regions: Array.from(selected),
              stage: 'scope'
            };
          }
          
          else if (key === 'U' && historyStack.length > 0) {
            const prev = historyStack.pop();
            selected = prev.selected;
            REGIONS.forEach((r,i) => {
              if (prev.regions[i]) {
                r.tag = prev.regions[i].tag;
                r.bidItem = prev.regions[i].bidItem;
                r.reason = prev.regions[i].reason;
                r.auto_tagged = prev.regions[i].auto_tagged;
              }
            });
            redraw();
            updatePreviousTagsDisplay();
          }
          
          else if (key === 'S') {
            document.getElementById('saveBtn').click();
          }
          
          else if (key === 'R') {
            document.getElementById('resetBtn').click();
          }
          
          else if (key === 'P') {
            document.getElementById('prevFigureBtn').click();
          }
        });

        // Handle scope input
    scopeInput.addEventListener('keydown', e => {
          if (e.key === 'Enter' && pendingTag) {
            const scope = scopeInput.value.trim();
            if (scope) {
              scopeInput.style.display = 'none';
              
              // Check if the scope is in the predefined list or "Others"
              if (!SCOPES.includes(scope) && scope !== "Others") {
                alert('Please select a scope from the predefined list or "Others".');
                // Reset and show the input again
                const rect = canvas.getBoundingClientRect();
                const firstRegion = REGIONS.find(r => selected.has(r.id));
                const xs = firstRegion.pts.map(p=>p[0]);
                const ys = firstRegion.pts.map(p=>p[1]);
                const xMin = Math.min(...xs);
                const yMin = Math.min(...ys);
                
                scopeInput.style.left = (rect.left + xMin) + 'px';
                scopeInput.style.top = (rect.top + window.scrollY + yMin - 30) + 'px';
                scopeInput.style.display = 'block';
                scopeInput.focus();
                return;
              }
              
              // If "Others" is selected, prompt for custom scope name
              if (scope === "Others") {
                const customScope = prompt("Enter custom scope name:");
                if (customScope && customScope.trim()) {
                  pendingTag.scope = customScope.trim();
                } else {
                  // If user cancels or enters empty string, use "Others"
                  pendingTag.scope = "Others";
                }
              } else {
                pendingTag.scope = scope;
              }
              
              // Show bid item input
              const rect = canvas.getBoundingClientRect();
              bidInput.style.left = scopeInput.style.left;
              bidInput.style.top = scopeInput.style.top;
              bidInput.style.display = 'block';
              bidInput.value = '';
              bidInput.focus();
              
              pendingTag.stage = 'bidItem';
            }
          }
          else if (e.key === 'Escape') {
            scopeInput.style.display = 'none';
            pendingTag = null;
          }
        });

        // Handle bid item input
        bidInput.addEventListener('keydown', e => {
          if (e.key === 'Enter' && pendingTag) {
            e.preventDefault(); // Prevent default behavior
            const bid = bidInput.value.trim().toLowerCase();
            if (bid === 'y' || bid === 'n') {
              bidInput.style.display = 'none';
              pendingTag.bidItem = bid === 'y' ? 'Yes' : 'No';
              
              // Show reason input
              const rect = canvas.getBoundingClientRect();
              reasonInput.style.left = bidInput.style.left;
              reasonInput.style.top = bidInput.style.top;
              reasonInput.style.display = 'block';
              reasonInput.value = '';
              reasonInput.focus();
              
              pendingTag.stage = 'reason';
            }
          }
          else if (e.key === 'Escape') {
            bidInput.style.display = 'none';
            pendingTag = null;
          }
        });
        
        // Handle reason input
        reasonInput.addEventListener('keydown', e => {
          // Allow normal typing in the textarea, only handle Enter and Escape
          if (e.key === 'Enter' && !e.shiftKey && pendingTag) {
            e.preventDefault(); // Prevent newline in textarea
            const reason = reasonInput.value.trim();
            reasonInput.style.display = 'none';
            
            // Get combined text from all selected regions
            const combinedText = pendingTag.regions
              .map(id => REGIONS.find(r => r.id === id))
              .filter(r => r && r.text)
              .map(r => r.text)
              .join(' ');
            
            // Apply tag to all selected regions
            pendingTag.regions.forEach(id => {
              const region = REGIONS.find(r => r.id === id);
              region.tag = pendingTag.scope;
              region.bidItem = pendingTag.bidItem;
              region.reason = reason;
              region.auto_tagged = false;  // Manually tagged
              region.combinedText = combinedText;  // Store combined text
            });
            
            selected.clear();
            pendingTag = null;
            redraw();
            updatePreviousTagsDisplay();
          }
          else if (e.key === 'Escape') {
            reasonInput.style.display = 'none';
            pendingTag = null;
          }
        });

        // Save button handler
    document.getElementById('saveBtn').onclick = () => {
          // Extract keywords-to-scope mapping
          const keywordMappings = [];
          const processedTexts = new Set();
          
          REGIONS.forEach(r => {
            if (r.tag) {
              // Use combined text if available, otherwise individual text
              const text = r.combinedText || r.text || '';
              
              // Avoid duplicates
              const key = `${text}-${r.tag}-${r.bidItem}`;
              if (!processedTexts.has(key) && text) {
                processedTexts.add(key);
                keywordMappings.push({
                  text: text,
                  scope: r.tag,
                  bidItem: r.bidItem,
                  reason: r.reason || ''
                });
              }
            }
          });
          
          fetch('/save_crop_annotations', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
              upload_id: UPLOAD_ID,
              page_num: PAGE_NUM,
              crop_idx: CROP_IDX,
              regions: REGIONS,
              keyword_mappings: keywordMappings
            })
          })
          .then(r => r.json())
          .then(data => {
            if (data.status === 'ok') {
              window.location.href = data.next_url;
            }
          });
        };

        // Save Only button handler
        document.getElementById('saveOnlyBtn').onclick = () => {
          // Extract keywords-to-scope mapping
          const keywordMappings = [];
          const processedTexts = new Set();
          
          REGIONS.forEach(r => {
            if (r.tag) {
              // Use combined text if available, otherwise individual text
              const text = r.combinedText || r.text || '';
              
              // Avoid duplicates
              const key = `${text}-${r.tag}-${r.bidItem}`;
              if (!processedTexts.has(key) && text) {
                processedTexts.add(key);
                keywordMappings.push({
                  text: text,
                  scope: r.tag,
                  bidItem: r.bidItem,
                  reason: r.reason || ''
                });
              }
            }
          });
          
          fetch('/save_crop_annotations', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
              upload_id: UPLOAD_ID,
              page_num: PAGE_NUM,
              crop_idx: CROP_IDX,
              regions: REGIONS,
              keyword_mappings: keywordMappings,
              stay_on_page: true
            })
          })
          .then(r => r.json())
          .then(data => {
            if (data.status === 'ok') {
              // Show a brief success message
              const saveMsg = document.createElement('div');
              saveMsg.textContent = 'Saved successfully!';
              saveMsg.style.position = 'fixed';
              saveMsg.style.top = '20px';
              saveMsg.style.left = '50%';
              saveMsg.style.transform = 'translateX(-50%)';
              saveMsg.style.backgroundColor = '#4CAF50';
              saveMsg.style.color = 'white';
              saveMsg.style.padding = '10px 20px';
              saveMsg.style.borderRadius = '4px';
              saveMsg.style.zIndex = '1000';
              document.body.appendChild(saveMsg);
              
              // Remove the message after 2 seconds
              setTimeout(() => {
                document.body.removeChild(saveMsg);
              }, 2000);
            }
          });
        };

        // Reset button handler
        document.getElementById('resetBtn').onclick = () => {
          selected.clear();
          redraw();
        };
        
        // Previous Figure button handler
        document.getElementById('prevFigureBtn').onclick = () => {
          // If we're on the first figure of the page
          if (CROP_IDX === 0) {
            // If we're on the first page, stay here
            if (PAGE_NUM === 1) {
              alert('This is the first figure of the first page.');
              return;
            }
            
            // Otherwise, go to the previous page
            // We'll navigate to the sheet progress page and let the user select the last figure
            window.location.href = `/sheet_progress/${UPLOAD_ID}/${PAGE_NUM - 1}`;
          } else {
            // Go to the previous figure on the same page
            window.location.href = `/annotate_crop/${UPLOAD_ID}/${PAGE_NUM}/${CROP_IDX - 1}`;
          }
        };
  </script>
</body>
</html>
    """, 
    upload_id=upload_id,
    page_num=page_num,
    crop_idx=crop_idx,
    total=total,
    boxes=boxes,
    all_scopes=all_scopes,
    image_url=image_url,
    auto_tagged_count=sum(1 for box in boxes if box.get('auto_tagged'))
    )

# ————————————————
# 4) Save annotations
# ————————————————
@app.route('/save_crop_annotations', methods=['POST'])
def save_crop_annotations():
    data = request.get_json()
    uid = data['upload_id']
    page_num = data['page_num']
    idx = data['crop_idx']
    stay_on_page = data.get('stay_on_page', False)
    
    # Extract all text from regions to create combined OCR text
    combined_ocr_text = " ".join([region.get('text', '') for region in data['regions'] if region.get('text')])
    
    # Add combined OCR text to the data
    data['combined_ocr_text'] = combined_ocr_text
    
    # Save annotations
    out_file = os.path.join(ANNOTATIONS_FOLDER, f"{uid}_page{page_num}_crop{idx}.json")
    with open(out_file, 'w') as f:
        json.dump(data, f)

    # Update completion status in crops metadata
    crops_dir = os.path.join(UPLOAD_FOLDER, f"{uid}_page{page_num}_crops")
    meta_path = os.path.join(crops_dir, 'crops.json')
    with open(meta_path) as f:
        meta = json.load(f)
    
    if 'completed_crops' not in meta:
        meta['completed_crops'] = []
    if idx not in meta['completed_crops']:
        meta['completed_crops'].append(idx)
    
    with open(meta_path, 'w') as f:
        json.dump(meta, f)

    # If stay_on_page is True, return current URL, otherwise get next crop index
    if stay_on_page:
        current_url = url_for('annotate_crop', upload_id=uid, page_num=page_num, crop_idx=idx)
        return jsonify(status='ok', next_url=current_url)
    else:
        # Get next crop index
        next_idx = idx + 1
        if next_idx < len(meta['crops']):
            next_url = url_for('annotate_crop', upload_id=uid, page_num=page_num, crop_idx=next_idx)
        else:
            next_url = url_for('sheet_progress', upload_id=uid, page_num=page_num)
        
        return jsonify(status='ok', next_url=next_url)

@app.route('/download_annotations/<upload_id>')
@admin_required
def download_annotations(upload_id):
    # Load metadata
    meta_path = os.path.join(UPLOAD_FOLDER, f"{upload_id}_metadata.json")
    if not os.path.exists(meta_path):
        return 'Invalid upload ID', 404
    
    with open(meta_path) as f:
        meta = json.load(f)
    
    # Collect all annotations for this PDF
    all_annotations = {
        'pdf_info': {
            'filename': meta['filename'],
            'upload_id': upload_id,
            'total_pages': meta['total_pages']
        },
        'pages': {},
        'keyword_mappings': []  # Add a section for keyword mappings
    }
    
    # Process each page
    for page_num in range(1, meta['total_pages'] + 1):
        page_annotations = []
        page_crops = []
        
        # Check if page has been processed
        crops_dir = os.path.join(UPLOAD_FOLDER, f"{upload_id}_page{page_num}_crops")
        crops_meta_path = os.path.join(crops_dir, 'crops.json')
        
        if os.path.exists(crops_meta_path):
            with open(crops_meta_path) as f:
                crops_meta = json.load(f)
            
            # Get YOLO boxes for reference
            yolo_boxes = crops_meta.get('yolo_boxes', [])
            
            # Process each crop in the page
            for crop_idx in range(len(crops_meta.get('crops', []))):
                annotation_file = os.path.join(ANNOTATIONS_FOLDER, f"{upload_id}_page{page_num}_crop{crop_idx}.json")
                if os.path.exists(annotation_file):
                    with open(annotation_file) as f:
                        crop_data = json.load(f)
                    
                    # Get crop box for reference
                    crop_box = next((box for box in yolo_boxes if box['crop_id'] == crop_idx), None)
                    
                    # Add crop data with combined OCR text
                    crop_info = {
                        'crop_id': crop_idx,
                        'crop_box': crop_box,
                        'combined_ocr_text': crop_data.get('combined_ocr_text', '')
                    }
                    page_crops.append(crop_info)
                    
                    # Process regions in this crop
                    if 'regions' in crop_data:
                        for region in crop_data['regions']:
                            if region.get('tag'):
                                # Create a clean annotation entry
                                annotation = {
                                    'text': region.get('text', ''),
                                    'tag': region['tag'],
                                    'bid_item': region['bidItem'],
                                    'reason': region.get('reason', ''),
                                    'auto_tagged': region.get('auto_tagged', False),
                                    'coordinates': {
                                        'sheet_pts': region.get('sheet_pts', []),
                                        'crop_id': crop_idx,
                                        'crop_box': crop_box
                                    }
                                }
                                page_annotations.append(annotation)
                    
                    # Collect keyword mappings
                    if 'keyword_mappings' in crop_data:
                        for mapping in crop_data['keyword_mappings']:
                            # Add page and crop info to the mapping
                            mapping_with_location = mapping.copy()
                            mapping_with_location['page_num'] = page_num
                            mapping_with_location['crop_idx'] = crop_idx
                            all_annotations['keyword_mappings'].append(mapping_with_location)
        
        # Add page annotations if any exist
        if page_annotations or page_crops:
            all_annotations['pages'][str(page_num)] = {
                'annotations': page_annotations,
                'crops': page_crops
            }
    
    # Create the response with the JSON data
    response = app.response_class(
        response=json.dumps(all_annotations, indent=2),
        status=200,
        mimetype='application/json'
    )
    response.headers["Content-Disposition"] = f"attachment; filename={upload_id}_annotations.json"
    return response

@app.route('/admin_dashboard')
@admin_required
def admin_dashboard():
    # Get all projects
    projects = get_projects()
    project_stats = []
    all_scope_stats = {}
    scope_keywords = {}  # Store keywords for each scope
    
    # Process each project
    for project in projects:
        project_id = project['id']
        project_name = project['name']
        
        # Initialize project statistics
        project_stat = {
            'id': project_id,
            'name': project_name,
            'total_pdfs': len(project['pdfs']),
            'total_keywords': 0,
            'scopes': {},
            'bid_items_yes': 0,
            'bid_items_no': 0
        }
        
        # Process each PDF in the project
        for pdf in project['pdfs']:
            upload_id = pdf['upload_id']
            
            # Search for all annotation files for this upload
            for file in os.listdir(ANNOTATIONS_FOLDER):
                if file.startswith(f"{upload_id}_") and file.endswith(".json"):
                    with open(os.path.join(ANNOTATIONS_FOLDER, file)) as f:
                        file_data = json.load(f)
                        
                        # Process keyword mappings
                        if 'keyword_mappings' in file_data:
                            for mapping in file_data['keyword_mappings']:
                                scope = mapping['scope']
                                bid_item = mapping['bidItem']
                                text = mapping['text']
                                
                                # Update project stats
                                project_stat['total_keywords'] += 1
                                
                                # Update scope stats for this project
                                if scope not in project_stat['scopes']:
                                    project_stat['scopes'][scope] = {
                                        'count': 0,
                                        'bid_yes': 0,
                                        'bid_no': 0
                                    }
                                project_stat['scopes'][scope]['count'] += 1
                                
                                # Update bid item counts
                                if bid_item == 'Yes':
                                    project_stat['bid_items_yes'] += 1
                                    project_stat['scopes'][scope]['bid_yes'] += 1
                                else:
                                    project_stat['bid_items_no'] += 1
                                    project_stat['scopes'][scope]['bid_no'] += 1
                                
                                # Update global scope stats
                                if scope not in all_scope_stats:
                                    all_scope_stats[scope] = {
                                        'count': 0,
                                        'bid_yes': 0,
                                        'bid_no': 0
                                    }
                                all_scope_stats[scope]['count'] += 1
                                if bid_item == 'Yes':
                                    all_scope_stats[scope]['bid_yes'] += 1
                                else:
                                    all_scope_stats[scope]['bid_no'] += 1
                                    
                                # Store keywords for each scope
                                if scope not in scope_keywords:
                                    scope_keywords[scope] = []
                                
                                # Add keyword with metadata
                                keyword_info = {
                                    'text': text,
                                    'bid_item': bid_item,
                                    'reason': mapping.get('reason', ''),
                                    'project_name': project_name,
                                    'pdf_name': pdf.get('filename', 'Unknown')
                                }
                                scope_keywords[scope].append(keyword_info)
        
        # Add project stats to the list
        project_stats.append(project_stat)
    
    # Sort scopes by count for better visualization
    sorted_scopes = sorted(all_scope_stats.items(), key=lambda x: x[1]['count'], reverse=True)
    
    # Get top 20 scopes for summary display
    top_scopes = sorted_scopes[:20]
    
    return render_template_string("""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Admin Dashboard - Scope Builder</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {
                font-family: system-ui, -apple-system, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
                color: #333;
            }
            .header {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 30px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .header-left {
                flex: 1;
            }
            .header h1 {
                margin: 0;
                color: #2c3e50;
            }
            .nav-links { 
                margin-bottom: 20px; 
                display: flex;
                gap: 20px;
            }
            .nav-links a { 
                color: #4CAF50;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                padding: 5px 10px;
                border-radius: 4px;
                background-color: #f0f8f0;
                transition: background-color 0.2s;
            }
            .nav-links a:hover {
                background-color: #e0f0e0;
                text-decoration: underline;
            }
            .dashboard-section {
                background: white;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 30px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .dashboard-section h2 {
                margin-top: 0;
                color: #2c3e50;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }
            .stats-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }
            .stat-card {
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                text-align: center;
            }
            .stat-card .number {
                font-size: 2rem;
                font-weight: bold;
                color: #4CAF50;
                margin: 10px 0;
            }
            .stat-card .label {
                color: #666;
                font-size: 0.9rem;
            }
            .chart-container {
                position: relative;
                height: 300px;
                margin-bottom: 30px;
            }
            .project-card {
                background: white;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            .project-card h3 {
                margin-top: 0;
                color: #2c3e50;
            }
            .project-stats {
                display: flex;
                gap: 20px;
                margin-bottom: 15px;
            }
            .project-stat {
                flex: 1;
                text-align: center;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 5px;
            }
            .project-stat .number {
                font-size: 1.5rem;
                font-weight: bold;
                color: #4CAF50;
            }
            .project-stat .label {
                color: #666;
                font-size: 0.8rem;
            }
            .scope-table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            .scope-table th, .scope-table td {
                padding: 8px 12px;
                text-align: left;
                border-bottom: 1px solid #eee;
            }
            .scope-table th {
                background: #f8f9fa;
                color: #2c3e50;
            }
            .scope-table tr:hover {
                background: #f8f9fa;
            }
            .bid-yes {
                color: #4CAF50;
            }
            .bid-no {
                color: #F44336;
            }
            .tabs {
                display: flex;
                margin-bottom: 20px;
                border-bottom: 1px solid #ddd;
            }
            .tab {
                padding: 10px 20px;
                cursor: pointer;
                border-bottom: 2px solid transparent;
            }
            .tab.active {
                border-bottom: 2px solid #4CAF50;
                font-weight: bold;
            }
            .tab-content {
                display: none;
            }
            .tab-content.active {
                display: block;
            }
            .search-container {
                margin-bottom: 20px;
            }
            .search-input {
                padding: 8px 12px;
                width: 100%;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 16px;
            }
            .pagination {
                display: flex;
                justify-content: center;
                margin-top: 20px;
                gap: 10px;
            }
            .pagination button {
                padding: 5px 10px;
                background: #f0f8f0;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            .pagination button:hover {
                background: #e0f0e0;
            }
            .pagination button.active {
                background: #4CAF50;
                color: white;
            }
            .btn {
                padding: 5px 10px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                transition: background-color 0.2s;
            }
            .btn-info {
                background: #2196F3;
                color: white;
            }
            .btn-info:hover {
                background: #1976D2;
            }
            .modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 1000;
                justify-content: center;
                align-items: center;
            }
            .modal-content {
                background: white;
                padding: 20px;
                border-radius: 8px;
                width: 90%;
                max-width: 800px;
                max-height: 80vh;
                overflow-y: auto;
            }
            .modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
                margin-bottom: 15px;
            }
            .modal-header h3 {
                margin: 0;
                color: #2c3e50;
            }
            .close-btn {
                background: none;
                border: none;
                font-size: 1.5rem;
                cursor: pointer;
                color: #666;
            }
            .keyword-item {
                padding: 10px;
                border-bottom: 1px solid #eee;
                margin-bottom: 10px;
            }
            .keyword-text {
                font-size: 1.1rem;
                margin-bottom: 5px;
            }
            .keyword-meta {
                color: #666;
                font-size: 0.9rem;
            }
            .keyword-reason {
                margin-top: 5px;
                font-style: italic;
                color: #666;
                background: #f9f9f9;
                padding: 5px;
                border-left: 3px solid #ddd;
            }
            .badge {
                display: inline-block;
                padding: 3px 8px;
                border-radius: 12px;
                font-size: 0.8rem;
                margin-right: 5px;
            }
            .badge-yes {
                background: #e8f5e9;
                color: #4CAF50;
            }
            .badge-no {
                background: #ffebee;
                color: #F44336;
            }
            .filter-container {
                margin-bottom: 15px;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 4px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-left">
                <h1>Admin Dashboard</h1>
            </div>
            <div>
                <div class="nav-links">
                    <a href="{{ url_for('index') }}">← Back to Projects</a>
                    <a href="{{ url_for('user_management') }}">User Management</a>
                    <a href="{{ url_for('logout') }}">Logout</a>
                </div>
            </div>
        </div>
        
        <div class="dashboard-section">
            <h2>Overall Statistics</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="label">Total Projects</div>
                    <div class="number">{{ projects|length }}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Total PDFs</div>
                    <div class="number">{{ projects|sum(attribute='total_pdfs') }}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Total Keywords Tagged</div>
                    <div class="number">{{ projects|sum(attribute='total_keywords') }}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Total Bid Items (Yes)</div>
                    <div class="number">{{ projects|sum(attribute='bid_items_yes') }}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Total Bid Items (No)</div>
                    <div class="number">{{ projects|sum(attribute='bid_items_no') }}</div>
                </div>
                <div class="stat-card">
                    <div class="label">Unique Scopes Used</div>
                    <div class="number">{{ all_scope_stats|length }}</div>
                </div>
            </div>
            
            <div class="chart-container">
                <canvas id="topScopesChart"></canvas>
            </div>
        </div>
        
        <div class="dashboard-section">
            <h2>Project Analysis</h2>
            
            <div class="tabs">
                <div class="tab active" data-tab="projects">Projects</div>
                <div class="tab" data-tab="scopes">Scopes</div>
            </div>
            
            <div class="tab-content active" id="projects-tab">
                {% for project in projects %}
                <div class="project-card">
                    <h3>{{ project.name }}</h3>
                    <div class="project-stats">
                        <div class="project-stat">
                            <div class="number">{{ project.total_pdfs }}</div>
                            <div class="label">PDFs</div>
                        </div>
                        <div class="project-stat">
                            <div class="number">{{ project.total_keywords }}</div>
                            <div class="label">Keywords</div>
                        </div>
                        <div class="project-stat">
                            <div class="number">{{ project.scopes|length }}</div>
                            <div class="label">Scopes</div>
                        </div>
                        <div class="project-stat">
                            <div class="number">{{ project.bid_items_yes }}</div>
                            <div class="label">Bid Yes</div>
                        </div>
                        <div class="project-stat">
                            <div class="number">{{ project.bid_items_no }}</div>
                            <div class="label">Bid No</div>
                        </div>
                    </div>
                    
                    {% if project.scopes %}
                    <details>
                        <summary>View Scopes ({{ project.scopes|length }})</summary>
                        <table class="scope-table">
                            <thead>
                                <tr>
                                    <th>Scope</th>
                                    <th>Keywords</th>
                                    <th>Bid Yes</th>
                                    <th>Bid No</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for scope, stats in project.scopes.items()|sort(attribute='1.count', reverse=true) %}
                                <tr>
                                    <td>{{ scope }}</td>
                                    <td>{{ stats.count }}</td>
                                    <td class="bid-yes">{{ stats.bid_yes }}</td>
                                    <td class="bid-no">{{ stats.bid_no }}</td>
                                    <td>
                                        <button class="btn btn-info view-keywords-btn" 
                                                data-scope="{{ scope }}" 
                                                data-project="{{ project.name }}">
                                            View Keywords
                                        </button>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </details>
                    {% else %}
                    <p>No scopes tagged in this project yet.</p>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
            
            <div class="tab-content" id="scopes-tab">
                <div class="search-container">
                    <input type="text" id="scopeSearch" class="search-input" placeholder="Search for a scope...">
                </div>
                
                <table class="scope-table" id="scopesTable">
                    <thead>
                        <tr>
                            <th>Scope</th>
                            <th>Total Keywords</th>
                            <th>Bid Yes</th>
                            <th>Bid No</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for scope, stats in all_scope_stats.items()|sort(attribute='1.count', reverse=true) %}
                        <tr class="scope-row">
                            <td>{{ scope }}</td>
                            <td>{{ stats.count }}</td>
                            <td class="bid-yes">{{ stats.bid_yes }}</td>
                            <td class="bid-no">{{ stats.bid_no }}</td>
                            <td>
                                <button class="btn btn-info view-keywords-btn" 
                                        data-scope="{{ scope }}" 
                                        data-project="all">
                                    View Keywords
                                </button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                
                <div class="pagination" id="scopePagination"></div>
            </div>
        </div>
        
        <!-- Keywords Modal -->
        <div id="keywordsModal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3 id="modalTitle">Keywords for Scope</h3>
                    <button class="close-btn">&times;</button>
                </div>
                <div class="filter-container">
                    <input type="text" id="keywordSearch" class="search-input" placeholder="Filter keywords...">
                </div>
                <div id="keywordsContainer"></div>
            </div>
        </div>
        
        <script>
            // Chart for top scopes
            const ctx = document.getElementById('topScopesChart').getContext('2d');
            const topScopesChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: {{ top_scopes|map(attribute=0)|list|tojson }},
                    datasets: [{
                        label: 'Keywords Tagged',
                        data: {{ top_scopes|map(attribute='1.count')|list|tojson }},
                        backgroundColor: 'rgba(76, 175, 80, 0.6)',
                        borderColor: 'rgba(76, 175, 80, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: 'Top 20 Scopes by Keyword Count',
                            font: {
                                size: 16
                            }
                        }
                    }
                }
            });
            
            // Tab switching
            document.querySelectorAll('.tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    // Remove active class from all tabs
                    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                    
                    // Add active class to clicked tab
                    tab.classList.add('active');
                    document.getElementById(tab.dataset.tab + '-tab').classList.add('active');
                });
            });
            
            // Scope search functionality
            const scopeSearch = document.getElementById('scopeSearch');
            const scopeRows = document.querySelectorAll('.scope-row');
            const rowsPerPage = 20;
            let currentPage = 1;
            
            function filterScopes() {
                const searchTerm = scopeSearch.value.toLowerCase();
                let visibleCount = 0;
                
                scopeRows.forEach(row => {
                    const scopeName = row.cells[0].textContent.toLowerCase();
                    if (scopeName.includes(searchTerm)) {
                        row.style.display = '';
                        visibleCount++;
                    } else {
                        row.style.display = 'none';
                    }
                });
                
                // Reset pagination when searching
                if (searchTerm) {
                    document.getElementById('scopePagination').style.display = 'none';
                } else {
                    document.getElementById('scopePagination').style.display = 'flex';
                    updatePagination();
                    goToPage(1);
                }
            }
            
            scopeSearch.addEventListener('input', filterScopes);
            
            // Pagination for scopes
            function updatePagination() {
                const totalPages = Math.ceil(scopeRows.length / rowsPerPage);
                const pagination = document.getElementById('scopePagination');
                pagination.innerHTML = '';
                
                // Previous button
                const prevButton = document.createElement('button');
                prevButton.textContent = '←';
                prevButton.addEventListener('click', () => {
                    if (currentPage > 1) goToPage(currentPage - 1);
                });
                pagination.appendChild(prevButton);
                
                // Page buttons
                for (let i = 1; i <= totalPages; i++) {
                    const pageButton = document.createElement('button');
                    pageButton.textContent = i;
                    if (i === currentPage) pageButton.classList.add('active');
                    pageButton.addEventListener('click', () => goToPage(i));
                    pagination.appendChild(pageButton);
                    
                    // Add ellipsis for many pages
                    if (totalPages > 10) {
                        if (i === 1 || i === totalPages || 
                            (i >= currentPage - 1 && i <= currentPage + 1)) {
                            // Show these page numbers
                        } else if (i === 2 || i === totalPages - 1) {
                            pageButton.textContent = '...';
                            i = i === 2 ? currentPage - 2 : totalPages - 1;
                        } else {
                            pagination.removeChild(pageButton);
                        }
                    }
                }
                
                // Next button
                const nextButton = document.createElement('button');
                nextButton.textContent = '→';
                nextButton.addEventListener('click', () => {
                    if (currentPage < totalPages) goToPage(currentPage + 1);
                });
                pagination.appendChild(nextButton);
            }
            
            function goToPage(page) {
                currentPage = page;
                const start = (page - 1) * rowsPerPage;
                const end = start + rowsPerPage;
                
                scopeRows.forEach((row, index) => {
                    if (index >= start && index < end) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
                
                // Update active button
                document.querySelectorAll('#scopePagination button').forEach(btn => {
                    btn.classList.remove('active');
                    if (btn.textContent == page) btn.classList.add('active');
                });
            }
            
            // Initialize pagination
            updatePagination();
            goToPage(1);
            
            // Keywords modal functionality
            const modal = document.getElementById('keywordsModal');
            const modalTitle = document.getElementById('modalTitle');
            const keywordsContainer = document.getElementById('keywordsContainer');
            const keywordSearch = document.getElementById('keywordSearch');
            const closeBtn = document.querySelector('.close-btn');
            const scopeKeywords = {{ scope_keywords|tojson }};
            
            // Close modal when clicking the close button
            closeBtn.addEventListener('click', () => {
                modal.style.display = 'none';
            });
            
            // Close modal when clicking outside
            window.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.style.display = 'none';
                }
            });
            
            // View keywords buttons
            document.querySelectorAll('.view-keywords-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const scope = btn.dataset.scope;
                    const project = btn.dataset.project;
                    
                    showKeywordsForScope(scope, project);
                });
            });
            
            // Filter keywords in modal
            keywordSearch.addEventListener('input', () => {
                const searchTerm = keywordSearch.value.toLowerCase();
                const keywordItems = document.querySelectorAll('.keyword-item');
                
                keywordItems.forEach(item => {
                    const text = item.querySelector('.keyword-text').textContent.toLowerCase();
                    if (text.includes(searchTerm)) {
                        item.style.display = '';
                    } else {
                        item.style.display = 'none';
                    }
                });
            });
            
            function showKeywordsForScope(scope, projectFilter) {
                // Set modal title
                if (projectFilter === 'all') {
                    modalTitle.textContent = `Keywords for "${scope}" (All Projects)`;
                } else {
                    modalTitle.textContent = `Keywords for "${scope}" in "${projectFilter}"`;
                }
                
                // Clear previous content
                keywordsContainer.innerHTML = '';
                keywordSearch.value = '';
                
                // Get keywords for this scope
                const keywords = scopeKeywords[scope] || [];
                
                if (keywords.length === 0) {
                    keywordsContainer.innerHTML = '<p>No keywords found for this scope.</p>';
                } else {
                    // Filter by project if needed
                    const filteredKeywords = projectFilter === 'all' 
                        ? keywords 
                        : keywords.filter(k => k.project_name === projectFilter);
                    
                    if (filteredKeywords.length === 0) {
                        keywordsContainer.innerHTML = '<p>No keywords found for this scope in this project.</p>';
                    } else {
                        // Create keyword items
                        filteredKeywords.forEach(keyword => {
                            const keywordItem = document.createElement('div');
                            keywordItem.className = 'keyword-item';
                            
                            const bidBadge = keyword.bid_item === 'Yes' 
                                ? '<span class="badge badge-yes">Bid: Yes</span>' 
                                : '<span class="badge badge-no">Bid: No</span>';
                            
                            let reasonHtml = '';
                            if (keyword.reason) {
                                reasonHtml = `<div class="keyword-reason">"${keyword.reason}"</div>`;
                            }
                            
                            keywordItem.innerHTML = `
                                <div class="keyword-text">${keyword.text}</div>
                                <div class="keyword-meta">
                                    ${bidBadge}
                                    <span>Project: ${keyword.project_name}</span>
                                    <span>PDF: ${keyword.pdf_name}</span>
                                </div>
                                ${reasonHtml}
                            `;
                            
                            keywordsContainer.appendChild(keywordItem);
                        });
                    }
                }
                
                // Show modal
                modal.style.display = 'flex';
            }
        </script>
    </body>
    </html>
    """, 
    projects=project_stats, 
    all_scope_stats=all_scope_stats,
    top_scopes=top_scopes,
    scope_keywords=scope_keywords)

if __name__ == '__main__':
    app.run(debug=True)
