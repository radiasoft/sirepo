# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc
from sirepo.template import flash_parser
from sirepo.template import template_common
import re
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.util
import subprocess
import zipfile

class SimData(sirepo.sim_data.SimDataBase):


    SETUP_PARAMS_SCHEMA_FILE = 'setup_params.json'
    _COMPILE_LOG = 'compile.log'
    _SETUP_LOG = 'setup.log'
    _FLASH_EXE_PREFIX = 'flash_exe'
    _FLASH_FILE_NAME_SEP = '-'

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        for m in ('setupArguments',):
            cls.update_model_defaults(dm[m], m)

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
            cls.schema().constants.flashAppName,
            basename,
        )

    @classmethod
    def proprietary_code_tarball(cls):
        return cls._proprietary_code_tarball()

    @classmethod
    def proprietary_code_lib_file_basenames(cls):
        return [
            # 'problemFiles-archive.CapLaser3D.zip',
            # 'problemFiles-archive.CapLaserBELLA.zip',
            cls._flash_src_tarball_basename(),
        ]

    @classmethod
    def sim_files_to_run_dir(cls, data, run_dir):
        if data.report == 'setupAnimation':
            cls._flash_create_sim_files(data, run_dir)
            return
        try:
            super().sim_files_to_run_dir(data, run_dir)
        except sirepo.sim_data.SimDbFileNotFound:
            cls._flash_create_sim_files(data, run_dir)

    @classmethod
    def _add_default_views(cls, flashSchema):
        flashSchema.view.Driver.basic = [
            'tmax',
            'dtinit',
            'IO.plotFileIntervalTime',
            'allowDtSTSDominate',
        ]

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if analysis_model == 'setupAnimation':
            return analysis_model
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        if r == 'setupAnimation' or r == 'animation':
            return ['setupConfigDirectives', 'setupArguments']
        return [r]

    @classmethod
    def _flash_create_sim_files(cls, data, run_dir):
        import sirepo.mpi
        import sirepo.template.flash

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
        d = []
        if data.models.problemFiles.archive:
            for i, r in cls._flash_extract_problem_files_archive(
                    run_dir.join(cls._flash_problem_files_archive_basename(data)),
            ):
                b = pkio.py_path(i.filename).basename
                #TODO(pjm): zip file also includes required datafiles
                # if not re.match(r'(\w+\.F90)|(Makefile)', b):
                #     continue
                p = cls.flash_simulation_unit_file_path(run_dir, data, b)
                pkio.mkdir_parent_only(p)
                pkio.write_text(p, r())
                d.append(p.basename)
        cls._flash_check_datafiles(data, d)
        sirepo.template.flash.generate_config_file(run_dir, data)
        t = s.join(cls.schema().constants.flashAppName)
        c = sirepo.template.flash.setup_command(data)
        pkdc('setup_command={}', ' '.join(c))
        cls._flash_run_command_and_pare_log_on_error(
            c,
            s,
            cls._SETUP_LOG,
            r'.*PPDEFINE.*$',
        )
        flash_schema = flash_parser.SetupParameterParser(
            run_dir.join(cls.sim_type(), cls.schema().constants.flashAppName)
        ).generate_schema()
        cls._add_default_views(flash_schema)
        pkio.write_text(
            run_dir.join(cls.SETUP_PARAMS_SCHEMA_FILE),
            pkjson.dump_pretty(PKDict(
                flashSchema=flash_schema,
            ))
        )
        datafiles = flash_schema.enum.SetupDatafiles
        cls._flash_run_command_and_pare_log_on_error(
            ['make', f'-j{sirepo.mpi.cfg.cores}'],
            t,
            cls._COMPILE_LOG,
            r'^(?:Error): (.*)',
        )
        for c, b in PKDict({
            v: v for v in [f[0] for f in datafiles]
        }).pkupdate(
            # POSIT: values match cls._sim_file_basenames
            flash4=cls.flash_exe_basename(data),
        ).items():
            p = t.join(c)
            cls.delete_sim_file(cls._flash_file_prefix(b), data)
            cls.put_sim_file(p, b, data)
            if p.check(link=1):
                p.copy(run_dir.join(b))
            else:
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
            data.models.simulation.name,
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
    def _flash_run_command_and_pare_log_on_error(
            cls,
            command,
            work_dir,
            log_file,
            regex,
    ):
        p = pkio.py_path(log_file)
        with pkio.open_text(p.ensure(), mode='r+') as l:
            try:
                subprocess.run(
                    command,
                    check=True,
                    cwd=work_dir,
                    stderr=l,
                    stdout=l,
                )
            except subprocess.CalledProcessError as e:
                l.seek(0)
                c = l.read()
                m = re.findall(regex, c, re.MULTILINE)
                if m:
                    r = ', '.join(m)
                else:
                    r = c.splitlines()[-1]
                raise sirepo.util.UserAlert(
                    r,
                    '{}',
                    e
                )

    @classmethod
    def _flash_src_tarball_basename(cls):
        return 'flash.tar.gz'

    @classmethod
    def _flash_check_datafiles(cls, data, filenames):
        e = []
        for d in data.models.setupConfigDirectives:
            if d._type != 'DATAFILES':
                continue
            if d.wildcard not in filenames:
                e.append(d.wildcard)
        if e:
            raise sirepo.util.UserAlert(
                f'{e} missing from supplied datafiles {filenames}'
            )

    @classmethod
    def _lib_file_basenames(cls, data):
        r = [cls._flash_src_tarball_basename()]
        if data.models.problemFiles.archive:
            r.append(cls._flash_problem_files_archive_basename(data))
        return r

    @classmethod
    def _sim_file_basenames(cls, data):
        datafiles = data.models.flashSchema.enum.SetupDatafiles
        return [
            PKDict(basename=cls.flash_exe_basename(data), is_exe=True),
        ] + [
            PKDict({
                'basename': v,
            })  for v in [f[0] for f in datafiles]
        ]
