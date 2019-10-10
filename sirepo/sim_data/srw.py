# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import math
import numpy
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    _ANALYSIS_ONLY_FIELDS = frozenset(
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
    )

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

    SRW_RUN_ALL_MODEL = 'simulation'

    @classmethod
    def compute_job_fields(cls, data):
        r = data['report']
        if r == 'mirrorReport':
            return [
                'mirrorReport.heightProfileFile',
                _lib_file_datetime(data['models']['mirrorReport']['heightProfileFile']),
                'mirrorReport.orientation',
                'mirrorReport.grazingAngle',
                'mirrorReport.heightAmplification',
            ]
        res = cls._fields_for_compute(data, r) + [
            'electronBeam', 'electronBeamPosition', 'gaussianBeam', 'multipole',
            'simulation.sourceType', 'tabulatedUndulator', 'undulator',
            'arbitraryMagField',
        ]
        if cls.srw_uses_tabulated_zipfile(data):
            res += cls._lib_file_mtimes(data.models.tabulatedUndulator.magneticFile)
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
                if item['type'] == 'mirror':
                    res.append(_lib_file_datetime(item['heightProfileFile']))
                elif item['type'] == 'sample':
                    res.append(_lib_file_datetime(item['imageFile']))
                elif item['type'] == 'watch' and item['id'] == wid:
                    break
            if beamline[-1]['id'] == wid:
                res.append('postPropagation')
        return res

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
        if 'simulationStatus' not in dm or 'state' in dm.simulationStatus:
            dm.simulationStatus = PKDict()
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
        cls._template_fixup_set(data)

    @classmethod
    def srw_compute_crystal_grazing_angle(cls, model):
        model.grazingAngle = math.acos(math.sqrt(1 - model.tvx ** 2 - model.tvy ** 2)) * 1e3

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
    def srw_uses_tabulated_zipfile(cls, data):
        return cls.srw_is_tabulated_undulator_with_magnetic_file(
            data.models.simulation.sourceType,
            data.models.tabulatedUndulator.undulatorType,
        )


    @classmethod
    def _lib_files(cls, data):
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
            for m in dm.beamline:
                for k, v in _SCHEMA.model[m.type].items():
                    t = v[1]
                    if m[k] and t in ('MirrorFile', 'ImageFile'):
                        res.append(m[k])
        return res
