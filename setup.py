# -*- coding: utf-8 -*-
u"""Sirepo setup script

:copyright: Copyright (c) 2015-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pykern.pksetup

pykern.pksetup.setup(
    author='RadiaSoft LLC.',
    author_email='pip@sirepo.com',
    description='accelerator code gui',
    install_requires=[
        'Flask>=1.1',
        'SQLAlchemy',
        'aenum',
        'asyncssh',
        'cryptography>=2.8',
        'futures',
        'numconv',
        'numpy',
        'pyIsEmail',
        'pykern',
        'pytz',
        'requests',
        'tornado',
        'user-agents',
        'uwsgi',
        'werkzeug',

        # Optional dependencies
        # required for email login and smtp
        'Authlib>=0.13',
        'dnspython',
        # required for sbatch agent
        'asyncssh',
    ],
    license='http://www.apache.org/licenses/LICENSE-2.0.html',
    name='sirepo',
    url='http://sirepo.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Flask',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: JavaScript',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Topic :: Scientific/Engineering :: Physics',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
    ],
)
