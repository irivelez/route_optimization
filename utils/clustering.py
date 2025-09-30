import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from itertools import combinations
from utils.common import haversine_distance

def cluster_addresses_geographically(df, num_trucks=3, depot=None):
    """
    Cluster addresses based purely on geographic proximity (no capacity constraints)
    
    Args:
        df: DataFrame with geocoded addresses
        num_trucks: Number of trucks (clusters)
        depot: Dictionary with depot information including lat/lng
    
    Returns:
        List of DataFrames, one per truck route
    """
    
    print(f"Clustering {len(df)} addresses into {num_trucks} geographic groups...")
    
    # If we have very few addresses, distribute them evenly
    if len(df) <= num_trucks:
        clusters = []
        for i in range(num_trucks):
            if i < len(df):
                cluster = df.iloc[[i]].copy()
                cluster['cluster'] = i
                cluster['truck_type'] = 'standard'
                cluster['truck_size'] = 'standard'
                clusters.append(cluster)
            else:
                # Create empty cluster if more trucks than addresses
                empty_cluster = df.iloc[:0].copy()
                empty_cluster['cluster'] = i
                empty_cluster['truck_type'] = 'standard' 
                empty_cluster['truck_size'] = 'standard'
                clusters.append(empty_cluster)
        return clusters
    
    # Use pure geographic K-means clustering
    coordinates = df[['lat', 'lng']].values
    
    # Apply depot weighting if available
    if depot and 'lat' in depot and 'lng' in depot:
        coordinates_weighted = apply_depot_weighting(coordinates, depot, 0.2)
    else:
        coordinates_weighted = coordinates
    
    # Perform K-means clustering
    best_clusters = None
    best_score = float('inf')
    
    # Try multiple random initializations
    for attempt in range(10):
        try:
            kmeans = KMeans(n_clusters=num_trucks, random_state=attempt, n_init=10)
            labels = kmeans.fit_predict(coordinates_weighted)
            
            # Create clusters
            clusters = []
            for i in range(num_trucks):
                cluster_mask = labels == i
                if cluster_mask.any():
                    cluster = df[cluster_mask].copy()
                    cluster['cluster'] = i
                    cluster['truck_type'] = 'standard'
                    cluster['truck_size'] = 'standard'
                    clusters.append(cluster)
            
            # Ensure we have exactly num_trucks clusters
            while len(clusters) < num_trucks:
                # Split the largest cluster
                largest_idx = max(range(len(clusters)), key=lambda i: len(clusters[i]))
                largest_cluster = clusters[largest_idx]
                
                if len(largest_cluster) > 1:
                    mid = len(largest_cluster) // 2
                    cluster1 = largest_cluster.iloc[:mid].copy()
                    cluster2 = largest_cluster.iloc[mid:].copy()
                    cluster1['cluster'] = largest_idx
                    cluster2['cluster'] = len(clusters)
                    clusters[largest_idx] = cluster1
                    clusters.append(cluster2)
                else:
                    # Create empty cluster
                    empty_cluster = df.iloc[:0].copy()
                    empty_cluster['cluster'] = len(clusters)
                    empty_cluster['truck_type'] = 'standard'
                    empty_cluster['truck_size'] = 'standard'
                    clusters.append(empty_cluster)
            
            # Calculate geographic distribution score
            score = calculate_geographic_score(clusters, depot)
            
            if score < best_score:
                best_score = score
                best_clusters = clusters
                
        except Exception as e:
            print(f"Clustering attempt {attempt} failed: {e}")
            continue
    
    if best_clusters is None:
        # Fallback: simple distribution
        print("Using fallback simple distribution")
        best_clusters = simple_geographic_clustering(df, num_trucks)
    
    print(f"Geographic clustering completed:")
    for i, cluster in enumerate(best_clusters):
        print(f"  Truck {i+1}: {len(cluster)} stops")
    
    return best_clusters

