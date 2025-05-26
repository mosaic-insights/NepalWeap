"""
------------------------------------------------------------------------
Module Name: outputvis
Parent Package: NepalWeapTools

******* Metadata *******
__author__ = ['Kristen Joyce', 'Richard Farr']
__copyright__ = 'Alluvium Consulting (TBC)'
__credits__ = ['Petter Nyman']
__version__ = 0.01
__maintainer__ = 'Richard Farr'
__email__ = 'richard.farr@alluvium.com.au'
__status__ = 'In development'

Last update: 26/05/2025

******* Description *******
Part of the NepalWeapTools package, this module takes the ouput files
produced by WEAP and plots them for visual interpretation.
------------------------------------------------------------------------
"""
####### Package imports: ######################################################
from . import util
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

####### Standard WEAP outputs: ################################################
#-----------------------------------------------------------------------
def plot_weap_outputs(
    summary_outputs:str,
    streamflow_comparison:str,
    streamflow_exceedance:str,
    date_column:str
    ):
    """
    Takes the three main WEAP outputs and plots them.
    
    Parameters:
    - summary_outputs (str): filename.ext string for excel file with
    daily outputs from the "Land Class Inflows and Outflows" section
    of the WEAP results tab
    - streamflow_comparison (str): filename.ext string for excel file
    with daily outputs from the 'Streamflow Gauge Comparison' section of
    the WEAP results tab
    - streamflow_exceedance (str): filename.ext string for excel file
    modelled and observed streamflow volumes for different exceedance
    levels
    - date (str): name of the date column in the cleaned input files
    above
    
    --------------------------------------------------------------------
    Notes:
    - WEAP output files must be cleaned PRIOR to running this function.
    The steps required are as follows:
        1. Delete sum columns and rows
        2. Delete the first three header rows
        3. Ensure the date column is labelled 'Date'
        4. Change streamflow volums to megalitres
    - Excel files must be stored in the InputData\WeapOutputs package
    folder
    - When selecting data for summary_outputs, only delineated
    sub-catchments (and not demand nodes) should be selected
    - When selecting data for streamflow_exceedance, check the 'Percent
    of Time Exceeded' and 'Log' buttons in the 'Streamflot Gauge
    Comparison' section.
    - Date column values must be in a valid ISO8601 format as per
    datetime.datetime.fromisoformat()
    
    --------------------------------------------------------------------
    """
    

