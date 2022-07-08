# -*- coding: utf-8 -*-
"""Flash Config parser.

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp, pkdlog
import inspect
import re


def _fields(templates, values):
    # template: [field template, label template]
    # values: values to insert into the field/label templates
    return {t[0].format(v): t[1].format(v.upper()) for v in values for t in templates}


def _sim_fields(schema, model_name, fields):
    # any model field may be overtaken by the main simulation Config
    n = "Simulation_SimulationMain_flashApp"
    res = []
    for f in fields:
        if n in schema.model and f in schema.model[n]:
            res.append(f"{n}.{f}")
        else:
            res.append(f"{model_name}.{f}")
    return res


class SpecializedViews:
    # POSIT: FLASH field names are unique so flat list is ok
    _LABELS = PKDict(
        LimitedSlopeBeta="Limited Slope Beta",
        RiemannSolver="Riemann Solver",
        UnitSystem="System of Units",
        allowDtSTSDominate="allowDtSTSDominate",
        cfl="Courant Factor",
        charLimiting="Characteristic Limiting",
        cvisc="Artificial Viscosity Constant",
        diff_eleFlCoef="Flux Limiter Coefficient",
        diff_eleXlBoundaryType="X Left Boundary",
        diff_eleXrBoundaryType="X Right Boundary",
        diff_eleYlBoundaryType="Y Left Boundary",
        diff_eleYrBoundaryType="Y Right Boundary",
        diff_eleZlBoundaryType="Z Left Boundary",
        diff_eleZrBoundaryType="Z Right Boundary",
        diff_thetaImplct="Implicitness Factor",
        diff_useEleCond="Use Ele Conduction",
        dt_diff_factor="Timestep Factor",
        dtinit="Initial Timestep [s]",
        dtmax="Maximum Timestep",
        dtmin="Minimum Timestep",
        ed_crossSectionFunctionType_1="Cross Section Function Type",
        ed_gaussianCenterMajor_1="Major Gaussian Center",
        ed_gaussianCenterMinor_1="Minor Gaussian Center",
        ed_gaussianExponent_1="Gaussian Exponent",
        ed_gaussianRadiusMajor_1="Major Gaussian Radius",
        ed_gaussianRadiusMinor_1="Minor Gaussian Radius",
        ed_gradOrder="Gradient Order",
        ed_gridType_1="Type of Beam Grid",
        ed_laser3Din2D="3D Ray Tracing",
        ed_laser3Din2DwedgeAngle="Wedge Angle",
        ed_laserIOMaxNumberOfPositions="Max Ray Positions",
        ed_laserIOMaxNumberOfRays="Max Rays",
        ed_lensSemiAxisMajor_1="Lens Semi Axis Major",
        ed_lensX_1="Lens X",
        ed_lensY_1="Lens Y",
        ed_lensZ_1="Lens Z",
        ed_maxRayCount="Max Ray Count",
        ed_numberOfBeams="Number of Beams",
        ed_numberOfPulses="Number of Pulses",
        ed_numberOfRays_1="Number of Rays",
        ed_numberOfSections_1="Number of Sections",
        ed_power_1_1="Laser Pulse Section 1",
        ed_power_1_2="Laser Pulse Section 2",
        ed_power_1_3="Laser Pulse Section 3",
        ed_power_1_4="Laser Pulse Section 4",
        ed_pulseNumber_1="Pulse Number",
        ed_semiAxisMajorTorsionAngle_1="Major Semiaxis Torsion Angle",
        ed_semiAxisMajorTorsionAxis_1="Major Semiaxis Torsion Axis",
        ed_targetSemiAxisMajor_1="Major Target Semiaxis",
        ed_targetSemiAxisMinor_1="Minor Target Semiaxis",
        ed_targetX_1="X Target",
        ed_targetY_1="Y Target",
        ed_targetZ_1="Z Target",
        ed_time_1_1="Laser Pulse Section 1",
        ed_time_1_2="Laser Pulse Section 2",
        ed_time_1_3="Laser Pulse Section 3",
        ed_time_1_4="Laser Pulse Section 4",
        ed_useLaserIO="Use Laser IO",
        ed_wavelength_1="Wavelength",
        entropy="Entropy Fix",
        eosMode="Eos Mode",
        eosModeInit="Initial Eos Mode",
        fl_b="Flame Width",
        fl_epsilon_0="Lower Sharpening Factor",
        fl_epsilon_1="Upper Sharpening Factor",
        fl_fsConstFlameSpeed="Constant Flame Speed",
        fl_kpp_fact="Prefactor Adjustment",
        flame_deltae="Flame Delta e",
        gconst="Acceleration Constant",
        gdirec="Direction of Acceleration",
        geometry="Grid Geometry",
        grav_boundary_type="Boundary Condition",
        lrefine_max="Maximum Refinement Level",
        lrefine_min="Minimum Refinement Level",
        nend="Maximum Number of Timesteps",
        order="Order",
        plotFileIntervalTime="Plot File Interval Time [s]",
        refine_var_count="Refine Variable Count",
        rt_dtFactor="Time Step Coefficient",
        rt_mgdBounds_1="Boundary 1",
        rt_mgdBounds_2="Boundary 2",
        rt_mgdBounds_3="Boundary 3",
        rt_mgdBounds_4="Boundary 4",
        rt_mgdBounds_5="Boundary 5",
        rt_mgdBounds_6="Boundary 6",
        rt_mgdBounds_7="Boundary 7",
        rt_mgdFlCoef="MGD Flux Limiter Coefficient",
        rt_mgdFlMode="MGD Glux Limiter Mode",
        rt_mgdNumGroups="Number of Groups",
        rt_mgdXlBoundaryType="X MGD Left Boundary",
        rt_mgdXrBoundaryType="X MGD Right Boundary",
        rt_mgdYlBoundaryType="Y MGD Left Boundary",
        rt_mgdYrBoundaryType="Y MGD Right Boundary",
        rt_mgdZlBoundaryType="Z MGD Left Boundary",
        rt_mgdZrBoundaryType="Z MGD Right Boundary",
        rt_useMGD="Use Multigroup Radiation Diffusion",
        shockDetect="Use Strong Compressive Shock Detection",
        slopeLimiter="Slope Limiter",
        sumyi_burned="Burned sumyi",
        sumyi_unburned="Unburned sumyi",
        threadHydroBlockList="Block List Threading",
        threadHydroWithinBlock="Within Block Threading",
        tmax="Maximum Simulation Time [s]",
        updateHydroFluxes="Update Hydro Fluxes",
        useDiffuse="Use Diffusive Effects",
        useEnergyDeposition="Use Energy Deposition",
        useFlame="Use Flame",
        useGravity="Use Gravity",
        useHydro="Use Hydro Calculation",
        useRadTrans="Use Radiative Transfer",
        use_cma_advection="Use CMA Advection",
        use_cma_flattening="Use CMA Flattening",
        ye_burned="Burned ye",
        ye_unburned="Unburned ye",
        **_fields(
            [
                ["{}l_boundary_type", "{} Lower Boundary Type"],
                ["{}r_boundary_type", "{} Upper Boundary Type"],
                ["{}min", "{} Minimum"],
                ["{}max", "{} Maximum"],
                ["nblock{}", "Blocks in {}"],
            ],
            ["x", "y", "z"],
        ),
        **_fields(
            [
                ["refine_var_{}", "Name Variable {}"],
                ["refine_cutoff_{}", "Refine Variable {}"],
                ["derefine_cutoff_{}", "Derefine Variable {}"],
            ],
            [str(v) for v in range(1, 7)],
        ),
    )

    _VIEW_FUNC_PREFIX = "_view_"

    def __init__(self):
        self._view_fns = PKDict()
        for n, o in inspect.getmembers(self):
            if n.startswith(self._VIEW_FUNC_PREFIX) and inspect.ismethod(o):
                self._view_fns[n[len(self._VIEW_FUNC_PREFIX) :]] = o

    def update_schema(self, schema):
        self._update_labels(schema)
        self._update_views(schema)
        return schema

    def _assert_model_view_fields_exist(self, name, view, schema):
        """Check that model fields in view exist in models"""

        def flatten(to_flatten):
            def flatten_column(to_flatten):
                if isinstance(to_flatten[0], str):
                    return flatten(to_flatten[1])
                res = []
                for f in to_flatten:
                    res += flatten_column(f)
                return res

            res = []
            for f in to_flatten:
                if isinstance(f, str):
                    res.append(f)
                    continue
                assert isinstance(f, list), "uknown type f={f}"
                res += flatten_column(f)
            return res

        for f in flatten(view.get("basic", []) + view.get("advanced", [])):
            if "." not in f:
                f = f"{name}.{f}"
            p = f.split(".")
            assert (
                p[0] in schema.model
            ), f"model name={p[0]} does not exist in known models={schema.model.keys()}"
            assert (
                p[1] in schema.model[p[0]]
            ), f"field={p[1]} name={p[0]} does not exist in model={schema.model[p[0]]}"

    def _get_species_list(self, schema):
        res = []
        for f in schema.model.Multispecies_MultispeciesMain:
            m = re.search(r"eos_(.*)EosType", f)
            if m:
                res.append(m.group(1))
        return res

    def _update_labels(self, schema):
        labels = self._LABELS.copy()
        self._update_sim_labels(schema, labels)
        self._update_multispecies_labels(schema, labels)
        for m in schema.model.values():
            for f in m:
                if f not in labels:
                    continue
                info = m[f]
                if len(info) == 3:
                    info.append(f)
                elif info[3]:
                    info[3] = "{} {}".format(f, info[3])
                else:
                    info[3] = f
                info[0] = labels[f]

    def _update_multispecies_labels(self, schema, labels):
        if "Multispecies_MultispeciesMain" not in schema.model:
            return
        for s in self._get_species_list(schema):
            for f, label in {
                "ms_{}A": "Number of protons and neutrons in nucleus",
                "ms_{}Z": "Atomic number",
                "ms_{}ZMin": "Minimum allowed average ionization",
                "eos_{}EosType": "EOS type to use for MTMMMT EOS",
                "eos_{}SubType": "EOS subtype to use for MTMMMT EOS",
                "ms_{}Gamma": "Ratio of heat capacities",
                "eos_{}TableFile": "Tabulated EOS file name",
                "op_{}Absorb": "Absorption",
                "op_{}Emiss": "Emission",
                "op_{}Trans": "Transport",
            }.items():
                labels[f.format(s)] = f"{s.title()} {label}"

    def _update_sim_labels(self, schema, labels):
        # TODO(pjm): use constant for flashApp model
        # special case for main simulation labels - use full description as label
        for f, info in schema.model.Simulation_SimulationMain_flashApp.items():
            if len(info) > 3:
                labels[f] = info[3]
                info[3] = ""

    def _update_views(self, schema):
        for n, f in self._view_fns.items():
            if n not in schema.view:
                continue
            v = f(schema)
            if v:
                self._assert_model_view_fields_exist(n, v, schema)
                schema.view[n].update(v)

    def _view_Driver_DriverMain(self, schema):
        # http://flash.uchicago.edu/site/flashcode/user_support/rpDoc_4p2.py?submit=rp_Driver.txt
        v = PKDict(
            title="Simulation Driver",
            advanced=[
                [
                    "Driver",
                    [
                        "dr_abortPause",
                        "dr_dtMinBelowAction",
                        "dr_dtMinContinue",
                        "dr_numPosdefVars",
                        "dr_posdefDtFactor",
                        "dr_posdefVar_1",
                        "dr_posdefVar_2",
                        "dr_posdefVar_3",
                        "dr_posdefVar_4",
                        "dr_printTStepLoc",
                        "dr_shortenLastStepBeforeTMax",
                        "dr_tstepSlowStartFactor",
                        "dr_usePosdefComputeDt",
                    ],
                ],
                [
                    "Drift",
                    [
                        "drift_break_inst",
                        "drift_trunc_mantissa",
                        "drift_tuples",
                        "drift_verbose_inst",
                    ],
                ],
                [
                    "Time",
                    [
                        "wall_clock_time_limit",
                        "tinitial",
                    ],
                ],
                [
                    "Timestep",
                    [
                        "tstep_change_factor",
                        "nbegin",
                        "nend",
                        "useSTS",
                        "useSTSforDiffusion",
                        "nuSTS",
                        "nstepTotalSTS",
                    ],
                ],
                [
                    "Thread",
                    [
                        "threadBlockListBuild",
                        "threadDriverBlockList",
                        "threadDriverWithinBlock",
                        "threadRayTraceBuild",
                        "threadWithinBlockBuild",
                    ],
                ],
                [
                    "Redshift",
                    [
                        "zInitial",
                        "zFinal",
                    ],
                ],
                [
                    "Other",
                    [
                        "meshCopyCount",
                        "sweepOrder",
                    ],
                ],
            ],
            basic=[
                "tmax",
                "dtinit",
                "nend",
                "allowDtSTSDominate",
            ],
        )
        if "IO_IOMain" in schema.model:
            v.basic.append("IO_IOMain.plotFileIntervalTime")
        return v

    def _view_physics_Diffuse_DiffuseMain(self, schema):
        # http://flash.uchicago.edu/site/flashcode/user_support/rpDoc_4p2.py?submit=rp_Diffuse.txt
        v = PKDict(
            title="Diffusive Effects",
            basic=[
                "diff_eleFlMode",
                "diff_eleFlCoef",
                "dt_diff_factor",
                [
                    [
                        "X",
                        [
                            "diff_eleXlBoundaryType",
                            "diff_eleXrBoundaryType",
                        ],
                    ],
                    [
                        "Y",
                        [
                            "diff_eleYlBoundaryType",
                            "diff_eleYrBoundaryType",
                        ],
                    ],
                    [
                        "Z",
                        [
                            "diff_eleZlBoundaryType",
                            "diff_eleZrBoundaryType",
                        ],
                    ],
                ],
            ],
        )
        if "physics_Diffuse_DiffuseMain_Unsplit" in schema.model:
            v.basic.insert(3, "physics_Diffuse_DiffuseMain_Unsplit.diff_thetaImplct")
        if "physics_Diffuse_DiffuseMain" in schema.model:
            v.basic.insert(0, "physics_Diffuse_DiffuseMain.diff_useEleCond")
            v.basic.insert(0, "physics_Diffuse_DiffuseMain.useDiffuse")
        return v

    def _view_physics_Gravity_GravityMain(self, schema):
        # http://flash.uchicago.edu/site/flashcode/user_support/rpDoc_4p2.py?submit=rp_Gravity.txt
        v = PKDict(
            basic=[
                "useGravity",
            ],
        )
        if "physics_Gravity" in schema.model:
            # Flash docs seem to be wrong. useGravity does not exist in
            # physics/Gravity. Just physics/Gravity/GravityMain
            v.basic.insert(1, "physics_Gravity.grav_boundary_type")
        if "physics_Gravity_GravityMain_Constant" in schema.model:
            v.basic.extend(
                [
                    "physics_Gravity_GravityMain_Constant.gconst",
                    "physics_Gravity_GravityMain_Constant.gdirec",
                ]
            )
        return v

    def _view_Grid_GridMain(self, schema):
        # http://flash.uchicago.edu/site/flashcode/user_support/rpDoc_4p2.py?submit=rp_Grid.txt
        v = PKDict(
            title="Grid",
            basic=[
                [
                    "Main",
                    [
                        "geometry",
                        "eosModeInit",
                        "eosMode",
                        [
                            [
                                "X",
                                [
                                    "xl_boundary_type",
                                    "xr_boundary_type",
                                    "xmin",
                                    "xmax",
                                ],
                            ],
                            [
                                "Y",
                                [
                                    "yl_boundary_type",
                                    "yr_boundary_type",
                                    "ymin",
                                    "ymax",
                                ],
                            ],
                            [
                                "Z",
                                [
                                    "zl_boundary_type",
                                    "zr_boundary_type",
                                    "zmin",
                                    "zmax",
                                ],
                            ],
                        ],
                    ],
                ],
            ],
        )
        if "Grid_GridMain_paramesh" in schema.model:
            v.basic.append(
                [
                    "Paramesh",
                    [
                        "Grid_GridMain_paramesh.nblockx",
                        "Grid_GridMain_paramesh.nblocky",
                        "Grid_GridMain_paramesh.nblockz",
                        "Grid_GridMain_paramesh.lrefine_min",
                        "Grid_GridMain_paramesh.lrefine_max",
                        "Grid_GridMain_paramesh.refine_var_count",
                        [
                            [
                                "Name",
                                [
                                    # TODO(pjm): this should apply to all view fields
                                    #  fields may be defined on main flash app module
                                    *_sim_fields(
                                        schema,
                                        "Grid_GridMain_paramesh",
                                        [
                                            "refine_var_1",
                                            "refine_var_2",
                                            "refine_var_3",
                                            "refine_var_4",
                                        ],
                                    ),
                                ],
                            ],
                            [
                                "Refine Cutoff",
                                [
                                    "Grid_GridMain_paramesh.refine_cutoff_1",
                                    "Grid_GridMain_paramesh.refine_cutoff_2",
                                    "Grid_GridMain_paramesh.refine_cutoff_3",
                                    "Grid_GridMain_paramesh.refine_cutoff_4",
                                ],
                            ],
                            [
                                "Derefine Cutoff",
                                [
                                    "Grid_GridMain_paramesh.derefine_cutoff_1",
                                    "Grid_GridMain_paramesh.derefine_cutoff_2",
                                    "Grid_GridMain_paramesh.derefine_cutoff_3",
                                    "Grid_GridMain_paramesh.derefine_cutoff_4",
                                ],
                            ],
                        ],
                    ],
                ],
            )
        return v

    def _view_physics_Hydro_HydroMain(self, schema):
        # http://flash.uchicago.edu/site/flashcode/user_support/rpDoc_4p2.py?submit=rp_Hydro.txt
        v = PKDict(
            title="Hydrodynamics",
            basic=[
                "useHydro",
                "cfl",
            ],
            fieldsPerTab=10,
        )
        if "physics_Hydro_HydroMain_unsplit" in schema.model:
            v.basic.extend(
                [
                    "physics_Hydro_HydroMain_unsplit.order",
                    "physics_Hydro_HydroMain_unsplit.slopeLimiter",
                    "physics_Hydro_HydroMain_unsplit.LimitedSlopeBeta",
                    "physics_Hydro_HydroMain_unsplit.charLimiting",
                    "physics_Hydro_HydroMain_unsplit.cvisc",
                    "physics_Hydro_HydroMain_unsplit.RiemannSolver",
                    "physics_Hydro_HydroMain_unsplit.entropy",
                    "physics_Hydro_HydroMain_unsplit.shockDetect",
                ]
            )
        return v

    def _view_physics_materialProperties_Opacity_OpacityMain_Multispecies(self, schema):
        v = PKDict(title="Material Properties", basic=[])
        if "physics_materialProperties_Opacity_OpacityMain" in schema.model:
            v.basic.append("physics_materialProperties_Opacity_OpacityMain.useOpacity")
        if "physics_materialProperties_Conductivity_ConductivityMain" in schema.model:
            v.basic.append(
                "physics_materialProperties_Conductivity_ConductivityMain.useConductivity"
            )
        if (
            "physics_materialProperties_MagneticResistivity_MagneticResistivityMain"
            in schema.model
        ):
            v.basic.append(
                "physics_materialProperties_MagneticResistivity_MagneticResistivityMain.useMagneticResistivity"
            )
        v.basic.append([])
        for s in self._get_species_list(schema):
            v.basic[-1].append(
                [
                    s.title(),
                    [
                        f"physics_materialProperties_Opacity_OpacityMain_Multispecies.op_{s}Absorb",
                        f"physics_materialProperties_Opacity_OpacityMain_Multispecies.op_{s}Emiss",
                        f"physics_materialProperties_Opacity_OpacityMain_Multispecies.op_{s}Trans",
                    ],
                ],
            )
        return v

    def _view_Multispecies_MultispeciesMain(self, schema):
        v = PKDict(
            title="Multispecies",
            basic=[
                [],
            ],
        )
        for s in self._get_species_list(schema):
            v.basic[-1].append(
                [
                    s.title(),
                    [
                        f"ms_{s}A",
                        f"ms_{s}Z",
                        f"ms_{s}ZMin",
                        f"eos_{s}EosType",
                        f"eos_{s}SubType",
                        f"eos_{s}TableFile",
                    ],
                ],
            )
        return v

    def _view_physics_RadTrans_RadTransMain_MGD(self, schema):
        # http://flash.uchicago.edu/site/flashcode/user_support/rpDoc_4.py?submit=rp_RadTrans.txt
        v = PKDict(
            title="Radiative Transfer",
            basic=[
                [
                    "Main",
                    [
                        "rt_useMGD",
                        "rt_mgdFlMode",
                        "rt_mgdFlCoef",
                        [
                            [
                                "X",
                                [
                                    "rt_mgdXlBoundaryType",
                                    "rt_mgdXrBoundaryType",
                                ],
                            ],
                            [
                                "Y",
                                [
                                    "rt_mgdYlBoundaryType",
                                    "rt_mgdYrBoundaryType",
                                ],
                            ],
                            [
                                "Z",
                                [
                                    "rt_mgdZlBoundaryType",
                                    "rt_mgdZrBoundaryType",
                                ],
                            ],
                        ],
                    ],
                ],
                [
                    "MGD Groups",
                    [
                        "rt_mgdNumGroups",
                        "rt_mgdBounds_1",
                        "rt_mgdBounds_2",
                        "rt_mgdBounds_3",
                        "rt_mgdBounds_4",
                        "rt_mgdBounds_5",
                        "rt_mgdBounds_6",
                        "rt_mgdBounds_7",
                    ],
                ],
            ],
        )
        if "physics_RadTrans_RadTransMain" in schema.model:
            v.basic[0][1].insert(0, "physics_RadTrans_RadTransMain.rt_dtFactor")
            v.basic[0][1].insert(0, "physics_RadTrans_RadTransMain.useRadTrans")
        return v

    def _view_physics_sourceTerms_EnergyDeposition_EnergyDepositionMain_Laser(
        self, schema
    ):
        # http://flash.uchicago.edu/site/flashcode/user_support/rpDoc_4p22.py?submit=rp_EnergyDeposition.txt
        v = PKDict(
            title="Energy Deposition - Laser",
            basic=[
                [
                    "Bulk",
                    [
                        "useEnergyDeposition",
                        "ed_maxRayCount",
                        "ed_gradOrder",
                        "ed_laser3Din2D",
                        "ed_laser3Din2DwedgeAngle",
                        "physics_sourceTerms_EnergyDeposition_EnergyDepositionMain_Laser_LaserIO.ed_useLaserIO",
                        "physics_sourceTerms_EnergyDeposition_EnergyDepositionMain_Laser_LaserIO.ed_laserIOMaxNumberOfPositions",
                        "physics_sourceTerms_EnergyDeposition_EnergyDepositionMain_Laser_LaserIO.ed_laserIOMaxNumberOfRays",
                    ],
                ],
                [
                    "Pulse 1",
                    [
                        "ed_numberOfPulses",
                        "ed_numberOfSections_1",
                        [
                            [
                                "Time",
                                [
                                    "ed_time_1_1",
                                    "ed_time_1_2",
                                    "ed_time_1_3",
                                    "ed_time_1_4",
                                ],
                            ],
                            [
                                "Power",
                                [
                                    "ed_power_1_1",
                                    "ed_power_1_2",
                                    "ed_power_1_3",
                                    "ed_power_1_4",
                                ],
                            ],
                        ],
                    ],
                ],
                [
                    "Beam 1",
                    [
                        [
                            [
                                "X",
                                [
                                    "ed_lensX_1",
                                    "ed_targetX_1",
                                ],
                            ],
                            [
                                "Y",
                                [
                                    "ed_lensY_1",
                                    "ed_targetY_1",
                                ],
                            ],
                            [
                                "Z",
                                [
                                    "ed_lensZ_1",
                                    "ed_targetZ_1",
                                ],
                            ],
                        ],
                        "ed_numberOfBeams",
                        "ed_lensSemiAxisMajor_1",
                        "ed_crossSectionFunctionType_1",
                        "ed_numberOfRays_1",
                        "ed_pulseNumber_1",
                        "ed_wavelength_1",
                        "ed_gridType_1",
                        "ed_gridnRadialTics_1",
                        "ed_gaussianExponent_1",
                        [
                            [
                                "Major",
                                [
                                    "ed_gaussianRadiusMajor_1",
                                    "ed_gaussianCenterMajor_1",
                                    "ed_targetSemiAxisMajor_1",
                                    "ed_semiAxisMajorTorsionAngle_1",
                                    "ed_semiAxisMajorTorsionAxis_1",
                                ],
                            ],
                            [
                                "Minor",
                                [
                                    "ed_gaussianRadiusMinor_1",
                                    "ed_gaussianCenterMinor_1",
                                    "ed_targetSemiAxisMinor_1",
                                ],
                            ],
                        ],
                    ],
                ],
            ],
        )
        return v

    def _view_physics_sourceTerms_Flame_FlameMain(self, schema):
        # TODO(e-carlin): add _LABELS for things
        # http://flash.uchicago.edu/site/flashcode/user_support/rpDoc_4p2.py?submit=rp_Flame.txt
        v = PKDict(
            basic=[
                "useFlame",
                "fl_epsilon_0",
                "fl_epsilon_1",
                "fl_kpp_fact",
                "fl_b",
            ],
        )
        if "physics_sourceTerms_Flame_FlameEffects_EIP" in schema.model:
            v.basic.extend(
                [
                    [
                        [
                            "Unburned",
                            [
                                "physics_sourceTerms_Flame_FlameEffects_EIP.ye_unburned",
                                "physics_sourceTerms_Flame_FlameEffects_EIP.sumyi_unburned",
                            ],
                        ],
                        [
                            "Burned",
                            [
                                "physics_sourceTerms_Flame_FlameEffects_EIP.ye_burned",
                                "physics_sourceTerms_Flame_FlameEffects_EIP.sumyi_burned",
                            ],
                        ],
                    ],
                    "physics_sourceTerms_Flame_FlameEffects_EIP.flame_deltae",
                ]
            )
        if "physics_sourceTerms_Flame_FlameSpeed_Constant" in schema.model:
            v.basic.append(
                "physics_sourceTerms_Flame_FlameSpeed_Constant.fl_fsConstFlameSpeed"
            )
        return v

    def _view_Simulation_SimulationMain_flashApp(self, schema):
        res = PKDict(
            title="FLASH Simulation",
            basic=schema.view.Simulation_SimulationMain_flashApp.advanced,
            advanced=schema.view.Simulation_SimulationMain_flashApp.advanced,
        )
        if "sim_condWall" in schema.model.Simulation_SimulationMain_flashApp:
            # TODO(pjm): special views for cap laser, instead look for common species fields
            res.basic = [
                "sim_condWall",
                "sim_peakField",
                "sim_period",
                "sim_zminWall",
                [
                    [
                        "Fill",
                        [
                            "sim_eosFill",
                            "sim_rhoFill",
                            "sim_teleFill",
                            "sim_tionFill",
                            "sim_tradFill",
                        ],
                    ],
                    [
                        "Wall",
                        [
                            "sim_eosWall",
                            "sim_rhoWall",
                            "sim_teleWall",
                            "sim_tionWall",
                            "sim_tradWall",
                        ],
                    ],
                ],
            ]
        return res
