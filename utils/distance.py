import math
import numpy as np
from utils.common import haversine_distance

def calculate_route_distances(route_data):
    """
    Calculate distances for all routes and add distance information
    
    Args:
        route_data: List of route dictionaries from TSP optimization
    
    Returns:
        Updated route data with distance calculations
    """
    
    updated_routes = []
    
    for route in route_data:
        stops = route['stops']
        
        if len(stops) <= 1:
            route['total_distance'] = 0
            route['segment_distances'] = []
            updated_routes.append(route)
            continue
        
        # Calculate distances between consecutive stops
        segment_distances = []
        total_distance = 0
        
        for i in range(len(stops)):
            j = (i + 1) % len(stops)  # Return to depot
            
            distance = haversine_distance(
                stops[i]['lat'], stops[i]['lng'],
                stops[j]['lat'], stops[j]['lng']
            )
            
            segment_distances.append({
                'from_stop': i,
                'to_stop': j,
                'from_name': stops[i]['nombre'],
                'to_name': stops[j]['nombre'],
                'distance_km': round(distance, 2)
            })
            
            total_distance += distance
        
        # Update route with distance information
        route['total_distance'] = round(total_distance, 2)
        route['segment_distances'] = segment_distances
        route['avg_distance_per_stop'] = round(total_distance / len(stops), 2) if len(stops) > 0 else 0
        
        # Add time estimates (assuming 30 km/h average speed in city + 5 min per stop)
        estimated_driving_time = total_distance / 30  # hours
        estimated_stop_time = len(stops) * (5/60)  # 5 minutes per stop in hours
        route['estimated_time_hours'] = round(estimated_driving_time + estimated_stop_time, 1)
        
        updated_routes.append(route)
    
    return updated_routes


def manhattan_distance(lat1, lon1, lat2, lon2):
    """
    Calculate Manhattan distance (city block distance) approximation
    Useful for urban routing where streets form a grid
    """
    # Convert to approximate meters per degree at Bogotá latitude
    lat_to_km = 111.32  # km per degree latitude
    lng_to_km = 111.32 * math.cos(math.radians(4.6))  # Bogotá latitude ≈ 4.6°N
    
    lat_diff = abs(lat2 - lat1) * lat_to_km
    lng_diff = abs(lon2 - lon1) * lng_to_km
    
    return lat_diff + lng_diff

def calculate_distance_matrix(coordinates):
    """
    Calculate distance matrix for a set of coordinates
    
    Args:
        coordinates: List of [lat, lng] pairs
    
    Returns:
        2D numpy array with distances between all pairs
    """
    n = len(coordinates)
    dist_matrix = np.zeros((n, n))
    
    for i in range(n):
        for j in range(n):
            if i != j:
                dist_matrix[i][j] = haversine_distance(
                    coordinates[i][0], coordinates[i][1],
                    coordinates[j][0], coordinates[j][1]
                )
    
    return dist_matrix

def calculate_route_efficiency(route_data):
    """
    Calculate efficiency metrics for routes
    
    Args:
        route_data: Route dictionary with stops and distances
    
    Returns:
        Dictionary with efficiency metrics
    """
    
    stops = route_data['stops']
    total_distance = route_data['total_distance']
    
    if len(stops) <= 1:
        return {
            'efficiency_score': 0,
            'avg_distance_per_stop': 0,
            'detour_factor': 1.0,
            'compactness_score': 0
        }
    
    # Calculate direct distances from depot to each stop
    depot = stops[0]  # Assuming first stop is depot
    direct_distances = []
    
    for stop in stops[1:]:  # Skip depot
        direct_dist = haversine_distance(
            depot['lat'], depot['lng'],
            stop['lat'], stop['lng']
        )
        direct_distances.append(direct_dist)
    
    # Calculate metrics
    total_direct_distance = sum(direct_distances) * 2  # Round trip
    detour_factor = total_distance / total_direct_distance if total_direct_distance > 0 else 1.0
    
    avg_distance_per_stop = total_distance / len(stops) if len(stops) > 0 else 0
    
    # Compactness: how close stops are to each other
    if len(stops) > 2:
        stop_coordinates = [[s['lat'], s['lng']] for s in stops]
        center_lat = sum(coord[0] for coord in stop_coordinates) / len(stop_coordinates)
        center_lng = sum(coord[1] for coord in stop_coordinates) / len(stop_coordinates)
        
        distances_from_center = [
            haversine_distance(center_lat, center_lng, coord[0], coord[1])
            for coord in stop_coordinates
        ]
        
        compactness_score = 1 / (1 + np.std(distances_from_center))
    else:
        compactness_score = 1.0
    
    # Overall efficiency score (lower detour factor and higher compactness = better)
    efficiency_score = compactness_score / detour_factor
    
    return {
        'efficiency_score': round(efficiency_score, 3),
        'avg_distance_per_stop': round(avg_distance_per_stop, 2),
        'detour_factor': round(detour_factor, 2),
        'compactness_score': round(compactness_score, 3),
        'total_direct_distance': round(total_direct_distance, 2)
    }

def calculate_fuel_consumption(route_data, fuel_efficiency_km_per_liter=8):
    """
    Estimate fuel consumption for a route
    
    Args:
        route_data: Route dictionary
        fuel_efficiency_km_per_liter: Truck fuel efficiency
    
    Returns:
        Dictionary with fuel consumption estimates
    """
    
    total_distance = route_data['total_distance']
    
    # Basic fuel consumption
    fuel_consumption_liters = total_distance / fuel_efficiency_km_per_liter
    
    # Add extra consumption for stops (idling, acceleration)
    num_stops = len(route_data['stops'])
    extra_fuel_per_stop = 0.2  # liters per stop
    total_fuel = fuel_consumption_liters + (num_stops * extra_fuel_per_stop)
    
    # Estimate cost (approximate Colombian diesel price)
    cost_per_liter = 3000  # COP (Colombian Pesos)
    total_cost = total_fuel * cost_per_liter
    
    return {
        'fuel_liters': round(total_fuel, 1),
        'fuel_cost_cop': round(total_cost, 0),
        'fuel_efficiency_used': fuel_efficiency_km_per_liter,
        'km_per_liter_actual': round(total_distance / total_fuel, 1) if total_fuel > 0 else 0
    }