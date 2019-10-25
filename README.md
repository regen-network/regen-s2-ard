# User Guide

## Background

regen-s2-ard (Regen Network Sentinel-2 Analysis Ready Data) is an open-source Sentinel-2 tile-based custom data pre-processing Docker container. 

The toolbox provides a modular approach to automate the pre-processing of any single Sentinel-2 data product. 

It allows users to begin with a single tile name (i.e. S2B_MSIL1C_20190927T000239_N0208_R030_T56JMP_20190927T011718) and in one command produce ARD Sentinel-2 end products.

The regen-s2-ard Docker bundles different open-source software components together such as the [European Space Agency's Sen2Cor](https://step.esa.int/main/third-party-plugins-2/sen2cor/), [FMask](http://www.pythonfmask.org/en/latest/), Anaconda environment, GDAL, gsutil etc. with a recipe for processing ARD products from start to finish.

This ARD toolbox draws inspiration from and It complements to the [Alaskan Satellite Facility's Sentinel-1 toolbox](https://github.com/asfadmin/grfn-s1tbx-rtc) which is a Docker toolbox integrating the ESA SNAP toolbox to pre-process [Radiometrically Terrain Corrected (RTC) S1 SAR data](https://www.youtube.com/watch?v=aZ4xLBrxUow).

## Modules (ARD Operations)

| ARD Operation          | Description   | 
|:---------------------- |:-------------| 
| **Downloading** | Fetching Sentinel-2 Top-of-Atmosphete L1C Data Product from [Google Cloud Storage](https://cloud.google.com/storage/docs/public-datasets/sentinel-2). |
| **Atmospheric Correction** | Running ESA Sen2Cor |
| **Band Subsetting** | Reflectence Bands can be subsetted creating composites |
| **Cloud Masking** | Applying ESA Sen2Cor Scene Classification and/or FMask |
| **Cut-to-AOI** | Batch Cutting the S2 Tile to the input Area-of-Interest Polygon or Polygons producing Image Chips |
| **Stacking** | Reflectance Bands can be merged into a single GTiff file |
| **Deriving Indices** | NDVI, NDWI, CRC, NDTI |

**Note:** *It is also possible to input an already downloaded data product (L1C or L2A) and to perform a reasonable set of operations on that unzipped SAFE data product. For example: You can download data product from [ESA Copernicus SciHub](https://scihub.copernicus.eu/dhus/#/home) manually or using API interfaces such as the excellent [sentinelsat](https://github.com/sentinelsat/sentinelsat) and input the path of the downloaded data product*

## Input options

| Option                 | Description   | 
|:---------------------- |:-------------| 
| --tile | Sentinel-2 SAFE Data Product Name or SAFE Data Product path. |
| --config | *(optional)* Configuration YAML file setting the ARD Operations and Output Product |
| --aoi | *(optional)* GeoJSON file having the Area-of-Interest polygon or polygons |

```
sh s2-ard.sh --tile TILE [--config CONFIG] [--aoi AOI]
```
### Default config.yml
``` yaml
# defining the ard operations
ard-settings:
  "atm-corr" : false
  "cloud-mask" : true
  "stack" : true
  "calibrate" : false
  "clip" : false
  "derived-index" : true

# pixel values in mask to keep (clear pixels)   
cloud-mask-settings:
  #"sen2cor-scl-codes" : [4, 5]
  "fmask-codes" : [1]

output-image-settings:
  # bands to stack 
  "bands" : ["B11", "B08", "B02"]
  # derived indices to calculate
  "vi" : ["ndvi", "ndwi", "ndti", "crc"] 
  # target spatial reference system - epsg code i. e. 3857
  "t-srs" : False
  # output image resolution
  "resolution" : 20
  # method for resampling bands when resolution changes or reprojection  
  "resampling-method" : "cubic"
```
* There are three section in the YAML file:
  - **ard-settings**
  These are True or False key: value pairs representing the performed ARD operations.
  
  - **cloud-mask-settings**
  If Cloud Masking is defined as True we need to define the pixel value(s) in the cloud mask raster we would like to keep
  
  - **output-image-settings**
  In this section we can define the bands we wanna subset from the L1C or L2A input data product and we can set the output image settings such as target spatial reference system, target resolution, resampling method, derived indices. Currently 4 different derived indices can be calculated : NDVI, NDWI, NDTI and CRC.

### 
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

### Example-1

1. Find the name of the L1C tile to process from [ESA Copernicus SciHub](https://scihub.copernicus.eu/dhus/#/home).
   
   *The example below uses S2A_MSIL1C_20190919T175011_N0208_R141_T13TDE_20190919T212919 tile*.

1. Open the Terminal app
   
1. In your Terminal window, navigate to the directory where **s2-ard.sh** is saved.
   
      *For example, if you saved the script to your Downloads directory, type:*
      ```
      cd ~/Downloads
      ```

1. Execute **s2-ard.sh** with the tile name
   ```
   sh s2-ard.sh --tile S2A_MSIL1C_20190919T175011_N0208_R141_T13TDE_20190919T212919
   ```
   Processing can take up from a few minutes to about an hour depending on the config.yml ard settings, internet connection, and computer resources.

1. Upon completion, ARD products will appear in the directory where **s2-ard.sh** was executed under a new folder called **output**
   ```
   S2A_MSIL1C_20190919T175011_N0208_R141_T13TDE_20190919T212919_stacked.tif
   S2A_MSIL1C_20190919T175011_N0208_R141_T13TDE_20190919T212919_FMASK.tif
   S2A_MSIL1C_20190919T175011_N0208_R141_T13TDE_20190919T212919_ndvi.tif
   S2A_MSIL1C_20190919T175011_N0208_R141_T13TDE_20190919T212919_ndwi.tif
   S2A_MSIL1C_20190919T175011_N0208_R141_T13TDE_20190919T212919_ndti.tif
   S2A_MSIL1C_20190919T175011_N0208_R141_T13TDE_20190919T212919_crc.tif
   ```
**Note:** *See the **Default config.yml** section. This is the default configuration of the toolbox. There are three different ARD operations defined: Stacking, Cloud Masking and Deriving Indices*   
