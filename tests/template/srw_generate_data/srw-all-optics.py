#!/usr/bin/env python
import os
try:
    __IPYTHON__
    import sys
    del sys.argv[1:]
except:
    pass


import srwl_bl
import srwlib
import srwlpy
import srwl_uti_smp


def set_optics(v=None):
    el = []
    pp = []
    names = ['Lens', 'Lens_CRL', 'CRL', 'CRL_Zone_Plate', 'Zone_Plate', 'Zone_Plate_Fiber', 'Fiber', 'Fiber_Aperture', 'Aperture', 'Aperture_Obstacle', 'Obstacle', 'Obstacle_Mask', 'Mask', 'Mask_Sample', 'Sample', 'Sample_Planar', 'Planar', 'Planar_Circular_Cylinder', 'Circular_Cylinder', 'Circular_Cylinder_Circular_Cylinder2', 'Circular_Cylinder2', 'Circular_Cylinder2_Elliptical_Cylinder', 'Elliptical_Cylinder', 'Elliptical_Cylinder_Elliptical_Cylinder2', 'Elliptical_Cylinder2', 'Elliptical_Cylinder2_Toroid', 'Toroid', 'Toroid_Toroid2', 'Toroid2', 'Toroid2_Crystal', 'Crystal', 'Crystal_Crystal2', 'Crystal2', 'Crystal2_Grating', 'Grating', 'Grating_Watchpoint', 'Watchpoint']
    for el_name in names:
        if el_name == 'Lens':
            # Lens: lens 20.0m
            el.append(srwlib.SRWLOptL(
                _Fx=v.op_Lens_Fx,
                _Fy=v.op_Lens_Fy,
                _x=v.op_Lens_x,
                _y=v.op_Lens_y,
            ))
            pp.append(v.op_Lens_pp)
        elif el_name == 'Lens_CRL':
            # Lens_CRL: drift 20.0m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Lens_CRL_L,
            ))
            pp.append(v.op_Lens_CRL_pp)
        elif el_name == 'CRL':
            # CRL: crl 21.0m
            el.append(srwlib.srwl_opt_setup_CRL(
                _foc_plane=v.op_CRL_foc_plane,
                _delta=v.op_CRL_delta,
                _atten_len=v.op_CRL_atten_len,
                _shape=v.op_CRL_shape,
                _apert_h=v.op_CRL_apert_h,
                _apert_v=v.op_CRL_apert_v,
                _r_min=v.op_CRL_r_min,
                _n=v.op_CRL_n,
                _wall_thick=v.op_CRL_wall_thick,
                _xc=v.op_CRL_x,
                _yc=v.op_CRL_y,
            ))
            pp.append(v.op_CRL_pp)
        elif el_name == 'CRL_Zone_Plate':
            # CRL_Zone_Plate: drift 21.0m
            el.append(srwlib.SRWLOptD(
                _L=v.op_CRL_Zone_Plate_L,
            ))
            pp.append(v.op_CRL_Zone_Plate_pp)
        elif el_name == 'Zone_Plate':
            # Zone_Plate: zonePlate 22.0m
            el.append(srwlib.SRWLOptZP(
                _nZones=v.op_Zone_Plate_nZones,
                _rn=v.op_Zone_Plate_rn,
                _thick=v.op_Zone_Plate_thick,
                _delta1=v.op_Zone_Plate_delta1,
                _atLen1=v.op_Zone_Plate_atLen1,
                _delta2=v.op_Zone_Plate_delta2,
                _atLen2=v.op_Zone_Plate_atLen2,
                _x=v.op_Zone_Plate_x,
                _y=v.op_Zone_Plate_y,
            ))
            pp.append(v.op_Zone_Plate_pp)
        elif el_name == 'Zone_Plate_Fiber':
            # Zone_Plate_Fiber: drift 22.0m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Zone_Plate_Fiber_L,
            ))
            pp.append(v.op_Zone_Plate_Fiber_pp)
        elif el_name == 'Fiber':
            # Fiber: fiber 23.0m
            el.append(srwlib.srwl_opt_setup_cyl_fiber(
                _foc_plane=v.op_Fiber_foc_plane,
                _delta_ext=v.op_Fiber_delta_ext,
                _delta_core=v.op_Fiber_delta_core,
                _atten_len_ext=v.op_Fiber_atten_len_ext,
                _atten_len_core=v.op_Fiber_atten_len_core,
                _diam_ext=v.op_Fiber_externalDiameter,
                _diam_core=v.op_Fiber_diam_core,
                _xc=v.op_Fiber_xc,
                _yc=v.op_Fiber_yc,
            ))
            pp.append(v.op_Fiber_pp)
        elif el_name == 'Fiber_Aperture':
            # Fiber_Aperture: drift 23.0m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Fiber_Aperture_L,
            ))
            pp.append(v.op_Fiber_Aperture_pp)
        elif el_name == 'Aperture':
            # Aperture: aperture 24.0m
            el.append(srwlib.SRWLOptA(
                _shape=v.op_Aperture_shape,
                _ap_or_ob='a',
                _Dx=v.op_Aperture_Dx,
                _Dy=v.op_Aperture_Dy,
                _x=v.op_Aperture_x,
                _y=v.op_Aperture_y,
            ))
            pp.append(v.op_Aperture_pp)
        elif el_name == 'Aperture_Obstacle':
            # Aperture_Obstacle: drift 24.0m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Aperture_Obstacle_L,
            ))
            pp.append(v.op_Aperture_Obstacle_pp)
        elif el_name == 'Obstacle':
            # Obstacle: obstacle 25.0m
            el.append(srwlib.SRWLOptA(
                _shape=v.op_Obstacle_shape,
                _ap_or_ob='o',
                _Dx=v.op_Obstacle_Dx,
                _Dy=v.op_Obstacle_Dy,
                _x=v.op_Obstacle_x,
                _y=v.op_Obstacle_y,
            ))
            pp.append(v.op_Obstacle_pp)
        elif el_name == 'Obstacle_Mask':
            # Obstacle_Mask: drift 25.0m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Obstacle_Mask_L,
            ))
            pp.append(v.op_Obstacle_Mask_pp)
        elif el_name == 'Mask':
            # Mask: mask 26.0m
            el.append(srwlib.srwl_opt_setup_mask(
                _delta=v.op_Mask_delta,
                _atten_len=v.op_Mask_atten_len,
                _thick=v.op_Mask_thick,
                _grid_sh=v.op_Mask_grid_sh,
                _grid_dx=v.op_Mask_grid_dx,
                _grid_dy=v.op_Mask_grid_dy,
                _pitch_x=v.op_Mask_pitch_x,
                _pitch_y=v.op_Mask_pitch_y,
                _grid_nx=v.op_Mask_grid_nx,
                _grid_ny=v.op_Mask_grid_ny,
                _mask_Nx=v.op_Mask_mask_Nx,
                _mask_Ny=v.op_Mask_mask_Ny,
                _grid_angle=v.op_Mask_gridTiltAngle,
                _hx=v.op_Mask_hx,
                _hy=v.op_Mask_hy,
                _mask_x0=v.op_Mask_mask_x0,
                _mask_y0=v.op_Mask_mask_y0,
            ))
            pp.append(v.op_Mask_pp)
        elif el_name == 'Mask_Sample':
            # Mask_Sample: drift 26.0m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Mask_Sample_L,
            ))
            pp.append(v.op_Mask_Sample_pp)
        elif el_name == 'Sample':
            # Sample: sample 27.0m
            el.append(srwl_uti_smp.srwl_opt_setup_transm_from_file(
                file_path=v.op_Sample_file_path,
                resolution=v.op_Sample_resolution,
                thickness=v.op_Sample_thick,
                delta=v.op_Sample_delta,
                atten_len=v.op_Sample_atten_len,
                xc=v.op_Sample_horizontalCenterCoordinate,
                yc=v.op_Sample_verticalCenterCoordinate,
                area=None if not v.op_Sample_cropArea else (
                    v.op_Sample_areaXStart,
                    v.op_Sample_areaXEnd,
                    v.op_Sample_areaYStart,
                    v.op_Sample_areaYEnd,
                ),
                extTr=v.op_Sample_extTransm,
                rotate_angle=v.op_Sample_rotateAngle,
                rotate_reshape=bool(int(v.op_Sample_rotateReshape)),
                cutoff_background_noise=v.op_Sample_cutoffBackgroundNoise,
                background_color=v.op_Sample_backgroundColor,
                tile=None if not v.op_Sample_tileImage else (
                    v.op_Sample_tileRows,
                    v.op_Sample_tileColumns,
                ),
                shift_x=v.op_Sample_shiftX,
                shift_y=v.op_Sample_shiftY,
                invert=bool(int(v.op_Sample_invert)),
                is_save_images=True,
                prefix='Sample_sample',
                output_image_format=v.op_Sample_outputImageFormat,
            ))
            pp.append(v.op_Sample_pp)
        elif el_name == 'Sample_Planar':
            # Sample_Planar: drift 27.0m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Sample_Planar_L,
            ))
            pp.append(v.op_Sample_Planar_pp)
        elif el_name == 'Planar':
            # Planar: mirror 28.0m
            mirror_file = v.op_Planar_hfn
            assert os.path.isfile(mirror_file), \
                'Missing input file {}, required by Planar beamline element'.format(mirror_file)
            el.append(srwlib.srwl_opt_setup_surf_height_1d(
                srwlib.srwl_uti_read_data_cols(mirror_file, "\t", 0, 1),
                _dim=v.op_Planar_dim,
                _ang=abs(v.op_Planar_ang),
                _amp_coef=v.op_Planar_amp_coef,
                _size_x=v.op_Planar_size_x,
                _size_y=v.op_Planar_size_y,
            ))
            pp.append(v.op_Planar_pp)
        elif el_name == 'Planar_Circular_Cylinder':
            # Planar_Circular_Cylinder: drift 28.0m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Planar_Circular_Cylinder_L,
            ))
            pp.append(v.op_Planar_Circular_Cylinder_pp)
        elif el_name == 'Circular_Cylinder':
            # Circular_Cylinder: sphericalMirror 29.0m
            el.append(srwlib.SRWLOptMirSph(
                _r=v.op_Circular_Cylinder_r,
                _size_tang=v.op_Circular_Cylinder_size_tang,
                _size_sag=v.op_Circular_Cylinder_size_sag,
                _nvx=v.op_Circular_Cylinder_nvx,
                _nvy=v.op_Circular_Cylinder_nvy,
                _nvz=v.op_Circular_Cylinder_nvz,
                _tvx=v.op_Circular_Cylinder_tvx,
                _tvy=v.op_Circular_Cylinder_tvy,
                _x=v.op_Circular_Cylinder_x,
                _y=v.op_Circular_Cylinder_y,
            ))
            pp.append(v.op_Circular_Cylinder_pp)
            
        elif el_name == 'Circular_Cylinder_Circular_Cylinder2':
            # Circular_Cylinder_Circular_Cylinder2: drift 29.0m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Circular_Cylinder_Circular_Cylinder2_L,
            ))
            pp.append(v.op_Circular_Cylinder_Circular_Cylinder2_pp)
        elif el_name == 'Circular_Cylinder2':
            # Circular_Cylinder2: sphericalMirror 29.5m
            el.append(srwlib.SRWLOptMirSph(
                _r=v.op_Circular_Cylinder2_r,
                _size_tang=v.op_Circular_Cylinder2_size_tang,
                _size_sag=v.op_Circular_Cylinder2_size_sag,
                _nvx=v.op_Circular_Cylinder2_nvx,
                _nvy=v.op_Circular_Cylinder2_nvy,
                _nvz=v.op_Circular_Cylinder2_nvz,
                _tvx=v.op_Circular_Cylinder2_tvx,
                _tvy=v.op_Circular_Cylinder2_tvy,
                _x=v.op_Circular_Cylinder2_x,
                _y=v.op_Circular_Cylinder2_y,
            ))
            pp.append(v.op_Circular_Cylinder2_pp)
            mirror_file = v.op_Circular_Cylinder2_hfn
            assert os.path.isfile(mirror_file), \
                'Missing input file {}, required by Circular_Cylinder2 beamline element'.format(mirror_file)
            el.append(srwlib.srwl_opt_setup_surf_height_1d(
                srwlib.srwl_uti_read_data_cols(mirror_file, "\t", 0, 1),
                _dim=v.op_Circular_Cylinder2_dim,
                _ang=abs(v.op_Circular_Cylinder2_ang),
                _amp_coef=v.op_Circular_Cylinder2_amp_coef,
            ))
            pp.append([0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0])
        elif el_name == 'Circular_Cylinder2_Elliptical_Cylinder':
            # Circular_Cylinder2_Elliptical_Cylinder: drift 29.5m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Circular_Cylinder2_Elliptical_Cylinder_L,
            ))
            pp.append(v.op_Circular_Cylinder2_Elliptical_Cylinder_pp)
        elif el_name == 'Elliptical_Cylinder':
            # Elliptical_Cylinder: ellipsoidMirror 30.0m
            el.append(srwlib.SRWLOptMirEl(
                _p=v.op_Elliptical_Cylinder_p,
                _q=v.op_Elliptical_Cylinder_q,
                _ang_graz=v.op_Elliptical_Cylinder_ang,
                _size_tang=v.op_Elliptical_Cylinder_size_tang,
                _size_sag=v.op_Elliptical_Cylinder_size_sag,
                _nvx=v.op_Elliptical_Cylinder_nvx,
                _nvy=v.op_Elliptical_Cylinder_nvy,
                _nvz=v.op_Elliptical_Cylinder_nvz,
                _tvx=v.op_Elliptical_Cylinder_tvx,
                _tvy=v.op_Elliptical_Cylinder_tvy,
                _x=v.op_Elliptical_Cylinder_x,
                _y=v.op_Elliptical_Cylinder_y,
            ))
            pp.append(v.op_Elliptical_Cylinder_pp)
            
        elif el_name == 'Elliptical_Cylinder_Elliptical_Cylinder2':
            # Elliptical_Cylinder_Elliptical_Cylinder2: drift 30.0m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Elliptical_Cylinder_Elliptical_Cylinder2_L,
            ))
            pp.append(v.op_Elliptical_Cylinder_Elliptical_Cylinder2_pp)
        elif el_name == 'Elliptical_Cylinder2':
            # Elliptical_Cylinder2: ellipsoidMirror 30.5m
            el.append(srwlib.SRWLOptMirEl(
                _p=v.op_Elliptical_Cylinder2_p,
                _q=v.op_Elliptical_Cylinder2_q,
                _ang_graz=v.op_Elliptical_Cylinder2_ang,
                _size_tang=v.op_Elliptical_Cylinder2_size_tang,
                _size_sag=v.op_Elliptical_Cylinder2_size_sag,
                _nvx=v.op_Elliptical_Cylinder2_nvx,
                _nvy=v.op_Elliptical_Cylinder2_nvy,
                _nvz=v.op_Elliptical_Cylinder2_nvz,
                _tvx=v.op_Elliptical_Cylinder2_tvx,
                _tvy=v.op_Elliptical_Cylinder2_tvy,
                _x=v.op_Elliptical_Cylinder2_x,
                _y=v.op_Elliptical_Cylinder2_y,
            ))
            pp.append(v.op_Elliptical_Cylinder2_pp)
            mirror_file = v.op_Elliptical_Cylinder2_hfn
            assert os.path.isfile(mirror_file), \
                'Missing input file {}, required by Elliptical_Cylinder2 beamline element'.format(mirror_file)
            el.append(srwlib.srwl_opt_setup_surf_height_2d(
                srwlib.srwl_uti_read_data_cols(mirror_file, "\t"),
                _dim=v.op_Elliptical_Cylinder2_dim,
                _ang=abs(v.op_Elliptical_Cylinder2_ang),
                _amp_coef=v.op_Elliptical_Cylinder2_amp_coef,
            ))
            pp.append([0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0])
        elif el_name == 'Elliptical_Cylinder2_Toroid':
            # Elliptical_Cylinder2_Toroid: drift 30.5m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Elliptical_Cylinder2_Toroid_L,
            ))
            pp.append(v.op_Elliptical_Cylinder2_Toroid_pp)
        elif el_name == 'Toroid':
            # Toroid: toroidalMirror 31.0m
            el.append(srwlib.SRWLOptMirTor(
                _rt=v.op_Toroid_rt,
                _rs=v.op_Toroid_rs,
                _size_tang=v.op_Toroid_size_tang,
                _size_sag=v.op_Toroid_size_sag,
                _x=v.op_Toroid_horizontalPosition,
                _y=v.op_Toroid_verticalPosition,
                _ap_shape=v.op_Toroid_ap_shape,
                _nvx=v.op_Toroid_nvx,
                _nvy=v.op_Toroid_nvy,
                _nvz=v.op_Toroid_nvz,
                _tvx=v.op_Toroid_tvx,
                _tvy=v.op_Toroid_tvy,
            ))
            pp.append(v.op_Toroid_pp)
            
        elif el_name == 'Toroid_Toroid2':
            # Toroid_Toroid2: drift 31.0m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Toroid_Toroid2_L,
            ))
            pp.append(v.op_Toroid_Toroid2_pp)
        elif el_name == 'Toroid2':
            # Toroid2: toroidalMirror 31.5m
            el.append(srwlib.SRWLOptMirTor(
                _rt=v.op_Toroid2_rt,
                _rs=v.op_Toroid2_rs,
                _size_tang=v.op_Toroid2_size_tang,
                _size_sag=v.op_Toroid2_size_sag,
                _x=v.op_Toroid2_horizontalPosition,
                _y=v.op_Toroid2_verticalPosition,
                _ap_shape=v.op_Toroid2_ap_shape,
                _nvx=v.op_Toroid2_nvx,
                _nvy=v.op_Toroid2_nvy,
                _nvz=v.op_Toroid2_nvz,
                _tvx=v.op_Toroid2_tvx,
                _tvy=v.op_Toroid2_tvy,
            ))
            pp.append(v.op_Toroid2_pp)
            mirror_file = v.op_Toroid2_hfn
            assert os.path.isfile(mirror_file), \
                'Missing input file {}, required by Toroid2 beamline element'.format(mirror_file)
            el.append(srwlib.srwl_opt_setup_surf_height_1d(
                srwlib.srwl_uti_read_data_cols(mirror_file, "\t", 0, 1),
                _dim=v.op_Toroid2_dim,
                _ang=abs(v.op_Toroid2_ang),
                _amp_coef=v.op_Toroid2_amp_coef,
            ))
            pp.append([0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0])
        elif el_name == 'Toroid2_Crystal':
            # Toroid2_Crystal: drift 31.5m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Toroid2_Crystal_L,
            ))
            pp.append(v.op_Toroid2_Crystal_pp)
        elif el_name == 'Crystal':
            # Crystal: crystal 32.0m
            crystal = srwlib.SRWLOptCryst(
                _d_sp=v.op_Crystal_d_sp,
                _psi0r=v.op_Crystal_psi0r,
                _psi0i=v.op_Crystal_psi0i,
                _psi_hr=v.op_Crystal_psiHr,
                _psi_hi=v.op_Crystal_psiHi,
                _psi_hbr=v.op_Crystal_psiHBr,
                _psi_hbi=v.op_Crystal_psiHBi,
                _tc=v.op_Crystal_tc,
                _ang_as=v.op_Crystal_ang_as,
            )
            crystal.set_orient(
                _nvx=v.op_Crystal_nvx,
                _nvy=v.op_Crystal_nvy,
                _nvz=v.op_Crystal_nvz,
                _tvx=v.op_Crystal_tvx,
                _tvy=v.op_Crystal_tvy,
            )
            el.append(crystal)
            pp.append(v.op_Crystal_pp)
            
        elif el_name == 'Crystal_Crystal2':
            # Crystal_Crystal2: drift 32.0m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Crystal_Crystal2_L,
            ))
            pp.append(v.op_Crystal_Crystal2_pp)
        elif el_name == 'Crystal2':
            # Crystal2: crystal 32.5m
            crystal = srwlib.SRWLOptCryst(
                _d_sp=v.op_Crystal2_d_sp,
                _psi0r=v.op_Crystal2_psi0r,
                _psi0i=v.op_Crystal2_psi0i,
                _psi_hr=v.op_Crystal2_psiHr,
                _psi_hi=v.op_Crystal2_psiHi,
                _psi_hbr=v.op_Crystal2_psiHBr,
                _psi_hbi=v.op_Crystal2_psiHBi,
                _tc=v.op_Crystal2_tc,
                _ang_as=v.op_Crystal2_ang_as,
            )
            crystal.set_orient(
                _nvx=v.op_Crystal2_nvx,
                _nvy=v.op_Crystal2_nvy,
                _nvz=v.op_Crystal2_nvz,
                _tvx=v.op_Crystal2_tvx,
                _tvy=v.op_Crystal2_tvy,
            )
            el.append(crystal)
            pp.append(v.op_Crystal2_pp)
            mirror_file = v.op_Crystal2_hfn
            assert os.path.isfile(mirror_file), \
                'Missing input file {}, required by Crystal2 beamline element'.format(mirror_file)
            el.append(srwlib.srwl_opt_setup_surf_height_1d(
                srwlib.srwl_uti_read_data_cols(mirror_file, "\t", 0, 1),
                _dim=v.op_Crystal2_dim,
                _ang=abs(v.op_Crystal2_ang),
                _amp_coef=v.op_Crystal2_amp_coef,
            ))
            pp.append([0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0])
        elif el_name == 'Crystal2_Grating':
            # Crystal2_Grating: drift 32.5m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Crystal2_Grating_L,
            ))
            pp.append(v.op_Crystal2_Grating_pp)
        elif el_name == 'Grating':
            # Grating: grating 33.0m
            mirror = srwlib.SRWLOptMirPl(
                _size_tang=v.op_Grating_size_tang,
                _size_sag=v.op_Grating_size_sag,
                _nvx=v.op_Grating_nvx,
                _nvy=v.op_Grating_nvy,
                _nvz=v.op_Grating_nvz,
                _tvx=v.op_Grating_tvx,
                _tvy=v.op_Grating_tvy,
                _x=v.op_Grating_x,
                _y=v.op_Grating_y,
            )
            el.append(srwlib.SRWLOptG(
                _mirSub=mirror,
                _m=v.op_Grating_m,
                _grDen=v.op_Grating_grDen,
                _grDen1=v.op_Grating_grDen1,
                _grDen2=v.op_Grating_grDen2,
                _grDen3=v.op_Grating_grDen3,
                _grDen4=v.op_Grating_grDen4,
            ))
            pp.append(v.op_Grating_pp)
        elif el_name == 'Grating_Watchpoint':
            # Grating_Watchpoint: drift 33.0m
            el.append(srwlib.SRWLOptD(
                _L=v.op_Grating_Watchpoint_L,
            ))
            pp.append(v.op_Grating_Watchpoint_pp)
        elif el_name == 'Watchpoint':
            # Watchpoint: watch 34.0m
            pass
    pp.append(v.op_fin_pp)
    return srwlib.SRWLOptC(el, pp)


