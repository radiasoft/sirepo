import math
import srwlib
import numpy as np
from srwlib import *

def createGsnSrcSRW(sigrW,propLen,pulseE,poltype,phE=10e3,sampFact=15,mx=0,my=0):
    
    """
    #sigrW: beam size at waist [m]
    #propLen: propagation length [m] required by SRW to create numerical Gaussian
    #pulseE: energy per pulse [J]
    #poltype: polarization type (0=linear horizontal, 1=linear vertical, 2=linear 45 deg, 3=linear 135 deg, 4=circular right, 5=circular left, 6=total)
    #phE: photon energy [eV]
    #sampFact: sampling factor to increase mesh density
    """
    
    constConvRad = 1.23984186e-06/(4*3.1415926536)  ##conversion from energy to 1/wavelength
    rmsAngDiv = constConvRad/(phE*sigrW)             ##RMS angular divergence [rad]
    sigrL=math.sqrt(sigrW**2+(propLen*rmsAngDiv)**2)  ##required RMS size to produce requested RMS beam size after propagation by propLen
    
        
    #***********Gaussian Beam Source
    GsnBm = SRWLGsnBm() #Gaussian Beam structure (just parameters)
    GsnBm.x = 0 #Transverse Positions of Gaussian Beam Center at Waist [m]
    GsnBm.y = 0
    GsnBm.z = propLen #Longitudinal Position of Waist [m]
    GsnBm.xp = 0 #Average Angles of Gaussian Beam at Waist [rad]
    GsnBm.yp = 0
    GsnBm.avgPhotEn = phE #Photon Energy [eV]
    GsnBm.pulseEn = pulseE #Energy per Pulse [J] - to be corrected
    GsnBm.repRate = 1 #Rep. Rate [Hz] - to be corrected
    GsnBm.polar = poltype #1- linear horizontal?
    GsnBm.sigX = sigrW #Horiz. RMS size at Waist [m]
    GsnBm.sigY = GsnBm.sigX #Vert. RMS size at Waist [m]

    GsnBm.sigT = 10e-15 #Pulse duration [s] (not used?)
    GsnBm.mx = mx #Transverse Gauss-Hermite Mode Orders
    GsnBm.my = my

    #***********Initial Wavefront
    wfr = SRWLWfr() #Initial Electric Field Wavefront
    wfr.allocate(1, 1000, 1000) #Numbers of points vs Photon Energy (1), Horizontal and Vertical Positions (dummy)
    wfr.mesh.zStart = 0.0 #Longitudinal Position [m] at which initial Electric Field has to be calculated, i.e. the position of the first optical element
    wfr.mesh.eStart = GsnBm.avgPhotEn #Initial Photon Energy [eV]
    wfr.mesh.eFin = GsnBm.avgPhotEn #Final Photon Energy [eV]

    wfr.unitElFld = 1 #Electric field units: 0- arbitrary, 1- sqrt(Phot/s/0.1%bw/mm^2), 2- sqrt(J/eV/mm^2) or sqrt(W/mm^2), depending on representation (freq. or time)

    distSrc = wfr.mesh.zStart - GsnBm.z
    #Horizontal and Vertical Position Range for the Initial Wavefront calculation
    #can be used to simulate the First Aperture (of M1)
    #firstHorAp = 8.*rmsAngDiv*distSrc #[m]
    xAp = 8.*sigrL
    yAp = xAp #[m]
    
    wfr.mesh.xStart = -0.5*xAp #Initial Horizontal Position [m]
    wfr.mesh.xFin = 0.5*xAp #Final Horizontal Position [m]
    wfr.mesh.yStart = -0.5*yAp #Initial Vertical Position [m]
    wfr.mesh.yFin = 0.5*yAp #Final Vertical Position [m]
    
    sampFactNxNyForProp = sampFact #sampling factor for adjusting nx, ny (effective if > 0)
    arPrecPar = [sampFactNxNyForProp]
    
    srwl.CalcElecFieldGaussian(wfr, GsnBm, arPrecPar)
    
    ##Beamline to propagate to waist
    
    optDriftW=SRWLOptD(propLen)
    propagParDrift = [0, 0, 1., 0, 0, 1.1, 1.2, 1.1, 1.2, 0, 0, 0]
    optBLW = SRWLOptC([optDriftW],[propagParDrift])
    #wfrW=deepcopy(wfr)
    srwl.PropagElecField(wfr, optBLW)
    
    return wfr

