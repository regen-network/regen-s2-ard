# User Guide

## Background

regen-s2-ard (Regen Network Sentinel-2 Analysis Ready Data) is an open-source Sentinel-2 tile-based custom data pre-processing Docker container.

The toolbox provides a modular approach to automate the pre-processing of any set of Sentinel-2 data products.

It allows users to begin with a directory of Sentinel-2 tile names (i.e. S2B_MSIL2A_20190506T235259_N0212_R130_T56JMM_20190522T0859529) and in one command produce analysis ready data products.

The regen-s2-ard Docker bundles different open-source software components together such as the [European Space Agency's Sen2Cor](https://step.esa.int/main/third-party-plugins-2/sen2cor/), [FMask](http://www.pythonfmask.org/en/latest/), Anaconda, GDAL, gsutil etc. with a recipe for processing ARD products from start to finish.

This ARD toolbox draws inspiration from and It complements to the [Alaskan Satellite Facility's Sentinel-1 toolbox](https://github.com/asfadmin/grfn-s1tbx-rtc) which is a Docker toolbox integrating the [ESA SNAP toolbox](https://step.esa.int/main/toolboxes/snap/) to pre-process [Radiometrically Terrain Corrected (RTC) Sentinel-1 SAR data](https://www.youtube.com/watch?v=aZ4xLBrxUow).

## Modules (ARD Operations)

| ARD Operation          | Description   |
|:---------------------- |:-------------|
| **Atmospheric Correction** | Running ESA Sen2Cor |
| **Band Subsetting** | Reflectence Bands can be subsetted to create composites |
| **Cloud Masking** | Applying ESA Sen2Cor Scene Classification and/or FMask |
| **Cut-to-AOI** | Batch cutting of S2 tiles to an input Area-of-Interest polygon or polygons to produce image chips |
| **Stacking** | Reflectance bands can be merged into a single GTiff file |
| **Deriving Indices** | NDVI, NDWI, CRC, NDTI, VDVI, BSI |
| **Mosaicing** | Mosaic two or more S2 Tiles into a single GTiff file |
| **Averaging** | Average two or more S2 Tiles into a single GTiff file |

**Note:** *It is also possible to input an already downloaded data product (L1C or L2A) and to perform a reasonable set of operations on that unzipped SAFE data product. For example: You can download data product from [ESA Copernicus SciHub](https://scihub.copernicus.eu/dhus/#/home) manually or using API interfaces such as [sentinelsat](https://github.com/sentinelsat/sentinelsat) and input the path of the downloaded data product*

## Input options

| Option                 | Description   |
|:---------------------- |:-------------|
| --tiles | Data directory containing one or more Sentinel-2 SAFE Data Product Names or SAFE Data Product paths. |
| --config | Configuration YAML file setting the ARD Operations and Output Product |
| --aoi | *(optional)* GeoJSON file having the Area-of-Interest polygon or polygons |

```
sh s2-ard.sh --tiles DATA_DIR --config CONFIG [--aoi AOI]
```
### Configuration File
``` yaml
# list of tiles to process
tile-list:
  tile-1:
    # name of the tile
    "tile-name" : "S2A_MSIL2A_20190521T235251_N0212_R130_T56JMM_20190522T014028.SAFE"

    # defining the ard operations
    ard-settings:
      "atm-corr" : false
      "cloud-mask" : false
      "stack" : true
      "calibrate" : false
      "clip" : true
      "derived-index" : true

    # pixel values in mask to keep (clear pixels)
    cloud-mask-settings:
      #"sen2cor-scl-codes" : [4, 5, 6, 7]
      #"fmask-codes" : [1]

    output-image-settings:
      # bands to stack
      "bands" : ["B02", "B03", "B04", "B05", "B06", "B08", "B11", "B12"]
      # derived indices to calculate
      "vi" : ["ndvi", "vdvi", "bsi"]
      # target spatial reference system - epsg code i. e. 3857
      "t-srs" : False
      # output image resolution
      "resolution" : 10
      # method for resampling bands when resolution changes or reprojection
      "resampling-method" : "cubic"

  tile-2:
    # name of the tile
    "tile-name" : "S2B_MSIL2A_20190506T235259_N0212_R130_T56JMM_20190522T085952.SAFE"

    # defining the ard operations
    ard-settings:
      "atm-corr" : false
      "cloud-mask" : true
      "stack" : true
      "calibrate" : false
      "clip" : true
      "derived-index" : true

    # pixel values in mask to keep (clear pixels)
    cloud-mask-settings:
      "sen2cor-scl-codes" : [4, 5, 6, 7]
      #"fmask-codes" : [1]

    output-image-settings:
      # bands to stack
      "bands" : ["B02", "B03", "B04", "B05", "B06", "B08", "B11", "B12"]
      # derived indices to calculate
      "vi" : ["ndvi", "vdvi", "bsi"]
      # target spatial reference system - epsg code i. e. 3857
      "t-srs" : False
      # output image resolution
      "resolution" : 10
      # method for resampling bands when resolution changes or reprojection
      "resampling-method" : "cubic"

# mosaic settings
mosaic-settings:
  # build mosaic
  "build-mosaic" : false
  # method for resampling bands during a mosaic (default is nearest)
  "resampling-method" : "nearest"
  # ordered list of images to mosaic - images are stacked w/last image on top
  image-list:
    1: ~

# image average settings
average-settings:
  # average images
  "compute-average" : true
  # clip to aoi
  "clip" : true
  # images to include in average
  image-list:
    1: "S2A_MSIL2A_20190521T235251_N0212_R130_T56JMM_20190522T014028.SAFE"
    2: "S2B_MSIL2A_20190506T235259_N0212_R130_T56JMM_20190522T085952.SAFE"

```
* There are three main sections in the YAML file:
  - **tile-list**
  List of one or more tiles to process. Each tile contains the following settings:  
    - **ard-settings**
    True or False key-value pairs representing the ARD operations to perform.
    - **cloud-mask-settings**
    List of pixels value(s) in the cloud mask raster we would like to keep if cloud mask is defined as true.
      * FMask Codes: http://www.pythonfmask.org/en/latest/fmask_fmask.html
      * S2 SCL Codes: https://earth.esa.int/web/sentinel/technical-guides/sentinel-2-msi/level-2a/algorithm
    - **output-image-settings**
    In this section we can define the bands we want to subset from the L1C or L2A input data product and set the output image settings such as target spatial reference system, target resolution, resampling method, derived indices. Currently 6 different derived indices can be calculated : NDVI, NDWI, NDTI, CRC, VDVI and BSI.
  - **mosaic-settings**
  List of images to include in the mosaic, GDAL buildvrt mosaic setting options.
  - **average-settings**
  List of images to include in the average.

## Output Products
* GeoTIFF image with
    - Optional pixel spacing (default is 10 m)
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

The following examples

### Example-1

**ARD Operations performed in this example:**
* **Cloud Masking:** FMASK
* **Stacking Bands :** Band-11 (SWIR), Band-08 (NIR), Band-02 (RED)
* **Deriving Indices:** NDVI, NDWI, NDTI, CRC
* **Spatial Resolution:** 20-m
* **Resampling:** Cubic

**config_file**
```yaml
# list of tiles to process
tile-list:
  tile-1:
    # name of the tile
    "tile-name" : "S2B_MSIL2A_20190506T235259_N0212_R130_T56JMM_20190522T085952.SAFE"

    # defining the ard operations
    ard-settings:
      "atm-corr" : false
      "cloud-mask" : false
      "stack" : true
      "calibrate" : false
      "clip" : true
      "derived-index" : true

    # pixel values to keep (aka. clear pixels)
    cloud-mask-settings:
      #"sen2cor-scl-codes" : [4, 5]
      #"fmask-codes" : [1]

    output-image-settings:
      # bands to stack
      "bands" : ["B02", "B03", "B04", "B08"]
      # derived indices to calculate
      "vi" : ["ndvi"]
      # target spatial reference system - epsg code i.e. 3857
      "t-srs" : False
      # output image resolution
      "resolution" : 10
      # method for resampling bands when resolution changes or reprojection
      "resampling-method" : "cubic"

  tile-2:
      # name of the tile
      "tile-name" : "S2A_MSIL2A_20190521T235251_N0212_R130_T56JMM_20190522T014028.SAFE"

      # defining the ard operations
      ard-settings:
        "atm-corr" : false
        "cloud-mask" : true
        "stack" : true
        "calibrate" : false
        "clip" : true
        "derived-index" : true

      # pixel values in mask to keep (clear pixels)
      cloud-mask-settings:
        "sen2cor-scl-codes" : [4, 5, 6, 7]
        #"fmask-codes" : [1]

      output-image-settings:
        # bands to stack
        "bands" : ["B02", "B03", "B04", "B08"]
        # derived indices to calculate
        "vi" : ["ndvi"]
        # target spatial reference system - epsg code i. e. 3857
        "t-srs" : False
        # output image resolution
        "resolution" : 10
        # method for resampling bands when resolution changes or reprojection
        "resampling-method" : "cubic"

# mosaic settings
mosaic-settings:
  # build mosaic
  "build-mosaic" : false
  # method for resampling bands during a mosaic (default is nearest)
  "resampling-method" : "nearest"
  # crop to aoi
  "clip" : false
  # ordered list of images to mosaic - images are stacked w/last image on top
  image-list:
    1: ~

# image average settings
average-settings:
  # average images
  "compute-average" : true
  # clip to aoi
  "clip" : true
  # images to include in average
  image-list:
    1: "S2B_MSIL2A_20190506T235259_N0212_R130_T56JMM_20190522T085952.SAFE"
    2: "S2A_MSIL2A_20190521T235251_N0212_R130_T56JMM_20190522T014028.SAFE"
```

1. Find the names of the L2A tiles listed in the config file from [ESA Copernicus SciHub](https://scihub.copernicus.eu/dhus/#/home).

1. Open the Terminal app

1. In your Terminal window, navigate to the directory where **s2-ard.sh** is saved.

      *For example, if you saved the script to your Downloads directory, type:*
      ```
      cd ~/Downloads
      ```

1. Execute **s2-ard.sh** with the directory containing the two tiles, the config file, and the aoi file
   ```
   sh s2-ard.sh --tiles data/ --config config.yml --aoi data/wilmot_extent.geojson
   ```
   Processing can take up from a few minutes to about an hour depending on the internet connection, and computer resources.

1. Upon completion, ARD products will appear in the directory where **s2-ard.sh** was executed under a new folder called **output**

``` bash
├── output
│   │
│   ├──S2B_MSIL2A_20190506T235259_N0212_R130_T56JMM_20190522T085952
│   │   ├── S2B_MSIL2A_20190506T235259_N0212_R130_T56JMM_20190522T085952_stacked.tif
│   │   ├── S2B_MSIL2A_20190506T235259_N0212_R130_T56JMM_20190522T0859529_ndvi.tif
│   │   ├── S2B_MSIL2A_20190506T235259_N0212_R130_T56JMM_20190522T0859529_ndwi.tif
│   │   ├── clipped
│   │   │   ├── S2B_MSIL2A_20190506T235259_N0212_R130_T56JMM_20190522T0859529_stacked_clipped.tif
│   │   │   ├── S2B_MSIL2A_20190506T235259_N0212_R130_T56JMM_20190522T0859529_ndvi_clipped.tif
│   │   │   ├── S2B_MSIL2A_20190506T235259_N0212_R130_T56JMM_20190522T0859529_ndwi_clipped.tif
│   │   
│   ├──S2A_MSIL2A_20190521T235251_N0212_R130_T56JMM_20190522T014028
│   │   ├── S2B_MSIL2A_20190506T235259_N0212_R130_T56JMM_20190522T085952_stacked.tif
│   │   ├── S2A_MSIL2A_20190521T235251_N0212_R130_T56JMM_20190522T014028_ndvi.tif
│   │   ├── S2A_MSIL2A_20190521T235251_N0212_R130_T56JMM_20190522T014028_ndwi.tif
│   │   ├── clipped
│   │   │   ├── S2A_MSIL2A_20190521T235251_N0212_R130_T56JMM_20190522T014028_stacked_clipped.tif
│   │   │   ├── S2A_MSIL2A_20190521T235251_N0212_R130_T56JMM_20190522T014028_ndvi_clipped.tif
│   │   │   ├── S2A_MSIL2A_20190521T235251_N0212_R130_T56JMM_20190522T014028_ndwi_clipped.tif
│   │
│   ├──average
│   │   ├── 20190521_20190506_average_stacked.tif
│   │   ├── 20190521_20190506_average_ndvi.tif
│   │   ├── 20190521_20190506_average_ndwi.tif
│   │   ├── clipped
│   │   │   ├── 20190521_20190506_average_stacked_clipped.tif
│   │   │   ├── 20190521_20190506_average_ndvi_clipped.tif
│   │   │   ├── 20190521_20190506_average_ndwi_clipped.tif
```
