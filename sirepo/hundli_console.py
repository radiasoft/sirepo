# -*- coding: utf-8 -*-
"""Hundli: a dog height and weight simulation engine

This is not technically part of Sirepo. It demonstrates a arbitrary 3rd
party code, which Sirepo calls as an independent program.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import csv
import numpy
import random
import sys
import yaml
import os


_MAX_AGE_BY_WEIGHT = [
    [0, 16],
    [20, 13],
    [50, 11],
    [90, 10],
]


def main():
    """Read the input yaml and write the output csv"""
    # hack support for openmpi/mpich so we can run under mpi with only one output file
    if os.environ.get('OMPI_COMM_WORLD_RANK', os.environ.get('PMI_RANK', '0')) != '0':
        sys.stderr.write('bye\n')
        exit(0)
    if len(sys.argv) != 3:
        sys.stderr.write('usage: hundli input.yml output.csv\n')
        exit(1)
    input_yaml, output_csv = sys.argv[1:]
    with open(input_yaml, 'r') as f:
        params = yaml.load(f)
    max_age = _max_age(params['weight'])
    years = numpy.linspace(0, max_age, int(max_age) + 1).tolist()
    heights = _points_size(params['height'], years)
    weights = _points_size(params['weight'], years)
    activity = _points_activity(years)
    with open(output_csv, 'w') as f:
        out = csv.writer(f)
        out.writerow(('Year', 'Height', 'Weight', 'Activity'))
        out.writerows(zip(years, heights, weights, activity))


def _factor(v, max_value, exp):
    return (random.random() * 0.5) * max_value / exp \
        + max_value * (exp - 1.0) / exp * (1.0 - 1.0 / (1.0 + v ** 2))


def _max_age(weight):
    """Weight affects life expectancy

    Improvement would be consider gender.
    """
    prev = None
    for bracket in _MAX_AGE_BY_WEIGHT:
        if weight <= bracket[0]:
            break
        prev = bracket[1]
    return prev


def _points_activity(years):
    """Random function"""
    max_value = 11.0
    return map(
        lambda v: max_value - _factor(v, max_value, 5.0),
        years,
    )


def _points_size(max_value, years):
    """Randomized """
    return map(
        lambda v: _factor(v, max_value, 20.0),
        years,
    )


if __name__ == '__main__':
    main()
