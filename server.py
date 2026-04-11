#!/usr/bin/env python3
"""
Simple Flask server for CV project with save endpoint
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__, static_folder='.')
CORS(app)  # Enable CORS for all routes

# Project root directory
PROJECT_ROOT = Path(__file__).parent

@app.route('/')
def index():
    """Serve the main page"""
    return send_from_directory('.', 'launch-profile-studio.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('.', path)

@app.route('/api/save-cv', methods=['POST'])
def save_cv():
    """Save CV data to review/cv.resume.json"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Paths
        review_dir = PROJECT_ROOT / 'review'
        cv_file = review_dir / 'cv.resume.json'
        backup_dir = review_dir / 'backups'
        
        # Create directories if they don't exist
        review_dir.mkdir(exist_ok=True)
        backup_dir.mkdir(exist_ok=True)
        
        # Create backup of existing file
        if cv_file.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f'cv.resume.{timestamp}.json'
            with open(cv_file, 'r', encoding='utf-8') as f:
                backup_data = f.read()
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(backup_data)
            print(f"✓ Backup created: {backup_file}")
        
        # Save new data
        with open(cv_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ CV saved to: {cv_file}")
        
        return jsonify({
            'success': True,
            'message': 'CV saved successfully',
            'file': str(cv_file.relative_to(PROJECT_ROOT))
        })
        
    except Exception as e:
        print(f"✗ Error saving CV: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def status():
    """Check server status"""
    return jsonify({
        'status': 'running',
        'project_root': str(PROJECT_ROOT)
    })

if __name__ == '__main__':
    print("=" * 60)
    print("CV Project Server")
    print("=" * 60)
    print(f"Project root: {PROJECT_ROOT}")
    print(f"\nAccess points:")
    print(f"  • Main page:       http://localhost:8000/")
    print(f"  • Profile Studio:  http://localhost:8000/launch-profile-studio.html")
    print(f"  • Your CV:         http://localhost:8000/docs/VitaliyHlynianyiZhuk2025.html")
    print(f"\nAPI Endpoints:")
    print(f"  • POST /api/save-cv   - Save CV to project")
    print(f"  • GET  /api/status    - Server status")
    print("=" * 60)
    print("\nServer starting on http://localhost:8000")
    print("Press Ctrl+C to stop\n")
    
    app.run(host='0.0.0.0', port=8000, debug=True)