def createDriftLensBL2(Length,f):
    """
    #Create beamline for propagation from end of crystal to end of cavity and through lens (representing a mirror)
    #First propagate by Length, then through lens with focal length f
    #Length: drift length [m]
    #f: focal length
    """
    #f=Lc/4 + df
    optDrift=SRWLOptD(Length)
    optLens = SRWLOptL(f, f)
    propagParLens = [0, 0, 1., 0, 0, 1., 1., 1., 1., 0, 0, 0]
    propagParDrift = [0, 0, 1., 0, 0, 1., 1., 1., 1., 0, 0, 0]
    #propagParLens = [0, 0, 1., 0, 0, 1.4, 2., 1.4, 2., 0, 0, 0]
    #propagParDrift = [0, 0, 1., 0, 0, 1.1, 1.2, 1.1, 1.2, 0, 0, 0]
    DriftLensBL = SRWLOptC([optDrift,optLens],[propagParDrift,propagParLens])
    return DriftLensBL

def createDriftLensBL(Lc,df):
    """
    #Create beamline for propagation from center of cell to end and through lens (representing a mirror)
    #First propagate Lc/2, then through lens with focal length Lc/2 + df
    #Lc: cavity length [m]
    #df: focusing error
    """
    f=Lc/4 + df
    optDrift=SRWLOptD(Lc/2)
    optLens = SRWLOptL(f, f)
    propagParLens = [0, 0, 1., 0, 0, 1., 1., 1., 1., 0, 0, 0]
    propagParDrift = [0, 0, 1., 1, 0, 1., 1., 1., 1., 0, 0, 0]
    #propagParLens = [0, 0, 1., 0, 0, 1.4, 2., 1.4, 2., 0, 0, 0]
    #propagParDrift = [0, 0, 1., 0, 0, 1.1, 1.2, 1.1, 1.2, 0, 0, 0]
    DriftLensBL = SRWLOptC([optDrift,optLens],[propagParDrift,propagParLens])
    return DriftLensBL

def createDriftBL(Lc):
    """
    #Create drift beamline container that propagates the wavefront through half the cavity
    #Lc is the length of the cavity
    """
    optDrift=SRWLOptD(Lc/2)
    propagParDrift = [0, 0, 1., 0, 0, 1., 1., 1., 1., 0, 0, 0]
    #propagParDrift = [0, 0, 1., 0, 0, 1.1, 1.2, 1.1, 1.2, 0, 0, 0]
    DriftBL = SRWLOptC([optDrift],[propagParDrift])
    return DriftBL

def createBL1to1(L,dfof=0):

    """
    ##Define beamline geometric variables.
    #L: drift length before and after lens
    #dfof: focal length variation factor (=0 for no variation; can be positive or negative)
    """
    
    
    ##Drift lengths between elements beginning with source to 1st crystal and ending with last crystal to start of undulator.
    
    
    ##focal length in meters
    f=(L/2)*(1+dfof)
    
    #Lens    
    optLens = SRWLOptL(f, f) 
    #Drift spaces
    optDrift1=SRWLOptD(L)
    optDrift2=SRWLOptD(L)
       

    #***********Wavefront Propagation Parameters:
    #[0]: Auto-Resize (1) or not (0) Before propagation
    #[1]: Auto-Resize (1) or not (0) After propagation
    #[2]: Relative Precision for propagation with Auto-Resizing (1. is nominal)
    #[3] Type of the propagator:
        #0 - Standard - Fresnel (it uses two FFTs);
        #1 - Quadratic Term - with semi-analytical treatment of the quadratic (leading) phase terms (it uses two FFTs);
        #2 - Quadratic Term - Special - special case;
        #3 - From Waist - good for propagation from "waist" over a large distance (it uses one FFT);
        #4 - To Waist - good for propagation to a "waist" (e.g. some 2D focus of an optical system) over some distance (it uses one FFT).
    #[4]: Do any Resizing on Fourier side, using FFT, (1) or not (0)
    #[5]: Horizontal Range modification factor at Resizing (1. means no modification)
    #[6]: Horizontal Resolution modification factor at Resizing
    #[7]: Vertical Range modification factor at Resizing
    #[8]: Vertical Resolution modification factor at Resizing
    #[9]: Type of wavefront Shift before Resizing (not yet implemented)
    #[10]: New Horizontal wavefront Center position after Shift (not yet implemented)
    #[11]: New Vertical wavefront Center position after Shift (not yet implemented)
    
    #propagParLens = [0, 0, 1., 0, 0, 1., 1.5, 1., 1.5, 0, 0, 0]
    #propagParDrift = [0, 0, 1., 0, 0, 1., 1., 1., 1., 0, 0, 0]
    
    propagParLens = [0, 0, 1., 0, 0, 1.4, 2., 1.4, 2., 0, 0, 0]
    propagParDrift = [0, 0, 1., 0, 0, 1.1, 1.2, 1.1, 1.2, 0, 0, 0]
    
    ##Beamline consruction
    optBL1to1 = SRWLOptC([optDrift1,optLens,optDrift2],[propagParDrift,propagParLens,propagParDrift])
    
    return optBL1to1


