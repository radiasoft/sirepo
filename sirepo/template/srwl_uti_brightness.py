# -*- coding: utf-8 -*-
#############################################################################
# SRW Brightness Calculation
#############################################################################

import math
from scipy import special
from boazextra import *
import numpy as np
from pykern import pkresource

#fluxcorrectionarray = np.loadtxt("IgorFiles/IGOR_wave_data/gwSrwBrilUndHarmUnivFlux.txt")
#TODO(pjm): need a way to initialize this module with a set of static datafiles
fluxcorrectionarray = np.loadtxt(pkresource.filename('template/srw/gwSrwBrilUndHarmUnivFlux.txt'))

def KtoE(K,E_elec,lam_u,n):
    #compute photon Energy (in KeV) from a given K value
    #E_elec: electron energy in GeV
    #lam: undulator wavelength in cm
    #n: harmonic number
    return 0.950*n*E_elec**2/lam_u/(1+K**2/2)


def srwl_compute_flux(Ib,kx,kz,phix,phiz,n,nPer,enDetPar,relEnSpr):
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

    return C0*N*Ib*(n*k12/(1+ke2/2))*JJbs*factDetunAndEnSpr*srwBrilUndPhotEnDetunCor(relEnSpr, enDetPar, k12, k22, n)

def SRW_flux_energy(Ib,kxmax,kzmax,kmin,numkpts,E_elec,lam_u,phix,phiz,n,nPer,enDetPar,relEnSpr):
    #compute kvals and Evals
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

    #compute flux for each k value
    fluxvals = []
    for j in range(len(kvals)):
        #print j
        fluxvals.append(srwl_compute_flux(Ib,kxvals[j],kzvals[j],0,0,n,nPer,enDetPar,relEnSpr))
    return (Evals,fluxvals)


def srwl_compute_size(sig,lambda_n,L):
     return math.sqrt(sig**2 + (2.740/(4*math.pi))**2*lambda_n*L)

def srwl_compute_divergence(sigp,lambda_n,L):
     return math.sqrt(sigp**2 + 0.69**2*lambda_n/L)

def srwl_compute_angularflux(Ib,kx,kz,phix,phiz,n,nPer,enDetPar,relEnSpr):
    return

def srwl_compute_brightness(Ib,kx,kz,phix,phiz,harmNum,nPer,enDetPar,relEnSpr,L,gamma,sigx,sigz,sigxp,sigzp):
    #compute Brightness from undulator by dividing flux by Sigx*Sigx'*Sigz*Sigz', with Sigx,z and Sigz,z'
    #photon beamsize at center of undulator
    #uses same parameters as srwl_compute_flux, plus
    #
    #L: undulator length
    #gamma: electron beam relativistic factor
    #sigx: RMS horizontal electron beam size
    #sigz: RMS vertical electron beam size
    #sigxp: RMS horizontal electron beam divergence
    #sigzp: RMS vertical electron beam divergence

    #So far, we don't take the energy spread and detuning into account.
    #To be added, soon.

    flux = fluxSRW(Ib,kx,kz,phix,phiz,harmNum,nPer,enDetPar,relEnSpr)

    lambda_n=KtoLambda(lamu,harmNum,gamma,math.sqrt(kx**2+kz**2))

    Sigmax = Sigmaxz(sigx,lambda_n,L)
    Sigmaz = Sigmaxz(sigz,lambda_n,L)
    Sigmaxp = Sigmaxzp(sigxp,lambda_n,L)
    Sigmazp = Sigmaxzp(sigzp,lambda_n,L)

    return flux/(Sigmax*Sigmaxp*Sigmaz*Sigmazp)


#def KtoLambda(lamu,n,gamma,K):
#     return lamu/(2*gamma**2)*(1+K**2/2)




#    srwl_compute_flux(Ib,kx,kz,phix,phiz,n,nPer,enDetPar,relEnSpr):


#def srwl_size_energy():

#def srwl_divergence_energy():

#def srwl_angularflux_energy():

#def srwl_brightness_energy():


def sigma_r(lambda_n,L):
     return (2.740/(4*math.pi))*math.sqrt(lambda_n*L)

def sigma_rp(lambda_n,L):
     return 0.69*math.sqrt(lambda_n/L)
