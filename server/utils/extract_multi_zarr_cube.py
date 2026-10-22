import xarray as xr
import geopandas as gpd
from shapely.geometry import shape
import pandas as pd
import numpy as np
import os
import rioxarray 
import uuid
import platform
from pathlib import Path
from datetime import datetime

from utils.citations import generate_citation_text

# Set zarr store depending on operating system
current_os = platform.system()
is_wsl = "WSL_DISTRO_NAME" in os.environ
if current_os == "Windows" or is_wsl:
    root_drive = "/mnt/r" if is_wsl else "R:"
    DATA_STORES = {
        'Greenland': {
            'path': Path(f"{root_drive}/SCADI/output/Sentinel1/Greenland/mosaic/subregions/lev/greenland_multisource_velocity_cubed.zarr"), 
            'crs': "EPSG:3413"
        },
        'Antarctica': {
            'path': Path(f"{root_drive}/SCADI/output/Sentinel1/Antarctica/mosaic/subregions/peninsula/antarctica_multisource_velocity_cubed.zarr"), 
            'crs': "EPSG:3031"
        }
    }
else:
    DATA_STORES = {
        'Greenland': {
            'path': Path("/mnt/grio1/Shared/SHIVER/data/Greenland/live/greenland_multisource_velocity_cubed.zarr"), 
            'crs': "EPSG:3413"
        },
        'Antarctica': {
            'path': Path("/mnt/grio1/Shared/SHIVER/data/Antarctica/live/antarctica_multisource_velocity_cubed.zarr"), 
            'crs': "EPSG:3031"
        }
    }

# Set export directory
if current_os == "Windows"  or is_wsl:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    export_dir = os.path.join(base_dir, "static", "exports")
    os.makedirs(export_dir, exist_ok=True)
else: 
    export_dir = Path("/mnt/grio1/Shared/SHIVER/data/exports")
    os.makedirs(export_dir, exist_ok=True)
    

