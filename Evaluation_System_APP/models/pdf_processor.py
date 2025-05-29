import os
import json
import time
from uuid import uuid4
from pdf2image import convert_from_path
from Evaluation_System_APP.config import (
    UPLOAD_FOLDER, THUMBNAILS_FOLDER, ANNOTATIONS_FOLDER,
    PDF_DPI, THUMBNAIL_DPI, METADATA_DPI
)

# Import YOLO and Azure client in a way that allows for lazy loading
# This helps avoid loading these heavy dependencies unless needed
def get_yolo():
    from ultralytics import YOLO
    from Evaluation_System_APP.config import YOLO_WEIGHTS
    return YOLO(YOLO_WEIGHTS)

def get_cv_client():
    from azure.cognitiveservices.vision.computervision import ComputerVisionClient
    from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
    from msrest.authentication import CognitiveServicesCredentials
    from Evaluation_System_APP.config import AZURE_ENDPOINT, AZURE_KEY
    return ComputerVisionClient(
        AZURE_ENDPOINT,
        CognitiveServicesCredentials(AZURE_KEY)
    ), OperationStatusCodes

def process_uploaded_pdf(file, project_id):
    """Process an uploaded PDF file"""
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
        return False, f"Error processing PDF: {str(e)}"

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

    return True, upload_id

def get_pdf_metadata(upload_id):
    """Get metadata for a PDF"""
    meta_path = os.path.join(UPLOAD_FOLDER, f"{upload_id}_metadata.json")
    if not os.path.exists(meta_path):
        return None
    
    with open(meta_path) as f:
        return json.load(f)

def get_page_progress(upload_id, meta):
    """Calculate completion percentage for each page"""
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
    
    return page_progress

def process_sheet(upload_id, page_num):
    """Process a single sheet (page) from a PDF"""
    # Load metadata
    meta_path = os.path.join(UPLOAD_FOLDER, f"{upload_id}_metadata.json")
    if not os.path.exists(meta_path):
        return False, 'Invalid upload ID'
    
    with open(meta_path) as f:
        meta = json.load(f)
    
    if page_num < 1 or page_num > meta['total_pages']:
        return False, 'Invalid page number'

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
        yolo = get_yolo()
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
        
        return True, None
        
    except Exception as e:
        print(f"Error processing sheet {page_num}: {e}")
        return False, f"Error processing sheet: {str(e)}"

def get_crops_metadata(upload_id, page_num):
    """Get metadata for crops on a page"""
    crops_dir = os.path.join(UPLOAD_FOLDER, f"{upload_id}_page{page_num}_crops")
    meta_path = os.path.join(crops_dir, 'crops.json')
    
    if not os.path.exists(meta_path):
        return None
        
    with open(meta_path) as f:
        return json.load(f)

