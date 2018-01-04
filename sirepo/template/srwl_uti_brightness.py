# -*- coding: utf-8 -*-
u"""
This script is to parse SRW Python scripts and to produce JSON-file with the parsed data.
It's highly dependent on the external Sirepo/SRW libraries and is written to allow parsing of the .py files using
SRW objects.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

#TODO(pjm): this is a place-holder module until the brightness calculation is integrated into srwlib

#############################################################################
# SRW Brightness Calculation
#############################################################################

import math
from scipy import special

def srwl_compute_flux(Ib,kx,kz,phix,phiz,harmNum,nPer,enDetPar,relEnSpr):
    #flux function in SRW Igor Pro
    #returns flux [#photons/sec/0.1%bandwidth]
    #Ib: beam current in Amps
    #kx: horizontal undulator strength parameter
    #kz: vertical undulator strength parameter
    #phix: horizontal undulator phase parameter
    #phiz: vertical undulator phase parameter
    #harmNum: harmonic number of undulator spectrum
    #nPer: number of periods in undulator magnetic array
    #enDetPar: relative difference from undulator energy from on resonance peak value dE/E
    #relEnSpr: energy spread of electron beam


    def JJbsfun(k12,k22,n):
        #same as srwBrilUndBessFactExt in SRW-Igor
        qq=(n/4.)*(k12-k22)/(1+0.5*(k12+k22))
        return (special.jv((n-1.)/2,qq)-special.jv((n+1.)/2,qq))**2+(k22/k12)*(special.jv((n-1.)/2,qq)+special.jv((n+1.)/2,qq))**2

    def srwBrilUndPhotEnDetunCor(dEperE, relEnSpr, K1e2, K2e2, harmNum):
        #additional correction factor from detuning and energy spread... explanation for this?
        #refered to as G function in notes
        fit_width = 0.63276
        auxMult = harmNum*harmNum*(K1e2 + K2e2)/(1 + (K1e2 + K2e2)/2)/(fit_width*fit_width)
        a_sig = auxMult*2*relEnSpr
        a_sigE2d2 = a_sig*a_sig/2
        genFact = 0.5 + 0.5*math.exp(a_sigE2d2)*(1 - special.erf(math.sqrt(a_sigE2d2)))
        if dEperE >= 0:
            res = genFact
        else:
            relarg = auxMult*dEperE
            res = math.exp(relArg)*genFact
        return res

    CSRW=4.5546497e13 #convConstFlux
    n=harmNum
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
    factDetunAndEnSpr = math.pi/2 #assumes zero detuning and energy spread, needs to be replaced with interpolation of external correction array
    return CSRW*N*Ib*(n*k12/(1+ke2/2))*JJbs*factDetunAndEnSpr*srwBrilUndPhotEnDetunCor(relEnSpr, enDetPar, k12, k22, harmNum)