def createReflectionOffFocusingMirrorBL(L,f,strDataFolderName,strMirSurfHeightErrInFileName):
    """
    #Create an SRW beamline container that will propagate a length L
    #then reflect off a flat mirror followed by a lens. Finally, propagate by L again.
    #L: length of propagation [m]
    #f: focal length of mirror [m]
    #strDataFolderName: Folder name where mirror data file is
    #strMirSurfHeightErrInFileName: File name for mirror slope error file
    #Assuming waist to waist propagation, we want f~L/2 (Note that this isn't a perfect identity
    #map in phase space due to the Rayleigh length of the mode)
    """
    #Drift
    optDrift1=SRWLOptD(L)
    
    #Transmission element to simulate mirror slope error
    #angM1 = np.pi #Incident Angle of M1 [rad] ( 1.8e-3 in Ex. 9 )
    #angM1 =  3.14 #Incident Angle of M1 [rad]
    angM1 = 1.e-2
    heightProfData = srwl_uti_read_data_cols(os.path.join(os.getcwd(), strDataFolderName, strMirSurfHeightErrInFileName), _str_sep='\t', _i_col_start=0, _i_col_end=1)
    opTrErM1 = srwl_opt_setup_surf_height_1d(heightProfData, _dim='y', _ang=angM1, _amp_coef=1) #_amp_coef=1e4
    
    #print('   Saving optical path difference data to file (for viewing/debugging) ... ', end='')
    #opPathDifErM1 = opTrErM1.get_data(3, 3)
    #srwl_uti_save_intens_ascii(opPathDifErM1, opTrErM1.mesh, os.path.join(os.getcwd(), strDataFolderName, strMirOptPathDifOutFileName01), 0,
    #                       ['', 'Horizontal Position', 'Vertical Position', 'Opt. Path Diff.'], _arUnits=['', 'm', 'm', 'm'])
    
    
    #Lens    
    optLens = SRWLOptL(f, f) 
    
    #Propagation parameters
    propagParLens = [0, 0, 1., 0, 0, 1.4, 2., 1.4, 2., 0, 0, 0]
    propagParDrift = [0, 0, 1., 0, 0, 1.1, 1.2, 1.1, 1.2, 0, 0, 0]
    #propagParDrift = [0, 0, 1., 0, 0, 1., 1., 1., 1., 0, 0, 0]
    #propagParLens = [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    prPar0 =    [0, 0, 1., 1, 0, 1.,   1., 1.,   1.,  0, 0, 0]
    
    #Construct beamline
    optBL = SRWLOptC([optDrift1,opTrErM1,optLens,optDrift1],[propagParDrift,prPar0,propagParLens,propagParDrift])
    #optBL = SRWLOptC([optDrift1,optLens,optDrift1],[propagParDrift,propagParLens,propagParDrift])
    return optBL

def createABCDbeamline(A,B,C,D):
    """
    #Use decomposition of ABCD matrix into kick-drift-kick Pei-Huang 2017 (https://arxiv.org/abs/1709.06222)
    #Construct corresponding SRW beamline container object
    #A,B,C,D are 2x2 matrix components.
    """
    
    f1= B/(1-A)
    L = B
    f2 = B/(1-D)
    
    optLens1 = SRWLOptL(f1, f1)
    optDrift=SRWLOptD(L)
    optLens2 = SRWLOptL(f2, f2)
    
    propagParLens1 = [0, 0, 1., 0, 0, 1, 1, 1, 1, 0, 0, 0]
    propagParDrift = [0, 0, 1., 0, 0, 1, 1, 1, 1, 0, 0, 0]
    propagParLens2 = [0, 0, 1., 0, 0, 1, 1, 1, 1, 0, 0, 0]
    
    optBL = SRWLOptC([optLens1,optDrift,optLens2],[propagParLens1,propagParDrift,propagParLens2])
    return optBL

def createCrystal(n0,n2,L_cryst):
    """
    #Create a set of optical elements representing a crystal.
    #Treat as an optical duct
    #ABCD matrix found here: https://www.rp-photonics.com/abcd_matrix.html
    #n(r) = n0 - 0.5 n2 r^2 
    #n0: Index of refraction along the optical axis
    #n2: radial variation of index of refraction
    """
    
    if n2==0:
        optBL=createDriftBL(2*L_cryst) #Note that this drift function divides length by 2
        #print("L_cryst/n0=",L_cryst/n0)
    else:
        gamma = np.sqrt(n2/n0)
        A = np.cos(gamma*L_cryst)
        B = (1/(gamma))*np.sin(gamma*L_cryst)
        C = -gamma*np.sin(gamma*L_cryst)
        D = np.cos(gamma*L_cryst)
        optBL=createABCDbeamline(A,B,C,D)
    
    return optBL