def run_ocr_on_crop(upload_id, page_num, crop_idx):
    """Run OCR on a specific crop of a PDF page"""
    # Find the crops directory and metadata file
    crops_dir = os.path.join(UPLOAD_FOLDER, f"{upload_id}_page{page_num}_crops")
    meta_path = os.path.join(crops_dir, 'crops.json')
    
    if not os.path.exists(meta_path):
        return None
        
    with open(meta_path) as f:
        meta = json.load(f)
    
    if crop_idx >= len(meta['crops']):
        return None
    
    img_fn = meta['crops'][crop_idx]
    yolo_boxes = meta['yolo_boxes']
    current_box = next(box for box in yolo_boxes if box['crop_id'] == crop_idx)
    
    # Check if we already have annotations for this crop
    annotation_file = os.path.join(ANNOTATIONS_FOLDER, f"{upload_id}_page{page_num}_crop{crop_idx}.json")
    if os.path.exists(annotation_file):
        with open(annotation_file) as f:
            previous_data = json.load(f)
            previous_regions = previous_data.get('regions', [])
            
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
                    'auto_tagged': region.get('auto_tagged', False)  # Preserve auto_tagged status
                })
            return boxes
    
    # Find all existing tags for this upload_id to enable auto-tagging
    existing_tags = {}
    try:
        # First, look for tags within the same sheet to allow auto-tagging of identical text
        for crop_id in range(len(meta['crops'])):
            # Skip the current crop, only look at other crops on the same sheet
            if crop_id == crop_idx:
                continue
                
            # Check if this crop has annotations
            crop_annotation_file = os.path.join(ANNOTATIONS_FOLDER, f"{upload_id}_page{page_num}_crop{crop_id}.json")
            if os.path.exists(crop_annotation_file):
                with open(crop_annotation_file) as f:
                    crop_data = json.load(f)
                    if 'regions' in crop_data:
                        for region in crop_data['regions']:
                            if region.get('tag') and region.get('text'):
                                # Store the tag and bid item for each unique text
                                text = region['text'].strip().lower()
                                if text and len(text) > 2:  # Ignore very short text
                                    existing_tags[text] = {
                                        'tag': region['tag'],
                                        'bidItem': region['bidItem'],
                                        'reason': region.get('reason', ''),
                                        'source': f"same_sheet_crop_{crop_id}"
                                    }
        
        # Then, look at annotations from other pages
        for file in os.listdir(ANNOTATIONS_FOLDER):
            if file.startswith(f"{upload_id}_") and file.endswith(".json"):
                # Skip the current crop file
                if file == f"{upload_id}_page{page_num}_crop{crop_idx}.json":
                    continue
                
                # Skip other crops from the same page that we've already processed above
                if file.startswith(f"{upload_id}_page{page_num}_crop"):
                    continue
                    
                with open(os.path.join(ANNOTATIONS_FOLDER, file)) as f:
                    file_data = json.load(f)
                    if 'regions' in file_data:
                        for region in file_data['regions']:
                            if region.get('tag') and region.get('text'):
                                # Store the tag and bid item for each unique text
                                text = region['text'].strip().lower()
                                if text and len(text) > 2:  # Ignore very short text
                                    # Only add if not already added from same sheet
                                    if text not in existing_tags:
                                        existing_tags[text] = {
                                            'tag': region['tag'],
                                            'bidItem': region['bidItem'],
                                            'reason': region.get('reason', ''),
                                            'source': file
                                        }
    except Exception as e:
        print(f"Error loading existing tags: {e}")
    
    # Run OCR
    boxes = []
    try:
        cv_client, OperationStatusCodes = get_cv_client()
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
            
            # First pass - collect all detected text
            all_detected_text = []
            for page in result.analyze_result.read_results:
                for line in page.lines:
                    all_detected_text.append(line.text.strip().lower())
            
            # Count occurrences of each text
            text_counts = {}
            for text in all_detected_text:
                if text and len(text) > 2:  # Ignore very short text
                    text_counts[text] = text_counts.get(text, 0) + 1
            
            # Process each text region
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
                    text_lower = text.strip().lower()
                    
                    # Check if this text has been tagged before
                    auto_tag = None
                    auto_bid_item = None
                    auto_reason = None
                    auto_source = None
                    
                    # Auto-tag based on existing annotations
                    if text_lower in existing_tags:
                        auto_tag = existing_tags[text_lower]['tag']
                        auto_bid_item = existing_tags[text_lower]['bidItem']
                        auto_reason = existing_tags[text_lower].get('reason', '')
                        auto_source = existing_tags[text_lower].get('source', '')
                    
                    boxes.append({
                        'id': idx,
                        'pts': pts,  # Crop-relative coordinates for display
                        'sheet_pts': list(zip(sheet_coords[0::2], sheet_coords[1::2])),  # Sheet-relative coordinates for storage
                        'tag': auto_tag,  # Auto-tag if text matches
                        'bidItem': auto_bid_item,  # Auto-set bid item
                        'reason': auto_reason,  # Auto-set reason
                        'crop_box': current_box,
                        'text': text,
                        'auto_tagged': True if auto_tag else False,  # Flag for UI to show auto-tagged
                        'auto_source': auto_source,  # For debugging
                        'text_count': text_counts.get(text_lower, 0)  # Store count for second pass
                    })
                    idx += 1
            
            # Second pass - auto-tag repetitive text within the same crop
            # Find the first manually tagged instance of each repetitive text
            tagged_text = {}
            for box in boxes:
                text_lower = box['text'].strip().lower()
                if text_lower and box['tag'] and box['text_count'] > 1 and not box.get('auto_tagged', False):
                    if text_lower not in tagged_text:
                        tagged_text[text_lower] = {
                            'tag': box['tag'],
                            'bidItem': box['bidItem'],
                            'reason': box.get('reason', '')
                        }
            
            # Apply tags to other instances of the same text
            for box in boxes:
                text_lower = box['text'].strip().lower()
                if text_lower in tagged_text and not box['tag']:
                    box['tag'] = tagged_text[text_lower]['tag']
                    box['bidItem'] = tagged_text[text_lower]['bidItem']
                    box['reason'] = tagged_text[text_lower]['reason']
                    box['auto_tagged'] = True
                    box['auto_source'] = 'same_crop_repetitive_text'
            
            # Remove the temporary text_count field
            for box in boxes:
                if 'text_count' in box:
                    del box['text_count']
        
        return boxes
    except Exception as e:
        print(f"Error running OCR: {e}")
        return []

