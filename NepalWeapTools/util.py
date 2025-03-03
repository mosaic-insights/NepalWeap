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
import rasterio
import numpy as np

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