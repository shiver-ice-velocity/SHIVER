# server/utils/zarr_metadata.py
import xarray as xr
import pandas as pd
import platform
import os

# Global dictionary to store the metadata in memory
metadata_cache = {}

current_os = platform.system()
is_wsl = "WSL_DISTRO_NAME" in os.environ
if current_os == "Windows" or is_wsl:
    root_drive = "/mnt/r" if is_wsl else "R:"
    ZARR_PATHS = {
        "Antarctica": f"{root_drive}/SCADI/output/Sentinel1/Antarctica/mosaic/subregions/peninsula/antarctica_multisource_velocity_timeseries.zarr",
        "Greenland": f"{root_drive}/SCADI/output/Sentinel1/Greenland/mosaic/subregions/lev/greenland_multisource_velocity_timeseries.zarr"
    }
else:
    ZARR_PATHS = {
        "Antarctica": r"/mnt/grio1/Shared/SHIVER/data/Antarctica/live/antarctica_multisource_velocity_timeseries.zarr",
        "Greenland": r"/mnt/grio1/Shared/SHIVER/data/Greenland/live/greenland_multisource_velocity_timeseries.zarr"
    }


def load_zarr_metadata():
    """Reads time and source variables from Zarr and populates the global cache."""
    print("Initializing Zarr metadata cache...")
    for region, path in ZARR_PATHS.items():
        try:
            ds = xr.open_zarr(path, consolidated=True) 
            
            # Extract dataset_version attribute from Zarr store metadata
            dataset_version = ds.attrs.get("dataset_version", None)
            
            # Extract mid-dates
            times = pd.to_datetime(ds['time'].values).strftime('%Y-%m-%d').tolist()
            
            # Robustly extract start and end dates using xarray's isel
            tb = ds['time_bnds']
            bnd_dim = [d for d in tb.dims if d != 'time'][0]
            
            starts = pd.to_datetime(tb.isel({bnd_dim: 0}).values).strftime('%Y-%m-%d').tolist()
            ends = pd.to_datetime(tb.isel({bnd_dim: 1}).values).strftime('%Y-%m-%d').tolist()
            
            # Extract sources
            sources = ds['data_source'].values.tolist()
            if isinstance(sources[0], bytes):
                sources = [s.decode('utf-8') for s in sources]
            
            unique_sources = sorted(list(set(sources)))
            
            # Build the epochs list
            epochs = []
            for i in range(len(times)):
                epochs.append({
                    "index": i,
                    "mid_date": times[i],
                    "start_date": starts[i],
                    "end_date": ends[i],
                    "source": sources[i]
                })
            
            metadata_cache[region] = {
                "dataset_version": dataset_version,
                "sources": unique_sources,
                "epochs": epochs
            }
            print(f"  -> {region}: Cached {len(epochs)} epochs.")
            ds.close()
            
        except Exception as e:
            print(f"  -> {region}: Failed to load metadata. Error: {e}")

def clear_zarr_metadata():
    """Clears the cache on shutdown."""
    metadata_cache.clear()