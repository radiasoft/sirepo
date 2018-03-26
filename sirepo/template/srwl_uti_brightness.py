# -*- coding: utf-8 -*-
#############################################################################
# SRW Brightness Calculation
#############################################################################

import math
from scipy import special
from boazextra import *
import numpy as np
from pykern import pkresource

# fluxcorrectionarray = np.loadtxt("IgorFiles/IGOR_wave_data/gwSrwBrilUndHarmUnivFlux.txt")
# divcorrectionarray = np.loadtxt("IgorFiles/IGOR_wave_data/gwSrwBrilUndHarmUnivDiv.txt")
# sizecorrectionarray = np.loadtxt("IgorFiles/IGOR_wave_data/gwSrwBrilUndHarmUnivSize.txt")
#TODO(pjm): need a way to initialize this module with a set of static datafiles
fluxcorrectionarray = np.loadtxt(pkresource.filename("template/srw/brilliance/gwSrwBrilUndHarmUnivFlux.txt"))
divcorrectionarray = np.loadtxt(pkresource.filename("template/srw/brilliance/gwSrwBrilUndHarmUnivDiv.txt"))
sizecorrectionarray = np.loadtxt(pkresource.filename("template/srw/brilliance/gwSrwBrilUndHarmUnivSize.txt"))

#srwlib.srwl_uti_read_data_cols
#np.array(srwlib.srwl_uti_read_data_cols('gwSrwBrilUndHarmUnivFlux.txt', '\t'))
#srwl_uti_interp_2d(_x, _y, _x_min, _x_step, _nx, _y_min, _y_step, _ny, _ar_f, _ord=3, _ix_per=1, _ix_ofst=0)

def KtoE(K,E_elec,lam_u,n):
    #compute photon Energy (in KeV) from a given K value
    #E_elec: electron energy in GeV
    #lam_u: undulator wavelength in cm
    #n: harmonic number
    return 0.9496376*n*E_elec**2/lam_u/(1+K**2/2)


def CalcK(B,lam_u):
    #compute undulator K value from magnetic field B [T] and period lam_u [m]
    return 93.36*B*lam_u

def CalcFluxUnd(Ib,kx,kz,phix,phiz,n,nPer,enDetPar,relEnSpr):
    #flux function in SRW Igor Pro
    #returns flux [#photons/sec/0.1%bandwidth]
    #Ib: beam current in Amps
    #kx: horizontal undulator strength parameter
    #kz: vertical undulator strength parameter
    #phix: horizontal undulator phase parameter
    #phiz: vertical undulator phase parameter
    #n: harmonic number of undulator spectrum
    #nPer: number of periods in undulator magnetic array
    #enDetPar: relative difference from undulator energy from on resonance peak value dE/E
    #relEnSpr: energy spread of electron beam


    def JJbsfun(k12,k22,n):
        #same as srwBrilUndBessFactExt in SRW-Igor
        qq=(n/4.)*(k12-k22)/(1+0.5*(k12+k22))
        return (special.jv((n-1.)/2,qq)-special.jv((n+1.)/2,qq))**2+(k22/k12)*(special.jv((n-1.)/2,qq)+special.jv((n+1.)/2,qq))**2

    def srwBrilUndPhotEnDetunCor(dEperE, relEnSpr, K1e2, K2e2, n):
        #additional correction factor from detuning and energy spread... explanation for this?
        #refered to as G function in notes
        fit_width = 0.63276
        auxMult = n*n*(K1e2 + K2e2)/(1 + (K1e2 + K2e2)/2)/(fit_width*fit_width)
        a_sig = auxMult*2*relEnSpr
        a_sigE2d2 = a_sig*a_sig/2
        genFact = 0.5 + 0.5*math.exp(a_sigE2d2)*(1 - special.erf(math.sqrt(a_sigE2d2)))
        if dEperE >= 0:
            res = genFact
        else:
            relarg = auxMult*dEperE
            res = math.exp(relArg)*genFact
        return res

    C0=4.5546497e13 #convConstFlux = alpha dw/w /e (dw/w = 0.001)
    #n=harmNum
    N=nPer
    normDetun = n*N*enDetPar
    normEnSpr = n*N*relEnSpr
    ke2=kx**2+kz**2
    phix=0 #what is phix?
    phiz=0 #what is phiz?
    phi0=0.5*math.atan((kz**2)*math.sin(2*phix)+(kx**2)*math.sin(2*phiz)/((kz**2)*math.cos(2*phix)+(kx**2)*math.cos(2*phiz)))
    k12=(kz**2)*(math.cos(phix-phi0))**2+(kx**2)*(math.cos(phiz-phi0))**2
    k22=(kz**2)*(math.sin(phix-phi0))**2+(kx**2)*(math.sin(phiz-phi0))**2
    JJbs=JJbsfun(k12,k22,n)
    #now get additional factors from energy spread and detuning
    #factDetunAndEnSpr = math.pi/2 #assumes zero detuning and energy spread, needs to be replaced with interpolation of external correction array
    factDetunAndEnSpr = interp(normDetun,normEnSpr,fluxcorrectionarray,-10,0,0.033389,0.02512565,600,200)
    GG=srwBrilUndPhotEnDetunCor(relEnSpr, enDetPar, k12, k22, n)

    return C0*N*Ib*(n*k12/(1+ke2/2))*JJbs*factDetunAndEnSpr*GG

