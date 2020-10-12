from ruamel_yaml import YAML
import os

# reading the configuration file
class ConfigReader(object):

    def __init__(self, yaml_file, geojson_file):

        with open(yaml_file, 'r') as stream:
            yaml = YAML()
            config = yaml.load(stream)

        # error handling happens in image reader
        self.tile_list = []
        for tile_args in config['tile-list']:
            tile_config = config['tile-list'][tile_args]
            tile_settings = ImageReader(tile_config, geojson_file)
            self.tile_list.append(tile_settings)

        # parse mosaic settings
        if config['mosaic-settings']['build-mosaic'] == True:
            try:
                self.mosaic_keywords = ["build-mosaic", "resampling-method", "clip"]
                self.mosaic_settings = self.parse_settings(self.mosaic_keywords, config['mosaic-settings'])
                self.mosaic_settings['image-list'] = []
                for i in config['mosaic-settings']['image-list']:
                    self.mosaic_settings['image-list'].append(config['mosaic-settings']['image-list'][i])

            except Exception:
                raise IOError('in YAML file mosaic-settings not defined')
        else:
            self.mosaic_settings = False

        # parse average settings
        if config['average-settings']['compute-average'] is True:
            try:
                self.average_keywords = ["compute-average", "include-mosaic", "clip"]
                self.average_settings = self.parse_settings(self.average_keywords, config['average-settings'])
                self.average_settings['image-list'] = []
                for i in config['average-settings']['image-list']:
                    self.average_settings['image-list'].append(config['average-settings']['image-list'][i])

            except Exception:
                raise IOError('in YAML file average-settings not defined')

        else:
            self.average_settings = False

    def parse_settings(self, keywords, config):
        param_dict = {}
        for key in keywords:
            if key in dict(config).keys():
                param_dict[key] = dict(config)[key]
        return param_dict


# reading of image objects in config file
class ImageReader(object):

    def __init__(self, config, geojson_file):

        # validate tile-name
        try:
            self.tile_name = config['tile-name']
        except Exception:
            raise IOError('in YAML file tile-name not defined')

        # validate ard-settings
        try:
            self.ard_keywords = ["atm-corr", "cloud-mask", "stack", "calibrate", "clip", "derived-index"]
            self.ard_settings = self.parse_settings(self.ard_keywords, config['ard-settings'])
        except Exception:
            raise IOError('in YAML file ard-settings is not defined for: ', self.tile_name)

        # validate cloud-mask-settings
        if self.ard_settings['cloud-mask'] == True:
            try:
                self.cloud_mask_keywords = ["sen2cor-scl-codes", "fmask-codes"]
                self.cloud_mask_settings = self.parse_settings(self.cloud_mask_keywords, config['cloud-mask-settings'])
            except Exception:
                raise IOError('in YAML file cloud-mask-settings is not defined for: ', self.tile_name)

        if self.ard_settings['cloud-mask'] == False:
            self.cloud_mask_settings = False

        # validate output-image-settings
        try:
            self.output_image_keywords = ["bands", "vi", "resampling-method", "t-srs", "resolution"]
            self.output_image_settings = self.parse_settings(self.output_image_keywords, config['output-image-settings'])

            # default keywords settings
            if 'bands' == False:
                self.output_image_settings['bands'] = ['B02', 'B03', 'B04', 'B08']  # BLUE-GREEN-RED-NIR Band Combinations
            if 'resolution' == False:
                self.output_image_settings['resolution'] = 10
            if 'resampling-method' == False:
                self.output_image_settings['resampling-method'] = 'near'

            if os.path.exists(geojson_file):
                self.output_image_settings['input-features'] = geojson_file
            else:
                self.output_image_settings['input-features'] = False

        except Exception:
            print('in YAML file output-image-settings are not defined for: {}. Default settings are used.'.format(self.tile_name))

    def parse_settings(self, keywords, config):
        param_dict = {}
        for key in keywords:
            if key in dict(config).keys():
                param_dict[key] = dict(config)[key]
            if key not in dict(config).keys():
                param_dict[key] = False
        return param_dict
