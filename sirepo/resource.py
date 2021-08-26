# -*- coding: utf-8 -*-
u"""Functions for accessing resource files

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
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
    return pkresource.file_path(
        _join_paths(paths),
        packages=sirepo.feature_config.cfg().package_path,
    )


def glob_paths(*paths):
    """Get matching paths

    Args:
        paths (str): Path components of file

    Returns:
        [py.path]: paths that match pattern
    """
    return pkresource.glob_paths(
            _join_paths(paths),
            packages=sirepo.feature_config.cfg().package_path,
    )


def static(*paths):
    """Absolute or relative path to resource static file

    Args:
        paths (str): Path components of file

    Returns:
        py.path: path to file
    """
    return file_path(static_url(*paths))


def static_paths_for_type(file_type):
    """Get paths of static file of type

    Args:
        file_type (str): The type of file (ex json)

    Returns:
        [py.path]: paths that match pattern
    """
    return glob_paths(static_url(file_type, f'*.{file_type}'))


def static_url(*paths):
    """Get url for static file

    Args:
        paths (str): Path components of file

    Returns:
        str: url for file
    """
    return _join_paths(['static', *paths])


def _join_paths(paths):
    a = [p for p in paths if os.path.isabs(p)]
    assert not a, f'absolute paths={a} in paths={paths}'
    return os.path.join(*paths)
