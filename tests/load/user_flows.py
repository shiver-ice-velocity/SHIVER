# File: web/tests/load/user_flows.py
import os
from locust import task, TaskSet
import random
import time

# Define region-specific configurations
REGION_CONFIG = {
    "Greenland": {
        "lat_range": (58.0, 82.0),
        "lon_range": (-89.0, 7.0),
        "epsg": "EPSG:3413",
        "limits": {
            "min_x": -640000, "max_x": 840000,
            "min_y": -3300000, "max_y": -630000
        },
        "tile_sizes": [1048576.0, 524288.0, 262144.0, 131072.0],
        "sources": [
            'PROMICE', 'SHIFT', 'MEaSUREs_monthly', 'MEaSUREs_quarterly', 'MEaSUREs_winter', 
            'MEaSUREs_annual', 'C3S_annual', 'Mouginot_annual', 'ITS_LIVE_annual', 
            'ESA_CCI_winter', 'ESA_CCI_Sentinel-1', 'ESA_CCI_Sentinel-2', 'ESA_CCI_CSK', 
            'ESA_CCI_ERS1-2_Envisat', 'ESA_CCI_ERS2_1995-1996', 'ESA_CCI_PALSAR', 'ESA_CCI_ERS1_1991-1992'
        ]
    },
    "Antarctica": {
        "lat_range": (-57, -82),
        "lon_range": (-178, 178),
        "epsg": "EPSG:3031",
        "limits": {
            "min_x": -2800000.0, "max_x": 2800000.0,
            "min_y": -2450000.0, "max_y": 2450000.0
        },
        "tile_sizes": [2097152.0, 1048576.0, 524288.0, 262144.0],
        "sources": [
            'ENVEO_monthly', 'ITS_LIVE_annual', 'MEaSUREs_annual', 'MEaSUREs_multiyear', 
            'MEaSUREs_ASE', 'SID_annual', 'C3S_annual', 'Joughin_Sentinel-1', 'Joughin_TSX', 
            'Li_Totten', 'ENVEO_Sentinel-1_PIG', 'ENVEO_ERS', 'ENVEO_TSX', 'ENVEO_ALOS', 
            'ENVEO_TSX_Sentinel-1', 'ENVEO_TSX_PALSAR', 'SHIFT'
        ]
    }
}

def generate_dynamic_bbox(limits, tile_sizes):
    """
    Generates a random, valid WMS bounding box to simulate panning and zooming.
    """
    # 1. Pick a random zoom level (tile width/height in meters)
    size = random.choice(tile_sizes)
    
    # 2. Pick a random bottom-left corner (minX, minY)
    # Ensure the tile doesn't spill over the maximum limits
    min_x = random.uniform(limits["min_x"], limits["max_x"] - size)
    min_y = random.uniform(limits["min_y"], limits["max_y"] - size)
    
    # 3. Calculate top-right corner
    max_x = min_x + size
    max_y = min_y + size
    
    # Format exactly as WMS expects: minX,minY,maxX,maxY
    return f"{min_x},{min_y},{max_x},{max_y}"


