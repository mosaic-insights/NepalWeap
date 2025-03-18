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
####### Module Imports: #######################################################
from . import util
import numpy as np
import pandas as pd
import geopandas as gpd
import os
import matplotlib as mpl
import matplotlib.pyplot as plt
import rasterio as rio

####### For when module is run directly: ######################################
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

#------------------------------------------------------------------------------
####### Measured variables: ###################################################
#------------------------------------------------------------------------------

class MeasVar:
    """
    Store data for individual variables that area measured, such as 
    streamflow or temperature.
    Allows broad classes to be extended to incorporate variables that 
    are not currently included.
    --------------------------------------------------------------------
    --------------------------------------------------------------------
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
        Read and store a dataframe passed from a HydroData or MeteoData
        instance.
        
        Parameters:
        - dataframe: a pandas dataframe with a row for each date and 
        column for each station.
        - date_range: a list of observation dates to include
        - parent: the instance of HydroData or MeteoData which created
        this instance
        - unit: if a unit is specified or known, this will be
        incorporated into the output column name.
        - skipped_rows: for audit trail purposes; the number of rows
        with date values that couldn't be handled by the source 
        instance.
        ----------------------------------------------------------------
        ----------------------------------------------------------------
        """
        ####### Method start ##################################################
        self.measure = measure
        self.date_range = date_range
        self.unit = unit
        self.parent = parent
        self.skipped_rows = skipped_rows
        
        #Load an empty dataframe with dates as the index:
        self.base_data = pd.DataFrame(index=self.date_range)
        self.base_data = self.base_data.merge(
            dataframe,
            left_index=True,
            right_index=True,
            how='left'
            )
        
    def vis(self, ax):
        """
        Visualise data for each station on a line chart.
        
        Parameters:
        - ax: Matplotlib axes object to plot on
        
        ----------------------------------------------------------------
        Notes:
        - Axes object must be provided. Instances of hydro or meteo data
        will create axes as required then use this method to plot.
        ----------------------------------------------------------------
        """
        ####### Method start ##################################################
        #Generate text for axis title:
        axis_title = (
            f'Time series plot of {self.measure} at '
            f'{len(self.base_data.columns)} sites'
            )
        #Store useful info:
        start_date = self.date_range[0]
        end_date = self.date_range[-1]
        num_years = (int(end_date[:4]) - int(start_date[:4]))
        
        #Instance of the dataframe with date object index:
        for_plotting = self.base_data
        for_plotting.index = pd.to_datetime(for_plotting.index)
        
        #Go through each station and plot its values:
        for col in for_plotting.columns:
            #Plot the current column, specifying label
            ax.plot(for_plotting.index, for_plotting[col], label=col)
        
        #Activate title and enable leend
        ax.set_title(axis_title)
        ax.legend()
        
        #Set the x-axis ticks and labels appropriately:
        util.x_axis_dater(ax, num_years)
        ax.set_xlabel('Date')
        
        #Set the y-axis label appropriately
        if self.unit != 'Unspecified':
            ax.set_ylabel(f'{self.measure} [{self.unit}]')
        else:
            ax.set_ylabel(f'{self.measure}')
        
        
    def to_weap_data(self):
        """
        Reformat the base_data to match WEAP's required CSV format, and
        write it as a file to the instance's output location.
        ----------------------------------------------------------------
        ----------------------------------------------------------------
        """
        ####### Method start ##################################################
        #Get an updated copy of the base_data with the date moved out of
        #the index, leaving the original untouched:
        w_data = self.base_data.reset_index(names='$Columns = Date')
        if self.unit != 'Unspecified':
            w_data.columns = (
                [col + f' [{self.unit}]' for col in w_data.columns]
                )
            
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
        out_file_path = (
            rf'{self.parent.output_loc}\{self.parent.input_file_name}'
            rf'_{self.measure}.csv'
            )
        w_data.to_csv(out_file_path, index=False)
        
        return True
        
    def __str__(self):
        """Define how to represent this as a string"""
        output_string = (
            'Set of {} recordings between {} and {}, for {} stations.'
            ).format(
                self.measure,
                self.date_range[0],
                self.date_range[-1],
                len(self.base_data.columns)
                )
        return output_string

#------------------------------------------------------------------------------
####### Hydro data: ###########################################################
#------------------------------------------------------------------------------

