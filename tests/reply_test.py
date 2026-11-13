"""test sirepo.reply

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_websocket_response_closed():
    """Client closed the websocket before the reply was sent"""
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from sirepo import srunit
    import asyncio
    import tornado.websocket

    class _Handler:
        def __init__(self):
            self.writes = 0

        def write_message(self, *args, **kwargs):
            self.writes += 1
            # same as tornado when the websocket is closed
            raise tornado.websocket.WebSocketClosedError()

    h = _Handler()
    with srunit.quest_start() as qcall:
        # raises if it tries to reply with an error on the closed websocket
        asyncio.run(
            qcall.reply_ok().websocket_response(PKDict(handler=h, req_seq=1)),
        )
    pkunit.pkeq(1, h.writes)
