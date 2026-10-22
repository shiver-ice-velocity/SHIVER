# SHIVER: SHeffield Ice Velocity ExploreR

__Low-latency access to ice velocity measurements for Greenland and Antarctica__

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21378056.svg)](https://doi.org/10.5281/zenodo.21378056)

**SHIVER** is a user-friendly, interactive platform for exploring, visualizing and extracting ice velocity measurements of Greenland and Antarctica.

The velocity datasets incorporated into SHIVER are described in the SHIVER [`Greenland`](https://shiver-ice-velocity.github.io/SHIVER/documentation/greenland) and [`Antarctica`](https://shiver-ice-velocity.github.io/SHIVER/documentation/Antarctica) data source documentation. 

You can use SHIVER to:

* **Visualize and download** time-series of ice velocity at any location on the Greenland and Antarctic ice sheets.
* **Calculate speed trends** at any location and time-period, through any and all data sources, on-the-fly.
* **Explore maps of flow speed** from any time-period and data source.
* **Generate maps of speed change** across any time-period and any combination of data sources, on-the-fly.
* **Generate and download** your own 3-D data cubes of ice velocity.

And much more! 

The SHIVER functionality is described in more detail in our [`SHIVER documentation pages`](https://shiver-ice-velocity.github.io/SHIVER/documentation/overview). 

## Contact: 
b.j.davison@sheffield.ac.uk & shiver@sheffield.ac.uk


## Website
[`SHIVER:`](https://shiver-ice-velocity.github.io/SHIVER/) https://shiver-ice-velocity.github.io/SHIVER/

## Cite
A dataset description paper for SHIVER is in preparation. Until it is published, cite it as:

> Davison, B. J. et al. (in prep). The SHeffield Ice Velocity ExploreR (SHIVER): an online tool for low latency exploration, analysis and sub-setting of unified satellite-derived ice velocity data for Earth's ice sheets. Manuscript in preparation.

The dataset itself should also be cited like this:

> Davison, B. J. (2026a). The SHeffield Ice Velocity ExploreR (SHIVER): A unified satellite-derived ice velocity dataset for Earth's ice sheets (Version v1.5.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.21375859

Replace `1.5.0` with the version you actually used. The SHIVER stores are updated as new data are appended, and every store records its release in its root attributes. Each release matches a version of the [Zenodo record](https://doi.org/10.5281/zenodo.21375859), so you can always recover exactly which data were used:

```python
import xarray as xr

ds = xr.open_zarr("https://data.source.coop/uos-shiver/greenland/greenland_multisource_velocity_timeseries.zarr")
print(ds.attrs["dataset_version"], ds.attrs["last_updated"])  # e.g. 1.5.0 2026-10-16
```

The SHIVER dataset is a compilation of many published velocity datasets and so would not have been possible without those. Therefore, those contributing datasets should also be cited. Specifically, you should cite all contributing datasets that your specific query intersected. If you are extracting data programmatically, please see our notebook describing how you can generate the correct citations for your query. 

If instead you are using the SHIVER application, all exports will contain citation details for the relevant contributing datasets. This will include a table (<strong>citations_summary.csv</strong>) summarising the required citations and a text file (<strong>citations_and_usage.txt</strong>) with descriptive details. 

<em>Note: The ESA_CCI_Sentinel-1, ESA_CCI_Sentinel-2 and ESA_CCI_ERS1-2_Envisat over selected glacier sites in Greenland require separate citations for each glacier site. Our dataset compilation method combines all of those glacier sites into one datasource. Our automated citation generator will therefore provide the citation information for all glacier sites even if only one is intersected. You should remove the unnecessary citations when incorporating them into your work.</em>
