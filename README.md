# Route Optimization for Bogotá

> A web-based vehicle routing application that optimizes delivery routes for multiple trucks in Bogotá, Colombia. The system uses geographic clustering and Traveling Salesman Problem (TSP) algorithms to minimize total travel distance.

**Built for:** Logistics company struggling with inefficient delivery routes in Bogotá  
**Build time:** ⏱️ 4 hours  
**Part of:** [thexperiment.dev](https://thexperiment.dev)

---

## 🎯 What It Does

Upload a CSV of delivery addresses in Bogotá. The system geocodes locations, clusters them geographically, and calculates optimal routes for 3-6 trucks. See everything visualized on an interactive map with color-coded routes.

## ⚡ Tech Stack

- **Backend:** Flask, scikit-learn (K-means clustering)
- **Optimization:** Custom TSP solver (exact + heuristic)
- **Geocoding:** OpenStreetMap Nominatim API
- **Frontend:** Bootstrap, Leaflet.js maps

## 🚀 Quick Start

Get the app running in 5 minutes:

### Prerequisites
- Python 3.11+ installed
- `uv` package manager (or use standard `pip`)
- Terminal/command line access


### Create the .env file for the Environment Variables
```env
SECRET_KEY=your-secret-key-here          # This is a random key generated in the terminal with the command: python3 -c "import secrets; print(secrets.token_hex(32))"
FLASK_DEBUG=True
FLASK_HOST=0.0.0.0
FLASK_PORT=8080
```

### Steps

```bash
# 1. Clone & install
git clone https://github.com/irivelez/route_optimization.git
cd route_optimization

# 2. Create and adtivate a virtual environment
uv venv                      # (This creates a `.venv` folder with isolated Python environment)
source .venv/bin/activate    # You should see `(.venv)` at the start of your terminal prompt.

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python app.py

# 5. Open browser
http://localhost:8080
```

**Upload a CSV file or use the local example file (30 addresses).**

**To stop the app:**
Press `Ctrl+C` in the terminal

**To deactivate the virtual environment:**
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

- Automatic address geocoding
- Geographic clustering (K-means)
- TSP optimization per cluster
- Interactive route visualization
- Supports 3-6 trucks
- All routes start/end at central depot

---

## ⚠️ Limitations

- Uses straight-line distances (not road routing)
- Bogotá addresses only
- No capacity constraints yet
- Development server (not production-ready)

---

## 📋 CSV Format Requirements

Your CSV file must contain at minimum:

### Required Columns
- `nombre`: Customer or location name
- `direccion`: Full street address in Bogotá

You can find examples of these csv files in the data folder

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

---

**⚡ Built in 4 hours • Part of [thexperiment.dev](https://thexperiment.dev)**