class HydroData:
    """
    Loads and stores hydrological data, and allows it to be exported to
    WEAP formats.
    Currently only streamflow is measured, but this class uses the
    MeasVar class in this module to handle separate variables, so is 
    extensible to additional hydro variables.
    --------------------------------------------------------------------
    --------------------------------------------------------------------
    """
    
    def __init__(self, file_name:str,
        station_list:list,
        model_cal_start:str,
        model_cal_end:str,
        measurements:list=['Streamflow'],
        units:list=['m3/s']
        ):
        """
        Read input streamflow data file and store with instance as
        dataframe
        
        Parameters:
        - file_name: path to file with raw stream gauge data
        - station_list: list of names of streamflow gauge stations to be
        examined. Must match worksheet names
        - model_cal_start: start date of the desired calibration time
        period in format YYYY-MM-DD
        - model_cal_end: end date of the desired calibration time period
        in format YYYY-MM-DD
        - measurements: list of hydrological variables to include
        - units: list of strings representing units of the corresponding
        entries in measurements
        
        ----------------------------------------------------------------
        Notes:
        - file_name will be deprecated once data is stored in a static 
        path relative to the module.
        - User will then just input the station list.
        - Dates must be in a valid ISO8601 format as per 
        datetime.date.fromisoformat()
        - Names of stations in the station list must exactly match the
        worksheet names
        - This code assumes there is only one variable per worksheet
        ----------------------------------------------------------------
        """
        ####### Method start ##################################################
        #Get the directory relative to the current script (dataprep.py)
        current_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
            )
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
        checked_stations = util.compare_sheet_names(
            self.input_file.sheet_names,
            self.stations
            )
        
        ####### Loading data by variable: #####################################
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
                this_df = pd.read_excel(
                    self.data_path,
                    station,
                    parse_dates=['Date']
                    )
                #Standardise the date:
                og_length = this_df.shape[0]
                this_df['Date'] = this_df['Date'].apply(util.date_standardiser)
                this_df = this_df.dropna(subset=['Date'])
                new_length = this_df.shape[0]
                skipped_rows += (og_length - new_length)
                this_df.set_index('Date', inplace=True)
                this_df.columns=[station]
                base_var_df = base_var_df.merge(
                    this_df,
                    left_index=True,
                    right_index=True,
                    how='left'
                    )
            
            #Create a linked MeasVar instance to store it as a formatted
            #dataset:
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
        """Define what shows when an instance is shown as a string"""
        return f'Hydro data with {len(self.datasets)} measurements .'

    def vis(self, axes=None):
        """
        Visualise data for each station on a line chart.
        
        Parameters:
        - ax: Matplotlib axes object to plot on, if plotting to a
        specific fig/ax is required
        
        ----------------------------------------------------------------
        Notes:
        - Will plot to a provided fig/ax if provided, otherwise creates
        a new fig/ax subplot
        - Current version assumes that there is only one variable 
        (streamflow). Method will need to be extended if additional 
        hydro variables are captured.
        ----------------------------------------------------------------
        """
        ####### Method start ##################################################
        #Determine behaviour based on whether an axes object is supplied
        if axes is not None:
            ax = axes
        else:
            fig, ax = plt.subplots()
            
        self.datasets[0].vis(ax)
        
            

#------------------------------------------------------------------------------
####### Meteo data: ###########################################################
#------------------------------------------------------------------------------

