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
####### Package imports: ######################################################
import datetime as dt
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.dates as mdates
import rasterio
from rasterio.io import MemoryFile
from rasterio.mask import mask
import geopandas as gpd
from shapely.geometry import Point
import overpy
import json

####### Date standardiser: ####################################################
#-----------------------------------------------------------------------
def date_standardiser(date_string):
    """Convert date string to YYYY-MM-DD"""
    # Try to parse the date_string assuming its in an ISO format
    try:
        date_object = dt.datetime.fromisoformat(str(date_string)).date() 
    except ValueError:
        try:
            date_object = dt.datetime.strptime(
                date_string,
                '%d/%m/%Y'
                ).date()
        except ValueError:
            try:
                date_object = dt.datetime.strptime(
                    date_string,
                    '%d/%b/%Y'
                    ).date()
            except ValueError:
                try:
                    date_object = dt.datetime.strptime(
                        date_string,
                        '%m/%d/%Y'
                        ).date()
                except ValueError:
                    return None
    # If success, format the date_object to 'YYYY-MM-DD' and return it
    return date_object.strftime('%Y-%m-%d')

####### Compare sheet names: ##################################################
#-----------------------------------------------------------------------
def compare_sheet_names(sheet_names:list, objects:list):
    """Remove objects from list if they're not in sheet_names"""
    #Get the set of strings in both:
    matches = set(sheet_names) & set(objects)
    
    #If there's none, raise an error:
    if not matches:
        raise ValueError(
            'None of the provided list elements matched worksheet names.'
            )
    
    #Get the unmatched ones:
    unmatched = set(objects) - set(sheet_names)
    if unmatched:
        print(
            f'Warning: {unmatched} were not found in Excel file'
            ' and have been removed'
            )
    
    new_obj = [a for a in objects if a in sheet_names]
    return new_obj

####### Get raster details: ###################################################
#-----------------------------------------------------------------------
def get_raster_deets(GeoTIFF):
    """
    Extracts and returns a bunch of useful information about a GeoTIFF 
    raster

    Parameters:
    - Raster: a 'path\filename.ext' string to the GeoTIFF raster

    Returns:
    - A dictionary with a bunch of useful info about the raster
    - The data from the raster as a numpy ndarray
    - The metadata as a dictionary
    
    --------------------------------------------------------------------
    Notes:
    - The RasterInfo and Meta dictionaries have some overlap. RasterInfo
    is meant for easy access in other lines of code, meta is designed to
    be attachable when the raster is processed or written as a GeoTIFF.
    --------------------------------------------------------------------
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

####### Get zonal stats: ######################################################
#-----------------------------------------------------------------------
def get_zonal_stats(
    in_raster,
    in_meta,
    gdf,
    class_dict:dict,
    key_field_name:str='Name'
    ):
    """
    Get zonal stats for a raster without relying on rasterstats
    
    Parameters:
    - in_raster: numpy array representing raster values
    - in_meta: metadata dictionary associated with the raster array
    - gdf: Geopandas GeoDataFrame in the same CRS as the raster
    - class_dict: dictionary of what the numerical values in the raster
    correspond to as categories
    - key_field_name: name of the field in the geodataframe which can be
    used to uniquely identify features
    
    Returns:
    - A dataframe with the number of times each class appears in each
    subcatchment
    --------------------------------------------------------------------
    --------------------------------------------------------------------
    """
    #Convert numeric values in the input raster to their text
    #equivalents:
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
                
                #Get a dictionary with the number of times each unique
                #element appears:
                cats, counts = np.unique(masked_ras, return_counts=True)
                freqs = dict(zip(cats, counts))
                freqs['Subcatchment'] = this_name
                
                #Add the values to the raw_stats dataframe:
                this_row = pd.DataFrame(freqs, index=[freqs['Subcatchment']])
                this_row = this_row.drop('Subcatchment', axis=1)
                raw_stats = pd.concat([raw_stats, this_row], axis=0)
    
    #Replace NaN values with 0 and format the dataframe for easy
    #interpretation:
    raw_stats = raw_stats.fillna(0).rename(
        class_dict,
        axis='columns'
        ).sort_index().sort_index(axis=1)
    raw_stats['None'] = raw_stats.pop('None')
    
    return raw_stats       

####### Get OSM locations: ####################################################
#-----------------------------------------------------------------------
def get_osm_locations(tag_dict, bbox):
    """
    Gets the locations/info for specified types of things in a specified
    bounding box
    
    Parameters:
    - tag_dict: a dictionary of node tag key: value elements like
    {'Tag key': 'tag value'}
    - bbox: a tuple of lat/lon coordinates (miny, minx, maxy, maxx)
    defining the search envelope
    
    Returns:
    - A geodataframe of feature locations with their name and type,
    within the bounding box
    --------------------------------------------------------------------
    --------------------------------------------------------------------
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
            (
                value for key, value
                in node.tags.items()
                if key in tag_dict.keys()
                ),
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
        places,
        geometry=[Point(p["lon"], p["lat"]) for p in places],
        crs="EPSG:4326"
    )
    
    return gdf_places