def calculate_geographic_score(clusters, depot):
    """
    Calculate score based on geographic compactness and depot proximity
    Lower score is better
    """
    total_score = 0
    
    for cluster in clusters:
        if len(cluster) == 0:
            continue
            
        # Calculate cluster compactness (spread of points)
        coords = cluster[['lat', 'lng']].values
        if len(coords) > 1:
            center_lat = coords[:, 0].mean()
            center_lng = coords[:, 1].mean()
            
            # Calculate average distance from cluster center
            distances = []
            for lat, lng in coords:
                dist = haversine_distance(center_lat, center_lng, lat, lng)
                distances.append(dist)
            
            avg_spread = np.mean(distances)
            total_score += avg_spread
        
        # Add depot proximity factor
        if depot and 'lat' in depot and 'lng' in depot and len(cluster) > 0:
            depot_distances = []
            for _, row in cluster.iterrows():
                dist = haversine_distance(depot['lat'], depot['lng'], row['lat'], row['lng'])
                depot_distances.append(dist)
            
            avg_depot_distance = np.mean(depot_distances)
            total_score += avg_depot_distance * 0.3  # Weight depot proximity
    
    return total_score

def simple_geographic_clustering(df, num_trucks):
    """
    Simple fallback clustering - just distribute addresses evenly
    """
    clusters = []
    cluster_size = len(df) // num_trucks
    
    for i in range(num_trucks):
        start_idx = i * cluster_size
        if i == num_trucks - 1:  # Last cluster gets remaining addresses
            cluster = df.iloc[start_idx:].copy()
        else:
            end_idx = (i + 1) * cluster_size
            cluster = df.iloc[start_idx:end_idx].copy()
        
        cluster['cluster'] = i
        cluster['truck_type'] = 'standard'
        cluster['truck_size'] = 'standard'
        clusters.append(cluster)
    
    return clusters

def cluster_addresses_with_capacity(df, truck_specs, num_trucks=3, depot=None):
    """
    Cluster addresses considering truck capacity constraints and depot proximity
    
    Args:
        df: DataFrame with geocoded addresses
        truck_specs: Dictionary with truck specifications
        num_trucks: Number of trucks (clusters)
        depot: Dictionary with depot information including lat/lng
    
    Returns:
        List of DataFrames, one per truck route
    """
    
    def calculate_cluster_load(cluster_df):
        """Calculate total weight and volume for a cluster"""
        return {
            'weight': cluster_df['peso'].sum(),
            'volume': cluster_df['volumen'].sum()
        }
    
    def find_suitable_truck(load):
        """Find the smallest truck that can handle the load"""
        for truck_type in ['small', 'medium', 'large']:
            specs = truck_specs[truck_type]
            if load['weight'] <= specs['max_weight'] and load['volume'] <= specs['max_volume']:
                return truck_type, specs
        
        # If no truck can handle it, use largest and flag as overloaded
        return 'large', truck_specs['large']
    
    def balance_clusters(clusters, truck_specs):
        """Balance clusters to better utilize truck capacities"""
        balanced_clusters = []
        truck_assignments = []
        
        for i, cluster in enumerate(clusters):
            load = calculate_cluster_load(cluster)
            truck_type, specs = find_suitable_truck(load)
            
            cluster_data = cluster.copy()
            cluster_data['cluster'] = i
            cluster_data['truck_type'] = truck_type
            cluster_data['truck_size'] = truck_type
            
            balanced_clusters.append(cluster_data)
            truck_assignments.append({
                'cluster': i,
                'truck_type': truck_type,
                'load': load,
                'capacity': specs
            })
        
        return balanced_clusters, truck_assignments
    
    # Prepare data for clustering
    coordinates = df[['lat', 'lng']].values
    
    # If we have very few addresses, just create simple clusters
    if len(df) <= num_trucks:
        clusters = []
        for i in range(min(len(df), num_trucks)):
            if i < len(df):
                cluster = df.iloc[[i]].copy()
                clusters.append(cluster)
        
        # Fill remaining clusters with copies if needed
        while len(clusters) < num_trucks:
            clusters.append(df.iloc[[0]].copy())
    else:
        # Use capacity-aware clustering approach with depot consideration
        clusters = capacity_aware_clustering(df, truck_specs, num_trucks, depot)
    
    # Balance and assign trucks
    balanced_clusters, truck_assignments = balance_clusters(clusters, truck_specs)
    
    print(f"Clustering completado:")
    for assignment in truck_assignments:
        print(f"  Cluster {assignment['cluster']}: {assignment['truck_type']} truck")
        print(f"    Carga: {assignment['load']['weight']:.1f}kg / {assignment['load']['volume']:.1f}m³")
        print(f"    Capacidad: {assignment['capacity']['max_weight']}kg / {assignment['capacity']['max_volume']}m³")
    
    return balanced_clusters

