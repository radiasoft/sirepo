import RF_Track as rft
import numpy

v = rft.Volume()
field_data = numpy.loadtxt("CAVITY-fieldMapFile.rf_gunG4.dat")
s = field_data[:, 0]
step = (s.max() - s.min()) / (len(s) - 1)
length = s.max() - s.min()
field = field_data[:, 1] / numpy.max(numpy.abs(field_data[:, 1])) * 20e6
gun = rft.RF_FieldMap_1d(field, step, length, 1.3e9, 1)
gun.set_name("gunG4")
gun.set_aperture(0.05, 0.05, "circular")
gun.set_phid(10.0)
v.add(gun, 0, 0, 0.0, 0, 0, 0)

g = rft.Bunch6dT_Generator()
g.species = "electron"
g.q_total = 1.0
p0 = rft.Bunch6dT(g, 1000)
