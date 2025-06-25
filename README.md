# NepalWeap
Python package for preparation, processing, and visualisation of data for WEAP

This package has the following key functions:
- Reformat the input datasets required for WEAP modelling, into files that are ready to import into WEAP, which has very specific requirements
- Visualise the input datasets
- Visualise the output datasets produced by WEAP

---
## Loading Data
### Hydro (streamflow) data
1. Ensure the excel file(s) with the data for the required municipalities and stations is in InputData\Hydro
2. Create an instance of the HydroData class, which requires specifying the following:
    1. File name and extension
    2. A list of station names as strings
    3. The start date for your WEAP model
    4. The end date
3.	View the loaded data by calling print or display on <instance name>.datasets[0].base_data, where <instance name> is the variable name you chose when creating the class instance.
    1.	Note that this structure has allowed for additional future hydro variables, even though currently only streamflow volume is included. The visualisation method will require an update in this case.
![](ImagesForDocs\Hydro_Streamflow_TimeSeriesPlot.png "Time series plot showing observed streamflow at 2 sites over 2 years.")

### Meteo (weather) data
1. Ensure the excel file(s) with the data for the required municipalities and stations is in InputData\Meteo
2. Create an instance of the MeteoData class, which requires specifying:
    1. File name and extension
    2. List of station names
    3. Start date
    4. End date
    5. List of weather variables to include
3. View the loaded data by calling print or display on any dataset.base_data in the  <instance name>.datasets list, where <instance name> is the variable name you chose when for class instance. 

### Land use data
1. Ensure the GeoTIFF (.tif) land use/land cover raster, and the Shapefile (.shp) of sub-catchments with all its sidecar files are in InputData\LandUse
2. Create an instance of the LulcData class, specifying:
    1. File name and extension for the GeoTIFF
    2. File name and extension for the shapefile
3. View the loaded data by calling print or display on <instance name>.raw_stats

### Urban demand (current) data
1. Ensure the excel files with population and student data, and the shapefiles delineating ward and utility service area boundaries, are in InputData\Demand
2. Create an instance of the UrbDemData class, specifying:
    1. Name of the relevant municipality
    2. Start date
    3. End date
    4. Filename and extension for:
        1. Population data file (.xlsx)
        2. Student data file (.xlsx)
        3. Ward boundaries (.shp)
    5. A python list of filenames and extensions for each of the utility service area files
    6. Other parameters as outlined in the class docstring
3. View the loaded data by calling print or display on <instance name>.ward_demand or <instance name>.utility_demand

### Urban demand (future) data
As for current urban demand outlined above, except the following must also be specified when creating the class instance:
1. Filename and extension for an excel file (.xlsx) with population numbers for each ward across two different census years
2. The year for which a future demand forecast is desired

### Visualising loaded data
All data types can be visualised easily using the <instance name>.vis() method. The output of this method varies for each type of data:

## Exporting Data for WEAP
### General data formats
While each data type has a slightly different structure, all exporting can be done by simply calling the to_weap_data() method on the main instance. When the method is called, a number of CSV files are created in the OutputData folder. The first few rows of each CSV file include metadata and column headers which are required when importing into WEAP, followed by the data entries:
1. Metadata Rows:
    1. $ListSeparator = , (tells WEAP that this is a CSV file)
    2. $DecimalSymbol = . (tells WEAP that the full-stop/period will be used as the decimal indicator)
2. Column Headers:
    1. Specific to each dataset, such as Date, Streamflow, Precipitation, etc.
    2. The first column header (usually Date) always starts with “$Columns = ” before the first column name. This tells WEAP that this row is column names, not data

Each remaining row contains values for each column, usually with one row per observation date. See the user guide for a table of all columns, their data types, and which datasets they appear in.

### Streamflow data
The streamflow dataset includes daily measurements of streamflow volume for one or more gauges. The data is structured with a column for the date and a column for each gauge.

### Meteorological data
The meteorological datasets include daily measurements of precipitation, relative humidity, and mean temperature for one or more locations. One file per variable is created, with a column for each measurement station as well as for the date.

### Land use data
The land use datasets show the distribution of five different land use types, with a separate file for each subcatchment. They include a year column and a row for each year in the requested modelling period, where *the values are identical for all years*. WEAP requires the data to be in this format with a row for each year, but tracking or predicting change in land use over time is beyond the scope of this work. This assumption – that land use will not change/has not changed over time – should be considered when interpreting model results. The data includes columns for the year and for areas of agriculture, forest, grassland, waterbody, and urban land in hectares. Land use datasets have an additional metadata row with a ‘#’ followed by the title of the file e.g. ‘# Subcatchment 1’.

### Demand data
The demand datasets contain daily water demand data for different water utility companies. Data is structured with columns for date and daily water demand in cubic meters per day for domestic, institutional, commercial, municipal, and industrial categories, as well as the total demand.

## Visualising WEAP Outputs
Clear, simple visualisations can be produced by calling the plot_weap_data() or plot_water_balance() functions in the outputvis module once the WEAP outputs have been cleaned and placed in the relevant folder.

