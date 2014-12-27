##########################################
# File: wilks.py                         #
# Copyright Richard Stebbing 2014.       #
# Distributed under the MIT License.     #
# (See accompany file LICENSE or copy at #
#  http://opensource.org/licenses/MIT)   #
##########################################

# Small script to parse the Wilks tables from
# http://www.wimwam.nl/wilksformula.htm and present functions to calculate
# required quantities

# Imports
import numpy as np
import os.path
from pickle_ import dump, load

# Logger
from log import getLogger
logger = getLogger('basic')

# all
__all__ = [
    'coefficient',
    'points',
    'required_total',
    'required_weight'
]

# Source files
WILKS_TABLE_MEN = 'wilks_data/wilks_men.txt'
WILKS_TABLE_WOMEN = 'wilks_data/wilks_women.txt'

# Working file(s)
WILKS_DICTIONARY_FILE = 'wilks_data/wilks_dictionary.dat'

# Global dictionary
WILKS_DICTIONARY = None

# Parse functions

# parse_wilks_table
def parse_wilks_table(fid):
    # Open file if required
    own_fid = False
    if isinstance(fid, basestring):
        fid = open(fid, 'r')
        own_fid = True

    # Skip first line
    fid.readline()

    W = []
    C = []

    for line in fid:
        as_floats = [float(x) for x in line.split('\t')]

        # Get base weight and coefficients
        base_weight = as_floats[0]
        coefficients = as_floats[1:]

        # Get all weights
        all_weights = base_weight + np.linspace(0.,1.,10,endpoint=False)

        # Save
        W.append(all_weights)
        C.append(coefficients)

    # Close file if required
    if own_fid:
        fid.close()

    return np.hstack(W), np.hstack(C)

# update_wilks_dictionary
def update_wilks_dictionary():
    global WILKS_DICTIONARY

    # Parse each set of wilks coefficients
    wilks_ = {}
    wilks_['M'] = parse_wilks_table(WILKS_TABLE_MEN)
    wilks_['F'] = parse_wilks_table(WILKS_TABLE_WOMEN)

    # Dump to file
    dump(WILKS_DICTIONARY_FILE, wilks_)

    # Reset WILKS_DICTIONARY
    WILKS_DICTIONARY = wilks_

# Access function

# wilks_dictionary
def wilks_dictionary(update=False):
    global WILKS_DICTIONARY

    # Update if required or file is not present
    if update or not os.path.exists(WILKS_DICTIONARY_FILE):
        update_wilks_dictionary()

    # Load the file if it is None
    if WILKS_DICTIONARY is None:
        WILKS_DICTIONARY = load(WILKS_DICTIONARY_FILE)

    return WILKS_DICTIONARY

# Calculation functions

# coefficient
def coefficient(g, w):
    # Get the Wilks dictionary
    d = wilks_dictionary()

    # Get the weight and coefficient arrays for the given gender
    try:
        W,C = d[g]
    except KeyError:
        raise KeyError, 'Gender "%s" not recognised' % g

    # Check bounds
    if w < W[0] or w > W[-1]:
        logger.warning('Input weight %.1f is outside of range: '\
            '[%.1f, %.1f]', w, W[0], W[-1])

    # Find closest weight
    index = np.argmin(np.abs(w - W))
    logger.debug('Closest weight: %f -> %.1f', w, W[index])

    # Return the coefficient
    return C[index]

# points
def points(g, w, total):
    return coefficient(g, w) * total

# required_total
def required_total(g, w, points):
    return float(points) / coefficient(g, w)

# required_weight
def required_weight(g, total, points):
    # Get the Wilks dictionary
    d = wilks_dictionary()

    # Get the weight and coefficient arrays for the given gender
    try:
        W,C = d[g]
    except KeyError:
        raise KeyError, 'Gender "%s" not recognised' % g

    # Calculate desired coefficient
    coeff = float(points) / total

    # Find closest coefficient at the largest weight

    # NOTE May not be as accurate at the fringes of the wilks coefficients
    # where the function is non-monotonic

    indices = np.nonzero(C >= coeff)[0]
    try:
        max_index = np.amax(indices)
    except ValueError:
        raise ValueError, 'Coefficient required (%.3f) is too large' % \
            coeff

    return W[max_index]

