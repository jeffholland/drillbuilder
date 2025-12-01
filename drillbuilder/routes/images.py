"""
Image upload and management routes.
Handles uploading, processing, and serving images for questions and answer components.
"""

from flask import Blueprint, request, jsonify, send_from_directory, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from PIL import Image
import os
import uuid
from datetime import datetime

bp = Blueprint("images", __name__)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg'}
MAX_SIZE = (200, 200)  # Max dimensions for resized images
UPLOAD_FOLDER = 'instance/uploads'

def allowed_file(filename):
    """Check if file has allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_image(file_path):
    """
    Process uploaded image: resize, compress, optimize.
    Returns the processed file path.
    """
    try:
        with Image.open(file_path) as img:
            # Convert to RGB if necessary (handles PNG with alpha, etc.)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Create white background
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize maintaining aspect ratio
            img.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
            
            # Save with optimization and compression
            img.save(file_path, 'JPEG', quality=85, optimize=True)
            
        return True
    except Exception as e:
        print(f"Error processing image: {e}")
        return False

@bp.post("/upload")
@jwt_required()
def upload_image():
    """
    Upload and process an image.
    Returns the image URL on success.
    """
    if 'image' not in request.files:
        return jsonify({"msg": "No image file provided"}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({"msg": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"msg": "Only .jpg and .jpeg files are allowed"}), 400
    
    try:
        # Generate unique filename
        original_filename = secure_filename(file.filename)
        extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{extension}"
        
        # Ensure upload directory exists
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Save file
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # Process image (resize, compress)
        if not process_image(file_path):
            os.remove(file_path)
            return jsonify({"msg": "Error processing image"}), 500
        
        # Return URL
        image_url = f"/images/serve/{unique_filename}"
        
        return jsonify({
            "image_url": image_url,
            "filename": unique_filename,
            "msg": "Image uploaded successfully"
        }), 201
        
    except Exception as e:
        return jsonify({"msg": f"Upload failed: {str(e)}"}), 500

@bp.get("/serve/<filename>")
def serve_image(filename):
    """Serve uploaded images."""
    # Security: ensure filename is safe
    safe_filename = secure_filename(filename)
    
    # Get absolute path to upload folder
    upload_path = os.path.join(current_app.root_path, '..', UPLOAD_FOLDER)
    upload_path = os.path.abspath(upload_path)
    
    # Check if file exists
    file_path = os.path.join(upload_path, safe_filename)
    if not os.path.exists(file_path):
        return jsonify({"msg": "Image not found"}), 404
    
    return send_from_directory(upload_path, safe_filename)

@bp.delete("/delete/<filename>")
@jwt_required()
def delete_image(filename):
    """
    Delete an uploaded image.
    Only allows deletion by authenticated users.
    """
    safe_filename = secure_filename(filename)
    file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
    
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({"msg": "Image deleted successfully"}), 200
        else:
            return jsonify({"msg": "Image not found"}), 404
    except Exception as e:
        return jsonify({"msg": f"Deletion failed: {str(e)}"}), 500

@bp.get("/info/<filename>")
def image_info(filename):
    """Get information about an uploaded image."""
    safe_filename = secure_filename(filename)
    file_path = os.path.join(UPLOAD_FOLDER, safe_filename)
    
    if not os.path.exists(file_path):
        return jsonify({"msg": "Image not found"}), 404
    
    try:
        with Image.open(file_path) as img:
            info = {
                "filename": safe_filename,
                "size": os.path.getsize(file_path),
                "dimensions": img.size,
                "format": img.format,
                "mode": img.mode
            }
        return jsonify(info), 200
    except Exception as e:
        return jsonify({"msg": f"Error reading image: {str(e)}"}), 500
