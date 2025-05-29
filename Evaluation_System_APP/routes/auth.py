from flask import (
    Blueprint, request, redirect, url_for,
    render_template_string, session, flash
)
from functools import wraps
from Evaluation_System_APP.models.user import authenticate_user, create_user, delete_user, get_users

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login', next=request.url))
        
        users = get_users()
        user = users.get(session['user_id'])
        
        if not user or user['role'] != 'admin':
            return 'Access denied: Admin privileges required', 403
            
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        success, user = authenticate_user(username, password)
        
        if success:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('project.index'))
        else:
            error = 'Invalid username or password'
    
    return render_template_string("""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Login - Scope Builder</title>
        <link rel="stylesheet" href="{{ url_for('static', filename='css/login.css') }}">
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

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/user_management')
@admin_required
def user_management():
    users = get_users()
    return render_template_string("""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>User Management - Scope Builder</title>
        <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
        <link rel="stylesheet" href="{{ url_for('static', filename='css/user_management.css') }}">
    </head>
    <body>
        <div class="header">
            <div class="header-left">
                <a href="{{ url_for('project.index') }}" class="nav-link">← Back to Projects</a>
                <h1>User Management</h1>
            </div>
            <div>
                <a href="{{ url_for('auth.logout') }}" class="btn btn-secondary">Logout</a>
            </div>
        </div>

        <div class="create-form">
            <h2>Create New User</h2>
            <form action="{{ url_for('auth.create_user_route') }}" method="post">
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

        <script src="{{ url_for('static', filename='js/user_management.js') }}"></script>
    </body>
    </html>
    """, users=users)

@auth_bp.route('/create_user', methods=['POST'])
@admin_required
def create_user_route():
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')
    
    success, message = create_user(username, password, role)
    
    if not success:
        flash(message, 'error')
    
    return redirect(url_for('auth.user_management'))

@auth_bp.route('/delete_user', methods=['POST'])
@admin_required
def delete_user_route():
    user_id = request.args.get('user_id')
    
    success, message = delete_user(user_id, session['user_id'])
    
    if not success:
        flash(message, 'error')
    
    return redirect(url_for('auth.user_management')) 