"""
------------------------------------------------------------------------
Module Name: dataprep
Parent Package: NepalWeapTools

******* Metadata *******
__author__ = ['Kristen Joyce', 'Richard Farr']
__copyright__ = 'Alluvium Consulting (TBC)'
__credits__ = ['Petter Nyman']
__version__ = 0.01
__maintainer__ = 'Richard Farr'
__email__ = 'richard.farr@alluvium.com.au'
__status__ = 'In development'

Last update: 03/03/2025

******* Description *******
Part of the NepalWeapTools package, this module takes inputs of various 
catchment variable as datsets and converts them into output formats
that are readable by the Stockholm Environment Institute's Water
Evaluation And Planning (WEAP) software.
------------------------------------------------------------------------
"""
####### Module Imports: #######
from . import util
import numpy as np
import pandas as pd
import geopandas as gpd
import os
import matplotlib as mpl
import matplotlib.pyplot as plt
import rasterio as rio

####### For when module is run directly: #######
def main():
    """
    Placeholder function for if this package is run directly.
    Running directly is not currently in scope
    """
    print('dataprep module has been run directly. \nPlease use within the\
    context of a python script and the NepalWeapTools package.')
    pass
    
if __name__ == '__main__':
    main()

####### Measured variables: #################################################

class MeasVar:
    """
    Store data for individual variables that area measured, such as streamflow or temperature.
    Allows broad classes to be extended to incorporate variables that are not currently included.
    """
    
    def __init__(self,
        dataframe,
        measure:str,
        date_range:list,
        parent,
        unit:str='Unspecified',
        skipped_rows:int=0
        ):
        """
        Read and store a dataframe passed from a HydroData or MeteoData instance.
        
        Parameters:
        dataframe: a pandas dataframe with a row for each date and column for each station.
        date_range: a list of observation dates to include
        parent: the instance of HydroData or MeteoData which created this instance
        unit: if a unit is specified or known, this will be incorporated into the output
            column name.
        skipped_rows: for audit trail purposes; the number of rows with date values that 
            couldn't be handled by the source instance.
        """
        self.measure = measure
        self.date_range = date_range
        self.unit = unit
        self.parent = parent
        self.skipped_rows = skipped_rows
        
        #Load an empty dataframe with dates as the index:
        self.base_data = pd.DataFrame(index=self.date_range)
        self.base_data = self.base_data.merge(dataframe, left_index=True, right_index=True, how='left')
        
    def to_weap_data(self):
        """
        Reformat the base_data to match WEAP's required CSV format, and write it as a file to the instance's
        output location.
        """
        #Get an updated copy of the base_data with the date moved out of the index, leaving the original untouched:
        w_data = self.base_data.reset_index(names='$Columns = Date')
        if self.unit != 'Unspecified':
            w_data.columns = [col + f' [{self.unit}]' for col in w_data.columns]
            
        num_blanks  = [ '' for i in range(len(w_data.columns) - 1)]
        #Add lines to match required formatting of WEAP files:
        w_data.columns = pd.MultiIndex.from_tuples(
            zip(
                ['$ListSeparator = ,'] + num_blanks,
                ['$DecimalSymbol = .'] + num_blanks,
                w_data.columns
            )
        )
        
        #Write to csv in the output folder:
        w_data.to_csv(rf'{self.parent.output_loc}\{self.parent.input_file_name}_{self.measure}.csv', index=False)
        
        return True
        
    def __str__(self):
        """Define how to represent this as a string"""
        output_string = 'Set of {} recordings between {} and {}, for {} stations.'.format(
            self.measure, self.date_range[0], self.date_range[-1], len(self.base_data.columns)
        )
        return output_string

####### Hydro data: ########################################################

