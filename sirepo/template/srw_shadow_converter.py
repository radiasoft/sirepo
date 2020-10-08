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

_SRW = sirepo.sim_data.get_class('srw')
_SHADOW = sirepo.sim_data.get_class('shadow')

class SRWShadowConverter():

    def __init__(self):
        pass

    def shadow_to_srw(self, data):
        #TODO(pjm): implement this
        pass

    def srw_to_shadow(self, models):
        res = simulation_db.default_data(_SHADOW.sim_type())
        self.__simulation_to_shadow(models, res.models)
        if res.models.simulation.sourceType == 'geometricSource':
            self.__beam_to_shadow(models, res.models)
        self.__beamline_to_shadow(models, res.models)
        _SHADOW.fixup_old_data(res)
        return res

    def __beam_to_shadow(self, srw, shadow):
        shadow.geometricSource.update(
            f_color='1',
            singleEnergyValue=srw.simulation.photonEnergy,
            fsour='3',
            fdistr='3',
            sigmax=srw.gaussianBeam.rmsSizeX,
            sigmaz=srw.gaussianBeam.rmsSizeY,
            # urad to mrad
            sigdix=srw.gaussianBeam.rmsDivergenceX * 1e-3,
            sigdiz=srw.gaussianBeam.rmsDivergenceY * 1e-3,
        )
        shadow.sourceDivergence.update(
            hdiv1=0,
            hdiv2=0,
            vdiv1=0,
            vdiv2=0,
        )

    def __beamline_to_shadow(self, srw, shadow):
        current_rotation = 0
        for item in srw.beamline:
            #TODO(pjm): implement more beamline elements
            if item.type == 'watch':
                shadow.beamline.append(self.__copy_item(item, item))
                watch_name = f'watchpointReport{item.id}'
                shadow[watch_name] = PKDict(
                    colorMap=srw[watch_name].colorMap,
                )
            elif item.type in ('aperture', 'obstacle'):
                ap = self.__copy_item(item, item)
                ap.shape = '0' if ap.shape == 'r' else '1'
                shadow.beamline.append(ap)
            elif item.type == 'ellipsoidMirror':
                r = self.__mirror_to_shadow(item, current_rotation, shadow)
                current_rotation = (current_rotation + r) % 360
            elif item.type == 'grating':
                r = self.__grating_to_shadow(item, current_rotation, shadow)
                current_rotation = (current_rotation + r) % 360

    def __copy_item(self, item, attrs):
        res = PKDict(
            id=item.id,
            position=item.position,
            title=item.title,
        )
        if item.get('isDisabled') and item.isDisabled:
            res.isDisabled = item.isDisabled
        res.update(attrs)
        return res

    def __grating_to_shadow(self, item, current_rotation, shadow):
        # Not sure whether this should be subtracted from 90
        angle = 90 - (abs(item.grazingAngle) * 180 / math.pi / 1e3)
        rotate = 0
        offset = 0
        shadow.beamline.append(self.__copy_item(item, PKDict(
            type='grating',
            fmirr='5',
            t_incidence=angle,
            alpha=rotate,
            f_ruling='5',
            rulingDensityPolynomial=item.grooveDensity0,
            rul_a1=item.grooveDensity1,
            rul_a2=item.grooveDensity2,
            rul_a3=item.grooveDensity3,
            rul_a4=item.grooveDensity3,
            fhit_c='1',
            fshape='1',
            halfWidthX1=item.tangentialSize * 1e3 / 2,
            halfWidthX2=item.tangentialSize * 1e3 / 2,
            halfLengthY1=item.sagittalSize * 1e3 / 2,
            halfLengthY2=item.sagittalSize * 1e3 / 2,
            f_default='0',
            theta=angle,
            t_reflection=angle,
            f_central='0',
            order=item.diffractionOrder,
            f_rul_abs='0',
            f_mono='0',
        )))
        return rotate

    def __mirror_to_shadow(self, item, current_rotation, shadow):
        angle = 90 - (abs(item.grazingAngle) * 180 / math.pi / 1e3)
        if item.autocomputeVectors == 'horizontal':
            offset = item.horizontalOffset
            if current_rotation == 90 or current_rotation == 270:
                rotate = 0
            else:
                rotate = 90
        elif item.autocomputeVectors == 'vertical':
            offset = item.verticalOffset
            if current_rotation == 0 or current_rotation == 180:
                rotate = 0
            else:
                rotate = 90
        else:
            #TODO(pjm): determine rotation for vectors
            rotate = 0
            offset = 0
        shadow.beamline.append(self.__copy_item(item, PKDict(
            type='mirror',
            fmirr='2',
            t_incidence=angle,
            alpha=rotate,
            fhit_c='1',
            fshape='1',
            halfWidthX1=item.tangentialSize * 1e3 / 2,
            halfWidthX2=item.tangentialSize * 1e3 / 2,
            halfLengthY1=item.sagittalSize * 1e3 / 2,
            halfLengthY2=item.sagittalSize * 1e3 / 2,
            f_default='0',
            ssour=item.firstFocusLength,
            simag=item.focalLength,
            theta=angle,
            offz=offset,
        )))
        #TODO(pjm): set vars: offx, offy, x_rot, y_rot, z_rot, cil_ang
        return rotate

    def __simulation_to_shadow(self, srw, shadow):
        _SOURCE_TYPE = PKDict(
            g='geometricSource',
        )
        shadow.simulation.update(
            sourceType=_SOURCE_TYPE[srw.simulation.sourceType],
            name=f'{srw.simulation.name} (from SRW)',
            npoint=100000,
        )
        shadow.plotXYReport.distanceFromSource = srw.simulation.distanceFromSource
        shadow.initialIntensityReport.colorMap = srw.initialIntensityReport.colorMap
