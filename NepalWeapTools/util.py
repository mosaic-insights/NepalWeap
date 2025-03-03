"""
------------------------------------------------------------------------
Module Name: util
Parent Package: NepalWeapTools

******* Metadata *******
__author__ = ['Richard Farr', 'Kristen Joyce']
__copyright__ = 'Alluvium Consulting (TBC)'
__credits__ = ['Petter Nyman']
__version__ = 0.01
__maintainer__ = 'Richard Farr'
__email__ = 'richard.farr@alluvium.com.au'
__status__ = 'In development'

Last update: 28/02/2025

******* Description *******
Part of the NepalWeapTools package, this module contains functions
commonly required by the classes in the other package modules
------------------------------------------------------------------------
"""
####### Package imports: #######
import datetime as dt
import numpy as np
import pandas as pd
import rasterio
from rasterio.io import MemoryFile
from rasterio.mask import mask
import geopandas as gpd


def date_standardiser(date_string):
    """Convert date string to YYYY-MM-DD"""
    # Try to parse the date_string assuming its in an ISO format
    try:
        date_object = dt.datetime.fromisoformat(str(date_string)).date() 
    except ValueError:
        try:
            date_object = dt.datetime.strptime(date_string, '%d/%b/%Y').date()
        except ValueError:
            try:
                date_object = dt.datetime.strptime(date_string, '%m/%d/%Y').date()
            except ValueError:
                return None
    # If successful, format the date_object to 'YYYY-MM-DD' and return it
    return date_object.strftime('%Y-%m-%d')

def compare_sheet_names(sheet_names:list, objects:list):
    """Remove objects from list if they're not in sheet_names"""
    #Get the set of strings in both:
    matches = set(sheet_names) & set(objects)
    
    #If there's none, raise an error:
    if not matches:
        raise ValueError('None of the provided list elements matched worksheet names.')
    
    #Get the unmatched ones:
    unmatched = set(objects) - set(sheet_names)
    if unmatched:
        print(f'Warning: {unmatched} were not found in Excel file and have been removed')
    
    new_obj = [a for a in objects if a in sheet_names]
    return new_obj
    
def get_raster_deets(GeoTIFF):
    """
    Extracts and returns a bunch of useful information about a GeoTIFF raster

    Args:
    -Raster: a 'path\filename.ext' string to the GeoTIFF raster

    Returns:
    -A dictionary with a bunch of useful info about the raster
    -The data from the raster as a numpy ndarray
    -The metadata as a dictionary
    
    Notes:
    -The The RasterInfo and Meta dictionaries have some overlap. RasterInfo is meant for easy access in other lines of code,
    Meta is designed to be attachable when the raster is processed or written as a GeoTIFF.
    """
    with rasterio.open(GeoTIFF) as src:
        RasterInfo = {}
        RasterInfo['crs'] =  int(src.crs.to_epsg())
        RasterInfo['minx'] = src.bounds[0]
        RasterInfo['miny'] = src.bounds[1]
        RasterInfo['maxx'] = src.bounds[2]
        RasterInfo['maxy'] = src.bounds[3]
        RasterInfo['transform'] = src.transform
        RasterInfo['cellsize'] = src.res
        RasterInfo['width'] = RasterInfo['maxx'] - RasterInfo['minx']
        RasterInfo['height'] = RasterInfo['maxy'] - RasterInfo['miny']
        Array = src.read(1)
        Meta = src.meta
        
    return RasterInfo, Array, Meta
    
def get_zonal_stats(in_raster, in_meta, gdf, class_dict:dict, key_field_name:str='Name'):
    """
    Get zonal stats for a raster without relying on rasterstats
    
    Parameters:
    in_raster: numpy array representing raster values
    in_meta: metadata dictionary associated with the raster array
    gdf: Geopandas GeoDataFrame in the same CRS as the raster
    class_dict: dictionary of what the numerical values in the raster corrspond to as categories
    key_field_name: name of the field in the geodataframe which can be used to uniquely identify features
    
    Returns:
    
    """
    #Convert numeric values in the input raster to their text equivalents:
    print('Getting zonal stats with get_zonal_stats()...')
    
    raw_stats = pd.DataFrame()
    
    #Get the raster ready for rasterio:
    with MemoryFile() as memfile:
        with memfile.open(**in_meta) as dataset:
            dataset.write(in_raster, 1)
            
            #Go through each feature in the input shapefile:
            for index, feature in gdf.iterrows():
                #Store relevant info
                this_feature = feature
                this_name = feature[key_field_name]
                this_geom = feature['geometry']
                
                #get just the current zone
                masked_ras, _ = mask(dataset, [this_geom], crop=True)
                
                #Get a dictionary with the number of times each unique element appears:
                cats, counts = np.unique(masked_ras, return_counts=True)
                freqs = dict(zip(cats, counts))
                freqs['Subcatchment'] = this_name
                
                #Add the values to the raw_stats dataframe:
                this_row = pd.DataFrame(freqs, index=[freqs['Subcatchment']])
                this_row = this_row.drop('Subcatchment', axis=1)
                raw_stats = pd.concat([raw_stats, this_row], axis=0)
    
    #Replace NaN values with 0 and format the dataframe for easy interpretation:
    raw_stats = raw_stats.fillna(0).rename(class_dict, axis='columns').sort_index().sort_index(axis=1)
    raw_stats['None'] = raw_stats.pop('None')
    
    return raw_stats       
                
                
                
                
                
                
                
                
                
                