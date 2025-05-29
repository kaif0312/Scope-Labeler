from Evaluation_System_APP.config import app
from Evaluation_System_APP.routes.auth import auth_bp
from Evaluation_System_APP.routes.project import project_bp
from Evaluation_System_APP.routes.pdf import pdf_bp
from Evaluation_System_APP.routes.admin import admin_bp
from Evaluation_System_APP.models.user import create_default_admin
from flask import redirect, url_for

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
    app.run(debug=True) 