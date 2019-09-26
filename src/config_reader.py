from ruamel.yaml import YAML
import os

# reading the configuration file 
class ConfigReader(object):

    def __init__(self, yaml_file, geojson_file):

        with open(yaml_file, 'r') as stream:
            yaml = YAML()
            config = yaml.load(stream)

        # validate ard-settings
        try:
            self.ard_keywords = ["atm-corr", "cloud-mask", "stack", "calibrate", "clip", "derived-index"]

            self.ard_settings = {}
            for key in self.ard_keywords:
                if key in dict(config['ard-settings']).keys():
                    self.ard_settings[key] = dict(config['ard-settings'])[key]
                # default ard settings are always false
                if key not in dict(config['ard-settings']).keys():
                    self.ard_settings[key] = False
        except Exception:
            raise IOError('in YAML file ars-settings is not defined')

        # validate cloud-mask-settings
        if self.ard_settings['cloud-mask'] == True:
            try:
                self.cloud_mask_keywords = ["sen2cor-scl-codes", "fmask-codes"]

                self.cloud_mask_settings = {}
                for key in self.cloud_mask_keywords:
                    if key in dict(config['cloud-mask-settings']).keys():
                        self.cloud_mask_settings[key] = dict(config['cloud-mask-settings'])[key]

                    if key not in dict(config['cloud-mask-settings']).keys():
                        self.cloud_mask_settings[key] = False
            except Exception:
                raise IOError('in YAML file cloud-mask-settings is not defined')

        if self.ard_settings['cloud-mask'] == False:
            self.cloud_mask_settings = False

        # validate output-image-settings
        try:
            self.output_image_keywords = ["bands", "vi", "resampling-method", "t-srs", "resolution"]

            self.output_image_settings = {}
            for key in self.output_image_keywords:
                if key in dict(config['output-image-settings']).keys():
                    self.output_image_settings[key] = dict(config['output-image-settings'])[key]
                # default output_image_settings are always false
                if key not in dict(config['output-image-settings']).keys():
                    self.output_image_settings[key] = False

            # default keywords settings
            if 'bands' not in dict(config['output-image-settings']).keys():
                self.output_image_settings['bands'] = [] # NIR-RED-GREEN Band Combinations 
            if 'resolution' not in dict(config['output-image-settings']).keys():
                self.output_image_settings['resolution'] = 10
            if 'resampling-method' not in dict(config['output-image-settings']).keys():
                self.output_image_settings['resampling-method'] = 'near'

            if os.path.exists(geojson_file):
                self.output_image_settings['input-features'] = geojson_file
            if not os.path.exists(geojson_file):
                self.output_image_settings['input-features'] = False

            if (self.ard_settings['clip'] == True) and (self.output_image_settings['input-features'] == False):
                print('in YAML file input_features as the cropt-to-cutline is not defined')
                exit(1)

        except Exception:
            print('in YAML file output-image-settings is not defined. Default settings are used.')