class HydroData:
    """
    Loads and stores hydrological data, and allows it to be exported to WEAP formats.
    Currently only streamflow is measured, but this class uses the MeasVar class in this module 
    to handle separate variables, so is extensible to additional hydro variables.
    """
    
    def __init__(self, file_name:str,
        station_list:list,
        model_cal_start:str,
        model_cal_end:str,
        measurements:list=['Streamflow'],
        units:list=['m3/s']
        ):
        """
        Read input streamflow data file and store with instance as dataframe
        
        Parameters:
        file_name: path to file with raw stream gauge data
        station_list: list of names of streamflow gauge stations to be examined. Must match worksheet names
        model_cal_start: start date of the desired calibration time preiod in format YYYY-MM-DD
        model_cal_end: end date of the desired calibration time preiod in format YYYY-MM-DD
        measurements: list of hydrological variables to include
        units: list of strings representing units of the corresponding entries in measurements
        
        Notes:
        - file_name will be deprecated once data is stored in a static path relative to the module.
        - User will then just input the station list.
        - Dates must be in a valid ISO8601 format as per datetime.date.fromisoformat()
        - Names of stations in the station list must exactly match the worksheet names
        - This code assumes there is only one variable per worksheet
        """
        
        #Get the directory relative to the current script (dataprep.py)
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        #Construct the path to the InputData folder
        input_data_path = os.path.join(current_dir, r'InputData\Hydro')
        #Add the file name to the path:
        self.data_path = os.path.join(input_data_path, file_name)
        #Same for output location:
        self.output_loc = os.path.join(current_dir, r'OutputData')
        
        #Store the basic info in this instance
        self.input_file_name = file_name.split('.')[0]
        self.stations = station_list
        self.measurements = measurements
        
        #Load date info for this instance:
        self.mc_start = util.date_standardiser(model_cal_start)
        self.mc_end = util.date_standardiser(model_cal_end)
        date_array = pd.date_range(start=self.mc_start, end=self.mc_end).date
        self.date_range = [date.strftime('%Y-%m-%d') for date in date_array]
        
        #Load the excel file and work out what variables are included
        self.input_file = pd.ExcelFile(self.data_path)
        checked_stations = util.compare_sheet_names(self.input_file.sheet_names, self.stations)
        
        self.datasets = []
        #Create a dummy df to merge the values for each station into:            
        base_var_df = pd.DataFrame(index=self.date_range)
        
        #Go through each measurement type:
        for variable in self.measurements:
            current_index = 0
            skipped_rows = 0            
            #Go through each station in the station list and load the data:
            for station in station_list:
                #Read in the excel file:
                this_df = pd.read_excel(self.data_path, station, parse_dates=['Date'])
                #Standardise the date:
                og_length = this_df.shape[0]
                this_df['Date'] = this_df['Date'].apply(util.date_standardiser)
                this_df = this_df.dropna(subset=['Date'])
                new_length = this_df.shape[0]
                skipped_rows += (og_length - new_length)
                this_df.set_index('Date', inplace=True)
                this_df.columns=[station]
                base_var_df = base_var_df.merge(this_df, left_index=True, right_index=True, how='left')
            
            #Create a linked MeasVar instance to store it as a formatted dataset:
            dataset = MeasVar(
                base_var_df,
                variable,
                self.date_range,
                parent=self,
                unit=units[current_index],
                skipped_rows=skipped_rows
            )
            #Add the MeasVar to the list of this instance's linked datasets:
            self.datasets.append(dataset)
            current_index += 1
        
    def __str__(self):
        """Define what shows when an instance is printed or shown as a string"""
        return f'Hydro data with {len(self.datasets)} measurements .'

####### Meteo data: ########################################################

