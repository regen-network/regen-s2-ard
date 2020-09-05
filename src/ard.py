#!/usr/bin/env python3
import os
import subprocess
from argparse import ArgumentParser
from pprint import pprint
import xml.etree.ElementTree as ET
from osgeo import gdal
from osgeo import ogr
import numpy as np
import osr
import json
import glob
from shutil import copyfile, copytree
from ruamel_yaml import YAML
import config_reader as cfg
import rasterio as rio

def system_call(params):
    fprint(" ".join(params))
    return_code = subprocess.call(params)
    if return_code:
        fprint(return_code)

def fprint(str):
    print('\t', str)

def average_images(image_dir, mosaic_dir, average_settings):

    def build_command(tiles):
        # create system command
        system_command = ["gdal_calc.py"]

        # flags for gdal_calc command
        flags = [chr(x) for x in range(ord('A'), ord('Z')+1)]
        flags = flags[:len(tiles)]

        # append flags to command
        for tile, flag in zip(tiles, flags):
            system_command.append('-' + flag)
            system_command.append(tile)

        # make output file
        tile_names = [tile.split('/')[-1] for tile in tiles]
        image_dates = [tile[11:19] for tile in tile_names if tile.startswith('S')]
        if average_settings['include-mosaic'] == True:
            image_dates = image_dates + tile_names[-1].split('_')[:-2]

        output_image = output_dir + os.sep + '_'.join(image_dates + ['average', extension])
        system_command.append("--outfile=" + output_image)

        # append calculation expression & choice flags
        system_command.append("--calc=({})/{}".format(' + '.join(flags), np.float32(len(flags))))
        system_command.append("--allBands={}".format(flags[0])) # average each band
        system_command.append("--overwrite")
        system_command.append("--quiet") # supress output messages

        return system_command


    # build image list
    tile_list = [file for file in os.listdir(image_dir)
                    if os.path.isfile(os.path.join(image_dir, file))
                    and file.endswith('.tif')]

    # filter tile list to include only images listed in config file
    filter = [image[:60] for image in average_settings['average-list']]
    tile_list = [os.path.join(image_dir, tile) for tile in tile_list
                    if tile[:60] in filter]


    # averages to generate based on extension (stacked, ndvi, etc...)
    file_extensions = list(set(tile.split('_')[-1] for tile in tile_list))
    # include images from mosaic folder
    if average_settings['include-mosaic'] == True:
        mosaic_list = [os.path.join(mosaic_dir, file) for file in os.listdir(mosaic_dir)
                            if os.path.isfile(os.path.join(mosaic_dir, file))
                            and 'mosaic' in file and file.endswith('tif')]
        tile_list = tile_list + mosaic_list

    # average images
    for extension in file_extensions:
        tiles = [tile for tile in tile_list if tile.endswith(extension)]
        system_command = build_command(tiles)
        system_call(system_command)

