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
    """Make a notebook
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
        for k in d:
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

        self.add_markdown_cell(
            [
                '# {} - {}'.format(data.simulationType, data.models.simulation.name),
            ]
        )
        self.add_markdown_cell(
            ['## Imports',]
        )

    def add_code_cell(self, source_strings, hide=False):
        self._add_cell('code', source_strings, hide=hide)

    def add_markdown_cell(self, source_strings):
        self._add_cell('markdown', source_strings)

    # parameter plot
    def add_report(self, cfg):
        self.add_code_cell([
            'from matplotlib import pyplot'
        ])
        plot_strs = []
        legends = []
        for y_cfg in cfg.y_info:
            x_pts_var = y_cfg.x_points if 'x_points' in y_cfg else cfg.x_var
            plot_strs.append(f'pyplot.plot({x_pts_var}, {y_cfg.y_var}, \'{self._PYPLOT_STYLE_MAP[y_cfg.style]}\')')
            legends.append(f'\'{y_cfg.y_label}\'')
        code = [
                'pyplot.figure()',
                f'pyplot.xlabel(\'{cfg.x_label}\')',
                f'pyplot.legend({legends})',
                f'pyplot.title(\'{cfg.title}\')',
            ]
        if len(cfg.y_info) == 1:
            code.append(f'pyplot.ylabel(\'{cfg.y_info[0].y_label}\')')
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

