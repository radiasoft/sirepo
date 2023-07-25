# -*- coding: utf-8 -*-
"""Sirepo setup script

:copyright: Copyright (c) 2015-2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import os
import pykern.pksetup

install_requires = [
    "Flask==2.0.3",
    "SQLAlchemy>=1.4,<2",
    "aenum",
    "asyncssh",
    "cryptography>=2.8",
    "futures",
    "matplotlib",
    "numconv",
    "numpy",
    "Pillow",
    "pyIsEmail",
    "pykern",
    "pytz",
    "requests",
    "tornado",
    "user-agents",
    "werkzeug==2.0.3",
    # Optional dependencies
    # required for email login and smtp
    "Authlib>=0.13",
    "dnspython",
    # required for sbatch agent
    "asyncssh",
]
if not os.environ.get("no_uwsgi", 0):
    # had a problem installing in one environment so make optional
    install_requires.append("uwsgi")

pykern.pksetup.setup(
    author="RadiaSoft LLC.",
    author_email="pip@sirepo.com",
    description="accelerator code gui",
    install_requires=install_requires,
    license="http://www.apache.org/licenses/LICENSE-2.0.html",
    name="sirepo",
    url="http://sirepo.com",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Flask",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
)
