import requests
import pandas as pd
import time
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)

def geocode_addresses(df):
    """
    Geocode addresses using OpenStreetMap Nominatim API with strict Bogotá constraints
    
    Args:
        df: DataFrame with columns 'nombre', 'direccion', 'localidad', 'peso', 'volumen'
    
    Returns:
        DataFrame with added 'lat' and 'lng' columns
    """
    
    # Strict Bogotá bounds (more precise)
    BOGOTA_BOUNDS = {
        'lat_min': 4.47,  # Southern boundary
        'lat_max': 4.83,  # Northern boundary 
        'lng_min': -74.22, # Western boundary
        'lng_max': -74.00  # Eastern boundary
    }
    
    # Bogotá locality centers for fallback geocoding
    BOGOTA_LOCALITIES = {
        'Chapinero': (4.6097, -74.0817),
        'Usaquén': (4.6954, -74.0308), 
        'Teusaquillo': (4.6392, -74.0931),
        'Barrios Unidos': (4.6609, -74.0687),
        'Engativá': (4.6868, -74.1439),
        'Suba': (4.7370, -74.0937),
        'Fontibón': (4.6735, -74.1365),
        'La Candelaria': (4.5980, -74.0760),
        'Santa Fé': (4.6097, -74.0654),
        'Antonio Nariño': (4.5924, -74.0989),
        'Puente Aranda': (4.6209, -74.1221),
        'Pontevedra': (4.6392, -74.0931),
        'Centro': (4.5980, -74.0760)
    }
    
    def is_in_bogota(lat, lng):
        """Check if coordinates are within Bogotá bounds"""
        return (BOGOTA_BOUNDS['lat_min'] <= lat <= BOGOTA_BOUNDS['lat_max'] and
                BOGOTA_BOUNDS['lng_min'] <= lng <= BOGOTA_BOUNDS['lng_max'])
    
    def geocode_address(address, locality="Bogotá"):
        """Geocode a single address with multiple fallback strategies"""
        import random
        
        # Strategy 1: Try specific address with locality
        coords = try_geocode_with_nominatim(f"{address}, {locality}, Bogotá, Colombia")
        if coords and is_in_bogota(coords[0], coords[1]):
            return coords
            
        # Strategy 2: Try address with just Bogotá
        coords = try_geocode_with_nominatim(f"{address}, Bogotá, Colombia")
        if coords and is_in_bogota(coords[0], coords[1]):
            return coords
            
        # Strategy 3: Try simplified address (remove # symbols and details)
        simplified_address = simplify_address(address)
        coords = try_geocode_with_nominatim(f"{simplified_address}, Bogotá, Colombia")
        if coords and is_in_bogota(coords[0], coords[1]):
            return coords
        
        # Strategy 4: Use locality center with random offset
        if locality in BOGOTA_LOCALITIES:
            base_lat, base_lng = BOGOTA_LOCALITIES[locality]
            lat = base_lat + random.uniform(-0.02, 0.02)
            lng = base_lng + random.uniform(-0.02, 0.02)
            print(f"  → Usando centro de {locality} para: {address}")
            return lat, lng
        
        # Strategy 5: Default to Bogotá center with random offset
        lat = 4.60971 + random.uniform(-0.05, 0.05)
        lng = -74.08175 + random.uniform(-0.05, 0.05)
        print(f"  → Usando centro de Bogotá para: {address}")
        return lat, lng
    
    def try_geocode_with_nominatim(query, max_retries=1):
        """Try geocoding with Nominatim API with exponential backoff retry"""
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': query,
            'format': 'json',
            'limit': 3,  # Get multiple results to choose best
            'countrycodes': 'co',
            'addressdetails': 1,
            'bounded': 1,
            'viewbox': f"{BOGOTA_BOUNDS['lng_min']},{BOGOTA_BOUNDS['lat_max']},{BOGOTA_BOUNDS['lng_max']},{BOGOTA_BOUNDS['lat_min']}"
        }

        headers = {
            'User-Agent': 'RouteOptimizationApp/1.0 (contact@example.com)'
        }

        for attempt in range(max_retries):
            try:
                response = requests.get(url, params=params, headers=headers, timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    # Try each result and return the first one within Bogotá bounds
                    for result in data:
                        lat = float(result['lat'])
                        lng = float(result['lon'])
                        if is_in_bogota(lat, lng):
                            return lat, lng
                    # If we got a response but no valid results, don't retry
                    return None
                elif response.status_code == 429:  # Rate limited
                    wait_time = (2 ** attempt) + (time.time() % 1)  # Exponential backoff with jitter
                    logger.warning(f"Rate limited by Nominatim API. Waiting {wait_time:.2f}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                elif response.status_code >= 500:  # Server error
                    wait_time = (2 ** attempt) + (time.time() % 1)
                    logger.warning(f"Nominatim server error {response.status_code}. Waiting {wait_time:.2f}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                else:
                    # Other error status codes - don't retry
                    logger.error(f"Nominatim API returned status {response.status_code} for query: {query}")
                    return None

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                # Don't retry on timeout/connection errors - fail fast
                logger.warning(f"Connection issue with Nominatim for '{query}': {type(e).__name__}")
                return None
            except Exception as e:
                logger.error(f"Nominatim error for '{query}': {str(e)}")
                return None

        logger.error(f"All {max_retries} retry attempts failed for query: {query}")
        return None
    
    def simplify_address(address):
        """Simplify address by removing # symbols and extra details"""
        # Remove # symbol and everything after it that might be apartment/floor details
        simplified = address.split('#')[0].strip()
        # Remove extra details in parentheses
        simplified = simplified.split('(')[0].strip()
        return simplified
    
    # Create a copy of the dataframe
    result_df = df.copy()
    
    # Add coordinate columns
    result_df['lat'] = 0.0
    result_df['lng'] = 0.0
    
    print(f"Geocodificando {len(result_df)} direcciones...")
    
    for index, row in result_df.iterrows():
        print(f"Procesando {index + 1}/{len(result_df)}: {row['direccion']}")
        
        # Use default Bogotá locality since localidad column may not exist
        localidad = row.get('localidad', 'Bogotá')
        lat, lng = geocode_address(row['direccion'], localidad)
        result_df.at[index, 'lat'] = lat
        result_df.at[index, 'lng'] = lng
        
        # Rate limiting - be respectful to Nominatim
        if index < len(result_df) - 1:  # Don't sleep after last request
            time.sleep(1)  # 1 second between requests
    
    print("Geocodificación completada!")
    
    # Final validation to ensure all coordinates are within Bogotá
    result_df = validate_coordinates(result_df)
    
    print(f"Todas las {len(result_df)} direcciones están ahora dentro de los límites de Bogotá")
    return result_df

def validate_coordinates(df):
    """
    Validate that coordinates are within strict bounds for Bogotá
    """
    # Use the same strict bounds as in geocoding
    bogota_bounds = {
        'lat_min': 4.47,
        'lat_max': 4.83,
        'lng_min': -74.22,
        'lng_max': -74.00
    }
    
    invalid_coords = df[
        (df['lat'] < bogota_bounds['lat_min']) |
        (df['lat'] > bogota_bounds['lat_max']) |
        (df['lng'] < bogota_bounds['lng_min']) |
        (df['lng'] > bogota_bounds['lng_max'])
    ]
    
    if len(invalid_coords) > 0:
        print(f"Warning: {len(invalid_coords)} coordinates are outside strict Bogotá bounds")
        print("Moving them to valid Bogotá locations...")
        
        # Fix invalid coordinates to appropriate Bogotá localities
        for index in invalid_coords.index:
            import random
            locality = df.at[index, 'localidad'] if 'localidad' in df.columns else 'Centro'
            
            # Use locality centers if available
            locality_centers = {
                'Chapinero': (4.6097, -74.0817),
                'Usaquén': (4.6954, -74.0308), 
                'Teusaquillo': (4.6392, -74.0931),
                'Barrios Unidos': (4.6609, -74.0687),
                'Engativá': (4.6868, -74.1439),
                'Suba': (4.7370, -74.0937),
                'Fontibón': (4.6735, -74.1365),
                'La Candelaria': (4.5980, -74.0760),
                'Santa Fé': (4.6097, -74.0654),
                'Antonio Nariño': (4.5924, -74.0989),
                'Puente Aranda': (4.6209, -74.1221),
                'Pontevedra': (4.6392, -74.0931),
                'Centro': (4.5980, -74.0760)
            }
            
            if locality in locality_centers:
                base_lat, base_lng = locality_centers[locality]
                df.at[index, 'lat'] = base_lat + random.uniform(-0.01, 0.01)
                df.at[index, 'lng'] = base_lng + random.uniform(-0.01, 0.01)
                print(f"  Moved {df.at[index, 'nombre']} to {locality} center")
            else:
                # Default to Bogotá center
                df.at[index, 'lat'] = 4.60971 + random.uniform(-0.02, 0.02)
                df.at[index, 'lng'] = -74.08175 + random.uniform(-0.02, 0.02)
                print(f"  Moved {df.at[index, 'nombre']} to Bogotá center")
    
    return df