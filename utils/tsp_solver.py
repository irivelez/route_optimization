import numpy as np
import pandas as pd
from itertools import permutations
import math
from utils.common import haversine_distance

def optimize_routes(clustered_data, depot=None):
    """
    Optimize routes within each cluster using TSP algorithms with depot as start/end point
    
    Args:
        clustered_data: List of DataFrames, one per cluster
        depot: Dictionary with depot information including lat/lng
    
    Returns:
        List of optimized route data
    """
    
    optimized_routes = []
    route_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA726', '#AB47BC', '#26A69A']  # Extended colors
    
    for i, cluster_df in enumerate(clustered_data):
        print(f"Optimizando ruta {i + 1} con {len(cluster_df)} paradas...")
        
        if len(cluster_df) == 0:
            continue
        
        # Get truck type from cluster
        truck_type = cluster_df.iloc[0].get('truck_type', 'medium')
        truck_size = cluster_df.iloc[0].get('truck_size', 'medium')
        
        # Apply TSP optimization with depot
        optimized_order = solve_tsp_with_depot(cluster_df, depot)
        
        # Reorder the cluster according to optimized route
        optimized_cluster = cluster_df.iloc[optimized_order].copy()
        
        # Add depot as first and last stop
        if depot:
            depot_stop = {
                'nombre': depot['nombre'],
                'direccion': depot['address'],
                'lat': depot['lat'],
                'lng': depot['lng'],
                'is_depot': True
            }
            
            # Convert optimized cluster to list of dictionaries
            stops_list = optimized_cluster.to_dict('records')
            
            # Create route: Depot -> Customer stops -> Depot
            route_stops = [depot_stop] + stops_list + [depot_stop.copy()]
        else:
            route_stops = optimized_cluster.to_dict('records')
        
        # Prepare route data (simplified - no weight/volume)
        route_data = {
            'cluster_id': i,
            'truck_type': 'Camión Estándar',
            'truck_size': 'standard',
            'color': route_colors[i % len(route_colors)],
            'stops': route_stops,
            'total_distance': 0,  # Will be calculated in distance module
            'customer_count': len(optimized_cluster),
            'depot': depot
        }
        
        optimized_routes.append(route_data)
    
    return optimized_routes

def solve_tsp_with_depot(cluster_df, depot):
    """
    Solve TSP for a cluster with depot as fixed start/end point
    
    Args:
        cluster_df: DataFrame with customer coordinates and address data
        depot: Dictionary with depot information
    
    Returns:
        List of indices representing optimized visit order for customers only
    """
    
    n = len(cluster_df)
    
    if n <= 1:
        return list(range(n))
    
    if n == 2:
        return [0, 1]
    
    if not depot or 'lat' not in depot or 'lng' not in depot:
        # Fallback to regular TSP if depot not available
        return solve_tsp(cluster_df)
    
    # Create coordinates array including depot
    customer_coords = cluster_df[['lat', 'lng']].values
    depot_coord = np.array([[depot['lat'], depot['lng']]])
    
    # Depot is at index 0, customers start from index 1
    all_coords = np.vstack([depot_coord, customer_coords])
    
    # For small instances, try exact solution
    if n <= 8:
        return solve_tsp_exact_with_depot(all_coords)
    
    # For larger instances, use heuristics
    return solve_tsp_heuristic_with_depot(all_coords)

def solve_tsp(cluster_df):
    """
    Solve TSP for a cluster using Nearest Neighbor + 2-opt improvement
    
    Args:
        cluster_df: DataFrame with coordinates and address data
    
    Returns:
        List of indices representing optimized visit order
    """
    
    n = len(cluster_df)
    
    if n <= 1:
        return list(range(n))
    
    if n == 2:
        return [0, 1]
    
    # For small instances, try exact solution
    if n <= 8:
        return solve_tsp_exact(cluster_df)
    
    # For larger instances, use heuristics
    return solve_tsp_heuristic(cluster_df)

def solve_tsp_exact_with_depot(all_coords):
    """
    Solve TSP exactly with depot for small instances
    
    Args:
        all_coords: Array with depot at index 0, customers at indices 1+
    
    Returns:
        List of customer indices in optimal order
    """
    n_customers = len(all_coords) - 1  # Exclude depot
    
    if n_customers <= 1:
        return list(range(n_customers))
    
    # Calculate distance matrix
    dist_matrix = calculate_distance_matrix(all_coords)
    
    min_distance = float('inf')
    best_tour = list(range(n_customers))
    
    # Try all permutations of customers (depot is fixed at start/end)
    for perm in permutations(range(1, len(all_coords))):  # Skip depot (index 0)
        # Create tour: depot -> customers -> depot
        tour = [0] + list(perm) + [0]
        distance = calculate_tour_distance(tour, dist_matrix)
        
        if distance < min_distance:
            min_distance = distance
            # Return customer indices only (subtract 1 to get original customer indices)
            best_tour = [i - 1 for i in perm]
    
    return best_tour

