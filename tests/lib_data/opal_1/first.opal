
Title, string="AWA Photoinjector";

REAL beta = sqrt(1 - (1 / pow(gamma, 2)));
REAL edes = 1.4e-09;
REAL gamma = (edes + emass) / emass;
REAL ibf = 550.0;
REAL isf = 273.0;
REAL ksbf = (ibf / 550) * 0.12017;
REAL n_particles = 10000.0;
REAL p0 = gamma * beta * emass;
REAL sf = (isf / 440) * 0.61126;


OP1: option,autophase=4.0,psdumpfreq=100.0,version=10900.0;

DR1: DRIFT,l=10.0;
DR2: DRIFT,l=-0.2927;
DR3: DRIFT,l=-0.5;
GUN: RFCAVITY,fmapfn="DriveGun_2D.T7",freq=1300.0,l=0.2927,type=STANDING,volt=60.0;
BF: SOLENOID,fmapfn="BF_550_2D.T7",ks=KSBF,l=0.5;
M: SOLENOID,fmapfn="M_440_2D.T7",ks=SF,l=0.5;

"GUN#0": GUN,elemedge=0;
"BF#0": BF,elemedge=0.0;
"M#0": M,elemedge=0.0;
"DR1#0": DR1,elemedge=0.5;
DRIVE: LINE=("GUN#0","BF#0","M#0","DR1#0");


FS_SC: fieldsolver,bboxincr=1.0,fstype="FFT",mt=16.0,mx=16.0,my=16.0;
BEAM1: beam,bcurrent=1.3,bfreq=1300.0,npart=n_particles,particle="ELECTRON",pc=P0;
DIST: distribution,cutofflong=4.0,ekin=0.55,emissionmodel="ASTRA",emissionsteps=100.0,emitted=true,nbin=9.0,sigmax=0.00075,sigmay=0.00075,tfall=6e-12,tpulsefwhm=2e-11,trise=6e-12,type="FLATTOP";
TR1: track,beam=BEAM1,dt=3e-12,line=DRIVE,maxsteps=19000.0,zstop=5.0;
 run, beam=BEAM1,distribution=Dist,fieldsolver=FS_SC,method="PARALLEL-T";
endtrack;