varParam = srwl_bl.srwl_uti_ext_options([
    ['name', 's', 'All optical elements', 'simulation name'],

#---Data Folder
    ['fdir', 's', '', 'folder (directory) name for reading-in input and saving output data files'],

#---Electron Beam
    ['ebm_nm', 's', 'NSLS-II Low Beta Final', 'standard electron beam name'],
    ['ebm_nms', 's', '', 'standard electron beam name suffix: e.g. can be Day1, Final'],
    ['ebm_i', 'f', 0.5, 'electron beam current [A]'],
    ['ebm_e', 'f', 3.0, 'electron beam avarage energy [GeV]'],
    ['ebm_de', 'f', 0.0, 'electron beam average energy deviation [GeV]'],
    ['ebm_x', 'f', 0.0, 'electron beam initial average horizontal position [m]'],
    ['ebm_y', 'f', 0.0, 'electron beam initial average vertical position [m]'],
    ['ebm_xp', 'f', 0.0, 'electron beam initial average horizontal angle [rad]'],
    ['ebm_yp', 'f', 0.0, 'electron beam initial average vertical angle [rad]'],
    ['ebm_z', 'f', 0., 'electron beam initial average longitudinal position [m]'],
    ['ebm_dr', 'f', -1.54, 'electron beam longitudinal drift [m] to be performed before a required calculation'],
    ['ebm_ens', 'f', 0.00089, 'electron beam relative energy spread'],
    ['ebm_emx', 'f', 5.5e-10, 'electron beam horizontal emittance [m]'],
    ['ebm_emy', 'f', 8e-12, 'electron beam vertical emittance [m]'],
    # Definition of the beam through Twiss:
    ['ebm_betax', 'f', 2.02, 'horizontal beta-function [m]'],
    ['ebm_betay', 'f', 1.06, 'vertical beta-function [m]'],
    ['ebm_alphax', 'f', 0.0, 'horizontal alpha-function [rad]'],
    ['ebm_alphay', 'f', 0.0, 'vertical alpha-function [rad]'],
    ['ebm_etax', 'f', 0.0, 'horizontal dispersion function [m]'],
    ['ebm_etay', 'f', 0.0, 'vertical dispersion function [m]'],
    ['ebm_etaxp', 'f', 0.0, 'horizontal dispersion function derivative [rad]'],
    ['ebm_etayp', 'f', 0.0, 'vertical dispersion function derivative [rad]'],
    # Definition of the beam through Moments:
    ['ebm_sigx', 'f', 3.3331666625e-05, 'horizontal RMS size of electron beam [m]'],
    ['ebm_sigy', 'f', 2.91204395571e-06, 'vertical RMS size of electron beam [m]'],
    ['ebm_sigxp', 'f', 1.65008250619e-05, 'horizontal RMS angular divergence of electron beam [rad]'],
    ['ebm_sigyp', 'f', 2.74721127897e-06, 'vertical RMS angular divergence of electron beam [rad]'],
    ['ebm_mxxp', 'f', 0.0, 'horizontal position-angle mixed 2nd order moment of electron beam [m]'],
    ['ebm_myyp', 'f', 0.0, 'vertical position-angle mixed 2nd order moment of electron beam [m]'],

#---Undulator
    ['und_bx', 'f', 0.0, 'undulator horizontal peak magnetic field [T]'],
    ['und_by', 'f', 0.88770981, 'undulator vertical peak magnetic field [T]'],
    ['und_phx', 'f', 0.0, 'initial phase of the horizontal magnetic field [rad]'],
    ['und_phy', 'f', 0.0, 'initial phase of the vertical magnetic field [rad]'],
    ['und_b2e', '', '', 'estimate undulator fundamental photon energy (in [eV]) for the amplitude of sinusoidal magnetic field defined by und_b or und_bx, und_by', 'store_true'],
    ['und_e2b', '', '', 'estimate undulator field amplitude (in [T]) for the photon energy defined by w_e', 'store_true'],
    ['und_per', 'f', 0.02, 'undulator period [m]'],
    ['und_len', 'f', 3.0, 'undulator length [m]'],
    ['und_zc', 'f', 0.0, 'undulator center longitudinal position [m]'],
    ['und_sx', 'i', 1, 'undulator horizontal magnetic field symmetry vs longitudinal position'],
    ['und_sy', 'i', -1, 'undulator vertical magnetic field symmetry vs longitudinal position'],
    ['und_g', 'f', 6.72, 'undulator gap [mm] (assumes availability of magnetic measurement or simulation data)'],
    ['und_ph', 'f', 0.0, 'shift of magnet arrays [mm] for which the field should be set up'],
    ['und_mdir', 's', '', 'name of magnetic measurements sub-folder'],
    ['und_mfs', 's', '', 'name of magnetic measurements for different gaps summary file'],



#---Calculation Types
    # Electron Trajectory
    ['tr', '', '', 'calculate electron trajectory', 'store_true'],
    ['tr_cti', 'f', 0.0, 'initial time moment (c*t) for electron trajectory calculation [m]'],
    ['tr_ctf', 'f', 0.0, 'final time moment (c*t) for electron trajectory calculation [m]'],
    ['tr_np', 'f', 10000, 'number of points for trajectory calculation'],
    ['tr_mag', 'i', 1, 'magnetic field to be used for trajectory calculation: 1- approximate, 2- accurate'],
    ['tr_fn', 's', 'res_trj.dat', 'file name for saving calculated trajectory data'],
    ['tr_pl', 's', '', 'plot the resulting trajectiry in graph(s): ""- dont plot, otherwise the string should list the trajectory components to plot'],

    #Single-Electron Spectrum vs Photon Energy
    ['ss', '', '', 'calculate single-e spectrum vs photon energy', 'store_true'],
    ['ss_ei', 'f', 100.0, 'initial photon energy [eV] for single-e spectrum vs photon energy calculation'],
    ['ss_ef', 'f', 20000.0, 'final photon energy [eV] for single-e spectrum vs photon energy calculation'],
    ['ss_ne', 'i', 10000, 'number of points vs photon energy for single-e spectrum vs photon energy calculation'],
    ['ss_x', 'f', 0.0, 'horizontal position [m] for single-e spectrum vs photon energy calculation'],
    ['ss_y', 'f', 0.0, 'vertical position [m] for single-e spectrum vs photon energy calculation'],
    ['ss_meth', 'i', 1, 'method to use for single-e spectrum vs photon energy calculation: 0- "manual", 1- "auto-undulator", 2- "auto-wiggler"'],
    ['ss_prec', 'f', 0.01, 'relative precision for single-e spectrum vs photon energy calculation (nominal value is 0.01)'],
    ['ss_pol', 'i', 6, 'polarization component to extract after spectrum vs photon energy calculation: 0- Linear Horizontal, 1- Linear Vertical, 2- Linear 45 degrees, 3- Linear 135 degrees, 4- Circular Right, 5- Circular Left, 6- Total'],
    ['ss_mag', 'i', 1, 'magnetic field to be used for single-e spectrum vs photon energy calculation: 1- approximate, 2- accurate'],
    ['ss_ft', 's', 'f', 'presentation/domain: "f"- frequency (photon energy), "t"- time'],
    ['ss_u', 'i', 1, 'electric field units: 0- arbitrary, 1- sqrt(Phot/s/0.1%bw/mm^2), 2- sqrt(J/eV/mm^2) or sqrt(W/mm^2), depending on representation (freq. or time)'],
    ['ss_fn', 's', 'res_spec_se.dat', 'file name for saving calculated single-e spectrum vs photon energy'],
    ['ss_pl', 's', '', 'plot the resulting single-e spectrum in a graph: ""- dont plot, "e"- show plot vs photon energy'],

    #Multi-Electron Spectrum vs Photon Energy (taking into account e-beam emittance, energy spread and collection aperture size)
    ['sm', '', '', 'calculate multi-e spectrum vs photon energy', 'store_true'],
    ['sm_ei', 'f', 100.0, 'initial photon energy [eV] for multi-e spectrum vs photon energy calculation'],
    ['sm_ef', 'f', 20000.0, 'final photon energy [eV] for multi-e spectrum vs photon energy calculation'],
    ['sm_ne', 'i', 10000, 'number of points vs photon energy for multi-e spectrum vs photon energy calculation'],
    ['sm_x', 'f', 0.0, 'horizontal center position [m] for multi-e spectrum vs photon energy calculation'],
    ['sm_rx', 'f', 0.001, 'range of horizontal position / horizontal aperture size [m] for multi-e spectrum vs photon energy calculation'],
    ['sm_nx', 'i', 1, 'number of points vs horizontal position for multi-e spectrum vs photon energy calculation'],
    ['sm_y', 'f', 0.0, 'vertical center position [m] for multi-e spectrum vs photon energy calculation'],
    ['sm_ry', 'f', 0.001, 'range of vertical position / vertical aperture size [m] for multi-e spectrum vs photon energy calculation'],
    ['sm_ny', 'i', 1, 'number of points vs vertical position for multi-e spectrum vs photon energy calculation'],
    ['sm_mag', 'i', 1, 'magnetic field to be used for calculation of multi-e spectrum spectrum or intensity distribution: 1- approximate, 2- accurate'],
    ['sm_hi', 'i', 1, 'initial UR spectral harmonic to be taken into account for multi-e spectrum vs photon energy calculation'],
    ['sm_hf', 'i', 15, 'final UR spectral harmonic to be taken into account for multi-e spectrum vs photon energy calculation'],
    ['sm_prl', 'f', 1.0, 'longitudinal integration precision parameter for multi-e spectrum vs photon energy calculation'],
    ['sm_pra', 'f', 1.0, 'azimuthal integration precision parameter for multi-e spectrum vs photon energy calculation'],
    ['sm_meth', 'i', -1, 'method to use for spectrum vs photon energy calculation in case of arbitrary input magnetic field: 0- "manual", 1- "auto-undulator", 2- "auto-wiggler", -1- dont use this accurate integration method (rather use approximate if possible)'],
    ['sm_prec', 'f', 0.01, 'relative precision for spectrum vs photon energy calculation in case of arbitrary input magnetic field (nominal value is 0.01)'],
    ['sm_nm', 'i', 1, 'number of macro-electrons for calculation of spectrum in case of arbitrary input magnetic field'],
    ['sm_na', 'i', 5, 'number of macro-electrons to average on each node at parallel (MPI-based) calculation of spectrum in case of arbitrary input magnetic field'],
    ['sm_ns', 'i', 5, 'saving periodicity (in terms of macro-electrons) for intermediate intensity at calculation of multi-electron spectrum in case of arbitrary input magnetic field'],
    ['sm_type', 'i', 1, 'calculate flux (=1) or flux per unit surface (=2)'],
    ['sm_pol', 'i', 6, 'polarization component to extract after calculation of multi-e flux or intensity: 0- Linear Horizontal, 1- Linear Vertical, 2- Linear 45 degrees, 3- Linear 135 degrees, 4- Circular Right, 5- Circular Left, 6- Total'],
    ['sm_rm', 'i', 1, 'method for generation of pseudo-random numbers for e-beam phase-space integration: 1- standard pseudo-random number generator, 2- Halton sequences, 3- LPtau sequences (to be implemented)'],
    ['sm_fn', 's', 'res_spec_me.dat', 'file name for saving calculated milti-e spectrum vs photon energy'],
    ['sm_pl', 's', '', 'plot the resulting spectrum-e spectrum in a graph: ""- dont plot, "e"- show plot vs photon energy'],
    #to add options for the multi-e calculation from "accurate" magnetic field

    #Power Density Distribution vs horizontal and vertical position
    ['pw', '', '', 'calculate SR power density distribution', 'store_true'],
    ['pw_x', 'f', 0.0, 'central horizontal position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_rx', 'f', 0.015, 'range of horizontal position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_nx', 'i', 100, 'number of points vs horizontal position for calculation of power density distribution'],
    ['pw_y', 'f', 0.0, 'central vertical position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_ry', 'f', 0.015, 'range of vertical position [m] for calculation of power density distribution vs horizontal and vertical position'],
    ['pw_ny', 'i', 100, 'number of points vs vertical position for calculation of power density distribution'],
    ['pw_pr', 'f', 1.0, 'precision factor for calculation of power density distribution'],
    ['pw_meth', 'i', 1, 'power density computation method (1- "near field", 2- "far field")'],
    ['pw_zst', 'f', 0., 'initial longitudinal position along electron trajectory of power density distribution (effective if pow_sst < pow_sfi)'],
    ['pw_zfi', 'f', 0., 'final longitudinal position along electron trajectory of power density distribution (effective if pow_sst < pow_sfi)'],
    ['pw_mag', 'i', 1, 'magnetic field to be used for power density calculation: 1- approximate, 2- accurate'],
    ['pw_fn', 's', 'res_pow.dat', 'file name for saving calculated power density distribution'],
    ['pw_pl', 's', '', 'plot the resulting power density distribution in a graph: ""- dont plot, "x"- vs horizontal position, "y"- vs vertical position, "xy"- vs horizontal and vertical position'],

    #Single-Electron Intensity distribution vs horizontal and vertical position
    ['si', '', '', 'calculate single-e intensity distribution (without wavefront propagation through a beamline) vs horizontal and vertical position', 'store_true'],
    #Single-Electron Wavefront Propagation
    ['ws', '', '', 'calculate single-electron (/ fully coherent) wavefront propagation', 'store_true'],
    #Multi-Electron (partially-coherent) Wavefront Propagation
    ['wm', '', '', 'calculate multi-electron (/ partially coherent) wavefront propagation', 'store_true'],

    ['w_e', 'f', 9000.0, 'photon energy [eV] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ef', 'f', -1.0, 'final photon energy [eV] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ne', 'i', 1, 'number of points vs photon energy for calculation of intensity distribution'],
    ['w_x', 'f', 0.0, 'central horizontal position [m] for calculation of intensity distribution'],
    ['w_rx', 'f', 0.0004, 'range of horizontal position [m] for calculation of intensity distribution'],
    ['w_nx', 'i', 100, 'number of points vs horizontal position for calculation of intensity distribution'],
    ['w_y', 'f', 0.0, 'central vertical position [m] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ry', 'f', 0.0006, 'range of vertical position [m] for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_ny', 'i', 100, 'number of points vs vertical position for calculation of intensity distribution'],
    ['w_smpf', 'f', 1.0, 'sampling factor for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_meth', 'i', 1, 'method to use for calculation of intensity distribution vs horizontal and vertical position: 0- "manual", 1- "auto-undulator", 2- "auto-wiggler"'],
    ['w_prec', 'f', 0.01, 'relative precision for calculation of intensity distribution vs horizontal and vertical position'],
    ['w_u', 'i', 1, 'electric field units: 0- arbitrary, 1- sqrt(Phot/s/0.1%bw/mm^2), 2- sqrt(J/eV/mm^2) or sqrt(W/mm^2), depending on representation (freq. or time)'],
    ['si_pol', 'i', 6, 'polarization component to extract after calculation of intensity distribution: 0- Linear Horizontal, 1- Linear Vertical, 2- Linear 45 degrees, 3- Linear 135 degrees, 4- Circular Right, 5- Circular Left, 6- Total'],
    ['si_type', 'i', 0, 'type of a characteristic to be extracted after calculation of intensity distribution: 0- Single-Electron Intensity, 1- Multi-Electron Intensity, 2- Single-Electron Flux, 3- Multi-Electron Flux, 4- Single-Electron Radiation Phase, 5- Re(E): Real part of Single-Electron Electric Field, 6- Im(E): Imaginary part of Single-Electron Electric Field, 7- Single-Electron Intensity, integrated over Time or Photon Energy'],
    ['w_mag', 'i', 1, 'magnetic field to be used for calculation of intensity distribution vs horizontal and vertical position: 1- approximate, 2- accurate'],

    ['si_fn', 's', 'res_int_se.dat', 'file name for saving calculated single-e intensity distribution (without wavefront propagation through a beamline) vs horizontal and vertical position'],
    ['si_pl', 's', '', 'plot the input intensity distributions in graph(s): ""- dont plot, "x"- vs horizontal position, "y"- vs vertical position, "xy"- vs horizontal and vertical position'],
    ['ws_fni', 's', 'res_int_pr_se.dat', 'file name for saving propagated single-e intensity distribution vs horizontal and vertical position'],
    ['ws_pl', 's', '', 'plot the resulting intensity distributions in graph(s): ""- dont plot, "x"- vs horizontal position, "y"- vs vertical position, "xy"- vs horizontal and vertical position'],

    ['wm_nm', 'i', 100000, 'number of macro-electrons (coherent wavefronts) for calculation of multi-electron wavefront propagation'],
    ['wm_na', 'i', 5, 'number of macro-electrons (coherent wavefronts) to average on each node for parallel (MPI-based) calculation of multi-electron wavefront propagation'],
    ['wm_ns', 'i', 5, 'saving periodicity (in terms of macro-electrons / coherent wavefronts) for intermediate intensity at multi-electron wavefront propagation calculation'],
    ['wm_ch', 'i', 0, 'type of a characteristic to be extracted after calculation of multi-electron wavefront propagation: #0- intensity (s0); 1- four Stokes components; 2- mutual intensity cut vs x; 3- mutual intensity cut vs y; 40- intensity(s0), mutual intensity cuts and degree of coherence vs X & Y'],
    ['wm_ap', 'i', 0, 'switch specifying representation of the resulting Stokes parameters: coordinate (0) or angular (1)'],
    ['wm_x0', 'f', 0, 'horizontal center position for mutual intensity cut calculation'],
    ['wm_y0', 'f', 0, 'vertical center position for mutual intensity cut calculation'],
    ['wm_ei', 'i', 0, 'integration over photon energy is required (1) or not (0); if the integration is required, the limits are taken from w_e, w_ef'],
    ['wm_rm', 'i', 1, 'method for generation of pseudo-random numbers for e-beam phase-space integration: 1- standard pseudo-random number generator, 2- Halton sequences, 3- LPtau sequences (to be implemented)'],
    ['wm_am', 'i', 0, 'multi-electron integration approximation method: 0- no approximation (use the standard 5D integration method), 1- integrate numerically only over e-beam energy spread and use convolution to treat transverse emittance'],
    ['wm_fni', 's', 'res_int_pr_me.dat', 'file name for saving propagated multi-e intensity distribution vs horizontal and vertical position'],

    #to add options
    ['op_r', 'f', 20.0, 'longitudinal position of the first optical element [m]'],

    # Former appParam:
    ['rs_type', 's', 'u', 'source type, (u) idealized undulator, (t), tabulated undulator, (m) multipole, (g) gaussian beam'],

#---Beamline optics:
    # Lens: lens
    ['op_Lens_Fx', 'f', 3.0, 'horizontalFocalLength'],
    ['op_Lens_Fy', 'f', 1e+23, 'verticalFocalLength'],
    ['op_Lens_x', 'f', 0.0, 'horizontalOffset'],
    ['op_Lens_y', 'f', 0.0, 'verticalOffset'],

    # Lens_CRL: drift
    ['op_Lens_CRL_L', 'f', 1.0, 'length'],

    # CRL: crl
    ['op_CRL_foc_plane', 'f', 2, 'focalPlane'],
    ['op_CRL_delta', 'f', 4.20757e-06, 'refractiveIndex'],
    ['op_CRL_atten_len', 'f', 0.007313, 'attenuationLength'],
    ['op_CRL_shape', 'f', 1, 'shape'],
    ['op_CRL_apert_h', 'f', 0.001, 'horizontalApertureSize'],
    ['op_CRL_apert_v', 'f', 0.001, 'verticalApertureSize'],
    ['op_CRL_r_min', 'f', 0.0015, 'tipRadius'],
    ['op_CRL_wall_thick', 'f', 8e-05, 'tipWallThickness'],
    ['op_CRL_x', 'f', 0.0, 'horizontalOffset'],
    ['op_CRL_y', 'f', 0.0, 'verticalOffset'],
    ['op_CRL_n', 'i', 3, 'numberOfLenses'],

    # CRL_Zone_Plate: drift
    ['op_CRL_Zone_Plate_L', 'f', 1.0, 'length'],

    # Zone_Plate: zonePlate
    ['op_Zone_Plate_rn', 'f', 0.0001, 'outerRadius'],
    ['op_Zone_Plate_thick', 'f', 1e-05, 'thickness'],
    ['op_Zone_Plate_delta1', 'f', 1e-06, 'mainRefractiveIndex'],
    ['op_Zone_Plate_atLen1', 'f', 0.1, 'mainAttenuationLength'],
    ['op_Zone_Plate_delta2', 'f', 0.0, 'complementaryRefractiveIndex'],
    ['op_Zone_Plate_atLen2', 'f', 1e-06, 'complementaryAttenuationLength'],
    ['op_Zone_Plate_x', 'f', 0.0, 'horizontalOffset'],
    ['op_Zone_Plate_y', 'f', 0.0, 'verticalOffset'],
    ['op_Zone_Plate_nZones', 'i', 100, 'numberOfZones'],

    # Zone_Plate_Fiber: drift
    ['op_Zone_Plate_Fiber_L', 'f', 1.0, 'length'],

    # Fiber: fiber
    ['op_Fiber_foc_plane', 'f', 1, 'focalPlane'],
    ['op_Fiber_delta_ext', 'f', 4.207568e-06, 'externalRefractiveIndex'],
    ['op_Fiber_delta_core', 'f', 4.207568e-06, 'coreRefractiveIndex'],
    ['op_Fiber_atten_len_ext', 'f', 0.007313, 'externalAttenuationLength'],
    ['op_Fiber_atten_len_core', 'f', 0.007313, 'coreAttenuationLength'],
    ['op_Fiber_externalDiameter', 'f', 0.0001, 'externalDiameter'],
    ['op_Fiber_diam_core', 'f', 1e-05, 'coreDiameter'],
    ['op_Fiber_xc', 'f', 0.0, 'horizontalCenterPosition'],
    ['op_Fiber_yc', 'f', 0.0, 'verticalCenterPosition'],

    # Fiber_Aperture: drift
    ['op_Fiber_Aperture_L', 'f', 1.0, 'length'],

    # Aperture: aperture
    ['op_Aperture_shape', 's', 'r', 'shape'],
    ['op_Aperture_Dx', 'f', 0.001, 'horizontalSize'],
    ['op_Aperture_Dy', 'f', 0.001, 'verticalSize'],
    ['op_Aperture_x', 'f', 0.0, 'horizontalOffset'],
    ['op_Aperture_y', 'f', 0.0, 'verticalOffset'],

    # Aperture_Obstacle: drift
    ['op_Aperture_Obstacle_L', 'f', 1.0, 'length'],

    # Obstacle: obstacle
    ['op_Obstacle_shape', 's', 'r', 'shape'],
    ['op_Obstacle_Dx', 'f', 0.0005, 'horizontalSize'],
    ['op_Obstacle_Dy', 'f', 0.0005, 'verticalSize'],
    ['op_Obstacle_x', 'f', 0.0, 'horizontalOffset'],
    ['op_Obstacle_y', 'f', 0.0, 'verticalOffset'],

    # Obstacle_Mask: drift
    ['op_Obstacle_Mask_L', 'f', 1.0, 'length'],

    # Mask: mask
    ['op_Mask_delta', 'f', 1.0, 'refractiveIndex'],
    ['op_Mask_atten_len', 'f', 1.0, 'attenuationLength'],
    ['op_Mask_thick', 'f', 1.0, 'maskThickness'],
    ['op_Mask_grid_sh', 'f', 0, 'gridShape'],
    ['op_Mask_grid_dx', 'f', 5e-06, 'horizontalGridDimension'],
    ['op_Mask_grid_dy', 'f', 5e-06, 'verticalGridDimension'],
    ['op_Mask_pitch_x', 'f', 2e-05, 'horizontalGridPitch'],
    ['op_Mask_pitch_y', 'f', 2e-05, 'verticalGridPitch'],
    ['op_Mask_gridTiltAngle', 'f', 0.436332312999, 'gridTiltAngle'],
    ['op_Mask_hx', 'f', 7.32e-07, 'horizontalSamplingInterval'],
    ['op_Mask_hy', 'f', 7.32e-07, 'verticalSamplingInterval'],
    ['op_Mask_mask_x0', 'f', 0.0, 'horizontalMaskCoordinate'],
    ['op_Mask_mask_y0', 'f', 0.0, 'verticalMaskCoordinate'],
    ['op_Mask_mask_Nx', 'i', 1024, 'horizontalPixelsNumber'],
    ['op_Mask_mask_Ny', 'i', 1024, 'verticalPixelsNumber'],
    ['op_Mask_grid_nx', 'i', 21, 'horizontalGridsNumber'],
    ['op_Mask_grid_ny', 'i', 21, 'verticalGridsNumber'],

    # Mask_Sample: drift
    ['op_Mask_Sample_L', 'f', 1.0, 'length'],

    # Sample: sample
    ['op_Sample_file_path', 's', 'sample.tif', 'imageFile'],
    ['op_Sample_outputImageFormat', 's', 'tif', 'outputImageFormat'],
    ['op_Sample_position', 'f', 27.0, 'position'],
    ['op_Sample_resolution', 'f', 2.480469e-09, 'resolution'],
    ['op_Sample_thick', 'f', 1e-05, 'thickness'],
    ['op_Sample_delta', 'f', 3.738856e-05, 'refractiveIndex'],
    ['op_Sample_atten_len', 'f', 3.38902e-06, 'attenuationLength'],
    ['op_Sample_horizontalCenterCoordinate', 'f', 0.0, 'horizontalCenterCoordinate'],
    ['op_Sample_verticalCenterCoordinate', 'f', 0.0, 'verticalCenterCoordinate'],
    ['op_Sample_rotateAngle', 'f', 0.0, 'rotateAngle'],
    ['op_Sample_cutoffBackgroundNoise', 'f', 0.5, 'cutoffBackgroundNoise'],
    ['op_Sample_cropArea', 'i', 1, 'cropArea'],
    ['op_Sample_extTransm', 'i', 1, 'transmissionImage'],
    ['op_Sample_areaXStart', 'i', 0, 'areaXStart'],
    ['op_Sample_areaXEnd', 'i', 1280, 'areaXEnd'],
    ['op_Sample_areaYStart', 'i', 0, 'areaYStart'],
    ['op_Sample_areaYEnd', 'i', 834, 'areaYEnd'],
    ['op_Sample_rotateReshape', 'i', 0, 'rotateReshape'],
    ['op_Sample_backgroundColor', 'i', 0, 'backgroundColor'],
    ['op_Sample_tileImage', 'i', 0, 'tileImage'],
    ['op_Sample_tileRows', 'i', 1, 'tileRows'],
    ['op_Sample_tileColumns', 'i', 1, 'tileColumns'],
    ['op_Sample_shiftX', 'i', 0, 'shiftX'],
    ['op_Sample_shiftY', 'i', 0, 'shiftY'],
    ['op_Sample_invert', 'i', 0, 'invert'],

    # Sample_Planar: drift
    ['op_Sample_Planar_L', 'f', 1.0, 'length'],

    # Planar: mirror
    ['op_Planar_hfn', 's', 'mirror_1d.dat', 'heightProfileFile'],
    ['op_Planar_dim', 's', 'x', 'orientation'],
    ['op_Planar_ang', 'f', 0.0031415926, 'grazingAngle'],
    ['op_Planar_amp_coef', 'f', 1.0, 'heightAmplification'],
    ['op_Planar_size_x', 'f', 0.001, 'horizontalTransverseSize'],
    ['op_Planar_size_y', 'f', 0.001, 'verticalTransverseSize'],

    # Planar_Circular_Cylinder: drift
    ['op_Planar_Circular_Cylinder_L', 'f', 1.0, 'length'],

    # Circular_Cylinder: sphericalMirror
    ['op_Circular_Cylinder_hfn', 's', '', 'heightProfileFile'],
    ['op_Circular_Cylinder_dim', 's', 'x', 'orientation'],
    ['op_Circular_Cylinder_r', 'f', 1049.0, 'radius'],
    ['op_Circular_Cylinder_size_tang', 'f', 0.3, 'tangentialSize'],
    ['op_Circular_Cylinder_size_sag', 'f', 0.11, 'sagittalSize'],
    ['op_Circular_Cylinder_ang', 'f', 0.0031415926, 'grazingAngle'],
    ['op_Circular_Cylinder_nvx', 'f', 0.999995065202, 'normalVectorX'],
    ['op_Circular_Cylinder_nvy', 'f', 0.0, 'normalVectorY'],
    ['op_Circular_Cylinder_nvz', 'f', -0.00314158743229, 'normalVectorZ'],
    ['op_Circular_Cylinder_tvx', 'f', 0.00314158743229, 'tangentialVectorX'],
    ['op_Circular_Cylinder_tvy', 'f', 0.0, 'tangentialVectorY'],
    ['op_Circular_Cylinder_amp_coef', 'f', 1.0, 'heightAmplification'],
    ['op_Circular_Cylinder_x', 'f', 0.0, 'horizontalOffset'],
    ['op_Circular_Cylinder_y', 'f', 0.0, 'verticalOffset'],

    # Circular_Cylinder_Circular_Cylinder2: drift
    ['op_Circular_Cylinder_Circular_Cylinder2_L', 'f', 0.5, 'length'],

    # Circular_Cylinder2: sphericalMirror
    ['op_Circular_Cylinder2_hfn', 's', 'mirror_1d.dat', 'heightProfileFile'],
    ['op_Circular_Cylinder2_dim', 's', 'x', 'orientation'],
    ['op_Circular_Cylinder2_r', 'f', 1049.0, 'radius'],
    ['op_Circular_Cylinder2_size_tang', 'f', 0.3, 'tangentialSize'],
    ['op_Circular_Cylinder2_size_sag', 'f', 0.11, 'sagittalSize'],
    ['op_Circular_Cylinder2_ang', 'f', 0.0031415926, 'grazingAngle'],
    ['op_Circular_Cylinder2_nvx', 'f', 0.999995065202, 'normalVectorX'],
    ['op_Circular_Cylinder2_nvy', 'f', 0.0, 'normalVectorY'],
    ['op_Circular_Cylinder2_nvz', 'f', -0.00314158743229, 'normalVectorZ'],
    ['op_Circular_Cylinder2_tvx', 'f', 0.00314158743229, 'tangentialVectorX'],
    ['op_Circular_Cylinder2_tvy', 'f', 0.0, 'tangentialVectorY'],
    ['op_Circular_Cylinder2_amp_coef', 'f', 1.0, 'heightAmplification'],
    ['op_Circular_Cylinder2_x', 'f', 0.0, 'horizontalOffset'],
    ['op_Circular_Cylinder2_y', 'f', 0.0, 'verticalOffset'],

    # Circular_Cylinder2_Elliptical_Cylinder: drift
    ['op_Circular_Cylinder2_Elliptical_Cylinder_L', 'f', 0.5, 'length'],

    # Elliptical_Cylinder: ellipsoidMirror
    ['op_Elliptical_Cylinder_hfn', 's', '', 'heightProfileFile'],
    ['op_Elliptical_Cylinder_dim', 's', 'x', 'orientation'],
    ['op_Elliptical_Cylinder_p', 'f', 30.0, 'firstFocusLength'],
    ['op_Elliptical_Cylinder_q', 'f', 1.7, 'focalLength'],
    ['op_Elliptical_Cylinder_ang', 'f', 0.0036, 'grazingAngle'],
    ['op_Elliptical_Cylinder_amp_coef', 'f', 1.0, 'heightAmplification'],
    ['op_Elliptical_Cylinder_size_tang', 'f', 0.5, 'tangentialSize'],
    ['op_Elliptical_Cylinder_size_sag', 'f', 0.01, 'sagittalSize'],
    ['op_Elliptical_Cylinder_nvx', 'f', 0.999993520007, 'normalVectorX'],
    ['op_Elliptical_Cylinder_nvy', 'f', 0.0, 'normalVectorY'],
    ['op_Elliptical_Cylinder_nvz', 'f', -0.00359999222401, 'normalVectorZ'],
    ['op_Elliptical_Cylinder_tvx', 'f', -0.00359999222401, 'tangentialVectorX'],
    ['op_Elliptical_Cylinder_tvy', 'f', 0.0, 'tangentialVectorY'],
    ['op_Elliptical_Cylinder_x', 'f', 0.0, 'horizontalOffset'],
    ['op_Elliptical_Cylinder_y', 'f', 0.0, 'verticalOffset'],

    # Elliptical_Cylinder_Elliptical_Cylinder2: drift
    ['op_Elliptical_Cylinder_Elliptical_Cylinder2_L', 'f', 0.5, 'length'],

    # Elliptical_Cylinder2: ellipsoidMirror
    ['op_Elliptical_Cylinder2_hfn', 's', 'mirror_2d.dat', 'heightProfileFile'],
    ['op_Elliptical_Cylinder2_dim', 's', 'x', 'orientation'],
    ['op_Elliptical_Cylinder2_p', 'f', 35.0, 'firstFocusLength'],
    ['op_Elliptical_Cylinder2_q', 'f', 1.7, 'focalLength'],
    ['op_Elliptical_Cylinder2_ang', 'f', 0.0036, 'grazingAngle'],
    ['op_Elliptical_Cylinder2_amp_coef', 'f', 1.0, 'heightAmplification'],
    ['op_Elliptical_Cylinder2_size_tang', 'f', 0.5, 'tangentialSize'],
    ['op_Elliptical_Cylinder2_size_sag', 'f', 0.01, 'sagittalSize'],
    ['op_Elliptical_Cylinder2_nvx', 'f', 0.999993520007, 'normalVectorX'],
    ['op_Elliptical_Cylinder2_nvy', 'f', 0.0, 'normalVectorY'],
    ['op_Elliptical_Cylinder2_nvz', 'f', -0.00359999222401, 'normalVectorZ'],
    ['op_Elliptical_Cylinder2_tvx', 'f', -0.00359999222401, 'tangentialVectorX'],
    ['op_Elliptical_Cylinder2_tvy', 'f', 0.0, 'tangentialVectorY'],
    ['op_Elliptical_Cylinder2_x', 'f', 0.0, 'horizontalOffset'],
    ['op_Elliptical_Cylinder2_y', 'f', 0.0, 'verticalOffset'],

    # Elliptical_Cylinder2_Toroid: drift
    ['op_Elliptical_Cylinder2_Toroid_L', 'f', 0.5, 'length'],

    # Toroid: toroidalMirror
    ['op_Toroid_hfn', 's', '', 'heightProfileFile'],
    ['op_Toroid_dim', 's', 'x', 'orientation'],
    ['op_Toroid_ap_shape', 's', 'r', 'apertureShape'],
    ['op_Toroid_rt', 'f', 7592.12, 'tangentialRadius'],
    ['op_Toroid_rs', 'f', 0.186, 'sagittalRadius'],
    ['op_Toroid_size_tang', 'f', 0.96, 'tangentialSize'],
    ['op_Toroid_size_sag', 'f', 0.08, 'sagittalSize'],
    ['op_Toroid_ang', 'f', 0.007, 'grazingAngle'],
    ['op_Toroid_horizontalPosition', 'f', 0.0, 'horizontalPosition'],
    ['op_Toroid_verticalPosition', 'f', 0.0, 'verticalPosition'],
    ['op_Toroid_nvx', 'f', 0.9999755001, 'normalVectorX'],
    ['op_Toroid_nvy', 'f', 0.0, 'normalVectorY'],
    ['op_Toroid_nvz', 'f', -0.00699994283347, 'normalVectorZ'],
    ['op_Toroid_tvx', 'f', 0.00699994283347, 'tangentialVectorX'],
    ['op_Toroid_tvy', 'f', 0.0, 'tangentialVectorY'],
    ['op_Toroid_amp_coef', 'f', 1.0, 'heightAmplification'],

    # Toroid_Toroid2: drift
    ['op_Toroid_Toroid2_L', 'f', 0.5, 'length'],

    # Toroid2: toroidalMirror
    ['op_Toroid2_hfn', 's', 'mirror2_1d.dat', 'heightProfileFile'],
    ['op_Toroid2_dim', 's', 'x', 'orientation'],
    ['op_Toroid2_ap_shape', 's', 'r', 'apertureShape'],
    ['op_Toroid2_rt', 'f', 7592.12, 'tangentialRadius'],
    ['op_Toroid2_rs', 'f', 0.186, 'sagittalRadius'],
    ['op_Toroid2_size_tang', 'f', 0.96, 'tangentialSize'],
    ['op_Toroid2_size_sag', 'f', 0.08, 'sagittalSize'],
    ['op_Toroid2_ang', 'f', 0.007, 'grazingAngle'],
    ['op_Toroid2_horizontalPosition', 'f', 0.0, 'horizontalPosition'],
    ['op_Toroid2_verticalPosition', 'f', 0.0, 'verticalPosition'],
    ['op_Toroid2_nvx', 'f', 0.9999755001, 'normalVectorX'],
    ['op_Toroid2_nvy', 'f', 0.0, 'normalVectorY'],
    ['op_Toroid2_nvz', 'f', -0.00699994283347, 'normalVectorZ'],
    ['op_Toroid2_tvx', 'f', 0.00699994283347, 'tangentialVectorX'],
    ['op_Toroid2_tvy', 'f', 0.0, 'tangentialVectorY'],
    ['op_Toroid2_amp_coef', 'f', 1.0, 'heightAmplification'],

    # Toroid2_Crystal: drift
    ['op_Toroid2_Crystal_L', 'f', 0.5, 'length'],

    # Crystal: crystal
    ['op_Crystal_hfn', 's', '', 'heightProfileFile'],
    ['op_Crystal_dim', 's', 'x', 'orientation'],
    ['op_Crystal_d_sp', 'f', 3.13557135638, 'dSpacing'],
    ['op_Crystal_psi0r', 'f', -1.20784200542e-05, 'psi0r'],
    ['op_Crystal_psi0i', 'f', 2.26348275468e-07, 'psi0i'],
    ['op_Crystal_psiHr', 'f', -6.38570337053e-06, 'psiHr'],
    ['op_Crystal_psiHi', 'f', 1.58030401297e-07, 'psiHi'],
    ['op_Crystal_psiHBr', 'f', -6.38570337053e-06, 'psiHBr'],
    ['op_Crystal_psiHBi', 'f', 1.58030401297e-07, 'psiHBi'],
    ['op_Crystal_tc', 'f', 0.01, 'crystalThickness'],
    ['op_Crystal_ang_as', 'f', 0.0, 'asymmetryAngle'],
    ['op_Crystal_nvx', 'f', 0.0, 'nvx'],
    ['op_Crystal_nvy', 'f', 0.975567318503, 'nvy'],
    ['op_Crystal_nvz', 'f', -0.219700721593, 'nvz'],
    ['op_Crystal_tvx', 'f', 0.0, 'tvx'],
    ['op_Crystal_tvy', 'f', 0.219700721593, 'tvy'],
    ['op_Crystal_ang', 'f', 0.221507686183, 'grazingAngle'],
    ['op_Crystal_amp_coef', 'f', 1.0, 'heightAmplification'],

    # Crystal_Crystal2: drift
    ['op_Crystal_Crystal2_L', 'f', 0.5, 'length'],

    # Crystal2: crystal
    ['op_Crystal2_hfn', 's', 'mirror_1d.dat', 'heightProfileFile'],
    ['op_Crystal2_dim', 's', 'x', 'orientation'],
    ['op_Crystal2_d_sp', 'f', 3.13557135638, 'dSpacing'],
    ['op_Crystal2_psi0r', 'f', -1.20784200542e-05, 'psi0r'],
    ['op_Crystal2_psi0i', 'f', 2.26348275468e-07, 'psi0i'],
    ['op_Crystal2_psiHr', 'f', -6.38570337053e-06, 'psiHr'],
    ['op_Crystal2_psiHi', 'f', 1.58030401297e-07, 'psiHi'],
    ['op_Crystal2_psiHBr', 'f', -6.38570337053e-06, 'psiHBr'],
    ['op_Crystal2_psiHBi', 'f', 1.58030401297e-07, 'psiHBi'],
    ['op_Crystal2_tc', 'f', 0.01, 'crystalThickness'],
    ['op_Crystal2_ang_as', 'f', 0.0, 'asymmetryAngle'],
    ['op_Crystal2_nvx', 'f', 0.0, 'nvx'],
    ['op_Crystal2_nvy', 'f', 0.975567318503, 'nvy'],
    ['op_Crystal2_nvz', 'f', -0.219700721593, 'nvz'],
    ['op_Crystal2_tvx', 'f', 0.0, 'tvx'],
    ['op_Crystal2_tvy', 'f', 0.219700721593, 'tvy'],
    ['op_Crystal2_ang', 'f', 0.221507686183, 'grazingAngle'],
    ['op_Crystal2_amp_coef', 'f', 1.0, 'heightAmplification'],

    # Crystal2_Grating: drift
    ['op_Crystal2_Grating_L', 'f', 0.5, 'length'],

    # Grating: grating
    ['op_Grating_size_tang', 'f', 0.2, 'tangentialSize'],
    ['op_Grating_size_sag', 'f', 0.015, 'sagittalSize'],
    ['op_Grating_nvx', 'f', 0.99991607766, 'normalVectorX'],
    ['op_Grating_nvy', 'f', 0.0, 'normalVectorY'],
    ['op_Grating_nvz', 'f', -0.0129552165957, 'normalVectorZ'],
    ['op_Grating_tvx', 'f', 0.0129552165957, 'tangentialVectorX'],
    ['op_Grating_tvy', 'f', 0.0, 'tangentialVectorY'],
    ['op_Grating_x', 'f', 0.0, 'horizontalOffset'],
    ['op_Grating_y', 'f', 0.0, 'verticalOffset'],
    ['op_Grating_m', 'f', 1.0, 'diffractionOrder'],
    ['op_Grating_grDen', 'f', 1800.0, 'grooveDensity0'],
    ['op_Grating_grDen1', 'f', 0.08997, 'grooveDensity1'],
    ['op_Grating_grDen2', 'f', 3.004e-06, 'grooveDensity2'],
    ['op_Grating_grDen3', 'f', 9.7e-11, 'grooveDensity3'],
    ['op_Grating_grDen4', 'f', 0.0, 'grooveDensity4'],

    # Grating_Watchpoint: drift
    ['op_Grating_Watchpoint_L', 'f', 1.0, 'length'],

#---Propagation parameters
    ['op_Lens_pp', 'f',                                     [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Lens'],
    ['op_Lens_CRL_pp', 'f',                                 [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Lens_CRL'],
    ['op_CRL_pp', 'f',                                      [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'CRL'],
    ['op_CRL_Zone_Plate_pp', 'f',                           [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'CRL_Zone_Plate'],
    ['op_Zone_Plate_pp', 'f',                               [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Zone_Plate'],
    ['op_Zone_Plate_Fiber_pp', 'f',                         [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Zone_Plate_Fiber'],
    ['op_Fiber_pp', 'f',                                    [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Fiber'],
    ['op_Fiber_Aperture_pp', 'f',                           [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Fiber_Aperture'],
    ['op_Aperture_pp', 'f',                                 [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Aperture'],
    ['op_Aperture_Obstacle_pp', 'f',                        [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Aperture_Obstacle'],
    ['op_Obstacle_pp', 'f',                                 [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Obstacle'],
    ['op_Obstacle_Mask_pp', 'f',                            [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Obstacle_Mask'],
    ['op_Mask_pp', 'f',                                     [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Mask'],
    ['op_Mask_Sample_pp', 'f',                              [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Mask_Sample'],
    ['op_Sample_pp', 'f',                                   [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Sample'],
    ['op_Sample_Planar_pp', 'f',                            [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Sample_Planar'],
    ['op_Planar_pp', 'f',                                   [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Planar'],
    ['op_Planar_Circular_Cylinder_pp', 'f',                 [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Planar_Circular_Cylinder'],
    ['op_Circular_Cylinder_pp', 'f',                        [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Circular_Cylinder'],
    ['op_Circular_Cylinder_Circular_Cylinder2_pp', 'f',     [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Circular_Cylinder_Circular_Cylinder2'],
    ['op_Circular_Cylinder2_pp', 'f',                       [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Circular_Cylinder2'],
    ['op_Circular_Cylinder2_Elliptical_Cylinder_pp', 'f',   [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Circular_Cylinder2_Elliptical_Cylinder'],
    ['op_Elliptical_Cylinder_pp', 'f',                      [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Elliptical_Cylinder'],
    ['op_Elliptical_Cylinder_Elliptical_Cylinder2_pp', 'f', [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Elliptical_Cylinder_Elliptical_Cylinder2'],
    ['op_Elliptical_Cylinder2_pp', 'f',                     [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Elliptical_Cylinder2'],
    ['op_Elliptical_Cylinder2_Toroid_pp', 'f',              [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Elliptical_Cylinder2_Toroid'],
    ['op_Toroid_pp', 'f',                                   [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Toroid'],
    ['op_Toroid_Toroid2_pp', 'f',                           [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Toroid_Toroid2'],
    ['op_Toroid2_pp', 'f',                                  [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Toroid2'],
    ['op_Toroid2_Crystal_pp', 'f',                          [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Toroid2_Crystal'],
    ['op_Crystal_pp', 'f',                                  [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Crystal'],
    ['op_Crystal_Crystal2_pp', 'f',                         [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Crystal_Crystal2'],
    ['op_Crystal2_pp', 'f',                                 [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Crystal2'],
    ['op_Crystal2_Grating_pp', 'f',                         [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Crystal2_Grating'],
    ['op_Grating_pp', 'f',                                  [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Grating'],
    ['op_Grating_Watchpoint_pp', 'f',                       [0, 0, 1.0, 1, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'Grating_Watchpoint'],
    ['op_fin_pp', 'f',                                      [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 'final post-propagation (resize) parameters'],

    #[ 0]: Auto-Resize (1) or not (0) Before propagation
    #[ 1]: Auto-Resize (1) or not (0) After propagation
    #[ 2]: Relative Precision for propagation with Auto-Resizing (1. is nominal)
    #[ 3]: Allow (1) or not (0) for semi-analytical treatment of the quadratic (leading) phase terms at the propagation
    #[ 4]: Do any Resizing on Fourier side, using FFT, (1) or not (0)
    #[ 5]: Horizontal Range modification factor at Resizing (1. means no modification)
    #[ 6]: Horizontal Resolution modification factor at Resizing
    #[ 7]: Vertical Range modification factor at Resizing
    #[ 8]: Vertical Resolution modification factor at Resizing
    #[ 9]: Type of wavefront Shift before Resizing (not yet implemented)
    #[10]: New Horizontal wavefront Center position after Shift (not yet implemented)
    #[11]: New Vertical wavefront Center position after Shift (not yet implemented)
    #[12]: Optional: Orientation of the Output Optical Axis vector in the Incident Beam Frame: Horizontal Coordinate
    #[13]: Optional: Orientation of the Output Optical Axis vector in the Incident Beam Frame: Vertical Coordinate
    #[14]: Optional: Orientation of the Output Optical Axis vector in the Incident Beam Frame: Longitudinal Coordinate
    #[15]: Optional: Orientation of the Horizontal Base vector of the Output Frame in the Incident Beam Frame: Horizontal Coordinate
    #[16]: Optional: Orientation of the Horizontal Base vector of the Output Frame in the Incident Beam Frame: Vertical Coordinate
])


def main():
    v = srwl_bl.srwl_uti_parse_options(varParam, use_sys_argv=True)
    op = set_optics(v)
    v.ss = True
    v.ss_pl = 'e'
    v.sm = True
    v.sm_pl = 'e'
    v.pw = True
    v.pw_pl = 'xy'
    v.si = True
    v.si_pl = 'xy'
    v.tr = True
    v.tr_pl = 'xz'
    v.ws = True
    v.ws_pl = 'xy'
    mag = None
    if v.rs_type == 'm':
        mag = srwlib.SRWLMagFldC()
        mag.arXc.append(0)
        mag.arYc.append(0)
        mag.arMagFld.append(srwlib.SRWLMagFldM(v.mp_field, v.mp_order, v.mp_distribution, v.mp_len))
        mag.arZc.append(v.mp_zc)
    srwl_bl.SRWLBeamline(_name=v.name, _mag_approx=mag).calc_all(v, op)


if __name__ == '__main__':
    main()