class MeteoData:
    """
    Loads and stores meteorological data, and allows it to be exported
    to WEAP formats.
    Uses the MeasVar class in this module to handle separate variables.
    --------------------------------------------------------------------
    --------------------------------------------------------------------
    """
    
    def __init__(self, file_name:str,
        station_list:list,
        model_cal_start:str,
        model_cal_end:str,
        measurements:list=[
            'Precip',
            'Temp_max',
            'Temp_min',
            'Relative humidity'
            ]
        ):
        """
        Read input meteorological data file and store with instance as
        dataframe
        
        Parameters:
        - file_name: filename.ext string for Excel spreadsheet with 
        meteorological data
        - station_list: list of strings representing station names.
        Must match column names in worksheets
        - model_cal_start: start date of the desired calibration time
        period
        - model_cal_end: end date of the desired calibration time
        period
        - measurements: list of meteorological variables to include.
        Must match worksheet names in spreadsheet
        
        ----------------------------------------------------------------
        Notes:
        - Climate data are stored in one excel file, with a worksheet
        for each variable.
        - Each worksheet has a column for each weather station
        - Start and end dates must be in a valid ISO8601 format as per
        datetime.datetime.fromisoformat()
        ----------------------------------------------------------------
        """
        ####### Method start ##################################################
        #Store the basic info in this instance
        self.input_file_name = file_name.split('.')[0]
        self.stations = station_list
        
        #Load date info for this instance:
        self.mc_start = util.date_standardiser(model_cal_start)
        self.mc_end = util.date_standardiser(model_cal_end)
        date_array = pd.date_range(start=self.mc_start, end=self.mc_end).date
        self.date_range = [date.strftime('%Y-%m-%d') for date in date_array]
        
        #Get the directory relative to the current script (dataprep.py)
        current_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
            )
        #Construct the path to the InputData folder
        input_data_path = os.path.join(current_dir, r'InputData\Meteo')
        #Add the file name to the path:
        self.data_path = os.path.join(input_data_path, file_name)
        #Same for output location:
        self.output_loc = os.path.join(current_dir, r'OutputData')
        
        #Load the excel file and work out what variables are included
        self.input_file = pd.ExcelFile(self.data_path)
        checked_measures = util.compare_sheet_names(
            self.input_file.sheet_names,
            measurements
            )
        
        ####### Loading data by variable: #####################################
        self.datasets = []
        #Create a MeasVar instance for each of the desired measurements:
        for variable in checked_measures:
            #Get the worksheet corresponding to the current variable
            this_df = pd.read_excel(
                self.data_path,
                variable,
                parse_dates=['Date']
                )
            og_length = this_df.shape[0]
            
            #Standardise the date column and set it as the index:
            this_df['Date'] = this_df['Date'].apply(util.date_standardiser)
            this_df = this_df.dropna(subset=['Date'])
            new_length = this_df.shape[0]
            skipped_rows = og_length - new_length
            this_df.set_index('Date', inplace=True)
            
            #Only get columns matching stations in our desired list:
            this_df = this_df.loc[:, this_df.columns.isin(self.stations)]
            #Create a linked MeasVar instance to store it as a formatted
            #dataset:
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
        Define what shows when an instance is shown as a string
        """
        return f'Meteo data with {len(self.datasets)} measurements .'
        
    def vis(self):
        """
        Visualise data for each station on a line chart, with a
        separate plot for each variable.
        
        ----------------------------------------------------------------
        Notes:
        - Assumes that all variables are to be plotted. Future versions
        should allow this to be specified when the method is called.
        - Currently does not allow the user to specify a figure or axes;
        given that there could be multiple variables this is currently
        all defined within this method.
        -Ideally this would also allow the user to specify particular
        stations to visualise.
        ----------------------------------------------------------------
        """
        ####### Method start ##################################################
        #Create an empty figure, and start tracking the number of
        #subplot rows required:
        fig = plt.figure()
        rows = 0
        num_vars = len(self.datasets)
        fig_height = 5 * num_vars
        fig.set_figheight(fig_height)
        fig.set_figwidth(12)
        
        #Go through each variable:
        for var in self.datasets:
            
            rows +=1
            this_ax = fig.add_subplot(num_vars, 1, rows)
            
            var.vis(this_ax)
        
        

#------------------------------------------------------------------------------
####### LULC data: ############################################################
#------------------------------------------------------------------------------

class LulcData:
    """
    Loads and stores land use/land cover data, and allows it to be 
    exported to WEAP formats.
    --------------------------------------------------------------------
    --------------------------------------------------------------------
    """
    
    def __init__(
        self,
        raster_file_name:str,
        vector_file_name:str,
        raster_res=30
        ):
        """
        Load summary statistics for Land Use / Land Cover data by
        subcatchment
        
        Parameters:
        - raster_file_name: filename.ext for a raster with values for
        LULC ICIMOD land use classification
        - vector_file_name: filename.ext for a shapefile of subcatchment
        areas
        - raster_res: spatial resolution (pixel size) of the input
        raster, in metres
        ----------------------------------------------------------------
        Notes:
        - LULC raster MUST be an integer raster which corresponds to
        standard ICIMOD classifications
        ----------------------------------------------------------------
        """
        ####### Method start ##################################################
        #Get names of the input files:
        self.input_raster_file_name = raster_file_name.split('.')[0]
        self.input_vector_file_name = vector_file_name.split('.')[0]
        #Get the directory relative to the current script (dataprep.py)
        current_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
            )
        
        #Construct the paths to the InputData folders
        input_raster_path = os.path.join(current_dir, r'InputData\LandUse')
        input_vector_path = os.path.join(current_dir, r'InputData\Catchments')
        
        #Add the file names to the paths:
        self.raster_data_path = os.path.join(
            input_raster_path, raster_file_name
            )
        self.vector_data_path = os.path.join(
            input_vector_path, vector_file_name
            )
        
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
        
        ####### Processing: ###################################################
        #Get key components of the raster file and store them in the class
        #instance:
        self.raster_info, self.raster_values, self.raster_meta = (
            util.get_raster_deets(self.raster_data_path)
            )
        print(
            f'Land use raster read. Its CRS is EPSG:{self.raster_info['crs']}'
            )
        
        #Check that the shapefile is in the same CRS as the raster:
        input_shape = gpd.read_file(self.vector_data_path)
        print(
            'Subcatchments shape file read. Its CRS is'
            f'EPSG:{input_shape.crs.to_epsg()}'
            )
        #If not, reproject it:
        if input_shape.crs.to_epsg() != self.raster_info['crs']:
            print(
                'Reprojecting subcatchments file to '
                f'{self.raster_info['crs']}...'
                )
            self.subcatchments = input_shape.to_crs(
                epsg=self.raster_info['crs']
                )
        else:
            self.subcatchments = input_shape
        
        #Get a table of pixel frequencies for each subcatchment:
        self.raw_stats = util.get_zonal_stats(
            self.raster_values,
            self.raster_meta,
            self.subcatchments,
            icimod_lulc_class_dict
        )
        
    def vis(self, subcatch='all', figure=None, axes=None):
        """
        Visualise the distrubtion of pixels as a pie chart
        
        Parameters:
        - subcatch: name of a subcatchment as defined by this
        instance's subcatchments attribute
        - figure: matplotlib figure object 
        - axes: matplotlib axes object
        
        ----------------------------------------------------------------
        Notes:
        - If no subcatchment is specified, or if the specified one is 
        not in the existing list, this will summarise across all
        subcatchments. 
        - A treemap would have been preferable to a pie chart but also
        required an additional module oustide of standard conda, so it
        was decided to stick with the pie chart
        ----------------------------------------------------------------
        """
        ####### Method start ##################################################
        #Standardise casing of text:
        needle = subcatch.title()
        haystack = self.raw_stats.rename(
            {a: a.title() for a in self.raw_stats.index},
            axis='index'
            )
        #Use the axes if provided, otherwise create one:
        if axes is not None and figure is not None:
            fig = figure
            ax = axes
        elif axes is None and figure is None:
            fig, ax = plt.subplots()
        else:
            raise ValueError(
                'figure and axes objects must either both be specified, '
                'or neither.'
                )
        
        #Summarise all values and plot those if 'all', nothing, or a
        #value not in the raw_stats index is specified:
        if needle == 'All' or needle not in haystack.index:
            print('Summarising data for all catchments. Either no '
                'specific subcatchment was specifed, or specified '
                'value was not in the dataset provided.'
                )
            
            #Get useful values:
            catchment_summary = haystack.sum()
            total_pix = catchment_summary.sum()
            none_sum = catchment_summary['None']
            none_perc = round(((none_sum/total_pix)*100))
            
            #Remove None values to clean up the chart:
            for_plotting = catchment_summary.drop('None')
            
            #Set the overarching figure title:
            fig.suptitle(
                'Distribution of land cover types in '
                f'{self.input_vector_file_name.split('_')[0]}'
                )
        
        #Plot just that subcatchment if it's been specified:
        else:
            print(f'Summarising data for {needle} subcatchment.')
            
            #Get useful values:
            this_subcatch = haystack.loc[needle]
            total_pix = this_subcatch.sum()
            none_sum = this_subcatch['None']
            none_perc = round(((none_sum/total_pix)*100))
            
            #Remove None values to clean up the chart:
            for_plotting = this_subcatch.drop('None')
            
            #Set the overarching figure title:
            fig.suptitle(
                'Distribution of land cover types in '
                f'{self.input_vector_file_name.split('_')[0]}\n'
                f'({needle} subcatchment)'
                )
            
        #Create the pie chart:
        wedges, texts = ax.pie(for_plotting)
        
        #Set the legend outside the axes to the right:
        ax.legend(
            wedges,
            for_plotting.index,
            loc='center left',
            bbox_to_anchor=(1, 0.5)
            )
        #Use the axes 'title' to set a subtitle that shows what
        #percentage of pixels had meaningful classifications:
        ax.set_title(
            f'{none_perc}% of pixels were classified',
            **{'size': 'small'},
            pad=0
            )
        #Show the pie chart:
        plt.show()
        
        
    
    def to_weap_data(self, start_year:int=2000, end_year:int=2021):
        """
        Reformat the base_data to match WEAP's required CSV format, and
        write it as a file to the instance's output location.
        
        Parameters:
        - start_year: first year in the desired modelling timeframe
        - end_year: last year in the desired modelling timeframe.
        
        ----------------------------------------------------------------
        Notes:
        - Will create a CSV for each subcatchment in this LulcData
        instance's subcatchment
        - Output files have a row for each year, but the data is the
        same for each row. This is not intended to actually model land
        use classifications at a particular point in time.
        ----------------------------------------------------------------
        """
        ####### Method start ##################################################
        name_header = 'Subcatchment Name'
        out_stats_all = self.raw_stats.reset_index(names=name_header)
        #Convert pixel counts to areas in Ha:
        for col in out_stats_all.columns[1:]:
            out_stats_all[col] = out_stats_all[col] * self.pixel_area_ha
        
        #Combine columns to get the ones WEAP is expecting:
        out_stats_all['Dense forest'] = (
            out_stats_all['Forest'] +
            out_stats_all['Other wooded land']
            )
        out_stats_all['Updated grassland'] = (
            out_stats_all['Grassland'] +
            out_stats_all['Bare soil'] +
            out_stats_all['Bare rock']
            )
        out_stats_all['Water'] = (
            out_stats_all['Waterbody'] +
            out_stats_all['Riverbed']
            )
        out_stats_all = out_stats_all.rename(columns={
            'Cropland':'Agriculture [ha]',
            'Dense forest':'Forest [ha]',
            'Updated grassland':'Grassland [ha]',
            'Water':'Waterbody [ha]',
            'Built-up area':'Urban [ha]'
        })
        selected_LULC = [
            'Agriculture [ha]',
            'Forest [ha]',
            'Grassland [ha]',
            'Waterbody [ha]',
            'Urban [ha]'
            ]
        
        ####### Generating output files: ######################################
        #List of years between start and end
        years = list(range(start_year, end_year))
        
        #Dictionary to store dataframes as they are created in the next
        #steps:
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
            
            #Create a dataframe with a row for each year in the
            #modelling timeframe:
            time_series_df = pd.DataFrame({'$Columns = Year' :years})
            
            #For each type of land use in selected_LULC, create a column
            #for that LU, with the same value for each year in the time
            #period (values will stay constant through time):
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
            time_series_df.to_csv(
                rf'{self.output_loc}\{this_filename}.csv',
                index=False
                )
        
    def __str__(self):
        """Define what to show when instance is presented as a string"""
        output_string = (
            'Land Use/Land Cover data for '
            f'{self.input_vector_file_name.split('_')[0]}.'
            )
        return output_string

#------------------------------------------------------------------------------
####### Urban Demand data: ####################################################
#------------------------------------------------------------------------------

class UrbDemData:
    """
    Load, calculate, and store water demand data
    --------------------------------------------------------------------
    --------------------------------------------------------------------
    """
    
    def __init__(self,
        municipality:str,
        start_date:str,
        end_date:str,
        pop_data_file,
        student_data_file:str,
        wards_data_file:str,
        utility_data_files:list,
        perc_full_plumb,
        num_hotels,
        num_hotel_beds,
        num_hospitals,
        num_hospital_beds,
        demand_student:float=0.01,
        demand_full_plumb_home:float=0.112,
        demand_not_plumb_home:float=0.045,
        demand_hotel_bed:float=0.2,
        demand_hospital_bed:float=0.5,
        demand_other_comm:float=0.01,
        other_comm_denom=3,
        munic_dem_propn:float=0.075,
        indust_dem_propn:float=0.225,
        census_year:int=2021
        ):
        """
        Collate and load data required for urban water demand
        calculations.
        
        Parameters:
        - municipality: Name of the municipality (Pokhara, 
        Tulsipur etc.) of interest
        - start_date: start date for the WEAP modelling (inclusive)
        - end_date: end date for modelling (inclusive)
        - pop_data_file: filename.ext for excel file containing
        population summaries per ward (can also be a prepared pandas
        dataframe passed from a child class
        - student_data_file: filename.ext for excel file containing
        number of students per ward
        - wards_data_file: filename.ext for shapefile of ward boundaries
        - utility_data_files: list of filename.ext strings for 
        shapefiles of water utility service areas
        - perc_full_plumb: integer representing the percentage of homes
        in the municipality with plumbing
        - num_hotels: number of hotels reported in Nepal 2021 to scale
        OpenStreetMap data to
        - num_hotel_beds: average number of beds per hotel
        - num_hospitals: number of hospitals reported in Nepal 2021 to
        scale OpenStreetMap data to
        - num_hospital_beds: average number of beds per hospital
        - demand_student: assumed daily water demand per student
        - demand_full_plumb_home: assumed daily water demand, per
        person, in cubic metres (m3/d) for plumbed home
        - demand_not_plumb_home: assumed daily water demand, per person,
        in cubic metres (m3/d) for un-plumbed home
        - demand_hotel_bed: assumed daily water demand per bed, in cubic
        metres (m3/d) for a hotel
        - demand_hospital_bed:assumed daily water demand per bed, in
        cubic metres (m3/d) for a hospital
        - demand_other_comm: assumed daily water demand per commercial
        population, in cubic metres (m3/d)
        - other_comm_denom: denominator of the fraction of the
        population assumed to be commercial i.e. 3 means one third of
        the population.
        - munic_dem_propn: The amount of municipal demand, relative to
        the sum of domestic, institutional, and commercial.
        - indust_dem_propn: The amount of industrial demand, relative to
        the sum of domestic, institutional, and commercial.
        - census_year: year the census we are using data for was
        conducted
        
        ----------------------------------------------------------------
        Notes:
        - All relevant data files must be stored in the package's
        InputData\\Demand folder
        - Start and end dates must be in a valid ISO8601 format as per
        datetime.datetime.fromisoformat()
        ----------------------------------------------------------------
        """
        ####### Method start ##################################################
        #Get the directory relative to the current script (dataprep.py)
        current_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
            )
        #Construct the path to the InputData folder
        input_data_loc = os.path.join(current_dir, r'InputData\Demand')
        #Set the location for output files:
        self.output_loc = os.path.join(current_dir, r'OutputData')
        
        #Bring in the wards:
        input_wards = gpd.read_file(
            os.path.join(input_data_loc, wards_data_file)
            )
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
            raise ValueError(
                'perc_full_plumb must be an integer in range [0,100] but'
                f' {perc_full_plumb} was provided.'
                )
        
        #Store static parameters:
        self.municipality = municipality
        self.start_date = util.date_standardiser(start_date)
        self.end_date =  util.date_standardiser(end_date)
        self.propn_full_plumb = perc_full_plumb / 100
        self.propn_not_plumb = 1 - self.propn_full_plumb
        self.num_hotels = num_hotels
        self.num_hotel_beds = num_hotel_beds
        self.num_hospitals = num_hospitals
        self.num_hospital_beds = num_hospital_beds
        self.demand_student = demand_student
        self.demand_full_plumb_home = demand_full_plumb_home
        self.demand_not_plumb_home = demand_not_plumb_home
        self.demand_hotel_bed = demand_hotel_bed
        self.demand_hospital_bed = demand_hospital_bed
        self.demand_other_comm = demand_other_comm
        self.other_comm_denom = other_comm_denom
        self.munic_dem_propn = munic_dem_propn
        self.indust_dem_propn = indust_dem_propn
        self.census_year = census_year
        
        ####### Domestic demands: #############################################
        
        if type(pop_data_file) == str:
            #Read in the excel file:
            pop_data = pd.read_excel(os.path.join(input_data_loc, pop_data_file))
            pop_data = pop_data[[
                'Ward',
                'Total population',
                'Number of households',
                'Average household size'
                ]].set_index('Ward')
        
        else:
            #Read in the excel file:
            pop_data = pop_data_file
        
        #Calculate a domestic demand column:
        pop_data['Household pop'] = (
            pop_data['Number of households'] *
            pop_data['Average household size']
            )
        pop_data['Fully plumbed pop'] = (
            pop_data['Household pop'] *
            self.propn_full_plumb
            )
        pop_data['Not plumbed pop'] = (
            pop_data['Household pop'] *
            self.propn_not_plumb
            )
        pop_data['Domestic demand [m3/d]'] = (
            (pop_data['Fully plumbed pop'] * demand_full_plumb_home)
            +
            (pop_data['Not plumbed pop'] * demand_not_plumb_home)
        )
        
        #Trim the helper columns and start building a summary dataframe:
        demand_data = pop_data.drop(
            labels=[
                'Total population',
                'Number of households',
                'Average household size',
                'Household pop',
                'Fully plumbed pop',
                'Not plumbed pop',
                ],
            axis='columns'
            )
        
        ####### Institutional demands (educational): ##########################
        #Read in the excel file:
        inst_data = pd.read_excel(
            os.path.join(input_data_loc, student_data_file)
            )
            
        #Calculate the demand column:
        inst_data['Institutional demand [m3/d]'] = (
            inst_data['Currently attending'] *
            self.demand_student
            )
        
        #Drop unnecessary column and set Ward as the index:    
        inst_data = inst_data.drop(
            labels=['Currently attending'],
            axis='columns'
            ).set_index('Ward')
        
        #Add the institutional demand to this instance's existing demand
        #dataframe:
        demand_data = demand_data.merge(
            inst_data,
            how='outer',
            left_index=True,
            right_index=True
            )
        
        ####### Commercial demands: ###########################################
        #get a bounding box in the format expected by
        #util.get_osm_locations():
        lat_long_bbox = (self.miny, self.minx, self.maxy, self.maxx)
        
        #Store relevant values as a dictionary:
        frames = {
            'Hotel': {
                'tag': {'tourism': 'hotel'},
                'num': self.num_hotels,
                'beds': self.num_hotel_beds,
                'dem': self.demand_hotel_bed
                },
            'Hospital': {
                'tag': {'amenity': 'hospital'},
                'num': self.num_hospitals,
                'beds': self.num_hospital_beds,
                'dem': self.demand_hospital_bed
                }
            }
        
        #Get a dataframe with just the census-scaled numbers for each
        #ward:
        ward_scaled_nums = pd.DataFrame(
            self.wards[["NEW_WARD_N"]].rename(
                {"NEW_WARD_N": 'Ward'},
                axis=1
                ).sort_values(by='Ward').set_index('Ward')
            )
        
        #Populate the scaled values for each feature type:
        dem_col_names = []
        for key, value in frames.items():
            #Get locations
            these_locs = util.get_osm_locations(value['tag'], lat_long_bbox)
            #Rescale values to OSM proportion of census numbers:
            this_df = util.rescale_to_census(
                these_locs,
                self.wards,
                value['num'],
                key
                )
            #Calculate total beds and the demand:
            tot_bed_col = key + ' total beds'
            this_df[tot_bed_col] = (
                this_df[key + ' scaled number'] *
                value['beds']
                )
            dem_col = key + ' demand'
            dem_col_names.append(dem_col)
            this_df[dem_col] = this_df[tot_bed_col] * value['dem']
            #Add to the exisitng dataframe
            ward_scaled_nums = ward_scaled_nums.merge(
                this_df,
                left_index=True,
                right_index=True,
                how='left'
                )
        
        #Bring the population in and calculate 'other' commercial demand:
        temp_pop = pop_data[[
            'Total population'
            ]]
        ward_scaled_nums = ward_scaled_nums[dem_col_names].merge(
            temp_pop,
            left_index=True,
            right_index=True,
            how='left'
            )
        ward_scaled_nums['Other demand'] = (
            (ward_scaled_nums['Total population'] / self.other_comm_denom) *
            self.demand_other_comm
            )
        
        #Add up the three sources for total commercial demand, and join
        #in back to the main demand DF:
        ward_scaled_nums['Commercial demand [m3/d]'] = (
            ward_scaled_nums['Hotel demand'] + 
            ward_scaled_nums['Hospital demand'] + 
            ward_scaled_nums['Other demand']
            )
        demand_data = demand_data.merge(
            ward_scaled_nums,
            how='outer',
            left_index=True,
            right_index=True
            ).drop(
                ['Hotel demand',
                'Hospital demand',
                'Total population',
                'Other demand'], 
                axis=1
                )
        
        ####### Municipal demand: #############################################
        demand_data['Municipal demand [m3/d]'] = (
            demand_data['Domestic demand [m3/d]'] + 
            demand_data['Institutional demand [m3/d]'] + 
            demand_data['Commercial demand [m3/d]']
            ) * self.munic_dem_propn
        
        ####### Industrial demand: ############################################
        demand_data['Industrial demand [m3/d]'] = (
            demand_data['Domestic demand [m3/d]'] + 
            demand_data['Institutional demand [m3/d]'] + 
            demand_data['Commercial demand [m3/d]']
            ) * self.indust_dem_propn
        
        ####### Total demand: #################################################
        #Bring the demands together and store with the ward geometry:
        temp_wards = self.wards.rename(
            {'NEW_WARD_N': 'Ward'},
            axis=1
            ).sort_values(by='Ward').set_index('Ward')
        temp_wards = temp_wards.merge(
            demand_data,
            left_index=True,
            right_index=True,
            how='outer'
            )[list(demand_data.columns) + ['geometry']]
        
        #Calculate total demand and store with class instance:
        temp_wards['Total demand [m3/d]'] = (
            temp_wards[list(demand_data.columns)].sum(axis=1)
            )
        self.ward_demand = temp_wards
        
        ####### Demand by utility area: #######################################
        #Get the estimated demand by utility area and join them into 
        #one geodataframe
        temp_utilities = gpd.GeoDataFrame()
        for utility_file in utility_data_files:
            this_utility = gpd.read_file(
                os.path.join(input_data_loc, utility_file)
                )
            utility_demand = util.areal_interp(self.ward_demand, this_utility)
            utility_demand['Utility'] = utility_file.split('.')[0]
            temp_utilities = pd.concat([temp_utilities, utility_demand])
        #Assign the CRS and store in class instance:
        temp_utilities.set_crs(epsg=self.ward_demand.crs.to_epsg())
        self.utility_demand = temp_utilities
    
    def vis(self):
        """
        Visualise demand by ward and/or utility area
        
        ----------------------------------------------------------------
        ----------------------------------------------------------------
        """
        ####### Method start ##################################################
        fig, (w_ax, u_ax) = plt.subplots(1, 2,
            **{'figsize': (12, 5)}
            )
        
        demand_cmap = 'YlGnBu'
        map_proj = 3857
        
        wards_for_plot = self.ward_demand.to_crs(epsg=map_proj)
        ut_for_plot = self.utility_demand.to_crs(epsg=map_proj)
        
        min_x = wards_for_plot.total_bounds[0]
        min_y = wards_for_plot.total_bounds[1]
        max_x = wards_for_plot.total_bounds[2]
        max_y = wards_for_plot.total_bounds[3]
        
        wards_for_plot.plot(ax=w_ax, cmap=demand_cmap)
        ut_for_plot.plot(ax=u_ax, cmap=demand_cmap)
        
        x_range = max_x - min_x
        y_range = max_y - min_y
        margin = 0.05
        x_buff = x_range * margin
        y_buff = y_range * margin
        x_left = min_x - x_buff
        x_right = max_x + x_buff
        y_bottom = min_y - y_buff
        y_top = max_y + y_buff
        
        for ax in fig.axes:
            ax.set_xlim((x_left, x_right))
            ax.set_ylim((y_bottom, y_top))
            ax.set_facecolor('#D3D3D3')
            
        for x, y, label in zip(
            ut_for_plot.geometry.centroid.x,
            ut_for_plot.geometry.centroid.y,
            ut_for_plot['Utility']
            ):
            u_ax.text(
                x,
                y,
                label,
                fontsize=8,
                ha='center',
                bbox={
                    'facecolor': 'white',
                    'edgecolor': 'none',
                    'boxstyle': 'round',
                    'pad': 0.1
                    }
                )
    
    def to_weap_data(self):
        """
        Export csv files of demand by utility service area
        
        ----------------------------------------------------------------
        Notes:
        - WEAP data in this instance is expecting a csv for each utility
        service area, for each demand type. It simply generates a date
        range for every day between the supplied start and end dates, 
        then copies the calculated daily demand into every row.
        ----------------------------------------------------------------
        """
        ####### Method start ##################################################
        #Get an array of dates between start and end:
        date_array = pd.date_range(
            start=self.start_date,
            end=self.end_date,
            ).date
        self.date_range = [date.strftime('%Y-%m-%d') for date in date_array]
        out_cols = [a for a in self.utility_demand.columns if a not in
            ['geometry', 'Utility']
            ]
        #get the number of empty strings required for output headers:
        num_blanks  = [ '' for i in range(len(out_cols))]
        
        #Go through each utility area and write an output file:
        for _, row in self.utility_demand.iterrows():
            #create a dataframe with a row for each date:
            this_df = pd.DataFrame({'$Columns = Date':self.date_range})
            #Store the utility name for the output file name:
            this_name = row['Utility']
            #Populate with the same demand value for each date:
            for col in out_cols:
                this_df[col] = row[col]
            
            #Generate the WEAP file headers:
            this_df.columns = pd.MultiIndex.from_tuples(
                zip(
                    ['$ListSeparator = ,'] + num_blanks,
                    ['$DecimalSymbol = .'] + num_blanks,
                    this_df.columns
                    )
                )
            
            #Write to file with meaningful name:
            this_filename = f'{this_name}_demand'
            this_df.to_csv(
                rf'{self.output_loc}\{this_filename}.csv',
                index=False
                )
            
        
    def __str__(self):
        """Define what to show when instance is presented as a string"""
        return f'Urban demand data instance for {self.municipality}'
        
#------------------------------------------------------------------------------
####### Future Urban Demand: ##################################################
#------------------------------------------------------------------------------

class FutUrbDem(UrbDemData):
    """
    Version of UrbDemData which first projects future population numbers
    and uses those for the UrbDemData instance's domestic demand.
    --------------------------------------------------------------------
    --------------------------------------------------------------------
    """
    
    def __init__(self,
        municipality:str,
        start_date:str,
        end_date:str,
        pop_data_file:str,
        
        pop_change_file:str,
        fut_pop_year:int,
        
        student_data_file:str,
        wards_data_file:str,
        utility_data_files:list,
        perc_full_plumb,
        num_hotels,
        num_hotel_beds,
        num_hospitals,
        num_hospital_beds,
        demand_student:float=0.01,
        demand_full_plumb_home:float=0.112,
        demand_not_plumb_home:float=0.045,
        demand_hotel_bed:float=0.2,
        demand_hospital_bed:float=0.5,
        demand_other_comm:float=0.01,
        other_comm_denom=3,
        munic_dem_propn:float=0.075,
        indust_dem_propn:float=0.225,
        census_year:int=2021
        ):
        """
        Recalculate population, then load UrbDemData instance
        
        Parameters:
        - municipality: Name of the municipality (Pokhara, 
        Tulsipur etc.) of interest
        - start_date: start date for the WEAP modelling (inclusive)
        - end_date: end date for modelling (inclusive)
        - pop_data_file: filename.ext for excel file with total pop,
        number of households, and average household size for the latest
        census year
        
        - pop_change_file: filename.ext for excel file containing
        population figures for each ward across two sequential censuses
        - fut_pop_year: year for which population forecast is required
        
        - student_data_file: filename.ext for excel file containing
        number of students per ward
        - wards_data_file: filename.ext for shapefile of ward boundaries
        - utility_data_files: list of filename.ext strings for
        shapefiles of water utility service areas
        - perc_full_plumb: integer representing the percentage of homes
        in the municipality with plumbing
        - num_hotels: number of hotels reported in Nepal 2021 to scale
        OpenStreetMap data to
        - num_hotel_beds: average number of beds per hotel
        - num_hospitals: number of hospitals reported in Nepal 2021 to
        scale OpenStreetMap data to
        - num_hospital_beds: average number of beds per hospital
        - demand_student: assumed daily water demand per student
        - demand_full_plumb_home: assumed daily water demand, per
        person, in cubic metres (m3/d) for plumbed home
        - demand_not_plumb_home: assumed daily water demand, per person,
        in cubic metres (m3/d) for un-plumbed home
        - demand_hotel_bed: assumed daily water demand per bed, in cubic
        metres (m3/d) for a hotel
        - demand_hospital_bed:assumed daily water demand per bed, in
        cubic metres (m3/d) for a hospital
        - demand_other_comm: assumed daily water demand per commercial
        population, in cubic metres (m3/d)
        - other_comm_denom: denominator of the fraction of the
        population assumed to be commercial i.e. 3 means one third of
        the population.
        - munic_dem_propn: The amount of municipal demand, relative to
        the sum of domestic, institutional, and commercial.
        - indust_dem_propn: The amount of industrial demand, relative to
        the sum of domestic, institutional, and commercial.
        - census_year: year the census we are using data for was
        conducted
        
        ----------------------------------------------------------------
        Notes:
        - All relevant data files must be stored in the package's
        InputData\\Demand folder
        - Start and end dates must be in a valid ISO8601 format as per
        datetime.datetime.fromisoformat()
        - Forecasted populations are NOT used to recalculate future 
        student populations or hotel/hospital numbers. The forecast will
        therefore mainly affect domestic demand
        ----------------------------------------------------------------
        """
        ####### Method start ##################################################
        
        #Get the directory relative to the current script (dataprep.py)
        current_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
            )
        #Construct the path to the InputData folder
        input_data_loc = os.path.join(current_dir, r'InputData\Demand')
        #Set the location for output files:
        self.output_loc = os.path.join(current_dir, r'OutputData')
        
        self.year = fut_pop_year
        
        #Read in the future population data file:
        pop_change = pd.read_excel(
            os.path.join(input_data_loc, pop_change_file)
            ).set_index('Ward')
        
        forec_tab_pop = util.pop_forecast(pop_change, fut_pop_year)
        
        #Read in the current population data:
        pop_deets = pd.read_excel(
            os.path.join(input_data_loc, pop_data_file)
            ).set_index('Ward')[[ 
                'Average household size'
                ]]
        self.pop_forec_table = forec_tab_pop.merge(
            pop_deets,
            left_index=True,
            right_index=True,
            how='outer',
            )
            
        self.pop_forec_table['Number of households'] = (
            self.pop_forec_table[str(fut_pop_year)]
            / self.pop_forec_table['Average household size']
            ).astype('int')
        
        pop_table_for_UrbDem = self.pop_forec_table[[
            str(fut_pop_year),
            'Average household size',
            'Number of households'
            ]].rename(
                {str(fut_pop_year): 'Total population'},
                axis='columns'
                )
        
        super().__init__(
            municipality,
            start_date,
            end_date,
            
            pop_table_for_UrbDem,
            
            student_data_file,
            wards_data_file,
            utility_data_files,
            perc_full_plumb,
            num_hotels,
            num_hotel_beds,
            num_hospitals,
            num_hospital_beds,
            demand_student,
            demand_full_plumb_home,
            demand_not_plumb_home,
            demand_hotel_bed,
            demand_hospital_bed,
            demand_other_comm,
            other_comm_denom,
            munic_dem_propn,
            indust_dem_propn,
            census_year
            )
    
    def __str__(self):
        """Define what to show when instance is presented as a string"""
        output = (
            'Future urban demand data instance for '
            f'{self.municipality} in {self.year}'
            )
        return output
        