def srwl_und_flux_en(Ib,kxmax,kzmax,kmin,numkpts,E_elec,lam_u,phix,phiz,n,nPer,enDetPar,relEnSpr):
    #compute kvals and Evals
    #lam_u: undulator wavelength in cm
    kmax = math.sqrt(kxmax**2+kzmax**2)
    dk = (kmax - kmin)/numkpts
    kvals=np.arange(kmin, kmax,dk)
    #compute Evals
    Evals = KtoE(kvals,E_elec,lam_u,n)
    #compute kxvals and kzvals
    if kxmax > kmin:
        dkx = (kxmax-kmin)/numkpts
        kxvals = np.arange(kmin,kxmax,dkx)
    else:
        kxvals = np.zeros(numkpts)

    if kzmax > kmin:
        dkz = (kzmax-kmin)/numkpts
        kzvals = np.arange(kmin,kzmax,dkz)
    else:
        kzvals = np.zeros(numkpts)

    #compute flux for each k value
    fluxvals = []
    for j in range(len(kvals)):
        #print j
        fluxvals.append(CalcFluxUnd(Ib,kxvals[j],kzvals[j],0,0,n,nPer,enDetPar,relEnSpr))
    return (Evals,fluxvals)


def CalcSizeUnd(sigsq,L,K,E_elec,lam_u,n,nPer,enDetPar,relEnSpr):
    #sigsq: hor. or vert. RMS electron beamsize squared [m^2]
    #L: length of undulator [m]
    #K: K value of undulator
    #E_elec: Energy of electron beam [GeV]
    #n: harmonic number
    #lam_u: undulator wavelength in cm
    normDetun = n*nPer*enDetPar
    normEnSpr = n*nPer*relEnSpr
    convConstSize = 0.5*1.239842e-06*L
    energy = 1000*KtoE(K,E_elec,lam_u,n)
    invSqrt2=1/math.sqrt(2)
    factAngDivDetunAndEnSpr = interp(normDetun,normEnSpr,sizecorrectionarray,-10,0,0.033389,0.02512565,600,200)*invSqrt2
    return math.sqrt(sigsq + (convConstSize/energy)*factAngDivDetunAndEnSpr**2)