# processing the tile
class ProcessTile():

    def __init__(self, config_dict):

        # read in configuration settings
        self.config = config_dict
        fprint('IMAGE SETTINGS: {}'.format(self.config.ard_settings))
        fprint('CLOUD MASK SETTINGS: {}'.format(self.config.cloud_mask_settings))
        fprint('OUTPUT IMAGE SETTINGS: {}'.format(self.config.output_image_settings))

        # output-image-settings
        self.bands = self.config.output_image_settings['bands']
        self.derived_indices = self.config.output_image_settings["vi"]

        self.image_properties = {'resolution' : self.config.output_image_settings['resolution'],
                                 't_srs' : self.config.output_image_settings['t-srs'],
                                 'resampling_method' : self.config.output_image_settings['resampling-method']}

        self.input_features = self.config.output_image_settings['input-features']

        # set output dir
        self.output_dir = "/output" + os.sep + self.config.tile_name[:-5]
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)

    def process_tile(self, input_tile):
        # getting bands pathes
        tile_name = os.path.basename(input_tile)

        # input product type toa (L1C) or boa (L2A)
        producttype = tile_name[7:10]
        if producttype == 'L2A':
            all_bands = self._get_boa_band_pathes(self._get_metadata_xml(input_tile))
            ref_bands = self._subset_boa_bands(self.bands, all_bands)

        if producttype == 'L1C':
            metadata_xml = self._get_metadata_xml(input_tile)
            all_bands = self._get_toa_band_pathes(metadata_xml)
            ref_bands = self._subset_toa_bands(self.bands, all_bands)

        # ATMOSPHERIC CORRECTION - SEN2COR
        if self.config.ard_settings['atm-corr'] == True:
            fprint('RUNNING ATMOSPHERIC CORRECTION - SEN2COR')
            system_command = ['L2A_Process', "--resolution", '10', input_tile]
            system_call(system_command)

            all_bands = self._get_boa_band_pathes(self._get_metadata_xml(input_tile))
            ref_bands = self._subset_boa_bands(self.bands, all_bands)

            copytree(tile_name, self.output_dir + os.sep + os.path.split(input_tile)[1])

        # if output spatial reference is missing epsg code is tile epsg code
        if self.image_properties['t_srs'] == False:
            self.image_properties['t_srs'] = self.get_band_meta(all_bands[list(all_bands.keys())[0]])['epsg']

        # RESAMPLING TO TARGET RESOLUTION
        # resampling to target resolution if bands/image does not meet target resolution
        for key in self.bands:
            if self.get_band_meta(ref_bands[key])['geotransform'][1] != self.image_properties['resolution']:
                fprint('RESAMPLING BAND TO TARGET RESOLUTION: %s' % (key))
                resampled_image = self.rename_image(work_dir, '.tif', os.path.split(os.path.splitext(input_tile)[0])[1], key)
                ref_bands[key] = self.resample_image(ref_bands[key], resampled_image, self.image_properties)

        # DERIVING INDICES
        if self.config.ard_settings["derived-index"] == True:
            fprint('DERIVE INDEX / INDICES')
            vi_band_dict = {
                            'ndvi' : ['B08', 'B04'],
                            'ndwi' : ['B08', 'B11'],
                            'ndti' : ['B11', 'B12'],
                            'crc'  : ['B11', 'B02']
                            }

            derived_bands = {}
            for index in self.derived_indices:
                fprint((index, vi_band_dict[index]))

                if self.config.ard_settings['atm-corr'] == False:
                    if producttype == 'L1C':
                        vi_bands = self._subset_toa_bands(vi_band_dict[index], all_bands)
                        fprint(vi_bands)

                if self.config.ard_settings['atm-corr'] == True or producttype == 'L2A':
                    vi_bands = self._subset_boa_bands(vi_band_dict[index], all_bands)
                    fprint(vi_bands)

                for key in vi_bands.keys():
                    if (self.get_band_meta(vi_bands[key])['geotransform'][1] != self.config.output_image_settings['resolution']):
                        fprint('RESAMPLING BAND TO TARGET RESOLUTION: %s' % (key))
                        resampled_image = self.rename_image(work_dir, '.tif', os.path.split(os.path.splitext(input_tile)[0])[1], key)
                        vi_bands[key] = self.resample_image(vi_bands[key], resampled_image, self.image_properties)

                # write index
                band_meta = self.get_band_meta(vi_bands[key])
                band_meta['dtype'] = 6
                derived_index = self.normalized_diff(vi_bands[vi_band_dict[index][0]], vi_bands[vi_band_dict[index][1]])
                derived_index_image = self.rename_image(work_dir, '.tif', os.path.splitext(os.path.split(input_tile)[1])[0], index)

                self.write_image(derived_index_image, "GTiff", band_meta, [derived_index])

                derived_bands[index] = derived_index_image

        # SEN2COR CLOUD MASKING ONLY
        if (self.config.ard_settings['cloud-mask'] == True) and (self.config.cloud_mask_settings['sen2cor-scl-codes']):

            if (self.config.ard_settings['atm-corr'] == False) and (producttype == 'L1C'):
                # running sen2cor scene classification only
                fprint('RUNNING SEN2COR SCENE CLASSIFICATION ONLY')
                system_command = ['L2A_Process', "--sc_only", input_tile]
                system_call(system_command)

            scl_image = '.'.join([self._get_boa_band_pathes(self._get_metadata_xml(input_tile))['SCL_20m']])
            # resampling to target resolution if bands/image does not meet target resolution
            if self.get_band_meta(scl_image)['geotransform'][1] != self.image_properties['resolution']:
                # changing resampling to near since cloud mask image contains discrete values
                _image_properties = self.image_properties.copy()
                _image_properties["resampling_method"] = "near"

                resampled_image = self.rename_image(work_dir, '.tif', os.path.split(os.path.splitext(scl_image)[0])[1], 'resampled')
                scl_image = self.resample_image(scl_image, resampled_image, _image_properties)

            mask = self.binary_mask(self.read_band(scl_image), self.config.cloud_mask_settings['sen2cor-scl-codes'])

            # apply scl_image as mask to ref images
            fprint('APPLYING SEN2COR SCENE CLASSIFICATION MASK TO REF BANDS')
            for key in self.bands:
                band_meta = self.get_band_meta(ref_bands[key])
                masked_array = self.mask_array(mask, self.read_band(ref_bands[key]))
                masked_image = self.rename_image(work_dir, '.tif', os.path.splitext(os.path.basename(ref_bands[key]))[0], 'scl', 'masked')

                self.write_image(masked_image, "GTiff", band_meta, [masked_array])
                ref_bands[key] = masked_image

            # apply scl_image as mask to index images
            fprint('APPLYING SEN2COR SCENE CLASSIFICATION MASK TO INDICES')
            if self.derived_indices != False:
                for key in self.derived_indices:
                    band_meta = self.get_band_meta(derived_bands[key])
                    masked_array = self.mask_array(mask, self.read_band(derived_bands[key]))
                    masked_image = self.rename_image(work_dir, '.tif', os.path.splitext(os.path.basename(derived_bands[key]))[0], 'scl', 'masked')

                    self.write_image(masked_image, "GTiff", band_meta, [masked_array])
                    derived_bands[key] = masked_image

        # FMASK CLOUD MASKING
        if (self.config.ard_settings['cloud-mask'] == True) and (self.config.cloud_mask_settings['fmask-codes']) and (producttype == 'L1C'):
            fprint('RUNNING FMASK CLOUD MASK')
            # running fmask cloud masking
            fmask_image = work_dir + os.sep + '_'.join([os.path.splitext(os.path.split(input_tile)[1])[0], 'FMASK']) + '.tif'
            system_command = ['fmask_sentinel2Stacked.py', '-o', fmask_image, '--safedir', input_tile]
            system_call(system_command)

            # copying fmask image to output dir
            output_image = self.rename_image(self.output_dir, '.tif', os.path.split(os.path.splitext(fmask_image)[0])[1])
            copyfile(fmask_image, output_image)

            # resampling to target resolution if bands/image does not meet target resolution
            if self.get_band_meta(fmask_image)['geotransform'][1] != self.image_properties['resolution']:
                # changing resampling to near since cloud mask image contains discrete values
                _image_properties = self.image_properties.copy()
                _image_properties["resampling_method"] = "near"
                fmask_image = self.resample_image(fmask_image, 'resampled', _image_properties)

            # applying fmask as mask to ref images
            fprint('APPLYING FMASK CLOUD MASK')
            mask = self.binary_mask(self.read_band(fmask_image), self.config.cloud_mask_settings['fmask-codes'])
            for key in self.bands:
                band_meta = self.get_band_meta(ref_bands[key])
                masked_array = self.mask_array(mask, self.read_band(ref_bands[key]))
                masked_image = self.rename_image(work_dir, '.tif', os.path.splitext(os.path.basename(ref_bands[key]))[0], 'fmask', 'masked')
                self.write_image(masked_image, "GTiff", band_meta, [masked_array])
                ref_bands[key] = masked_image

            # apply fmask as mask to index images
            fprint('APPLYING FMASK CLOUD MASK TO INDICES')
            if self.derived_indices != False:
                for key in self.derived_indices:
                    band_meta = self.get_band_meta(derived_bands[key])
                    masked_array = self.mask_array(mask, self.read_band(derived_bands[key]))
                    masked_image = self.rename_image(work_dir, '.tif', os.path.splitext(os.path.basename(derived_bands[key]))[0], 'fmask', 'masked')
                    self.write_image(masked_image, "GTiff", band_meta, [masked_array])
                    derived_bands[key] = masked_image

        # CALIBRATION
        if self.config.ard_settings['calibrate'] == True:
            fprint('CALIBRATING BANDS')
            for key in self.bands:
                fprint('CALIBRATING BAND %s' % (key))
                ref_bands[key] = self.calibrate('.'.join([ref_bands[key]]))

        # REPROJECTION
        # ref images
        for key in ref_bands:
            if self.get_band_meta(ref_bands[key])['epsg'] != str(self.image_properties['t_srs']):
                fprint('REPROJECTING BAND %s' % (key))
                ref_bands[key] = self.warp_image(ref_bands[key], 'resampled', self.image_properties)

        # index images
        if self.config.ard_settings["derived-index"] == True:
            for key in derived_bands:
                if self.get_band_meta(derived_bands[key])['epsg'] != str(self.image_properties['t_srs']):
                    fprint('REPROJECTING BAND %s' % (key))
                    derived_bands[key] = self.warp_image(derived_bands[key], 'resampled', self.image_properties)

        # STACKING
        # onyl ref images
        if self.config.ard_settings['stack'] == True:
            fprint('STACKING BANDS')
            arrays = []
            if len(self.bands) > 1:
                for key in self.bands:
                    fprint('STACKING BAND %s' % (key))
                    band_meta = self.get_band_meta(ref_bands[key])
                    arrays.append(self.read_band(ref_bands[key]))
                stacked_image = self.rename_image(work_dir, '.tif', os.path.splitext(os.path.split(input_tile)[1])[0], 'stacked')
                self.write_image(stacked_image, "GTiff", band_meta, arrays)

                ref_bands = {}
                ref_bands['stacked'] = stacked_image

        # add ref images dict + index images dict and loop
        if self.config.ard_settings["derived-index"] == True:
            ref_bands.update(derived_bands)

        # copying output images to /output directory
        for key in ref_bands.keys():
            output_image = self.rename_image(self.output_dir, '.tif', os.path.split(os.path.splitext(tile_name)[0])[1], key)
            copyfile(ref_bands[key], output_image)

        # CLIPPING / CROP_TO_CUTLINE
        if self.config.ard_settings['clip'] == True:
            self.crop_to_cutline(self.output_dir, self.input_features)

    # metadata xml and parsing operations
    def _get_l2a_name(self, input_tile):
        for safe in os.listdir(work_dir):
            tile_name = work_dir + os.sep + safe
            if os.path.isdir(tile_name) and (os.path.split(tile_name)[1][7:10] == 'L2A'):
                return(tile_name)

    def _get_metadata_xml(self, input_tile):
        for i in os.listdir(input_tile):
            if (os.path.splitext(i)[1] == '.xml') and ('MTD' in i):
                metadata_xml = input_tile + os.sep + i
        return(metadata_xml)

    def _get_boa_band_pathes(self, metadata_xml):
        band_pathes = {}
        root = ET.parse(metadata_xml)
        product = root.findall('.//Product_Organisation/Granule_List/Granule')
        for res_dir in product:
            for band in res_dir.findall('IMAGE_FILE'):
                #if band.text[-7:-4] in self.bands:
                band_pathes[band.text[-7:]] = os.path.split(metadata_xml)[0] + os.sep + band.text + '.jp2'
        return(band_pathes)

    def _get_toa_band_pathes(self, metadata_xml):
        band_pathes = {}
        root = ET.parse(metadata_xml)
        product = root.findall('.//Product_Organisation/Granule_List/Granule')
        for res_dir in product:
            for band in res_dir.findall('IMAGE_FILE'):
                #if band.text[-3:] in self.bands:
                band_pathes[band.text[-3:]] = os.path.split(metadata_xml)[0] + os.sep + band.text + '.jp2'
        return(band_pathes)

    def _subset_boa_bands(self, subset_bands, band_pathes):
        subset_band_pathes = {}
        for band in subset_bands:
            key = '_'.join([band, '10m'])
            if key in band_pathes.keys():
                subset_band_pathes[key[:3]] = band_pathes[key]
            if key not in band_pathes.keys():
                key = '_'.join([band, '20m'])
                subset_band_pathes[key[:3]] = band_pathes[key]
        return(subset_band_pathes)

    def _subset_toa_bands(self, subset_bands, all_bands):
        ref_bands = {}
        for key in all_bands.keys():
            if key in subset_bands:
                ref_bands[key] = all_bands[key]
        return(ref_bands)

    def _get_raster_epsg(self, input_raster):
        src = gdal.Open(input_raster)
        proj = osr.SpatialReference(wkt=src.GetProjection())
        return(proj.GetAttrValue('AUTHORITY',1))

    def rename_image(self, basedir, extension, *argv):
        new_name = basedir + os.sep + "_".join(argv) + extension
        return(new_name)

    # raster operations
    def resample_image(self, image, resampled_image, img_prop):
        fprint('Resolution does not meet target_resolution, resampling %s' % (image))
        system_command = ['gdal_translate', "-tr", str(img_prop['resolution']), str(img_prop['resolution']), '-r', str(img_prop['resampling_method']), image, resampled_image]
        system_call(system_command)
        return(resampled_image)

    def warp_image(self, image, suffix, img_prop):
        warped_image = work_dir + os.sep + '_'.join([os.path.splitext(os.path.basename(image))[0], suffix, str(img_prop['resolution']), img_prop['resampling_method'], str(img_prop['t_srs'])]) + '.tif'
        system_command = ['gdalwarp', "-tr", str(img_prop['resolution']), str(img_prop['resolution']), '-t_srs', 'EPSG:' + str(img_prop['t_srs']),'-r', img_prop['resampling_method'], image, warped_image, '-overwrite']
        system_call(system_command)
        return(warped_image)

    def calibrate(self, band_path):
        calibrated_band = work_dir + os.sep + os.path.split(os.path.splitext(band_path)[0])[1] + '.tif'
        band_meta = self.get_band_meta(band_path)
        src = gdal.Open(band_path)
        scale_factor = 10000.
        dst = src.GetRasterBand(1).ReadAsArray() / scale_factor
        band_meta['dtype'] = 6
        self.write_image(calibrated_band, 'GTiff', band_meta, [dst])
        return(calibrated_band)

    def read_band(self, band_path):
        src = gdal.Open(band_path)
        return(src.GetRasterBand(1).ReadAsArray())

    # reads whole image as opposed to a single band
    def read_image(self, img):
        print('reading: ', img)
        with rio.open(img) as src:
            return(src.read())

    def get_band_arrays(self, bands):
        band_arrays = []
        for band in bands:
            band_arrays.append(self.read_band(band))
        return(band_arrays)

    def get_band_meta(self, img_file):
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

    def binary_mask(self, scl, pixel_values):
        mask = np.zeros(scl.shape)
        for pixel_value in pixel_values:
            mask = np.ma.masked_where(scl == pixel_value, mask).filled(1)
        return(mask)

    def mask_array(self, mask, array):
        return(np.ma.masked_where(mask == 0, array).filled(0))

    def normalized_diff(self, b1, b2):

        np.seterr(divide='ignore', invalid='ignore')

        b1, b2 = self.read_band(b1) / float(10000), self.read_band(b2) / float(10000)

        if not (b1.shape == b2.shape):
            raise ValueError("Both arrays should have the same dimensions")

        # Ignore warning for division by zero
        with np.errstate(divide="ignore"):
            n_diff = (b1 - b2) / (b1 + b2).astype(np.float32)

        # Set inf values to nan and provide custom warning
        if np.isinf(n_diff).any():
            warnings.warn(
                "Divide by zero produced infinity values that will be replaced "
                "with nan values",
                Warning,
            )
            n_diff[np.isinf(n_diff)] = np.nan

        # Mask invalid values
        if np.isnan(n_diff).any():
            n_diff = np.ma.masked_invalid(n_diff)

        return n_diff

    def write_image(self, out_name, driver, band_meta, arrays):
        fprint('WRITING IMAGE: ' + out_name)
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

    def build_mosaic(self, image_dir, mosaic_settings):
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
            mosaic_bands = [x for _,x in sorted(zip(mosaic_settings['image-list'], to_mosaic))]
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
                except:
                    print('unable to remove: ', file)

    def crop_to_cutline(self, image_dir, input_features):
        fprint('CROPPING TO CUTLINE')

        # generate image list & get src epsg
        image_list = glob.glob(os.path.join(image_dir, '*.tif'))
        t_srs = self._get_raster_epsg(image_list[0])
        features_epsg = self.get_vector_epsg(input_features)
        # reprojecting input_features to target_srs if not common projection
        if features_epsg != t_srs:
            fprint('REPROJECTING INPUT FEATURES TO TARGET PROJECTION')
            t_srs_feature_aoi = work_dir + os.sep + "_".join([os.path.splitext(os.path.split(input_features)[1])[0], t_srs]) + '.geojson'
            system_command = ['ogr2ogr', "-overwrite", "-t_srs", 'EPSG:' + t_srs, t_srs_feature_aoi, input_features]
            system_call(system_command)
            input_features = t_srs_feature_aoi

        src = ogr.Open(input_features, 0)
        layer = src.GetLayer()
        count = layer.GetFeatureCount()
        for feature in layer:
            feature_id = feature.GetFID()
            feature_shp = work_dir + os.sep + '_'.join([os.path.splitext(os.path.split(input_features)[1])[0], 'FEATURE_ID', str(feature_id)]) + '.geojson'
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
                system_command = ['gdalwarp', "-cutline", feature_shp, '-crop_to_cutline', image, image_chip, '-overwrite']
                system_call(system_command)

    def compute_average(self, image_dir, mosaic_dir, average_settings):

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

        # include images from mosaic folder
        if average_settings['include-mosaic'] == True:
            mosaic_list = [os.path.join(mosaic_dir, file) for file in os.listdir(mosaic_dir)
                                if os.path.isfile(os.path.join(mosaic_dir, file))
                                and 'mosaic' in file and file.endswith('tif')]
            tile_list = tile_list + mosaic_list
            image_dates = image_dates + mosaic_list[0].split('/')[-1].split('_')[:-2]

        output_dir = "/output/average"

        for extension in file_extensions:
            # build image list from extension
            tiles = [tile for tile in tile_list if tile.endswith(extension)]
            # read in images
            array_list = [self.read_image(x) for x in tiles]
            try:
                with np.errstate(all='raise'):
                    array_mean = np.nanmean(array_list,axis=0)
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

    # vector operations
    def get_vector_epsg(self, shp):
        src = ogr.Open(shp, 0)
        layer = src.GetLayer()
        srs = layer.GetSpatialRef()
        return(srs.GetAttrValue("AUTHORITY", 1))