class MeteoData:
    """
    Loads and stores meteorological data, and allows it to be exported to WEAP formats.
    Uses the MeasVar class in this module to handle separate variables.
    """
    
    def __init__(self, file_name:str,
        station_list:list,
        model_cal_start:str,
        model_cal_end:str,
        measurements:list=['Precip', 'Temp_max', 'Temp_min', 'Relative humidity']
        ):
        """
        
        Parameters:
        file_name: filename.ext string for Excel spreadsheet with meteorological data
        station_list: list of strings representing station names. Must match column names in worksheets
        model_cal_start: start date of the desired calibration time period
        model_cal_end: end date of the desired calibration time period
        measurements: list of meteorological variables to include. Must match worksheet names in spreadsheet
        
        Notes:
        - Climate data are stored in one excel file, with a worksheet for each variable.
        - Each worksheet has a column for each weather station
        - Start and end dates must be in a valid ISO8601 format as per datetime.datetime.fromisoformat()
        """
        
        #Store the basic info in this instance
        self.input_file_name = file_name.split('.')[0]
        self.stations = station_list
        
        #Load date info for this instance:
        self.mc_start = util.date_standardiser(model_cal_start)
        self.mc_end = util.date_standardiser(model_cal_end)
        date_array = pd.date_range(start=self.mc_start, end=self.mc_end).date
        self.date_range = [date.strftime('%Y-%m-%d') for date in date_array]
        
        #Get the directory relative to the current script (dataprep.py)
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        #Construct the path to the InputData folder
        input_data_path = os.path.join(current_dir, r'InputData\Meteo')
        #Add the file name to the path:
        self.data_path = os.path.join(input_data_path, file_name)
        #Same for output location:
        self.output_loc = os.path.join(current_dir, r'OutputData')
        
        #Load the excel file and work out what variables are included
        self.input_file = pd.ExcelFile(self.data_path)
        checked_measures = util.compare_sheet_names(self.input_file.sheet_names, measurements)
        
        self.datasets = []
        #Create a MeasVar instance for each of the desired measurements:
        for variable in checked_measures:
            #Get the worksheet corresponding to the current variable
            this_df = pd.read_excel(self.data_path, variable, parse_dates=['Date'])
            og_length = this_df.shape[0]
            
            #Standardise the date column and set it as the index:
            this_df['Date'] = this_df['Date'].apply(util.date_standardiser)
            this_df = this_df.dropna(subset=['Date'])
            new_length = this_df.shape[0]
            skipped_rows = og_length - new_length
            this_df.set_index('Date', inplace=True)
            
            #Only get columns matching stations in our desired list:
            this_df = this_df.loc[:, this_df.columns.isin(self.stations)]
            #Create a linked MeasVar instance to store it as a formatted dataset:
            dataset = MeasVar(
                this_df,
                variable,
                self.date_range,
                parent=self,
                skipped_rows=skipped_rows
            )
            #Add the MeasVar to the list of this instance's linked datasets:
            self.datasets.append(dataset)
        
        def __str__(self):
            """
            Placeholder string function
            """
            return f'Meteo data with {len(self.datasets)} measurements .'

####### LULC data: ########################################################

