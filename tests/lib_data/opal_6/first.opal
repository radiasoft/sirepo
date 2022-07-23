
"OPT1": option,autophase=4.0,psdumpfreq=5000000.0,statdumpfreq=1000.0,version=10900.0;

"CC1": RFCAVITY,fmapfn="./map/TESLA_SF7.T7",freq=1300.0,l=1.3492,lag=-0.29588672123275295,volt=29.576267706602067;
"CC1#0": "CC1",elemedge=2.1229889999999996;
LINAC: LINE=("CC1#0");


"GEN_DIST": distribution,cutoffr=1.0,ekin=0.55,emissionsteps=100.0,emitted=true,nbin=9.0,sigmar=0.0016311995860689569,tpulsefwhm=1.1899831482510942e-11,type="FLATTOP",writetofile=true;
"FS_SC": fieldsolver,bboxincr=1.0,fstype="FFT",mt=32.0,mx=32.0,my=32.0, PARFFTX=true,PARFFTY=true,PARFFTT=true;
"BEAM1": beam,bcurrent=0.52,bfreq=1300.0,charge=-1.0,npart=60000,particle="ELECTRON",pc=1e-06;
"TR1": track,beam=BEAM1,dt={1.0e-13,2.0e-13},line=LINAC,maxsteps=2500000.0,zstop={0.28,8.25};
 run, beam=BEAM1,distribution=GEN_DIST,fieldsolver=FS_SC,method="PARALLEL-T";
endtrack;
