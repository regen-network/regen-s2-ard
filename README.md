# User Guide

## Background

regen-s2-ard (Regen Network Sentinel-2 Analysis Ready Data) is an open-source Sentinel-2 tile-based custom data pre-processing Docker container. 

The toolbox provides a modular approach to automate the pre-processing of any single Sentinel-2 data product. 

It allows users to begin with a single tile name (i.e. S2A_MSIL1C_20190919T175011_N0208_R141_T13TDE_20190919T212919) and in one command produce ARD Sentinel-2 end products.

The regen-s2-ard Docker bundles different open-source software components together such as the [European Space Agency's Sen2Cor](https://step.esa.int/main/third-party-plugins-2/sen2cor/), [FMask](http://www.pythonfmask.org/en/latest/), Anaconda, GDAL, gsutil etc. with a recipe for processing ARD products from start to finish.

This ARD toolbox draws inspiration from and It complements to the [Alaskan Satellite Facility's Sentinel-1 toolbox](https://github.com/asfadmin/grfn-s1tbx-rtc) which is a Docker toolbox integrating the [ESA SNAP toolbox](https://step.esa.int/main/toolboxes/snap/) to pre-process [Radiometrically Terrain Corrected (RTC) Sentinel-1 SAR data](https://www.youtube.com/watch?v=aZ4xLBrxUow).

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

**Note:** *It is also possible to input an already downloaded data product (L1C or L2A) and to perform a reasonable set of operations on that unzipped SAFE data product. For example: You can download data product from [ESA Copernicus SciHub](https://scihub.copernicus.eu/dhus/#/home) manually or using API interfaces such as [sentinelsat](https://github.com/sentinelsat/sentinelsat) and input the path of the downloaded data product*

## Input options

| Option                 | Description   | 
|:---------------------- |:-------------| 
| --tile | Sentinel-2 SAFE Data Product Name or SAFE Data Product path. |
| --config | *(optional)* Configuration YAML file setting the ARD Operations and Output Product |
| --aoi | *(optional)* GeoJSON file having the Area-of-Interest polygon or polygons |

```
sh s2-ard.sh --tile TILE [--config CONFIG] [--aoi AOI]
```
### Configuration
* Default config.yml
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
<details><summary>Ubuntu 18.04</summary>

1. Install Docker using apt
   ```
   sudo apt update
   sudo apt install -y docker.io
   ```
1. Add your user to the docker group
   ```
   sudo usermod -aG docker $USER
   ```
1. Log out and log back in for the group change to take effect
1. To verify everything is working run the docker command
   ```
   docker run hello-world
   ```
   Confirm you see the following in your output
   ```
   Hello from Docker!
   This message shows that your installation appears to be working correctly.
   ```
1. Download **s2-ard.sh** to the directory where ARD products should be saved
   ```
   wget https://raw.githubusercontent.com/regen-network/regen-s2-ard/master/scripts/s2-ard.sh
   ```
</details>

## Usage

### Example-1

**ARD Operations performed in this example:** 
* **Cloud Masking:** FMASK
* **Stacking Bands :** Band-11 (SWIR), Band-08 (NIR), Band-02 (RED)
* **Deriving Indices:** NDVI, NDWI, NDTI, CRC
* **Spatial Resolution:** 20-m
* **Resampling:** Cubic

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
   Processing can take up from a few minutes to about an hour depending on the internet connection, and computer resources.

1. Upon completion, ARD products will appear in the directory where **s2-ard.sh** was executed under a new folder called **output**

``` bash
├── output
│   ├── S2A_MSIL1C_20190919T175011_N0208_R141_T13TDE_20190919T212919_stacked.tif
│   ├── S2A_MSIL1C_20190919T175011_N0208_R141_T13TDE_20190919T212919_FMASK.tif
│   ├── S2A_MSIL1C_20190919T175011_N0208_R141_T13TDE_20190919T212919_ndvi.tif
│   ├── S2A_MSIL1C_20190919T175011_N0208_R141_T13TDE_20190919T212919_ndwi.tif
│   ├── S2A_MSIL1C_20190919T175011_N0208_R141_T13TDE_20190919T212919_ndti.tif
│   ├── S2A_MSIL1C_20190919T175011_N0208_R141_T13TDE_20190919T212919_crc.tif
```

**Note:** *See the **Default config.yml** section. This is the default configuration of the toolbox. There are three different ARD operations defined: Stacking, Cloud Masking and Deriving Indices*   

### Example-2

**ARD Operations performed in this example:**
* **Atmospheric Correction:** ESA Sen2Cor
* **Cloud Masking:** Sen2Cor Scene Classification
* **Stacking Bands:** Band-02, Band-03, Band-04, Band-05, Band-06, Band-07, Band-08, Band-8A, Band-11, Band-12 
* **Deriving Index:** NDVI
* **Spatial Resolution:** 30-m
* **Resampling:** Cubic

1. Find the name of the L1C tile to process from [ESA Copernicus SciHub](https://scihub.copernicus.eu/dhus/#/home).
   
   *The example below uses S2A_MSIL1C_20190919T175011_N0208_R141_T13TDE_20190919T212919 tile*.

1. Open the Terminal app

1. In your Terminal window, navigate to the directory where **s2-ard.sh** is saved.
   
      *For example, if you saved the script to your Downloads directory, type:*
      ```
      cd ~/Downloads
      ```

1. Create a new configuration YAML file (new_config.yml) with the following content. (The name of the configuration file can be anything.)

``` yaml
# defining the ard operations
ard-settings:
  "atm-corr" : true
  "cloud-mask" : true
  "stack" : true
  "calibrate" : false
  "clip" : false
  "derived-index" : true

# pixel values in mask to keep (clear pixels)   
cloud-mask-settings:
  "sen2cor-scl-codes" : [4, 5]
  #"fmask-codes" : [1]

output-image-settings:
  # bands to stack 
  "bands" : ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]
  # derived indices to calculate
  "vi" : ["ndvi"] 
  # target spatial reference system - epsg code i. e. 3857
  "t-srs" : False
  # output image resolution
  "resolution" : 30
  # method for resampling bands when resolution changes or reprojection  
  "resampling-method" : "cubic"
```

1. Execute **s2-ard.sh** with the tile name
   ```
   sh s2-ard.sh --tile S2A_MSIL1C_20190919T175011_N0208_R141_T13TDE_20190919T212919 --config new_config.yml
   ```
   Processing can take up about an hour this case depending on the internet connection, and computer resources. Atmospheric Correction runs about ~45 minutes.

1. Upon completion, ARD products will appear in the directory where **s2-ard.sh** was executed under a new folder called **output**

``` bash
├── output
│   ├── S2A_MSIL2A_20190919T175011_N9999_R141_T13TDE_20191026T081601.SAFE
│   ├── S2A_MSIL2A_20190919T175011_N9999_R141_T13TDE_20191026T081601_ndvi.tif
│   ├── S2A_MSIL2A_20190919T175011_N9999_R141_T13TDE_20191026T081601_stacked.tif
```

### Example-3

**ARD Operations performed in this example:**
* **Cloud Masking:** Sen2Cor Scene Classification
* **Deriving Index:** NDVI
* **Spatial Resolution:** 10-m
* **Reprojection:** EPSG:23700 (Hungarian National Projection)
* **Resampling:** Near

1. The */tests/example-3/forest_patches.geojson* file contians 4 forest polygons derived from [Corine Land Cover (CLC 2018) 100-m Raster](https://land.copernicus.eu/pan-european/corine-land-cover/clc2018?tab=download) located near Budapest, Hungary.

1. Find the name of a L1C tile covering these forest patches to process from [ESA Copernicus SciHub](https://scihub.copernicus.eu/dhus/#/home).
   
   *The example below uses S2A_MSIL1C_20191002T094031_N0208_R036_T34TCT_20191002T111505 tile*.

1. Open the Terminal app

1. In your Terminal window, navigate to the directory where **s2-ard.sh** is saved.
   
      *For example, if you saved the script to your Downloads directory, type:*
      ```
      cd ~/Downloads
      ```

1. Create a new configuration YAML file (new_config.yml) with the following content. (The name of the configuration file can be anything.)

``` yaml
# defining the ard operations
ard-settings:
  "atm-corr" : false
  "cloud-mask" : true
  "stack" : false
  "calibrate" : false
  "clip" : true
  "derived-index" : true

# pixel values in mask to keep (clear pixels)   
cloud-mask-settings:
  "sen2cor-scl-codes" : [4, 5]
  #"fmask-codes" : [1]

output-image-settings:
  # bands to stack 
  "bands" : []
  # derived indices to calculate
  "vi" : ["ndvi"] 
  # target spatial reference system - epsg code i. e. 3857
  "t-srs" : 23700
  # output image resolution
  "resolution" : 10
  # method for resampling bands when resolution changes or reprojection  
  "resampling-method" : "near"
```

1. Execute **s2-ard.sh** with the tile name
   ```
   sh s2-ard.sh --tile S2A_MSIL1C_20191002T094031_N0208_R036_T34TCT_20191002T111505 --config new_config.yml
   ```
   Processing can take up about a few minutes this case depending on the internet connection, and computer resources.

1. Upon completion, ARD products will appear in the directory where **s2-ard.sh** was executed under a new folder called **output**. The image chip output of the batch clipping is organized under the **clipped** sub-directory by feature id.

``` bash

├── output
│   ├──clipped
│   │   ├── 0
│   │   │   ├── S2A_MSIL1C_20191002T094031_N0208_R036_T34TCT_20191002T111505_ndvi_FEATURE_ID_0_clipped.tif
│   │   ├── 1
│   │   │   ├── S2A_MSIL1C_20191002T094031_N0208_R036_T34TCT_20191002T111505_ndvi_FEATURE_ID_1_clipped.tif
│   │   ├── 2
│   │   │   ├── S2A_MSIL1C_20191002T094031_N0208_R036_T34TCT_20191002T111505_ndvi_FEATURE_ID_2_clipped.tif
│   │   ├── 3
│   │   │   ├── S2A_MSIL1C_20191002T094031_N0208_R036_T34TCT_20191002T111505_ndvi_FEATURE_ID_3_clipped.tif
│   S2A_MSIL1C_20191002T094031_N0208_R036_T34TCT_20191002T111505_ndvi.tif
```

### Example-4

**ARD Operations performed in this example:**
* **Cloud Masking:** Sen2Cor Scene Classification, FMASK
* **Stacking Bands:** Band-02, Band-03, Band-04, Band-05, Band-06, Band-07, Band-08, Band-8A, Band-11, Band-12 
* **Deriving Index:** NDVI
* **Spatial Resolution:** 20-m
* **Resampling:** Cubic

1. In the previous examples the L1C Sentinel-2 Data Product was downloaded inside the docker container while this example and the next use an already downloaded data product. You can download data product from [ESA Copernicus SciHub](https://scihub.copernicus.eu/dhus/#/home) manually or using API interfaces such as [sentinelsat](https://github.com/sentinelsat/sentinelsat). 
   
   *The example below uses S2A_MSIL2A_20191028T235251_N0213_R130_T56JMM_20191029T015139.SAFE tile*.

1. Open the Terminal app

1. Unzip the downloaded data product
   
   ```
   unzip S2A_MSIL2A_20191028T235251_N0213_R130_T56JMM_20191029T015139.zip
   ```
   
1. In your Terminal window, navigate to the directory where **s2-ard.sh** is saved.
   
      *For example, if you saved the script to your Downloads directory, type:*
      ```
      cd ~/Downloads
      ```

1. Create a new configuration YAML file (new_config.yml) with the following content. (The name of the configuration file can be anything.)

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
  "sen2cor-scl-codes" : [4, 5]
  "fmask-codes" : [1]

output-image-settings:
  # bands to stack 
  "bands" : ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]
  # derived indices to calculate
  "vi" : ["ndvi"] 
  # target spatial reference system - epsg code i. e. 3857
  "t-srs" : False
  # output image resolution
  "resolution" : 20
  # method for resampling bands when resolution changes or reprojection  
  "resampling-method" : "cubic"
```

1. Execute **s2-ard.sh** with the tile name
   ```
   sh s2-ard.sh --tile /path/to/S2A_MSIL2A_20191028T235251_N0213_R130_T56JMM_20191029T015139.SAFE --config new_config.yml
   ```
   Processing can take up about a few minutes this case depending on the internet connection, and computer resources.

1. Upon completion, ARD products will appear in the directory where **s2-ard.sh** was executed under a new folder called **output**.

``` bash
├── output
│   S2A_MSIL2A_20191028T235251_N0213_R130_T56JMM_20191029T015139_stacked.tif
│   S2A_MSIL2A_20191028T235251_N0213_R130_T56JMM_20191029T015139_ndvi.tif
```

### Example-5

**ARD Operations performed in this example:**
* **Atmospheric Correction:** ESA Sen2Cor
* **Cloud Masking:** Sen2Cor Scene Classification, FMASK
* **Stacking Bands:** Band-02, Band-03, Band-04, Band-05, Band-06, Band-07, Band-08, Band-8A, Band-11, Band-12 
* **Deriving Index:** NDVI
* **Spatial Resolution:** 20-m
* **Resampling:** Cubic

1. In the previous examples the L1C Sentinel-2 Data Product was downloaded inside the docker container while this example and the next use an already downloaded data product. You can download data product from [ESA Copernicus SciHub](https://scihub.copernicus.eu/dhus/#/home) manually or using API interfaces such as [sentinelsat](https://github.com/sentinelsat/sentinelsat). 
   
   *The example below uses S2A_MSIL1C_20191028T235251_N0208_R130_T56JMM_20191029T011422.SAFE tile*.

1. Open the Terminal app

1. Unzip the downloaded data product
   
   ```
   unzip S2A_MSIL1C_20191028T235251_N0208_R130_T56JMM_20191029T011422.zip
   ```
   
1. In your Terminal window, navigate to the directory where **s2-ard.sh** is saved.
   
      *For example, if you saved the script to your Downloads directory, type:*
      ```
      cd ~/Downloads
      ```

1. Create a new configuration YAML file (new_config.yml) with the following content. (The name of the configuration file can be anything.)

``` yaml
# defining the ard operations
ard-settings:
  "atm-corr" : true
  "cloud-mask" : true
  "stack" : true
  "calibrate" : false
  "clip" : false
  "derived-index" : true

# pixel values in mask to keep (clear pixels)   
cloud-mask-settings:
  "sen2cor-scl-codes" : [4, 5]
  "fmask-codes" : [1]

output-image-settings:
  # bands to stack 
  "bands" : ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]
  # derived indices to calculate
  "vi" : ["ndvi"] 
  # target spatial reference system - epsg code i. e. 3857
  "t-srs" : False
  # output image resolution
  "resolution" : 20
  # method for resampling bands when resolution changes or reprojection  
  "resampling-method" : "cubic"
```

1. Execute **s2-ard.sh** with the tile name
   ```
   sh s2-ard.sh --tile /path/to/S2A_MSIL1C_20191028T235251_N0208_R130_T56JMM_20191029T011422.SAFE --config new_config.yml
   ```
   Processing can take up about a few minutes this case depending on the internet connection, and computer resources.

1. Upon completion, ARD products will appear in the directory where **s2-ard.sh** was executed under a new folder called **output**.

``` bash
├── output
│   S2A_MSIL2A_20191028T235251_N0213_R130_T56JMM_20191029T015139_stacked.tif
│   S2A_MSIL2A_20191028T235251_N0213_R130_T56JMM_20191029T015139_ndvi.tif
```
