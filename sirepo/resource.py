# -*- coding: utf-8 -*-
"""Functions for accessing resource files

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkresource
from pykern.pkdebug import pkdp
import importlib
import os
import pykern.pkio
import pykern.pkjinja
import sirepo.const
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


def render_jinja(*paths, target_dir=None, j2_ctx=None):
    """Render a resource template file with Jinja into target_dir.

    Args:
        paths (str): Path components of resource file without pykern.pkjinja.RESOURCE_SUFFIX
        target_dir (py.path): target directory for rendered file
        j2_ctx (PKDict): parameters to jinja file

    Returns:
        py.path: output path which is target_dir.join(paths[-1])
    """
    f = paths[-1]
    res = target_dir.join(f)
    pykern.pkjinja.render_file(
        file_path(*paths[:-1], f + pykern.pkjinja.RESOURCE_SUFFIX),
        j2_ctx,
        output=res,
    )
    return res


def root_modules():
    """Get all root modules in package_path

    Returns:
        [module]: root modules
    """
    return [
        importlib.import_module(p) for p in sirepo.feature_config.cfg().package_path
    ]


def static(*paths):
    """Absolute or relative path to resource static file

    Args:
        paths (str): Path components of file

    Returns:
        py.path: path to file
    """
    return file_path(static_url(*paths))


def static_files():
    """Generate all, non-overlapping, non-dot static files

    Yields:
        (str, py.path): relative path (including static) and absolute paths
    """
    s = set()
    for d in glob_paths(static_url()):
        for f in pykern.pkio.walk_tree(d):
            r = d.bestrelpath(f)
            if "/." not in f"/{r}" and r not in s:
                s.add(r)
                yield (static_url(r), f)


def static_paths_for_type(file_type):
    """Get paths of static file of type

    Args:
        file_type (str): The type of file (ex json)

    Returns:
        [py.path]: paths that match pattern
    """
    return glob_paths(static_url(file_type, f"*.{file_type}"))


def static_url(*paths):
    """Get url for static file

    Args:
        paths (str): Path components of file

    Returns:
        str: url for file
    """
    return _join_paths([sirepo.const.STATIC_D, *paths])


def _join_paths(paths):
    a = [p for p in paths if os.path.isabs(p)]
    assert not a, f"absolute paths={a} in paths={paths}"
    return os.path.join(*paths)
