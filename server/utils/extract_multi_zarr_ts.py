import xarray as xr
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
import numpy as np
from pathlib import Path
import platform
import os
import warnings
from scipy.signal import savgol_filter
from functools import lru_cache

# --- 1. CONFIGURATION & ENVIRONMENT DETECTION ---
current_os = platform.system()
is_wsl = "WSL_DISTRO_NAME" in os.environ
if current_os == "Windows" or is_wsl:
    root_drive = "/mnt/r" if is_wsl else "R:"
    DATA_STORES = {
        'Greenland': {
            'path': Path(f"{root_drive}/SCADI/output/Sentinel1/Greenland/mosaic/subregions/lev/greenland_multisource_velocity_timeseries_subset.zarr"), 
            'crs': "EPSG:3413"
        },
        'Antarctica': {
            'path': Path(f"{root_drive}/SCADI/output/Sentinel1/Antarctica/mosaic/subregions/peninsula/antarctica_multisource_velocity_timeseries.zarr"), 
            'crs': "EPSG:3031"
        }
    }
else:
    DATA_STORES = {
        'Greenland': {
            'path': Path("/mnt/grio1/Shared/SHIVER/data/Greenland/live/greenland_multisource_velocity_timeseries.zarr"), 
            'crs': "EPSG:3413"
        },
        'Antarctica': {
            'path': Path("/mnt/grio1/Shared/SHIVER/data/Antarctica/live/antarctica_multisource_velocity_timeseries.zarr"), 
            'crs': "EPSG:3031"
        }
    }

@lru_cache(maxsize=8)
def get_cached_timeseries_zarr(zarr_path):
    """
    Opens the time-series Zarr store and caches the dataset in memory.
    """
    return xr.open_zarr(zarr_path, consolidated=True).sortby('time')


def _empty_site_response(status="error", message="", variable=["speed"]):
    data_dict = {
        "dates": [],
        "dt": [],
        "data_source": [],
        "count": []
    }
    for var in variable:
        data_dict[f"{var}_error"] = []
        data_dict[var] = {
            "raw": [],
            "smoothed": []
        }
    return {
        "status": status,
        "message": message,
        "data": data_dict
    }


def clean_nans(data_series, decimals=None):
    """
    Vectorized conversion of floats/NaNs to standard Python lists matching JSON schema.
    Safely handles both NumPy arrays and Pandas ExtensionDtypes (e.g., StringDtype).
    """
    # Safely check numeric type across NumPy and Pandas ExtensionDtypes
    if isinstance(data_series, (pd.Series, pd.Index)):
        is_numeric = pd.api.types.is_numeric_dtype(data_series.dtype)
        arr = data_series.to_numpy()
    else:
        arr = np.asarray(data_series)
        is_numeric = pd.api.types.is_numeric_dtype(arr.dtype)
        
    if arr.size == 0:
        return []

    if is_numeric:
        if decimals is not None:
            arr = np.round(arr, decimals)
        res = np.where(np.isfinite(arr), arr, None)
        return res.tolist()
    else:
        return np.where(pd.notnull(arr), arr, None).tolist()


