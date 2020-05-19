# -*- coding: utf-8 -*-
"""Wrapper to run IRAD from the command line.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from dicompylercore import dicomparser, dvhcalc
from pykern.pkdebug import pkdlog, pkdp
from pykern import pkio
from pykern.pkcollections import PKDict
from sirepo import simulation_db
from sirepo.template import template_common
from zipfile import ZipFile
import copy
import json
import numpy as np
import pydicom
import sirepo.template.irad as template

_DICOM_CLASS = PKDict(
    CT_IMAGE='1.2.840.10008.5.1.4.1.1.2',
    RT_DOSE='1.2.840.10008.5.1.4.1.1.481.2',
    RT_STRUCT='1.2.840.10008.5.1.4.1.1.481.3',
)
_DVH_FILE_NAME = 'dvh-data.json'
_PIXEL_DATA_DIR = 'data'
_PIXEL_DATA_FILE = '{}/out.bin'.format(_PIXEL_DATA_DIR)
_ROI_FILE_NAME = template.RTSTRUCT_FILE
_VTI_CT_ZIP_FILE = template.CT_FILE
_VTI_RTDOSE_ZIP_FILE = template.RTDOSE_FILE
_VTI_TEMPLATE = PKDict(
    cellData=PKDict(
        arrays=[],
        vtkClass='vtkDataSetAttributes'
    ),
    fieldData=PKDict(
        arrays=[],
        vtkClass='vtkDataSetAttributes'
    ),
    vtkClass='vtkImageData',
    pointData=PKDict(
        arrays=[
            PKDict(
                data=PKDict(
                    numberOfComponents=1,
                    name='ImageScalars',
                    vtkClass='vtkDataArray',
                    ref=PKDict(
                        registration='setScalars',
                        encode='LittleEndian',
                        basepath='data',
                        id='out.bin'
                    )
                )
            )
        ],
        vtkClass='vtkDataSetAttributes'
    ),
)

def process_dicom_files(cfg_dir):
    # convert dicom files into ct.zip, rt.zip, rtdose.json and rtstruct.json
    files = _dicom_files(cfg_dir)
    ctinfo = _write_ct_vti_file(files)
    pkdlog('ct: {}', ctinfo)
    rtdose = _write_rtdose_file(files)
    pkdlog('rtdose: {}', rtdose)
    pkdlog('creating rtstruct')
    rois = _write_rtstruct_file(files)
    pkdlog('computing dvh')
    _write_dvh_file(files, rois)
    pkdlog('done')


def run(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if data.report == 'dvhReport':
        sim_id = data.models.simulation.simulationId
        filename = template.sim_file(sim_id, _DVH_FILE_NAME)
        template_common.write_sequential_result(simulation_db.read_json(filename))
    elif data.report == 'dicom3DReport':
        template_common.write_sequential_result({
            'simulationId': data.models.simulation.simulationId,
        })
    else:
        assert False, 'unknown report: {}'.format(data.report)


def _compute_dvh(roi_numbers, rtstruct, rtdose):
    y_range = None
    plots = []
    max_x = 0
    rtdose = dicomparser.DicomParser(rtdose)
    dp = dicomparser.DicomParser(rtstruct)
    for roi_number in roi_numbers:
        roi_number = int(roi_number)
        for roi in dp.ds.ROIContourSequence:
            if roi.ReferencedROINumber == roi_number and 'ContourSequence' in roi:
                for c in roi.ContourSequence:
                    if 'ContourImageSequence' not in c:
                        c.ContourImageSequence = []
    for roi_number in roi_numbers:
        roi_number = int(roi_number)
        s = dp.GetStructures()[roi_number]
        pkdlog('  {}: {}', roi_number, s['name'])
        s['planes'] = dp.GetStructureCoordinates(roi_number)
        s['thickness'] = dp.CalculatePlaneThickness(s['planes'])
        calcdvh = dvhcalc.calculate_dvh(s, rtdose, None, True, None)
        counts = np.append(calcdvh.histogram, 0.0)
        counts = counts[::-1].cumsum()[::-1]
        if len(counts) and counts.max() > 0:
            counts = 100 * counts / counts.max()
        max_x = max(max_x, counts.size)
        min_y = np.min(counts)
        max_y = np.max(counts)
        if y_range:
            if min_y < y_range[0]:
                y_range[0] = min_y
            if max_y > y_range[1]:
                y_range[1] = max_y
        else:
            y_range = [min_y, max_y]
        rgb = s['color']
        plots.append({
            'points': counts.tolist(),
            'color': '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2])),
            'label': s['name'],
        })
    return {
        'title': '',
        'aspectRatio': 1,
        'x_range': [0, max_x / 100.0, max_x],
        'y_label': 'Volume [%]',
        'x_label': 'Dose [gy]',
        'y_range': y_range,
        'plots': sorted(plots, key=lambda v: v['label'].lower()),
    }


def _dicom_files(dirname):
    files = PKDict(
        ctmap=PKDict(),
        rtdose=None,
        rtstruct=None,
        position=None,
    )
    for path in pkio.walk_tree(dirname):
        if not pkio.has_file_extension(str(path), 'dcm'):
            continue
        v = pydicom.dcmread(str(path), specific_tags=[
            'SOPClassUID',
            'InstanceNumber',
            'PatientPosition',
        ])
        if v.SOPClassUID == _DICOM_CLASS.CT_IMAGE:
            files.ctmap[int(v.InstanceNumber)] = str(path)
            files.position = v.PatientPosition
        elif v.SOPClassUID == _DICOM_CLASS.RT_DOSE:
            files.rtdose = str(path)
        elif v.SOPClassUID == _DICOM_CLASS.RT_STRUCT:
            files.rtstruct = str(path)
    assert files.rtdose and files.rtstruct, 'Missing RTSTRUCT and/or RTDOSE'
    return files


def _extract_dcm_info(files, info, frame):
    if info is None:
        info = PKDict(
            ImagePositionPatient=_float_list(frame.ImagePositionPatient),
            PixelSpacing=_float_list(frame.PixelSpacing),
            Rows=frame.Rows,
            Columns=frame.Columns,
            ImageOrientationPatient=_float_list(frame.ImageOrientationPatient),
            BitsAllocated=frame.BitsAllocated,
        )
        if 'PatientPosition' in frame:
            # ct
            info.update(PKDict(
                PatientPosition=frame.PatientPosition,
                # WindowCenter=float(frame.WindowCenter),
                # WindowWidth=float(frame.WindowWidth),
                RescaleIntercept=float(frame.RescaleIntercept),
                RescaleSlope=float(frame.RescaleSlope),
                Count=len(files.ctmap),
            ))
        else:
            # rtdose
            info.SliceThickness=float(frame.GridFrameOffsetVector[1]) - float(frame.GridFrameOffsetVector[0])
            info.Count=int(frame.NumberOfFrames)
    elif 'SliceThickness' not in info:
        info.SliceThickness = abs(info.ImagePositionPatient[2] - frame.ImagePositionPatient[2])
    return info


def _float_list(ar):
    return [float(x) for x in ar]


def _write_ct_vti_file(files):
    ctinfo = None
    #instance_numbers = sorted(files.ctmap.keys()) if files.position == 'HFS' else reversed(sorted(files.ctmap.keys()))
    instance_numbers = sorted(files.ctmap.keys())
    if pydicom.dcmread(files.ctmap[instance_numbers[0]]).ImagePositionPatient[2] \
       > pydicom.dcmread(files.ctmap[instance_numbers[-1]]).ImagePositionPatient[2]:
        instance_numbers = reversed(instance_numbers)
    for idx in instance_numbers:
        frame = pydicom.dcmread(files.ctmap[idx])
        ctinfo = _extract_dcm_info(files, ctinfo, frame)
        pkio.mkdir_parent(_PIXEL_DATA_DIR)
        with open(_PIXEL_DATA_FILE, 'ab') as f:
            frame.pixel_array.tofile(f)
    _write_vti_file(_VTI_CT_ZIP_FILE, ctinfo)
    return ctinfo


def _write_dvh_file(files, rois):
    with open (_DVH_FILE_NAME, 'w') as f:
        json.dump(_compute_dvh(rois.keys(), files.rtstruct, files.rtdose), f)


def _write_rtdose_file(files):
    rtdose = pydicom.dcmread(files.rtdose)
    doseinfo = _extract_dcm_info(files, None, rtdose)
    doseinfo.DoseMax = int(rtdose.pixel_array.max())
    doseinfo.DoseGridScaling = rtdose.DoseGridScaling
    pkdlog('max dose: {}, scaler: {}', doseinfo.DoseMax, doseinfo.DoseGridScaling)
    pkdlog('max dose (scaled): {}', rtdose.pixel_array.max() * rtdose.DoseGridScaling)
    #doseinfo.ImagePositionPatient[2] += (doseinfo.Count - 1) * doseinfo.SliceThickness
    #pkdp('dose pixel array size: {}, len(rtdose.pixel_array))
    pkio.mkdir_parent(_PIXEL_DATA_DIR)
    pkdlog(rtdose.pixel_array.shape)

    # order frame in direction used by ct (assumes HFS)
    with open (_PIXEL_DATA_FILE, 'ab') as f:
        #for di in reversed(range(rtdose.pixel_array.shape[0])):
        for di in range(rtdose.pixel_array.shape[0]):
            for yi in range(rtdose.pixel_array.shape[1]):
                rtdose.pixel_array[di][yi].tofile(f)
    _write_vti_file(_VTI_RTDOSE_ZIP_FILE, doseinfo)
    return doseinfo


def _write_rtstruct_file(files):
    rtstruct = pydicom.dcmread(files.rtstruct)
    rois = {}
    for roi in rtstruct.StructureSetROISequence:
        rois[roi.ROINumber] = {
            'name': roi.ROIName,
            'contour': {},
        }
    for roi_contour in rtstruct.ROIContourSequence:
        if not hasattr(roi_contour, 'ContourSequence'):
            continue
        roi = rois[roi_contour.ReferencedROINumber]
        roi['color'] = _float_list(roi_contour.ROIDisplayColor),
        for contour in roi_contour.ContourSequence:
            if contour.ContourGeometricType != 'CLOSED_PLANAR':
                continue
            #TODO(pjm): this is tied to irad.js zFrame formatting
            ct_z = '{:.1f}'.format(float(contour.ContourData[2]))
            if ct_z not in roi['contour']:
                roi['contour'][ct_z] = []
            data = _float_list(contour.ContourData)
            del data[2::3]
            roi['contour'][ct_z].append(data)
    with open (_ROI_FILE_NAME, 'w') as f:
        json.dump({
            'regionOfInterest': rois,
        }, f)
    return rois

def _write_vti_file(filename, info):
    vti = copy.deepcopy(_VTI_TEMPLATE)
    vti.spacing = [
        info.PixelSpacing[0],
        info.PixelSpacing[1],
        info.SliceThickness,
    ]
    vti.extent = [
        0, info.Columns - 1,
        0, info.Rows - 1,
        0, info.Count - 1,
    ]
    vti.metadata = PKDict(
        name='ct.vti' if 'PatientPosition' in info else 'dose.vti',
    )
    for f in ('RescaleSlope', 'RescaleIntercept', 'DoseMax', 'DoseGridScaling'):
        if f in info:
            vti.metadata[f] = info[f]
    vti.origin = info.ImagePositionPatient
    vti.pointData.arrays[0].data.size = info.Rows * info.Columns * info.Count
    vti.pointData.arrays[0].data.dataType = 'Int{}Array'.format(info.BitsAllocated)
    pkio.unchecked_remove(filename)
    with ZipFile(filename, 'w') as vti_zip:
        vti_zip.writestr('index.json', json.dumps(vti))
        vti_zip.write(_PIXEL_DATA_FILE)
    #pkdp('vti json: {}', vti)
    pkio.unchecked_remove(_PIXEL_DATA_DIR)