def srwl_und_size_en(kxmax,kzmax,kmin,numkpts,E_elec,lam_u,phix,phiz,n,nPer,enDetPar,relEnSpr,sigsq):
    #compute kvals and Evals
    #lam_u: undulator wavelength in cm
    kmax = math.sqrt(kxmax**2+kzmax**2)
    dk = (kmax - kmin)/numkpts
    kvals=np.arange(kmin, kmax,dk)
    #compute Evals
    Evals = KtoE(kvals,E_elec,lam_u,n)
    #compute kxvals and kzvals
    dkx = (kxmax -kmin)/numkpts
    dkz = (kzmax -kmin)/numkpts
    kxvals = np.arange(kmin,kxmax,dkx)
    kzvals = np.arange(kmin,kzmax,dkz)

    L=(lam_u/100.)*nPer
    #compute size for each k value
    sizevals = []
    for j in range(len(kvals)):
        sizevals.append(CalcSizeUnd(sigsq,L,kvals[j],E_elec,lam_u,n,nPer,enDetPar,relEnSpr))
    return (Evals,sizevals)

def CalcDivergenceUnd(sigpsq,L,K,E_elec,lam_u,n,nPer,enDetPar,relEnSpr):
    #sigpsq: hor. or vert. RMS electron divergence squared
    #L: length of undulator [m]
    #K: K value of undulator
    #E_elec: Energy of electron beam [GeV]
    #n: harmonic number
    #lam_u: undulator wavelength in cm
    normDetun = n*nPer*enDetPar
    normEnSpr = n*nPer*relEnSpr
    convConstDiv = 2*1.239842e-06/L
    energy = 1000*KtoE(K,E_elec,lam_u,n)
    invSqrt2=1/math.sqrt(2)
    factAngDivDetunAndEnSpr = interp(normDetun,normEnSpr,divcorrectionarray,-10,0,0.033389,0.02512565,600,200)*invSqrt2
    return math.sqrt(sigpsq + (convConstDiv/energy)*factAngDivDetunAndEnSpr**2)

def srwl_und_div_en(kxmax,kzmax,kmin,numkpts,E_elec,lam_u,phix,phiz,n,nPer,enDetPar,relEnSpr,sigpsq):
    #compute kvals and Evals
    #lam_u: undulator wavelength in cm
    kmax = math.sqrt(kxmax**2+kzmax**2)
    dk = (kmax - kmin)/numkpts
    kvals=np.arange(kmin, kmax,dk)
    #compute Evals
    Evals = KtoE(kvals,E_elec,lam_u,n)
    #compute kxvals and kzvals
    dkx = (kxmax -kmin)/numkpts
    dkz = (kzmax -kmin)/numkpts
    kxvals = np.arange(kmin,kxmax,dkx)
    kzvals = np.arange(kmin,kzmax,dkz)

    L=(lam_u/100.)*nPer
    #compute divergence for each k value
    divergevals = []
    for j in range(len(kvals)):
        divergevals.append(CalcDivergenceUnd(sigpsq,L,kvals[j],E_elec,lam_u,n,nPer,enDetPar,relEnSpr))
    return (Evals,divergevals)


def CalcAngularfluxUnd(Ib,kx,kz,phix,phiz,n,nPer,E_elec,lam_u,enDetPar,relEnSpr,sigpxsq,sigpzsq):
    #Ib: beam current in Amps
    #kx: horizontal undulator strength parameter
    #kz: vertical undulator strength parameter
    #phix: horizontal undulator phase parameter
    #phiz: vertical undulator phase parameter
    #n: harmonic number of undulator spectrum
    #nPer: number of periods in undulator magnetic array
    #enDetPar: relative difference from undulator energy from on resonance peak value dE/E
    #relEnSpr: energy spread of electron beam
    #lam_u: undulator wavelength in cm
    L=(lam_u/100.)*nPer
    convConstDiv = 2*1.239842e-06/L
    K=math.sqrt(kx**2+kz**2)
    flux = CalcFluxUnd(Ib,kx,kz,phix,phiz,n,nPer,enDetPar,relEnSpr)
    divx = CalcDivergenceUnd(sigpxsq,L,K,E_elec,lam_u,n,nPer,enDetPar,relEnSpr)
    divz = CalcDivergenceUnd(sigpzsq,L,K,E_elec,lam_u,n,nPer,enDetPar,relEnSpr)
    fluxdivide = (2e+06*math.pi)*divx*divz
    return flux/fluxdivide

