# File header, followed by a blank line, so it isn't a heading
# more header

no_heading = 1
# ======== Geometry ========
length = 2
area = '${fparse length * length}'
# Trap 1 parameters
# a second comment line isn't part of the name
trap_density = '${units 3 m -> mum}'
ref = ${length}

# Mesh controls are above a block, not a parameter
[Mesh]
  inside_block = 4
[]
