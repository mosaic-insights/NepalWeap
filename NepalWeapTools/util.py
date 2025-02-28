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

def compare_sheet_names(sheet_names:list, measurements:list):
    """Remove measurements from list if they're not in sheet_names"""
    #Get the set of strings in both:
    matches = set(sheet_names) & set(measurements)
    
    #If there's none, raise an error:
    if not matches:
        raise ValueError('None of the provided measurements matched worksheet names.')
    
    #Get the unmatched ones:
    unmatched = set(measurements) - set(sheet_names)
    if unmatched:
        print(f'Warning: {unmatched} were not found in Excel file and have been removed')
    
    new_meas = [a for a in measurements if a in sheet_names]
    return new_meas