def srwl_und_ang_flux_en(Ib,kxmax,kzmax,kmin,numkpts,E_elec,lam_u,phix,phiz,n,nPer,enDetPar,relEnSpr,sigpxsq,sigpzsq):
     #compute kvals and Evals
     #lam_u: undulator wavelength in cm
    kmax = math.sqrt(kxmax**2+kzmax**2)
    dk = (kmax - kmin)/numkpts
    kvals=np.arange(kmin, kmax,dk)
    #compute Evals
    Evals = KtoE(kvals,E_elec,lam_u,n)
    #compute kxvals and kzvals
    dkx = (kxmax -kmin)/numkpts
    dkz = (kzmax -kmin)/numkpts
    kxvals = np.arange(kmin,kxmax,dkx)
    kzvals = np.arange(kmin,kzmax,dkz)

    L=(lam_u/100.)*nPer
    #compute flux for each k value
    angularflux = []
    for j in range(len(kvals)):
        angularflux.append(CalcAngularfluxUnd(Ib,kxvals[j],kzvals[j],phix,phiz,n,nPer,E_elec,lam_u,enDetPar,relEnSpr,sigpxsq,sigpzsq))
    return (Evals,angularflux)


def CalcBrightnessUnd(Ib,kx,kz,phix,phiz,n,E_elec,lam_u,nPer,enDetPar,relEnSpr,L,sigxsq,sigzsq,sigxpsq,sigzpsq):
    #compute Brightness from undulator by dividing flux by Sigx*Sigx'*Sigz*Sigz', with Sigx,z and Sigz,z'
    #photon beamsize at center of undulator
    #uses same parameters as srwl_compute_flux, plus
    #
    #L: undulator length
    #sigx: RMS horizontal electron beam size
    #sigz: RMS vertical electron beam size
    #sigxp: RMS horizontal electron beam divergence
    #sigzp: RMS vertical electron beam divergence
    cst=(math.pi*2)**2*1e12

    flux = CalcFluxUnd(Ib,kx,kz,phix,phiz,n,nPer,enDetPar,relEnSpr)

    K = math.sqrt(kx**2+kz**2)

    Sigmax = CalcSizeUnd(sigxsq,L,K,E_elec,lam_u,n,nPer,enDetPar,relEnSpr)
    Sigmaz = CalcSizeUnd(sigzsq,L,K,E_elec,lam_u,n,nPer,enDetPar,relEnSpr)
    Sigmaxp = CalcDivergenceUnd(sigxpsq,L,K,E_elec,lam_u,n,nPer,enDetPar,relEnSpr)
    Sigmazp = CalcDivergenceUnd(sigzpsq,L,K,E_elec,lam_u,n,nPer,enDetPar,relEnSpr)

    return flux/(cst*Sigmax*Sigmaxp*Sigmaz*Sigmazp)

def srwl_und_bright_en(Ib,kx,kz,phix,phiz,n,E_elec,lam_u,nPer,enDetPar,relEnSpr,L,sigxsq,sigzsq,sigxpsq,sigzpsq,kxmax,kzmax,kmin,numkpts):
    #compute kvals and Evals
    #lam_u: undulator wavelength in cm
    kmax = math.sqrt(kxmax**2+kzmax**2)
    dk = (kmax - kmin)/numkpts
    kvals=np.arange(kmin, kmax,dk)
    #compute Evals
    Evals = KtoE(kvals,E_elec,lam_u,n)
    #compute kxvals and kzvals
    dkx = (kxmax -kmin)/numkpts
    dkz = (kzmax -kmin)/numkpts
    kxvals = np.arange(kmin,kxmax,dkx)
    kzvals = np.arange(kmin,kzmax,dkz)

    brightnessvals = []
    for j in range(len(kvals)):
           brightnessvals.append(CalcBrightnessUnd(Ib,kxvals[j],kzvals[j],phix,phiz,n,E_elec,lam_u,nPer,enDetPar,relEnSpr,L,sigxsq,sigzsq,sigxpsq,sigzpsq))
    return (Evals,brightnessvals)