def save_crop_annotations(data):
    """Save annotations for a crop"""
    uid = data['upload_id']
    page_num = data['page_num']
    idx = data['crop_idx']
    
    # Extract all text from regions to create combined OCR text
    combined_ocr_text = " ".join([region.get('text', '') for region in data['regions'] if region.get('text')])
    
    # Add combined OCR text to the data
    data['combined_ocr_text'] = combined_ocr_text
    
    # Apply auto-tagging to repeated text instances in the same crop
    # This ensures that if a user manually tags one instance, other identical instances are auto-tagged
    tagged_regions = {}
    for region in data['regions']:
        if region.get('tag') and region.get('text') and not region.get('auto_tagged', False):
            text_lower = region['text'].strip().lower()
            if text_lower and len(text_lower) > 2:  # Ignore very short text
                tagged_regions[text_lower] = {
                    'tag': region['tag'],
                    'bidItem': region['bidItem'],
                    'reason': region.get('reason', '')
                }
    
    # Apply tags to untagged instances of the same text
    for region in data['regions']:
        text_lower = region['text'].strip().lower() if region.get('text') else ''
        if text_lower in tagged_regions and not region.get('tag'):
            region['tag'] = tagged_regions[text_lower]['tag']
            region['bidItem'] = tagged_regions[text_lower]['bidItem']
            region['reason'] = tagged_regions[text_lower]['reason']
            region['auto_tagged'] = True
            if not region.get('auto_source'):
                region['auto_source'] = 'auto_tagged_on_save'
    
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
    
    # Now auto-tag identical text in other crops of the same sheet
    if tagged_regions:  # Only do this if we have manual tags to propagate
        for crop_id in range(len(meta['crops'])):
            # Skip the current crop, we already processed it
            if crop_id == idx:
                continue
                
            # Check if this crop has annotations
            crop_annotation_file = os.path.join(ANNOTATIONS_FOLDER, f"{uid}_page{page_num}_crop{crop_id}.json")
            if os.path.exists(crop_annotation_file):
                updated = False
                
                with open(crop_annotation_file) as f:
                    crop_data = json.load(f)
                
                # Auto-tag matching text regions
                if 'regions' in crop_data:
                    for region in crop_data['regions']:
                        if region.get('text') and not region.get('tag'):
                            text_lower = region['text'].strip().lower()
                            if text_lower in tagged_regions:
                                region['tag'] = tagged_regions[text_lower]['tag']
                                region['bidItem'] = tagged_regions[text_lower]['bidItem']
                                region['reason'] = tagged_regions[text_lower]['reason']
                                region['auto_tagged'] = True
                                region['auto_source'] = 'cross_crop_auto_tagged'
                                updated = True
                
                # If we made any changes, save the updated annotations
                if updated:
                    with open(crop_annotation_file, 'w') as f:
                        json.dump(crop_data, f)
    
    return True

