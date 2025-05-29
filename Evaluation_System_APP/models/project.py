import os
import json
from uuid import uuid4
from datetime import datetime
from Evaluation_System_APP.config import PROJECTS_FOLDER, UPLOAD_FOLDER, THUMBNAILS_FOLDER, ANNOTATIONS_FOLDER

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

def get_project_by_id(project_id):
    """Get a project by its ID"""
    projects = get_projects()
    project = next((p for p in projects if p['id'] == project_id), None)
    return project

def create_project(name, description=''):
    """Create a new project"""
    if not name:
        return False, 'Project name is required'
    
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
    
    return True, new_project['id']

def add_pdf_to_project(project_id, upload_id, filename):
    """Add a PDF to a project"""
    projects = get_projects()
    project = next((p for p in projects if p['id'] == project_id), None)
    if not project:
        return False, 'Project not found'
    
    project['pdfs'].append({
        'upload_id': upload_id,
        'filename': filename,
        'upload_date': datetime.now().strftime('%Y-%m-%d %H:%M')
    })
    save_projects(projects)
    
    return True, None

def delete_pdf(project_id, upload_id):
    """Delete a PDF from a project and all associated files"""
    if not upload_id:
        return False, 'Upload ID is required'
    
    # Get project
    projects = get_projects()
    project = next((p for p in projects if p['id'] == project_id), None)
    if not project:
        return False, 'Project not found'
    
    # Find the PDF in the project
    pdf_to_delete = next((pdf for pdf in project['pdfs'] if pdf['upload_id'] == upload_id), None)
    if not pdf_to_delete:
        return False, 'PDF not found in project'
    
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
    
    return True, None 