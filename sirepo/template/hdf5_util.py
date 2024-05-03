# -*- coding: utf-8 -*-
"""HDF5 utilities.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
from sirepo.template import template_common
import h5py
import numpy as np
import time


class HDF5Util:
    def __init__(self, filename):
        self.filename = filename

    def heatmap(self, plot_attrs):
        """Returns heatmap from HDF5 file

        Args:
            plot_attrs (PKDict):
                format_plot (func): Formats plot for field (add labels, units, etc)
                frame_index (int): Frame index for points
                model (PKDict): Contains info about entire plot
                points (func): Returns points for field at frame index
                title (func): Returns title for plot
        """
        with h5py.File(self.filename, "r") as p:
            x_field = "x"
            y_field = "y"
            plots = PKDict()
            for f in (x_field, y_field):
                n = plot_attrs.model[f]
                plots[f] = PKDict(
                    name=n,
                    points=plot_attrs.points(p, plot_attrs.frame_index, n),
                    label=n,
                )
                plot_attrs.format_plot(p, plots[f])
            t = plot_attrs.title(p, plot_attrs.frame_index)

        return template_common.heatmap(
            values=[plots[x_field].points, plots[y_field].points],
            model=plot_attrs.model,
            plot_fields=PKDict(
                x_label=plots[x_field].label,
                y_label=plots[y_field].label,
                title=t,
            ),
        )

    def lineplot(self, plot_attrs):
        """Returns lineplot from HDF5 file

        Args:
            plot_attrs (PKDict):
                format_plots (func): Formats plots for field (add labels, units, etc)
                index (func): Returns dimension index for field
                model (PKDict): Contains info about entire plot
        """
        x_field = "x"
        y_fields = ("y1", "y2", "y3")

        plots = PKDict()
        for f in (x_field,) + y_fields:
            name_and_field = plot_attrs.model[f].split(" ")
            if name_and_field[0] == "none":
                continue
            plots[f] = PKDict(
                label=plot_attrs.model[f],
                dim=f,
                points=[],
                name=name_and_field[0],
                index=plot_attrs.index(name_and_field),
            )
        with h5py.File(self.filename, "r") as p:
            plot_attrs.format_plots(p, plots)
        x = plots.get(x_field)
        return template_common.parameter_plot(
            x=x.points,
            plots=[p for p in plots.values() if p.dim != x_field],
            model=plot_attrs.model,
            plot_fields=PKDict(
                dynamicYLabel=True,
                title="",
                y_label="",
                x_label=x.label,
            ),
        )

    def read_while_writing(self, callback, retries=10, timeout=3):
        e = None
        for _ in range(retries):
            try:
                with h5py.File(self.filename, "r") as p:
                    return callback(p)
            except (BlockingIOError, IOError, KeyError) as err:
                e = err
                pkdlog(
                    "{} when reading file {}, will retry",
                    type(e).__name__,
                    self.filename,
                )
                time.sleep(timeout)
        raise AssertionError(
            f"{self.filename} read failed with {type(e).__name__}: {e}"
        )
