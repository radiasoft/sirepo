import RF_Track as rft

v = rft.Volume()


def place(e, name, ax, ay, dx, dy, z, rz, rx, ry):
    e.set_name(name)
    e.set_aperture(ax, ay, "circular")
    v.add(e, dx, dy, z, rz, rx, ry)


place(rft.Drift(1.5), "D1", 0.02, 0.02, 0, 0, 0.0, 0, 0, 0)
place(rft.Quadrupole(0.2, 3.0), "Q1", 0.015, 0.015, 0, 0, 1.5, 0, 0, 0)

qg = rft.Quadrupole(0.3, float("nan"), 0.0)
qg.set_gradient(5.0)
place(qg, "Q2", 0.015, 0.015, 0, 0, 1.8, 0, 0, 0)

place(rft.Corrector(0.1, 0.001, -0.002), "C1", 0.02, 0.02, 0, 0, 2.1, 0, 0, 0)
place(rft.Screen(), "SCR1", 0.02, 0.02, 0, 0, 2.5, 0, 0, 0)

g = rft.Bunch6dT_Generator()
g.species = "electron"
g.q_total = 0.5
g.sig_x = 0.001
g.lt = 2e-12
g.rt = 0.5e-12
g.c_sig_t = 3.0
g.c_sig_x = 2.5
g.c_sig_y = 2.5
g.e_photon = 2.1
g.phi_eff = 1.57
g.noise_reduc = True
p0 = rft.Bunch6dT(g, 10000)
