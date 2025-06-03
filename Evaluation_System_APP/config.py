import os
from flask import Flask

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "scopebuilder_secret_key")

# Paths configuration
APP_ROOT = app.root_path
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'uploads')
THUMBNAILS_FOLDER = os.path.join(APP_ROOT, 'thumbnails')
ANNOTATIONS_FOLDER = os.path.join(APP_ROOT, 'annotated_data')
PROJECTS_FOLDER = os.path.join(APP_ROOT, 'projects')
USERS_FOLDER = os.path.join(APP_ROOT, 'users')

# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMBNAILS_FOLDER, exist_ok=True)
os.makedirs(ANNOTATIONS_FOLDER, exist_ok=True)
os.makedirs(PROJECTS_FOLDER, exist_ok=True)
os.makedirs(USERS_FOLDER, exist_ok=True)

# Azure configuration
AZURE_ENDPOINT = os.getenv("AZURE_VISION_ENDPOINT", "https://scopebuilder.cognitiveservices.azure.com")
AZURE_KEY = os.getenv("AZURE_VISION_KEY", "75gzAOgClEIGv8CxaYZcre8X04QxJZGE256MK4y7dMaL1sfLtnHdJQQJ99BEACYeBjFXJ3w3AAAFACOGeQxC")

# YOLO configuration
YOLO_WEIGHTS = os.getenv("YOLO_WEIGHTS", os.path.join(APP_ROOT, 'weights', 'best.pt'))

# PDF processing settings
PDF_DPI = 100  # Reduced from 150 to lower memory usage
METADATA_DPI = 72  # Lower DPI just for counting pages
THUMBNAIL_DPI = 72  # Low DPI for thumbnails

# Scopes list
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