# -*- coding: utf-8 -*-
u"""Jupyter utilities

:copyright: Copyright (c) 2018-2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp


class Notebook(PKDict):
    """A dictionary and methods for building a valid Jupyter notebook

    A jupyter notebook is just a JSON document with a specific structure and
    attributes. Coarsely, it comprises an array of cells containing either python
    code or markdown, along with various metadata

    Methods:
        add_code_cell(source_strings, hide=False)
            Adds a cell from an array of strings of python
        add_markdown_cell(source_strings)
            Adds a cell from an array of strings of arbitrary markdown
        add_report(params)
            Adds a pyplot graph of x values vs. one or more arrays of y values
    """

    _PYPLOT_STYLE_MAP = PKDict(
        line='-',
        scatter='.',
    )

    @classmethod
    def _append_newline(cls, s):
        return s + ('\n' if not s.endswith('\n') else '')

    @classmethod
    def _dict_to_kwargs_str(cls, d):
        d_str = ''
        for k in d.keys():
            v = f"'{d[k]}'" if isinstance(d[k], pkconfig.STRING_TYPES) \
                else f'{d[k]}'
            d_str += f'{k}={v},'
        return d_str

    def __init__(self, data):
        super().__init__(
            cells=[],
            metadata=PKDict(
                kernelspec=PKDict(
                    display_name='Python 3',
                    language='python',
                    name='python3'
                ),
                language_info=PKDict(
                    codemirror_mode=PKDict(
                        name='ipython',
                        version=3
                    ),
                    file_extension='.py',
                    mimetype='text/x-python',
                    name='python',
                    nbconvert_exporter='python',
                    pygments_lexer='ipython3',
                    version='3.7.2'
                )
            ),
            nbformat = 4,
            nbformat_minor = 4,
        )

        self.add_markdown_cell([
                f'# {data.simulationType} - {data.models.simulation.name}',
            ])
        # commenting this out for now - may want a monolothic imports cell later
        #self.add_markdown_cell(['## Imports', ])

    def add_code_cell(self, source_strings, hide=False):
        """Adds a cell containing arbitrary python

        Args:
            source_strings (list): strings to include. These get joined to a single
                linesep-delimited string for clarity of presentation
            hide (bool): hide the cell when the notebook loads.  Useful for long data
                arrays etc.
        """
        self._add_cell('code', source_strings, hide=hide)

    def add_markdown_cell(self, source_strings):
        """Adds a cell containing arbitrary markdown

         Args:
             source_strings (list): strings to include. These get joined to a single
                 linesep-delimited string for clarity of presentation
         """
        self._add_cell('markdown', source_strings)

    def add_report(self, params):
        """Adds a pyplot graph of x values vs. one or more arrays of y values

         Args:
             params (dict): plot parameters as follows:
                title (str): plot title
                x_var (array): x values to plot
                x_label (str): label for the x axis
                y_info (array): array of parameter dicts for the y axis:
                    style (str): plot style (currently accepts 'line' or 'scatter',
                        becoming '-' or '.' for pyplot
                    x_points (array): x values to use instead of the global array
                    y_var (array): y values to plot
                    y_label (str): label for the y axis or legend
         """
        self.add_code_cell([
            'from matplotlib import pyplot'
        ])
        plot_strs = []
        legends = []
        for y_params in params.y_info:
            x_pts_var = y_params.x_points if 'x_points' in y_params else params.x_var
            plot_strs.append(
                f"pyplot.plot(\
                    {x_pts_var},\
                    {y_params.y_var},\
                    '{self._PYPLOT_STYLE_MAP[y_params.style]}'\
                )"
            )
            legends.append(f'\'{y_params.y_label}\'')
        code = [
                'pyplot.figure()',
                f"pyplot.xlabel('{params.x_label}')",
                f'pyplot.legend({legends})',
                f"pyplot.title('{params.title}')",
            ]
        if len(params.y_info) == 1:
            code.append(f"pyplot.ylabel('{params.y_info[0].y_label}')")
        code.extend(plot_strs)
        code.append('pyplot.show()')
        self.add_code_cell(code)

    def _add_cell(self, cell_type, source_strings, hide=False):
        c = PKDict(
            cell_type=cell_type,
            metadata=PKDict(
                jupyter=PKDict(source_hidden=hide)
            ),
            source=[Notebook._append_newline(s) for s in source_strings]
        )
        if cell_type == 'code':
            c.execution_count = 0
            c.outputs=[]
        self.cells.append(c)

