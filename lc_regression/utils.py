#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""General utility functions used across the analysis package."""

from copy import deepcopy

import numpy as np
import sncosmo
from astropy.time import Time
from sndata.csp import dr1, dr3

from .exceptions import NoCSPData


def chisq(data, error, model):
    """Calculate chi-squared

    Args:
        data  (ndarray): Observed values
        error (ndarray): Observed errors
        model (ndarray): Modeled Values

    Returns:
        sum(((data - model) / error) ** 2)
    """

    return np.sum(((data - model) / error) ** 2)


@np.vectorize
def convert_to_jd(date):
    """Convert MJD and Snoopy dates into JD

    Args:
        date (float): Time stamp in JD, MJD, or SNPY format

    Returns:
        The time value in JD format
    """

    snoopy_offset = 53000  # Snoopy date format is MDJ minus 53000
    mjd_offset = 2400000.5  # MJD date format is JD minus 2400000.5
    date_format = 'mjd'

    if date < snoopy_offset:
        date += snoopy_offset

    elif date > mjd_offset:
        date_format = 'jd'

    t = Time(date, format=date_format)
    t.format = 'jd'
    return t.value


def get_csp_t0(obj_id):
    """Get the t0 value published by CSP DR3 for a given object

    Args:
        obj_id (str): The object Id value

    Returns:
        The published MJD of maximum minus 53000
    """

    dr3.download_module_data()
    params = dr3.load_table(3)
    params = params[~params['T(Bmax)'].mask]
    if obj_id not in params['SN']:
        raise NoCSPData(f'No published t0 for {obj_id}')

    return params[params['SN'] == obj_id]['T(Bmax)'][0] + 2400000.5


def get_csp_ebv(obj_id):
    """Get the E(B - V) value published by CSP DR1 for a given object

    Args:
        obj_id (str): The object Id value

    Returns:
        The published E(B - V) value
    """

    dr1.download_module_data()
    extinction_table = dr1.load_table(1)
    if obj_id not in extinction_table['SN']:
        raise NoCSPData(f'No published E(B-V) for {obj_id}')

    data_for_target = extinction_table[extinction_table['SN'] == obj_id]
    return data_for_target['E(B-V)'][0]


def filter_has_csp_data(data_table):
    """A filter function for an SNData table iterator

    Returns whether the object ID associated with a data table has an
    available t0 and E(B - V) value.

    Args:
        data_table (Table): A table from sndata

    Returns:
        A boolean
    """

    obj_id = data_table.meta['obj_id']
    try:
        get_csp_t0(obj_id)
        get_csp_ebv(obj_id)

    except NoCSPData:
        return False

    else:
        return True


def get_effective_wavelength(band_name):
    """Get the effective wavelength for a given band

    Band name must be registered with SNCosmo.

    Args:
        band_name (str): The name of a registered bandpass

    Returns:
        The effective wavelength in Angstroms
    """

    return sncosmo.get_bandpass(band_name).wave_eff


def calc_model_chisq(data, result, model):
    """Calculate the chi-squared for a given data table and model

    Chi-squareds are calculated using parameter values from ``model``. Degrees
    of freedom are calculated using the number of varied parameters specified
    is the ``result`` object.

    Args:
        data    (Table): An sncosmo input table
        model   (Model): An sncosmo Model
        result (Result): sncosmo fitting result

    Returns:
        The un-normalized chi-squared
        The number of data points used in the calculation
    """

    data = deepcopy(data)

    # Drop any data that is not withing the model's range
    min_band_wave = [sncosmo.get_bandpass(b).minwave() for b in data['band']]
    max_band_wave = [sncosmo.get_bandpass(b).maxwave() for b in data['band']]
    data = data[
        (data['time'] >= model.mintime()) &
        (data['time'] <= model.maxtime()) &
        (min_band_wave >= model.minwave()) &
        (max_band_wave <= model.maxwave())
        ]

    if len(data) == 0:
        raise ValueError('No data within model range')

    return sncosmo.chisq(data, model), len(data) - len(result.vparam_names)

