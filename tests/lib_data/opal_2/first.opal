
OPTION, PSDUMPFREQ=5000;   // 6d data written on steps (h5).
OPTION, STATDUMPFREQ=1;  // Beam Stats written on steps (stat).
OPTION, BOUNDPDESTROYFQ=10; // Delete lost particles, if any       
OPTION, AUTOPHASE= 6; 
OPTION, VERSION = 20000;

Title, string="conversion";

//----------------------------------------------------------------------------
//Global Parameters
//----------------------------------------------------------------------------

REAL n_particles=5E4;

REAL gamma=273.97316778927893;  // 140 MeV electrons

REAL beta=sqrt(1-(1/gamma^2));

REAL P0=gamma*beta*EMASS;    //inital z momentum

value , {gamma*beta, EMASS, P0};


//----------------------------------------------------------------------------
//Bookkeeping
//----------------------------------------------------------------------------

// emit = 0.2e-6
// alpha = 0
// beta = 0.1
// rms emittance

REAL emit_n = 7.8983331046e-07;
REAL emit = emit_n / (beta * gamma);
REAL beta_twi = 2.83302878621;

//----------------------------------------------------------------------------
// Import Lattice definitions
//----------------------------------------------------------------------------

// CALL,FILE="spectrometer.txt";
REAL edge_drift_und2quads = 0;
drift_und2quads: DRIFT, L = 1.0, ELEMEDGE = edge_drift_und2quads;
REAL edge_q_def = 1.0;
q_def: QUADRUPOLE, L = 0.074, K1 = 21.808275280025114, ELEMEDGE = edge_q_def;
REAL edge_drift_quad2quad = 1.074;
drift_quad2quad: DRIFT, L = 0.03, ELEMEDGE = edge_drift_quad2quad;
REAL edge_q_foc = 1.104;
q_foc: QUADRUPOLE, L = 0.074, K1 = -21.808275280025114, ELEMEDGE = edge_q_foc;
REAL edge_drift_quad2dip = 1.1780000000000002;
drift_quad2dip: DRIFT, L = 1.5, ELEMEDGE = edge_drift_quad2dip;
REAL edge_spectr_dipole = 2.678;
spectr_dipole: SBEND, L = 0.49430796473268457, ANGLE = 0.5235987755982988, E1 = 0.0, E2 = 0.0,
        GAP = 0.0, PSI = 0.0, ELEMEDGE = edge_spectr_dipole, DESIGNENERGY = 139.489, FMAPFN = "hard_edge_profile.txt";
REAL edge_drift_dip2dump = 3.1723079647326844;
drift_dip2dump: DRIFT, L = 0.3, ELEMEDGE = edge_drift_dip2dump;

beamline_1: LINE=(drift_und2quads, q_def, drift_quad2quad, q_foc, drift_quad2dip, 
spectr_dipole, drift_dip2dump); 

//----------------------------------------------------------------------------
// INITIAL DISTRIBUTION
//----------------------------------------------------------------------------

// Cold Gaussian distribution for testing purposes
start_gaussian: DISTRIBUTION, TYPE = GAUSS,
        SIGMAX = sqrt(emit * beta_twi ),
        SIGMAPX = sqrt(emit / beta_twi) * beta * gamma,
        SIGMAY = sqrt(emit * beta_twi ),
        SIGMAPY = sqrt(emit / beta_twi ) * beta * gamma,
        SIGMAZ = 0.00065,
        CUTOFFLONG = 0.1, 
        SIGMAPZ = 6.576e-3 * beta * gamma ,   
        EMITTED = False,
        INPUTMOUNITS = None,      
        WRITETOFILE = True; 
 
//----------------------------------------------------------------------------
// Define Field solvers
//----------------------------------------------------------------------------

FS_SC: Fieldsolver, FSTYPE = NONE, // None or FFT
            MX = 32, MY = 32, MT = 32,
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
        BFREQ = 1.0e6, BCURRENT = 0.0, CHARGE = -1;

//----------------------------------------------------------------------------
// Initialize Simulation
//----------------------------------------------------------------------------

TRACK, LINE =beamline_1, BEAM = BEAM1, MAXSTEPS = 10000000, 
    DT = 1.8076756186965821e-12, ZSTOP=3.5;

RUN, METHOD = "PARALLEL-T", BEAM = BEAM1, 
    FIELDSOLVER = FS_SC, DISTRIBUTION = start_gaussian;
ENDTRACK;

Stop;
Quit;