def get_annotations_for_download(upload_id):
    """Collect all annotations for a PDF"""
    # Load metadata
    meta_path = os.path.join(UPLOAD_FOLDER, f"{upload_id}_metadata.json")
    if not os.path.exists(meta_path):
        return None
    
    with open(meta_path) as f:
        meta = json.load(f)
    
    # Collect all annotations for this PDF
    all_annotations = {
        'pdf_info': {
            'filename': meta['filename'],
            'upload_id': upload_id,
            'total_pages': meta['total_pages'],
            'processed_pages': meta.get('processed_pages', []),
            'thumbnails': meta.get('thumbnails', [])
        },
        'pages': {},
        'keyword_mappings': [],  # Add a section for keyword mappings
        'unique_scopes': set()   # Will be converted to list before returning
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
            completed_crops = crops_meta.get('completed_crops', [])
            
            # Get page thumbnail if available
            page_thumbnail = None
            if meta.get('thumbnails') and page_num <= len(meta.get('thumbnails')):
                page_thumbnail = meta['thumbnails'][page_num - 1]
            
            # Include all YOLO boxes in the page data
            page_data = {
                'annotations': page_annotations,
                'crops': page_crops,
                'yolo_boxes': yolo_boxes,
                'completed_crops': completed_crops,
                'total_figures': crops_meta.get('total_figures', len(crops_meta.get('crops', []))),
                'thumbnail': page_thumbnail,
                'page_num': page_num
            }
            
            # Process each crop in the page
            for crop_idx in range(len(crops_meta.get('crops', []))):
                annotation_file = os.path.join(ANNOTATIONS_FOLDER, f"{upload_id}_page{page_num}_crop{crop_idx}.json")
                if os.path.exists(annotation_file):
                    with open(annotation_file) as f:
                        crop_data = json.load(f)
                    
                    # Get crop box for reference
                    crop_box = next((box for box in yolo_boxes if box['crop_id'] == crop_idx), None)
                    
                    # Construct the full crop image path and URL
                    crop_filename = crops_meta['crops'][crop_idx] if crop_idx < len(crops_meta['crops']) else None
                    crop_image_path = None
                    if crop_filename:
                        crop_image_path = f"{upload_id}_page{page_num}_crops/{crop_filename}"
                    
                    # Add complete crop data
                    crop_info = {
                        'crop_id': crop_idx,
                        'crop_box': crop_box,
                        'combined_ocr_text': crop_data.get('combined_ocr_text', ''),
                        'is_completed': crop_idx in completed_crops,
                        'filename': crop_filename,
                        'image_path': crop_image_path
                    }
                    page_crops.append(crop_info)
                    
                    # Process regions in this crop
                    if 'regions' in crop_data:
                        for region in crop_data['regions']:
                            if region.get('tag'):
                                # Track unique scopes
                                if isinstance(region['tag'], str):
                                    all_annotations['unique_scopes'].add(region['tag'])
                                
                                # Create a comprehensive annotation entry with all data
                                annotation = {
                                    'text': region.get('text', ''),
                                    'tag': region['tag'],
                                    'bid_item': region['bidItem'],
                                    'reason': region.get('reason', ''),
                                    'auto_tagged': region.get('auto_tagged', False),
                                    'auto_source': region.get('auto_source', ''),
                                    'coordinates': {
                                        'sheet_pts': region.get('sheet_pts', []),
                                        'pts': region.get('pts', []),  # Include relative coordinates
                                        'crop_id': crop_idx,
                                        'crop_box': crop_box
                                    },
                                    'id': region.get('id'),
                                    'combined_text': region.get('combinedText', '')
                                }
                                page_annotations.append(annotation)
                    
                    # Collect keyword mappings
                    if 'keyword_mappings' in crop_data:
                        for mapping in crop_data['keyword_mappings']:
                            # Add page and crop info to the mapping
                            mapping_with_location = mapping.copy()
                            mapping_with_location['page_num'] = page_num
                            mapping_with_location['crop_idx'] = crop_idx
                            mapping_with_location['crop_image_path'] = crop_image_path
                            
                            # Add coordinates if available from crop_box
                            if crop_box:
                                mapping_with_location['coordinates'] = {
                                    'x1': crop_box.get('x1'),
                                    'y1': crop_box.get('y1'),
                                    'x2': crop_box.get('x2'),
                                    'y2': crop_box.get('y2')
                                }
                            
                            # Track unique scopes in keyword mappings
                            if 'scope' in mapping:
                                all_annotations['unique_scopes'].add(mapping['scope'])
                                
                            all_annotations['keyword_mappings'].append(mapping_with_location)
            
            # Add page data if anything exists
            if page_annotations or page_crops:
                all_annotations['pages'][str(page_num)] = page_data
    
    # Convert unique scopes set to list
    all_annotations['unique_scopes'] = list(all_annotations['unique_scopes'])
    
    # Include a version marker for future compatibility
    all_annotations['version'] = '1.1'
    all_annotations['export_date'] = time.strftime('%Y-%m-%d %H:%M:%S')
    
    return all_annotations 