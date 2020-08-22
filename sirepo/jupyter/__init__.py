# -*- coding: utf-8 -*-
u"""Jupyter utilities

:copyright: Copyright (c) 2018-2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.feature_config
import sirepo.template

class Notebook():
    """Make a notebook
    """

    _CELL_TYPES = ('code', 'markdown')
    _HEADER_CELL_INDEX = 0
    _IMPORT_HEADER_CELL_INDEX = 1
    _IMPORT_CELL_INDEX = 2
    _PYPLOT_STYLE_MAP = PKDict(
        line='-',
        scatter='.',
    )

    @classmethod
    def _base_dict(cls):
        return PKDict(
            cells=[],
            nbformat=4,
            nbformat_minor=4,
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
            )
        )

    @classmethod
    def _dict_to_kwargs_str(cls, d):
        d_str = ''
        for k in d:
            v = f"'{d[k]}'" if isinstance(d[k], pkconfig.STRING_TYPES) \
                else f'{d[k]}'
            d_str += f'{k}={v},'
        return d_str

    def __init__(self, data):
        self.data = data
        self.notebook = Notebook._base_dict()
        self.imports = PKDict()
        self.widgets = []

        # cell 0
        self.add_markdown_cell(
            [
                '# {} - {}'.format(data.simulationType, data.models.simulation.name),
            ]
        )
        # cell 1
        self.add_markdown_cell(
            ['## Imports',]
        )
        # cell 2
        self.add_code_cell([])

        super(object, self).__init__()

    def add_cell(self, cell_type, source_strings, hide=False):
        assert cell_type in self._CELL_TYPES, 'Invalid cell type {}'.format(cell_type)
        cell = PKDict(
            cell_type=cell_type,
            metadata={},
            source=[s + ('\n' if s[-1] != '\n' else '') for s in source_strings]
        )
        if hide:
            cell.metadata['jupyter'] = {
                'source_hidden': 'true'
            }
        self.notebook.cells.append(cell)

    def add_code_cell(self, source_strings, hide=False):
        self.add_cell('code', source_strings, hide=hide)

    # {<pkg>: [sub_pkg]}
    # just merge?
    def add_imports(self, pkg_dict):
        for pkg in pkg_dict:
            if pkg not in self.imports:
                self.imports[pkg] = pkg_dict[pkg]
        for s in pkg_dict[pkg]:
            if s not in self.imports[pkg]:
                self.imports[pkg].append(s)
        self._update()

    # meaningful to load arbitrary file name?
    def add_load_csv(self, widget_var):
        data_var = f'data_{widget_var}'
        self.add_imports({'numpy': ['genfromtxt'], })
        self.add_code_cell(
            [
                f'f = {widget_var}.value',
                'f_name = next(iter(f.keys()))',
                f'{data_var} = numpy.genfromtxt(f_name, delimiter=\',\')',
            ]
        )
        return data_var

    def add_markdown_cell(self, source_strings):
        self.add_cell('markdown', source_strings)

    # parameter plot
    def add_report(self, cfg):
        self.add_imports({'matplotlib': ['pyplot']})
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

    def add_widget(self, widget_type, cfg):
        self.add_imports({'ipywidgets': []})
        n_widgets = len([w for w in self.widgets if w.type == widget_type])
        widget_var = f'{widget_type.lower()}_{n_widgets}'
        if not n_widgets:
            self.widgets.append(PKDict(name=widget_var, type=widget_type))
        widget_kwargs = Notebook._dict_to_kwargs_str(cfg)
        self.add_code_cell(
            [
                f'{widget_var} = ipywidgets.{widget_type}({widget_kwargs})',
                f'display({widget_var})'
            ]
        )
        return widget_var

    def _update(self):
        import_source = []
        pkgs = sorted(self.imports.keys())
        for p in [pkg for pkg in pkgs]:
            import_source.append(
                f'import {p}\n'
            )
        for s in [pkg for pkg in pkgs if len(self.imports[pkg])]:
            for p in self.imports[s]:
                import_source.append(
                    f'from {s} import {p}\n'
                )
        self.notebook.cells[self._IMPORT_CELL_INDEX].source = import_source


