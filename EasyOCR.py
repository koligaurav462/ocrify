# -*- coding: utf-8 -*-
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from flask import Flask, request, jsonify
import easyocr
from PIL import Image
import cv2
import numpy as np
from werkzeug.utils import secure_filename
import base64
from io import BytesIO
import sys

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Suppress EasyOCR download progress output
import warnings
warnings.filterwarnings('ignore')

print("Initializing EasyOCR reader... (downloading models on first run)")
print("This may take a few minutes on first startup...")

# Initialize EasyOCR reader (supports multiple languages)
# Download models on first run
try:
    reader = easyocr.Reader(['en'], gpu=True, verbose=False)
except Exception as e:
    print(f"Warning: Could not initialize EasyOCR: {e}")
    reader = None

# HTML Template as a string
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OCR Text Extractor - AI Powered</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f0f23;
            min-height: 100vh;
            padding: 20px;
            color: #fff;
            position: relative;
            overflow-x: hidden;
        }

        /* Animated background */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(circle at 20% 50%, rgba(120, 119, 198, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(138, 43, 226, 0.15) 0%, transparent 50%),
                radial-gradient(circle at 40% 20%, rgba(72, 149, 239, 0.15) 0%, transparent 50%);
            animation: float 20s ease-in-out infinite;
            z-index: 0;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0) scale(1); }
            50% { transform: translateY(-20px) scale(1.05); }
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            position: relative;
            z-index: 1;
        }

        .header {
            text-align: center;
            margin-bottom: 50px;
            animation: fadeInDown 0.8s ease-out;
        }

        @keyframes fadeInDown {
            from {
                opacity: 0;
                transform: translateY(-30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .header h1 {
            font-size: 3.5em;
            margin-bottom: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-weight: 800;
            letter-spacing: -1px;
        }

        .header .subtitle {
            font-size: 1.2em;
            color: #a0a0c0;
            font-weight: 300;
        }

        .header .tagline {
            display: inline-block;
            margin-top: 10px;
            padding: 8px 20px;
            background: rgba(102, 126, 234, 0.2);
            border-radius: 20px;
            font-size: 0.9em;
            color: #8b9cff;
            border: 1px solid rgba(102, 126, 234, 0.3);
        }

        .main-content {
            background: rgba(25, 25, 45, 0.6);
            backdrop-filter: blur(20px);
            border-radius: 30px;
            padding: 50px;
            box-shadow: 0 30px 90px rgba(0, 0, 0, 0.5),
                        0 0 0 1px rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.05);
            animation: fadeInUp 0.8s ease-out 0.2s both;
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .upload-section {
            text-align: center;
            padding: 60px 40px;
            border: 3px dashed rgba(102, 126, 234, 0.4);
            border-radius: 20px;
            background: rgba(102, 126, 234, 0.05);
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }

        .upload-section::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(102, 126, 234, 0.1), transparent);
            transition: left 0.6s;
        }

        .upload-section:hover::before {
            left: 100%;
        }

        .upload-section:hover {
            border-color: #667eea;
            background: rgba(102, 126, 234, 0.1);
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(102, 126, 234, 0.2);
        }

        .upload-section.dragover {
            border-color: #f093fb;
            background: rgba(240, 147, 251, 0.1);
            transform: scale(1.02);
        }

        .upload-icon {
            font-size: 5em;
            margin-bottom: 20px;
            animation: bounce 2s infinite;
        }

        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        .upload-section h2 {
            color: #fff;
            margin-bottom: 10px;
            font-size: 1.8em;
            font-weight: 600;
        }

        .upload-section p {
            color: #a0a0c0;
            margin-bottom: 30px;
            font-size: 1.1em;
        }

        #fileInput {
            display: none;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 16px 40px;
            border-radius: 30px;
            font-size: 1.1em;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
            position: relative;
            overflow: hidden;
        }

        .btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: left 0.5s;
        }

        .btn:hover::before {
            left: 100%;
        }

        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 15px 40px rgba(102, 126, 234, 0.5);
        }

        .btn:active {
            transform: translateY(-1px);
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .results-section {
            display: none;
            margin-top: 40px;
            animation: fadeInUp 0.6s ease-out;
        }

        .results-header {
            color: #fff;
            margin-bottom: 30px;
            font-size: 2em;
            font-weight: 700;
            text-align: center;
        }

        .results-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-top: 20px;
        }

        @media (max-width: 968px) {
            .results-grid {
                grid-template-columns: 1fr;
            }
            .header h1 {
                font-size: 2.5em;
            }
            .main-content {
                padding: 30px 20px;
            }
        }

        .result-card {
            background: rgba(35, 35, 60, 0.6);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 0.3s ease;
        }

        .result-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0, 0, 0, 0.4);
        }

        .result-card h3 {
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 20px;
            font-size: 1.5em;
            font-weight: 700;
        }

        .image-container {
            position: relative;
            border-radius: 15px;
            overflow: hidden;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .image-container:hover {
            transform: scale(1.02);
            box-shadow: 0 15px 40px rgba(102, 126, 234, 0.3);
        }

        .image-preview {
            width: 100%;
            display: block;
            border-radius: 15px;
        }

        .image-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity 0.3s ease;
            border-radius: 15px;
        }

        .image-container:hover .image-overlay {
            opacity: 1;
        }

        .image-overlay span {
            color: white;
            font-size: 1.2em;
            font-weight: 600;
            padding: 10px 20px;
            background: rgba(102, 126, 234, 0.8);
            border-radius: 10px;
        }

        .extracted-text {
            background: rgba(20, 20, 35, 0.8);
            padding: 25px;
            border-radius: 15px;
            border-left: 4px solid #667eea;
            white-space: pre-wrap;
            word-wrap: break-word;
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Monaco', 'Courier New', monospace;
            line-height: 1.8;
            color: #e0e0f0;
            font-size: 0.95em;
        }

        .extracted-text::-webkit-scrollbar {
            width: 8px;
        }

        .extracted-text::-webkit-scrollbar-track {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
        }

        .extracted-text::-webkit-scrollbar-thumb {
            background: #667eea;
            border-radius: 10px;
        }

        .stats {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
        }

        .stat-item {
            background: rgba(102, 126, 234, 0.1);
            padding: 15px;
            border-radius: 12px;
            flex: 1;
            text-align: center;
            border: 1px solid rgba(102, 126, 234, 0.2);
            transition: all 0.3s ease;
        }

        .stat-item:hover {
            background: rgba(102, 126, 234, 0.15);
            transform: translateY(-3px);
        }

        .stat-value {
            font-size: 2em;
            font-weight: 800;
            background: linear-gradient(135deg, #667eea, #f093fb);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .stat-label {
            font-size: 0.9em;
            color: #a0a0c0;
            margin-top: 5px;
        }

        .loading {
            display: none;
            text-align: center;
            padding: 60px;
        }

        .spinner {
            width: 60px;
            height: 60px;
            margin: 0 auto 30px;
            position: relative;
        }

        .spinner::before,
        .spinner::after {
            content: '';
            position: absolute;
            border-radius: 50%;
            animation: pulse 2s ease-in-out infinite;
        }

        .spinner::before {
            width: 60px;
            height: 60px;
            border: 4px solid rgba(102, 126, 234, 0.3);
            animation: spin 1s linear infinite;
        }

        .spinner::after {
            width: 60px;
            height: 60px;
            border: 4px solid transparent;
            border-top-color: #667eea;
            border-right-color: #764ba2;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .loading p {
            color: #a0a0c0;
            font-size: 1.1em;
        }

        .error {
            background: rgba(255, 59, 92, 0.2);
            color: #ff6b9d;
            padding: 20px;
            border-radius: 15px;
            margin-top: 20px;
            display: none;
            border: 1px solid rgba(255, 59, 92, 0.3);
            animation: shake 0.5s;
        }

        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-10px); }
            75% { transform: translateX(10px); }
        }

        .copy-btn {
            background: linear-gradient(135deg, #11998e, #38ef7d);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            margin-top: 15px;
            box-shadow: 0 8px 20px rgba(56, 239, 125, 0.3);
            transition: all 0.3s ease;
        }

        .copy-btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 30px rgba(56, 239, 125, 0.4);
        }

        .copy-btn:active {
            transform: translateY(-1px);
        }

        /* Modal for full image view */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.95);
            animation: fadeIn 0.3s;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .modal-content {
            margin: auto;
            display: block;
            max-width: 90%;
            max-height: 90%;
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            border-radius: 10px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        }

        .close-modal {
            position: absolute;
            top: 30px;
            right: 50px;
            color: #fff;
            font-size: 40px;
            font-weight: bold;
            cursor: pointer;
            z-index: 1001;
            transition: all 0.3s ease;
        }

        .close-modal:hover {
            color: #667eea;
            transform: rotate(90deg);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✨ OCR Text Extractor</h1>
            <p class="subtitle">EasyOCR-Powered Document Text Recognition</p>
            <div class="tagline">🚀 Extract text from any image instantly</div>
        </div>

        <div class="main-content">
            <div class="upload-section" id="uploadSection">
                <div class="upload-icon">📸</div>
                <h2>Upload Your Document</h2>
                <p>Drag and drop an image here or click to browse</p>
                <input type="file" id="fileInput" accept="image/*">
                <button class="btn" onclick="document.getElementById('fileInput').click()">
                    Choose File
                </button>
            </div>

            <div class="loading" id="loading">
                <div class="spinner"></div>
                <p>🔍 Processing image with EasyOCR...</p>
            </div>

            <div class="error" id="error"></div>

            <div class="results-section" id="results">
                <h2 class="results-header">✅ Extraction Results</h2>
                <div class="results-grid">
                    <div class="result-card">
                        <h3>📷 Original Image</h3>
                        <div class="image-container" onclick="openModal()">
                            <img id="previewImage" class="image-preview" alt="Uploaded image">
                            <div class="image-overlay">
                                <span>🔍 Click to view full size</span>
                            </div>
                        </div>
                        <div class="stats">
                            <div class="stat-item">
                                <div class="stat-value" id="detections">0</div>
                                <div class="stat-label">Text Detections</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value" id="charCount">0</div>
                                <div class="stat-label">Characters</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value" id="confidence">0%</div>
                                <div class="stat-label">Avg Confidence</div>
                            </div>
                        </div>
                    </div>
                    <div class="result-card">
                        <h3>📝 Extracted Text</h3>
                        <div class="extracted-text" id="extractedText"></div>
                        <button class="copy-btn" onclick="copyText()">📋 Copy Text</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal for full image view -->
    <div id="imageModal" class="modal" onclick="closeModal()">
        <span class="close-modal">&times;</span>
        <img class="modal-content" id="modalImage">
    </div>

    <script>
        const uploadSection = document.getElementById('uploadSection');
        const fileInput = document.getElementById('fileInput');
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        const error = document.getElementById('error');
        let currentImageData = '';

        uploadSection.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadSection.classList.add('dragover');
        });

        uploadSection.addEventListener('dragleave', () => {
            uploadSection.classList.remove('dragover');
        });

        uploadSection.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadSection.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFile(e.target.files[0]);
            }
        });

        function handleFile(file) {
            if (!file.type.startsWith('image/')) {
                showError('Please upload a valid image file');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            uploadSection.style.display = 'none';
            loading.style.display = 'block';
            results.style.display = 'none';
            error.style.display = 'none';

            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                loading.style.display = 'none';
                
                if (data.success) {
                    displayResults(data);
                } else {
                    showError(data.error || 'An error occurred during processing');
                }
            })
            .catch(err => {
                loading.style.display = 'none';
                showError('Failed to process image: ' + err.message);
            });
        }

        function displayResults(data) {
            currentImageData = 'data:image/jpeg;base64,' + data.image;
            document.getElementById('previewImage').src = currentImageData;
            document.getElementById('extractedText').textContent = data.text || 'No text detected';
            document.getElementById('detections').textContent = data.detections || 0;
            document.getElementById('charCount').textContent = data.char_count || 0;
            document.getElementById('confidence').textContent = (data.confidence || 0) + '%';
            
            results.style.display = 'block';
            uploadSection.style.display = 'block';
        }

        function showError(message) {
            error.textContent = '❌ ' + message;
            error.style.display = 'block';
            uploadSection.style.display = 'block';
        }

        function copyText() {
            const text = document.getElementById('extractedText').textContent;
            navigator.clipboard.writeText(text).then(() => {
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = '✅ Copied!';
                setTimeout(() => {
                    btn.textContent = originalText;
                }, 2000);
            });
        }

        function openModal() {
            const modal = document.getElementById('imageModal');
            const modalImg = document.getElementById('modalImage');
            modal.style.display = 'block';
            modalImg.src = currentImageData;
        }

        function closeModal() {
            document.getElementById('imageModal').style.display = 'none';
        }

        // Close modal with Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeModal();
            }
        });
    </script>
