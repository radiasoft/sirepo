# Validation Problem #2d from TMAP7 V&V document
# Thermal Desorption Spectroscopy on Tungsten

# General parameters
kB = '${units 1.380649e-23 J/K}' # Boltzmann constant (from TMAP8PhysicalConstants.h)

# Model parameters
TDS_initial_time = '${units 5e3 s}'
TDS_critial_time_1 = '${units 5400 s}'
TDS_critial_time_2 = '${units 5404 s}'
simulation_time = '${units 6.8e3 s}'
outputs_initial_time = '${units 5000 s}' # Sirepo: TDS_initial_time, not 4000, so the plot starts at the desorption
step_interval_max = 50 # (-)
step_interval_mid = 15 # (-)
step_interval_min = 6 # (-)
bound_value_max = '${units 2e4 at/mum^3}'
bound_value_min = '${units -1e-10 at/mum^3}'

# Diffusion parameters
flux_high = '${units 1e19 at/m^2/s -> at/mum^2/s}'
flux_low = '${units 0      at/mum^2/s}'
diffusivity_coefficient = '${units 4.1e-7 m^2/s -> mum^2/s}'
E_D = '${units 0.39 eV -> J}'
initial_concentration = '${units 1e-10 at/m^3 -> at/mum^3}'
width_source = '${units 3e-9 m -> mum}'
depth_source = '${units 4.6e-9 m -> mum}'

# Traps parameters
N = '${units 6.25e28 at/m^3 -> at/mum^3}'
initial_concentration_trap_2 = 4.4e-10 # (-)
initial_concentration_trap_3 = 1.4e-10 # (-)
trapping_energy = '${fparse ${units 0.39 eV -> J} / ${kB}}'
detrapping_energy_1 = '${fparse ${units 1.2 eV -> J} / ${kB}}'
detrapping_energy_2 = '${fparse ${units 1.6 eV -> J} / ${kB}}'
detrapping_energy_3 = '${fparse ${units 3.1 eV -> J} / ${kB}}'
trapping_site_fraction_1 = 0.002156 # (-)
trapping_site_fraction_2 = 0.00175 # (-)
trapping_site_fraction_3 = 0.0020 # (-)
trapping_rate_prefactor = '${units 9.1316e12 1/s}'
release_rate_profactor = '${units 8.4e12 1/s}'
trap_per_free_1 = 1e6 # (-)
trap_per_free_2 = 1e4 # (-)
trap_per_free_3 = 1e4 # (-)
width_trap1 = '${units 10e-9 m -> mum}'

# thermal parameters
temperature_low = '${units 300 K}'
temperature_high = '${units 1273 K}'
temperature_rate = '${units ${fparse 50 / 60} K/s}'

[Mesh]
  active = 'cartesian_mesh'
  # finer mesh for heavy simulations
  [cartesian_mesh]
    nx_scale = 2
    type = CartesianMeshGenerator
    dim = 1
    dx = '${fparse 10 * ${units 1.5e-9 m -> mum}}
          ${units 1e-9 m -> mum}       ${units 1e-8 m -> mum}     ${units 1e-7 m -> mum}
          ${units 4e-6 m -> mum}       ${units 4.407e-6 m -> mum} ${fparse 11 * ${units 7.407e-6 m -> mum}}'
    ix = '${fparse 10 * ${nx_scale}}
          ${fparse 1 * ${nx_scale}}    ${fparse 1 * ${nx_scale}}   ${fparse 1 * ${nx_scale}}
          ${fparse 50 * ${nx_scale}}   ${fparse 2}                 ${fparse 1}'
    subdomain_id = '0 1 1 1 1 1 1'
  []
  # coarse mesh for tests
  [cartesian_mesh_coarse]
    nx_scale = 1
    type = CartesianMeshGenerator
    dim = 1
    dx = '${fparse 10 * ${units 1.5e-9 m -> mum}}
          ${units 1e-9 m -> mum}       ${units 1e-8 m -> mum}      ${units 1e-7 m -> mum}
          ${units 4e-6 m -> mum}       ${units 4.407e-6 m -> mum}  ${fparse 11 * ${units 7.407e-6 m -> mum}}'
    ix = '${fparse 10 * ${nx_scale}}
          ${fparse 1 * ${nx_scale}}    ${fparse 1 * ${nx_scale}}   ${fparse 1 * ${nx_scale}}
          ${fparse 6 * ${nx_scale}}    ${fparse 1}                 ${fparse 1}'
    subdomain_id = '0 1 1 1 1 1 1'
  []