class StandardUserBehavior(TaskSet):
    """
    Defines the specific actions a standard user performs.
    """
    
    def on_start(self):
        """
        Runs once when a simulated user spawns. 
        Logs the user in and stores the JWT for authenticated endpoints.
        """
        # 1. Assign the user a region profile (~50/50 split)
        self.region_name = random.choice(["Greenland", "Antarctica"])
        self.region_data = REGION_CONFIG[self.region_name]
        
        self.token = None
        login_payload = {"email": "shiver@sheffield.ac.uk", "password": "framtastic26_"}
        
        with self.client.post("/auth/login", json=login_payload, name="/auth/login", catch_response=True) as response:
            if response.status_code == 200:
                self.token = response.json().get("access_token")
                response.success()
            else:
                response.failure(f"Failed to login: {response.text}")
                
        # Set up headers for future authenticated requests
        self.auth_headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(int(os.getenv("WEIGHT_TIMESERIES", 20)))
    def request_timeseries(self):
        """
        Interaction 1: Click map to extract timeseries (MultiRoiRequest)
        """
        lat_min, lat_max = self.region_data["lat_range"]
        lon_min, lon_max = self.region_data["lon_range"]
        
        lat = random.uniform(lat_min, lat_max)
        lon = random.uniform(lon_min, lon_max)
        
        payload = {
            "roi": [[lon, lat]], 
            "buffer": 500,
            "gap_fill": 24,
            "win_raw": 25,
            "win_daily": 25,
            "poly": 2
        }
        
        self.client.post(
            "/api/timeseries/multi/json", 
            json=payload, 
            headers=self.auth_headers, # Optional auth based on your endpoints
            name="1. Timeseries Extraction"
        )

    @task(int(os.getenv("WEIGHT_WMS_BASIC", 10)))
    def request_wms_basic(self):
        """
        Interaction 2a: Basic WMS (Speed, Trend, Count)
        """
        layer = random.choice(["default_speed", "trend", "count"])
        
        # Generate bounding box
        bbox = generate_dynamic_bbox(self.region_data["limits"], self.region_data["tile_sizes"])
        epsg = self.region_data["epsg"]
        t = int(time.time() * 1000)
                
        url = f"/api/wms/{self.region_name}?t={t}&service=WMS&request=GetMap&layers={layer}&styles=&format=image%2Fpng&transparent=true&version=1.1.1&width=256&height=256&srs={epsg}&bbox={bbox}"
        self.client.get(url, name="2a. WMS: Basic Layers")

    @task(int(os.getenv("WEIGHT_WMS_COG", 5)))
    def request_wms_analysis_cog(self):
        """
        Interaction 2b: Analysis WMS (Pre-computed COG Average)
        """
        # Generate bounding box
        bbox = generate_dynamic_bbox(self.region_data["limits"], self.region_data["tile_sizes"])
        epsg = self.region_data["epsg"]
        t = int(time.time() * 1000)
        source = random.choice(self.region_data["sources"])
        
        url = f"/api/analysis/wms/{self.region_name}?variable=speed&source={source}&vmin=-500&vmax=3000&t={t}&epoch=average&service=WMS&request=GetMap&layers=analysis_layer&styles=&format=image%2Fpng&transparent=true&version=1.1.1&width=256&height=256&srs={epsg}&bbox={bbox}"
        self.client.get(url, name="2b. WMS: Analysis COG (Average)")

    @task(int(os.getenv("WEIGHT_WMS_ZARR", 4)))
    def request_wms_analysis_zarr(self):
        """
        Interaction 2c: Analysis WMS (Single Zarr Time-slice)
        """
        # Generate bounding box
        bbox = generate_dynamic_bbox(self.region_data["limits"], self.region_data["tile_sizes"])
        epsg = self.region_data["epsg"]
        t = int(time.time() * 1000)
        source = random.choice(self.region_data["sources"])
        epoch = random.choice([2464, 2500, 2600]) # Example epochs
        
        url = f"/api/analysis/wms/{self.region_name}?variable=speed&source={source}&vmin=-500&vmax=3000&t={t}&epoch={epoch}&service=WMS&request=GetMap&layers=analysis_layer&styles=&format=image%2Fpng&transparent=true&version=1.1.1&width=256&height=256&srs={epsg}&bbox={bbox}"
        self.client.get(url, name="2c. WMS: Analysis Zarr (Single Epoch)")

    @task(int(os.getenv("WEIGHT_WMS_DIFF", 2)))
    def request_wms_analysis_differencing(self):
        """
        Interaction 2d: Analysis WMS (On-the-fly Differencing)
        Weight is low (2) because this is highly intensive.
        """
        # Generate bounding box
        bbox = generate_dynamic_bbox(self.region_data["limits"], self.region_data["tile_sizes"])
        epsg = self.region_data["epsg"]
        t = int(time.time() * 1000)
        source1 = random.choice(self.region_data["sources"])
        source2 = random.choice(self.region_data["sources"])
        
        url = f"/api/analysis/wms/{self.region_name}?variable=speed&source={source1}&vmin=-1000&vmax=1000&t={t}&epoch=1&compareepoch=1&comparesource={source2}&service=WMS&request=GetMap&layers=analysis_layer&styles=&format=image%2Fpng&transparent=true&version=1.1.1&width=256&height=256&srs={epsg}&bbox={bbox}"
        self.client.get(url, name="2d. WMS: Analysis Differencing")

    @task(int(os.getenv("WEIGHT_DATACUBE", 1)))
    def request_datacube_download(self):
        """
        Interaction 3: Background NetCDF Extraction (MultiCubeRequest)
        Weight is very low (1) as users do this infrequently, but it heavily stresses the server.
        """
        if not self.token:
            return # Skip if login failed
        
        # 1. Dynamically generate a 1-year date range
        start_year = random.randint(2015, 2021) # Adjust to your valid data years
        date_start = f"{start_year}-01-01"
        date_end = f"{start_year + 1}-01-01" # Exactly 1 year later
        
        # 2. Dynamically generate a valid, small GeoJSON bounding box
        lat_min, lat_max = self.region_data["lat_range"]
        lon_min, lon_max = self.region_data["lon_range"]
        
        # Use a small delta to ensure the box is < 10,000 km^2 
        # (0.5 deg lat x 1.0 deg lon is roughly 55km x 40km near the poles)
        delta_lat = 0.5
        delta_lon = 1.0
        
        # Pick a random bottom-left corner that leaves room for the delta
        box_lat_min = random.uniform(lat_min, lat_max - delta_lat)
        box_lon_min = random.uniform(lon_min, lon_max - delta_lon)
        
        box_lat_max = box_lat_min + delta_lat
        box_lon_max = box_lon_min + delta_lon
        
        # Pick a source
        source = random.choice(self.region_data["sources"])
            
        payload = {
            "roi_geojson": {
                "type": "Polygon",
                "coordinates": [[
                    [box_lon_min, box_lat_min], 
                    [box_lon_max, box_lat_min], 
                    [box_lon_max, box_lat_max], 
                    [box_lon_min, box_lat_max], 
                    [box_lon_min, box_lat_min] # Close the polygon
                ]]
            },
            "date_start": date_start,
            "date_end": date_end,
            "variables": ["speed", "error"],
            "sources": [source],
            "mode": "multi"
        }
        
        self.client.post(
            "/api/multiSourceCube/download", 
            json=payload, 
            headers=self.auth_headers,
            name="3. Background NetCDF Extraction"
        )