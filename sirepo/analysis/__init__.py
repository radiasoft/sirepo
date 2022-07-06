# -*- coding: utf-8 -*-
"""Data analysus

:copyright: Copyright (c) 2018-2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import numpy
import scipy
import sympy
import sirepo.feature_config
import sirepo.template


def get_fft(t_vals, y_vals):
    import scipy.fftpack
    import scipy.signal

    # fft takes the y data only and assumes it corresponds to equally-spaced x values.
    fft_out = scipy.fftpack.fft(y_vals)

    num_samples = len(y_vals)
    half_num_samples = num_samples // 2

    # should all be the same - this will normalize the frequencies
    sample_period = abs(t_vals[1] - t_vals[0])

    # the first half of the fft data (taking abs() folds in the imaginary part)
    y = 2.0 / num_samples * numpy.abs(fft_out[0:half_num_samples])

    # get the frequencies found
    # fftfreq just generates an array of equally-spaced values that represent the x-axis
    # of the fft of data of a given length.  It includes negative values
    freqs = scipy.fftpack.fftfreq(len(fft_out), d=sample_period)  # / sample_period
    w = 2.0 * numpy.pi * freqs[0:half_num_samples]

    coefs = (2.0 / num_samples) * numpy.abs(fft_out[0:half_num_samples])
    peaks, props = scipy.signal.find_peaks(coefs)
    found_freqs = [v for v in zip(peaks, numpy.around(w[peaks], 3))]

    bin_spread = 10
    min_bin = max(0, peaks[0] - bin_spread) if len(peaks) > 0 else 0
    max_bin = (
        min(half_num_samples, peaks[-1] + bin_spread)
        if len(peaks) > 0
        else half_num_samples
    )
    yy = 2.0 / num_samples * numpy.abs(fft_out[min_bin:max_bin])
    max_yy = numpy.max(yy)
    yy_norm = yy / (max_yy if max_yy != 0 else 1)
    ww = 2.0 * numpy.pi * freqs[min_bin:max_bin]

    max_y = numpy.max(y)
    y_norm = y / (max_y if max_y != 0 else 1)

    return w.tolist(), y_norm.tolist()


def fit_to_equation(x, y, equation, var, params):
    sym_curve = sympy.sympify(equation)
    sym_str = f"{var} {' '.join(params)}"

    syms = sympy.symbols(sym_str)
    sym_curve_l = sympy.lambdify(syms, sym_curve, "numpy")

    p_vals, pcov = scipy.optimize.curve_fit(sym_curve_l, x, y, maxfev=500000)
    sigma = numpy.sqrt(numpy.diagonal(pcov))

    p_subs = []
    p_subs_min = []
    p_subs_max = []

    # exclude the symbol of the variable when subbing
    for sidx, p in enumerate(p_vals, 1):
        sig = sigma[sidx - 1]
        p_min = p - 2 * sig
        p_max = p + 2 * sig
        s = syms[sidx]
        p_subs.append((s, p))
        p_subs_min.append((s, p_min))
        p_subs_max.append((s, p_max))
    y_fit = sym_curve.subs(p_subs)
    y_fit_min = sym_curve.subs(p_subs_min)
    y_fit_max = sym_curve.subs(p_subs_max)

    y_fit_l = sympy.lambdify(var, y_fit, "numpy")
    y_fit_min_l = sympy.lambdify(var, y_fit_min, "numpy")
    y_fit_max_l = sympy.lambdify(var, y_fit_max, "numpy")

    x_uniform = numpy.linspace(numpy.min(x), numpy.max(x), 100)
    return (
        x_uniform,
        y_fit_l(x_uniform),
        y_fit_min_l(x_uniform),
        y_fit_max_l(x_uniform),
        p_vals,
        sigma,
    )


def _init():
    pass


_init()
