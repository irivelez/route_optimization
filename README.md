# Route Optimization for Bogotá

> **One-liner:** Optimize multi-truck delivery routes in Bogotá using clustering + TSP algorithms
A web-based vehicle routing application that optimizes delivery routes for multiple trucks in Bogotá, Colombia. The system uses geographic clustering and Traveling Salesman Problem (TSP) algorithms to minimize total travel distance.

---

## 🚀 QUICKSTART

Get the app running in 5 minutes:

### Prerequisites
- Python 3.11+ installed
- `uv` package manager (or use standard `pip`)
- Terminal/command line access

### Steps

1. **Open your terminal and navigate to the project directory:**
   ```bash
   cd /Users/irina/Coding/Repositorios/route_opt
   ```

2. **Create a virtual environment:**
   ```bash
   uv venv
   ```
   (This creates a `.venv` folder with isolated Python environment)

3. **Activate the virtual environment:**
   ```bash
   source .venv/bin/activate
   ```
   You should see `(.venv)` at the start of your terminal prompt.

4. **Install dependencies:**
   ```bash
   uv pip install -r requirements.txt
   ```
   This installs Flask, pandas, scikit-learn, and other required packages.

5. **Run the application:**
   ```bash
   python app.py
   ```

   You should see output like:
   ```
   * Running on http://0.0.0.0:8080
   * Running on http://127.0.0.1:8080
   ```

6. **Open your web browser and visit:**
   ```
   http://localhost:8080
   ```

7. **Upload a CSV file or use the local example file (30 addresses).**

8. **To stop the app:**
   Press `Ctrl+C` in the terminal

9. **To deactivate the virtual environment:**
   ```bash
   deactivate
   ```

### Next Time You Run the App
```bash
cd /Users/irina/Coding/Repositorios/route_opt
source .venv/bin/activate
python app.py
```

---

## ✨ Features

### Core Functionality
- **CSV File Upload**: Process address lists with customer names and locations
- **Automatic Geocoding**: Convert Bogotá addresses to GPS coordinates using OpenStreetMap
- **Smart Clustering**: Group addresses geographically using K-means algorithm
- **Route Optimization**: Solve Traveling Salesman Problem for each cluster
  - Exact algorithm for small routes (≤8 stops)
  - Heuristic approach (Nearest Neighbor + 2-opt) for larger routes