[]

[Problem]
  type = ReferenceResidualProblem
  extra_tag_vectors = 'ref'
  reference_vector = 'ref'
[]

[Bounds]
  # Bounds to limit the maximum and minimum values for variables
  [concentration_lower_bound]
    type = ConstantBounds
    variable = bounds_dummy
    bounded_variable = concentration
    bound_type = lower
    bound_value = ${bound_value_min}
  []
  [trapped_1_lower_bound]
    type = ConstantBounds
    variable = bounds_dummy
    bounded_variable = trapped_1
    bound_type = lower
    bound_value = ${bound_value_min}
  []
  [trapped_2_upper_bound]
    type = ConstantBounds
    variable = bounds_dummy
    bounded_variable = trapped_2
    bound_type = upper
    bound_value = ${bound_value_max}
  []
  [trapped_2_lower_bound]
    type = ConstantBounds
    variable = bounds_dummy
    bounded_variable = trapped_2
    bound_type = lower
    bound_value = ${bound_value_min}
  []
  [trapped_3_upper_bound]
    type = ConstantBounds
    variable = bounds_dummy
    bounded_variable = trapped_3
    bound_type = upper
    bound_value = ${bound_value_max}
  []
  [trapped_3_lower_bound]
    type = ConstantBounds
    variable = bounds_dummy
    bounded_variable = trapped_3
    bound_type = lower
    bound_value = ${bound_value_min}
  []
[]

[Variables]
  # Mobile concentration variable
  [concentration]
    order = FIRST
    family = LAGRANGE
    initial_condition = ${initial_concentration}
  []
  # Three trapped concentration variables
  [trapped_1]
    order = FIRST
    family = LAGRANGE
    block = 0
    outputs = none
  []
  [trapped_2]
    order = FIRST
    family = LAGRANGE
    initial_condition = '${fparse initial_concentration_trap_2 * trapping_site_fraction_2 * N}'
    outputs = none
  []
  [trapped_3]
    order = FIRST
    family = LAGRANGE
    initial_condition = '${fparse initial_concentration_trap_3 * trapping_site_fraction_3 * N}'
    outputs = none
  []
[]

[AuxVariables]
  [temperature]
  []
  # necessary dummy variable for bounds
  [bounds_dummy]
    order = FIRST
    family = LAGRANGE
  []
[]

[AuxKernels]
  [temperature_Aux]
    type = FunctionAux
    variable = temperature
    function = Temperature_function
    execute_on = 'initial timestep_end linear'
  []
[]

[Kernels]
  # mobile concentration kernel
  [diffusion_implantation]
    type = ADMatDiffusion
    variable = concentration
    diffusivity = Diffusivity
    extra_vector_tags = ref
  []
  [time_diffusion_implantation]
    type = ADTimeDerivative
    variable = concentration
    extra_vector_tags = ref
  []
  [source]
    type = ADBodyForce
    variable = concentration
    function = concentration_source_norm_function
  []

  # trapping kernel
  [coupled_time_trap_1]
    type = ADCoefCoupledTimeDerivative
    variable = concentration
    v = trapped_1
    coef = ${trap_per_free_1}
    block = 0
    extra_vector_tags = ref
  []
  [coupled_time_trap_2_implantation]
    type = ADCoefCoupledTimeDerivative
    variable = concentration
    v = trapped_2
    coef = ${trap_per_free_2}
    extra_vector_tags = ref
  []
  [coupled_time_trap_3_implantation]
    type = ADCoefCoupledTimeDerivative
    variable = concentration
    v = trapped_3
    coef = ${trap_per_free_3}
    extra_vector_tags = ref
  []
[]