def get_multi_glacier_timeseries(
    location_input, 
    buffer=500, 
    variable=['speed'], 
    sources=None,
    name_column=None, 
    gap_fill=24,
    win_raw=25,
    win_daily=25,
    poly=2
):
    results = {}
    
    # 1. Parse Input
    gdf = _load_input_to_gdf(location_input)
    if gdf.empty:
        return {"error": "Input file contains no geometries."}
    
    if len(gdf) > 10:
        gdf = gdf.head(10)
        results["warning"] = "File contained more than 10 locations. Only the first 10 were extracted."

    # 2. Detect Region
    first_geom = gdf.geometry.iloc[0]
    ref_lat = first_geom.centroid.y
    region = 'Antarctica' if ref_lat < 0 else 'Greenland'
    store_info = DATA_STORES[region]
    
    # 3. Open Zarr
    try:
        ds = get_cached_timeseries_zarr(store_info['path'])
    except Exception as e:
        return {"error": f"Could not open multi-source data store: {str(e)}"}

    # 4. Iterate Sites
    for idx, row in gdf.iterrows():
        site_name = f"Site_{idx}"
        if name_column and name_column in gdf.columns: site_name = str(row[name_column])
        elif 'name' in gdf.columns: site_name = str(row['name'])
        elif 'Name' in gdf.columns: site_name = str(row['Name'])

        current_buffer = buffer
        if 'buffer' in gdf.columns:
            try: current_buffer = float(row['buffer'])
            except (ValueError, TypeError): current_buffer = buffer
            
        site_data = _process_single_site_multi(
            ds, row.geometry, store_info['crs'], current_buffer, variable, sources,
            gap_fill, win_raw, win_daily, poly
        )
        
        centroid = row.geometry.centroid
        meta = {
            "site_name": site_name,
            "region": region,
            "buffer_used": current_buffer,
            "lat": round(centroid.y, 5),
            "lon": round(centroid.x, 5),
            "type": "Polygon" if isinstance(row.geometry, Polygon) else "Point",
            "variable": variable,
            "sources_requested": sources if sources else "All",
            "params": { "gap": gap_fill, "win_raw": win_raw, "win_daily": win_daily, "poly": poly }
        }

        if 'meta' in site_data:
            site_data['meta'].update(meta)
        else:
            site_data['meta'] = meta
            
        results[site_name] = site_data

    return results