class LulcData:
    """
    Loads and stores land use/land cover data, and allows it to be exported to WEAP formats.
    """
    
    def __init__(self, raster_file_name:str, vector_file_name:str, raster_res=30):
        """
        Load summary statistics for Land Use / Land Cover data by subcatchment
        
        Parameters:
        raster_file_name: filename.ext for a raster with values for LULC ICIMOD land use classification
        vector_file_name: filename.ext for a shapefile of subcatchment areas
        raster_res: spatial resolution (pixel size) of the input raster, in metres
        
        Notes:
        - LULC raster MUST be an integer raster which corresponds to standard ICIMOD classifications
        
        """
        #Get names of the input files:
        self.input_raster_file_name = raster_file_name.split('.')[0]
        self.input_vector_file_name = vector_file_name.split('.')[0]
        #Get the directory relative to the current script (dataprep.py)
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        #Construct the paths to the InputData folders
        input_raster_path = os.path.join(current_dir, r'InputData\LandUse')
        input_vector_path = os.path.join(current_dir, r'InputData\Catchments')
        
        #Add the file names to the paths:
        self.raster_data_path = os.path.join(input_raster_path, raster_file_name)
        self.vector_data_path = os.path.join(input_vector_path, vector_file_name)
        
        #Same for output location:
        self.output_loc = os.path.join(current_dir, r'OutputData')
        
        #Define ICIMOD LULC classes from corresponding integer rasters
        icimod_lulc_class_dict = {
            1: "Waterbody",
            2: "Glacier",
            3: "Snow",
            4: "Forest",
            5: "Riverbed",
            6: "Built-up area",
            7: "Cropland",
            8: "Bare soil",
            9: "Bare rock",
            10: "Grassland",
            11: "Other wooded land",
            15: 'None'
        }
        
        #Get and store some basic details about the input raster:
        self.pixel_res = raster_res
        self.pixel_area = self.pixel_res ** 2
        self.pixel_area_ha = self.pixel_area / 10000
        
        #Get key components of the raster file and store them in the class instance:
        self.raster_info, self.raster_values, self.raster_meta = util.get_raster_deets(self.raster_data_path)
        print(f'Land use raster read. Its CRS is EPSG:{self.raster_info['crs']}')
        
        #Check that the shapefile is in the same CRS as the raster:
        input_shape = gpd.read_file(self.vector_data_path)
        print(f'Subcatchments shape file read. Its CRS is EPSG:{input_shape.crs.to_epsg()}')
        if input_shape.crs.to_epsg() != self.raster_info['crs']:
            print(f'Reprojecting subcatchments file to {self.raster_info['crs']}...')
            self.subcatchments = input_shape.to_crs(epsg=self.raster_info['crs'])
        else:
            self.subcatchments = input_shape
        
        #Get a table of pixel frequencies for each subcatchment:
        self.raw_stats = util.get_zonal_stats(
            self.raster_values,
            self.raster_meta,
            self.subcatchments,
            icimod_lulc_class_dict
        )
        
    def to_weap_data(self, start_year:int=2000, end_year:int=2021):
        """
        Reformat the base_data to match WEAP's required CSV format, and write it as a file to the instance's
        output location.
        
        Parameters:
        start_year: first year in the desired modelling timeframe
        end_year: last year in the desired modelling timeframe.
        
        Notes:
        - Will create a CSV for each subcatchment in this LulcData instance's subcatchment
        - Output files have a row for each year, but the data is the same for each row. This is not intended
        to actually model land use classifications at a particular point in time.
        """
        name_header = 'Subcatchment Name'
        out_stats_all = self.raw_stats.reset_index(names=name_header)
        #Convert pixel counts to areas in Ha:
        for col in out_stats_all.columns[1:]:
            out_stats_all[col] = out_stats_all[col] * self.pixel_area_ha
        
        #Combine columns to get the ones WEAP is expecting:
        out_stats_all['Dense forest'] = out_stats_all['Forest'] + out_stats_all['Other wooded land']
        out_stats_all['Updated grassland'] = out_stats_all['Grassland'] + out_stats_all['Bare soil'] + out_stats_all['Bare rock']
        out_stats_all['Water'] = out_stats_all['Waterbody'] + out_stats_all['Riverbed']
        out_stats_all = out_stats_all.rename(columns={
            'Cropland':'Agriculture [ha]',
            'Dense forest':'Forest [ha]',
            'Updated grassland':'Grassland [ha]',
            'Water':'Waterbody [ha]',
            'Built-up area':'Urban [ha]'
        })
        selected_LULC = ['Agriculture [ha]', 'Forest [ha]', 'Grassland [ha]', 'Waterbody [ha]', 'Urban [ha]']
        #List of years between start and end
        years = list(range(start_year, end_year))
        
        #Dictionary to store dataframes as they are created in the next steps:
        sub_catchment_dfs = {}
        
        #Loop through each subcatchment in the main one:
        for _, row in out_stats_all.iterrows():
            #Store current subcatchment name for the output file
            subcatchment = row[name_header]
            
            #Create header lines needed for WEAP output file:
            header_lines = [
                [f'# Catchment {subcatchment}', '', '', ''],
                ['$ListSeparator = ,', '', '', ''],
                ['$DecimalSymbol = .', '', '', '']
            ]
            
            #Create a dataframe with a row for each year in the modelling timeframe:
            time_series_df = pd.DataFrame({'$Columns = Year' :years})
            
            #For each type of land use in selected_LULC, create a column for that LU, with the same value
            #for each year in the time period (values will stay constant through time):
            for land_use in selected_LULC:
                time_series_df[land_use] = row[land_use]
            
            #Add lines to match required formatting of WEAP files:
            num_blanks  = [ '' for i in range(len(time_series_df.columns) - 1)]
            time_series_df.columns = pd.MultiIndex.from_tuples(
                zip(
                    [f'# Catchment {subcatchment}'] + num_blanks,
                    ['$ListSeparator = ,'] + num_blanks,
                    ['$DecimalSymbol = .'] + num_blanks,
                    time_series_df.columns
                )
            )
            
            #Write file to CSV with sensible name
            area = self.input_vector_file_name.split('_')[0]
            this_filename = f'{area}_{subcatchment}_LULC_Areas'
            time_series_df.to_csv(rf'{self.output_loc}\{this_filename}.csv', index=False)
            
        return True
        
    def __str__(self):
        """Define what to show when instance is presented as a string"""
        return f'Land Use/Land Cover data for {self.input_vector_file_name.split('_')[0]}.'