def capacity_aware_clustering(df, truck_specs, num_trucks, depot=None):
    """
    Perform clustering with capacity awareness and depot proximity consideration
    """
    # Start with geographical K-means, considering depot if available
    coordinates = df[['lat', 'lng']].values
    
    # If depot is available, include it in the clustering considerations
    if depot and 'lat' in depot and 'lng' in depot:
        # Add depot to coordinates for better cluster initialization
        depot_coord = np.array([[depot['lat'], depot['lng']]])
        extended_coords = np.vstack([depot_coord, coordinates])
        
        # Use depot-aware initialization
        depot_distance_weight = 0.3  # Weight for depot proximity
        coordinates_weighted = apply_depot_weighting(coordinates, depot, depot_distance_weight)
    else:
        extended_coords = coordinates
        coordinates_weighted = coordinates
    
    # Try multiple clustering attempts and pick the best one
    best_clusters = None
    best_score = float('inf')
    
    for attempt in range(10):  # Try 10 different random initializations
        try:
            kmeans = KMeans(n_clusters=num_trucks, random_state=attempt, n_init=10)
            labels = kmeans.fit_predict(coordinates_weighted)
            
            # Create initial clusters
            clusters = []
            for i in range(num_trucks):
                cluster_mask = labels == i
                if cluster_mask.any():
                    cluster = df[cluster_mask].copy()
                    clusters.append(cluster)
            
            # Ensure we have exactly num_trucks clusters
            while len(clusters) < num_trucks:
                # Split the largest cluster
                largest_idx = max(range(len(clusters)), key=lambda i: len(clusters[i]))
                largest_cluster = clusters[largest_idx]
                
                if len(largest_cluster) > 1:
                    mid = len(largest_cluster) // 2
                    clusters[largest_idx] = largest_cluster.iloc[:mid].copy()
                    clusters.append(largest_cluster.iloc[mid:].copy())
                else:
                    # If can't split, duplicate the cluster
                    clusters.append(largest_cluster.copy())
            
            # Calculate capacity violations and depot proximity
            score = calculate_capacity_score(clusters, truck_specs, depot)
            
            if score < best_score:
                best_score = score
                best_clusters = clusters
                
        except Exception as e:
            print(f"Clustering attempt {attempt} failed: {e}")
            continue
    
    # If all attempts failed, create simple clusters
    if best_clusters is None:
        print("Using fallback clustering method")
        best_clusters = simple_clustering(df, num_trucks)
    
    # Apply capacity balancing
    best_clusters = balance_capacity_violations(best_clusters, truck_specs)
    
    return best_clusters

def apply_depot_weighting(coordinates, depot, weight):
    """
    Apply weighting to coordinates based on distance from depot
    """
    if not depot or 'lat' not in depot or 'lng' not in depot:
        return coordinates
    
    # Calculate distances from depot
    depot_lat, depot_lng = depot['lat'], depot['lng']
    weighted_coords = coordinates.copy()
    
    for i, (lat, lng) in enumerate(coordinates):
        # Calculate distance from depot
        distance = haversine_distance(depot_lat, depot_lng, lat, lng)
        
        # Apply inverse distance weighting (closer points get more weight towards depot)
        # Adjust coordinates slightly towards depot based on distance
        if distance > 0:
            factor = weight / (1 + distance)  # Closer = higher factor
            weighted_coords[i][0] += (depot_lat - lat) * factor
            weighted_coords[i][1] += (depot_lng - lng) * factor
    
    return weighted_coords


