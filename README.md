# User Guide

## Background

regen-s2-ard (Regen Network Sentinel-2 Analysis Ready Data) is an open-source Sentinel-2 tile-based custom data pre-processing Docker container. 
The toolbox provides a modular approach to automate the pre-processing of any single Sentinel-2 data product. It allows users to begin with a single tile name (i.e. S2B_MSIL1C_20190927T000239_N0208_R030_T56JMP_20190927T011718) and in one command produce ARD Sentinel-2 end products.

The regen-s2-ard Docker bundles different open-source software components together such as the [European Space Agency's Sen2Cor](https://step.esa.int/main/third-party-plugins-2/sen2cor/), [FMask](http://www.pythonfmask.org/en/latest/), Anaconda environment, GDAL, gsutil etc. with a recipe for processing ARD products from start to finish.

This ARD toolbox draws inspiration from and It complements to the [Alaskan Satellite Facility's Sentinel-1 toolbox](https://github.com/asfadmin/grfn-s1tbx-rtc) which is a Docker toolbox integrating the ESA SNAP toolbox to pre-process [Radiometrically Terrain Corrected (RTC) S1 SAR data](https://www.youtube.com/watch?v=aZ4xLBrxUow).

* Inputs
    - Sentinel-2 SAFE Data Product Name or SAFE Data Product path
    - * *(optional)* * Configuration YAML file setting the ARD Operations and Output Product 
    - * *(optional)* * GeoJSON file having the Area-of-Interest polygon or polygons

* Modules (ARD Operations)
    **Note:** It is possible to input an already downloaded data product (L1C or L2A) and to perform a reasonable set of operations on that unzipped SAFE data product. For example You can download data product from [ESA Copernicus SciHub](https://scihub.copernicus.eu/dhus/#/home) manually or using API interfaces such as the excellent [sentinelsat](https://github.com/sentinelsat/sentinelsat) and input the path of the downloaded data product
    - Downloading : Fetching Sentinel-2 Top-of-Atmosphete L1C Data Product from [Google Cloud Storage](https://cloud.google.com/storage/docs/public-datasets/sentinel-2) 
    - Atmospheric Correction : running ESA Sen2cor
    - Band Subsetting : Reflectence Bands can be subsetted creating composites
    - Cloud Masking : Applying ESA Sen2Cor Scene Classification and/or FMask 
    - Cut-to-AOI : Batch Cutting the S2 Tile to the input Area-of-Interest Polygon or Polygons producing Image Chips
    - Stacking : Reflectance Bands can be merged into a single GTiff file
    - Deriving Vegetation Indices : NDVI, NDWI, CRC, NDTI

## Output Products
* GeoTIFF image with 
    - Optional pixel spacing (default is 20 m)
    - Pixel values indicate Top-of-Atmosphere Reflectance or Bottom-of-Atmosphere Reflectance or Derived Index
    - Optional spatial reference system (EPSG code based Reprojection; default: Projection of the processed S2 Tile) 

## System Requirements
* Operating System
    - Ubuntu 18.04 or later
* 64-bit installation
* 16 GB of RAM
* 20 GB of available hard disk space

## Installation

## Usage