####### Urban Demand data: ########################################################

class UrbDemData:
    """
    Placeholder docstring
    """
    
    def __init__(self, municipality:str,
        start_date:str,
        end_date:str,
        pop_data_file:str,
        student_data_file:str,
        wards_data_file:str,
        utility_data_files:list,
        perc_full_plumb,
        num_hotels,
        num_hotel_beds,
        num_hospitals,
        num_hospital_beds,
        demand_full_plumb_home:float=0.112,
        demand_not_plumb_home:float=0.045,
        demand_student:float=0.01,
        census_year:int=2021
        ):
        """
        Collate and load data required for urban water demand calculations.
        
        Parameters:
        municipality: Name of the municipality (Pokhara, Tulsipur etc.) of interest
        start_date: start date for the WEAP modelling (inclusive)
        end_date: end date for modelling (inclusive)
        pop_data_file: filename.ext for excel file containing population summaries per ward
        student_data_file: filename.ext for excel file containing number of students per ward
        wards_data_file: filename.ext for shapefile of ward boundaries
        utility_data_files: list of filename.ext strings for shapefiles of water utility service areas
        perc_full_plumb: integer representing the percentage of homes in the municipality with plumbing
        num_hotels: number of hotels reported in Nepal 2021 to scale OpenStreetMap data to
        num_hotel_beds: average number of beds per hotel
        num_hospitals: number of hospitals reported in Nepal 2021 to scale OpenStreetMap data to
        num_hospital_beds: average number of beds per hospital
        demand_full_plumb_home: assumed daily water demand, per person, in cubic metres (m3/d) for plumbed home
        demand_not_plumb_home: assumed daily water demand, per person, in cubic metres (m3/d) for un-plumbed home
        demand_student: assumed daily water demand per student
        census_year: year the census we are using data for was conducted
        
        Notes:
        - All relevant data files must be stored in the package's InputData\Demand folder
        - Start and end dates must be in a valid ISO8601 format as per datetime.datetime.fromisoformat()
        """
        
        #Get the directory relative to the current script (dataprep.py)
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        #Construct the path to the InputData folder
        input_data_loc = os.path.join(current_dir, r'InputData\Demand')
        #Set the location for output files:
        self.output_loc = os.path.join(current_dir, r'OutputData')
        
        #Bring in the wards:
        input_wards = gpd.read_file(os.path.join(input_data_loc, wards_data_file))
        print(f'Wards file read. Its CRS is EPSG:{input_wards.crs.to_epsg()}')
        if input_wards.crs.to_epsg() != 4326:
            print(f'Reprojecting wards file to WGS84 GCS (EPSG:4326)...')
            self.wards = input_wards.to_crs(epsg=4326)
        else:
            self.wards = input_wards
        #Get useful info for later:
        self.minx = self.wards.total_bounds[0]
        self.miny = self.wards.total_bounds[1]
        self.maxx = self.wards.total_bounds[2]
        self.maxy = self.wards.total_bounds[3]
        
        
        
        #Check that plumbing values are correct
        if perc_full_plumb < 0 or perc_full_plumb > 100:
            raise ValueError(f'perc_full_plumb must be an integer in range [0,100] but {perc_full_plumb} was provided.')
        #Store static parameters:
        self.municipality = municipality
        self.start_date = util.date_standardiser(start_date)
        self.end_date = util.date_standardiser(end_date)
        self.propn_full_plumb = perc_full_plumb / 100
        self.propn_not_plumb = 1 - self.propn_full_plumb
        self.num_hotels = num_hotels
        self.num_hotel_beds = num_hotel_beds
        self.num_hospitals = num_hospitals
        self.num_hospital_beds = num_hospital_beds
        self.demand_full_plumb_home = demand_full_plumb_home
        self.demand_not_plumb_home = demand_not_plumb_home
        self.demand_student = demand_student
        self.census_year = census_year
        
        ####### Domestic demands: #######
        #Read in the excel file:
        pop_data = pd.read_excel(os.path.join(input_data_loc, pop_data_file))
        pop_data = pop_data[['Ward', 'Total population', 'Number of households', 'Average household size']]
        
        #Calculate a domestic demand column:
        pop_data['Household pop'] = pop_data['Number of households'] * pop_data['Average household size']
        pop_data['Fully plumbed pop'] = pop_data['Household pop'] * self.propn_full_plumb
        pop_data['Not plumbed pop'] = pop_data['Household pop'] * self.propn_not_plumb
        pop_data['Domestic demand [m3/d]'] = (
            (pop_data['Fully plumbed pop'] * demand_full_plumb_home)
            +
            (pop_data['Not plumbed pop'] * demand_not_plumb_home)
        )
        #Trim the helper columns and start building a summary dataframe:
        demand_data = pop_data.drop(labels=[
                'Total population',
                'Number of households',
                'Average household size',
                'Household pop',
                'Fully plumbed pop',
                'Not plumbed pop',
            ],
            axis='columns'
        ).set_index('Ward')
        
        ####### Institutional demands (educational): #######
        #Read in the excel file:
        inst_data = pd.read_excel(os.path.join(input_data_loc, student_data_file))
        #Calculate the demand column:
        inst_data['Institutional demand [m3/d]'] = inst_data['Currently attending'] * self.demand_student
        inst_data = inst_data.drop(labels=['Currently attending'], axis='columns').set_index('Ward')
        demand_data = demand_data.merge(inst_data, how='outer', left_index=True, right_index=True)
        
        ####### Commercial demands: #######
        #Get a geodataframe with their locations:
        self.hotel_locs = util.get_osm_locations(
            {'tourism': 'hotel'},
            (self.miny, self.minx, self.maxy, self.maxx)
        )
        self.hospital_locs = util.get_osm_locations(
            {'amenity': 'hospital'},
            (self.miny, self.minx, self.maxy, self.maxx)
        )
        
        #Get dataframes with their total census numbers, distributed according to their OSM distribution:
        scaled_hotel = util.rescale_to_census(
            self.hotel_locs,
            self.wards,
            self.num_hotels,
            'Hotel'
        )
        print(scaled_hotel)
        scaled_hospital = util.rescale_to_census(
            self.hospital_locs,
            self.wards,
            self.num_hospitals,
            'Hospital'
        )
        print(scaled_hospital)
        
        pass
        
    def __str__(self):
        """Define what to show when instance is presented as a string"""
        pass