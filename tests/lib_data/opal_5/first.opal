
OPTION, PSDUMPFREQ = 500;   // 6d data written every 10 time steps (h5).
OPTION, STATDUMPFREQ = 500;  // Beam Stats written every 10 time steps (stat).
OPTION, BOUNDPDESTROYFQ = 10; // Delete lost particles, if any
OPTION, AUTOPHASE = 4;
OPTION, VERSION = 10900;

//----------------------------------------------------------------------------
//Global Parameters
//----------------------------------------------------------------------------

REAL n_particles=41428;      // Number of particles in simulation. (Overridden if distibution imported)

// Initial Momentum (Set very small when starting simulation from cathode emission)
REAL P0 = 1.0e-6;    //inital z momentum
REAL rf_frequency = 1300.0;

REAL gun_phase = -20.0;
REAL cc1_phase = -2.0;
REAL cc2_phase = -10.0;
REAL solenoid_strength_parameter = 0.17765710979201543;
REAL I_Q106 = 0.0;
REAL I_Q107 = 0.0;

REAL beam_current = 0.13;
//----------------------------------------------------------------------------
// Injector Accelerating Cavities
//----------------------------------------------------------------------------


GUN: RFCAVITY, L = 0.265, VOLT = 42.93509225,
    FREQ = rf_frequency,
    ELEMEDGE = 0.0,
    FMAPFN = "GUN_SF7.T7",
    LAG = gun_phase * Pi / 180,
    APVETO = TRUE;

MS:  Solenoid, L = 0, ELEMEDGE = -0.0017, KS = solenoid_strength_parameter,
    FMAPFN = "Should_be_ignored.T7";

DG1: DRIFT, L = 0.363253, ELEMEDGE = GUN->ELEMEDGE + GUN->L;

DG2: DRIFT, L = 0.256055, ELEMEDGE = DG1->ELEMEDGE + DG1->L;

DG3: DRIFT, L = 0.039253, ELEMEDGE = DG2->ELEMEDGE + DG2->L;

DG4: DRIFT, L = 0.262251, ELEMEDGE = DG3->ELEMEDGE + DG3->L;

DG5: DRIFT, L = 0.246295, ELEMEDGE = DG4->ELEMEDGE + DG4->L;

DG6: DRIFT, L = 0.193948, ELEMEDGE = DG5->ELEMEDGE + DG5->L;

DG7: DRIFT, L = 0.076743, ELEMEDGE = DG6->ELEMEDGE + DG6->L;

DG8: DRIFT, L = 0.420191, ELEMEDGE = DG7->ELEMEDGE + DG7->L;

CC1: RFCAVITY, L = 1.3492, VOLT = 28.57233448,
    FREQ = rf_frequency,
    ELEMEDGE = DG8->ELEMEDGE + DG8->L,
    FMAPFN = "TESLA_SF7.T7",
    LAG = cc1_phase * Pi/180;

DCC1_1: DRIFT, L = 0.58952, ELEMEDGE = CC1->ELEMEDGE + CC1->L;

DCC1_2: DRIFT, L = 0.045959, ELEMEDGE = DCC1_1->ELEMEDGE + DCC1_1->L;

DCC1_3: DRIFT, L = 0.724255, ELEMEDGE = DCC1_2->ELEMEDGE + DCC1_2->L;

CC2: RFCAVITY, L = 1.3492, VOLT = 30.6427935,
    FREQ = rf_frequency,
    ELEMEDGE = DCC1_3->ELEMEDGE + DCC1_3->L,
    FMAPFN = "TESLA_SF7.T7",
    LAG = cc2_phase * Pi/180;

DCC2_1: DRIFT, L = 0.801182, ELEMEDGE = CC2->ELEMEDGE + CC1->L;

DCC2_2: DRIFT, L = 0.090742, ELEMEDGE = DCC2_1->ELEMEDGE + DCC2_1->L;

DCC2_3: DRIFT, L = 0.213827, ELEMEDGE = DCC2_2->ELEMEDGE + DCC2_2->L;

