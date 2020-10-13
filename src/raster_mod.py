#!/usr/bin/env python3

# Python modules
import os
import subprocess
import numpy as np
from osgeo import gdal
from osgeo import ogr
import osr
import glob


def system_call(params):
    print(" ".join(params))
    return_code = subprocess.call(params)
    if return_code:
        print(return_code)

# raster operations
def compute_average(self, image_dir, output_dir, average_settings):

    # list of images to mosaic
    tile_list = []
    for image in average_settings['image-list']:
        tile_path = os.path.join(image_dir, image[:-5])
        for file in os.listdir(tile_path):
            if os.path.isfile(os.path.join(tile_path, file)) and file.endswith('.tif'):
                tile_list.append(os.path.join(tile_path, file))

    # averages to generate based on extension (stacked, ndvi, etc...)
    file_extensions = list(set(tile.split('_')[-1] for tile in tile_list))

    # sensing date of images
    image_dates = [tile.split('/')[-1][11:19] for tile in average_settings['image-list']]

    output_dir = "/output/average"

    for extension in file_extensions:
        # build image list from extension
        tiles = [tile for tile in tile_list if tile.endswith(extension)]
        # read in images
        array_list = [self.read_image(x) for x in tiles]
        try:
            with np.errstate(all='raise'):
                array_mean = np.nanmean(array_list, axis=0)
        except:
            print('failed')
        # performing average
        print('performing average')
        #array_out = np.squeeze(array_out)
        # create output image
        output_image = output_dir + os.sep + '_'.join(image_dates + ['average', extension])
        # write image
        with rio.open(tiles[0]) as src:
            meta = src.meta
        meta['driver'] = 'GTiff'
        meta['dtype'] = 'float32'
        with rio.open(output_image, 'w', **meta) as dst:
            dst.write(array_mean.astype(rio.float32))

def build_mosaic(image_dir, mosaic_settings):
    # list of images to mosaic
    tile_list = []
    for image in mosaic_settings['image-list']:
        tile_path = os.path.join(image_dir, image[:-5])
        for file in os.listdir(tile_path):
            if os.path.isfile(os.path.join(tile_path, file)) and file.endswith('.tif'):
                tile_list.append(os.path.join(tile_path, file))

    # mosaics to build based on extension (stacked, ndvi, etc...)
    file_extensions = list(set(tile.split('_')[-1] for tile in tile_list))
    # sensing date of images
    image_dates = [tile[11:19] for tile in mosaic_settings['image-list']]
    # output directory
    output_dir = "/output/mosaic"

    for extension in file_extensions:
        # create a list of images to mosaic
        to_mosaic = [tile for tile in tile_list if tile.endswith(extension)]
        # order the list of images to mosaic (last image in is the image on top)
        mosaic_bands = [x for _, x in sorted(zip(mosaic_settings['image-list'], to_mosaic))]
        # build mosaic
        mosaic_vrt = output_dir + os.sep + '_'.join(image_dates + ['mosaic', extension[:-4]]) + '.vrt'
        system_command = ['gdalbuildvrt', mosaic_vrt, '-r', mosaic_settings['resampling-method']] + mosaic_bands
        system_call(system_command)
        # convert mosaic to geotiff
        output_image = mosaic_vrt[:-4] + '.tif'
        system_command = ["gdal_translate", "-of", "GTiff", mosaic_vrt, output_image]
        system_call(system_command)

    # cleanup
    for file in os.listdir(output_dir):
        if file.endswith('.vrt'):
            try:
                os.remove(output_dir + os.sep + file)
            except Exception:
                print('unable to remove: ', file)


def get_raster_epsg(input_raster):
    src = gdal.Open(input_raster)
    proj = osr.SpatialReference(wkt=src.GetProjection())
    return(proj.GetAttrValue('AUTHORITY', 1))


def get_band_meta(img_file):
    band_meta = {}
    src = gdal.Open(img_file)
    band_meta['band_num'] = src.RasterCount
    band_meta['geotransform'] = list(src.GetGeoTransform())
    band_meta['crs'] = src.GetProjectionRef()
    band_meta['epsg'] = osr.SpatialReference(wkt=src.GetProjectionRef()).GetAttrValue('AUTHORITY', 1)
    band_meta['X'] = src.RasterXSize
    band_meta['Y'] = src.RasterYSize
    band_meta['dtype'] = src.GetRasterBand(1).DataType
    band_meta['datatype'] = gdal.GetDataTypeName(band_meta["dtype"])
    band_meta['nodata'] = src.GetRasterBand(1).GetNoDataValue()
    band_meta['nodata'] = 0
    return(band_meta)


def read_band(band_path):
    src = gdal.Open(band_path)
    return(src.GetRasterBand(1).ReadAsArray())


def resample_image(image, resampled_image, img_prop):
    """ Resamples image to a target resolution

        Parameters
        ----------
        image : str
            file path to input raster
        resampled_image : str
            file path to resampled image
        img_prop : dict
            contains target resolution and resampling method according to gdal
            standards.

            example:
                { 'resolution' : 10,
                  'resmpling_method' : 'cubic' }

        Returns
        -------
        str
            path to resampled image
    """
    print('Resolution does not meet target_resolution, resampling %s' % (image))
    system_command = ['gdal_translate', "-tr", str(img_prop['resolution']), str(img_prop['resolution']), '-r', str(img_prop['resampling_method']), image, resampled_image]
    system_call(system_command)
    return(resampled_image)


