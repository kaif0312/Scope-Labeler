from flask import Blueprint, render_template_string
from Evaluation_System_APP.models.project import get_projects
from Evaluation_System_APP.models.pdf_processor import get_annotations_for_download
from .auth import admin_required
import os
import json
from Evaluation_System_APP.config import ANNOTATIONS_FOLDER

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin_dashboard')
@admin_required
def dashboard():
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
        <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
        <link rel="stylesheet" href="{{ url_for('static', filename='css/admin.css') }}">
    </head>
    <body>
        <div class="header">
            <div class="header-left">
                <h1>Admin Dashboard</h1>
            </div>
            <div>
                <div class="nav-links">
                    <a href="{{ url_for('project.index') }}">← Back to Projects</a>
                    <a href="{{ url_for('auth.user_management') }}">User Management</a>
                    <a href="{{ url_for('auth.logout') }}">Logout</a>
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
            // Pass data to JavaScript
            const scopeKeywords = {{ scope_keywords|tojson }};
            const topScopes = {{ top_scopes|tojson }};
        </script>
        <script src="{{ url_for('static', filename='js/admin.js') }}"></script>
    </body>
    </html>
    """, 
    projects=project_stats, 
    all_scope_stats=all_scope_stats,
    top_scopes=top_scopes,
    scope_keywords=scope_keywords) 