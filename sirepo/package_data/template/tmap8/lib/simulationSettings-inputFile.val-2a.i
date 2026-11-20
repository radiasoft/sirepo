# Validation Problem #2a from TMAP4/TMAP7 V&V document
# Deuterium ion implantation through PCA disk
# No trapping or Soret effects

# Mesh and solver controls
nx_scale = 5
high_dt_max = 300
low_dt_max = 4
simulation_time = '${units 2e4 s}'

# Material properties and boundary coefficients
diffusivity_D = '${units 3e-10 m^2/s -> mum^2/s}'
recombination_parameter_enclos2 = '${units 2e-31 m^4/at/s -> mum^4/at/s}'
recombination_coefficient_parameter_enclos1_TMAP4 = '${units 1e-27 m^4/at/s -> mum^4/at/s}'

# Source term definition (normal distribution) and applied surface flux history
flux_high = '${units 4.9e19 at/m^2/s -> at/mum^2/s}'
flux_low =  '${units 0      at/mum^2/s}'
width = '${units 2.4e-9 m -> mum}'
depth = '${units 14e-9 m -> mum}'
time_1 = '${units 5820 s}'
time_2 = '${units 9056 s}'
time_3 = '${units 12062 s}'
time_4 = '${units 14572 s}'
time_5 = '${units 17678 s}'

[Variables]
  # Concentration of deuterium in PCA (atoms/mum^3/s)
  [concentration]
    order = FIRST
    family = LAGRANGE
  []
[]

[Mesh]
  # mesh for implantation input manually
  [cartesian]
    type = CartesianMeshGenerator
    dim = 1
    dx = '${fparse 5 * ${units 4e-9 m -> mum}}  ${units 1e-8 m -> mum}  ${units 1e-7 m -> mum}
          ${units 1e-6 m -> mum}                ${units 1e-5 m -> mum}  ${fparse 10 * ${units 4.88e-5 m -> mum}}'
    ix = '${fparse 5 * ${nx_scale}}             ${nx_scale}             ${nx_scale}
          ${nx_scale}                           ${nx_scale}             ${fparse 10 * ${nx_scale}}'
  []
[]

[Kernels]
  # Diffusion and transient terms for deuterium concentration
  [diffusion]
    type = ADMatDiffusion
    variable = concentration
    diffusivity = ${diffusivity_D}
  []
  [time_diffusion]
    type = ADTimeDerivative
    variable = concentration
  []
  # Normal-distribution implantation source term
  [source]
    type = ADBodyForce
    variable = concentration
    function = concentration_source_norm_func
  []
[]

[AuxVariables]
  # Source term profile used for postprocessing
  [concentration_source]
  []
  # Time-dependent recombination coefficient on the upstream side
  [recombination_TMAP4]
  []
[]

[AuxKernels]
  [concentration_source_aux]
    type = FunctionAux
    variable = concentration_source
    function = concentration_source_norm_func
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [recombination_aux_TMAP4]
    type = FunctionAux
    variable = recombination_TMAP4
    function = '${recombination_coefficient_parameter_enclos1_TMAP4}'
    execute_on = 'INITIAL TIMESTEP_END'
  []
[]

[BCs]
  # Flux balance from recombination on upstream surface (left)
  [left]
    type = ADMatNeumannBC
    variable = concentration
    boundary = left
    value = 1
    boundary_material = flux_on_left
  []
  # Flux balance from recombination on downstream surface (right)
  [right]
    type = ADMatNeumannBC
    variable = concentration
    boundary = right
    value = 1
    boundary_material = flux_on_right
  []
[]

[Materials]
  # Recombination-driven flux on upstream boundary (left)
  [flux_on_left]
    type = ADDerivativeParsedMaterial
    coupled_variables = 'concentration'
    property_name = 'flux_on_left'
    functor_names = 'Kr_left_func'
    functor_symbols = 'Kr_left_func'
    expression = '- 2 * Kr_left_func * concentration ^ 2'
  []
  # Recombination-driven flux on downstream boundary (right)
  [flux_on_right]
    type = ADDerivativeParsedMaterial
    coupled_variables = 'concentration'
    property_name = 'flux_on_right'
    expression = '- 2 * ${recombination_parameter_enclos2} * concentration ^ 2'
  []