####### Rescale to census: ####################################################
#-----------------------------------------------------------------------
def rescale_to_census(locations, wards, census_num, name:str):
    """
    Rescales numbers of a certain feature per ward, based on the
    official number for the study area.
    
    Parameters:
    - locations: GeoDataFrame of locations of a specific type in the
    area of interest
    - wards: GeoDataFrame of the ward boundaries in the AOI
    - census_num: official number of that specific type of amenity 
    - name: place type to append to column names in output dataframe
    
    Returns:
    - Dataframe with the scaled numbers, with the ward number as the
    index
    --------------------------------------------------------------------
    --------------------------------------------------------------------
    """
    #Perform spatial join to get the ward number for each commercial
    #location:
    places_with_wards = gpd.sjoin(
        locations,
        wards,
        how='left',
        predicate='within'
        )
    
    #Count number of hotels and hospitals per ward:
    ward_counts = places_with_wards.groupby(
        ["NEW_WARD_N", "type"]
        ).size().unstack(fill_value=0)
    
    #Ensure all wards are included by merging with the full list of
    #ward:
    all_wards = pd.DataFrame(wards[["NEW_WARD_N"]])
    ward_counts = all_wards.merge(
        ward_counts,
        on="NEW_WARD_N",
        how="left"
        ).fillna(0)
    
    #Rename columns for clarity:
    ward_counts.columns = ['Ward', 'OSM count']
    ward_counts = ward_counts.sort_values(by='Ward').set_index('Ward')
    
    #Get proportion from OSM in each ward:
    ward_counts['OSM proportion'] = (
        ward_counts['OSM count'] / ward_counts['OSM count'].sum()
        )
    
    #Scale the proportions in each ward by the total number reported in
    #the census:
    ward_counts['scaled number'] = ward_counts['OSM proportion'] * census_num
    ward_counts = ward_counts.drop(
        labels=['OSM count', 'OSM proportion'],
        axis=1
        )
    ward_counts.columns = [name + ' scaled number']
    
    return ward_counts
                
####### Areal interpolation: ##################################################
#-----------------------------------------------------------------------
def areal_interp(
    wards,
    service_area, 
    eq_ar_proj=6931,
    demand_cols=[
        'Domestic demand [m3/d]',
        'Institutional demand [m3/d]',
        'Commercial demand [m3/d]',
        'Municipal demand [m3/d]',
        'Industrial demand [m3/d]',
        'Total demand [m3/d]'
        ]
    ):
    """
    Estimate total water demand for a service area based on its
    consituent wards.
    
    Parameters:
    - wards: geodataframe of ward boundary polgons with attributes for
    demand
    - service_area: geodataframe of a single service area polygon
    - eq_ar_proj: epsg code for the desired equal-area proejction to use
    - demand_cols: list of column names in the wards file
    
    Returns:
    - Geodataframe of the service area polygon with the estimated total
    demand
    --------------------------------------------------------------------
    Notes:
    - This is a crude areal interpolator which assumes uniform demand
    across the wards
    --------------------------------------------------------------------
    """
    #Get and store the input CRS:
    input_crs = wards.crs.to_epsg()
    #Reproject both to EPSG:6931, which is an equal-area projection:
    ea_wards = wards.to_crs(epsg=eq_ar_proj)
    ea_utility = service_area.to_crs(epsg=eq_ar_proj)
    
    #Second, calculate the area of each ward in the reprojected layer:
    ea_wards['OG_area'] = ea_wards.geometry.area
    
    #Get the intersection of the wards layer with the utility layer:
    wards_in_utility = ea_wards.overlay(ea_utility, keep_geom_type=True)
        
    #Calculate the area of each ward in the clipped layer again:
    wards_in_utility['New_area'] = wards_in_utility.geometry.area
        
    #Calculate the proportion of the original area in the clipped layer:
    wards_in_utility['Area_propn'] = (
        wards_in_utility['New_area'] / wards_in_utility['OG_area']
        )
    
    new_cols = []
    #Apply that proportion to the demand for each ward
    for column in demand_cols:
        new_col = 'SA ' + column
        new_cols.append(new_col)
        wards_in_utility[new_col] = (
            wards_in_utility[column] * wards_in_utility['Area_propn']
            )
    
    #Calculate the sum of all rescaled ward demands in the clipped layer
    #and make them attribbutes of the utility layer:
    for column in new_cols:
        this_demand_total = wards_in_utility[column].sum()
        ea_utility[column] = this_demand_total
    
    #Return a geodataframe of just the utility boundary and the demands:
    ea_utility = ea_utility[new_cols + ['geometry']]
    ea_utility.columns = [a.replace('SA ', '') for a in ea_utility.columns]
    return ea_utility.to_crs(epsg=input_crs)
    