DCC2_4: DRIFT, L = 0.120424, ELEMEDGE = DCC2_3->ELEMEDGE + DCC2_3->L;

DCC2_5: DRIFT, L = 0.343, ELEMEDGE = DCC2_4->ELEMEDGE + DCC2_4->L;

DCC2_6: DRIFT, L = 0.343, ELEMEDGE = DCC2_5->ELEMEDGE + DCC2_5->L;

DCC2_7: DRIFT, L = 0.32599, ELEMEDGE = DCC2_6->ELEMEDGE + DCC2_6->L;

DCC2_8: DRIFT, L = 0.078595, ELEMEDGE = DCC2_7->ELEMEDGE + DCC2_7->L;

DCC2_9: DRIFT, L = 0.126538, ELEMEDGE = DCC2_8->ELEMEDGE + DCC2_8->L;

DCC2_10: DRIFT, L = 0.078569, ELEMEDGE = DCC2_9->ELEMEDGE + DCC2_9->L;

X_106: MONITOR, OUTFN = 'output_x_106.h5', ELEMEDGE = DCC2_10->ELEMEDGE + DCC2_10->L;

Q_106: QUADRUPOLE, L = 0.167, ELEMEDGE = X_106->ELEMEDGE, K1S = I_Q106 * 10.135 * 40 / ( 1.8205 * 299.8 );

DQ106: DRIFT, L = 0.034249, ELEMEDGE = Q_106->ELEMEDGE + Q_106->L;

Q_107: QUADRUPOLE, L = 0.167, ELEMEDGE = DQ106->ELEMEDGE + DQ106->L, K1S = I_Q107 * 10.135 * 40 / ( 1.8205 * 299.8 );

DX107: DRIFT, L = 0.255184, ELEMEDGE = Q_107->ELEMEDGE + Q_107->L;

X_107: MONITOR, OUTFN = 'output_x_107.h5', ELEMEDGE = DX107->ELEMEDGE + DX107->L;

LINAC: LINE = (GUN, MS, CC1, CC2, X_106, Q_106, Q_107, X_107);

// Still needs adjustment, bunch length does not match very well.
REAL fwhm = 3.12 / 360 * (1 / (rf_frequency*1.0e6));

gen_dist: DISTRIBUTION, TYPE = FLATTOP,
        SIGMAR = 0.001*2,
        TPULSEFWHM = fwhm*2,
        NBIN = 9,
        EMISSIONSTEPS = 100,
        EMISSIONMODEL = NONE,
        EKIN = 0.55,
        EMITTED = True,
        WRITETOFILE = True;    //Saves the distribution to a text file

vc_dist: DISTRIBUTION, TYPE = FROMFILE,
        FNAME = "fast_laser.dist",
        EMISSIONMODEL = None,
        NBIN = 9,
        EMISSIONSTEPS = 100,
        EKIN = 0.4,
        EMITTED = True;

//----------------------------------------------------------------------------
// Define Field solvers
//----------------------------------------------------------------------------

FS_SC: Fieldsolver, FSTYPE = FFT, // None or FFT
            MX = 26, MY = 26, MT = 25,
            PARFFTX = false,
            PARFFTY = false,
            PARFFTT = true,  //parallel in the z direction only
            BCFFTX = open,
            BCFFTY = open,
            BCFFTT = open,
            BBOXINCR = 1,
            GREENSF = INTEGRATED;

//----------------------------------------------------------------------------
// Electron Beam Definition

BEAM1:  BEAM, PARTICLE = ELECTRON, pc = P0, NPART = n_particles,
        BFREQ = 1300.0, BCURRENT = beam_current, CHARGE = -1;

//----------------------------------------------------------------------------
// Initialize Simulation
//----------------------------------------------------------------------------


TRACK, LINE = LINAC, BEAM = BEAM1, MAXSTEPS = 2500000,
    DT = {2.0e-13}, ZSTOP={9.25};

RUN, METHOD = "PARALLEL-T", BEAM = BEAM1,
    FIELDSOLVER = FS_SC, DISTRIBUTION = vc_dist;
ENDTRACK;

Stop;
Quit;