def _process_single_site_multi(ds, geometry, target_crs, buffer, variable, sources, gap_fill, win_raw, win_daily, poly):
    temp_gdf = gpd.GeoDataFrame({'geometry': [geometry]}, crs="EPSG:4326").to_crs(target_crs)
    proj_geom = temp_gdf.geometry.iloc[0]
    
    x_min, x_max = ds.x.min().item(), ds.x.max().item()
    y_min, y_max = ds.y.min().item(), ds.y.max().item()
    if y_min > y_max: y_min, y_max = y_max, y_min

    px, py = proj_geom.centroid.x, proj_geom.centroid.y
    if not (x_min <= px <= x_max) or not (y_min <= py <= y_max):
        return _empty_site_response("error", "Location outside data coverage.", variable=variable)
    
    is_single_pixel = False
    if isinstance(proj_geom, Point):
        if buffer <= 0: is_single_pixel = True 
        else: minx, miny, maxx, maxy = proj_geom.buffer(buffer).bounds
    else:
        if buffer > 0: proj_geom = proj_geom.buffer(buffer)
        minx, miny, maxx, maxy = proj_geom.bounds

    if not is_single_pixel:
        y_slice = slice(maxy, miny) if ds.y[0] > ds.y[-1] else slice(miny, maxy)
        try:
            subset = ds.sel(x=slice(minx, maxx), y=y_slice)
            if subset.x.size == 0 or subset.y.size == 0: is_single_pixel = True 
        except Exception: is_single_pixel = True

    if is_single_pixel:
        try:
            subset = ds.sel(x=proj_geom.centroid.x, y=proj_geom.centroid.y, method='nearest')
        except Exception as e:
            return _empty_site_response("error", f"Pixel selection failed: {e}", variable=variable)
            
    # Load slice into memory once to speed up downstream evaluations
    subset = subset.load()

    if 'time_bnds' in subset.data_vars or 'time_bnds' in subset.coords:
        tb = subset['time_bnds']
        if len(tb.dims) >= 2:
            bnd_dim = [d for d in tb.dims if d != 'time'][0]
            t0 = tb.isel({bnd_dim: 0})
            t1 = tb.isel({bnd_dim: 1})
            dt_days = (t1 - t0) / np.timedelta64(1, 'D')
            subset = subset.assign(time_separation=dt_days)
        else:
            subset = subset.assign(time_separation=xr.full_like(subset['time'], 12.0, dtype=float))
        subset = subset.drop_vars('time_bnds')
    else:
        subset = subset.assign(time_separation=xr.full_like(subset['time'], 12.0, dtype=float))

    extract_vars = variable + [f"{v}_error" for v in variable]
    
    if is_single_pixel:
        df = subset[extract_vars + ['data_source', 'time_separation']].to_dataframe()
        df['valid_count'] = subset[variable[0]].notnull().astype(int).to_series()
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            spatial_median = subset[extract_vars].median(dim=['x', 'y'])
        
        valid_count = subset[variable[0]].notnull().sum(dim=['x', 'y'])
        
        df = spatial_median.to_dataframe()
        
        if 'x' in subset['data_source'].dims:
            df['data_source'] = subset['data_source'].isel(x=0, y=0).values
            df['time_separation'] = subset['time_separation'].isel(x=0, y=0).values
        else:
            df['data_source'] = subset['data_source'].values
            df['time_separation'] = subset['time_separation'].values
            
        df['valid_count'] = valid_count.values

    # Filter by Data Source
    if sources is not None and len(sources) > 0:
        df = df[df['data_source'].astype(str).isin(sources)]
        
    if df.empty or df[variable[0]].dropna().empty:
        return _empty_site_response("error", "No valid data or all selected sources masked/NaN", variable=variable)
    
    df['time_separation'] = df['time_separation'].apply(lambda x: x if x > 0 else 0.5).fillna(12.0)
    df = df.sort_index()
    
    if df.index.duplicated().any():
        df = df.groupby(level=0).first()
        
    # GLOBAL TIMELINE SETUP
    exact_idx = df.index
    daily_idx = pd.date_range(start=exact_idx.min().floor('D'), end=exact_idx.max().ceil('D'), freq='D')
    full_idx = exact_idx.union(daily_idx).sort_values()

    df_daily = df.reindex(full_idx) 

    output_data = {
        "dates": full_idx.strftime('%Y-%m-%dT%H:%M:%S').tolist(), 
        "dt": clean_nans(df_daily['time_separation'].astype(float), decimals=1),
        "data_source": clean_nans(df_daily['data_source']), 
        "count": df_daily['valid_count'].fillna(0).astype(int).tolist()
    }
    
    # Pre-calculate shared temporal variables
    capped_separation = df['time_separation'].clip(upper=gap_fill)
    time_sep_days = pd.to_timedelta(capped_separation, unit='D')
    starts_arr = (df.index - (time_sep_days / 2)).dt.floor('D').values
    ends_arr   = (df.index + (time_sep_days / 2)).dt.ceil('D').values
    dt_arr     = df['time_separation'].values

    # PROCESSING LOOP FOR VARIABLES
    for var in variable:
        var_series = df[var].copy()
        
        # --- 1. ABSOLUTE MASKING ---
        if var == 'speed':
            var_series.loc[(var_series < -100) | (var_series > 100000)] = np.nan
        else:
            var_series.loc[var_series.abs() > 100000] = np.nan
        
        # --- 2. ROBUST HAMPEL FILTER (ROLLING MAD) ---
        rolling_med = var_series.rolling(window=5, center=True, min_periods=1).median()
        abs_dev = (var_series - rolling_med).abs()
        rolling_mad = abs_dev.rolling(window=5, center=True, min_periods=1).median()
        
        # Threshold: 3 * 1.4826 * MAD (~3 sigma for Gaussian)
        threshold = 3.0 * 1.4826 * rolling_mad
        
        # Fallback when MAD is zero (e.g., identical values)
        global_std = var_series.std()
        if pd.isna(global_std) or global_std == 0: global_std = 1.0
        threshold = threshold.replace(0, np.nan).fillna(3.0 * global_std)
        
        outliers = abs_dev > threshold
        var_series.loc[outliers] = np.nan
        
        # Map raw data onto combined timeline
        df_daily_var = var_series.reindex(full_idx)
        valid_dates_mask = df_daily_var.notnull() 
        
        output_data[f"{var}_error"] = clean_nans(df_daily[f"{var}_error"].astype(float), decimals=2)

        # --- STEP 1: RAW SMOOTHING ---
        daily_filled = df_daily_var.interpolate(method='time', limit=gap_fill)
        processed_raw_series = df_daily_var.copy() 
        
        try:
            temp_series = daily_filled.interpolate(method='time', limit_direction='both')
            curr_len = len(temp_series)
            effective_window = win_raw
            if curr_len < effective_window: effective_window = curr_len
            if effective_window % 2 == 0: effective_window -= 1 

            if effective_window >= 3:
                smoothed_values = savgol_filter(temp_series.values, window_length=effective_window, polyorder=poly)
                daily_smoothed_raw = pd.Series(smoothed_values, index=full_idx)
                processed_raw_series = daily_smoothed_raw.where(valid_dates_mask)
        except Exception:
            pass

        # --- STEP 2: VECTORIZED WEIGHTED DAILY AVERAGE ---
        raw_at_df = processed_raw_series.reindex(df.index).values
        vals_arr = np.where(pd.notnull(raw_at_df), raw_at_df, var_series.values)
        
        valid_mask = pd.notnull(vals_arr)
        
        if valid_mask.any():
            v_vals = vals_arr[valid_mask]
            v_starts = starts_arr[valid_mask]
            v_ends = ends_arr[valid_mask]
            v_dts = np.where((pd.notnull(dt_arr[valid_mask])) & (dt_arr[valid_mask] >= 1.0), dt_arr[valid_mask], 1.0)
            v_weights = 1.0 / v_dts
            
            num_days = ((v_ends - v_starts) / np.timedelta64(1, 'D')).astype(int) + 1
            valid_range = num_days > 0

            if valid_range.any():
                v_vals = v_vals[valid_range]
                v_starts = v_starts[valid_range]
                v_weights = v_weights[valid_range]
                num_days = num_days[valid_range]

                rep_vals = np.repeat(v_vals, num_days)
                rep_weights = np.repeat(v_weights, num_days)
                
                offsets = np.concatenate([np.arange(n) for n in num_days])
                rep_dates = np.repeat(v_starts, num_days) + offsets.astype('timedelta64[D]')

                big_df = pd.DataFrame({
                    'date': rep_dates,
                    'weighted_val': rep_vals * rep_weights,
                    'weight': rep_weights
                })
                grouped = big_df.groupby('date', sort=False)
                daily_ts = grouped['weighted_val'].sum() / grouped['weight'].sum()
                daily_ts = daily_ts.reindex(full_idx)
            else:
                daily_ts = pd.Series(dtype=float, index=full_idx)
        else:
            daily_ts = pd.Series(dtype=float, index=full_idx)

        # --- DAILY SMOOTHING & GAP RE-MASKING ---
        daily_ts_filled = daily_ts.interpolate(method='time', limit=gap_fill)
        daily_final = daily_ts.copy() 
        
        try:
            temp_series_daily = daily_ts_filled.interpolate(method='time', limit_direction='both')
            curr_len_d = len(temp_series_daily)
            eff_win_daily = win_daily
            if curr_len_d < eff_win_daily: eff_win_daily = curr_len_d
            if eff_win_daily % 2 == 0: eff_win_daily -= 1

            if eff_win_daily >= 3:
                smooth_vals_daily = savgol_filter(temp_series_daily.values, window_length=eff_win_daily, polyorder=poly)
                daily_final = pd.Series(smooth_vals_daily, index=full_idx)
                daily_final[daily_ts_filled.isna()] = np.nan
        except Exception: 
            pass
            
        output_data[var] = {
            "raw": clean_nans(processed_raw_series.astype(float), decimals=2), 
            "smoothed": clean_nans(daily_final.astype(float), decimals=2)             
        }

    return {
        "status": "success",
        "message": "Data processed successfully.",
        "data": output_data
    }


def _load_input_to_gdf(loc_input):
    if isinstance(loc_input, (str, Path)):
        path_str = str(loc_input)
        if path_str.lower().endswith('.zip'):
            return gpd.read_file(f"zip://{path_str}")
        return gpd.read_file(path_str)
    
    if isinstance(loc_input, list):
        if len(loc_input) > 0 and isinstance(loc_input[0], (int, float)):
             loc_input = [loc_input]
        geoms = [Point(lon, lat) for lat, lon in loc_input]
        return gpd.GeoDataFrame(geometry=geoms, crs="EPSG:4326")
    
    if isinstance(loc_input, gpd.GeoDataFrame):
        return loc_input.to_crs("EPSG:4326")

    raise ValueError("Unsupported input format.")