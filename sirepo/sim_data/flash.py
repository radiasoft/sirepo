# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc
from sirepo.template import flash_parser
import re
import sirepo.mpi
import sirepo.sim_data
import sirepo.util
import subprocess
import zipfile


class SimData(sirepo.sim_data.SimDataBase):
    COMPILE_LOG = "compile.log"
    FLASH_PAR_FILE = "flash.par"
    SETUP_LOG = "setup.log"
    SETUP_PARAMS_SCHEMA_FILE = "setup_params.json"
    _FLASH_EXE_PREFIX = "flash_exe"
    _FLASH_FILE_NAME_SEP = "-"
    _FLASH_SRC_TARBALL_BASENAME = "flash.tar.gz"

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        dm = data.models
        cls._init_models(
            dm,
            (
                "animation",
                "gridEvolutionAnimation",
                "initZipReport",
                "oneDimensionProfileAnimation",
                "problemFiles",
                "setupAnimation",
                "setupArguments",
                "varAnimation",
            ),
        )

    @classmethod
    def flash_app_archive_basename(cls):
        return f"{cls.__flash_app_name()}.zip"

    @classmethod
    def flash_exe_basename(cls, data):
        return cls._FLASH_FILE_NAME_SEP.join(
            [
                cls._FLASH_EXE_PREFIX,
                sirepo.util.url_safe_hash(
                    str(
                        (
                            data.models.setupArguments,
                            data.models.problemFiles.filesHash,
                        )
                    )
                ),
            ]
        )

    @classmethod
    def flash_app_lib_basename(cls, sim_id):
        return f"{sim_id}.zip"

    @classmethod
    def flash_problem_files_archive_basename(cls, data):
        return cls.lib_file_name_with_model_field(
            "problemFiles",
            "archive",
            data.models.problemFiles.archive,
        )

    @classmethod
    def flash_problem_files_archive_hash(cls, path):
        return sirepo.util.url_safe_hash(
            str(
                [r() for _, r in cls.__extract_problem_files_archive(path)],
            )
        )

    @classmethod
    def flash_setup_command(cls, setup_args):
        def _integer(key, value):
            return f"-{key}={value}"

        def _shortcut(value):
            return f"+{value}"

        s = cls.schema()
        c = []
        for k, v in setup_args.items():
            if k == "units":
                for e in v:
                    c.append(f"--with-unit={e}")
                continue
            if k == "withParticles":
                if v == "1":
                    c.append(f"{k}=TRUE")
                continue
            if k not in s.model.setupArguments:
                continue
            t = s.model.setupArguments[k][1]
            if t == "SetupArgumentDimension":
                # always include the setup dimension
                c.append(f"-{v}d")
                continue
            if v == s.model.setupArguments[k][2]:
                continue
            if t == "Boolean":
                v == "1" and c.append(f"-{k}")
            elif t == "Integer":
                c.append(_integer(k, v))
            elif t == "NoDashInteger":
                c.append(f"{k}={v}")
            elif t == "OptionalInteger":
                # Do not move up to enclosing if.
                # We need to handle OptionalInteger even if v is falsey (no-op)
                if v:
                    c.append(_integer(k, v))
            elif t == "SetupArgumentGridGeometry":
                c.append(_shortcut(v))
            elif t == "SetupArgumentShortcut":
                v == "1" and c.append(_shortcut(k))
            elif t == "String" or t == "OptionalString":
                c.append(f"{k}={v}")
            else:
                raise AssertionError(f"type={t} not supported")
        return [
            "./setup",
            cls.__flash_app_name(),
            f"-objdir={cls.__flash_app_name()}",
        ] + c

    @classmethod
    def proprietary_code_lib_file_basenames(cls):
        return [
            cls._FLASH_SRC_TARBALL_BASENAME,
        ]

    @classmethod
    def proprietary_code_tarball(cls):
        return cls._proprietary_code_tarball()

    @classmethod
    def sim_files_to_run_dir(cls, data, run_dir):
        if data.report == "setupAnimation":
            super().sim_files_to_run_dir(data, run_dir)
            cls.__create_sim_files(data, run_dir)
            return
        try:
            super().sim_files_to_run_dir(data, run_dir)
        except Exception as e:
            if not pkio.exception_is_not_found(e):
                raise
            raise sirepo.util.UserAlert("Must first run Setup and Compile")

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if analysis_model == "setupAnimation":
            return analysis_model
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        if r == "initZipReport":
            # always compute initZipReport when asked
            return [[sirepo.util.random_base62()]]
        return [r]

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        r = data.get("report")
        if r == "initZipReport":
            if data.models.problemFiles.flashExampleName:
                res.append(cls._FLASH_SRC_TARBALL_BASENAME)
            else:
                res.append(cls.flash_problem_files_archive_basename(data))
        elif r == "setupAnimation":
            res.append(cls._FLASH_SRC_TARBALL_BASENAME)
            res.append(
                cls.flash_app_lib_basename(
                    data.models.simulation.simulationId,
                )
            )
        elif r is None:
            res.append(
                cls.flash_app_lib_basename(
                    data.models.problemFiles.archiveLibId,
                )
            )
        return res

    @classmethod
    def _sim_file_basenames(cls, data):
        r = data.get("report")
        if r == "initZipReport":
            return []
        if r == "setupAnimation":
            # return [PKDict(basename=cls.flash_app_archive_basename())]
            return []
        datafiles = data.models.flashSchema.enum.SetupDatafiles
        return [
            PKDict(basename=cls.flash_exe_basename(data), is_exe=True),
            # PKDict(basename=cls.flash_app_archive_basename()),
        ] + [
            PKDict(
                {
                    "basename": v,
                }
            )
            for v in [f[0] for f in datafiles]
        ]

    @classmethod
    def __create_schema(cls, data, make_dir, run_dir):
        res = PKDict(
            flashSchema=flash_parser.SetupParameterParser(
                run_dir.join(cls.sim_type(), cls.__flash_app_name()),
            ).generate_schema()
        )
        if not data.models.get("Driver_DriverMain"):
            # no initial models, set from flash.par if present
            par_path = make_dir.join(cls.FLASH_PAR_FILE)
            if par_path.exists():
                data.models.flashSchema = res.flashSchema
                res.parValues = flash_parser.ParameterParser().parse(
                    data,
                    pkio.read_text(par_path),
                )
        pkio.write_text(
            run_dir.join(cls.SETUP_PARAMS_SCHEMA_FILE),
            pkjson.dump_pretty(res),
        )
        return res

    @classmethod
    def __create_sim_files(cls, data, run_dir):
        cls.__untar_flash_src(run_dir)
        make_dir = cls.__run_setup(data, run_dir)
        s = cls.__create_schema(data, make_dir, run_dir)
        cls.__run_make(make_dir)
        cls.__delete_flash_exe(data)
        cls.__put_sim_files(data, s.flashSchema.enum.SetupDatafiles, make_dir, run_dir)

    @classmethod
    def __delete_flash_exe(cls, data):
        """Delete the flash executable if it exists

        The executables are named like _FLASH_EXE_PREFIX_<unique-hash>.
        They have a hash so we know when we need to recreate the executable
        based on the user changing parameters.

        sirepo.sim_db_file delete does a glob of the filename to delete. So, we
        will delete any file that starts with _FLASH_EXE_PREFIX
        """
        cls.sim_db_client().delete_glob(
            data.models.simulation.simulationId,
            cls._FLASH_EXE_PREFIX,
        )

    @classmethod
    def __extract_problem_files_archive(cls, path):
        with zipfile.ZipFile(path, "r") as z:
            for i in z.infolist():
                yield i, lambda: z.read(i)

    @classmethod
    def __flash_app_name(cls):
        return cls.schema().constants.flashAppName

    @classmethod
    def __flash_unit_file_path(cls, run_dir, data, basename):
        return run_dir.join(cls.sim_type()).join(
            "source",
            "Simulation",
            "SimulationMain",
            cls.__flash_app_name(),
            basename,
        )

    @classmethod
    def __put_sim_files(cls, data, datafiles, make_dir, run_dir):
        for c, b in (
            PKDict({v: v for v in [f[0] for f in datafiles]})
            .pkupdate(
                flash4=cls.flash_exe_basename(data),
            )
            .items()
        ):
            p = make_dir.join(c)
            cls.put_sim_file(data.models.simulation.simulationId, p, b)
            if p.check(link=1):
                p.copy(run_dir.join(b))
            else:
                p.move(run_dir.join(b))

    @classmethod
    def __run_command_and_parse_log_on_error(
        cls,
        command,
        work_dir,
        log_file,
        err_subject,
        regex,
    ):
        p = pkio.py_path(log_file)
        with pkio.open_text(p.ensure(), mode="r+") as l:
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
                m = [
                    x.group().strip()
                    for x in re.finditer(
                        regex,
                        c,
                        re.MULTILINE,
                    )
                ]
                if m:
                    r = "\n".join(m)
                else:
                    r = c.splitlines()[-1]
                raise sirepo.util.UserAlert(f"FLASH {err_subject} Error:\n{r}", "{}", e)

    @classmethod
    def __run_make(cls, make_dir):
        cls.__run_command_and_parse_log_on_error(
            ["make", f"-j{sirepo.mpi.cfg().cores}"],
            make_dir,
            cls.COMPILE_LOG,
            "Compile",
            r"^(?:Error): (.*)",
        )

    @classmethod
    def __run_setup(cls, data, run_dir):
        d = []
        for i, r in cls.__extract_problem_files_archive(
            run_dir.join(
                cls.flash_app_lib_basename(
                    data.models.simulation.simulationId,
                )
            ),
        ):
            b = pkio.py_path(i.filename).basename
            p = cls.__flash_unit_file_path(run_dir, data, b)
            pkio.mkdir_parent_only(p)
            t = r()
            try:
                pkio.write_text(p, t)
            except UnicodeDecodeError:
                with open(p, "wb") as f:
                    f.write(t)
            d.append(p.basename)
        c = cls.flash_setup_command(data.models.setupArguments)
        pkdc("setup_command={}", " ".join(c))
        s = run_dir.join(cls.sim_type())
        cls.__run_command_and_parse_log_on_error(
            c,
            s,
            cls.SETUP_LOG,
            "Setup",
            r"(.*PPDEFINE.*$)|(^\s+\*.*$(\n\w+.*)?)",
        )
        return s.join(cls.__flash_app_name())

    @classmethod
    def __untar_flash_src(cls, run_dir):
        subprocess.check_output(
            [
                "tar",
                "--extract",
                "--gunzip",
                f"--file={cls._FLASH_SRC_TARBALL_BASENAME}",
                f"--directory={run_dir}",
            ],
            stderr=subprocess.STDOUT,
        )
