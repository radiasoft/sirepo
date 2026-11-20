# Validation Problem val-2j
# Tritium TDS from neutron-irradiated Li2TiO3 solid breeder
# Reference: Kobayashi et al., J. Nucl. Mater. 458 (2015) 22-28
# (O-)-center trapping model with first-order defect annihilation during TDS heating.
# (F+)-center trapping is excluded because its detrapping is too fast relative to
# diffusion (release near 580 K coincides with diffusion-controlled release; see Kobayashi p.26).

# ============ Physical Constants ============
kB_J = '${units 1.380649e-23 J/K}' # Boltzmann constant in J/K

# ============ Diffusion Parameters (Eq. 11) ============
D0 = '${units 6.9e-7 m^2/s -> mum^2/s}' # diffusivity pre-exponential
E_d = '${fparse ${units 1.07 eV -> J} / ${kB_J}}' # diffusion activation energy (K)

# ============ (O-)-center (hydroxyl) Trapping Parameters (Eq. 13, 21) ============
alpha_t = '${units 4.2e8 1/s}' # trapping prefactor (Eq. 21)
epsilon_t = '${fparse ${units 1.04 eV -> J} / ${kB_J}}' # trapping energy (K) (Eq. 21)
alpha_r = '${units 4.1e6 1/s}' # detrapping prefactor (Eq. 13)
epsilon_r = '${fparse ${units 1.19 eV -> J} / ${kB_J}}' # detrapping energy (K) (Eq. 13)

# ============ Defect Annihilation Parameters (Eqs. 16-18) ============
alpha_anneal = '${units 1.0e2 1/s}' # annihilation prefactor (Eq. 18)
E_anneal = '${fparse ${units 0.9 eV -> J} / ${kB_J}}' # annihilation energy (K) (Eq. 18)
# Base input file for val-2j: Tritium TDS from Li2TiO3 solid breeder
# This file contains the shared simulation blocks for all val-2j cases.
# The including input file must define:
#   D0, E_d, alpha_t, epsilon_t, alpha_r, epsilon_r (diffusion/trapping params)
#   alpha_anneal, E_anneal (defect annihilation params)

# ============ Geometry ============
grain_radius = '${units 1.5e-6 m -> mum}' # average grain radius
num_elems = 100 # number of radial elements

# ============ Material Properties ============
# Li2TiO3 lattice density: rho=3.43 g/cm3, MW=109.75 g/mol
N_lattice = '${units 1.88e28 1/m^3 -> 1/mum^3}' # lattice molecule density
Ct0 = 0.018 # total defect fraction: Sample E (Table 1)
trap_per_free = 1 # concentration scaling factor

# ============ TDS Parameters ============
T_start = '${units 300 K}' # initial temperature
heating_rate = '${units ${fparse 5.0/60.0} K/s}' # 5 K/min
end_time = '${fparse (900.0 - 300.0) / ${heating_rate}}' # ramp duration (300 K to 900 K)

# ============ Initial Conditions ============
# Mobile and trapped concentrations start in local trapping/detrapping
# equilibrium at T_start. This avoids an initial transient from an
# imbalance between trapping and detrapping rates.
# Since TDS output is normalized, absolute concentrations don't matter.
C0_trapped = 1.0 # initial trapped concentration (arb. units, uniform)
C0_mobile = '${fparse alpha_r * exp(-epsilon_r / T_start) * C0_trapped / (alpha_t * exp(-epsilon_t / T_start) * Ct0)}'

[Mesh]
  type = GeneratedMesh
  dim = 1
  nx = ${num_elems}
  xmax = ${grain_radius}
  coord_type = RSPHERICAL
[]

[Problem]
  type = ReferenceResidualProblem
  extra_tag_vectors = 'ref'
  reference_vector = 'ref'
[]

[Variables]
  [mobile]
    initial_condition = ${C0_mobile}
  []
  [trapped]
    initial_condition = ${C0_trapped}
  []
  [defect_density]
    initial_condition = ${Ct0}
  []
[]

[AuxVariables]
  [temperature]
  []
[]

[AuxKernels]
  [temperature_aux]
    type = FunctionAux
    variable = temperature
    function = temperature_ramp
    execute_on = 'initial timestep_end linear'
  []
[]