####### Population forecasting: ###############################################
#-----------------------------------------------------------------------
def pop_forecast(
    pop_dataframe,
    future_year:int,
    growth_cap=0.1):
    """
    Estimate populations in future years based on levels in previous
    years.
    
    Parameters:
    - pop_dataframe: Pandas dataframe with historical population figures
    for each ward, for at least two different census years.
    - future_year: The future year for which a forecast is desrired
    - growth_cap: maximum absolute value for positive or negative
    growth to be used in forcasting.
    
    Returns:
    - Dataframe with a column for the new year and the forecasted
    population
    --------------------------------------------------------------------
    Notes:
    - Requires that the column names have a four-digit year somewhere in
    them, and no other numeric characters
    --------------------------------------------------------------------
    """
    print('Forecasting future population...')
    input_cols = pop_dataframe.columns
    year_cols = [''.join([c for c in h if c.isdigit()]) for h in input_cols]
    
    #Check that the remaining strings are valid years:
    for item in year_cols:
        #Check that the resulting year is four digits long:
        if len(item) != 4:
            raise ValueError(
                'Column names in population change file must include a '
                '4-digit string that can convert to a year. At least '
                f'one column had a year of length {len(item)}, or had '
                'other non-year numeric characters in. The first issue '
                f'encountered was in {item}.'
                )
    
    latest_year = max([int(a) for a in year_cols])
    years_elapsed = future_year - latest_year
    
    #Assign the new columns, then sort so we have ascending years:
    pop_dataframe.columns = year_cols
    pop_dataframe = pop_dataframe.sort_index(axis='columns')
    
    #Empty list to store the future pops as they are calculated:
    pop_change_rates = []
    
    #Go through each row (ward):
    for i in range(len(pop_dataframe.index)):
        num_years = 0
        pop_change = 0
        this_ward = pop_dataframe.iloc[[i]]
        start_pop = this_ward.iloc[0, 0]
        #Go through each column (census year):
        for j in range(len(pop_dataframe.columns) - 1):
            y1 = int(pop_dataframe.columns[j])
            y1_pop = this_ward.iloc[0, j]
            y2 = int(pop_dataframe.columns[j+1])
            y2_pop = this_ward.iloc[0, j+1]
            #Number of elapsed years:
            num_years += (y2 - y1)
            #Gross population change:
            pop_change += (y2_pop - y1_pop)
        
        annual_change = pop_change / num_years
        rate_pa = annual_change / start_pop
        pop_change_rates.append(rate_pa)
        
    pop_dataframe['Change rate'] = pop_change_rates
    
    #Replace any growth rates with absolute value > 0.1 with 0.1,
    #retaining their sign:
    pop_dataframe['Change rate'] = pop_dataframe['Change rate'].apply(
        lambda x: 0.1 if x > 0.1 else (-0.1 if x < -0.1 else x)
        )
    
    #Calculate the forecasted growth:
    pop_dataframe[str(future_year)] = (
        pop_dataframe[str(latest_year)]
        * ((1 + pop_dataframe['Change rate']) ** years_elapsed)
        )
    return pop_dataframe

####### X-axis date formatting: ###############################################
def x_axis_dater(axes, years):
    """
    Set appropriate date ticks/lables for the x-axis depending on the
    time interval
    
    Parameters:
    - axes: Matplotlib axes object with datetime objects as the x-axis
    values
    - years: number of years
    --------------------------------------------------------------------
    --------------------------------------------------------------------
    """
    #Format x-axis labels/ticks based on the timeframe of the data:
    if years < 1:
        #Tick every month:
        axes.xaxis.set_major_locator(mdates.MonthLocator())
        axes.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    elif years <=2:
        #Tick every second month:
        axes.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        axes.xaxis.set_major_formatter(mdates.DateFormatter('%b-%y'))
    elif years <= 10:
        #Tick every year:
        axes.xaxis.set_major_locator(mdates.YearLocator())
        axes.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    elif years <=20:
        #Tick every second year
        axes.xaxis.set_major_locator(mdates.YearLocator(2))
        axes.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    else:
        #Tick every 5th year:
        axes.xaxis.set_major_locator(mdates.YearLocator(5))
        axes.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))