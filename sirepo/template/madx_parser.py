# -*- coding: utf-8 -*-
u"""MAD-X parser.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template import lattice
import re
import sirepo.sim_data


class MadXParser(lattice.LatticeParser):
    def __init__(self):
        self.ignore_commands = set([
            'aperture', 'assign', 'beta0', 'coguess', 'constraint',
            'correct', 'create', 'ealign', 'efcomp', 'emit', 'endedit',
            'endmatch', 'eoption', 'esave', 'exec', 'fill', 'global',
            'install', 'jacobian', 'lmdif', 'lmdif', 'makethin', 'match',
            'observe', 'option', 'plot', 'print', 'readtable', 'reflect',
            'return', 'run', 'save', 'savebeta', 'select',
            'select_ptc_normal', 'seqedit', 'set', 'setplot', 'setvars',
            'setvars_lin', 'show', 'simplex', 'sixtrack', 'sodd', 'start',
            'stop', 'survey', 'sxfread', 'sxfwrite', 'system', 'touschek',
            'twiss', 'use_macro', 'usekick', 'usemonitor', 'value',
            'vary', 'weight', 'wire', 'write',
        ])
        super().__init__(sirepo.sim_data.get_class('madx'))

    def parse_file(self, lattice_text):
        from sirepo.template import madx
        res = super().parse_file(lattice_text)
        cv = madx.madx_code_var(self.data.models.rpnVariables)
        self._code_variables_to_float(cv)
        self.__convert_sequences_to_beamlines(cv)
        self._set_default_beamline('use', 'sequence', 'period')
        return res

    def __convert_sequences_to_beamlines(self, code_var):
        data = PKDict(
            models=self.data.models,
        )
        drifts = self._compute_drifts(code_var)
        util = lattice.LatticeUtil(data, self.schema);
        for seq in data.models.sequences:
            beamline = PKDict(
                name=seq.name,
                items=[],
            )
            #TODO(pjm): need to realign elements which are not "at" entry
            # assert 'refer' not in seq or seq.refer.lower() == 'entry', \
            #     'unsupported sequence refer: {}: {}'.format(seq.name, seq.refer)
            prev = None
            for item in seq['items']:
                el = util.id_map[item[0]]
                at = self._eval_var(code_var, item[1])
                if prev is not None:
                    d = self._get_drift(drifts, at - prev)
                    if d:
                        beamline['items'].append(d._id)
                beamline['items'].append(el._id)
                prev = at + self._eval_var(code_var, el.get('l', 0))
            if len(beamline['items']):
                if 'l' in seq:
                    d = self._get_drift(drifts, self._eval_var(code_var, seq.l) - prev)
                    if d:
                        beamline['items'].append(d._id)
                beamline.id = self.parser.next_id()
                data.models.beamlines.append(beamline)
        del data.models['sequences']
        util.sort_elements_and_beamlines()


def parse_file(lattice_text):
    return MadXParser().parse_file(lattice_text)
