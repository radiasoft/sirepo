import bluesky
import bluesky.plans
import databroker
import ophyd.sim
import time


def create(num_scans, catalog_name, delay=True):
    num_scans = int(num_scans)
    assert num_scans > 0, f"num_scans={num_scans} must be > 0"
    RE = bluesky.RunEngine({})
    RE.subscribe(databroker.Broker.named(catalog_name).insert)
    for i in range(num_scans):
        RE(
            bluesky.plans.count(
                [ophyd.sim.det1, ophyd.sim.det2],
                num=5,
                md={
                    "T_sample_": i,
                    "owner": "foo",
                    "sequence id": i,
                },
            )
        )
        if delay:
            time.sleep(2)