[Kernels]
  [diffusion]
    type = ADMatDiffusion
    variable = mobile
    diffusivity = diffusivity
    extra_vector_tags = ref
  []
  [time_mobile]
    type = ADTimeDerivative
    variable = mobile
    extra_vector_tags = ref
  []
  [coupled_time_trapped]
    type = ScaledCoupledTimeDerivative
    variable = mobile
    v = trapped
    factor = ${trap_per_free}
    extra_vector_tags = ref
  []
[]

[NodalKernels]
  # --- (O-)-center (hydroxyl) trap ---
  [time_trapped]
    type = TimeDerivativeNodalKernel
    variable = trapped
  []
  [trapping]
    type = TrappingNodalKernel
    variable = trapped
    mobile_concentration = mobile
    alpha_t = ${alpha_t}
    trapping_energy = ${epsilon_t}
    N = ${N_lattice}
    Ct0 = 'Ct0_func'
    temperature = temperature
    trap_per_free = ${trap_per_free}
    extra_vector_tags = ref
  []
  [releasing]
    type = ReleasingNodalKernel
    variable = trapped
    alpha_r = ${alpha_r}
    detrapping_energy = ${epsilon_r}
    temperature = temperature
    extra_vector_tags = ref
  []
  [releasing_defect_annealing]
    type = ReleasingNodalKernel
    variable = trapped
    alpha_r = ${alpha_anneal}
    detrapping_energy = ${E_anneal}
    temperature = temperature
    extra_vector_tags = ref
  []
  # --- Defect annihilation ODE: dD_id/dt = -k_anneal * D_id ---
  [time_defect_density]
    type = TimeDerivativeNodalKernel
    variable = defect_density
  []
  [defect_annihilation]
    type = ReleasingNodalKernel
    variable = defect_density
    alpha_r = ${alpha_anneal}
    detrapping_energy = ${E_anneal}
    temperature = temperature
    extra_vector_tags = ref
  []
[]

[BCs]
  # C = 0 at grain surface (fast surface release - Eq. 20)
  # No BC at r=0; symmetry is automatic in RSPHERICAL
  [surface]
    type = ADDirichletBC
    variable = mobile
    boundary = right
    value = 0
  []
[]

[Materials]
  [diffusivity_mat]
    type = ADDerivativeParsedMaterial
    property_name = diffusivity
    functor_names = 'temperature_ramp'
    functor_symbols = 'T'
    expression = '${D0} * exp(-${E_d} / T)'
  []
  [converter_to_regular]
    type = MaterialADConverter
    ad_props_in = 'diffusivity'
    reg_props_out = 'diffusivity_nonAD'
    outputs = none
  []
[]

[Functions]
  [temperature_ramp]
    type = ParsedFunction
    expression = '${T_start} + ${heating_rate} * t'
  []
  [Ct0_func]
    type = ParsedFunction
    symbol_names = 'Ct0_value'
    symbol_values = 'defect_density_pp'
    expression = 'Ct0_value'
  []
[]

[Postprocessors]
  # Tritium release rate = diffusive flux at grain surface (right boundary)
  [release_rate]
    type = SideDiffusiveFluxIntegral
    variable = mobile
    diffusivity = diffusivity_nonAD
    boundary = right
  []
  [temperature_pp]
    type = FunctionValuePostprocessor
    function = temperature_ramp
    # Sirepo: also at initial, so the first output row isn't 0 K
    execute_on = 'initial timestep_end'
  []
  [defect_density_pp]
    type = AverageNodalVariableValue
    variable = defect_density
    execute_on = 'initial timestep_end'
  []
  [total_mobile]
    type = ElementIntegralVariablePostprocessor
    variable = mobile
  []
  [total_trapped]
    type = ElementIntegralVariablePostprocessor
    variable = trapped
  []
[]

[Preconditioning]
  [smp]
    type = SMP
    full = true
  []
[]

[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON
  petsc_options_iname = '-pc_type'
  petsc_options_value = 'lu'
  line_search = none
  automatic_scaling = true
  compute_scaling_once = true

  end_time = ${end_time}
  dtmax = 30 # limit time step to ~2.5 K per step for TDS resolution
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 1.0
    optimal_iterations = 12
    growth_factor = 1.2
    cutback_factor = 0.8
  []
  nl_rel_tol = 1e-10
  nl_abs_tol = 1e-12
[]

[Outputs]
  exodus = true
  csv = true
[]