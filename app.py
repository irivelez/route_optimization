from flask import Flask, render_template, request, jsonify, session, redirect
import pandas as pd
import numpy as np
import os
import uuid
import json
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from utils.geocoding import geocode_addresses
from utils.clustering import cluster_addresses_geographically
from utils.tsp_solver import optimize_routes as tsp_optimize_routes
from utils.distance import calculate_route_distances

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24).hex()

# Configure logging
if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/route_opt.log', maxBytes=10240000, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Route Optimization startup')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Depot configuration
DEPOT_CONFIG = {
    'address': 'Carrera 7 #32-18',
    'localidad': 'Centro',
    'nombre': 'Depot Central',
    'lat': None,  # Will be geocoded
    'lng': None   # Will be geocoded
}

# Truck specifications
TRUCK_SPECS = {
    'small': {'max_weight': 1500, 'max_volume': 10, 'name': 'Camión Pequeño'},
    'medium': {'max_weight': 3500, 'max_volume': 20, 'name': 'Camión Mediano'},
    'large': {'max_weight': 7500, 'max_volume': 40, 'name': 'Camión Grande'}
}

def convert_numpy_types(obj):
    """Convert numpy types to native Python types for JSON serialization"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'

def validate_num_trucks(num_trucks):
    """Validate number of trucks parameter"""
    try:
        num = int(num_trucks)
        if num < 1 or num > 20:
            return False, "Number of trucks must be between 1 and 20"
        return True, num
    except (ValueError, TypeError):
        return False, "Invalid number of trucks"

def validate_csv_content(df):
    """Validate CSV content and structure"""
    if df.empty:
        return False, "CSV file is empty"

    if len(df) > 1000:
        return False, "CSV file cannot exceed 1000 addresses"

    required_cols = ['nombre', 'direccion']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return False, f"Missing required columns: {', '.join(missing_cols)}"

    # Check for empty required fields
    if df['nombre'].isna().any() or df['direccion'].isna().any():
        return False, "CSV contains empty 'nombre' or 'direccion' fields"

    # Validate data types
    if not all(isinstance(val, str) or pd.isna(val) for val in df['nombre']):
        return False, "'nombre' column must contain text values"

    if not all(isinstance(val, str) or pd.isna(val) for val in df['direccion']):
        return False, "'direccion' column must contain text values"

    return True, df

def process_rtf_to_csv(content):
    """Extract CSV data from RTF content"""
    lines = content.split('\n')
    csv_lines = []
    
    for line in lines:
        # Remove RTF formatting and extract CSV data
        if ',' in line and 'Cliente' in line:
            # Clean RTF escape sequences
            clean_line = line.replace('\\', '')
            # Extract the CSV part after the formatting
            if 'Cliente' in clean_line:
                start_idx = clean_line.find('Cliente')
                csv_part = clean_line[start_idx:]
                # Remove trailing RTF artifacts
                csv_part = csv_part.split('}')[0]
                csv_lines.append(csv_part)
    
    return '\n'.join(['nombre,direccion,localidad,peso,volumen'] + csv_lines)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' in request.files:
            file = request.files['file']
            if not file or not file.filename:
                app.logger.warning('Upload attempt with no file selected')
                return jsonify({'error': 'No se seleccionó ningún archivo'})

            if not allowed_file(file.filename):
                app.logger.warning(f'Invalid file type uploaded: {file.filename}')
                return jsonify({'error': 'Solo se permiten archivos CSV'})

            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            try:
                file.save(filepath)
                app.logger.info(f'File saved: {filepath}')
            except Exception as e:
                app.logger.error(f'Error saving file: {str(e)}')
                return jsonify({'error': f'Error guardando archivo: {str(e)}'})

            # Read and process the file
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                app.logger.error(f'Encoding error reading file: {filepath}')
                return jsonify({'error': 'Error de codificación. El archivo debe estar en UTF-8'})
            except Exception as e:
                app.logger.error(f'Error reading file: {str(e)}')
                return jsonify({'error': f'Error leyendo archivo: {str(e)}'})

            # Check if it's RTF format and convert
            if content.startswith('{\\rtf'):
                try:
                    csv_content = process_rtf_to_csv(content)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(csv_content)
                    app.logger.info(f'Converted RTF to CSV: {filepath}')
                except Exception as e:
                    app.logger.error(f'Error converting RTF: {str(e)}')
                    return jsonify({'error': f'Error convirtiendo RTF: {str(e)}'})

            session['csv_file'] = filepath
            app.logger.info(f'CSV file uploaded successfully: {filepath}')
            return jsonify({'success': True, 'message': 'Archivo subido exitosamente'})
        
        # Check for local files (prefer the real address files)
        local_files = [
            ('data/Direcciones_30_formatted.csv', 'Direcciones_30_formatted.csv (30 direcciones reales de Bogotá - formato comma)'),
            ('data/Direcciones_30.csv', 'Direcciones_30.csv (30 direcciones reales de Bogotá - formato semicolon)'),
            ('data/Direcciones_processed.csv', 'Direcciones_processed.csv (100 direcciones de ejemplo)'),
            ('data/Direcciones.csv', 'Direcciones.csv (original RTF)')
        ]
        
        for file_path, description in local_files:
            if os.path.exists(file_path):
                if file_path.endswith('.csv') and not file_path.endswith('Direcciones.csv'):
                    # Direct CSV file
                    session['csv_file'] = file_path
                    return jsonify({'success': True, 'message': f'Usando archivo local: {description}'})
                else:
                    # RTF file - process it
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    if content.startswith('{\\rtf'):
                        csv_content = process_rtf_to_csv(content)
                        processed_path = 'data/Direcciones_processed.csv'
                        with open(processed_path, 'w', encoding='utf-8') as f:
                            f.write(csv_content)
                        session['csv_file'] = processed_path
                    else:
                        session['csv_file'] = file_path
                    
                    return jsonify({'success': True, 'message': f'Usando archivo local: {description}'})
        
        return jsonify({'error': 'No se encontró archivo válido'})
    
    except Exception as e:
        return jsonify({'error': f'Error procesando archivo: {str(e)}'})

def geocode_depot():
    """Geocode the depot address if not already done"""
    if DEPOT_CONFIG['lat'] is None or DEPOT_CONFIG['lng'] is None:
        from utils.geocoding import geocode_addresses
        import pandas as pd
        
        depot_df = pd.DataFrame([{
            'nombre': DEPOT_CONFIG['nombre'],
            'direccion': DEPOT_CONFIG['address'],
            'localidad': DEPOT_CONFIG['localidad'],
            'peso': 0,
            'volumen': 0
        }])
        
        geocoded_depot = geocode_addresses(depot_df)
        DEPOT_CONFIG['lat'] = float(geocoded_depot.iloc[0]['lat'])
        DEPOT_CONFIG['lng'] = float(geocoded_depot.iloc[0]['lng'])
        
        print(f"Depot geocoded: {DEPOT_CONFIG['lat']}, {DEPOT_CONFIG['lng']}")

@app.route('/optimize', methods=['POST'])
def optimize_routes_endpoint():
    try:
        if 'csv_file' not in session:
            return jsonify({'error': 'No hay archivo CSV cargado'})

        # Get and validate number of trucks
        num_trucks_input = request.json.get('num_trucks', 3) if request.is_json else 3
        is_valid, result = validate_num_trucks(num_trucks_input)
        if not is_valid:
            return jsonify({'error': result})
        num_trucks = result

        # Ensure depot is geocoded
        geocode_depot()
        
        # Read CSV file - try to detect delimiter
        try:
            # First try semicolon delimiter
            df = pd.read_csv(session['csv_file'], delimiter=';')
            if len(df.columns) < 2:
                # If that didn't work, try comma delimiter
                df = pd.read_csv(session['csv_file'], delimiter=',')
        except Exception as e:
            # Fallback to comma delimiter
            try:
                df = pd.read_csv(session['csv_file'], delimiter=',')
            except Exception as e:
                return jsonify({'error': f'Error leyendo archivo CSV: {str(e)}'})

        # Validate CSV content
        is_valid, result = validate_csv_content(df)
        if not is_valid:
            return jsonify({'error': result})
        df = result
        
        # Step 1: Geocode addresses with Bogotá constraints
        app.logger.info(f'Starting geocoding for {len(df)} addresses')
        print("Geocodificando direcciones dentro de los límites de Bogotá...")
        try:
            geocoded_df = geocode_addresses(df)
            app.logger.info(f'Geocoding completed for {len(geocoded_df)} addresses')
            print("✓ Todas las direcciones geocodificadas dentro de Bogotá")
        except Exception as e:
            app.logger.error(f'Geocoding failed: {str(e)}')
            return jsonify({'error': f'Error geocodificando direcciones: {str(e)}'})

        # Step 2: Cluster addresses geographically (no capacity constraints)
        app.logger.info(f'Starting clustering into {num_trucks} groups')
        print("Agrupando direcciones geográficamente...")
        try:
            clusters = cluster_addresses_geographically(geocoded_df, num_trucks=num_trucks, depot=DEPOT_CONFIG)
            app.logger.info(f'Clustering completed with {len(clusters)} clusters')
        except Exception as e:
            app.logger.error(f'Clustering failed: {str(e)}')
            return jsonify({'error': f'Error agrupando direcciones: {str(e)}'})

        # Step 3: Optimize routes within each cluster with depot
        app.logger.info('Starting route optimization')
        print("Optimizando rutas...")
        try:
            optimized_routes = tsp_optimize_routes(clusters, depot=DEPOT_CONFIG)
            app.logger.info(f'Route optimization completed for {len(optimized_routes)} routes')
        except Exception as e:
            app.logger.error(f'Route optimization failed: {str(e)}')
            return jsonify({'error': f'Error optimizando rutas: {str(e)}'})

        # Step 4: Calculate distances
        app.logger.info('Calculating route distances')
        print("Calculando distancias...")
        try:
            route_data = calculate_route_distances(optimized_routes)
            app.logger.info('Distance calculation completed')
        except Exception as e:
            app.logger.error(f'Distance calculation failed: {str(e)}')
            return jsonify({'error': f'Error calculando distancias: {str(e)}'})
        
        # Convert numpy types for JSON serialization
        route_data = convert_numpy_types(route_data)
        
        # Store results in session
        session['route_results'] = route_data
        app.logger.info('Optimization completed successfully')

        return jsonify({
            'success': True,
            'routes': route_data,
            'depot': DEPOT_CONFIG,
            'message': 'Optimización completada exitosamente'
        })

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        app.logger.error(f'Optimization error: {str(e)}\n{error_trace}')
        traceback.print_exc()
        return jsonify({'error': f'Error en optimización: {str(e)}'})

@app.route('/results')
def results():
    if 'route_results' not in session:
        return redirect('/')
    
    return render_template('results.html', 
                         routes=session['route_results'],
                         truck_specs=TRUCK_SPECS)

@app.route('/redirect')
def redirect_to_index():
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)