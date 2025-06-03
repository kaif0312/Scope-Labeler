from flask import (
    Blueprint, request, redirect, url_for,
    render_template_string, jsonify, send_from_directory
)
from Evaluation_System_APP.models.pdf_processor import (
    get_pdf_metadata, get_page_progress, process_sheet as process_sheet_function,
    get_crops_metadata, run_ocr_on_crop, save_crop_annotations,
    get_annotations_for_download
)
from Evaluation_System_APP.config import UPLOAD_FOLDER, THUMBNAILS_FOLDER, ANNOTATIONS_FOLDER, SCOPES
from .auth import login_required, admin_required
import os
import json

pdf_bp = Blueprint('pdf', __name__)

@pdf_bp.route('/select_sheet/<upload_id>')
@login_required
def select_sheet(upload_id):
    # Load metadata
    meta = get_pdf_metadata(upload_id)
    if not meta:
        return 'Invalid upload ID', 404
    
    # Calculate completion percentage for each page
    page_progress = get_page_progress(upload_id, meta)

    return render_template_string("""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Select Sheet to Process - {{ meta.filename }}</title>
        <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
        <link rel="stylesheet" href="{{ url_for('static', filename='css/select_sheet.css') }}">
    </head>
    <body>
        <a href="{{ url_for('project.index') }}" class="nav-link">← Back to Projects</a>
        <h1>{{ meta.filename }} - Select Sheet to Process</h1>
        <div class="sheets-container">
            {% for i in range(meta.total_pages) %}
            {% set progress = page_progress[i+1] %}
            <div class="sheet-card {% if progress.percent == 100 %}processed{% endif %}">
                <img src="{{ url_for('pdf.thumbnails', filename=meta.upload_id + '/' + meta.thumbnails[i]) }}" 
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
                        <a href="{{ url_for('pdf.process_sheet', upload_id=meta.upload_id, page_num=i+1) }}" 
                           class="process-btn">Process Sheet</a>
                    {% else %}
                        <div class="status-badge processed">Completed</div>
                        <a href="{{ url_for('pdf.sheet_progress', upload_id=meta.upload_id, page_num=i+1) }}" 
                           class="process-btn">View Progress</a>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """, meta=meta, page_progress=page_progress)

@pdf_bp.route('/process_sheet/<upload_id>/<int:page_num>')
@login_required
def process_sheet(upload_id, page_num):
    """Process a sheet from a PDF"""
    success, error_message = process_sheet_function(upload_id, int(page_num))
    
    if success:
        return redirect(url_for('pdf.sheet_progress', upload_id=upload_id, page_num=page_num))
    else:
        return f'Error processing sheet: {error_message}', 500

@pdf_bp.route('/sheet_progress/<upload_id>/<int:page_num>')
@login_required
def sheet_progress(upload_id, page_num):
    # Load metadata
    meta = get_crops_metadata(upload_id, page_num)
    
    # If the sheet hasn't been processed yet, process it directly
    if not meta:
        success, error_message = process_sheet_function(upload_id, int(page_num))
        if not success:
            return f'Error processing sheet: {error_message}', 500
        # Reload metadata after processing
        meta = get_crops_metadata(upload_id, page_num)
        if not meta:
            return 'Error loading sheet metadata after processing', 500
    
    # Ensure all required keys exist
    if not all(key in meta for key in ['crops', 'completed_crops', 'total_figures']):
        # If metadata is incomplete, process the sheet directly
        success, error_message = process_sheet_function(upload_id, int(page_num))
        if not success:
            return f'Error processing sheet: {error_message}', 500
        # Reload metadata after processing
        meta = get_crops_metadata(upload_id, page_num)
        if not all(key in meta for key in ['crops', 'completed_crops', 'total_figures']):
            return 'Error: Metadata is still incomplete after processing', 500
    
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
        <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
        <link rel="stylesheet" href="{{ url_for('static', filename='css/sheet_progress.css') }}">
    </head>
    <body>
        <div class="nav-links">
            <a href="{{ url_for('pdf.select_sheet', upload_id=upload_id) }}">← Back to Sheet Selection</a>
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
                <a href="{{ url_for('pdf.annotate_crop', upload_id=upload_id, page_num=page_num, crop_idx=idx) }}">
                    Figure {{idx + 1}}
                </a>{% if not loop.last %}, {% endif %}
            {% endfor %}
            </p>
        </div>
        {% endif %}

        <div class="figures-grid">
            {% for idx in range(total_figures) %}
            <div class="figure-card {{ 'completed' if idx in completed_crops else 'incomplete' }}"
                 onclick="window.location.href='{{ url_for('pdf.annotate_crop', upload_id=upload_id, page_num=page_num, crop_idx=idx) }}'">
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

