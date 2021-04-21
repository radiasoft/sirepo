# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc
from sirepo.template import template_common
import re
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.util
import zipfile



class SimData(sirepo.sim_data.SimDataBase):

    _FLASH_EXE_PREFIX = 'flash_exe'
    _FLASH_FILE_NAME_SEP = '-'
    _FLASH_SETUP_UNITS_PREFIX = 'setup_units'

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        for m in list(dm.keys()):
            n = m
            for x in (':', ''), ('magnetoHD', ''), ('CapLaser$', 'CapLaserBELLA'):
                n = re.sub(x[0], x[1], n)
            if m != n:
                dm[n] = dm[m]
                del dm[m]
        cls.__fixup_old_data_problem_files(data)
        cls.__fixup_old_data_setup_arguments(data)
        cls.__fixup_old_data_one_dimension_profile_animation(data)
        cls.__fixup_old_data_var_animation_axis(data)
        cls._init_models(dm)
        cls.__fixup_old_data_setup_config_directives(data)
        cls.__fixup_old_data_setup_arguments_units(data)
        if dm.simulation.flashType == 'CapLaser':
            dm.simulation.flashType = 'CapLaserBELLA'
        if dm.simulation.flashType == 'CapLaserBELLA':
            dm.IO.update(
                plot_var_5='magz',
                plot_var_6='depo',
            )
            if not dm.Multispecies.ms_fillSpecies:
                m = dm.Multispecies
                m.ms_fillSpecies = 'hydrogen'
                m.ms_wallSpecies = 'alumina'
                m.eos_fillTableFile = 'helium-fill-imx.cn4'
                m.eos_wallTableFile = 'alumina-wall-imx.cn4'
                m.eos_fillSubType = 'ionmix4'
                m.eos_wallSubType = 'ionmix4'
                m = dm['physicsmaterialPropertiesOpacityMultispecies']
                m.op_fillFileName = 'helium-fill-imx.cn4'
                m.op_wallFileName  = 'alumina-wall-imx.cn4'
                m.op_fillFileType = 'ionmix4'
                m.op_wallFileType = 'ionmix4'
        dm['physicssourceTermsEnergyDepositionLaser'].pkdel('ed_gridnAngularTics_1')
        for n in 'currType', 'eosFill', 'eosWall':
            dm.pkdel(f'SimulationCapLaserBELLA{n}')
        m = dm.physicssourceTermsHeatexchange
        if 'useHeatExchange' in m:
            m.useHeatexchange = m.useHeatExchange
            m.pkdel('useHeatExchange')
        m = dm.gridEvolutionAnimation
        if 'valueList' not in m:
            m.valueList = PKDict()
            for x in 'y1', 'y2', 'y3':
                if dm.simulation.flashType in ('CapLaserBELLA', 'CapLaser3D'):
                    m.valueList[x] = [
                        'mass',
                        'x-momentum',
                        'y-momentum',
                        'z-momentum',
                        'E_total',
                        'E_kinetic',
                        'E_internal',
                        'MagEnergy',
                        'r001',
                        'r002',
                        'r003',
                        'r004',
                        'r005',
                        'r006',
                        'sumy',
                        'ye',
                    ]
                elif dm.simulation.flashType == 'RTFlame':
                    m.valueList[x] = [
                        'mass',
                        'x-momentum',
                        'y-momentum',
                        'z-momentum',
                        'E_total',
                        'E_kinetic',
                        'E_turbulent',
                        'E_internal',
                        'Burned Mass',
                        'dens_burning_ave',
                        'db_ave samplevol',
                        'Burning rate',
                        'fspd to input_fspd ratio',
                        'surface area flam=0.1',
                        'surface area flam=0.5',
                        'surface area flam=0.9',
                    ]

    @classmethod
    def flash_exe_basename(cls, data):
        return cls._flash_file_basename(
            cls._FLASH_EXE_PREFIX,
            data,
        )

    @classmethod
    def flash_simulation_unit_file_path(cls, run_dir, data, basename):
        return run_dir.join(cls.sim_type()).join(
            'source',
            'Simulation',
            'SimulationMain',
            data.models.simulation.flashType,
            basename,
        )

    @classmethod
    def flash_setup_units_basename(cls, data):
        return cls._flash_file_basename(cls._FLASH_SETUP_UNITS_PREFIX, data)

    @classmethod
    def proprietary_code_tarball(cls):
        return cls._proprietary_code_tarball()

    @classmethod
    def proprietary_code_lib_file_basenames(cls):
        return [
            'problemFiles-archive.CapLaser3D.zip',
            'problemFiles-archive.CapLaserBELLA.zip',
            cls._flash_src_tarball_basename(),
        ]

    @classmethod
    def sim_files_to_run_dir(cls, data, run_dir):
        try:
            super().sim_files_to_run_dir(data, run_dir)
        except sirepo.sim_data.SimDbFileNotFound:
            cls._flash_create_sim_files(data, run_dir)

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        return [r]

    @classmethod
    def _flash_create_sim_files(cls, data, run_dir):
        import sirepo.mpi
        import sirepo.template.flash
        import subprocess

        subprocess.check_output(
            [
                'tar',
                '--extract',
                '--gunzip',
                f'--file={cls._flash_src_tarball_basename()}',
                f'--directory={run_dir}',
            ],
            stderr=subprocess.STDOUT,
        )
        s = run_dir.join(cls.sim_type())
        if data.models.problemFiles.archive:
            for i, r in cls._flash_extract_problem_files_archive(
                    run_dir.join(cls._flash_problem_files_archive_basename(data)),
            ):
                b = pkio.py_path(i.filename).basename
                if not re.match(r'(\w+\.F90)|(Makefile)', b):
                    continue
                p = cls.flash_simulation_unit_file_path(run_dir, data, b)
                pkio.mkdir_parent_only(p)
                pkio.write_text(p, r())
        sirepo.template.flash.generate_config_file(run_dir, data)
        t = s.join(data.models.simulation.flashType)
        with run_dir.join(template_common.COMPILE_LOG).open('w') as log:
            k = PKDict(
                check=True,
                stdout=log,
                stderr=log
            )
            c = sirepo.template.flash.setup_command(data)
            pkdc('setup_command={}', ' '.join(c))
            subprocess.run(c, cwd=s, **k)
            subprocess.run(['make', f'-j{sirepo.mpi.cfg.cores}'], cwd=t, **k)
        for c, b in PKDict(
                # POSIT: values match cls._sim_file_basenames
                flash4=cls.flash_exe_basename(data),
                setup_units=cls.flash_setup_units_basename(data),
        ).items():
            p = t.join(c)
            cls.delete_sim_file(cls._flash_file_prefix(b), data)
            cls.put_sim_file(p, b, data)
            p.move(run_dir.join(b))

    @classmethod
    def _flash_extract_problem_files_archive(cls, path):
        with zipfile.ZipFile(path, 'r') as z:
            for i in z.infolist():
                yield i, lambda: z.read(i)

    @classmethod
    def _flash_file_basename(cls, prefix, data):
        return prefix + cls._FLASH_FILE_NAME_SEP + cls._flash_file_hash(data)

    @classmethod
    def _flash_file_hash(cls, data):
        def _remove_value_key(obj):
            r = PKDict(obj)
            r.pkdel('value')
            return r

        f = []
        if data.models.problemFiles.archive:
            f = [r() for _, r in cls._flash_extract_problem_files_archive(
                cls.lib_file_abspath(
                    cls._flash_problem_files_archive_basename(data),
                    data=data,
                ),
            )]
        return sirepo.util.url_safe_hash(str((
            data.models.simulation.flashType,
            data.models.setupArguments,
            f,
            list(map(_remove_value_key, data.models.setupConfigDirectives)),
        )))

    @classmethod
    def _flash_file_prefix(cls, basename):
        return basename.split(cls._FLASH_FILE_NAME_SEP)[0]

    @classmethod
    def _flash_problem_files_archive_basename(cls, data):
       return cls.lib_file_name_with_model_field(
           'problemFiles',
            'archive',
            data.models.problemFiles.archive,
       )

    @classmethod
    def _flash_src_tarball_basename(cls):
        return 'flash.tar.gz'

    @classmethod
    def _get_example_for_flash_type(cls, flash_type):
        for e in sirepo.simulation_db.examples(cls.sim_type()):
            if e.models.simulation.flashType == flash_type:
                return e
        raise AssertionError(f'no example with flash_type={flash_type}')

    @classmethod
    def _lib_file_basenames(cls, data):
        t = data.models.simulation.flashType
        r = [cls._flash_src_tarball_basename()]
        if data.models.problemFiles.archive:
            r.append(cls._flash_problem_files_archive_basename(data))
        if t == 'RTFlame':
            return r + ['helm_table.dat']
        if 'CapLaser' in t:
            r.extend([
                'alumina-wall-imx.cn4',
                'argon-fill-imx.cn4',
                'helium-fill-imx.cn4',
                'hydrogen-fill-imx.cn4',
            ])
            if t == 'CapLaserBELLA'  and data.models['SimulationCapLaserBELLA'].sim_currType == '2':
                r.append(cls.lib_file_name_with_model_field(
                    'SimulationCapLaserBELLA',
                    'sim_currFile',
                    data.models['SimulationCapLaserBELLA'].sim_currFile,
                ))
            return r
        raise AssertionError('invalid flashType: {}'.format(t))

    @classmethod
    def _sim_file_basenames(cls, data):
        return [
            PKDict(basename=cls.flash_exe_basename(data), is_exe=True),
            PKDict(basename=cls.flash_setup_units_basename(data)),
        ]

    @classmethod
    def __fixup_old_data_one_dimension_profile_animation(cls, data):
        dm = data.models
        if 'oneDimensionProfileAnimation' in dm:
            return
        dm.oneDimensionProfileAnimation = cls._get_example_for_flash_type(
            dm.simulation.flashType,
        ).models.oneDimensionProfileAnimation

    @classmethod
    def __fixup_old_data_problem_files(cls, data):
        dm = data.models
        if 'problemFiles' in dm:
            return
        f = None
        t = dm.simulation.flashType
        if 'CapLaser' in t:
            f = f'{t}.zip'
        dm.problemFiles = PKDict(archive=f)

    @classmethod
    def __fixup_old_data_setup_arguments(cls, data):
        dm = data.models
        if 'setupArguments' in dm:
            return
        dm.setupArguments = cls._get_example_for_flash_type(
            dm.simulation.flashType,
        ).models.setupArguments

    @classmethod
    def __fixup_old_data_setup_arguments_units(cls, data):
        if 'units' not in data.models.setupArguments:
            return
        i = max([d._id for d in data.models.setupConfigDirectives]) + 1
        for u in data.models.setupArguments.pkdel('units', []):
            data.models.setupConfigDirectives.append(PKDict(
                _id=i,
                _type="REQUIRES",
                unit=u
            ))
            i += 1

    @classmethod
    def __fixup_old_data_setup_config_directives(cls, data):
        if 'setupConfigDirectives'  in data.models:
            return
        e = cls._get_example_for_flash_type(data.models.simulation.flashType)
        data.models.setupConfigDirectives = e.models.setupConfigDirectives

    @classmethod
    def __fixup_old_data_var_animation_axis(cls, data):
        if 'axis' in data.models.varAnimation:
            return
        e = cls._get_example_for_flash_type(data.models.simulation.flashType)
        data.models.varAnimation.axis = e.models.varAnimation.axis