def solve_tsp_heuristic_with_depot(all_coords):
    """
    Solve TSP with depot using Nearest Neighbor + 2-opt improvement
    
    Args:
        all_coords: Array with depot at index 0, customers at indices 1+
    
    Returns:
        List of customer indices in optimal order
    """
    # Calculate distance matrix
    dist_matrix = calculate_distance_matrix(all_coords)
    
    # Phase 1: Nearest Neighbor starting from depot
    tour = nearest_neighbor_with_depot(dist_matrix)
    
    # Phase 2: 2-opt improvement
    improved_tour = two_opt_improvement(tour, dist_matrix)
    
    # Return customer indices only (exclude depot and convert to customer indices)
    customer_tour = [i - 1 for i in improved_tour[1:-1]]  # Remove first and last depot, adjust indices
    
    return customer_tour

def nearest_neighbor_with_depot(dist_matrix):
    """
    Nearest Neighbor heuristic starting from depot (index 0)
    """
    n = len(dist_matrix)
    
    if n <= 2:
        return list(range(n))
    
    # Start from depot (index 0)
    tour = [0]
    unvisited = set(range(1, n))  # Exclude depot
    
    current = 0
    
    while unvisited:
        # Find nearest unvisited customer
        nearest_dist = float('inf')
        nearest_city = None
        
        for city in unvisited:
            if dist_matrix[current][city] < nearest_dist:
                nearest_dist = dist_matrix[current][city]
                nearest_city = city
        
        tour.append(nearest_city)
        unvisited.remove(nearest_city)
        current = nearest_city
    
    # Return to depot
    tour.append(0)
    
    return tour

def solve_tsp_exact(cluster_df):
    """
    Solve TSP exactly for small instances (≤ 8 stops)
    """
    n = len(cluster_df)
    coordinates = cluster_df[['lat', 'lng']].values
    
    # Calculate distance matrix
    dist_matrix = calculate_distance_matrix(coordinates)
    
    min_distance = float('inf')
    best_tour = list(range(n))
    
    # Try all permutations starting from point 0
    for perm in permutations(range(1, n)):
        tour = [0] + list(perm)
        distance = calculate_tour_distance(tour, dist_matrix)
        
        if distance < min_distance:
            min_distance = distance
            best_tour = tour
    
    return best_tour

def solve_tsp_heuristic(cluster_df):
    """
    Solve TSP using Nearest Neighbor + 2-opt improvement
    """
    coordinates = cluster_df[['lat', 'lng']].values
    dist_matrix = calculate_distance_matrix(coordinates)
    
    # Phase 1: Nearest Neighbor construction
    tour = nearest_neighbor(dist_matrix)
    
    # Phase 2: 2-opt improvement
    improved_tour = two_opt_improvement(tour, dist_matrix)
    
    return improved_tour

def nearest_neighbor(dist_matrix):
    """
    Nearest Neighbor heuristic for TSP
    """
    n = len(dist_matrix)
    
    if n <= 1:
        return list(range(n))
    
    # Start from depot (index 0)
    tour = [0]
    unvisited = set(range(1, n))
    
    current = 0
    
    while unvisited:
        # Find nearest unvisited city
        nearest_dist = float('inf')
        nearest_city = None
        
        for city in unvisited:
            if dist_matrix[current][city] < nearest_dist:
                nearest_dist = dist_matrix[current][city]
                nearest_city = city
        
        tour.append(nearest_city)
        unvisited.remove(nearest_city)
        current = nearest_city
    
    return tour

def two_opt_improvement(tour, dist_matrix):
    """
    2-opt improvement heuristic
    """
    def calculate_improvement(tour, i, j, dist_matrix):
        """Calculate improvement if we reverse segment between i and j"""
        n = len(tour)
        
        # Current edges
        current_dist = (dist_matrix[tour[i-1]][tour[i]] + 
                       dist_matrix[tour[j]][tour[(j+1) % n]])
        
        # New edges after 2-opt
        new_dist = (dist_matrix[tour[i-1]][tour[j]] + 
                   dist_matrix[tour[i]][tour[(j+1) % n]])
        
        return current_dist - new_dist
    
    n = len(tour)
    if n <= 3:
        return tour
    
    improved = True
    max_iterations = 100
    iteration = 0
    
    while improved and iteration < max_iterations:
        improved = False
        iteration += 1
        
        for i in range(1, n-1):
            for j in range(i+1, n):
                improvement = calculate_improvement(tour, i, j, dist_matrix)
                
                if improvement > 0:
                    # Apply 2-opt swap
                    tour[i:j+1] = reversed(tour[i:j+1])
                    improved = True
                    break
            
            if improved:
                break
    
    return tour

def calculate_distance_matrix(coordinates):
    """
    Calculate distance matrix between all coordinate pairs
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

def calculate_tour_distance(tour, dist_matrix):
    """
    Calculate total distance for a tour
    """
    total_distance = 0
    n = len(tour)
    
    for i in range(n):
        j = (i + 1) % n
        total_distance += dist_matrix[tour[i]][tour[j]]
    
    return total_distance


def get_truck_name(truck_type):
    """
    Get Spanish truck type name
    """
    truck_names = {
        'small': 'Camión Pequeño',
        'medium': 'Camión Mediano',
        'large': 'Camión Grande'
    }
    
    return truck_names.get(truck_type, 'Camión Mediano')