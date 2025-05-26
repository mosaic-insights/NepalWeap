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
import os
import datetime as dt
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
    date_column:str,
    save:bool=False
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
    - save (bool): whether to save the figures in the OutputData folder,
    defaults to False.
    
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
    
    #Get the directory relative to the current script (outputvis.py)
    current_dir = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
        )
    #Construct the path to the InputData folder
    input_data_path = os.path.join(current_dir, r'InputData\WeapOutputs')
    #Add the file names to the path:
    summary_path = os.path.join(input_data_path, summary_outputs)
    comparison_path = os.path.join(input_data_path, streamflow_comparison)
    exceedance_path = os.path.join(input_data_path, streamflow_exceedance)
    #Same for output location:
    output_loc = os.path.join(current_dir, r'OutputData')
    
    #-------------------------------------------------------------------
    # CATCHMENT WATER BALANCE FIGURE
    # load summary catchment data
    summary_data = pd.read_excel(summary_path)

    # set date column in datetime format
    summary_data[date_column] = pd.to_datetime(summary_data[date_column])
    summary_data['month'] = summary_data[date_column].dt.month

    # get monthly averages of the summary data
    monthly_avg = summary_data.groupby('month').mean(numeric_only = True)

    #Save calculated averages in an Excel file:
    monthly_avg.to_excel(
        os.path.join(output_loc, 'monthly_avgs.xlsx'),
        index=False
        )

    #Specify colours to use for plot:
    summary_colour_list = [
        'blue',
        'cornflowerblue',
        'yellow',
        'orange',
        'red',
        'indianred',
        'maroon'
        ]
    
    # plot the monthly averages
    plt.figure(figsize = (10, 5))
    columns = monthly_avg.columns
    num_colors = len(summary_colour_list)
    #Plot each column individually to the current figure, with its
    #associated colour:
    for i, column in enumerate(columns):
        color = summary_colour_list[i]
        plt.plot(
            monthly_avg.index,
            monthly_avg[column],
            label=column,
            color=color
            )
    #Format chart:
    plt.xlabel('Month', fontsize = 12)
    plt.ylabel('Quantities of water (mm)', fontsize = 12)
    plt.xticks(ticks=range(1, 13), labels=[
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ])
    plt.legend()
    plt.tight_layout()
    
    #Save to OutputData if save is True
    if save:
        plt.savefig(
            'Summary outputs.png',
            dpi=300,
            bbox_inches='tight'
            )
    
    #-------------------------------------------------------------------
    # STREAMFLOW COMPARISON FIGURE
    
    # load streamflow comparison data
    sfc_data = pd.read_excel(comparison_path)

    # set date column to datetime format
    sfc_data[date_column] = pd.to_datetime(sfc_data[date_column])
    sfc_data['month'] = sfc_data[date_column].dt.month

    #Get monthly average streamflow and save as Excel file:
    sfc_monthly_avg = sfc_data.groupby('month').mean(numeric_only=True)
    sfc_monthly_avg.to_excel(
        os.path.join(output_loc, 'sfc_monthly_avgs.xlsx'),
        index=False
        )
    
    #Specify colours to use for plot:
    comparison_color_list = ['royalblue', 'tomato']
    
    #Plot the monthly averages:
    plt.figure(figsize = (10, 5))
    columns = sfc_monthly_avg.columns
    num_colors = len(comparison_color_list)
    #Plot each column individually to the current figure, with its
    #associated colour:
    for i, column in enumerate(columns):
        color = comparison_color_list[i]
        plt.plot(
            sfc_monthly_avg.index,
            sfc_monthly_avg[column],
            label=column,
            color=color
            )
    
    #Format the chart:
    plt.xlabel('Month', fontsize = 12)
    plt.ylabel('Streamflow (Megaliters)', fontsize = 12)
    plt.xticks(ticks=range(1, 13), labels=[
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
    ])
    plt.legend()
    plt.tight_layout()
    
    #Save to output data if save is True:
    if save:
        plt.savefig(
            'Streamflow comparison.png',
            dpi=300,
            bbox_inches='tight'
            )
    #-------------------------------------------------------------------
    # STREAMFLOW EXCEEDANCE FIGURE

    # load data of streamflow exceedances
    sf_exc = pd.read_excel(exceedance_path)

    # convert exceedance from decimal to percentage
    sf_exc['Statistic'] = sf_exc['Statistic'] * 100

    color_list = ['royalblue', 'tomato']

    # plot exceedances
    plt.figure(figsize = (10, 5))
    num_colors = len(color_list)

    plt.plot(
        sf_exc['Statistic'],
        sf_exc['Modeled'],
        label='Modeled',
        color=color_list[0]
        )
    plt.plot(
        sf_exc['Statistic'],
        sf_exc['Observed'],
        label='Observed',
        color = color_list[1]
        )
        
    #Format the chart:
    plt.yscale('log')
    plt.xlabel('Percent of time exceeded', fontsize = 12)
    plt.ylabel('Flow volume (Megaliters)', fontsize = 12)
    plt.legend()
    plt.tight_layout()

    if save:
        plt.savefig(
            'Streamflow exceedance.png',
            dpi=300,
            bbox_inches='tight'
            )