[]

[Functions]
  # Upstream recombination coefficient (time-dependent exponential) in microns^4/at/s
  [Kr_left_func]
    type = ParsedFunction
    expression = '${recombination_coefficient_parameter_enclos1_TMAP4} * (1 - 0.9999 * exp(-6e-5 * t))'
  []
  # Beam flux schedule applied to upstream surface (atoms/mum^2/s)
  [surface_flux_func]
    type = ParsedFunction
    expression = 'if(t < ${time_1}, ${flux_high},
                  if(t < ${time_2}, ${flux_low},
                  if(t < ${time_3},  ${flux_high},
                  if(t < ${time_4},  ${flux_low},
                  if(t < ${time_5},  ${flux_high}, ${flux_low}))))) * 0.75'
  []
  # Normalized implantation distribution across PCA thickness
  [source_distribution] # (-)
    type = ParsedFunction
    expression = '1.5 / (${width} * sqrt(2 * pi)) * exp(-0.5 * ((x - ${depth}) / ${width})^2)'
  []
  # Spatial-temporal source term from beam flux and implantation profile (atoms/microns^2/s)
  [concentration_source_norm_func] # atoms/microns^2/s
    type = ParsedFunction
    symbol_names = 'source_distribution surface_flux_func'
    symbol_values = 'source_distribution surface_flux_func'
    expression = 'source_distribution * surface_flux_func'
  []
  # Adaptive timestep ceiling near beam on/off transitions (s)
  [max_dt_size_func] # s
    type = ParsedFunction
    expression = 'if(t<${time_1}-100,  ${high_dt_max},
                  if(t<${time_1}+100,  ${low_dt_max},
                  if(t<${time_2}-100,  ${high_dt_max},
                  if(t<${time_2}+100,  ${low_dt_max},
                  if(t<${time_3}-100,  ${high_dt_max},
                  if(t<${time_3}+100,  ${low_dt_max},
                  if(t<${time_4}-100,  ${high_dt_max},
                  if(t<${time_4}+100,  ${low_dt_max},
                  if(t<${time_5}-100,  ${high_dt_max},
                  if(t<${time_5}+100,  ${low_dt_max}, ${high_dt_max}))))))))))'
  []
[]

[Postprocessors]
  # Average flux on upstream surface (left) from recombination
  [dcdx_left]
    type = ADSideAverageMaterialProperty
    boundary = left
    property = flux_on_left
    outputs = none
  []
  # Output upstream recombination flux (scaled to atoms/mum^2/s)
  [scaled_recombination_flux_left]
    type = ScalePostprocessor
    scaling_factor = '${fparse -1 * ${units 1 m^2 -> mum^2}}'
    value = dcdx_left
    execute_on = 'initial nonlinear linear timestep_end'
    outputs = 'console csv exodus'
  []
  # Average flux on downstream surface (right) from recombination
  [dcdx_right]
    type = ADSideAverageMaterialProperty
    boundary = right
    property = flux_on_right
    outputs = none
  []
  # Output downstream recombination flux (scaled to atoms/mum^2/s)
  [scaled_recombination_flux_right]
    type = ScalePostprocessor
    scaling_factor = '${fparse -1 * ${units 1 m^2 -> mum^2}}'
    value = dcdx_right
    execute_on = 'initial nonlinear linear timestep_end'
    outputs = 'console csv exodus'
  []
  # Limit timestep size according to beam on/off schedule
  [max_time_step_size]
    type = FunctionValuePostprocessor
    function = max_dt_size_func
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
  petsc_options_iname = '-pc_type'
  petsc_options_value = 'lu'
  end_time = ${simulation_time}
  automatic_scaling = true
  nl_rel_tol = 5e-7
  [TimeStepper]
    type = IterationAdaptiveDT
    dt = 1
    optimal_iterations = 6
    growth_factor = 1.1
    cutback_factor_at_failure = 0.9
    timestep_limiting_postprocessor = max_time_step_size
  []
[]

[Outputs]
  file_base = 'val-2a_out'
  csv = true
  [exodus]
    type = Exodus
    # legacy value
    max_output_name_length = 32
    output_material_properties = true
    time_step_interval = 2
  []
[]
