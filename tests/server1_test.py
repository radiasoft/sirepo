# -*- coding: utf-8 -*-
u"""Test simulationSerial

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
pytest.importorskip('srwl_bl')

#: Used for a sanity check on serial numbers
_MIN_SERIAL = 10000000


def test_1_serial_stomp():
    from pykern.pkdebug import pkdp, pkdpretty
    from pykern.pkunit import pkfail, pkok
    from sirepo import sr_unit
    import copy

    fc = sr_unit.flask_client()
    sim_type = 'srw'
    fc.get('/{}'.format(sim_type))
    data = fc.sr_post('listSimulations', {'simulationType': sim_type})
    for youngs in data:
        if youngs['name'] == "Young's Double Slit Experiment":
            break
    else:
        pkfail("{}: Young's not found", pkdpretty(data))
    data = fc.sr_get(
        'simulationData',
        {
            'simulation_type': sim_type,
            'pretty': '0',
            'simulation_id': youngs['simulationId'],
        },
    )
    prev_serial = data['models']['simulation']['simulationSerial']
    prev_data = copy.deepcopy(data)
    pkok(
        prev_serial > _MIN_SERIAL,
        '{}: serial must be greater than {}',
        prev_serial,
        _MIN_SERIAL,
    )
    data['models']['beamline'][4]['position'] = '61'
    curr_data = fc.sr_post('saveSimulationData', data)
    curr_serial = curr_data['models']['simulation']['simulationSerial']
    pkok(
        prev_serial < curr_serial,
        '{}: serial not incremented, still < {}',
        prev_serial,
        curr_serial,
    )
    prev_data['models']['beamline'][4]['position'] = '60.5'
    failure = fc.sr_post('saveSimulationData', prev_data)
    pkok(
        failure['error'] == 'invalidSerial',
        '{}: unexpected status, expected serial failure',
        failure,
    )
    curr_data['models']['beamline'][4]['position'] = '60.5'
    curr_serial = curr_data['models']['simulation']['simulationSerial']
    new_data = fc.sr_post('saveSimulationData', curr_data)
    new_serial = new_data['models']['simulation']['simulationSerial']
    pkok(
        curr_serial < new_serial,
        '{}: serial not incremented, still < {}',
        new_serial,
        curr_serial,
    )


def test_missing_cookies():
    from pykern.pkunit import pkeq
    from sirepo import sr_unit
    import json
    fc = sr_unit.flask_client()
    sim_type = 'srw'
    resp = fc.post('/simulation-list', data=json.dumps({'simulationType': sim_type}), content_type='application/json')
    pkeq(403, resp.status_code)


def test_oauth():
    from pykern import pkconfig
    pkconfig.reset_state_for_testing({
        'SIREPO_SERVER_OAUTH_LOGIN': '1',
        'SIREPO_OAUTH_GITHUB_KEY': 'n/a',
        'SIREPO_OAUTH_GITHUB_SECRET': 'n/a',
        'SIREPO_OAUTH_GITHUB_CALLBACK_URI': 'n/a',
    })

    from pykern.pkunit import pkfail, pkok
    from sirepo import server
    from sirepo import sr_unit
    import re

    sim_type = 'srw'
    fc = sr_unit.flask_client()
    fc.get('/{}'.format(sim_type))
    fc.sr_post('listSimulations', {'simulationType': sim_type})
    text = fc.sr_get(
        'oauthLogin',
        {
            'simulation_type': sim_type,
            'oauth_type': 'github',
        },
        raw_response=True,
    ).data
    state = re.search(r'state=(.*?)"', text).group(1)
    #TODO(pjm): causes a forbidden error due to missing variables, need to mock-up an oauth test type
    text = fc.get('/oauth-authorized/github')
    text = fc.sr_get(
        'oauthLogout',
        {
            'simulation_type': sim_type,
        },
        raw_response=True,
    ).data
    pkok(
        text.find('Redirecting') > 0,
        'missing redirect',
    )
    pkok(
        text.find('"/{}"'.format(sim_type)) > 0,
        'missing redirect target',
    )
