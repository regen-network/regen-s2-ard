#!/usr/bin/env python3
import os
import subprocess
import numpy as np
np.seterr(divide='ignore', invalid='ignore')
from osgeo import gdal
from osgeo import ogr
import osr
import glob
import shutil


def system_call(params):
    print(" ".join(params))
    return_code = subprocess.call(params)
    if return_code:
        print(return_code)


# raster operations
def crop_to_cutline(image_dir, input_features):
    """ Crops directory of rasters to shapefile

        Parameters
        ----------
        image_dir : str
            path to directory containing input rasters
        input_features : str
            full path to input feature (shapefile / geojson / geopackage)
    """

    print('CROPPING TO CUTLINE')
    # generate image list & get src epsg
    image_list = glob.glob(os.path.join(image_dir, '*.tif'))
    t_srs = get_raster_epsg(image_list[0])
    features_epsg = get_vector_epsg(input_features)
    # reprojecting input_features to target_srs if not common projection
    if features_epsg != t_srs:
        print('REPROJECTING INPUT FEATURES TO TARGET PROJECTION')
        t_srs_feature_aoi = image_dir + os.sep + "_".join([os.path.splitext(os.path.split(input_features)[1])[0], t_srs]) + '.geojson'
        system_command = ['ogr2ogr', "-overwrite", "-t_srs", 'EPSG:' + t_srs, t_srs_feature_aoi, input_features]
        system_call(system_command)
        input_features = t_srs_feature_aoi

    src = ogr.Open(input_features, 0)
    layer = src.GetLayer()
    count = layer.GetFeatureCount()
    for feature in layer:
        feature_id = feature.GetFID()
        feature_shp = image_dir + os.sep + '_'.join([os.path.splitext(os.path.split(input_features)[1])[0], 'FEATURE_ID', str(feature_id)])
        if not os.path.exists(feature_shp):
            ftr_drv = ogr.GetDriverByName('Esri Shapefile')
            out_feature = ftr_drv.CreateDataSource(feature_shp)
            lyr = out_feature.CreateLayer('poly', layer.GetSpatialRef(), ogr.wkbPolygon)
            feat = lyr.CreateFeature(feature.Clone())
            out_feature = None

        # cropping reflectance band image chips
        for image in image_list:
            subdir = image_dir + os.sep + 'clipped'
            if not os.path.exists(subdir):
                os.mkdir(subdir)
            if count == 1:
                image_chip = subdir + os.sep + '_'.join([os.path.split(os.path.splitext(image)[0])[1], 'clipped']) + '.tif'
            if count > 1:
                image_chip = subdir + os.sep + '_'.join([os.path.split(os.path.splitext(image)[0])[1], 'FEATURE_ID', str(feature_id), 'clipped']) + '.tif'
            # cropping to cutline bands
            crop_image(image, image_chip, feature_shp)
    src = None

    # cleanup
    for file in os.listdir(image_dir):
        if file.endswith('.geojson'):
            try:
                shutil.rmtree(image_dir + os.sep + file)
            except Exception:
                print('unable to remove: ', image_dir + os.sep + file)


def crop_image(input_image, output_image, feature_shp):
    system_command = ['gdalwarp', "-cutline", feature_shp, '-crop_to_cutline', input_image, output_image, '-overwrite']
    system_call(system_command)


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


def read_band(band_path, band_num=1):
    src = gdal.Open(band_path)
    return(src.GetRasterBand(band_num).ReadAsArray())


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


def vdvi(blue, green, red):
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
    b1, b2, b3 = read_band(blue), read_band(green), read_band(red)

    # ignore warning for division by zero
    with np.errstate(divide="ignore"):
        vdvi = ((2*b2) - b3 - b1) / ((2*b2) + b3 + b1).astype(np.float32)
        # mask out invalid values
        vdvi[np.isinf(vdvi)] = np.nan
        if np.isnan(vdvi).any():
            vdvi = np.ma.masked_invalid(vdvi)

    return vdvi


def bare_soil(blue, red, nir, swir):
    """ Bare Soil Index

        Equation:
        ---------
        BSI = ((SWIR + Red) - (NIR + Blue)) / ((SWIR + Red) + (NIR + Blue))

        Parameters:
        -----------
        blue, red, nir, swir : numpy array

        Returns:
        --------
        numpy array
            BSI
    """
    b2, b4, b8, b11 = read_band(blue) / float(10000), read_band(red) / float(10000), read_band(nir) / float(10000), read_band(swir) / float(10000)
    if not (b2.shape == b4.shape == b8.shape == b11.shape):
        raise ValueError("Both arrays should have the same dimensions")

    # Ignore warning for division by zero
    with np.errstate(divide="ignore"):
        bsi = ((b11 + b4) - (b8 + b2)) / ((b11 + b4) + (b8 + b2)).astype(np.float32)
        # mask out invalid values
        bsi[np.isinf(bsi)] = np.nan
        if np.isnan(bsi).any():
            bsi = np.ma.masked_invalid(bsi)

    return bsi

def bsi_2(blue, red, nir, swir):
    """ (New?) Bare Soil Index (https://medium.com/sentinel-hub/area-monitoring-bare-soil-marker-608bc95712ae)

        Equation:
        ---------
        BSI2 = (SWIR - Red) / (NIR + Blue)

        Parameters:
        -----------
        blue, red, nir, swir : numpy array

        Returns:
        --------
        numpy array
            BSI2
    """


    blue_arr, red_arr, nir_arr, swir_arr = read_band(blue), read_band(red), read_band(nir), read_band(swir)
    with np.errstate(divide="ignore"):
        bsi_2 = ((swir_arr - red_arr) / (nir_arr + blue_arr))

    bsi_2[np.isinf(bsi_2)] = np.nan
    if np.isnan(bsi_2).any():
        bsi_2 = np.ma.masked_invalid(bsi_2)

    return bsi_2


# vector operations
def get_vector_epsg(shp):
    src = ogr.Open(shp, 0)
    layer = src.GetLayer()
    srs = layer.GetSpatialRef()
    return(srs.GetAttrValue("AUTHORITY", 1))
