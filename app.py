from flask import Flask, jsonify, request, send_file, Response, stream_with_context
from flask_cors import CORS
import os
import sys
import json
from qbyte_utils import QbyteDataProcessor
import subprocess
from datetime import datetime

# Add the Qbyte directory to the path so we can import functions
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Qbyte'))

# Import our headless QByte implementation
from qbyte_headless import run_qbyte, QByteHeadless

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Root directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QBYTE_DIR = os.path.join(ROOT_DIR, 'Qbyte')

# Initialize data processor
data_processor = QbyteDataProcessor(QBYTE_DIR)

@app.route('/')
def index():
    """API root endpoint with documentation"""
    return jsonify({
        'name': 'Qbyte API',
        'version': '1.0.0',
        'description': 'API for accessing Qbyte data and functionality',
        'endpoints': {
            '/api/files': 'Get list of available Qbyte data files',
            '/api/file/<filename>': 'Get data from a specific file',
            '/api/stats/<filename>': 'Get statistical analysis for a specific file',
            '/api/visualization/<filename>': 'Get visualization for a specific file',
            '/api/shapes': 'Get list of available shapes',
            '/api/shape/<shape_name>': 'Get data for a specific shape',
            '/api/run_birthday_party': 'Execute headless QByte with BirthdayParty parameters',
            '/api/run_qbyte_headless': 'Execute headless QByte with custom parameters'
        }
    })

@app.route('/api/files')
def get_files():
    """Get list of available Qbyte data files"""
    files = []
    for file in os.listdir(QBYTE_DIR):
        if file.startswith('QB_') and file.endswith('.txt'):
            files.append({
                'name': file,
                'path': os.path.join(QBYTE_DIR, file),
                'size': os.path.getsize(os.path.join(QBYTE_DIR, file)),
                'created': os.path.getctime(os.path.join(QBYTE_DIR, file))
            })
    return jsonify(files)

@app.route('/api/file/<filename>')
def get_file_data(filename):
    """Get data from a specific file"""
    file_path = os.path.join(QBYTE_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        # Parse file using the data processor
        params, lines = data_processor.parse_file_header(file_path)
        qbyte_data, _ = data_processor.extract_qbyte_data(lines)
        
        return jsonify({
            'filename': filename,
            'parameters': params,
            'data_sample': qbyte_data[:100],  # Return only first 100 entries
            'total_lines': len(lines)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats/<filename>')
def get_file_stats(filename):
    """Get statistical analysis for a specific file"""
    file_path = os.path.join(QBYTE_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        # Parse file and calculate statistics using the data processor
        params, lines = data_processor.parse_file_header(file_path)
        stats = data_processor.calculate_statistics(params)
        events = data_processor.count_events(lines)
        
        return jsonify({
            'filename': filename,
            'parameters': params,
            'statistics': stats,
            'events': events
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/visualization/<filename>')
def get_visualization(filename):
    """Generate and return a visualization for a specific file"""
    file_path = os.path.join(QBYTE_DIR, filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        # Generate visualization using the data processor
        img_io = data_processor.generate_visualization(file_path)
        
        if img_io:
            return send_file(img_io, mimetype='image/png')
        else:
            return jsonify({'error': 'No valid data found in file'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/shapes')
def get_shapes():
    """Get list of available shapes"""
    shapes = ['hypercube', 'sphere', 'pyramid', 'AEM', 'quad']
    shape_data = []
    
    for shape in shapes:
        sim_file = f'sim_{shape}.txt'
        file_path = os.path.join(QBYTE_DIR, sim_file)
        if os.path.exists(file_path):
            shape_data.append({
                'name': shape,
                'file': sim_file,
                'size': os.path.getsize(file_path),
                'path': file_path
            })
    
    return jsonify(shape_data)

@app.route('/api/shape/<shape_name>')
def get_shape_data(shape_name):
    """Get data for a specific shape"""
    shape_data = data_processor.get_shape_data(shape_name)
    
    if shape_data:
        return jsonify(shape_data)
    else:
        return jsonify({'error': 'Shape data not found'}), 404

@app.route('/api/hypercube')
def get_hypercube():
    """Get hypercube data"""
    hypercube_data = data_processor.get_hypercube_data()
    
    if hypercube_data:
        return jsonify(hypercube_data)
    else:
        return jsonify({'error': 'Hypercube data not found'}), 404

@app.route('/api/run_birthday_party', methods=['GET'])
def run_birthday_party():
    """Execute 'python QByte.py static BirthdayParty' and stream the output in chunks"""
    continuous = request.args.get('continuous', 'false').lower() == 'true'
    
    def generate():
        try:
            # Use our headless implementation instead of the original QByte.py
            print(f"Starting headless QByte run at {datetime.now()}")
            
            if continuous:
                # Create QByte instance
                qbyte = QByteHeadless('static', 'BirthdayParty')
                
                # Send initial message
                yield "data: Starting continuous QByte data generation...\n\n"
                
                # Generate data continuously
                for iteration_data in qbyte.generate_continuous_data():
                    # Stream each iteration as JSON
                    yield f"data: {json.dumps(iteration_data)}\n\n"
                    
                # This point is never reached in continuous mode unless an exception occurs
                
            else:
                # Fixed number of iterations
                iterations = int(request.args.get('iterations', 60))
                yield "data: Starting QByte data generation...\n\n"
                
                # Generate data in chunks and stream it
                qbyte = run_qbyte('static', 'BirthdayParty', iterations)
                
                # Stream the results as JSON
                yield f"data: {json.dumps(qbyte)}\n\n"
                
                # Signal the end of the stream
                yield "data: [END]\n\n"
                
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
            yield "data: [END]\n\n"
    
    # Return a streaming response
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream'
    )

@app.route('/api/run_qbyte_headless', methods=['GET'])
def run_qbyte_headless():
    """Execute headless QByte with custom parameters and stream the output"""
    mode = request.args.get('mode', 'static')
    remarks = request.args.get('remarks', 'API')
    continuous = request.args.get('continuous', 'false').lower() == 'true'
    iterations = int(request.args.get('iterations', 60))
    
    def generate():
        try:
            # Use our headless implementation
            print(f"Starting headless QByte run with mode={mode}, remarks={remarks}")
            
            if continuous:
                # Create QByte instance
                qbyte = QByteHeadless(mode, remarks)
                
                # Send initial message
                yield f"data: Starting continuous QByte data generation with mode={mode}, remarks={remarks}...\n\n"
                
                # Generate data continuously
                for iteration_data in qbyte.generate_continuous_data():
                    # Stream each iteration as JSON
                    yield f"data: {json.dumps(iteration_data)}\n\n"
                    
                # This point is never reached in continuous mode unless an exception occurs
                
            else:
                # Fixed number of iterations
                yield f"data: Starting QByte data generation with mode={mode}, remarks={remarks}, iterations={iterations}...\n\n"
                
                # Generate data
                qbyte = run_qbyte(mode, remarks, iterations)
                
                # Stream the results as JSON
                yield f"data: {json.dumps(qbyte)}\n\n"
                
                # Signal the end of the stream
                yield "data: [END]\n\n"
                
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
            yield "data: [END]\n\n"
    
    # Return a streaming response
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream'
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
