# -*- coding: utf-8 -*-
u"""Sirepo setup script

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
try:
    import pykern.pksetup
except ImportError:
    import pip
    pip.main(['install', 'pykern'])
    import pykern.pksetup

pykern.pksetup.setup(
    name='sirepo',
    description='accelerator code gui',
    author='RadiaSoft LLC.',
    author_email='pip@sirepo.com',
    url='http://sirepo.com',
    license='http://www.apache.org/licenses/LICENSE-2.0.html',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Flask',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: JavaScript',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering :: Physics',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ],
)
