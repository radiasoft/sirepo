# -*- coding: utf-8 -*-
u"""Functions for accessing resource files

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkresource
from pykern.pkdebug import pkdp
import os
import sirepo.feature_config
import sirepo.util


def file_path(*paths):
    """Get absolute path to a resource file

    Args:
        paths (str): Names of paths to get to resource file

    Returns:
        py.path: absolute path to resource file
    """
    return pkio.py_path(pkresource.filename(
        os.path.join(*paths),
        packages=sirepo.feature_config.cfg().package_path,
    ))


def glob_paths(*paths):
    """Get matching paths

    Args:
        paths (str): Path components of file

    Returns:
        [py.path]: paths that match pattern
    """
    for f in pkresource.glob_files(
            os.path.join(*paths),
            packages=sirepo.feature_config.cfg().package_path,
    ):
        yield pkio.py_path(f)


def static(*paths, relpath=False):
    """Absolute or relative path to resource static file

    Args:
        paths (str): Path components of file
        relpath (bool): If True path is relative to package package_data dir

    Returns:
        py.path: path to file
    """
    p = pkresource.filename(
        os.path.join('static', *paths),
        packages=sirepo.feature_config.cfg().package_path,
        relpath=relpath
    )
    if not relpath:
        p = pkio.py_path(p)
    return p


def static_paths_for_type(file_type):
    """Get paths of static file of type

    Args:
        file_type (str): The type of file (ex json)

    Returns:
        [py.path]: paths that match pattern
    """
    return glob_paths('static', file_type, f'*.{file_type}')
