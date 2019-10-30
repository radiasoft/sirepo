# -*- coding: utf-8 -*-
u"""?

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp

# Placeholder for notes:
# I think for the short term, we should use ssh, not NEWT to
# get into NERSC. I don't see how they are different, and it will
# save us a lot of time dealing with NEWT's arcane interface. We
# can use NEWT later, if we need to, but ssh will allow us to
# handle other s-batch style systems easily. It will be enough
# to ssh/scp in to establish an environment.
