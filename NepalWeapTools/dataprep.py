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
        file_name will be deprecated once data is stored in a static path relative to the module.
        User will then just input the station list.
        """
        
        #Get the directory relative to the current script (dataprep.py)
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        print(current_dir)
        #Construct the path to the InputData folder
        input_data_path = os.path.join(current_dir, r'InputData\Hydro')
        print(input_data_path)
        #Add the file name to the path:
        self.data_path = os.path.join(input_data_path, file_name)
        print('data path:', self.data_path)
        
        sf_data = pd.read_excel(self.data_path, station_list[0])
        print(sf_data)
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

