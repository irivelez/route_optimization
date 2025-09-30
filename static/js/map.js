// Map functionality with Leaflet.js
document.addEventListener('DOMContentLoaded', function() {
    // Route colors
    const routeColors = ['#FF6B6B', '#4ECDC4', '#45B7D1'];
    
    // Initialize map centered on Bogotá
    const map = L.map('map').setView([4.60971, -74.08175], 11);
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    // Store route layers for toggling
    const routeLayers = [];
    const markerLayers = [];
    
    // Process and display routes
    if (typeof routesData !== 'undefined' && routesData.length > 0) {
        displayRoutes(routesData);
        setupRouteControls();
        
        // Add depot if available
        if (routesData[0] && routesData[0].depot) {
            addDepotToMap(routesData[0].depot);
        }
    }
    
    function displayRoutes(routes) {
        const allPoints = [];
        
        routes.forEach((route, routeIndex) => {
            const color = routeColors[routeIndex] || '#333333';
            const routeGroup = L.layerGroup();
            const markerGroup = L.layerGroup();
            
            // Create route polyline
            const routeCoords = route.stops.map(stop => [stop.lat, stop.lng]);
            allPoints.push(...routeCoords);
            
            const polyline = L.polyline(routeCoords, {
                color: color,
                weight: 4,
                opacity: 0.8
            }).addTo(routeGroup);
            
            // Add markers for each stop
            route.stops.forEach((stop, stopIndex) => {
                // Skip depot markers here (they will be handled separately)
                if (stop.is_depot) {
                    return;
                }
                
                const marker = L.circleMarker([stop.lat, stop.lng], {
                    radius: 8,
                    fillColor: color,
                    color: '#ffffff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8
                });
                
                // Create popup content
                const popupContent = `
                    <div style="min-width: 200px;">
                        <h6 style="color: ${color}; margin-bottom: 10px;">
                            <i class="fas fa-truck"></i> Camión ${routeIndex + 1} - Parada ${stopIndex}
                        </h6>
                        <p style="margin-bottom: 5px;"><strong>${stop.nombre}</strong></p>
                        <p style="margin-bottom: 5px; font-size: 0.9em; color: #666;">
                            ${stop.direccion}
                        </p>
                        <hr style="margin: 8px 0;">
                        <div style="font-size: 0.85em; text-align: center;">
                            <span style="color: #28a745;"><i class="fas fa-map-marker-alt"></i> Ubicación optimizada</span>
                        </div>
                    </div>
                `;
                
                marker.bindPopup(popupContent);
                marker.addTo(markerGroup);
            });
            
            // Note: Depot marker will be added separately to avoid duplication
            
            // Add layers to map
            routeGroup.addTo(map);
            markerGroup.addTo(map);
            
            // Store layers for control
            routeLayers.push(routeGroup);
            markerLayers.push(markerGroup);
        });
        
        // Fit map to show all routes
        if (allPoints.length > 0) {
            const group = new L.featureGroup(routeLayers);
            map.fitBounds(group.getBounds().pad(0.1));
        }
        
        // Add legend
        addLegend(routes);
    }
    
    function setupRouteControls() {
        // Toggle stops visibility
        document.querySelectorAll('.toggle-stops').forEach(button => {
            button.addEventListener('click', function() {
                const routeIndex = this.dataset.route;
                const stopsList = document.getElementById(`stops-${routeIndex}`);
                
                if (stopsList.style.display === 'none') {
                    stopsList.style.display = 'block';
                    this.innerHTML = '<i class="fas fa-eye-slash"></i> Ocultar Paradas';
                } else {
                    stopsList.style.display = 'none';
                    this.innerHTML = '<i class="fas fa-list"></i> Ver Paradas';
                }
            });
        });
        
        // Route summary hover effects
        document.querySelectorAll('.route-summary').forEach((summary, index) => {
            summary.addEventListener('mouseenter', function() {
                // Highlight corresponding route on map
                if (routeLayers[index]) {
                    routeLayers[index].eachLayer(layer => {
                        if (layer instanceof L.Polyline) {
                            layer.setStyle({ weight: 6 });
                        }
                    });
                }
            });
            
            summary.addEventListener('mouseleave', function() {
                // Reset route style
                if (routeLayers[index]) {
                    routeLayers[index].eachLayer(layer => {
                        if (layer instanceof L.Polyline) {
                            layer.setStyle({ weight: 4 });
                        }
                    });
                }
            });
        });
    }
    
    function addLegend(routes) {
        const legend = L.control({ position: 'bottomright' });
        
        legend.onAdd = function(map) {
            const div = L.DomUtil.create('div', 'legend');
            div.style.backgroundColor = 'white';
            div.style.padding = '10px';
            div.style.borderRadius = '5px';
            div.style.boxShadow = '0 2px 6px rgba(0,0,0,0.3)';
            div.style.fontSize = '14px';
            
            let legendContent = '<h6 style="margin: 0 0 10px 0;"><i class="fas fa-map-signs"></i> Rutas</h6>';
            
            routes.forEach((route, index) => {
                const color = routeColors[index];
                legendContent += `
                    <div style="margin-bottom: 5px; display: flex; align-items: center;">
                        <div style="width: 20px; height: 3px; background-color: ${color}; margin-right: 8px;"></div>
                        <span style="font-size: 13px;">
                            Camión ${index + 1} (${route.stops.length} paradas)
                        </span>
                    </div>
                `;
            });
            
            div.innerHTML = legendContent;
            return div;
        };
        
        legend.addTo(map);
    }
    
    function addDepotToMap(depot) {
        if (!depot || !depot.lat || !depot.lng) return;
        
        // Create depot marker with distinct icon
        const depotMarker = L.marker([depot.lat, depot.lng], {
            icon: L.divIcon({
                className: 'depot-marker',
                html: `<div style="background-color: #2C3E50; color: white; border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 4px solid white; box-shadow: 0 3px 10px rgba(0,0,0,0.4); font-size: 18px;">
                    <i class="fas fa-warehouse"></i>
                </div>`,
                iconSize: [40, 40],
                iconAnchor: [20, 20]
            }),
            zIndexOffset: 1000  // Ensure depot appears above other markers
        });
        
        depotMarker.bindPopup(`
            <div style="text-align: center; min-width: 180px;">
                <h5 style="color: #2C3E50; margin-bottom: 10px;">
                    <i class="fas fa-warehouse"></i> Depot Central
                </h5>
                <p style="margin-bottom: 5px;"><strong>${depot.address}</strong></p>
                <p style="margin-bottom: 8px; font-size: 0.9em; color: #666;">
                    ${depot.localidad}
                </p>
                <div style="background-color: #f8f9fa; padding: 8px; border-radius: 5px; margin-top: 10px;">
                    <small style="color: #666;">
                        <i class="fas fa-info-circle"></i>
                        Punto de partida y llegada para todos los camiones
                    </small>
                </div>
            </div>
        `);
        
        depotMarker.addTo(map);
        
        // Store depot marker for future reference
        window.depotMarker = depotMarker;
    }
    
    // Add scale control
    L.control.scale({
        metric: true,
        imperial: false,
        position: 'bottomleft'
    }).addTo(map);
    
    // Add fullscreen control (if available)
    if (typeof L.control.fullscreen !== 'undefined') {
        L.control.fullscreen({
            position: 'topleft'
        }).addTo(map);
    }
});