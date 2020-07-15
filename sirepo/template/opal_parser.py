# -*- coding: utf-8 -*-
u"""OPAL parser.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template import lattice
from sirepo.template.code_variable import CodeVar
from sirepo.template.lattice import LatticeUtil
import os.path
import re
import sirepo.sim_data

_MATERIAL_CODE_TO_NAME = PKDict(
    al='ALUMINUM',
    be='BERYLLIUM',
    cu='COPPER',
    au='GOLD',
    mo='MOLYBDENUM',
    ti='TITANIUM',
)

class OpalParser(lattice.LatticeParser):

    def __init__(self):
        self.ignore_commands = set([
            'value',
            'stop',
            'quit',
        ])
        super().__init__(sirepo.sim_data.get_class('opal'))

    def parse_file(self, lattice_text):
        from sirepo.template import opal
        res = super().parse_file(lattice_text)
        self.__fix_pow_variables()
        self.__add_variables_for_lattice_references()
        cv = opal.opal_code_var(self.data.models.rpnVariables)
        self._code_variables_to_float(cv)
        self.__remove_bend_default_fmap()
        self.__remove_default_commands()
        self.__combine_track_and_run()
        self.util = lattice.LatticeUtil(self.data, self.schema)
        input_files = self.__update_filenames()
        self.__add_drifts_to_beamlines(cv)
        self._set_default_beamline('select', 'line')
        self.__legacy_fixups()
        self.__convert_references_to_ids()
        self.__combine_options()
        self.__dedup_elements()
        return res, input_files

    def __add_variables_for_lattice_references(self):
        # iterate all values, adding "x->y" lattice referenes as variables "x.y"

        def _fix_value(value, names):
            expr = CodeVar.infix_to_postfix(value.lower())
            for v in expr.split(' '):
                m = re.match(r'^(.*?)\-\>(.*)', v)
                if m:
                    v = re.sub(r'\-\>', '.', v)
                    names[v] = [m.group(1), m.group(2)]
            return re.sub(r'\-\>', '.', value)

        names = {}
        for v in self.data.models.rpnVariables:
            if CodeVar.is_var_value(v.value):
                v.value = _fix_value(v.value, names)
        for el in self.data.models.elements:
            for f in el:
                v = el[f]
                if CodeVar.is_var_value(v):
                    el[f] = _fix_value(v, names)
        for name in names:
            for el in self.data.models.elements:
                if el.name.lower() == names[name][0]:
                    f = names[name][1]
                    if f in el:
                        self.data.models.rpnVariables.append(PKDict(
                            name=name,
                            value=el[f],
                        ))

    def __add_drifts_to_beamlines(self, code_var):
        drifts = self._compute_drifts(code_var)
        for beamline in self.data.models.beamlines:
            current = 0
            res = []
            for item in beamline['items']:
                el = self.util.id_map[item]
                if 'elemedge' in el:
                    pos = self._eval_var(code_var, el.elemedge)
                else:
                    pos = 0
                if 'type' in el and pos != current:
                    d = self._get_drift(drifts, pos - current, allow_negative_drift=True)
                    if d:
                        res.append(d)
                        current = pos
                res.append(item)
                if 'l' in el and not code_var.is_var_value(el.l):
                    el.l = float(el.l)
                current += self._eval_var(code_var, el.get('l', 0))
            beamline['items'] = res
        for el in self.data.models.elements:
            if 'elemedge' in el:
                del el['elemedge']
        self.util.sort_elements_and_beamlines()

    def __combine_options(self):
        option = None
        res = []
        s = self.schema.model.command_option
        for cmd in self.data.models.commands:
            if cmd._type == 'option':
                if not option:
                    option = cmd
                else:
                    for f in cmd:
                        if f in s and s[f][2] != cmd[f]:
                            option[f] = cmd[f]
                    continue
            res.append(cmd)
        if option:
            option.name = 'Opt1'
        self.data.models.commands = res

    def __combine_track_and_run(self):
        fields = self.schema.model.command_track
        track = None
        res = []
        for cmd in self.data.models.commands:
            if cmd._type == 'run':
                assert track
                for f in cmd:
                    name = 'run_{}'.format(f)
                    if name in fields:
                        track[name] = cmd[f]
                continue
            if cmd._type == 'track':
                track = cmd
            res.append(cmd)
        self.data.models.commands = res

    def __convert_references_to_ids(self):
        ref_model = PKDict(
            BeamList='beam',
            FieldsolverList='fieldsolver',
            DistributionList='distribution',
            ParticlematterinteractionList='particlematterinteraction',
            WakeList='wake',
            GeometryList='geometry',
            LatticeBeamlineList='beamline',
            OptionalLatticeBeamlineList='beamline',
        )
        name_to_id = PKDict()
        for id in self.util.id_map:
            name = self.util.id_map[id].name.upper()
            assert name not in name_to_id, 'duplicate name: {}'.format(name)
            name_to_id[name] = id
        for container in ('elements', 'commands'):
            for el in self.data.models[container]:
                model_schema = self.schema.model[self.util.model_name_for_data(el)]
                for f in model_schema:
                    if f in el and el[f]:
                        el_schema = model_schema[f]
                        if el_schema[1] in ref_model:
                            el[f] = name_to_id[el[f].upper()]
                        elif el_schema[1] in self.schema.enum:
                            if el_schema[1] == 'Boolean':
                                if el[f] == '1' or el[f] == '0':
                                    pass
                                elif el[f].lower() == 'true':
                                    el[f] = '1'
                                else:
                                    el[f] = '0'
                            else:
                                el[f] = el[f].upper()
                                found_enum = False
                                if el_schema[1] == 'ParticlematterinteractionMaterial':
                                    el[f] = _MATERIAL_CODE_TO_NAME.get(el[f].lower(), el[f])
                                for e in self.schema.enum[el_schema[1]]:
                                    if el[f] == e[0]:
                                        found_enum = True
                                        break
                                assert found_enum, 'unknown value {}: {}'.format(f, el[f])

    def __dedup_elements(self):
        # iterate all element, remove duplicates, fixup beamlines
        elements_by_type = PKDict()
        for el in self.data.models.elements:
            t = el.type
            if t not in elements_by_type:
                elements_by_type[t] = []
            elements_by_type[t].append(el)
        id_map = PKDict()
        for t in elements_by_type:
            elements = elements_by_type[t]
            for i in range(len(elements)):
                if '_matched' in elements[i]:
                    continue
                for j in range(i + 1, len(elements)):
                    if '_matched' in elements[j]:
                        continue
                    is_equal = True
                    for f in elements[i]:
                        if f in ('name', '_id'):
                            continue
                        if f in elements[i] and f in elements[j] and elements[i][f] != elements[j][f]:
                            is_equal = False
                            break
                    if is_equal:
                        id_map[elements[j]._id] = elements[i]._id
                        elements[j]._matched = True
        elements = []
        for el in self.data.models.elements:
            if '_matched' not in el:
                elements.append(el)
        self.data.models.elements = elements
        for beamline in self.data.models.beamlines:
            items = []
            for el_id in beamline['items']:
                if el_id in id_map:
                    items.append(id_map[el_id])
                else:
                    items.append(el_id)
            beamline['items'] = items

    def __fix_pow_variables(self):
        # REAL beta=sqrt(1-(1/gamma^2));
        # REAL p_tot = (e_tot^2-PMASS^2)^0.5;
        for v in self.data.models.rpnVariables:
            #TODO(pjm): only works for simple cases
            v.value = re.sub(r'\(([^)]+)\)\s*\^\s*([\d.]+)', r'pow(\1,\2)', v.value)
            v.value = re.sub(r'(\w+)\s*\^\s*([\d.]+)', r'pow(\1,\2)', v.value)

    def __legacy_fixups(self):
        for cmd in self.data.models.commands:
            if cmd._type == 'distribution' \
               and not cmd.type \
               and 'distribution' in cmd:
                cmd.type = cmd.distribution
                del cmd['distribution']

    def __remove_bend_default_fmap(self):
        for el in self.data.models.elements:
            if re.search(r'bend', el.type.lower()):
                if 'fmapfn' in el and el.fmapfn.upper() == '1DPROFILE1-DEFAULT':
                    del el['fmapfn']

    def __remove_default_commands(self):
        from sirepo import simulation_db
        size = len(simulation_db.default_data(self.sim_data.sim_type()).models.commands)
        res = []
        names = set(self.data.models.commands[0].name)
        for i in range(len(self.data.models.commands)):
            cmd = self.data.models.commands[i]
            if i > size or cmd._type == 'option':
                if not cmd.name:
                    cmd.name = self.__unique_name(cmd, names)
                res.append(cmd)
                names.add(cmd.name)
        self.data.models.commands = res

    def __unique_name(self, cmd, names):
        prefix = cmd._type.upper()[:2]
        num = 1
        while True:
            name = '{}{}'.format(prefix, num)
            if name not in names:
                return name
            num += 1

    def __update_filenames(self):
        res = []
        visited = set()
        for container in ('elements', 'commands'):
            for el in self.data.models[container]:
                model_name = self.util.model_name_for_data(el)
                el_schema = self.schema.model[model_name]
                for f in el:
                    if f not in el_schema:
                        continue
                    if el_schema[f][1] == 'OutputFile' and el[f]:
                        el[f] = '1'
                    elif el_schema[f][1] == 'InputFile' and el[f]:
                        el[f] = os.path.basename(el[f])
                        filename = self.sim_data.lib_file_name_with_model_field(
                            model_name, f, el[f])
                        if filename not in visited:
                            res.append(PKDict(
                                label=el.name,
                                type=LatticeUtil.type_for_data(el),
                                file_type='{}-{}'.format(model_name, f),
                                filename=el[f],
                                field=f,
                                lib_filename=filename,
                            ))
                        visited.add(filename)
        return res


def parse_file(lattice_text, filename=None):
    res, files = OpalParser().parse_file(lattice_text)
    set_simulation_name(res, filename)
    return res, files


def set_simulation_name(data, filename):
    data.models.simulation.name = None
    commands = []
    for cmd in data.models.commands:
        if cmd._type == 'title':
            data.models.simulation.name = cmd.string
        else:
            commands.append(cmd)
    data.models.commands = commands
    if not data.models.simulation.name:
        data.models.simulation.name = re.sub(r'\..*$', '', os.path.basename(filename))