def warp_image(image, warped_image, img_prop):
    """ Reprojects image to target crs

        Parameters
        ----------
        image : str
            file path to input raster
        warped_image : str
            file path to resampled image
        img_prop : dict
            contains target resolution and resampling method according to gdalwarp
            standards.

            example:
                { 'resolution' : 10,
                  't_srs' : '4326' }

        Returns
        -------
        str
            path to resampled image
    """
    system_command = ['gdalwarp', "-tr", str(img_prop['resolution']), str(img_prop['resolution']), '-t_srs', 'EPSG:' + str(img_prop['t_srs']), '-r', img_prop['resampling_method'], image, warped_image, '-overwrite']
    system_call(system_command)
    return(warped_image)


def write_image(out_name, driver, band_meta, arrays):
    """ Write raster to file

        Parameters
        ----------
        out_name : str
            full path to output file
        driver : str
            driver type (ex. )
        band_meta : dict
            output raster metadata (coordinate system, transform, cell size, etc...)
        arrays : list
            list of 2d-numpy arrays to write to file
    """
    print('WRITING IMAGE: ' + out_name)
    driver = gdal.GetDriverByName(driver)
    dataset_out = driver.Create(out_name, band_meta["X"], band_meta["Y"], len(arrays), band_meta["dtype"])
    dataset_out.SetGeoTransform(band_meta["geotransform"])
    dataset_out.SetProjection(band_meta["crs"])
    dataset_out.SetMetadataItem('AREA_OR_POINT', 'Area')
    for i in range(len(arrays)):
        band = dataset_out.GetRasterBand(i + 1)
        band.WriteArray(arrays[i])
        band.SetNoDataValue(band_meta['nodata'])
    dataset_out = None


# masking operations
def binary_mask(scl, pixel_values):
    """ Binary mask

        Parameters
        ----------
        scl : numpy array
            Land use land cover (LULC) array
        pixel_values : list
            list of values in scl to keep
    """
    mask = np.zeros(scl.shape)
    for pixel_value in pixel_values:
        mask = np.ma.masked_where(scl == pixel_value, mask).filled(1)
    return(mask)


def mask_array(mask, array):
    return(np.ma.masked_where(mask == 0, array).filled(0))


# spectral index calculations
def normalized_diff(b1, b2):
    """ Normalized Difference Index (NDVI, NWDI, etc...)

        Equation:
        ---------
            NDIFF = (B1 - B2) / (B1 + B2)

        Parameters:
        -----------
        b1 , b2 : numpy array

        Returns:
        --------
        numpy array
            normalized difference raster
    """

    b1, b2 = read_band(b1) / float(10000), read_band(b2) / float(10000)
    if not (b1.shape == b2.shape):
        raise ValueError("Both arrays should have the same dimensions")

    # Ignore warning for division by zero
    with np.errstate(divide="ignore"):
        n_diff = (b1 - b2) / (b1 + b2).astype(np.float32)
        # mask out invalid values
        n_diff[np.isinf(n_diff)] = np.nan
        if np.isnan(n_diff).any():
            n_diff = np.ma.masked_invalid(n_diff)

    return n_diff


def vdvi(self, blue, green, red):
    """ Visible Difference Vegetation Index (Wang et al 2005)

        Equation:
        ---------
        VDVI = ((2 * Green) - Red - Blue) / ((2 * Green) + Red + Blue)

        Parameters:
        -----------
        red, green, blue : numpy array

        Returns:
        --------
        numpy array
            vdvi
    """
    b1, b2, b3 = self.read_band(blue), self.read_band(green), self.read_band(red)

    # ignore warning for division by zero
    with np.errstate(divide="ignore"):
        vdvi = ((2*b2) - b3 - b1) / ((2*b2) + b3 + b1)
        # mask out invalid values
        vdvi[np.isinf(vdvi)] = np.nan
        if np.isnan(vdvi).any():
            vdvi = np.ma.masked_invalid(vdvi)

    return vdvi


def bare_soil(blue, red, nir, swir):
    """ Bare Soil Index

        Equation:
        ---------
        BSI = ((SWIR - Red) - (NIR + Blue)) / ((SWIR - Red) + (NIR + Blue))

        Parameters:
        -----------
        blue, red, nir, swir : numpy array

        Returns:
        --------
        numpy array
            BSI
    """
    b2, b4, b8, b11 = read_band(blue), read_band(red), read_band(nir), read_band(swir)
    with np.errstate(divide="ignore"):
        bsi = ((b11 - b4) - (b8 + b2)) / ((b11 - b4) + (b8 + b2))
    # mask out invalid values
    bsi[np.isinf(bsi)] = np.nan
    if np.isnan(bsi).any():
        bsi = np.ma.masked_invalid(bsi)

    return bsi


# vector operations
def get_vector_epsg(shp):
    src = ogr.Open(shp, 0)
    layer = src.GetLayer()
    srs = layer.GetSpatialRef()
    return(srs.GetAttrValue("AUTHORITY", 1))
