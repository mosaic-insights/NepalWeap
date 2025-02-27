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

Last update: 26/02/2025

******* Description *******
Part of the NepalWeapTools package, this module takes inputs of various 
catchment variable as datsets and converts them into output formats
that are readable by the Stockholm Environment Institute's Water
Evaluation And Planning (WEAP) software.
------------------------------------------------------------------------
"""
####### Module Imports: #######
import numpy as np
import pandas as pd
import os
import datetime as dt
import matplotlib as mpl
import matplotlib.pyplot as plt

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

####### Hydro data: #######

class HydroData:
    
    def __init__(self, file_name:str, station_list:list, model_cal_start:str, model_cal_end:str):
        """
        Read input streamflow data file and store with instance as dataframe
        
        Parameters:
        file_name: path to file with raw stream gauge data
        station_list: list of names of stremflow gauge stations to be examined
        model_cal_start: start date of the desired calibration time preiod in format YYYY-MM-DD
        model_cal_end: end date of the desired calibration time preiod in format YYYY-MM-DD
        
        Returns:
        True if the file was loaded successfully, False otherwise.
        
        Notes:
        - file_name will be deprecated once data is stored in a static path relative to the module.
        - User will then just input the station list.
        - Dates must be in a valid ISO8601 format as per datetime.date.fromisoformat()
        - Names of stations in the station list must exactly match the worksheet names
        """
        #------------TODO: Move this to util module---------------
        def date_standardiser(date_string):
            """Convert date string to YYYY-MM-DD"""
            # Try to parse the date_string assuming its in an ISO format
            try:
                date_object = dt.datetime.fromisoformat(str(date_string)).date() 
            except ValueError:
                date_object = dt.datetime.strptime(date_string, '%d/%b/%Y').date()
            # If successful, format the date_object to 'YYYY-MM-DD' and return it
            return date_object.strftime('%Y-%m-%d')
            
        #----------------------------------
        
        #Load date info for this instance:
        self.mc_start = date_standardiser(model_cal_start)
        self.mc_end = date_standardiser(model_cal_end)
        date_array = pd.date_range(start=self.mc_start, end=self.mc_end).date
        self.date_range = [date.strftime('%Y-%m-%d') for date in date_array]
        
        print(f'Start: {self.mc_start}, End: {self.mc_end}')
        
        #Get the directory relative to the current script (dataprep.py)
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        #Construct the path to the InputData folder
        input_data_path = os.path.join(current_dir, r'InputData\Hydro')
        #Add the file name to the path:
        self.data_path = os.path.join(input_data_path, file_name)
        
        #Load an empty dataframe with dates as the index:
        self.base_data = pd.DataFrame(index=self.date_range)
        
        
        #Go through each station in the station list and load the data:
        for station in station_list:
            #Read in the excel file:
            sf_data = pd.read_excel(self.data_path, station, parse_dates=['Date'])
            #Standardise the date:
            sf_data['Date'] = sf_data['Date'].apply(date_standardiser)
            sf_data.rename(columns={'Streamflow m3/s': station}, inplace=True)
            sf_data.set_index('Date', inplace=True)
            #Merge with the existing base_data
            self.base_data = self.base_data.merge(sf_data, left_index=True, right_index=True, how='left')
        
        
        
        
        pass
        
    def __str__(self):
        """
        Placeholder string function
        """
        pass
        
    def to_weap_data(self):
        """
        Placeholder to convert to WEAP format and save as file
        """
        pass
        
    def vis(self):
        """
        Placeholder to visualise the processed data as a chart
        """
        pass

