# server/config.py
import platform
from pathlib import Path
import os

current_os = platform.system()
is_wsl = "WSL_DISTRO_NAME" in os.environ
if current_os == "Windows" or is_wsl:
    root_drive = "/mnt/r" if is_wsl else "R:"
    base_path_gr = Path(f"{root_drive}/aux_data/overlays/Greenland")
    base_path_ant = Path(f"{root_drive}/aux_data/overlays/Antarctica")
    overlay_path_gr = Path(f"{root_drive}/aux_data/overlays/Greenland")
    overlay_path_ant = Path(f"{root_drive}/aux_data/overlays/Antarctica")
    landsat_mosaic_path_gr = Path(f"{root_drive}/aux_data/image_mosaic/Greenland/GEE_S2/greenland_tiles_20m")
    SPATIAL_ZARR_PATHS = {
        "Greenland": Path(f"{root_drive}/SCADI/output/Sentinel1/Greenland/mosaic/subregions/lev/greenland_multisource_velocity_spatial_200.zarr"),
        "Antarctica": Path(f"{root_drive}/SCADI/output/Sentinel1/Antarctica/mosaic/subregions/peninsula/antarctica_multisource_velocity_spatial_200.zarr")
    }
    TIMESERIES_ZARR_PATHS = {
        "Greenland": Path(f"{root_drive}/SCADI/output/Sentinel1/Greenland/mosaic/subregions/lev/greenland_multisource_velocity_timeseries.zarr"),
        "Antarctica": Path(f"{root_drive}/SCADI/output/Sentinel1/Antarctica/mosaic/subregions/peninsula/antarctica_multisource_velocity_timeseries.zarr")
    }
    CUBED_ZARR_PATHS = {
        "Greenland": Path(f"{root_drive}/SCADI/output/Sentinel1/Greenland/mosaic/subregions/lev/greenland_multisource_velocity_cubed.zarr"),
        "Antarctica": Path(f"{root_drive}/SCADI/output/Sentinel1/Antarctica/mosaic/subregions/peninsula/antarctica_multisource_velocity_cubed.zarr")
    }
    OMEZARR_PATHS = {
        "Greenland": Path(f"{root_drive}/SCADI/output/Sentinel1/Greenland/mosaic/subregions/lev/greenland_multisource_velocity_spatial.zarr"),
        "Antarctica": Path(f"{root_drive}/SCADI/output/Sentinel1/Antarctica/mosaic/subregions/peninsula/antarctica_multisource_velocity_spatial.zarr")
    }
    COG_BASE_DIR = {
        "Greenland": Path(f"{root_drive}/aux_data/overlays/Greenland"),
        "Antarctica": Path(f"{root_drive}/aux_data/overlays/Antarctica")
    }
else:
    base_path_gr = Path("/mnt/grio1/Shared/SHIVER/data/Greenland")
    base_path_ant = Path("/mnt/grio1/Shared/SHIVER/data/Antarctica")
    overlay_path_gr = Path("/mnt/grio1/Shared/SHIVER/data/Greenland/overlays")
    overlay_path_ant = Path("/mnt/grio1/Shared/SHIVER/data/Antarctica/overlays")
    landsat_mosaic_path_gr = Path("/mnt/grio1/Shared/SHIVER/data/Greenland/image_mosaic/greenland_tiles_20m")
    SPATIAL_ZARR_PATHS = {
        "Greenland": Path("/mnt/grio1/Shared/SHIVER/data/Greenland/live/greenland_multisource_velocity_spatial_200.zarr"),
        "Antarctica": Path("/mnt/grio1/Shared/SHIVER/data/Antarctica/live/antarctica_multisource_velocity_spatial_200.zarr")
    }
    TIMESERIES_ZARR_PATHS = {
        "Greenland": Path("/mnt/grio1/Shared/SHIVER/data/Greenland/live/greenland_multisource_velocity_timeseries.zarr"),
        "Antarctica": Path("/mnt/grio1/Shared/SHIVER/data/Antarctica/live/antarctica_multisource_velocity_timeseries.zarr")
    }
    CUBED_ZARR_PATHS = {
        "Greenland": Path("/mnt/grio1/Shared/SHIVER/data/Greenland/live/greenland_multisource_velocity_cubed.zarr"),
        "Antarctica": Path("/mnt/grio1/Shared/SHIVER/data/Antarctica/live/antarctica_multisource_velocity_cubed.zarr")
    }
    OMEZARR_PATHS = {
        "Greenland": Path("/mnt/grio1/Shared/SHIVER/data/Greenland/live/greenland_multisource_velocity_spatial.zarr"),
        "Antarctica": Path("/mnt/grio1/Shared/SHIVER/data/Antarctica/live/antarctica_multisource_velocity_spatial.zarr")
    }
    COG_BASE_DIR = {
        "Greenland": Path("/mnt/grio1/Shared/SHIVER/data/Greenland/overlays"),
        "Antarctica": Path("/mnt/grio1/Shared/SHIVER/data/Antarctica/overlays")
    }

TIFF_PATHS = {
    "Greenland": {
        "default_speed": overlay_path_gr / "Greenland_Speed_Hillshaded_COG.tif",
        "u"    : overlay_path_gr / "Greenland_U_Merged_COG.tif", 
        "v"    : overlay_path_gr / "Greenland_V_Merged_COG.tif", 
        "count": overlay_path_gr / "Greenland_AllSources_Epoch_Count.tif",
        "trend": overlay_path_gr / "Greenland_AllSources_Linear_Trend_masked.tif",
        "hillshade": overlay_path_gr / "Greenland_Hillshade_COG.tif",
        "range": overlay_path_gr / "greenland_agg_mean_COG.tif",
        "landsat_mosaic": landsat_mosaic_path_gr / "greenland_20m_mosaic.vrt"
    },
    "Antarctica": {
        "default_speed": overlay_path_ant / "Antarctica_Speed_Hillshaded_COG.tif",
        "u":     overlay_path_ant / "Antarctica_U_Merged_COG.tif", 
        "v":     overlay_path_ant / "Antarctica_V_Merged_COG.tif", 
        "count": overlay_path_ant / "Antarctica_AllSources_Epoch_Count.tif",
        "trend": overlay_path_ant / "Antarctica_AllSources_Linear_Trend_masked.tif",
        "hillshade": overlay_path_ant / "Antarctica_Hillshade_COG.tif",
        "range": overlay_path_ant / "antarctica_agg_mean_COG.tif",
    }
}
    