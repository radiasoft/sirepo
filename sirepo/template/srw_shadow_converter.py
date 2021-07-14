# -*- coding: utf-8 -*-
u"""Convert codes to/from SRW/shadow.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from pykern.pkcollections import PKDict
from sirepo import simulation_db
import math
import sirepo.sim_data
import scipy.constants

_SRW = sirepo.sim_data.get_class('srw')
_SHADOW = sirepo.sim_data.get_class('shadow')


class SRWShadowConverter():

    __FIELD_MAP = [
        # [shadow model, srw model, field map (field=field or field=[field, scale])
        ['aperture', 'aperture', PKDict(
            shape='shape',
            horizontalSize='horizontalSize',
            verticalSize='verticalSize',
            horizontalOffset='horizontalOffset',
            verticalOffset='verticalOffset',
        )],
        ['bendingMagnet', 'simulation', PKDict(
            ph1='photonEnergy',
            ph2='photonEnergy',
        )],
        ['crl', 'crl', PKDict(
            lensDiameter='horizontalApertureSize',
            lensThickness=['tipWallThickness', 1e-3],
            numberOfLenses='numberOfLenses',
            rmirr=['tipRadius', 1e-3],
        )],
        ['crystal', 'crystal', PKDict(
            phot_cent='energy',
            braggMillerH='h',
            braggMillerK='k',
            braggMillerL='l',
        )],
        ['undulator', 'undulator', PKDict(
            k_horizontal='horizontalDeflectingParameter',
            k_vertical='verticalDeflectingParameter',
            length='length',
            period='period',
        )],
        ['electronBeam', 'electronBeam', PKDict(
            bener='energy',
            sigmax='rmsSizeX',
            sigmaz='rmsSizeY',
            epsi_x='horizontalEmittance',
            epsi_z='verticalEmittance',
        )],
        ['undulatorBeam', 'electronBeam', PKDict(
            alpha_x='horizontalAlpha',
            alpha_y='verticalAlpha',
            beta_x='horizontalBeta',
            beta_y='verticalBeta',
            current='current',
            emittance_x='horizontalEmittance',
            emittance_y='verticalEmittance',
            energy='energy',
            energy_spread='rmsSpread',
            eta_x='horizontalDispersion',
            eta_y='verticalDispersion',
            etap_x='horizontalDispersionDerivative',
            etap_y='verticalDispersionDerivative',
        )],
        ['geometricSource', 'simulation', PKDict(
            singleEnergyValue='photonEnergy',
        )],
        ['geometricSource', 'gaussianBeam', PKDict(
            sigmax='rmsSizeX',
            sigmaz='rmsSizeY',
            sigdix=['rmsDivergenceX', 1e-3],
            sigdiz=['rmsDivergenceY', 1e-3],
        )],
        ['lens', 'lens', PKDict(
            focal_x='horizontalFocalLength',
            focal_z='verticalFocalLength',
        )],
        ['grating', 'grating', PKDict(
            rulingDensityPolynomial='grooveDensity0',
            rul_a1='grooveDensity1',
            rul_a2='grooveDensity2',
            rul_a3='grooveDensity3',
            rul_a4='grooveDensity4',
            halfWidthX1=['sagittalSize', 1e3 / 2],
            halfWidthX2=['sagittalSize', 1e3 / 2],
            halfLengthY1=['tangentialSize', 1e3 / 2],
            halfLengthY2=['tangentialSize', 1e3 / 2],
            order=['diffractionOrder', -1],
            phot_cent='energyAvg',
        )],
        ['mirror', 'ellipsoidMirror', PKDict(
            halfWidthX1=['sagittalSize', 1e3 / 2],
            halfWidthX2=['sagittalSize', 1e3 / 2],
            halfLengthY1=['tangentialSize', 1e3 / 2],
            halfLengthY2=['tangentialSize', 1e3 / 2],
            ssour='firstFocusLength',
            simag='focalLength',
        )],
        ['mirror', 'sphericalMirror', PKDict(
            halfWidthX1=['sagittalSize', 1e3 / 2],
            halfWidthX2=['sagittalSize', 1e3 / 2],
            halfLengthY1=['tangentialSize', 1e3 / 2],
            halfLengthY2=['tangentialSize', 1e3 / 2],
            rmirr=['radius', 1e3],
        )],
        ['mirror', 'toroidalMirror', PKDict(
            halfWidthX1=['sagittalSize', 1e3 / 2],
            halfWidthX2=['sagittalSize', 1e3 / 2],
            halfLengthY1=['tangentialSize', 1e3 / 2],
            halfLengthY2=['tangentialSize', 1e3 / 2],
            r_maj='tangentialRadius',
            r_min='sagittalRadius',
        )],
        #TODO(pjm): srw "mirror" is only mirror errors, not reflective
        # ['mirror', 'mirror', PKDict(
        #     halfWidthX1=['horizontalTransverseSize', 1e3 / 2],
        #     halfWidthX2=['horizontalTransverseSize', 1e3 / 2],
        #     halfLengthY1=['verticalTransverseSize', 1e3 / 2],
        #     halfLengthY2=['verticalTransverseSize', 1e3 / 2],
        # )],
        ['obstacle', 'obstacle', PKDict(
            shape='shape',
            horizontalSize='horizontalSize',
            verticalSize='verticalSize',
            horizontalOffset='horizontalOffset',
            verticalOffset='verticalOffset',
        )],
        ['rayFilter', 'simulation', PKDict(
            x1=['horizontalRange', -0.5],
            x2=['horizontalRange', 0.5],
            z1=['verticalRange', -0.5],
            z2=['verticalRange', 0.5],
        )],
        ['watch', 'watch', PKDict()],
        ['zonePlate', 'zonePlate', PKDict(
            width_coating=['thickness', 1e3],
            height=['outerRadius', 2],
            diameter=['outerRadius', 2],
            zone_plate_material='mainMaterial',
            template_material='complementaryMaterial',
        )],
    ]

    def __init__(self):
        pass

    def shadow_to_srw(self, data):
        #TODO(pjm): implement this
        pass

    def srw_to_shadow(self, models):
        res = simulation_db.default_data(_SHADOW.sim_type())
        self.beamline = res.models.beamline
        self.__simulation_to_shadow(models, res.models)
        if res.models.simulation.sourceType == 'geometricSource':
            self.__beam_to_shadow(models, res.models)
        elif res.models.simulation.sourceType == 'undulator':
            self.__undulator_to_shadow(models, res.models)
        elif res.models.simulation.sourceType == 'bendingMagnet':
            self.__multipole_to_shadow(models, res.models)
        self.__beamline_to_shadow(models, res.models)
        if res.models.simulation.sourceType == 'undulator':
            self.__fix_undulator_gratings(res.models)
        _SHADOW.fixup_old_data(res)
        return res

    def __beam_to_shadow(self, srw, shadow):
        self.__copy_model_fields('geometricSource', srw, shadow)
        shadow.geometricSource.update(
            f_color='1',
            fsour='3',
            fdistr='3',
        )
        shadow.sourceDivergence.update(
            hdiv1=0,
            hdiv2=0,
            vdiv1=0,
            vdiv2=0,
        )
        self.photon_energy = shadow.geometricSource.singleEnergyValue

    def __beamline_to_shadow(self, srw, shadow):
        for item in srw.beamline:
            #TODO(pjm): implement more beamline elements
            if item.type == 'watch':
                watch = self.__copy_item(item)
                self.beamline.append(watch)
                shadow[f'watchpointReport{watch.id}'] = PKDict(
                    colorMap=srw[f'watchpointReport{item.id}'].colorMap,
                )
            elif item.type in ('aperture', 'obstacle'):
                ap = self.__copy_item(item)
                ap.shape = '0' if ap.shape == 'r' else '1'
                self.beamline.append(ap)
            elif item.type == 'crl':
                self.beamline.append(self.__crl_to_shadow(item))
            elif item.type == 'crystal':
                self.__crystal_to_shadow(item)
            elif item.type in ('ellipsoidMirror', 'sphericalMirror', 'toroidalMirror'):
                self.__mirror_to_shadow(item, shadow)
            elif item.type == 'grating':
                self.__grating_to_shadow(item, shadow)
            elif item.type == 'lens':
                self.beamline.append(self.__copy_item(item, PKDict(
                    type='lens',
                )))
            elif item.type == 'zonePlate':
                self.__zoneplate_to_shadow(item, shadow)

    def __closest_undulator_harmonic(self, srw):
        from orangecontrib.shadow.util.undulator.source_undulator import SourceUndulator
        from syned.storage_ring.electron_beam import ElectronBeam
        from syned.storage_ring.magnetic_structures.undulator import Undulator
        ebeam = ElectronBeam(
            energy_in_GeV=srw.electronBeam.energy,
        )
        gamma = ebeam.gamma()
        u = Undulator(
            K_horizontal=float(srw.undulator.horizontalDeflectingParameter),
            K_vertical=float(srw.undulator.verticalDeflectingParameter),
            period_length=float(srw.undulator.period) * 1e-3,
            number_of_periods=int(float(srw.undulator.length) / (float(srw.undulator.period) * 1e-3)),
        )
        search_energy = float(srw.simulation.photonEnergy)
        diff = search_energy
        harmonic = '1'
        energy = 1000
        for h in _SHADOW.schema().enum.Harmonic:
            v = u.resonance_energy(gamma, harmonic=int(h[0]))
            if abs(search_energy - v) < diff:
                diff = abs(search_energy - v)
                harmonic = h[0]
                energy = v
            if v > search_energy:
                break
        su = SourceUndulator(
            syned_electron_beam=ebeam,
            syned_undulator=u,
        )
        su.set_energy_monochromatic_at_resonance(int(harmonic))
        return harmonic, round(su._EMIN, 2), round(su._MAXANGLE * 1e6, 4)

    def __crl_to_shadow(self, item):
        return self.__copy_item(item, PKDict(
            type='crl',
            attenuationCoefficient=1e-2 / float(item.attenuationLength),
            fcyl='0',
            fhit_c='1',
            fmirr='4' if item.shape == '1' else '1',
            focalDistance=float(item.position) * float(item.focalDistance) / (float(item.position) - float(item.focalDistance)),
            pilingThickness=0,
            refractionIndex=1 - float(item.refractiveIndex),
        ))

    def __crystal_to_shadow(self, item):
        material_map = PKDict({
            'Germanium (X0h)': 'Ge',
            'Diamond (X0h)': 'Diamond',
        })
        angle, rotate, offset = self.__compute_angle(
            'vertical' if item.diffractionAngle == '0' or item.diffractionAngle == '3.14159265' \
            else 'horizontal',
            item)
        self.beamline.append(self.__copy_item(item, PKDict(
            type='crystal',
            braggMaterial=material_map.get(item.material, 'Si'),
            f_mosaic='0',
            braggMinEnergy=item.energy - 500,
            braggMaxEnergy=item.energy + 500,
            braggEnergyStep=50,
            alpha=rotate,
        )))
        self.__reset_rotation(rotate, item.position)


    def __compute_angle(self, orientation, item):
        rotate = 0
        offset = 0
        if orientation == 'horizontal':
            vector_x = item.get('normalVectorX', item.get('nvx', 0))
            rotate = 90 if vector_x >= 0 else 270
            offset = item.get('horizontalOffset', item.get('horizontalPosition', 0))
        if orientation == 'vertical':
            vector_y = item.get('normalVectorY', item.get('nvy', 0))
            rotate = 0 if vector_y >= 0 else 180
            offset = item.get('verticalOffset', item.get('verticalPosition', 0))
        angle = 90 - (abs(float(item.grazingAngle)) * 180 / math.pi / 1e3)
        return angle, rotate, offset

    def __copy_fields(self, name, srw, shadow, is_item):
        for m in self.__FIELD_MAP:
            if m[0] != name:
                continue
            _, srw_name, fields = m
            if is_item and srw.type != srw_name:
                continue
            schema = _SRW.schema().model[srw_name]
            for f in fields:
                if isinstance(fields[f], list):
                    srw_f, scale = fields[f]
                else:
                    srw_f, scale = fields[f], 1
                v = srw[srw_f] if is_item else srw[srw_name][srw_f]
                if schema[srw_f][1] == 'Float':
                    v = float(v) * scale
                if is_item:
                    shadow[f] = v
                else:
                    shadow[name][f] = v

    def __copy_item(self, item, attrs=None):
        res = PKDict(
            id=self.__next_id(),
            type=item.type,
            position=item.position,
            title=item.title,
        )
        if item.get('isDisabled') and item.isDisabled:
            res.isDisabled = item.isDisabled
        if attrs:
            res.update(attrs)
        self.__copy_item_fields(item, res)
        return res

    def __copy_item_fields(self, srw, shadow):
        self.__copy_fields(shadow.type, srw, shadow, True)

    def __copy_model_fields(self, name, srw, shadow):
        self.__copy_fields(name, srw, shadow, False)

    def __grating_to_shadow(self, item, shadow):
        angle, rotate, offset = self.__compute_angle(
            'horizontal' if item.outoptvy == 0 else 'vertical',
            item,
        )
        self.beamline.append(self.__copy_item(item, PKDict(
            type='grating',
            fmirr='5',
            t_incidence=angle,
            alpha=rotate,
            f_ruling='5',
            fhit_c='1',
            fshape='1',
            f_default='0',
            theta=angle,
            t_reflection=angle,
            f_central='1',
            f_rul_abs='1',
            f_mono='0',
            offz=offset,
        )))
        self.__reset_rotation(rotate, item.position)

    def __fix_undulator_gratings(self, shadow):
        # fix target photon energy on any gratings to exact photon energy value
        for item in shadow.beamline:
            if item.type == 'grating':
                item.phot_cent = shadow.undulator.photon_energy

    def __mirror_to_shadow(self, item, shadow):
        orientation = item.get('autocomputeVectors')
        if item.type == 'mirror':
            orientation = 'horizontal' if item.orientation == 'x' else 'vertical'
        angle, rotate, offset = self.__compute_angle(orientation, item)
        if item.type in ('mirror', 'ellipsoidMirror', 'sphericalMirror', 'toroidalMirror'):
            mirror_shape = PKDict(
                mirror='5',
                ellipsoidMirror='2',
                sphericalMirror='1',
                toroidalMirror='3',
            )
            self.beamline.append(self.__copy_item(item, PKDict(
                type='mirror',
                fmirr=mirror_shape[item.type],
                t_incidence=angle,
                alpha=rotate,
                fhit_c='1',
                fshape='1',
                f_default='0',
                theta=angle,
                offz=offset,
                f_ext='0' if item.type == 'ellipsoidMirror' else '1',
            )))
        self.__reset_rotation(rotate, item.position)
        #TODO(pjm): set vars: offx, offy, x_rot, y_rot, z_rot, cil_ang

    def __multipole_to_shadow(self, srw, shadow):
        self.__copy_model_fields('bendingMagnet', srw, shadow)
        shadow.bendingMagnet.ph2 = shadow.bendingMagnet.ph1 + 0.001
        self.__copy_model_fields('electronBeam', srw, shadow)

        self.__copy_model_fields('rayFilter', srw, shadow)
        shadow.rayFilter.f_bound_sour = '2'
        shadow.rayFilter.distance = srw.beamline[0].position

        # calculate magnet radius
        shadow.bendingMagnet.r_magnet = 1e9 / scipy.constants.c * srw.electronBeam.energy / srw.multipole.field


    def __next_id(self):
        res = 0
        for item in self.beamline:
            if item.id > res:
                res = item.id
        return res + 1

    def __reset_rotation(self, rotate, position):
        if rotate != 0:
            self.beamline.append(PKDict(
                type='emptyElement',
                id=self.__next_id(),
                position=position,
                title='Reset Orientation',
                alpha=str(360 - rotate),
            ))

    def __simulation_to_shadow(self, srw, shadow):
        _SOURCE_TYPE = PKDict(
            g='geometricSource',
            u='undulator',
            m='bendingMagnet',
        )
        shadow.simulation.update(
            sourceType=_SOURCE_TYPE[srw.simulation.sourceType],
            name=f'{srw.simulation.name} (from SRW)',
            npoint=100000,
        )
        shadow.plotXYReport.distanceFromSource = srw.simulation.distanceFromSource
        shadow.initialIntensityReport.colorMap = srw.initialIntensityReport.colorMap

    def __undulator_to_shadow(self, srw, shadow):
        self.__copy_model_fields('undulator', srw, shadow)
        self.__copy_model_fields('undulatorBeam', srw, shadow)
        harmonic, energy, angle = self.__closest_undulator_harmonic(srw)
        shadow.undulator.update(
            energy_harmonic=harmonic,
            f_coher='1',
            select_energy='harmonic',
            photon_energy=energy,
            maxangle=angle,
        )
        self.photon_energy = energy


    def __zoneplate_to_shadow(self, item, shadow):
        #TODO(pjm): map User-defined matrials to defaults
        self.beamline.append(self.__copy_item(item, PKDict(
            type='zonePlate',
            zone_plate_type='0',
            b_min=(2 * item.outerRadius * 1e-3) / (4 * item.numberOfZones) * 1e6,
        )))
