import os
import json
import hashlib
from uuid import uuid4
from datetime import datetime
from Evaluation_System_APP.config import USERS_FOLDER

# Custom password hashing functions that use SHA-256 (supported in Python 3.13)
def generate_password_hash(password):
    """Generate a SHA-256 hash of the password with a salt"""
    salt = os.urandom(16).hex()  # Generate a random salt
    hash_obj = hashlib.sha256((salt + password).encode())
    password_hash = hash_obj.hexdigest()
    return f"sha256${salt}${password_hash}"

def check_password_hash(stored_hash, password):
    """Check if the password matches the stored hash"""
    try:
        # Parse the stored hash format: algorithm$salt$hash
        alg, salt, hash_value = stored_hash.split('$')
        if alg != 'sha256':
            # Handle old format hashes (from werkzeug)
            # This is a placeholder for migration - won't work for old hashes
            return False
            
        # Compute hash with the same salt
        computed_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        return computed_hash == hash_value
    except Exception:
        # Any parsing error means invalid hash format
        return False

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

def create_user(username, password, role):
    """Create a new user"""
    if not username or not password or not role:
        return False, 'All fields are required'
    
    if role not in ['admin', 'worker']:
        return False, 'Invalid role'
    
    users = get_users()
    
    # Check if username already exists
    for user in users.values():
        if user['username'] == username:
            return False, 'Username already exists'
    
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
    return True, user_id

def delete_user(user_id, current_user_id):
    """Delete a user"""
    if not user_id:
        return False, 'User ID is required'
    
    # Get users
    users = get_users()
    
    # Check if user exists
    if user_id not in users:
        return False, 'User not found'
    
    # Check if trying to delete self
    if user_id == current_user_id:
        return False, 'Cannot delete your own account'
    
    # Delete user
    del users[user_id]
    save_users(users)
    
    return True, None

def authenticate_user(username, password):
    """Authenticate a user"""
    users = get_users()
    user = None
    
    # Find user by username
    for user_id, user_data in users.items():
        if user_data['username'] == username:
            user = user_data
            break
    
    if user and check_password_hash(user['password'], password):
        return True, user
    else:
        return False, None 