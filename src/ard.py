#!/usr/bin/env python3
import os
import subprocess
from argparse import ArgumentParser
import xml.etree.ElementTree as ET
from osgeo import gdal
from osgeo import ogr
import numpy as np
import osr
import glob
from shutil import copyfile, copytree
import config_reader as cfg
import raster_mod as rm


def system_call(params):
    print(" ".join(params))
    return_code = subprocess.call(params)
    if return_code:
        print(return_code)

# processing the tile
class ProcessTile():

    def __init__(self, config_dict):

        # read in configuration settings
        self.config = config_dict
        print('IMAGE SETTINGS: {}'.format(self.config.ard_settings))
        print('CLOUD MASK SETTINGS: {}'.format(self.config.cloud_mask_settings))
        print('OUTPUT IMAGE SETTINGS: {}'.format(self.config.output_image_settings))

        # output-image-settings
        self.tile_name = self.config.tile_name
        self.bands = self.config.output_image_settings['bands']
        self.derived_indices = self.config.output_image_settings["vi"]

        self.image_properties = {'resolution': self.config.output_image_settings['resolution'],
                                 't_srs': self.config.output_image_settings['t-srs'],
                                 'resampling_method': self.config.output_image_settings['resampling-method']}

        self.input_features = self.config.output_image_settings['input-features']

        # set output dir
        self.output_dir = "/output"

    def process_tile(self, input_tile):

        # input product type toa (L1C) or boa (L2A)
        producttype = self.tile_name[7:10]
        if producttype == 'L2A':
            all_bands = self._get_boa_band_pathes(self._get_metadata_xml(input_tile))
            ref_bands = self._subset_boa_bands(self.bands, all_bands)

        if producttype == 'L1C':
            metadata_xml = self._get_metadata_xml(input_tile)
            all_bands = self._get_toa_band_pathes(metadata_xml)
            ref_bands = self._subset_toa_bands(self.bands, all_bands)

        # ATMOSPHERIC CORRECTION - SEN2COR
        if self.config.ard_settings['atm-corr'] == True:
            print('RUNNING ATMOSPHERIC CORRECTION - SEN2COR')
            system_command = ['L2A_Process', "--resolution", '10', input_tile]
            rm.system_call(system_command)

            self.tile_name = self._get_l2a_name(self.tile_name)
            all_bands = self._get_boa_band_pathes(self._get_metadata_xml(input_tile))
            ref_bands = self._subset_boa_bands(self.bands, all_bands)

            copytree(self.tile_name, self.output_dir + os.sep + os.path.split(input_tile)[1])

        # SET OUTPUT DIRECTORY - happens after atm_corr in case of tile renaming (L1C -> L2A)
        self.output_dir = self.output_dir + os.sep + os.path.split(self.tile_name)[1][:-5]
        if not os.path.exists(self.output_dir):
            os.mkdirs(self.output_dir)

        # if output spatial reference is missing epsg code is tile epsg code
        if self.image_properties['t_srs'] == False:
            self.image_properties['t_srs'] = rm.get_band_meta(all_bands[list(all_bands.keys())[0]])['epsg']

        # RESAMPLING TO TARGET RESOLUTION
        # resampling to target resolution if bands/image does not meet target resolution
        for key in self.bands:
            if rm.get_band_meta(ref_bands[key])['geotransform'][1] != self.image_properties['resolution']:
                print('RESAMPLING BAND TO TARGET RESOLUTION: %s' % (key))
                resampled_image = self.rename_image(work_dir, '.tif', os.path.split(os.path.splitext(input_tile)[0])[1], key)
                ref_bands[key] = rm.resample_image(ref_bands[key], resampled_image, self.image_properties)

        # DERIVING INDICES
        if self.config.ard_settings["derived-index"] == True:
            print('DERIVE INDEX / INDICES')
            vi_band_dict = {
                            'ndvi': ['B08', 'B04'],
                            'ndwi': ['B08', 'B11'],
                            'ndti': ['B11', 'B12'],
                            'crc': ['B11', 'B02'],
                            'vdvi': ['B02', 'B03', 'B04'],
                            'bsi': ['B02', 'B04', 'B08', 'B11']
                            }

            derived_bands = {}
            for index in self.derived_indices:
                print((index, vi_band_dict[index]))

                if self.config.ard_settings['atm-corr'] == False:
                    if producttype == 'L1C':
                        vi_bands = self._subset_toa_bands(vi_band_dict[index], all_bands)
                        print(vi_bands)

                if self.config.ard_settings['atm-corr'] == True or producttype == 'L2A':
                    vi_bands = self._subset_boa_bands(vi_band_dict[index], all_bands)
                    print(vi_bands)

                for key in vi_bands.keys():
                    if (rm.get_band_meta(vi_bands[key])['geotransform'][1] != self.config.output_image_settings['resolution']):
                        print('RESAMPLING BAND TO TARGET RESOLUTION: %s' % (key))
                        resampled_image = self.rename_image(work_dir, '.tif', os.path.split(os.path.splitext(input_tile)[0])[1], key)
                        vi_bands[key] = rm.resample_image(vi_bands[key], resampled_image, self.image_properties)

                # write index
                band_meta = rm.get_band_meta(vi_bands[key])
                band_meta['dtype'] = 6
                if index == 'vdvi':
                    derived_index = rm.calculate_vdvi(vi_bands[vi_band_dict[index][0]], vi_bands[vi_band_dict[index][1]], vi_bands[vi_band_dict[index][2]])
                elif index == 'bsi':
                    derived_index = rm.calculate_bsi(vi_bands[vi_band_dict[index][0]], vi_bands[vi_band_dict[index][1]], vi_bands[vi_band_dict[index][2]], vi_bands[vi_band_dict[index][3]])
                else:
                    derived_index = rm.normalized_diff(vi_bands[vi_band_dict[index][0]], vi_bands[vi_band_dict[index][1]])
                derived_index_image = self.rename_image(work_dir, '.tif', os.path.splitext(os.path.split(input_tile)[1])[0], index)

                rm.write_image(derived_index_image, "GTiff", band_meta, [derived_index])

                derived_bands[index] = derived_index_image

        # SEN2COR CLOUD MASKING ONLY
        if (self.config.ard_settings['cloud-mask'] == True) and (self.config.cloud_mask_settings['sen2cor-scl-codes']):

            if (self.config.ard_settings['atm-corr'] == False) and (producttype == 'L1C'):
                # running sen2cor scene classification only
                print('RUNNING SEN2COR SCENE CLASSIFICATION ONLY')
                system_command = ['L2A_Process', "--sc_only", input_tile]
                system_call(system_command)

            scl_image = '.'.join([self._get_boa_band_pathes(self._get_metadata_xml(input_tile))['SCL_20m']])
            # resampling to target resolution if bands/image does not meet target resolution
            if rm.get_band_meta(scl_image)['geotransform'][1] != self.image_properties['resolution']:
                # changing resampling to near since cloud mask image contains discrete values
                _image_properties = self.image_properties.copy()
                _image_properties["resampling_method"] = "near"

                resampled_image = self.rename_image(work_dir, '.tif', os.path.split(os.path.splitext(scl_image)[0])[1], 'resampled')
                scl_image = rm.resample_image(scl_image, resampled_image, _image_properties)

            mask = rm.binary_mask(rm.read_band(scl_image), self.config.cloud_mask_settings['sen2cor-scl-codes'])

            # apply scl_image as mask to ref images
            print('APPLYING SEN2COR SCENE CLASSIFICATION MASK TO REF BANDS')
            for key in self.bands:
                band_meta = rm.get_band_meta(ref_bands[key])
                masked_array = rm.mask_array(mask, rm.read_band(ref_bands[key]))
                masked_image = self.rename_image(work_dir, '.tif', os.path.splitext(os.path.basename(ref_bands[key]))[0], 'scl', 'masked')

                rm.write_image(masked_image, "GTiff", band_meta, [masked_array])
                ref_bands[key] = masked_image

            # apply scl_image as mask to index images
            print('APPLYING SEN2COR SCENE CLASSIFICATION MASK TO INDICES')
            if self.derived_indices != False:
                for key in self.derived_indices:
                    band_meta = rm.get_band_meta(derived_bands[key])
                    masked_array = rm.mask_array(mask, self.read_band(derived_bands[key]))
                    masked_image = self.rename_image(work_dir, '.tif', os.path.splitext(os.path.basename(derived_bands[key]))[0], 'scl', 'masked')

                    rm.write_image(masked_image, "GTiff", band_meta, [masked_array])
                    derived_bands[key] = masked_image

        # FMASK CLOUD MASKING
        if (self.config.ard_settings['cloud-mask'] == True) and (self.config.cloud_mask_settings['fmask-codes']) and (producttype == 'L1C'):
            print('RUNNING FMASK CLOUD MASK')
            # running fmask cloud masking
            fmask_image = work_dir + os.sep + '_'.join([os.path.splitext(os.path.split(input_tile)[1])[0], 'FMASK']) + '.tif'
            system_command = ['fmask_sentinel2Stacked.py', '-o', fmask_image, '--safedir', input_tile]
            system_call(system_command)

            # copying fmask image to output dir
            output_image = self.rename_image(self.output_dir, '.tif', os.path.split(os.path.splitext(fmask_image)[0])[1])
            copyfile(fmask_image, output_image)

            # resampling to target resolution if bands/image does not meet target resolution
            if rm.get_band_meta(fmask_image)['geotransform'][1] != self.image_properties['resolution']:
                # changing resampling to near since cloud mask image contains discrete values
                _image_properties = self.image_properties.copy()
                _image_properties["resampling_method"] = "near"
                fmask_image = rm.resample_image(fmask_image, 'resampled', _image_properties)

            # applying fmask as mask to ref images
            print('APPLYING FMASK CLOUD MASK')
            mask = rm.binary_mask(rm.read_band(fmask_image), self.config.cloud_mask_settings['fmask-codes'])
            for key in self.bands:
                band_meta = rm.get_band_meta(ref_bands[key])
                masked_array = rm.mask_array(mask, rm.read_band(ref_bands[key]))
                masked_image = self.rename_image(work_dir, '.tif', os.path.splitext(os.path.basename(ref_bands[key]))[0], 'fmask', 'masked')
                rm.write_image(masked_image, "GTiff", band_meta, [masked_array])
                ref_bands[key] = masked_image

            # apply fmask as mask to index images
            print('APPLYING FMASK CLOUD MASK TO INDICES')
            if self.derived_indices != False:
                for key in self.derived_indices:
                    band_meta = rm.get_band_meta(derived_bands[key])
                    masked_array = rm.mask_array(mask, rm.read_band(derived_bands[key]))
                    masked_image = self.rename_image(work_dir, '.tif', os.path.splitext(os.path.basename(derived_bands[key]))[0], 'fmask', 'masked')
                    rm.write_image(masked_image, "GTiff", band_meta, [masked_array])
                    derived_bands[key] = masked_image

        # CALIBRATION
        if self.config.ard_settings['calibrate'] == True:
            print('CALIBRATING BANDS')
            for key in self.bands:
                print('CALIBRATING BAND %s' % (key))
                ref_bands[key] = self.calibrate('.'.join([ref_bands[key]]))

        # REPROJECTION
        # ref images
        for key in ref_bands:
            if rm.get_band_meta(ref_bands[key])['epsg'] != str(self.image_properties['t_srs']):
                print('REPROJECTING BAND %s' % (key))
                warped_image = work_dir + os.sep + '_'.join([os.path.splitext(os.path.basename(ref_bands[key]))[0], '.tif', str(self.image_properties['resolution']), self.image_properties['resampling_method'], str(self.image_properties['t_srs'])])
                ref_bands[key] = rm.warp_image(ref_bands[key], 'resampled', self.image_properties)

        # index images
        if self.config.ard_settings["derived-index"] == True:
            for key in derived_bands:
                if rm.get_band_meta(derived_bands[key])['epsg'] != str(self.image_properties['t_srs']):
                    print('REPROJECTING BAND %s' % (key))
                    warped_image = self.rename_image(work_dir, '.tif', os.path.split(os.path.basename(derived_bands[key]))[0], 'resampled', str(self.image_properties['resolution']), self.image_properties['resampling_method'], str(self.image_properties['t_srs']))
                    derived_bands[key] = rm.warp_image(derived_bands[key], warped_image, self.image_properties)

        # STACKING
        # onyl ref images
        if self.config.ard_settings['stack'] == True:
            print('STACKING BANDS')
            arrays = []
            if len(self.bands) > 1:
                for key in self.bands:
                    print('STACKING BAND %s' % (key))
                    band_meta = rm.get_band_meta(ref_bands[key])
                    arrays.append(rm.read_band(ref_bands[key]))
                stacked_image = self.rename_image(work_dir, '.tif', os.path.splitext(os.path.split(input_tile)[1])[0], 'stacked')
                rm.write_image(stacked_image, "GTiff", band_meta, arrays)

                ref_bands = {}
                ref_bands['stacked'] = stacked_image

        # add ref images dict + index images dict and loop
        if self.config.ard_settings["derived-index"] == True:
            ref_bands.update(derived_bands)

        # copying output images to /output directory
        for key in ref_bands.keys():
            output_image = self.rename_image(self.output_dir, '.tif', os.path.split(os.path.splitext(self.tile_name)[0])[1], key)
            copyfile(ref_bands[key], output_image)

        # CLIPPING / CROP_TO_CUTLINE
        if self.config.ard_settings['clip'] == True:
            self.crop_to_cutline(self.output_dir, self.input_features)

    # metadata xml and parsing operations
    def _get_l2a_name(self, input_tile):
        for safe in os.listdir(data_dir):
            tile_name = data_dir + os.sep + safe
            if os.path.isdir(tile_name) and (os.path.split(tile_name)[1][7:10] == 'L2A') and (os.path.split(tile_name)[1][11:26] == input_tile[11:26]):
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
                band_pathes[band.text[-7:]] = os.path.split(metadata_xml)[0] + os.sep + band.text + '.jp2'
        return(band_pathes)

    def _get_toa_band_pathes(self, metadata_xml):
        band_pathes = {}
        root = ET.parse(metadata_xml)
        product = root.findall('.//Product_Organisation/Granule_List/Granule')
        for res_dir in product:
            for band in res_dir.findall('IMAGE_FILE'):
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

    def rename_image(self, basedir, extension, *argv):
        new_name = basedir + os.sep + "_".join(argv) + extension
        return(new_name)

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

    def calibrate(self, band_path):
        calibrated_band = work_dir + os.sep + os.path.split(os.path.splitext(band_path)[0])[1] + '.tif'
        band_meta = rm.get_band_meta(band_path)
        src = gdal.Open(band_path)
        scale_factor = 10000.
        dst = src.GetRasterBand(1).ReadAsArray() / scale_factor
        band_meta['dtype'] = 6
        self.write_image(calibrated_band, 'GTiff', band_meta, [dst])
        return(calibrated_band)

    def crop_to_cutline(self, image_dir, input_features):
        print('CROPPING TO CUTLINE')

        # generate image list & get src epsg
        image_list = glob.glob(os.path.join(image_dir, '*.tif'))
        t_srs = self._get_raster_epsg(image_list[0])
        features_epsg = self.get_vector_epsg(input_features)
        # reprojecting input_features to target_srs if not common projection
        if features_epsg != t_srs:
            print('REPROJECTING INPUT FEATURES TO TARGET PROJECTION')
            t_srs_feature_aoi = work_dir + os.sep + \
                "_".join([os.path.splitext(os.path.split(input_features)[1])[0], t_srs]) + '.geojson'
            system_command = ['ogr2ogr', "-overwrite", "-t_srs", 'EPSG:' + t_srs, t_srs_feature_aoi, input_features]
            system_call(system_command)
            input_features = t_srs_feature_aoi

        src = ogr.Open(input_features, 0)
        layer = src.GetLayer()
        count = layer.GetFeatureCount()
        for feature in layer:
            feature_id = feature.GetFID()
            feature_shp = work_dir + os.sep + '_'.join([os.path.splitext(os.path.split(
                input_features)[1])[0], 'FEATURE_ID', str(feature_id)]) + '.geojson'
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
                    image_chip = subdir + os.sep + \
                        '_'.join([os.path.split(os.path.splitext(image)[0])[1], 'clipped']) + '.tif'
                if count > 1:
                    image_chip = subdir + os.sep + '_'.join([os.path.split(os.path.splitext(
                        image)[0])[1], 'FEATURE_ID', str(feature_id), 'clipped']) + '.tif'
                # cropping to cutline bands
                system_command = ['gdalwarp', "-cutline", feature_shp,
                                  '-crop_to_cutline', image, image_chip, '-overwrite']
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
        image_dates = [tile.split('/')[-1][11:19]
                       for tile in average_settings['image-list']]

        # include images from mosaic folder
        if average_settings['include-mosaic']:
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

            output_arr = []
            band_count = array_list[0].shape[0]
            for i in range(0, band_count):
                band_list = [img[i, :, :] for img in array_list]
                output_arr.append(np.nanmean(band_list, axis=0))

            # create output image
            output_image = output_dir + os.sep + '_'.join(image_dates + ['average', extension])
            # write image
            with rio.open(tiles[0]) as src:
                meta = src.meta
            meta['driver'] = 'GTiff'
            meta['dtype'] = 'float32'
            with rio.open(output_image, 'w', **meta) as dst:
                dst.write(output_arr.astype(rio.float32))

    def get_band_arrays(self, bands):
        band_arrays = []
        for band in bands:
            band_arrays.append(rm.read_band(band))
        return(band_arrays)


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
    work_dir = "/work"
    output_dir = "/output"
    mosaic_dir = "/output/mosaic"
    average_dir = "/output/average"

    # L1C --> L2A name updates
    l2a_names = {}

    # PROCESS TILES
    for image_config in ard_settings.image_list:
        input_tile = data_dir + os.sep + image_config.tile_name
        if os.path.isdir(input_tile) == True:
            print('\n----------------------------------------------------------------------\n')
            print('PROCESSING IMAGE: {}\n'.format(image_config.tile_name))
            pg = ProcessTile(image_config)
            pg.process_tile(input_tile)

            # update L1C tile name to L2A tile name
            if pg.tile_name != image_config.tile_name:
                l2a_names[image_config.tile_name] = pg.tile_name
        else:
            print('Unable to process tile:', image_config.tile_name)

    # MOSAIC IMAGES
    if ard_settings.mosaic_settings['build-mosaic'] == True:
        print('\n----------------------------------------------------------------------\n')
        print("BUILDING TILE MOSAIC...")
        if not os.path.exists(mosaic_dir):
            os.mkdir(mosaic_dir)

        # update L1C product name to Sen2Cor corrected L2A name
        for key, val in l2a_names:
            if key in ard_settings.mosaic_settings['image-list']:
                ard_settings.mosaic_settings['image-list'].remove(key)
                ard_settings.mosaic_settings['image-list'].append(val)

        # build tile mosaic
        build_mosaic(output_dir, ard_settings.mosaic_settings)

        # clip image chips
        if ard_settings.mosaic_settings['clip'] == True:
            pg.crop_to_cutline(mosaic_dir, aoi_file)

    # AVERAGE IMAGES
    if ard_settings.average_settings['compute-average'] == True:
        print('\n----------------------------------------------------------------------\n')
        print("AVERAGING IMAGES...")
        if not os.path.exists(average_dir):
            os.mkdir(average_dir)

        # update L1C product name to Sen2Cor corrected L2A name
        for key, val in l2a_names:
            if key in ard_settings.average_settings['image-list']:
                ard_settings.average_settings['image-list'].remove(key)
                ard_settings.average_settings['image-list'].append(val)

        pg.compute_average(output_dir, mosaic_dir, ard_settings.average_settings)