if __name__ == "__main__":
    # parse command line arguments
    desc = "Sentinel-2 Analysis Ready Data"
    parser = ArgumentParser(description=desc)
    parser.add_argument("--tiles", "-t", type=str, dest='tiles', help="Sentinel-2 data product name", required=True)
    args = parser.parse_args()

    # data dir
    data_dir = args.tiles

    # tiles
    tile_list = os.listdir(data_dir)

    # yaml
    config_file = os.path.dirname(os.path.realpath(__file__)) + os.sep + 'config.yml'

    # geojson
    aoi_file = os.path.dirname(os.path.realpath(__file__)) + os.sep + 'aoi.geojson'

    # extract image metadata
    ard_settings = cfg.ConfigReader(config_file, aoi_file)

    # working directories
    work_dir    = "/work"
    output_dir  = "/output"
    mosaic_dir  = "/output/mosaic"
    average_dir = "/output/average"

    # process tiles

    for image_config in ard_settings.image_list:
        input_tile = data_dir + os.sep + image_config.tile_name
        if os.path.isdir(input_tile) == True:
            print('\n----------------------------------------------------------------------\n')
            print('PROCESSING IMAGE: {}\n'.format(image_config.tile_name))
            pg = ProcessTile(image_config)
            pg.process_tile(input_tile)
        else:
            print('Unable to process tile:', image_config.tile_name)

    # mosaic images
    if ard_settings.mosaic_settings['build-mosaic'] == True:
        print('\n----------------------------------------------------------------------\n')
        print("BUILDING TILE MOSAIC...")
        if not os.path.exists(mosaic_dir):
            os.mkdir(mosaic_dir)
        pg.build_mosaic(output_dir, ard_settings.mosaic_settings)
        # clip image chips
        if ard_settings.mosaic_settings['clip'] == True:
            pg.crop_to_cutline(mosaic_dir, aoi_file)

    # average images
    if ard_settings.average_settings['compute-average'] == True:
        print('\n----------------------------------------------------------------------\n')
        print("AVERAGING IMAGES...")
        if not os.path.exists(average_dir):
            os.mkdir(average_dir)
        pg.compute_average(output_dir, mosaic_dir, ard_settings.average_settings)
        # crop to cutline
        if ard_settings.average_settings['clip'] == True:
            pg.crop_to_cutline(average_dir, aoi_file)
