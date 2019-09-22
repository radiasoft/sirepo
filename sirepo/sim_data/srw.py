# -*- coding: utf-8 -*-
u"""myapp simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkinspect
from sirepo import simulation_db
import math
import numpy
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    EXAMPLE_FOLDERS = pkcollections.Dict({
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

    RUN_ALL_MODEL = 'simulation'

    @classmethod
    def compute_crystal_grazing_angle(cls, model):
        model.grazingAngle = math.acos(math.sqrt(1 - model.tvx ** 2 - model.tvy ** 2)) * 1e3

    @classmethod
    def fixup_old_data(cls, data):
        """Fixup data to match the most recent schema."""
        dm = data.models
        x = (
            'arbitraryMagField',
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
        cls.init_models(dm, x)
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
            if cls.is_undulator_source(dm.simulation):
                dm.intensityReport.method = '1'
            elif cls.is_dipole_source(dm.simulation):
                dm.intensityReport.method = '2'
            else:
                dm.intensityReport.method = '0'
        # default sourceIntensityReport.method based on source type
        if 'method' not in dm.sourceIntensityReport:
            if cls.is_undulator_source(dm.simulation):
                dm.sourceIntensityReport.method = '1'
            elif cls.is_dipole_source(dm.simulation):
                dm.sourceIntensityReport.method = '2'
            elif cls.is_arbitrary_source(dm.simulation):
                dm.sourceIntensityReport.method = '2'
            else:
                dm.sourceIntensityReport.method = '0'
        if 'simulationStatus' not in dm or 'state' in dm.simulationStatus:
            dm.simulationStatus = pkcollections.Dict()
        if 'facility' in dm.simulation:
            del dm.simulation['facility']
        if 'multiElectronAnimation' not in dm:
            m = dm.initialIntensityReport
            dm.multiElectronAnimation = pkcollections.Dict(
                horizontalPosition=m.horizontalPosition,
                horizontalRange=m.horizontalRange,
                verticalPosition=m.verticalPosition,
                verticalRange=m.verticalRange,
            )
        cls.update_model_defaults(dm.multiElectronAnimation, 'multiElectronAnimation')
        if 'folder' not in dm.simulation:
            if dm.simulation.name in cls.EXAMPLE_FOLDERS:
                dm.simulation.folder = cls.EXAMPLE_FOLDERS[dm.simulation.name]
            else:
                dm.simulation.folder = '/'
        cls.template_fixup_set(data)

    @classmethod
    def is_arbitrary_source(cls, sim):
        return sim.sourceType == 'a'

    @classmethod
    def is_background_report(cls, report):
        return 'Animation' in report

    @classmethod
    def is_beamline_report(cls, report):
        return not report or cls.is_watchpoint(report) \
            or report in ('multiElectronAnimation', cls.RUN_ALL_MODEL)

    @classmethod
    def is_dipole_source(cls, sim):
        return sim.sourceType == 'm'

    @classmethod
    def is_gaussian_source(cls, sim):
        return sim.sourceType == 'g'

    @classmethod
    def is_idealized_undulator(cls, source_type, undulator_type):
        return source_type == 'u' or (source_type == 't' and undulator_type == 'u_i')

    @classmethod
    def is_tabulated_undulator_source(cls, sim):
        return sim.sourceType == 't'

    @classmethod
    def is_tabulated_undulator_with_magnetic_file(cls, source_type, undulator_type):
        return source_type == 't' and undulator_type == 'u_t'

    @classmethod
    def is_undulator_source(cls, sim):
        return sim.sourceType in ('u', 't')

    @classmethod
    def is_user_defined_model(cls, model):
        return not model.get('isReadOnly', False)
