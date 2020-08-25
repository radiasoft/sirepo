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
        'maxIntensityLimit',
        'minIntensityLimit',
        'notes',
        'plotAxisX',
        'plotAxisY',
        'plotAxisY2',
        'plotScale',
        'rotateAngle',
        'rotateReshape',
        'useIntensityLimits',
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
        has_electron_beam_position = 'electronBeamPosition' in dm
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
        e = dm.electronBeam
        if not has_electron_beam_position:
            dm.electronBeamPosition.update(
                horizontalPosition=e.horizontalPosition,
                verticalPosition=e.verticalPosition,
                driftCalculationMethod=e.get('driftCalculationMethod', 'auto'),
                drift=e.get('drift', 0),
            )
        if 'horizontalPosition' in e:
            for f in 'horizontalPosition', 'verticalPosition', 'driftCalculationMethod', 'drift':
                if f in e:
                    del e[f]
        cls.__fixup_old_data_beamline(data)
        cls.__fixup_old_data_by_template(data)
        hv = ('horizontalPosition', 'horizontalRange', 'verticalPosition', 'verticalRange')
        if 'samplingMethod' not in dm.simulation:
            simulation = dm.simulation
            simulation.samplingMethod = 1 if simulation.sampleFactor > 0 else 2
            for k in hv:
                simulation[k] = dm.initialIntensityReport[k]
        if 'horizontalPosition' in dm.initialIntensityReport:
            for k in dm:
                if k == 'sourceIntensityReport' or k == 'initialIntensityReport' or cls.is_watchpoint(k):
                    for f in hv:
                        del dm[k][f]
        if 'indexFile' in data.models.tabulatedUndulator:
            del data.models.tabulatedUndulator['indexFile']
        u = dm.undulator
        if 'effectiveDeflectingParameter' not in u and 'horizontalDeflectingParameter' in u:
            u.effectiveDeflectingParameter = math.sqrt(
                u.horizontalDeflectingParameter ** 2 + u.verticalDeflectingParameter ** 2,
            )
        for k in (
            'photonEnergy',
            'horizontalPointCount',
            'horizontalPosition',
            'horizontalRange',
            'sampleFactor',
            'samplingMethod',
            'verticalPointCount',
            'verticalPosition',
            'verticalRange',
        ):
            if k not in dm.sourceIntensityReport:
                dm.sourceIntensityReport[k] = dm.simulation[k]
        if 'photonEnergy' not in dm.gaussianBeam:
            dm.gaussianBeam.photonEnergy = dm.simulation.photonEnergy
        if 'longitudinalPosition' in dm.tabulatedUndulator:
            u = dm.tabulatedUndulator
            for k in (
                'undulatorParameter',
                'period',
                'longitudinalPosition',
                'horizontalAmplitude',
                'horizontalSymmetry',
                'horizontalInitialPhase',
                'verticalAmplitude',
                'verticalSymmetry',
                'verticalInitialPhase',
            ):
                if k in u:
                    if cls.srw_is_tabulated_undulator_source(dm.simulation):
                        dm.undulator[k] = u[k]
                    del u[k]
        if 'name' not in dm['tabulatedUndulator']:
            u = dm.tabulatedUndulator
            u.name = u.undulatorSelector = 'Undulator'
        if dm.tabulatedUndulator.get('id', '1') == '1':
            dm.tabulatedUndulator.id = '{} 1'.format(dm.simulation.simulationId)
        if len(dm.postPropagation) == 9:
            dm.postPropagation += [0, 0, 0, 0, 0, 0, 0, 0]
            for i in dm.propagation:
                for r in dm.propagation[i]:
                    r += [0, 0, 0, 0, 0, 0, 0, 0]
        if 'electronBeams' in dm:
            del dm['electronBeams']
        # special case for old examples with incorrect electronBeam.drift
        if dm.simulation.isExample and dm.simulation.name in (
                'NSLS-II HXN beamline',
                'NSLS-II HXN beamline: SSA closer',
                'NSLS-II CSX-1 beamline'):
            dm.electronBeamPosition.driftCalculationMethod = 'manual'
            dm.electronBeamPosition.drift = -1.8 if 'HXN' in dm.simulation.name else -1.0234
        cls._organize_example(data)

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
    def _organize_example(cls, data):
        dm = data.models
        if dm.simulation.get('isExample'):
            f = cls.__EXAMPLE_FOLDERS.get(dm.simulation.name)
            if f:
                dm.simulation.folder = f
        elif not dm.simulation.get('folder'):
            dm.simulation.folder = '/'

    @classmethod
    def srw_compute_crystal_grazing_angle(cls, model):
        model.grazingAngle = math.acos(math.sqrt(1 - model.tvx ** 2 - model.tvy ** 2)) * 1e3

    @classmethod
    def srw_find_closest_angle(cls, angle, allowed_angles):
        """Find closest string value from the input list to
           the specified angle (in radians).
        """
        def _wrap(a):
            """Convert an angle to constraint it between -pi and pi.
               See https://stackoverflow.com/a/29237626/4143531 for details.
            """
            return numpy.arctan2(numpy.sin(a), numpy.cos(a))

        angles = numpy.array([float(x) for x in allowed_angles])
        threshold = numpy.min(numpy.diff(angles))
        return allowed_angles[
            numpy.where(numpy.abs(_wrap(angle) - angles) < threshold / 2.0)[0][0]
        ]

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
            or report in ('multiElectronAnimation', cls.SRW_RUN_ALL_MODEL) \
            or report == 'beamline3DReport'

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
    def srw_lib_file_paths_for_type(cls, file_type, op, want_user_lib_dir):
        """Search for files of type"""
        res = []
        for e in cls.SRW_FILE_TYPE_EXTENSIONS[file_type]:
            for f in cls._lib_file_list('*.{}'.format(e), want_user_lib_dir=want_user_lib_dir):
                x = op(f)
                if x:
                    res.append(x)
        return res

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
        if watchpoint or r == 'initialIntensityReport' or r == 'beamline3DReport':
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
        #TODO(pjm): any changes to the beamline will recompute the beamline3DReport
        #           instead, need to determine which model fields affect the orientation
        if r == 'beamline3DReport':
            res.append('beamline')
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

    @classmethod
    def __fixup_old_data_by_template(cls, data):
        import sirepo.template.srw_fixup
        import sirepo.template.srw
        sirepo.template.srw_fixup.do(sirepo.template.srw, data)


    @classmethod
    def __fixup_old_data_beamline(cls, data):
        dm = data.models
        for i in dm.beamline:
            t = i.type
            if t == 'ellipsoidMirror':
                if 'firstFocusLength' not in i:
                    i.firstFocusLength = i.position
            if t in ('grating', 'ellipsoidMirror', 'sphericalMirror', 'toroidalMirror'):
                if 'grazingAngle' not in i:
                    angle = 0
                    if i.normalVectorX:
                        angle = math.acos(abs(float(i.normalVectorX))) * 1000
                    elif i.normalVectorY:
                        angle = math.acos(abs(float(i.normalVectorY))) * 1000
                    i.grazingAngle = angle
            if 'grazingAngle' in i and 'normalVectorX' in i and 'autocomputeVectors' not in i:
                i.autocomputeVectors = '1'
            if t == 'crl':
                for k, v in PKDict(
                    material='User-defined',
                    method='server',
                    absoluteFocusPosition=None,
                    focalDistance=None,
                    tipRadius=float(i.radius) * 1e6,  # m -> um
                    tipWallThickness=float(i.wallThickness) * 1e6,  # m -> um
                ).items():
                    if k not in i:
                        i[k] = v
            if t == 'crystal':
                # this is a hack for existing bad data
                for k in ['outframevx', 'outframevy', 'outoptvx', 'outoptvy', 'outoptvz',
                         'tvx', 'tvy']:
                    if i.get(k, 0) is None: i[k] = 0
                    i[k] = float(i.get(k, 0))
                if 'diffractionAngle' not in i:
                    allowed_angles = [x[0] for x in cls.schema().enum.DiffractionPlaneAngle]
                    i.diffractionAngle = cls.srw_find_closest_angle(i.grazingAngle or 0, allowed_angles)
                    if i.tvx == '':
                        i.tvx = i.tvy = 0
                    cls.srw_compute_crystal_grazing_angle(i)
            if t == 'sample':
                if 'horizontalCenterCoordinate' not in i:
                    i.horizontalCenterCoordinate = cls.schema().model.sample.horizontalCenterCoordinate[2]
                    i.verticalCenterCoordinate = cls.schema().model.sample.verticalCenterCoordinate[2]
                if 'cropArea' not in i:
                    for f in (
                        'areaXEnd',
                        'areaXStart',
                        'areaYEnd',
                        'areaYStart',
                        'backgroundColor',
                        'cropArea',
                        'cutoffBackgroundNoise',
                        'invert',
                        'outputImageFormat',
                        'rotateAngle',
                        'rotateReshape',
                        'shiftX',
                        'shiftY',
                        'tileColumns',
                        'tileImage',
                        'tileRows',
                    ):
                        i[f] = cls.schema().model.sample[f][2]
                if 'transmissionImage' not in i:
                    i.transmissionImage = cls.schema().model.sample.transmissionImage[2]
            if t in ('crl', 'grating', 'ellipsoidMirror', 'sphericalMirror') \
                and 'horizontalOffset' not in i:
                i.horizontalOffset = 0
                i.verticalOffset = 0
            if 'autocomputeVectors' in i:
                if i.autocomputeVectors == '0':
                    i.autocomputeVectors = 'none'
                elif i.autocomputeVectors == '1':
                    i.autocomputeVectors = 'vertical' if i.normalVectorX == 0 else 'horizontal'
            cls.update_model_defaults(i, t)