def generate_multi_netcdf_cube(
    geojson_geometry: dict,
    date_range: tuple[str, str], 
    sources: list[str],
    variables: list[str] = ["speed", "speed_error", "vx", "vy", "vx_error", "vy_error"] 
) -> tuple[str, str, str, str]:
    """
    Generates a NetCDF file for Multi-Source Zarr data.
    Runs strictly as a background task.
    """
    
    # 1. Parse Geometry & Detect Region
    user_shape = shape(geojson_geometry)
    
    if user_shape.centroid.y < 0:
        region = "Antarctica"
        target_crs = "EPSG:3031"
    else:
        region = "Greenland"
        target_crs = "EPSG:3413"
        
    store_info = DATA_STORES.get(region)
    if not store_info:
        raise ValueError(f"Region not found for lat: {user_shape.centroid.y}")

    # 2. Project Geometry to Data CRS
    gdf = gpd.GeoDataFrame({'geometry': [user_shape]}, crs="EPSG:4326")
    gdf_proj = gdf.to_crs(target_crs)
    minx, miny, maxx, maxy = gdf_proj.total_bounds
    
    # 3. Open Zarr Store (Lazy Load)
    ds = xr.open_zarr(store_info['path'], consolidated=True, chunks={})
    
    # Extract dataset_version attribute from Zarr store metadata
    dataset_version = ds.attrs.get("dataset_version", None)
    version = f" (Version v{dataset_version})" if dataset_version else ""

    # Handle duplicate times
    time_series = pd.Series(ds['time'].values)
    if time_series.duplicated().any():
        print("Duplicate times detected. Adding nanosecond noise to make them unique...")
        # cumcount() gives 0 for the first occurrence, 1 for the second, 2 for the third, etc.
        offsets = time_series.groupby(time_series).cumcount()
        # Convert offsets to nanosecond timedeltas and add to original times
        noise = pd.to_timedelta(offsets, unit='ns')
        ds = ds.assign_coords(time=(time_series + noise).values)
    
    # 4. Spatial and Temporal Subsetting
    print(f"Subsetting spatially and temporally...")
    buffer = 200 
    y_slice = slice(maxy + buffer, miny - buffer) if ds.y[0] > ds.y[-1] else slice(miny - buffer, maxy + buffer)
    
    # Sort time first to prevent Pandas non-monotonic indexing errors
    subset = ds.sortby("time").sel( 
        x=slice(minx - buffer, maxx + buffer), 
        y=y_slice,
        time=slice(date_range[0], date_range[1])
    )
    
    # 5. Select variables 
    final_vars = list(variables) 
    
    # Add errors to variable list if needed
    if any('vx' in v.lower() for v in variables) and 'vx' in subset:
        final_vars.append('vx_error')
    # 7c. Add U error if any U variable is requested
    if any('vy' in v.lower() for v in variables) and 'vy' in subset:
        final_vars.append('vy_error')
    # 7d. Add S (Speed) error if any Speed variable is requested
    if any('speed' in v.lower() for v in variables) and 'speed_error' in subset:
        final_vars.append('speed_error')
        
    # Always include data_source and time_bnds
    if "data_source" in ds:
        final_vars.append("data_source")
    if "time_bnds" in ds:
        bnds_dim = [d for d in ds["time_bnds"].dims if d != "time"][0] # Find the boundary dimension (usually 'bnds', 'nv', or 'd2')
        time_sep = (ds["time_bnds"].isel({bnds_dim: 1}) - ds["time_bnds"].isel({bnds_dim: 0})) # Subtract start time from end time
        subset["time_separation"] = (time_sep / np.timedelta64(1, 'D')).astype(float) # Convert timedelta64[ns] directly to float days
        final_vars.append("time_separation")

    # Filter the dataset to include only these variables
    vars_to_keep = [v for v in final_vars if v in subset]
    subset = subset[vars_to_keep]
    
    # 6. Clip to polygon boundaries
    print("Clipping data to exact polygon shape...")
    try:
        subset.rio.write_crs(target_crs, inplace=True)
        subset = subset.rio.clip(gdf_proj.geometry, crs=target_crs, drop=False, invert=False, all_touched=True)
    except Exception as e:
        print(f"Clipping failed: {e}. Returning unclipped bounding box.")
    
    # 7. Filter by data source
    if sources and "data_source" in subset:
        print(f"Filtering by selected sources: {sources}")
        
        # Compute the boolean mask into memory so Xarray knows the exact shape
        mask = subset["data_source"].isin(sources).compute()
        valid_times = subset.time[mask]
        
        # Subset the entire dataset to only keep those valid time slices
        subset = subset.sel(time=valid_times)
        
        # Safety check: Did we filter out everything?
        if subset.time.size == 0:
            raise ValueError("No data found for the exact region, time period, and data sources selected.")
            
    # 8. Add citation information
    actual_sources = []
    if "data_source" in subset:
        unique_vals = np.unique(subset["data_source"].values)
        actual_sources = [
            str(s) for s in unique_vals 
            if pd.notna(s) and str(s).lower() not in ['nan', 'none', 'unknown', '']
        ]
        
    # The global 30+ line citation string for the metadata and txt file
    citation_text = generate_citation_text(actual_sources, region, dataset_version=dataset_version)
    
    # A. Create the dedicated SHIVER row first
    shiver_citations = (
        f"SHIVER data and compilation method: Davison, B. J. (2026). The SHeffield Ice Velocity ExploreR (SHIVER): A unified satellite-derived ice velocity dataset for Earth's ice sheets{version} [Data set]. Zenodo. https://doi.org/10.5281/zenodo.21375859\n\n"
        f"SHIVER method paper: Davison, B. J. et al. (in prep). The SHeffield Ice Velocity ExploreR (SHIVER): an online tool for low latency exploration, analysis and sub-setting of unified satellite-derived ice velocity data for Earth's ice sheets. Manuscript in preparation."
    )
    
    summary_rows = [{
        "Data Source": "SHIVER",
        "First Date": "",
        "Last Date": "",
        "Mode Temporal Resolution (days)": "",
        "Epochs (Measurements)": "",
        "Citation": shiver_citations
    }]
    
    # B. Generate the Summary Table (CSV) Data
    for src in actual_sources:
        # Isolate the time slices for this specific source
        mask = (subset["data_source"] == src).compute()
        valid_times = subset.time[mask]
        
        if len(valid_times) == 0:
            continue
            
        sub_src = subset.sel(time=valid_times)
        
        #  Dates
        first_date = pd.to_datetime(sub_src.time.values.min()).strftime('%Y-%m-%d')
        last_date = pd.to_datetime(sub_src.time.values.max()).strftime('%Y-%m-%d')
        
        # 3. Mode Temporal Resolution
        mode_res = "N/A"
        if "time_separation" in sub_src:
            # Calculate mode, ignoring NaNs
            mode_vals = pd.Series(sub_src["time_separation"].values).dropna().mode()
            if not mode_vals.empty:
                mode_res = round(float(mode_vals.iloc[0]), 2)
                
        # Epochs
        epochs = len(valid_times)
        
        # Specific Citation for just this row
        full_cite = generate_citation_text([src], region, dataset_version=dataset_version)
        delimiter = "cite these original sources:\n\n* "
        
        if delimiter in full_cite:
            clean_cite = full_cite.split(delimiter)[1].strip()
        else:
            # Fallback if the format slightly changes
            clean_cite = full_cite.split("* ")[-1].strip()
                    
        summary_rows.append({
            "Data Source": src,
            "First Date": first_date,
            "Last Date": last_date,
            "Mode Temporal Resolution (days)": mode_res if isinstance(mode_res, (int, float)) else mode_res,
            "Epochs (Measurements)": epochs,
            "Citation": clean_cite
        })

    # C. Convert the list of dictionaries directly into a CSV string
    csv_text = pd.DataFrame(summary_rows).to_csv(index=False)
            
    # 9. Metadata Check
    if subset.rio.crs is None:
        subset.rio.write_crs(target_crs, inplace=True)
        
    for var_name in subset.variables:
        subset[var_name].attrs['grid_mapping'] = 'spatial_ref'
        
        lower_name = var_name.lower()
        if var_name == 'x':
            subset[var_name].attrs.update({'long_name': f"polar stereographic easting ({target_crs})", 'units': "m"})
        elif var_name == 'y':
            subset[var_name].attrs.update({'long_name': f"polar stereographic northing ({target_crs})", 'units': "m"})
        elif var_name == 'time':
            subset[var_name].attrs.update({'long_name': "time", 'standard_name': "time"})
        elif var_name == 'time_separation':
            subset[var_name].attrs.update({'long_name': "time separation between image pairs in each measurement epoch",'units': "days"})
        elif 'speed' in lower_name:
            subset[var_name].attrs.update({'long_name': "ice surface velocity magnitude", 'units': "m yr-1"})
        elif 'vx' in lower_name:
            subset[var_name].attrs.update({'long_name': "ice surface easting velocity", 'units': "m yr-1"})
        elif 'vy' in lower_name:
            subset[var_name].attrs.update({'long_name': "ice surface northing velocity", 'units': "m yr-1"})
        elif 'speed_error' in lower_name:
             subset[var_name].attrs.update({'long_name': "magnitude of ice velocity error", 'units': "m yr-1"})
        elif 'vx_error' in lower_name:
             subset[var_name].attrs.update({'long_name': "easting velocity error", 'units': "m yr-1"})
        elif 'vy_error' in lower_name:
             subset[var_name].attrs.update({'long_name': "northing velocity error", 'units': "m yr-1"})
        elif 'data_source' in lower_name:
             subset[var_name].attrs.update({'long_name': "original satellite data source ID"})
               
    time_start = pd.to_datetime(subset.time.values.min()).strftime('%Y%m%d') if subset.time.size > 0 else date_range[0]
    time_end = pd.to_datetime(subset.time.values.max()).strftime('%Y%m%d') if subset.time.size > 0 else date_range[1]
    
    subset.attrs = {
        'title': f"{region} Multi-Source Ice Velocity Cube",
        'author': 'Benjamin Davison and Andrew Sole',
        'creator_name': 'Benjamin Davison',
        'creator_email': 'b.j.davison@sheffield.ac.uk',
        'institution': 'University of Sheffield',
        'product_version': dataset_version,
        'time_coverage_start': time_start,
        'time_coverage_end': time_end,
        'user_selected_sources': ", ".join(sources), # Log requested sources in metadata
        'keywords': f"{region}, velocity, Sentinel-1",
        'Conventions': 'CF-1.8, ACDD-1.3',
        'date_created': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'acknowledgment': citation_text
    }
    
    # 10. Save
    encoding = {}
    for var in subset.data_vars:
        # Handle string arrays (like data_source) safely without float _FillValues
        if subset[var].dtype.kind in 'UOS': 
            encoding[var] = {'zlib': True, 'complevel': 5}
        else:
            encoding[var] = {'zlib': True, 'complevel': 5, 'shuffle': True, '_FillValue': -9999.0}
            
        # Specific override for SHIFT's measurement_count to save space
        if var == "measurement_count":
             encoding[var]['dtype'] = 'int16'
             encoding[var]['_FillValue'] = -1
             
    # Force identical time encoding across ALL data cubes
    # This prevents the int64/scipy crash and guarantees consistency
    encoding['time'] = {
        'units': 'days since 1950-01-01',
        'calendar': 'proleptic_gregorian',
        'dtype': 'float64',
        '_FillValue': None
    }
        
    #base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    #export_dir = os.path.join(base_dir, "static", "exports")
    #os.makedirs(export_dir, exist_ok=True)
    
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{region}_multisource_{date_range[0]}_{date_range[1]}_{unique_id}.nc"
    output_path = os.path.join(export_dir, filename)

    subset.to_netcdf(output_path, encoding=encoding, engine='netcdf4', format='NETCDF4')    
    print(f"Saved multi-source cube to: {output_path}")
    return output_path, region, citation_text, csv_text