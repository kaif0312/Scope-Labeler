from flask import (
    Blueprint, request, redirect, url_for,
    render_template_string, jsonify
)
from Evaluation_System_APP.models.project import (
    get_projects, get_project_by_id, create_project as create_project_model,
    add_pdf_to_project, delete_pdf
)
from Evaluation_System_APP.models.pdf_processor import process_uploaded_pdf
from .auth import login_required, admin_required

project_bp = Blueprint('project', __name__)

@project_bp.route('/')
@login_required
def index():
    projects = get_projects()
    return render_template_string("""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Scope Builder Projects</title>
        <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
        <link rel="stylesheet" href="{{ url_for('static', filename='css/projects.css') }}">
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
                    <a href="{{ url_for('admin.dashboard') }}">Admin Dashboard</a>
                    <a href="{{ url_for('auth.user_management') }}">User Management</a>
                    {% endif %}
                    <a href="{{ url_for('auth.logout') }}">Logout</a>
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
                    <a href="{{ url_for('project.view_project', project_id=project.id) }}" 
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
                <form action="{{ url_for('project.create_project') }}" method="post">
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

        <script src="{{ url_for('static', filename='js/projects.js') }}"></script>
    </body>
    </html>
    """, projects=projects)

@project_bp.route('/create_project', methods=['POST'])
@login_required
def create_project():
    name = request.form.get('name')
    description = request.form.get('description', '')
    
    success, project_id = create_project_model(name, description)
    
    if not success:
        return project_id, 400
    
    return redirect(url_for('project.view_project', project_id=project_id))

@project_bp.route('/project/<project_id>')
@login_required
def view_project(project_id):
    project = get_project_by_id(project_id)
    if not project:
        return 'Project not found', 404

    return render_template_string("""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{{ project.name }} - Scope Builder</title>
        <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
        <link rel="stylesheet" href="{{ url_for('static', filename='css/project_view.css') }}">
    </head>
    <body>
        <div class="header">
            <div class="header-left">
                <a href="{{ url_for('project.index') }}" class="nav-link">← Back to Projects</a>
                <h1>{{ project.name }}</h1>
                {% if project.description %}
                <p>{{ project.description }}</p>
                {% endif %}
            </div>
        </div>

        <div class="upload-form">
            <h2>Upload New PDF</h2>
            <form action="{{ url_for('project.upload_pdf', project_id=project.id) }}" 
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
                        <a href="{{ url_for('pdf.select_sheet', upload_id=pdf.upload_id) }}" 
                           class="btn btn-primary">Process PDF</a>
                        {% if session.role == 'admin' %}
                        <a href="{{ url_for('pdf.download_annotations', upload_id=pdf.upload_id) }}" 
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

        <script src="{{ url_for('static', filename='js/project_view.js') }}"></script>
    </body>
    </html>
    """, project=project)

@project_bp.route('/project/<project_id>/upload', methods=['POST'])
@login_required
def upload_pdf(project_id):
    project = get_project_by_id(project_id)
    if not project:
        return 'Project not found', 404

    file = request.files.get('file')
    if not file or not file.filename.lower().endswith('.pdf'):
        return 'Please upload a PDF', 400

    try:
        success, result = process_uploaded_pdf(file, project_id)
        
        if not success:
            return result, 500
        
        upload_id = result
        
        # Update project information
        add_pdf_to_project(project_id, upload_id, file.filename)

        return redirect(url_for('pdf.select_sheet', upload_id=upload_id))
    
    except Exception as e:
        print(f"Unexpected error during PDF upload: {e}")
        return f"Error uploading PDF: {str(e)}", 500

@project_bp.route('/project/<project_id>/delete_pdf', methods=['POST'])
@admin_required
def delete_pdf_route(project_id):
    upload_id = request.args.get('upload_id')
    
    success, message = delete_pdf(project_id, upload_id)
    
    if not success:
        return message, 400
    
    return redirect(url_for('project.view_project', project_id=project_id)) 