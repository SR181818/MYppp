import os
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename  # Import secure_filename
import fitz  # PyMuPDF for extracting text from PDF
import json

app = Flask(__name__)

UPLOAD_FOLDER = './uploaded_docs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
RESULTS_FILE = 'results.json'

def load_results():
    try:
        with open('results.json', 'r') as file:
            results = json.load(file)
    except FileNotFoundError:
        results = []  # Return empty list if file is not found
    return results
# Storage for comparison results
comparison_results = []

UPLOAD_FOLDER = './uploaded_docs'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    pdf_document = fitz.open(pdf_path)
    text = ""
    
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        text += page.get_text()
    
    pdf_document.close()
    return text

# Function to find requirements in text
def find_requirements_in_text(text):
    requirements = []
    lines = text.splitlines()
    
    for line in lines:
        if len(line.strip()) > 0:
            requirements.append(line.strip())
    return requirements

# Function to match requirements
def match_requirements(text, requirements):
    matched = 0
    for req in requirements:
        if req in text:
            matched += 1
    return matched, len(requirements)

# Function to compare PDFs
def compare_pdfs(pdf1_path, pdf2_folder):
    text_pdf1 = extract_text_from_pdf(pdf1_path)
    requirements = find_requirements_in_text(text_pdf1)
    results = []

    for filename in os.listdir(pdf2_folder):
        if filename.endswith(".pdf"):
            pdf2_path = os.path.join(pdf2_folder, filename)
            text_pdf2 = extract_text_from_pdf(pdf2_path)
            matched, total_requirements = match_requirements(text_pdf2, requirements)
            match_percentage = (matched / total_requirements) * 100 if total_requirements > 0 else 0
            results.append((filename, matched, total_requirements, match_percentage))

    return results

# Function to load results from JSON file
def load_results():
    try:
        with open(RESULTS_FILE, 'r') as file:
            results = json.load(file)
    except FileNotFoundError:
        results = []
    return results

# Function to save results to JSON file
def save_results(new_result):
    results = load_results()
    results.append(new_result)
    with open(RESULTS_FILE, 'w') as file:
        json.dump(results, file, indent=4)


@app.route('/')
def index():
    return render_template('index.html')  # Create an index.html file for your upload form.

@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    if 'pdf' not in request.files:
        return jsonify({"message": "No file part"}), 400

    file = request.files['pdf']

    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400

    if file and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(pdf_path)

        # Now compare the uploaded PDF with the other PDFs in the folder
        results = compare_pdfs(pdf_path, app.config['UPLOAD_FOLDER'])
        
        # Render the results in the results.html template
        return render_template('results.html', results=results)

    else:
        return jsonify({"message": "Invalid file format. Only PDFs are allowed."}), 400

@app.route('/admin')
def admin_dashboard():
    # Load results from the JSON file
    results = load_results()
    return render_template('admin_dashboard.html', results=results)

@app.route('/api/documents', methods=['GET'])
def list_documents():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    pdf_files = [f for f in files if f.endswith('.pdf')]
    return jsonify({"documents": [{"filename": f} for f in pdf_files]})

@app.route('/api/delete/<filename>', methods=['DELETE'])
def delete_document(filename):
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({"message": f"{filename} has been deleted."}), 200
        else:
            return jsonify({"message": "File not found."}), 404
    except Exception as e:
        return jsonify({"message": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "UP"}), 200

if __name__ == '__main__':
    app.run(debug=True)