- **Interactive Map**: Visualize all routes with color-coded paths
- **Multiple Trucks**: Support for 3-6 trucks with configurable parameters
- **Fixed Depot**: All routes start and end at central depot (Carrera 7 #32-18, Centro)

### Distance & Time Estimates
- Haversine formula for straight-line distances
- Estimated driving times (assumes 30 km/h average city speed)
- 5 minutes per stop for deliveries
- Total route statistics and metrics

---

## 🛠 Technical Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Flask 2.3.3, Python 3.11+ |
| **Clustering** | scikit-learn (K-means) |
| **Optimization** | Custom TSP solver (exact + heuristic) |
| **Geocoding** | OpenStreetMap Nominatim API |
| **Distance Calculation** | Haversine formula |
| **Frontend** | Bootstrap 5, JavaScript |
| **Maps** | Leaflet.js |
| **Data Processing** | pandas, numpy |

---

## 📋 CSV Format Requirements

Your CSV file must contain at minimum:

### Required Columns
- `nombre`: Customer or location name
- `direccion`: Full street address in Bogotá

### Optional Columns
- `localidad`: Neighborhood/locality in Bogotá (helps with geocoding)

### Format
- **Delimiter**: Semicolon (`;`) or comma (`,`)
- **Encoding**: UTF-8
- **Max addresses**: 1000

### Example CSV (semicolon delimiter)
```csv
nombre;direccion;localidad
Cliente A;Carrera 7 #32-16;Centro
Cliente B;Calle 100 #15-20;Usaquén
Cliente C;Carrera 13 #85-40;Chapinero
```

### Example CSV (comma delimiter)
```csv
nombre,direccion,localidad
Cliente A,Carrera 7 #32-16,Centro
Cliente B,Calle 100 #15-20,Usaquén
Cliente C,Carrera 13 #85-40,Chapinero
```

---

## ⚙️ Configuration

### Environment Variables (.env)
```env
SECRET_KEY=your-secret-key-here
FLASK_DEBUG=True
FLASK_HOST=0.0.0.0
FLASK_PORT=8080
```

### Depot Configuration
Located in `app.py` (lines 22-28):
```python
DEPOT_CONFIG = {
    'address': 'Carrera 7 #32-18',
    'localidad': 'Centro',
    'nombre': 'Depot Central',
    'lat': None,  # Auto-geocoded on first run
    'lng': None
}
```

### Truck Specifications
Currently configured in `app.py` but not actively used (geographic clustering only):
```python
TRUCK_SPECS = {
    'small': {'max_weight': 1500, 'max_volume': 10},
    'medium': {'max_weight': 3500, 'max_volume': 20},
    'large': {'max_weight': 7500, 'max_volume': 40}
}
```

---

## 📁 Project Structure

```
route_opt/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── .env                        # Environment configuration
├── .gitignore                 # Git ignore rules
│
├── utils/                      # Utility modules
│   ├── __init__.py
│   ├── common.py              # Shared functions (haversine distance)
│   ├── geocoding.py           # OpenStreetMap geocoding with retry logic
│   ├── clustering.py          # K-means geographic clustering
│   ├── tsp_solver.py          # TSP optimization algorithms
│   └── distance.py            # Distance calculation and route metrics
│
├── templates/                  # HTML templates
│   ├── base.html              # Base template
│   ├── index.html             # Upload and configure page
│   └── results.html           # Results visualization
│
├── static/                     # Static assets
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── upload.js          # File upload handling
│   │   └── map.js             # Leaflet map visualization
│   └── uploads/               # Uploaded CSV files
│
├── data/                       # Sample data files
│   └── Direcciones_30_formatted.csv
│
└── logs/                       # Application logs (auto-generated)
    └── route_opt.log
```

---

## ⚠️ Current Limitations

### Distance Calculation
- ❌ Uses **straight-line (haversine) distances**, not actual road distances
- ❌ Does not account for one-way streets, traffic, or road types
- ✅ Fast and reliable for geographic approximations

### API Limitations
- ⚠️ **Nominatim API** can be slow or timeout for large datasets
- ⚠️ Rate limited (1 request per second)
- ⚠️ Public server shared with other users

### Optimization Constraints
- ❌ **No capacity constraints** (weight/volume not considered in routing)
- ❌ **Single depot only** (all trucks start/end at same location)
- ❌ **Geographic clustering only** (doesn't optimize for cost, time, or other factors)
- ❌ Routes optimized within clusters but clusters themselves may not be optimal

### Application Infrastructure
- ⚠️ **Development server only** (not production-ready)
- ❌ No user authentication or multi-user support
- ❌ Session-based storage (data lost when server restarts)
- ❌ No database persistence
- ⚠️ Debug mode enabled (security risk if exposed publicly)

### Data Constraints
- ⚠️ Maximum 1000 addresses per optimization
- ⚠️ Bogotá-only (coordinates validated within city bounds)
- ⚠️ UTF-8 encoding required

---

## 🔒 Security Notes

**For Development Only:**
- Debug mode is enabled (`FLASK_DEBUG=True`)
- Server is accessible from network (`host='0.0.0.0'`)
- No authentication required
- Secret key should be changed for production

**Before Production Deployment:**
- Disable debug mode
- Use production WSGI server (Gunicorn, uWSGI)
- Add authentication/authorization
- Use HTTPS
- Implement database storage
- Set up proper logging
- Add rate limiting

---

## 🔧 Troubleshooting

### "Connection refused" error
- Make sure the app is running (`python app.py`)
- Check that port 8080 is not in use by another application

### Geocoding timeouts
- Normal for some addresses when Nominatim API is slow
- App will fallback to locality centers or Bogotá center
- Consider implementing OSRM or self-hosted geocoding for production

### "Module not found" errors
- Activate virtual environment: `source .venv/bin/activate`
- Reinstall dependencies: `uv pip install -r requirements.txt`

### CSV upload fails
- Check file encoding is UTF-8
- Verify required columns exist: `nombre`, `direccion`
- Check file size is under 16MB
- Ensure addresses are in Bogotá

---

## 📈 Future Improvements

### High Priority
- **OSRM Integration**: Real road distances and driving times
- **Capacity Constraints**: Respect truck weight/volume limits
- **Production Deployment**: Proper WSGI server, database, authentication

### Medium Priority
- **Multiple Depots**: Support for multiple distribution centers
- **Time Windows**: Delivery time constraints
- **Cost Optimization**: Factor in fuel costs, driver hours
- **Real-time Tracking**: GPS integration

### Low Priority
- **Mobile App**: Native iOS/Android applications
- **Historical Analysis**: Route performance metrics over time
- **Machine Learning**: Predictive delivery times based on historical data

---

## 📝 License

This project is for educational and demonstration purposes.

---

## 🤝 Contributing

This is a demonstration project. For questions or suggestions, please contact the repository owner.

---

## 📞 Support

For issues or questions about the application:
1. Check the Troubleshooting section above
2. Review application logs in `logs/route_opt.log`
3. Verify your CSV format matches requirements
4. Ensure addresses are within Bogotá city limits
