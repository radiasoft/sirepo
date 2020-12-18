
OPTION, PSDUMPFREQ=102;   // 6d data written every x time steps (h5).
OPTION, STATDUMPFREQ=10;  // Beam Stats written every x time steps (stat).
OPTION, BOUNDPDESTROYFQ=10; // Delete lost particles, if any       
OPTION, AUTOPHASE=8; 
OPTION, VERSION = 20000;       //10600;

Title, string="Photoinjector Beamline";

//----------------------------------------------------------------------------
//Global Parameters
//----------------------------------------------------------------------------

REAL rf_freq=2.856e9;     // RF frequency. (Hz)
REAL n_particles=100000;      // Number of particles in simulation. (Overridden if distibution imported)
REAL beam_bunch_charge=300e-12;      // Charge of bunch. (C)

// Initial Momentum (Set very small when starting simulation from cathode emission)
REAL Edes=1.4e-9; // Setting small initial energy
REAL gamma=(Edes+EMASS)/EMASS; 
REAL beta=sqrt(1-(1/gamma^2));
REAL P0=gamma*beta*EMASS;    //inital z momentum

REAL slac_length=3.01;
REAL hwl=0.052464; //half-wavelength of cavity

//----------------------------------------------------------------------------
//Bookkeeping
//----------------------------------------------------------------------------


//----------------------------------------------------------------------------
// Injector Accelerating Cavities
//----------------------------------------------------------------------------


//----------------------------------------------------------------------------
// Import APS LINAC Lattice definitions
//----------------------------------------------------------------------------

//CALL,FILE="PCG_L1_linac.txt"; // Gun through L1
REAL pcg_offset = 0.738;
REAL pcg_start = 0;
REAL pcg_length = 0.15; // TODO: Currently taken from gunCavity.dat length. Is this correct?
REAL pcg_phi_deg = -13.534;

PCG:    RFCavity, L = pcg_length, VOLT = 100.0, ELEMEDGE = pcg_start, 
        TYPE = "STANDING", 
        FMAPFN = "gunCavity.T7", 
        FREQ = 2856.0, 
        LAG = (pcg_phi_deg*Pi)/180.0; // LAG (phase) is converted to radians


REAL solenoid_start = pcg_offset - 0.5831;
REAL solenoid_length = 0.355601 * 2; // TODO: This length is taken from field map, not sure if it matters
REAL solenoid_strength = 0.22989;

MS:  Solenoid, L = solenoid_length, ELEMEDGE = solenoid_start, KS = solenoid_strength,
    FMAPFN = "Solenoid.T7";


REAL l1_start = 1.12682 + pcg_offset + hwl;
REAL l1_phi_deg = -4.982;

L1:     TRAVELINGWAVE, L = slac_length, VOLT = 17.594, ELEMEDGE = l1_start,
        NUMCELLS = 84, MODE = 1/3,
        FAST = False, 
        FMAPFN = "TWS_Sband.T7", 
        FREQ = 2856.0, 
        LAG = (l1_phi_deg*Pi)/180.0; // LAG (phase) is converted to radians
        
Q1:     QUADRUPOLE, L = 0.136, ELEMEDGE = 1.212 + pcg_offset, K1 = 0.1620695476;
Q2:     QUADRUPOLE, L = 0.136, ELEMEDGE = 1.542 + pcg_offset, K1 = -0.1866068772055;


PCG_LINE:  Line = (PCG, MS, L1);

//----------------------------------------------------------------------------
// Master Line Definitions
//----------------------------------------------------------------------------

LINAC: Line = (PCG_LINE);

//----------------------------------------------------------------------------
// INITIAL DISTRIBUTION
// astra_dist taken from radial1k0.ini
// gen_dist is an attempt to approximately replicate radial1k0 with a 
//  transverse hardedge distribution and gaussian temporal profile (zero initial emittance still)
//----------------------------------------------------------------------------
        
gen_dist: DISTRIBUTION, TYPE = FLATTOP,
        SIGMAX = 0.00040 * 2, 
        SIGMAY = 0.00040 * 2,
        SIGMAT = 1.15e-12,
        CUTOFFLONG = 4.0,
        NBIN = 9,
        SBIN = 100, 
        EMISSIONSTEPS = 100,
        EMISSIONMODEL = ASTRA,
        EKIN = 0.2,           
        EMITTED = True,        
        WRITETOFILE = True;    //Saves the distribution to a text file

// Cold Gaussian distribution for testing purposes
cold_gaussian: DISTRIBUTION, TYPE = GAUSS,
        SIGMAX = 0.0007 * 2,
        SIGMAPX = 50.0,
        SIGMAY = 0.0007 * 2,
        SIGMAPY = 50.0,
        SIGMAZ = 0.0007 * 2,
        SIGMAPZ = 1.1E6,   
        EMITTED = False,
        INPUTMOUNITS = EV,      
        WRITETOFILE = True; 
 
//----------------------------------------------------------------------------
// Define Field solvers
//----------------------------------------------------------------------------

FS_SC: Fieldsolver, FSTYPE = FFT, // None or FFT
            MX = 32, MY = 32, MT = 32,
            PARFFTX = false, 
            PARFFTY = false, 
            PARFFTT = true,  //parallel in the z direction only
            BCFFTX = open, 
            BCFFTY = open, 
            BCFFTT = open,
            BBOXINCR = 1,
            //ENBINS = 9,
            GREENSF = INTEGRATED;

//----------------------------------------------------------------------------
// Electron Beam Definition

BEAM1:  BEAM, PARTICLE = ELECTRON, pc = P0, NPART = n_particles,
        BFREQ = rf_freq*1e-6, BCURRENT = beam_bunch_charge * rf_freq, CHARGE = -1;

//----------------------------------------------------------------------------
// Initialize Simulation
//----------------------------------------------------------------------------

TRACK, LINE = LINAC, BEAM = BEAM1, MAXSTEPS = 10000000,
      DT = 5e-13, ZSTOP = 5.5;  //TODO: Change back after sirepo.lib fixed
    //DT = {1.0e-13, 5.0e-13}, ZSTOP={0.4, 5.5};

RUN, METHOD = "PARALLEL-T", BEAM = BEAM1, 
    FIELDSOLVER = FS_SC, DISTRIBUTION = gen_dist;
ENDTRACK;

Stop;
Quit;