[NodalKernels]
  # First traps
  [time_1]
    type = TimeDerivativeNodalKernel
    variable = trapped_1
  []
  [trapping_1]
    type = TrappingNodalKernel
    variable = trapped_1
    mobile_concentration = concentration
    alpha_t = '${trapping_rate_prefactor}'
    trapping_energy = '${trapping_energy}'
    N = '${N}'
    Ct0 = 'trap_1_distribution_function'
    temperature = 'temperature'
    trap_per_free = ${trap_per_free_1}
    extra_vector_tags = ref
  []
  [release_1]
    type = ReleasingNodalKernel
    variable = trapped_1
    alpha_r = '${release_rate_profactor}'
    detrapping_energy = '${detrapping_energy_1}'
    temperature = 'temperature'
  []

  # Second traps
  [time_2]
    type = TimeDerivativeNodalKernel
    variable = trapped_2
  []
  [trapping_2_implantation]
    type = TrappingNodalKernel
    variable = trapped_2
    mobile_concentration = concentration
    alpha_t = '${trapping_rate_prefactor}'
    trapping_energy = '${trapping_energy}'
    N = '${N}'
    Ct0 = '${trapping_site_fraction_2}'
    temperature = 'temperature'
    trap_per_free = ${trap_per_free_2}
    extra_vector_tags = ref
  []
  [release_2_implantation]
    type = ReleasingNodalKernel
    variable = trapped_2
    alpha_r = '${release_rate_profactor}'
    detrapping_energy = '${detrapping_energy_2}'
    temperature = 'temperature'
  []

  # Third traps
  [time_3]
    type = TimeDerivativeNodalKernel
    variable = trapped_3
  []
  [trapping_3_implantation]
    type = TrappingNodalKernel
    variable = trapped_3
    mobile_concentration = concentration
    alpha_t = '${trapping_rate_prefactor}'
    trapping_energy = '${trapping_energy}'
    N = '${N}'
    Ct0 = '${trapping_site_fraction_3}'
    temperature = 'temperature'
    trap_per_free = ${trap_per_free_3}
    extra_vector_tags = ref
  []
  [release_3_implantation]
    type = ReleasingNodalKernel
    variable = trapped_3
    alpha_r = '${release_rate_profactor}'
    detrapping_energy = '${detrapping_energy_3}'
    temperature = 'temperature'
  []
[]

[BCs]
  # Constant concentration on both boundary
  [left]
    type = ADDirichletBC
    variable = concentration
    boundary = left
    value = 0
  []
  [right]
    type = ADDirichletBC
    variable = concentration
    boundary = right
    value = 0
  []
[]

[Materials]
  [Diffusivity_implantation]
    type = ADDerivativeParsedMaterial
    property_name = 'Diffusivity'
    functor_names = 'Temperature_function'
    functor_symbols = 'Temperature_function'
    expression = '${diffusivity_coefficient} * exp(- ${E_D} / ${kB} / Temperature_function)'
    block = 0
    output_properties = 'Diffusivity'
  []
  [Diffusivity_Tungsten]
    type = ADDerivativeParsedMaterial
    property_name = 'Diffusivity'
    functor_names = 'Temperature_function'
    functor_symbols = 'Temperature_function'
    expression = '${diffusivity_coefficient} * exp(- ${E_D} / ${kB} / Temperature_function) * 10'
    block = 1
    output_properties = 'Diffusivity'
  []
  [converter_to_regular]
    type = MaterialADConverter
    ad_props_in = 'Diffusivity'
    reg_props_out = 'Diffusivity_nonAD'
    outputs = none
  []
[]

