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
        # some "concrete" dependencies in requirements.txt
        'Flask-OAuthlib',
        'Flask-Mail',
        'Flask_SQLAlchemy',
        'SQLAlchemy',
        'aenum',
        'beaker',
        'celery==3.1.23',
        'cryptography',
        'flower==0.8.4',
        'futures',
        'kombu==3.0.35',
        'numconv',
        'numpy',
        'pillow',
        'pyIsEmail',
        'pykern',
        'pytz==2015.7',
        # requests-oauthlib-1.2.0 forces oauthlib-3.0.0 but Flask-OAuthlib
        # requires oauthlib<3.0.0.
        'requests-oauthlib==1.1.0',
        'scikit-learn==0.20',
        'sympy',
        'uwsgi',
        'trio >= 0.11.0; python_version >= "3"',
        'docker; python_version >= "3"',
   ],
    license='http://www.apache.org/licenses/LICENSE-2.0.html',
    name='sirepo',
    url='http://sirepo.com',
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
