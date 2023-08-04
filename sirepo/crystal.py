#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Get polarizability from X0h server (http://x-server.gmca.aps.anl.gov/x0h.html).
For details see http://x-server.gmca.aps.anl.gov/pub/Stepanov_CR_1991_08.pdf.
"""
from __future__ import division

import math
import re

import requests

X0H_SERVER = "https://x-server.gmca.aps.anl.gov/cgi/x0h_form.exe"


def calc_bragg_angle(d, energy_eV, n=1):
    """Calculate Bragg angle from the provided energy and d-spacing.

    Args:
        d (float): interplanar spacing (d-spacing) [A].
        energy_eV (float): photon energy [eV].
        n (int): number of diffraction peak.

    Returns:
        dict: the resulted dictionary with:
            lamda (float): wavelength [nm].
            bragg_angle (float): Bragg angle [rad].
            bragg_angle_deg (float): Bragg angle [deg].
    """
    # Check/convert types first:
    d = float(d)
    energy_eV = float(energy_eV)
    n = int(n)

    lamda = 1239.84193 / energy_eV  # lamda in [nm]
    bragg_angle = math.asin(n * lamda / (2 * d * 0.1))  # convert d from [A] to [nm].
    bragg_angle_deg = 180.0 / math.pi * bragg_angle
    return {
        "lamda": lamda,
        "bragg_angle": bragg_angle,
        "bragg_angle_deg": bragg_angle_deg,
    }


def get_crystal_parameters(material, energy_eV, h, k, l):
    """Obtain parameters for the specified crystal and energy.

    Args:
        material (str): material full name (e.g., 'Silicon').
        energy_eV (float): photon energy [eV].
        h (int): Miller's index h.
        k (int): Miller's index k.
        l (int): Miller's index l.

    Returns:
        dict: crystal parameters:
            d (float): interplanar spacing (d-spacing) [A].
            xr0 (float): real part of the 0-th Fourier component of crystal's polarizability.
            xi0 (float): imaginary part of the 0-th Fourier component of crystal's polarizability.
            xrh (float): real part of the H-th Fourier component of crystal's polarizability (Sigma polarization).
            xih (float): imaginary part of the H-th Fourier component of crystal's polarizability (Sigma polarization).
            bragg_angle_deg (float): Bragg angle [deg].
    """
    # Check/convert types first:
    energy_eV = float(energy_eV)
    h = int(h)
    k = int(k)
    l = int(l)

    energy_keV = energy_eV / 1000.0  # convert to keV
    content = _get_server_data(energy_keV, material, h, k, l)
    crystal_parameters = _get_crystal_parameters(content, [h, k, l])

    return crystal_parameters


def _get_crystal_parameters(content, miller_indices=None):
    """Get reflecting planes distance and polarizability from the server's response.

    Args:
        content: split content of the server's response.
        miller_indices: Miller's indices of reflection.

    Returns:
        dict: crystal parameters.
    """
    a1_list = []  # lattice parameter
    d_server_list = []  # d-spacing from the server
    bragg_angle_list = []
    xr0_list = []
    xi0_list = []
    xrh_list = []
    xih_list = []
    for row in content:
        if re.search("a1=", row):
            a1_list.append(row)
        elif re.search(" d=", row):
            d_server_list.append(row)
        elif re.search("QB=", row):
            bragg_angle_list.append(row)
        elif re.search("xr0=", row):
            xr0_list.append(row)
        elif re.search("xi0=", row):
            xi0_list.append(row)
        elif re.search("xrh", row):
            xrh_list.append(row)
        elif re.search("xih", row):
            xih_list.append(row)
    assert len(a1_list) > 0
    a1 = _parse_xr_xi(a1_list[0])
    d_calculated = a1
    if miller_indices:
        d_calculated /= (sum(n**2 for n in miller_indices)) ** 0.5

    assert len(d_server_list) > 0
    d_server = _parse_xr_xi(d_server_list[0])

    assert len(bragg_angle_list) > 0
    bragg_angle_deg = _parse_xr_xi(bragg_angle_list[0])

    assert len(xr0_list) > 0
    xr0 = _parse_xr_xi(xr0_list[0])
    xi0 = _parse_xr_xi(xi0_list[0])
    xrh = _parse_xr_xi(xrh_list[0])
    xih = _parse_xr_xi(xih_list[0])

    return {
        "a1": a1,
        "d": d_calculated,
        "d_calculated": d_calculated,
        "d_server": d_server,
        "bragg_angle_deg": bragg_angle_deg,
        "xr0": xr0,
        "xi0": xi0,
        "xrh": xrh,
        "xih": xih,
    }


def _get_server_data(energy, material, h, k, l):
    """
    The function gets data from the server and splits it by lines.

    :param energy: energy [keV].
    :param material: material, e.g. Silicon or Germanium
    :param h: Miller's index h.
    :param k: Miller's index k.
    :param l: Miller's index l.
    :return content: split server's response.
    """
    payload = {
        "xway": 2,
        "wave": energy,
        "coway": 0,
        "code": material,
        "i1": h,
        "i2": k,
        "i3": l,
        "df1df2": -1,
        "modeout": 1,
    }
    r = requests.get(X0H_SERVER, params=payload, timeout=5)
    content = r.text
    content = content.split("\n")
    return content


def _parse_xr_xi(string):
    return float(string.split("=")[-1].strip())