[Functions]
  # Sirepo: environmental background ramp added to the TMAP8 desorption flux
  # before comparing with the experiment (see comparison_val-2d.py)
  [background_flux_function]
    type = ParsedFunction
    expression = 'min(max(4.87e17 / ((1273 - 300) / (50 / 60)) * (t - 5000), 0), 4.87e17)'
  []
  # Function for temperature and input flux
  [Temperature_function]
    type = ParsedFunction
    expression = 'if(t<${TDS_initial_time},   ${temperature_low},
                  if(t<${TDS_initial_time} + (${temperature_high} - ${temperature_low}) /
                        ${temperature_rate},  ${temperature_low} + ${temperature_rate} * (t - ${TDS_initial_time}),
                                              ${temperature_high}))'
  []
  [surface_flux_function]
    type = ParsedFunction
    expression = 'if(t<${TDS_initial_time}, ${flux_high}, ${flux_low})'
  []
  [source_distribution_function]
    type = ParsedFunction
    expression = '1 / ( ${width_source} * sqrt(2 * pi) ) * exp(-0.5 * ((x - ${depth_source}) / ${width_source} ) ^ 2)'
  []
  [trap_1_distribution_function]
    type = ParsedFunction
    expression = ' ${trapping_site_fraction_1} / ( ${width_trap1} * sqrt(2 * pi) ) * exp(-0.5 * ((x - ${depth_source}) / ${width_trap1}) ^ 2)'
  []
  [concentration_source_norm_function]
    type = ParsedFunction
    symbol_names = 'source_distribution_function surface_flux_function'
    symbol_values = 'source_distribution_function surface_flux_function'
    expression = 'source_distribution_function * surface_flux_function'
  []
  # maximum time size during simulations
  [max_dt_size_function]
    type = ParsedFunction
    expression = 'if(t<${TDS_initial_time}  , ${step_interval_mid}, ${step_interval_min})'
  []
  [max_dt_size_function_coarse]
    type = ParsedFunction
    expression = 'if(t<${TDS_initial_time}  , ${step_interval_mid},
                  if(t<${TDS_critial_time_1}, ${step_interval_max},
                  if(t<${TDS_critial_time_2}, ${step_interval_min}, ${step_interval_max})))'
  []
[]

[Postprocessors]
  # left flux
  [flux_surface_left]
    type = SideDiffusiveFluxIntegral
    variable = concentration
    diffusivity = 'Diffusivity_nonAD'
    boundary = 'left'
    outputs = none
  []
  [scaled_flux_surface_left]
    type = ScalePostprocessor
    scaling_factor = '${units 1 m^2 -> mum^2}'
    value = flux_surface_left
    execute_on = 'initial nonlinear linear timestep_end'
    outputs = 'console csv exodus'
  []
  # Sirepo: the quantity plotted against the experiment in comparison_val-2d.py
  [background_flux]
    type = FunctionValuePostprocessor
    function = background_flux_function
    execute_on = 'initial timestep_end'
    outputs = 'console csv'
  []
  [total_desorption_flux]
    type = ParsedPostprocessor
    expression = 'background_flux + scaled_flux_surface_left / 2'
    pp_names = 'background_flux scaled_flux_surface_left'
    execute_on = 'initial timestep_end'
    outputs = 'console csv'
  []
  # right flux
  [flux_surface_right]
    type = SideDiffusiveFluxIntegral
    variable = concentration
    diffusivity = 'Diffusivity_nonAD'
    boundary = 'right'
    outputs = none
  []
  [scaled_flux_surface_right]
    type = ScalePostprocessor
    scaling_factor = '${units 1 m^2 -> mum^2}'
    value = flux_surface_right
    execute_on = 'initial nonlinear linear timestep_end'
    outputs = none
  []
  [max_time_step_size]
    type = FunctionValuePostprocessor
    function = max_dt_size_function
    execute_on = 'initial nonlinear linear timestep_end'
    outputs = none
  []
[]

[Preconditioning]
  [SMP]
    type = SMP
    full = true
  []
[]

[Executioner]
  type = Transient
  scheme = bdf2
  solve_type = NEWTON
  petsc_options_iname = '-pc_type -snes_type'
  petsc_options_value = 'lu vinewtonrsls'

  end_time = ${simulation_time}
  line_search = 'none'
  automatic_scaling = true
  nl_rel_tol = 1e-10
  nl_abs_tol = 1e-9
  nl_max_its = 34
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 1.0
    iteration_window = 5
    optimal_iterations = 26
    growth_factor = 1.1
    cutback_factor = 0.9
    cutback_factor_at_failure = 0.9
    timestep_limiting_postprocessor = max_time_step_size
  []
[]

[Outputs]
  file_base = 'val-2d_out'
  [csv]
    type = CSV
    start_time = ${outputs_initial_time}
  []
  [exodus]
    type = Exodus
    # legacy value
    max_output_name_length = 32
    start_time = ${outputs_initial_time}
    output_material_properties = true
    time_step_interval = 20
  []
[]
