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
    
    def __init__(self):
        """
        Placeholder init function. This will do most of the work
        """
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

