# -*- coding: utf-8 -*-
"""
Geospatial Metadata Transfer for Model Predictions

This script copies geospatial metadata (coordinate system and geotransform) from 
source imagery to machine learning model prediction outputs.

Purpose:
    When a machine learning model generates predictions, the output TIFFs often lack 
    geospatial reference information. This script transfers that metadata from the 
    original imagery to enable the predictions to be used in GIS applications.

Use Case:
    2025 California Eastern Municipal Water District Land Use Classification project.
    The UNet ResNet101 model produces semantic segmentation predictions that need to 
    be georeferenced to match the original 4-band RGBN imagery.

Created on Thu Dec 19 16:04:05 2019

@author: Chris.Robinson
"""
import os
import glob
from osgeo import gdal
import yaml
from pathlib import Path
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Update geotransform in TIFFs')
parser.add_argument('--config', type=str, help='Path to config file')
args = parser.parse_args()

# Determine config file path
if args.config:
    config_path = Path(args.config)
else:
    # Fallback to default location
    config_path = Path(__file__).parent / 'gdal_update_geotrans_config.yml'

print(f"Loading config from: {config_path}", flush=True)

# Load configuration from YAML file
try:
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    if config is None:
        raise ValueError("Config file is empty")
        
    print(f"Config loaded successfully", flush=True)
except Exception as e:
    print(f"Error loading config: {e}", flush=True)
    raise

img_dir = config['img_dir']
label_dir = config['label_dir']


def add_proj(src_tiff, lbl_tiff):
    """
    Copy geospatial metadata from source imagery to prediction output.
    
    Transfers geotransform (pixel-to-coordinate mapping) and projection 
    (coordinate system) from the source TIFF to the label/prediction TIFF.
    
    Args:
        src_tiff (str): Path to source imagery file with geospatial metadata
        lbl_tiff (str): Path to prediction/label file to update with metadata
        
    Returns:
        None: The lbl_ds is closed and returned as None
    """
    # Open files as GDAL Dataset Objects
    ds = gdal.Open(src_tiff)
    print(src_tiff)
    print(lbl_tiff)
    lbl_ds = gdal.Open(lbl_tiff, gdal.GA_Update)

    # Get Transform and Projection info from source image
    geotransform = ds.GetGeoTransform()
    projection = ds.GetProjection()

    lbl_ds.SetGeoTransform(geotransform)
    lbl_ds.SetProjection(projection)
    # Close Dataset
    lbl_ds = None
    return lbl_ds


if __name__ == "__main__":
    tile_list = glob.glob(f'{label_dir}/*.tif')
    tile_ids = [(os.path.splitext(os.path.basename(t))[0]) for t in tile_list]
    print("Tiles for inference : ", tile_ids)

    for id in tile_ids:
        src_tiff = os.path.join(img_dir, f"{id}.tif")
        lbl_tiff = os.path.join(label_dir, f"{id}.tif")
        add_proj(src_tiff, lbl_tiff)
        print(f"adding projection for {lbl_tiff}")
    print("Process Complete")
