# -*- coding: utf-8 -*-
u"""RS4PI execution template.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from scipy.ndimage.interpolation import zoom
from sirepo import simulation_db
from sirepo.template import template_common
import ctypes
import datetime
import glob
import h5py
import numpy as np
import os
import os.path
import py.path
import re
import sirepo.sim_data
import struct
import time
import werkzeug
import zipfile
try:
    # pydicom is changing to pydicom in 1.0
    import pydicom as dicom
except ImportError:
    import dicom

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

RTSTRUCT_EXPORT_FILENAME = 'rtstruct.dcm'
RTDOSE_EXPORT_FILENAME = 'dose.dcm'
PRESCRIPTION_FILENAME = 'prescription.json'
WANT_BROWSER_FRAME_CACHE = True
DOSE_CALC_SH = 'dose_calc.sh'
DOSE_CALC_OUTPUT = 'Full_Dose.h5'
_DICOM_CLASS = {
    'CT_IMAGE': '1.2.840.10008.5.1.4.1.1.2',
    'RT_DOSE': '1.2.840.10008.5.1.4.1.1.481.2',
    'RT_STRUCT': '1.2.840.10008.5.1.4.1.1.481.3',
    'DETATCHED_STUDY': '1.2.840.10008.3.1.2.3.1',
}
_DICOM_DIR = 'dicom'
_DICOM_MAX_VALUE = 1000
_DICOM_MIN_VALUE = -1000
_DOSE_DICOM_FILE = RTDOSE_EXPORT_FILENAME
_DOSE_FILE = 'dose3d.dat'
_EXPECTED_ORIENTATION = np.array([1, 0, 0, 0, 1, 0])
# using np.float32 for pixel storage
_FLOAT_SIZE = 4
_PIXEL_FILE = 'pixels3d.dat'
_RADIASOFT_ID = 'RadiaSoft'
_ROI_FILE_NAME = 'rs4pi-roi-data.json'
_TMP_INPUT_FILE_FIELD = 'tmpDicomFilePath'
_TMP_ZIP_DIR = 'tmp-dicom-files'
_ZIP_FILE_NAME = 'input.zip'


def background_percent_complete(report, run_dir, is_running):
    data_path = run_dir.join(template_common.INPUT_BASE_NAME)
    if not os.path.exists(str(simulation_db.json_filename(data_path))):
        return {
            'percentComplete': 0,
            'frameCount': 0,
        }
    return {
        'percentComplete': 100,
        # real frame count depends on the series selected
        'frameCount': 1,
        'errors': '',
    }


def copy_related_files(data, source_path, target_path):
    # pixels3d.dat, rs4pi-roi-data.json, dicom/*.json
    for filename in (_PIXEL_FILE, _ROI_FILE_NAME, _DOSE_FILE, RTDOSE_EXPORT_FILENAME):
        f = py.path.local(source_path).join(filename)
        if f.exists():
            f.copy(py.path.local(target_path).join(filename))
    dicom_dir = py.path.local(target_path).join(_DICOM_DIR)
    pkio.mkdir_parent(str(dicom_dir))
    for f in glob.glob(str(py.path.local(source_path).join(_DICOM_DIR, '*'))):
        py.path.local(f).copy(dicom_dir)


def generate_rtdose_file(data, run_dir):
    dose_hd5 = str(run_dir.join(DOSE_CALC_OUTPUT))
    dicom_series = data['models']['dicomSeries']
    frame = pkcollections.Dict(
        StudyInstanceUID=dicom_series['studyInstanceUID'],
        shape=np.array([
            dicom_series['planes']['t']['frameCount'],
            dicom_series['planes']['c']['frameCount'],
            dicom_series['planes']['s']['frameCount'],
        ]),
        spacing=np.array(_float_list(dicom_series['pixelSpacing'])),
    )
    with h5py.File(dose_hd5, 'r') as f:
        start = f['/dose'].attrs['dicom_start_cm'] * 10
        #TODO(pjm): assumes the size closely matches original dicom when scaled
        # size = f['/dose'].attrs['voxel_size_cm'] * 10
        ds = _create_dicom_dataset(frame['StudyInstanceUID'], 'RT_DOSE', 'RTDOSE')
        pixels = np.array(f['/dose'])
        shape = pixels.shape
        # reshape the pixels in place: z is actually first
        pixels.shape = (shape[2], shape[0], shape[1])
        shape = pixels.shape
        pixels = zoom(pixels, zoom=frame['shape']/shape, order=1)
        shape = pixels.shape

        ds.ImagePositionPatient = _string_list(start)
        ds.PixelSpacing = _string_list([frame['spacing'][0], frame['spacing'][1]])
        ds.Rows = shape[1]
        ds.Columns = shape[2]
        ds.NumberOfFrames = shape[0]
        ds.DoseUnits = 'GY'

        pixels = pixels.flatten()
        v = pixels.max()
        max_int = np.iinfo(np.uint32).max - 1
        scale = v / max_int
        ds.DoseGridScaling = scale
        pixels /= scale
        ds.BitsAllocated = 32
        ds.BitsStored = 32
        ds.HighBit = 31
        ds.PixelRepresentation = 0
        ds.SamplesPerPixel = 1
        ds.PixelData = pixels.astype(np.uint32)
        ds.file_meta.TransferSyntaxUID = '1.2.840.10008.1.2'

        # for dicompyler
        ds.PhotometricInterpretation = 'MONOCHROME2'
        ds.DoseType = 'PHYSICAL'
        ds.DoseSummationType = 'PLAN'
        ds.ImageOrientationPatient = _string_list(_EXPECTED_ORIENTATION)
        ds.GridFrameOffsetVector = np.linspace(0.0, frame['spacing'][2] * (shape[0] - 1), shape[0]).tolist()
        ds.save_as(_parent_file(run_dir, _DOSE_DICOM_FILE))
        return _summarize_rt_dose(None, ds, run_dir=run_dir)


def get_application_data(data):
    if data['method'] == 'roi_points':
        return _read_roi_file(data['simulationId'])
    elif data['method'] == 'update_roi_points':
        return _update_roi_file(data['simulationId'], data['editedContours'])
    else:
        raise RuntimeError('{}: unknown application data method'.format(data['method']))


def get_data_file(run_dir, model, frame, **kwargs):
    if model == 'dicomAnimation4':
        with open(_parent_file(run_dir, _DOSE_DICOM_FILE)) as f:
            return RTDOSE_EXPORT_FILENAME, f.read(), 'application/octet-stream'
    with simulation_db.tmp_dir() as tmp_dir:
        filename, _ = _generate_rtstruct_file(_parent_dir(run_dir), tmp_dir)
        with open (filename, 'rb') as f:
            dicom_data = f.read()
        return RTSTRUCT_EXPORT_FILENAME, dicom_data, 'application/octet-stream'


def get_simulation_frame(run_dir, data, model_data):
    frame_index = int(data['frameIndex'])
    args = data['animationArgs'].split('_')
    if data['modelName'].startswith('dicomAnimation'):
        plane = args[0]
        res = simulation_db.read_json(_dicom_path(model_data['models']['simulation'], plane, frame_index))
        res['pixel_array'] = _read_pixel_plane(plane, frame_index, model_data)
        return res
    if data['modelName'] == 'dicomDose':
        return {
            'dose_array': _read_dose_frame(frame_index, model_data)
        }
    raise RuntimeError('{}: unknown simulation frame model'.format(data['modelName']))


def import_file(request, tmp_dir=None):
    f = request.files['file']
    filename = werkzeug.secure_filename(f.filename)
    if not pkio.has_file_extension(str(filename), 'zip'):
        raise RuntimeError('unsupported import filename: {}'.format(filename))
    filepath = str(tmp_dir.join(_ZIP_FILE_NAME))
    f.save(filepath)
    data = simulation_db.default_data(SIM_TYPE)
    data['models']['simulation']['name'] = filename
    data['models']['simulation'][_TMP_INPUT_FILE_FIELD] = filepath
    # more processing occurs below in prepare_for_client() after simulation dir is prepared
    return data


def prepare_for_client(data):
    if _TMP_INPUT_FILE_FIELD in data['models']['simulation']:
        _move_import_file(data)
    return data


def remove_last_frame(run_dir):
    pass


def write_parameters(data, run_dir, is_parallel):
    rtfile = py.path.local(_parent_file(run_dir, RTSTRUCT_EXPORT_FILENAME))
    if data['report'] == 'dvhReport' and rtfile.exists():
        return
    if data['report'] in ('doseCalculation', 'dvhReport'):
        _, roi_models = _generate_rtstruct_file(_parent_dir(run_dir), _parent_dir(run_dir))
        if data['report'] == 'doseCalculation':
            dose_calc = data.models.doseCalculation
            roi_data = roi_models['regionsOfInterest']
            ptv_name = ''
            oar_names = []
            for roi_number in roi_data:
                if roi_number == dose_calc.selectedPTV:
                    ptv_name = roi_data[roi_number]['name']
                elif roi_number in dose_calc.selectedOARs:
                    oar_names.append(roi_data[roi_number]['name'])
            prescription = run_dir.join(PRESCRIPTION_FILENAME)
            simulation_db.write_json(
                prescription,
                {
                    'ptv': ptv_name,
                    'oar': oar_names,
                })
            pkjinja.render_file(
                _SIM_DATA.resource_path(DOSE_CALC_SH).new(ext='.jinja'),
                {
                    'prescription': prescription,
                    'beamlist': run_dir.join(_SIM_DATA.RS4PI_BEAMLIST_FILENAME),
                    'dicom_zip': _sim_file(data['simulationId'], _ZIP_FILE_NAME),
                },
                output=run_dir.join(DOSE_CALC_SH),
                strict_undefined=True,
            )


def _calculate_domain(frame):
    position = _float_list(frame['ImagePositionPatient'])
    spacing = frame['PixelSpacing']
    shape = frame['shape']
    return [
        [
            position[0] - spacing[0] / 2,
            position[1] - spacing[1] / 2,
            position[2],
        ],
        [
            position[0] + spacing[0] * shape[1] - spacing[0] / 2,
            position[1] + spacing[1] * shape[0] - spacing[1] / 2,
            position[2],
        ],
    ]


def _compute_histogram(simulation, frames):
    pixels = []
    for frame in frames:
        pixels.append(frame['pixels'])
    histogram = _histogram_from_pixels(pixels)
    filename = _roi_file(simulation['simulationId'])
    if os.path.exists(filename):
        roi_data = _read_roi_file(simulation['simulationId'])
    else:
        roi_data = {
            'models': {
                'regionsOfInterest': {},
            },
        }
    roi_data['models']['dicomHistogram'] = histogram
    roi_data['models']['dicomFrames'] = _summarize_frames(frames)
    simulation_db.write_json(filename, roi_data)


def _create_dicom_dataset(study_uid, dicom_class, modality):
    sop_uid = dicom.uid.generate_uid()

    file_meta = dicom.dataset.Dataset()
    file_meta.MediaStorageSOPClassUID = _DICOM_CLASS[dicom_class]
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    #TODO(pjm): need proper implementation uid
    file_meta.ImplementationClassUID = "1.2.3.4"
    file_meta.ImplementationVersionName = 'dcm4che-2.0'

    ds = dicom.dataset.FileDataset('', {}, file_meta=file_meta, preamble=b"\0" * 128)
    now = datetime.datetime.now()
    ds.InstanceCreationDate = now.strftime('%Y%m%d')
    ds.InstanceCreationTime = now.strftime('%H%M%S.%f')
    ds.SOPClassUID = _DICOM_CLASS[dicom_class]
    ds.SOPInstanceUID = sop_uid
    ds.StudyDate = ''
    ds.StudyTime = ''
    ds.AccessionNumber = ''
    ds.Modality = modality
    ds.Manufacturer = _RADIASOFT_ID
    ds.ReferringPhysiciansName = ''
    ds.ManufacturersModelName = _RADIASOFT_ID
    ds.PatientsName = _RADIASOFT_ID
    ds.PatientID = _RADIASOFT_ID
    ds.PatientsBirthDate = ''
    ds.PatientsSex = ''
    ds.StudyInstanceUID = study_uid
    ds.SeriesInstanceUID = dicom.uid.generate_uid()
    ds.StudyID = ''
    ds.SeriesNumber = ''
    return ds


def _dicom_path(simulation, plane, idx):
    return str(py.path.local(_sim_file(simulation['simulationId'], _DICOM_DIR)).join(_frame_file_name(plane, idx)))


def _dose_dicom_filename(simulation):
    return _sim_file(simulation['simulationId'], _DOSE_DICOM_FILE)


def _dose_filename(simulation):
    return _sim_file(simulation['simulationId'], _DOSE_FILE)


def _extract_series_frames(simulation, dicom_dir):
    #TODO(pjm): give user a choice between multiple study/series if present
    selected_series = None
    frames = {}
    dicom_dose = None
    rt_struct_path = None
    res = {
        'description': '',
    }
    for path in pkio.walk_tree(dicom_dir):
        if pkio.has_file_extension(str(path), 'dcm'):
            plan = dicom.read_file(str(path))
            if plan.SOPClassUID == _DICOM_CLASS['RT_STRUCT']:
                rt_struct_path = str(path)
            elif plan.SOPClassUID == _DICOM_CLASS['RT_DOSE']:
                res['dicom_dose'] = _summarize_rt_dose(simulation, plan)
                plan.save_as(_dose_dicom_filename(simulation))
            if plan.SOPClassUID != _DICOM_CLASS['CT_IMAGE']:
                continue
            orientation = _float_list(plan.ImageOrientationPatient)
            if not (_EXPECTED_ORIENTATION == orientation).all():
                continue
            if not selected_series:
                selected_series = plan.SeriesInstanceUID
                res['StudyInstanceUID'] = plan.StudyInstanceUID
                res['PixelSpacing'] = plan.PixelSpacing
                if hasattr(plan, 'SeriesDescription'):
                    res['description'] = plan.SeriesDescription
            if selected_series != plan.SeriesInstanceUID:
                continue
            info = {
                'pixels': np.float32(plan.pixel_array),
                'shape': plan.pixel_array.shape,
                'ImagePositionPatient': _string_list(plan.ImagePositionPatient),
                'ImageOrientationPatient': _float_list(plan.ImageOrientationPatient),
                'PixelSpacing': _float_list(plan.PixelSpacing),
            }
            for f in ('FrameOfReferenceUID', 'StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID'):
                info[f] = getattr(plan, f)
            z = _frame_id(info['ImagePositionPatient'][2])
            info['frameId'] = z
            if z in frames:
                raise RuntimeError('duplicate frame with z coord: {}'.format(z))
            _scale_pixel_data(plan, info['pixels'])
            frames[z] = info
    if not selected_series:
        raise RuntimeError('No series found with {} orientation'.format(_EXPECTED_ORIENTATION))
    if rt_struct_path:
        res['regionsOfInterest'] = _summarize_rt_structure(simulation, dicom.read_file(rt_struct_path), frames.keys())
    sorted_frames = []
    res['frames'] = sorted_frames
    for z in sorted(_float_list(frames.keys())):
        sorted_frames.append(frames[_frame_id(z)])
    return res


def _frame_id(v):
    # normalize on float's string format, ex 2 --> '2.0'
    return str(float(v))


def _frame_info(count):
    return {
        'frameIndex': int(count / 2),
        'frameCount': count,
    }


def _float_list(ar):
    return map(lambda x: float(x), ar)


def _frame_file_name(plane, index):
    return plane + str(index).zfill(5)


def _generate_dicom_reference_frame_info(plan, frame_data):
    ref_ds = dicom.dataset.Dataset()
    ref_ds.FrameOfReferenceUID = frame_data['FrameOfReferenceUID']
    study_ds = dicom.dataset.Dataset()
    study_ds.ReferencedSOPClassUID = _DICOM_CLASS['DETATCHED_STUDY']
    study_ds.ReferencedSOPInstanceUID = frame_data['StudyInstanceUID']
    series_ds = dicom.dataset.Dataset()
    series_ds.SeriesInstanceUID = frame_data['SeriesInstanceUID']
    series_ds.ContourImageSequence = []
    for uid in frame_data['SOPInstanceUID']:
        instance_ds = dicom.dataset.Dataset()
        instance_ds.ReferencedSOPClassUID = _DICOM_CLASS['CT_IMAGE']
        instance_ds.ReferencedSOPInstanceUID = uid
        series_ds.ContourImageSequence.append(instance_ds)
    study_ds.RTReferencedSeriesSequence = [series_ds]
    ref_ds.RTReferencedStudySequence = [study_ds]
    plan.ReferencedFrameOfReferenceSequence = [ref_ds]


def _generate_dicom_roi_info(plan, frame_data, roi_data):
    plan.StructureSetROISequence = []
    plan.ROIContourSequence = []

    for roi_number in sorted(roi_data.keys()):
        roi = roi_data[roi_number]
        roi_ds = dicom.dataset.Dataset()
        roi_ds.ROINumber = roi_number
        roi_ds.ROIName = roi['name']
        roi_ds.ReferencedFrameOfReferenceUID = frame_data['FrameOfReferenceUID']
        plan.StructureSetROISequence.append(roi_ds)

        contour_ds = dicom.dataset.Dataset()
        contour_ds.ReferencedROINumber = roi_number
        contour_ds.ROIDisplayColor = _string_list(roi['color'])
        contour_ds.ContourSequence = []
        image_num = 1

        for frame_id in sorted(_float_list(roi['contour'].keys())):
            for points in roi['contour'][str(frame_id)]:
                image_ds = dicom.dataset.Dataset()
                image_ds.ContourGeometricType = 'CLOSED_PLANAR'
                image_ds.ContourNumber = str(image_num)
                image_num += 1
                image_ds.ContourData = []
                for i in range(0, len(points), 2):
                    image_ds.ContourData.append(str(points[i]))
                    image_ds.ContourData.append(str(points[i + 1]))
                    image_ds.ContourData.append(str(frame_id))
                image_ds.NumberOfContourPoints = str(int(len(image_ds.ContourData) / 3))
                contour_ds.ContourSequence.append(image_ds)
        plan.ROIContourSequence.append(contour_ds)


def _generate_rtstruct_file(sim_dir, target_dir):
    models = simulation_db.read_json(sim_dir.join(_ROI_FILE_NAME))['models']
    frame_data = models['dicomFrames']
    roi_data = models['regionsOfInterest']
    plan = _create_dicom_dataset(frame_data['StudyInstanceUID'], 'RT_STRUCT', 'RTSTRUCT')
    plan.StructureSetLabel = '{} Exported'.format(_RADIASOFT_ID)
    plan.StructureSetDate = plan.InstanceCreationDate
    plan.StructureSetTime = plan.InstanceCreationTime
    _generate_dicom_reference_frame_info(plan, frame_data)
    _generate_dicom_roi_info(plan, frame_data, roi_data)
    filename = str(target_dir.join(RTSTRUCT_EXPORT_FILENAME))
    plan.save_as(filename)
    return filename, models


def _histogram_from_pixels(pixels):
    m = 50
    extent = [np.array(pixels).min(), np.array(pixels).max()]
    if extent[0] < _DICOM_MIN_VALUE:
        extent[0] = _DICOM_MIN_VALUE
    if extent[1] > _DICOM_MAX_VALUE:
        extent[1] = _DICOM_MAX_VALUE
    span = extent[1] - extent[0]
    step = np.power(10, np.floor(np.log(span / m) / np.log(10)))
    err = float(m) / span * step
    if err <= .15:
        step *= 10
    elif err <= .35:
        step *= 5
    elif err <= .75:
        step *= 2
    e = [
        np.ceil(extent[0] / step) * step,
        np.floor(extent[1] / step) * step + step * .5,
        step,
    ]
    bins = int(np.ceil((e[1] - e[0]) / e[2]))
    hist, edges = np.histogram(pixels, bins=bins, range=[e[0], e[0] + (bins - 1) * step])
    if hist[0] == hist.max():
        v = hist[0]
        hist[0] = 0
        if v > hist.max() * 2:
            hist[0] = hist.max() * 2
        else:
            hist[0] = v
    return {
        'histogram': hist.tolist(),
        'extent': [edges[0].item(), edges[-1].item(), bins],
    }


def _move_import_file(data):
    sim = data['models']['simulation']
    path = sim[_TMP_INPUT_FILE_FIELD]
    del sim[_TMP_INPUT_FILE_FIELD]
    if os.path.exists(path):
        zip_path = _sim_file(sim['simulationId'], _ZIP_FILE_NAME)
        os.rename(path, zip_path)
        pkio.unchecked_remove(os.path.dirname(path))
        tmp_dir = _sim_file(sim['simulationId'], _TMP_ZIP_DIR)
        zipfile.ZipFile(zip_path).extractall(tmp_dir)
        _summarize_dicom_files(data, tmp_dir)
        pkio.unchecked_remove(tmp_dir)
        simulation_db.save_simulation_json(data)


def _parent_dir(child_dir):
    return child_dir.join('..')


def _parent_file(child_dir, filename):
    return str(_parent_dir(child_dir).join(filename))


def _pixel_filename(simulation):
    return _sim_file(simulation['simulationId'], _PIXEL_FILE)


def _read_dose_frame(idx, data):
    res = []
    if 'dicomDose' not in data['models']:
        return res
    dicom_dose = data['models']['dicomDose']
    if idx >= dicom_dose['frameCount']:
        return res
    shape = dicom_dose['shape']
    with open (_dose_filename(data['models']['simulation']), 'rb') as f:
        f.seek(idx * _FLOAT_SIZE * shape[0] * shape[1], 1)
        for r in range(shape[0]):
            row = []
            res.append(row)
            for c in range(shape[1]):
                row.append(struct.unpack('f', f.read(_FLOAT_SIZE))[0])
    return res


def _read_pixel_plane(plane, idx, data):
    plane_info = data['models']['dicomSeries']['planes']
    size = [plane_info['c']['frameCount'], plane_info['s']['frameCount'], plane_info['t']['frameCount']]
    frame = []
    # pixels = np.array(all_frame_pixels)[:, idx]
    # pixels = np.array(all_frame_pixels)[:, :, idx]
    with open (_pixel_filename(data['models']['simulation']), 'rb') as f:
        if plane == 't':
            if idx > 0:
                f.seek(idx * _FLOAT_SIZE * size[0] * size[1], 1)
            for r in range(size[1]):
                row = []
                frame.append(row)
                for v in range(size[0]):
                    row.append(struct.unpack('f', f.read(_FLOAT_SIZE))[0])
        elif plane == 'c':
            if idx > 0:
                f.seek(idx * _FLOAT_SIZE * size[0], 1)
            for r in range(size[2]):
                row = []
                frame.append(row)
                for v in range(size[0]):
                    row.append(struct.unpack('f', f.read(_FLOAT_SIZE))[0])
                f.seek(_FLOAT_SIZE * (size[0] - 1) * size[1], 1)
            frame = np.flipud(frame).tolist()
        elif plane == 's':
            if idx > 0:
                f.seek(idx * _FLOAT_SIZE, 1)
            for r in range(size[2]):
                row = []
                frame.append(row)
                for v in range(size[1]):
                    row.append(struct.unpack('f', f.read(_FLOAT_SIZE))[0])
                    f.seek(_FLOAT_SIZE * (size[0] - 1), 1)
            frame = np.flipud(frame).tolist()
        else:
            raise RuntimeError('plane not supported: {}'.format(plane))
    return frame


def _read_roi_file(sim_id):
    return simulation_db.read_json(_roi_file(sim_id))


def _roi_file(sim_id):
    return _sim_file(sim_id, _ROI_FILE_NAME)


def _scale_pixel_data(plan, pixels):
    scale_required = False
    slope = 1
    offset = 0
    if 'RescaleSlope' in plan and plan.RescaleSlope != slope:
        slope = plan.RescaleSlope
        scale_required = True
    if 'RescaleIntercept' in plan and plan.RescaleIntercept != offset:
        offset = plan.RescaleIntercept
        scale_required = True
    if scale_required:
        pixels *= float(slope)
        pixels += float(offset)


def _sim_file(sim_id, filename):
    return str(simulation_db.simulation_dir(SIM_TYPE, sim_id).join(filename))


def _string_list(ar):
    return map(lambda x: str(x), ar)


def _summarize_dicom_files(data, dicom_dir):
    simulation = data['models']['simulation']
    info = _extract_series_frames(simulation, dicom_dir)
    frames = info['frames']
    info['pixelSpacing'] = _summarize_dicom_series(simulation, frames)
    with open (_pixel_filename(simulation), 'wb') as f:
        for frame in frames:
            frame['pixels'].tofile(f)
    data['models']['dicomSeries'] = {
        'description': info['description'],
        'pixelSpacing': info['pixelSpacing'],
        'studyInstanceUID': info['StudyInstanceUID'],
        'planes': {
            't': _frame_info(len(frames)),
            's': _frame_info(len(frames[0]['pixels'])),
            'c': _frame_info(len(frames[0]['pixels'][0])),
        }
    }
    time_stamp = int(time.time())
    for m in ('dicomAnimation', 'dicomAnimation2', 'dicomAnimation3', 'dicomAnimation4'):
        data['models'][m]['startTime'] = time_stamp
    if 'regionsOfInterest' in info:
        dose_calc = data['models']['doseCalculation']
        selectedPTV = None
        dose_calc['selectedOARs'] = []
        for roi_number in sorted(info['regionsOfInterest']):
            roi = info['regionsOfInterest'][roi_number]
            if not selectedPTV or re.search(r'\bptv\b', roi['name'], re.IGNORECASE):
                selectedPTV = str(roi_number)
            dose_calc['selectedOARs'].append(str(roi_number))
        if selectedPTV:
            dose_calc['selectedPTV'] = selectedPTV
            data['models']['dvhReport']['roiNumbers'] = [selectedPTV]
    if 'dicom_dose' in info:
        data['models']['dicomDose'] = info['dicom_dose']
    _compute_histogram(simulation, frames)


def _summarize_dicom_series(simulation, frames):
    idx = 0
    z_space = abs(float(frames[0]['ImagePositionPatient'][2]) - float(frames[1]['ImagePositionPatient'][2]))
    os.mkdir(_sim_file(simulation['simulationId'], _DICOM_DIR))
    for frame in frames:
        res = {
            'shape': frame['shape'],
            'ImagePositionPatient': frame['ImagePositionPatient'],
            'PixelSpacing': frame['PixelSpacing'],
            'domain': _calculate_domain(frame),
            'frameId': frame['frameId'],
        }
        filename = _dicom_path(simulation, 't', idx)
        simulation_db.write_json(filename, res)
        idx += 1

    frame0 = frames[0]
    shape = [
        len(frames),
        len(frame0['pixels'][0]),
    ]
    res = {
        'shape': shape,
        'ImagePositionPatient': [
            frame0['ImagePositionPatient'][0],
            frame0['ImagePositionPatient'][2],
            frame0['ImagePositionPatient'][1],
        ],
        'PixelSpacing': [
            frame0['PixelSpacing'][0],
            z_space,
        ],
    }
    for idx in range(len(frame0['pixels'][0])):
        res['ImagePositionPatient'][2] = str(float(frame0['ImagePositionPatient'][1]) + idx * float(frame0['PixelSpacing'][0]))
        res['domain'] = _calculate_domain(res)
        filename = _dicom_path(simulation, 'c', idx)
        simulation_db.write_json(filename, res)

    shape = [
        len(frames),
        len(frame0['pixels'][1]),
    ]
    res = {
        'shape': shape,
        'ImagePositionPatient': [
            frame0['ImagePositionPatient'][1],
            frame0['ImagePositionPatient'][2],
            frame0['ImagePositionPatient'][0],
        ],
        'PixelSpacing': [
            frame0['PixelSpacing'][0],
            z_space,
        ],
    }
    for idx in range(len(frame0['pixels'][0])):
        res['ImagePositionPatient'][2] = str(float(frame0['ImagePositionPatient'][0]) + idx * float(frame0['PixelSpacing'][1]))
        res['domain'] = _calculate_domain(res)
        filename = _dicom_path(simulation, 's', idx)
        simulation_db.write_json(filename, res)
    spacing = frame0['PixelSpacing']
    return _string_list([spacing[0], spacing[1], z_space])


def _summarize_frames(frames):
    res = {}
    frame0 = frames[0]
    for n in ('FrameOfReferenceUID', 'StudyInstanceUID', 'SeriesInstanceUID'):
        res[n] = frame0[n]
    res['SOPInstanceUID'] = []
    for frame in frames:
        res['SOPInstanceUID'].append(frame['SOPInstanceUID'])
    return res


def _summarize_rt_dose(simulation, plan, run_dir=None):
    pixels = np.float32(plan.pixel_array)
    if plan.DoseGridScaling:
        pixels *= float(plan.DoseGridScaling)
    fn = _parent_file(run_dir, _DOSE_FILE) if run_dir else _dose_filename(simulation)
    with open (fn, 'wb') as f:
        pixels.tofile(f)
    #TODO(pjm): assuming frame start matches dicom frame start
    res = {
        'frameCount': int(plan.NumberOfFrames),
        'units': plan.DoseUnits,
        'min': float(np.min(pixels)),
        'max': float(np.max(pixels)),
        'shape': [plan.Rows, plan.Columns],
        'ImagePositionPatient': _string_list(plan.ImagePositionPatient),
        'PixelSpacing': _float_list(plan.PixelSpacing),
        'startTime': int(time.time()),
    }
    res['domain'] = _calculate_domain(res)
    return res


def _summarize_rt_structure(simulation, plan, frame_ids):
    rois = {}
    for roi in plan.StructureSetROISequence:
        rois[roi.ROINumber] = {
            'name': roi.ROIName,
        }
    res = {}
    for roi_contour in plan.ROIContourSequence:
        roi = rois[roi_contour.ReferencedROINumber]
        if 'contour' in roi:
            raise RuntimeError('duplicate contour sequence for roi')
        if not hasattr(roi_contour, 'ContourSequence'):
            continue
        roi['contour'] = {}
        for contour in roi_contour.ContourSequence:
            if contour.ContourGeometricType != 'CLOSED_PLANAR':
                continue
            if len(contour.ContourData):
                # the z index is the key
                ct_id = _frame_id(contour.ContourData[2])
                if ct_id not in frame_ids:
                    raise RuntimeError('contour z not in frames: {}', ct_id)
                contour_data = _float_list(contour.ContourData)
                if len(contour_data) > 3 and ct_id != _frame_id(contour_data[5]):
                    raise RuntimeError('expected contour data z to be equal')
                del contour_data[2::3]
                if ct_id not in roi['contour']:
                    roi['contour'][ct_id] = []
                roi['contour'][ct_id].append(contour_data)
        if roi['contour']:
            roi['color'] = _string_list(roi_contour.ROIDisplayColor)
            res[roi_contour.ReferencedROINumber] = roi
    simulation_db.write_json(_roi_file(simulation['simulationId']), {
        'models': {
            'regionsOfInterest': res,
        },
    })
    return res


def _update_roi_file(sim_id, contours):
    data = _read_roi_file(sim_id)
    rois = data['models']['regionsOfInterest']
    for roi_number in contours:
        if roi_number not in rois:
            rois[roi_number] = contours[roi_number]
        else:
            for frame_id in contours[roi_number]:
                points = contours[roi_number][frame_id]
                rois[roi_number]['contour'][frame_id] = points
    #TODO(pjm): file locking or atomic update
    simulation_db.write_json(_roi_file(sim_id), data)
    return {}
