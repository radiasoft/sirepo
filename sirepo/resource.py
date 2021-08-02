# -*- coding: utf-8 -*-
u"""Functions for accessing resource files

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkresource
import os
import sirepo.feature_config
import werkzeug.utils


def filename(*paths):
    """Get absolute path to a resource file

    Args:
        paths (str): Names of paths to get to resource file

    Returns:
        py.path: absolute path to resource file
    """
    return pkio.py_path(pkresource.filename(
        os.path.join(*paths),
        additional_packages=sirepo.feature_config.dynamic_sim_type_packages(),
    ))


def glob_static(path):
    """Get paths that match path

    Args:
        path (str): pattern

    Returns:
        [py.path]: paths that match pattern
    """
    for f in pkresource.glob(
            os.path.join('static', path),
            additional_packages=sirepo.feature_config.dynamic_sim_type_packages(),
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
        # SECURITY: We take untrusted paths (ex api_staticFile). Must use
        # safe_join to make sure they don't escape the static dir.
        werkzeug.utils.safe_join('static', *paths),
        additional_packages=sirepo.feature_config.dynamic_sim_type_packages(),
        relpath=relpath
    )
    if not relpath:
        p = pkio.py_path(p)
    return p


def template(common_filename_or_sim_type):
    return filename('template', common_filename_or_sim_type)
