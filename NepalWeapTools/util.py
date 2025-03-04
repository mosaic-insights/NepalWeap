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
from shapely.geometry import Point
import overpy
import json


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
                
def get_osm_locations(tag_dict, bbox):
    """
    Gets the locations/info for specified types of things in a specified bounding box
    
    Parameters:
    tag_dict: a dictionary of node tag key: value elements like {'Tag key': 'tag value'}
    bbox: a tuple of lat/lon coordinates (miny, minx, maxy, maxx) defining the search envelope
    """
    #Build a string of tag searches for the query:
    searches = []
    for key, value in tag_dict.items():
        string = f'\n  node["{key}"="{value}"]{bbox};'
        searches.append(string)
    bracket_bit = '(' + ''.join(searches) + '\n);'
    
    #Put the query string together:
    query = '[out:json];\n' + bracket_bit + '\nout body;'
    #Initialise overpass api:
    api = overpy.Overpass()
    #Fetch OSM data:
    result = api.query(query)
    
    # Store results in a structured format
    places = []
    for node in result.nodes:
        #get the type dynamically based on the tag_dict provided
        type_val = next(
            (value for key, value in node.tags.items() if key in tag_dict.keys()),
            'Unknown' #Default value
        )
        places.append({
            "name": node.tags.get("name", "Unknown"),
            "type": type_val,
            "lat": float(node.lat),  # Convert Decimal to float
            "lon": float(node.lon)   # Convert Decimal to float
        })

    # Convert data to GeoDataFrame
    gdf_places = gpd.GeoDataFrame(
        places, geometry=[Point(p["lon"], p["lat"]) for p in places], crs="EPSG:4326"
    )
    
    return gdf_places
    
def rescale_to_census(locations, wards, census_num, name:str):
    """
    Rescales numbers of a certain feature per ward, based on the official number for the 
    study area.
    
    Parameters:
    locations: GeoDataFrame of locations of a specific type in the area of interest
    wards: GeoDataFrame of the ward boundaries in the AOI
    census_num: official number of that specific type of amenity 
    name: place type to append to column names in output dataframe
    
    Returns:
    Dataframe with the scaled numbers, with the ward number as the index
    """
    #Perform spatial join to get the ward number for each commercial location:
    places_with_wards = gpd.sjoin(locations, wards, how='left', predicate='within')
    
    # Count number of hotels and hospitals per ward
    ward_counts = places_with_wards.groupby(["NEW_WARD_N", "type"]).size().unstack(fill_value=0)
    
    # Ensure all wards are included by merging with the full list of wards
    all_wards = pd.DataFrame(wards[["NEW_WARD_N"]])
    ward_counts = all_wards.merge(ward_counts, on="NEW_WARD_N", how="left").fillna(0)
    #Rename columns for clarity:
    ward_counts.columns = ['Ward', 'OSM count']
    ward_counts = ward_counts.sort_values(by='Ward').set_index('Ward')
    
    #Get proportion from OSM in each ward:
    ward_counts['OSM proportion'] = ward_counts['OSM count'] / ward_counts['OSM count'].sum()
    
    #Scale the proportions in each ward by the total number reported in the census:
    ward_counts['scaled number'] = ward_counts['OSM proportion'] * census_num
    
    ward_counts.columns = [name + ' ' + header for header in ward_counts.columns]
    
    return ward_counts
                
                
                
                
                
                
                
                