@pdf_bp.route('/thumbnails/<path:filename>')
@login_required
def thumbnails(filename):
    return send_from_directory(THUMBNAILS_FOLDER, filename)

@pdf_bp.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@pdf_bp.route('/annotate_crop/<upload_id>/<int:page_num>/<int:crop_idx>')
@login_required
def annotate_crop(upload_id, page_num, crop_idx):
    # Load crop metadata
    meta = get_crops_metadata(upload_id, page_num)
    if not meta:
        return redirect(url_for('pdf.process_sheet', upload_id=upload_id, page_num=page_num))
    
    crop_list = meta['crops']
    yolo_boxes = meta['yolo_boxes']
    
    total = len(crop_list)
    if crop_idx >= total:
        return redirect(url_for('pdf.select_sheet', upload_id=upload_id))

    # Pick this crop
    img_fn = crop_list[crop_idx]
    image_url = url_for('pdf.uploaded_file', filename=f"{upload_id}_page{page_num}_crops/{img_fn}")
    
    # Get current box
    current_box = next(box for box in yolo_boxes if box['crop_id'] == crop_idx)
    
    # Run OCR or load previous annotations
    boxes = run_ocr_on_crop(upload_id, page_num, crop_idx) or []

    # Auto-tagging is already handled in the pdf_processor.py module
    # The run_ocr_on_crop function already checks for existing tags and auto-tags regions

    all_scopes = SCOPES + ['Others']

    return render_template_string("""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Sheet {{page_num}} - Figure {{crop_idx+1}}/{{total}}</title>
        <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
        <link rel="stylesheet" href="{{ url_for('static', filename='css/annotate.css') }}">
    </head>
    <body>
        <div class="nav-links">
            <a href="{{ url_for('pdf.select_sheet', upload_id=upload_id) }}">← Back to Sheet Selection</a>
            <a href="{{ url_for('pdf.sheet_progress', upload_id=upload_id, page_num=page_num) }}">← Back to Sheet Figures</a>
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
        </script>
        <script src="{{ url_for('static', filename='js/annotate.js') }}"></script>
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

@pdf_bp.route('/save_crop_annotations', methods=['POST'])
@login_required
def save_crop_annotations_route():
    data = request.get_json()
    stay_on_page = data.get('stay_on_page', False)
    
    # Call the model function to save annotations and apply auto-tagging
    success = save_crop_annotations(data)
    
    if not success:
        return jsonify(status='error', message='Failed to save annotations'), 500

    # If stay_on_page is True, return current URL, otherwise get next crop index
    if stay_on_page:
        # For "Save Only", we want to return a refresh of the current page to show auto-tags
        current_url = url_for('pdf.annotate_crop', 
                             upload_id=data['upload_id'], 
                             page_num=data['page_num'], 
                             crop_idx=data['crop_idx'])
        return jsonify(status='ok', next_url=current_url)
    else:
        # Get next crop index
        meta = get_crops_metadata(data['upload_id'], data['page_num'])
        next_idx = data['crop_idx'] + 1
        if next_idx < len(meta['crops']):
            next_url = url_for('pdf.annotate_crop', 
                              upload_id=data['upload_id'], 
                              page_num=data['page_num'], 
                              crop_idx=next_idx)
        else:
            next_url = url_for('pdf.sheet_progress', 
                              upload_id=data['upload_id'], 
                              page_num=data['page_num'])
        
        return jsonify(status='ok', next_url=next_url)

@pdf_bp.route('/download_annotations/<upload_id>')
@admin_required
def download_annotations(upload_id):
    """Download all annotations for a PDF as a JSON file"""
    # Get PDF metadata to include filename in the download
    meta_path = os.path.join(UPLOAD_FOLDER, f"{upload_id}_metadata.json")
    if not os.path.exists(meta_path):
        return 'Invalid upload ID: Metadata file not found', 404
    
    try:
        with open(meta_path) as f:
            meta = json.load(f)
        
        # Get all annotations
        annotations = get_annotations_for_download(upload_id)
        if not annotations:
            return 'Failed to generate annotations: No data found', 404
        
        # Create a sanitized filename from the original PDF name
        original_filename = meta.get('filename', 'unknown')
        safe_filename = original_filename.replace(' ', '_').replace('.pdf', '')
        download_filename = f"{safe_filename}_annotations_{upload_id}.json"
        
        # Create the response with the JSON data
        response = jsonify(annotations)
        response.headers["Content-Disposition"] = f"attachment; filename={download_filename}"
        response.headers["Content-Type"] = "application/json"
        
        # Include file size in the header
        json_data = json.dumps(annotations)
        response.headers["Content-Length"] = len(json_data)
        
        return response
    
    except Exception as e:
        print(f"Error generating annotations for download: {e}")
        return f'Error generating annotations: {str(e)}', 500 