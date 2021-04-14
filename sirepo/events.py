# -*- coding: utf-8 -*-
u"""Reigster callbacks for events and call callbacks when events are emitted.

Using events allows disparate areas of the code base to perform some task on
an event without muddling the code that triggered the event. In addition events
can be registered by configuration. This allows areas of the code to
register/emit events when they are configured on and doesn't require if
statements throughout the code.

For example, when a user logs out the AUTH_LOGOUT event is emitted. Other
areas of the code can register a callback for this event (ex to clear jupyterhub
cookies so the user is logged out of jupyterhub too).

The events:
- 'auth_logout' emitted when a user logs out, before the cookie is cleared.
  kwargs contains uid.
- 'end_api_call' emitted at the end of of an http request to the flask server.
  kwargs contains resp, the Flask response object.
- 'github_authorized' emitted once the authorized github user is retrieved and
  confirmed valid but before that user is logged in or the github db is updated.
  kwargs contains user_name, the github handle.
- 'srcontext_created' emitted when the srcontext object is populated.
- 'srcontext_destroyed' emitted when the srcontext object is destroyed.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import aenum

#: Map of events to handlers. Note: this is the list of all possible events.
_MAP = PKDict(
    auth_logout=[],
    end_api_call=[],
    github_authorized=[],
    srcontext_created=[],
    srcontext_destroyed=[],
)


def emit(event, kwargs=None):
    """Call the handlers for `event` with `kwargs`

    Handlers will be called in registration order (FIFO).

    Args:
        event (str): one of the names in `_MAP`
        kwargs (PKDict): optional arguments to pass to event
    """
    for h in _MAP[event]:
        h(PKDict() if kwargs is None else kwargs)


def register(registrants):
    """Register callback(s) for event(s)

    Args:
        registrants (PKDict): Key is the event and value is the callback
    """
    for k, v in registrants.items():
        if v not in _MAP[k]:
            _MAP[k].append(v)
