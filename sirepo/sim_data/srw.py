# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import copy
import math
import numpy
import re
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    ANALYSIS_ONLY_FIELDS = frozenset((
        'aspectRatio',
        'colorMap',
        'copyCharacteristic',
        'intensityPlotsWidth',
        'notes',
        'plotAxisX',
        'plotAxisY',
        'plotAxisY2',
        'plotScale',
        'rotateAngle',
        'rotateReshape',
    ))

    SRW_RUN_ALL_MODEL = 'simulation'

    __EXAMPLE_FOLDERS = PKDict({
        'Bending Magnet Radiation': '/SR Calculator',
        'Diffraction by an Aperture': '/Wavefront Propagation',
        'Ellipsoidal Undulator Example': '/Examples',
        'Focusing Bending Magnet Radiation': '/Examples',
        'Gaussian X-ray Beam Through Perfect CRL': '/Examples',
        'Gaussian X-ray beam through a Beamline containing Imperfect Mirrors': '/Examples',
        'Idealized Free Electron Laser Pulse': '/SR Calculator',
        'LCLS SXR beamline - Simplified': '/Light Source Facilities/LCLS',
        'LCLS SXR beamline': '/Light Source Facilities/LCLS',
        'NSLS-II CHX beamline': '/Light Source Facilities/NSLS-II/NSLS-II CHX beamline',
        'Polarization of Bending Magnet Radiation': '/Examples',
        'Soft X-Ray Undulator Radiation Containing VLS Grating': '/Examples',
        'Tabulated Undulator Example': '/Examples',
        'Undulator Radiation': '/SR Calculator',
        'Young\'s Double Slit Experiment (green laser)': '/Wavefront Propagation',
        'Young\'s Double Slit Experiment (green laser, no lens)': '/Wavefront Propagation',
        'Young\'s Double Slit Experiment': '/Wavefront Propagation',
    })

    SRW_FILE_TYPE_EXTENSIONS = PKDict(
        mirror=['dat', 'txt'],
        sample=['tif', 'tiff', 'png', 'bmp', 'gif', 'jpg', 'jpeg'],
        undulatorTable=['zip'],
        arbitraryField=['dat', 'txt'],
    )

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if analysis_model in ('coherenceXAnimation', 'coherenceYAnimation'):
            # degree of coherence reports are calculated out of the multiElectronAnimation directory
            return 'multiElectronAnimation'
        # SRW is different: it doesn't translate *Animation into animation
        return analysis_model

    @classmethod
    def fixup_old_data(cls, data):
        """Fixup data to match the most recent schema."""
        dm = data.models
        x = (
            'arbitraryMagField',
            'beamline3DReport',
            'brillianceReport',
            'coherenceXAnimation',
            'coherenceYAnimation',
            'electronBeamPosition',
            'fluxAnimation',
            'fluxReport',
            'gaussianBeam',
            'initialIntensityReport',
            'intensityReport',
            'mirrorReport',
            'powerDensityReport',
            'simulation',
            'sourceIntensityReport',
            'tabulatedUndulator',
            'trajectoryReport',
        )
        cls._init_models(dm, x)
        for m in x:
            if 'intensityPlotsScale' in dm[m]:
                dm[m].plotScale = dm[m].intensityPlotsScale
                del dm[m]['intensityPlotsScale']
        for m in dm:
            if cls.is_watchpoint(m):
                cls.update_model_defaults(dm[m], cls.WATCHPOINT_REPORT)
        # move sampleFactor to simulation model
        if 'sampleFactor' in dm.initialIntensityReport:
            if 'sampleFactor' not in dm.simulation:
                dm.simulation.sampleFactor = dm.initialIntensityReport.sampleFactor
            for k in dm:
                if k == 'initialIntensityReport' or cls.is_watchpoint(k):
                    if 'sampleFactor' in dm[k]:
                        del dm[k]['sampleFactor']
        # default intensityReport.method based on source type
        if 'method' not in dm.intensityReport:
            if cls.srw_is_undulator_source(dm.simulation):
                dm.intensityReport.method = '1'
            elif cls.srw_is_dipole_source(dm.simulation):
                dm.intensityReport.method = '2'
            else:
                dm.intensityReport.method = '0'
        # default sourceIntensityReport.method based on source type
        if 'method' not in dm.sourceIntensityReport:
            if cls.srw_is_undulator_source(dm.simulation):
                dm.sourceIntensityReport.method = '1'
            elif cls.srw_is_dipole_source(dm.simulation):
                dm.sourceIntensityReport.method = '2'
            elif cls.srw_is_arbitrary_source(dm.simulation):
                dm.sourceIntensityReport.method = '2'
            else:
                dm.sourceIntensityReport.method = '0'
        if 'facility' in dm.simulation:
            del dm.simulation['facility']
        if 'multiElectronAnimation' not in dm:
            m = dm.initialIntensityReport
            dm.multiElectronAnimation = PKDict(
                horizontalPosition=m.horizontalPosition,
                horizontalRange=m.horizontalRange,
                verticalPosition=m.verticalPosition,
                verticalRange=m.verticalRange,
            )
        cls.update_model_defaults(dm.multiElectronAnimation, 'multiElectronAnimation')
        if 'folder' not in dm.simulation:
            if dm.simulation.name in cls.__EXAMPLE_FOLDERS:
                dm.simulation.folder = cls.__EXAMPLE_FOLDERS[dm.simulation.name]
            else:
                dm.simulation.folder = '/'
        if 'horizontalPosition' in dm.electronBeam:
            e = dm.electronBeam
            dm.electronBeamPosition.update(dict(
                horizontalPosition=e.horizontalPosition,
                verticalPosition=e.verticalPosition,
                driftCalculationMethod=e.get('driftCalculationMethod', 'auto'),
                drift=e.get('drift', 0),
            ))
            for f in 'horizontalPosition', 'verticalPosition', 'driftCalculationMethod', 'drift':
                if f in e:
                    del e[f]
        cls._template_fixup_set(data)


    @classmethod
    def lib_file_name_with_type(cls, filename, file_type):
        return filename

    @classmethod
    def lib_file_name_without_type(cls, filename):
        return filename

    @classmethod
    def lib_file_names_for_type(cls, file_type):
        return sorted(
            cls.srw_lib_file_paths_for_type(
                file_type,
                lambda f: cls.srw_is_valid_file(file_type, f) and f.basename,
                want_user_lib_dir=True
            ),
        )

    @classmethod
    def srw_lib_file_paths_for_type(cls, file_type, op, want_user_lib_dir):
        """Search for files of type"""
        from sirepo import simulation_db

        res = []
        for e in cls.SRW_FILE_TYPE_EXTENSIONS[file_type]:
            for f in cls._lib_file_list('*.{}'.format(e), want_user_lib_dir=want_user_lib_dir):
                x = op(f)
                if x:
                    res.append(x)
        return res

    @classmethod
    def srw_compute_crystal_grazing_angle(cls, model):
        model.grazingAngle = math.acos(math.sqrt(1 - model.tvx ** 2 - model.tvy ** 2)) * 1e3

    @classmethod
    def srw_format_float(cls, v):
        return float('{:.8f}'.format(v))

    @classmethod
    def srw_is_arbitrary_source(cls, sim):
        return sim.sourceType == 'a'

    @classmethod
    def srw_is_background_report(cls, report):
        return 'Animation' in report

    @classmethod
    def srw_is_beamline_report(cls, report):
        return not report or cls.is_watchpoint(report) \
            or report in ('multiElectronAnimation', cls.SRW_RUN_ALL_MODEL)

    @classmethod
    def srw_is_dipole_source(cls, sim):
        return sim.sourceType == 'm'

    @classmethod
    def srw_is_gaussian_source(cls, sim):
        return sim.sourceType == 'g'

    @classmethod
    def srw_is_idealized_undulator(cls, source_type, undulator_type):
        return source_type == 'u' or (source_type == 't' and undulator_type == 'u_i')

    @classmethod
    def srw_is_tabulated_undulator_source(cls, sim):
        return sim.sourceType == 't'

    @classmethod
    def srw_is_tabulated_undulator_with_magnetic_file(cls, source_type, undulator_type):
        return source_type == 't' and undulator_type == 'u_t'

    @classmethod
    def srw_is_undulator_source(cls, sim):
        return sim.sourceType in ('u', 't')

    @classmethod
    def srw_is_user_defined_model(cls, model):
        return not model.get('isReadOnly', False)

    @classmethod
    def srw_is_valid_file(cls, file_type, path):
        # special handling for mirror and arbitraryField - scan for first data row and count columns
        if file_type not in ('mirror', 'arbitraryField'):
            return True

        _ARBITRARY_FIELD_COL_COUNT = 3

        with pkio.open_text(path) as f:
            for line in f:
                if re.search(r'^\s*#', line):
                    continue
                c = len(line.split())
                if c > 0:
                    if file_type == 'arbitraryField':
                        return c == _ARBITRARY_FIELD_COL_COUNT
                    return c != _ARBITRARY_FIELD_COL_COUNT
        return False

    @classmethod
    def srw_is_valid_file_type(cls, file_type, path):
        return path.ext[1:] in cls.SRW_FILE_TYPE_EXTENSIONS.get(file_type, tuple())

    @classmethod
    def srw_predefined(cls):
        import pykern.pkjson
        import sirepo.template.srw_common

        f = cls.resource_path(sirepo.template.srw_common.PREDEFINED_JSON)
        if not f.check():
            assert pkconfig.channel_in('dev'), \
                '{}: not found; call "sirepo srw create-predefined" before pip install'.format(f)
            import sirepo.pkcli.srw
            sirepo.pkcli.srw.create_predefined()
        return cls._memoize(pykern.pkjson.load_any(f))

    @classmethod
    def srw_uses_tabulated_zipfile(cls, data):
        return cls.srw_is_tabulated_undulator_with_magnetic_file(
            data.models.simulation.sourceType,
            data.models.tabulatedUndulator.undulatorType,
        )

    @classmethod
    def want_browser_frame_cache(cls):
        return False

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        if r == 'mirrorReport':
            return [
                'mirrorReport.heightProfileFile',
                'mirrorReport.orientation',
                'mirrorReport.grazingAngle',
                'mirrorReport.heightAmplification',
            ]
        res = cls._non_analysis_fields(data, r) + [
            'electronBeam', 'electronBeamPosition', 'gaussianBeam', 'multipole',
            'simulation.sourceType', 'tabulatedUndulator', 'undulator',
            'arbitraryMagField',
        ]
        watchpoint = cls.is_watchpoint(r)
        if watchpoint or r == 'initialIntensityReport':
            res.extend([
                'simulation.horizontalPointCount',
                'simulation.horizontalPosition',
                'simulation.horizontalRange',
                'simulation.photonEnergy',
                'simulation.sampleFactor',
                'simulation.samplingMethod',
                'simulation.verticalPointCount',
                'simulation.verticalPosition',
                'simulation.verticalRange',
                'simulation.distanceFromSource',
            ])
        if r == 'initialIntensityReport':
            beamline = data['models']['beamline']
            res.append([beamline[0]['position'] if len(beamline) else 0])
        if watchpoint:
            wid = cls.watchpoint_id(r)
            beamline = data['models']['beamline']
            propagation = data['models']['propagation']
            for item in beamline:
                item_copy = item.copy()
                del item_copy['title']
                res.append(item_copy)
                res.append(propagation[str(item['id'])])
                if item['type'] == 'watch' and item['id'] == wid:
                    break
            if beamline[-1]['id'] == wid:
                res.append('postPropagation')
        return res

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        dm = data.models
        # the mirrorReport.heightProfileFile may be different than the file in the beamline
        r = data.get('report')
        if r == 'mirrorReport':
            res.append(dm.mirrorReport.heightProfileFile)
        if cls.srw_uses_tabulated_zipfile(data):
            if 'tabulatedUndulator' in dm and dm.tabulatedUndulator.magneticFile:
                res.append(dm.tabulatedUndulator.magneticFile)
        if cls.srw_is_arbitrary_source(dm.simulation):
            res.append(dm.arbitraryMagField.magneticFile)
        if cls.srw_is_beamline_report(r):
            s = cls.schema()
            for m in dm.beamline:
                for k, v in s.model[m.type].items():
                    if k not in m:
                        # field may be missing and fixups are not applied
                        # until sim is loaded in prepare_for_client()
                        continue
                    t = v[1]
                    if m[k] and t in ('MirrorFile', 'ImageFile'):
                        res.append(m[k])
        return res