def calculate_capacity_score(clusters, truck_specs, depot=None):
    """
    Calculate a score based on capacity violations, efficiency, and depot proximity
    Lower score is better
    """
    total_score = 0
    
    for cluster in clusters:
        load = {'weight': cluster['peso'].sum(), 'volume': cluster['volumen'].sum()}
        
        # Find minimum truck size needed
        truck_needed = None
        for truck_type in ['small', 'medium', 'large']:
            specs = truck_specs[truck_type]
            if load['weight'] <= specs['max_weight'] and load['volume'] <= specs['max_volume']:
                truck_needed = truck_type
                break
        
        if truck_needed is None:
            # Massive penalty for overloaded cluster
            total_score += 10000
        else:
            # Small penalty for underutilization
            specs = truck_specs[truck_needed]
            weight_util = load['weight'] / specs['max_weight']
            volume_util = load['volume'] / specs['max_volume']
            utilization = max(weight_util, volume_util)
            
            # Prefer higher utilization but not overloading
            if utilization < 0.3:
                total_score += 100  # Penalty for very low utilization
            elif utilization > 0.9:
                total_score += 10   # Small penalty for very high utilization
        
        # Add depot proximity score if depot is available
        if depot and 'lat' in depot and 'lng' in depot and len(cluster) > 0:
            depot_penalty = calculate_depot_proximity_penalty(cluster, depot)
            total_score += depot_penalty
    
    return total_score

def calculate_depot_proximity_penalty(cluster, depot):
    """
    Calculate penalty based on average distance from depot
    Closer clusters get lower penalty
    """
    if len(cluster) == 0:
        return 0
    
    depot_lat, depot_lng = depot['lat'], depot['lng']
    total_distance = 0
    
    for _, row in cluster.iterrows():
        distance = haversine_distance(depot_lat, depot_lng, row['lat'], row['lng'])
        total_distance += distance
    
    avg_distance = total_distance / len(cluster)
    
    # Penalty increases with distance (scaled down to not overwhelm capacity constraints)
    return avg_distance * 0.5  # Scale factor to balance with capacity penalties

def simple_clustering(df, num_trucks):
    """
    Simple fallback clustering method
    """
    cluster_size = len(df) // num_trucks
    clusters = []
    
    for i in range(num_trucks):
        start_idx = i * cluster_size
        if i == num_trucks - 1:  # Last cluster gets remaining addresses
            cluster = df.iloc[start_idx:].copy()
        else:
            end_idx = (i + 1) * cluster_size
            cluster = df.iloc[start_idx:end_idx].copy()
        
        clusters.append(cluster)
    
    return clusters

def balance_capacity_violations(clusters, truck_specs):
    """
    Attempt to fix capacity violations by moving addresses between clusters
    """
    max_iterations = 50
    iteration = 0
    
    while iteration < max_iterations:
        violations_fixed = False
        
        for i, cluster in enumerate(clusters):
            load = {'weight': cluster['peso'].sum(), 'volume': cluster['volumen'].sum()}
            
            # Check if cluster exceeds any truck capacity
            exceeds_large = (load['weight'] > truck_specs['large']['max_weight'] or 
                           load['volume'] > truck_specs['large']['max_volume'])
            
            if exceeds_large and len(cluster) > 1:
                # Try to move heaviest/largest item to another cluster
                heaviest_idx = cluster['peso'].idxmax()
                largest_vol_idx = cluster['volumen'].idxmax()
                
                # Try both heaviest and largest volume
                for item_idx in [heaviest_idx, largest_vol_idx]:
                    item = cluster.loc[item_idx]
                    
                    # Find a cluster that can accommodate this item
                    for j, other_cluster in enumerate(clusters):
                        if i == j:
                            continue
                        
                        other_load = {
                            'weight': other_cluster['peso'].sum() + item['peso'],
                            'volume': other_cluster['volumen'].sum() + item['volumen']
                        }
                        
                        # Check if other cluster can handle the additional load
                        can_handle = (other_load['weight'] <= truck_specs['large']['max_weight'] and
                                    other_load['volume'] <= truck_specs['large']['max_volume'])
                        
                        if can_handle:
                            # Move the item
                            clusters[i] = cluster.drop(item_idx)
                            clusters[j] = pd.concat([other_cluster, item.to_frame().T], ignore_index=True)
                            violations_fixed = True
                            break
                    
                    if violations_fixed:
                        break
                
                if violations_fixed:
                    break
        
        if not violations_fixed:
            break
        
        iteration += 1
    
    return clusters