</body>
</html>
"""

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_easyocr(image_path):
    """Extract text from image using EasyOCR"""
    try:
        # Read image
        image = cv2.imread(image_path)
        if image is None:
            return {
                'text': '',
                'error': 'Failed to read image file',
                'success': False
            }
        
        # Run OCR
        results = reader.readtext(image_path)
        
        if not results:
            return {
                'text': '',
                'detections': 0,
                'confidence': 0,
                'char_count': 0,
                'success': True
            }
        
        # Extract text and confidence scores
        extracted_text = ""
        confidences = []
        
        for detection in results:
            text = detection[1]
            confidence = detection[2]
            
            extracted_text += text + "\n"
            confidences.append(confidence * 100)  # Convert to percentage
        
        # Calculate average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        char_count = len(extracted_text.replace('\n', ''))
        
        return {
            'text': extracted_text.strip(),
            'detections': len(results),
            'confidence': round(avg_confidence, 2),
            'char_count': char_count,
            'success': True
        }
    
    except Exception as e:
        return {
            'text': '',
            'error': f'OCR Error: {str(e)}',
            'success': False
        }

@app.route('/')
def index():
    return HTML_TEMPLATE

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        result = extract_text_easyocr(filepath)
        
        with open(filepath, 'rb') as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
        
        os.remove(filepath)
        
        if result['success']:
            return jsonify({
                'text': result['text'],
                'detections': result.get('detections', 0),
                'confidence': result.get('confidence', 0),
                'char_count': result.get('char_count', 0),
                'image': img_base64,
                'success': True
            })
        else:
            return jsonify({'error': result['error'], 'success': False}), 500
    
    return jsonify({'error': 'Invalid file type'}), 400

if __name__ == '__main__':
    print("=" * 50)
    print("OCR Text Extractor Server Starting...")
    print("Using EasyOCR")
    print("=" * 50)
    print("Server running at: http://127.0.0.1:5000")
    print("Or access via: http://localhost:5000")
    print("=" * 50)
    print("Press CTRL+C to stop the server")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=True)