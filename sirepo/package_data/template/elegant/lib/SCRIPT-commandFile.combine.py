#!/usr/bin/env python
from io import StringIO
import pandas
import subprocess
import sys

if len(sys.argv) != 4:
    raise RuntimeError(
        f"Expected 3 args, got {len(sys.argv) - 1}\nusage: {sys.argv[0]} <infile> <infile> <outfile>",
    )


def sdds_to_numpy(f):
    cols = ['x', 'xp', 'y', 'yp', 't', 'p', 'particleID']
    txt = subprocess.run(
        ("sdds2stream", "-delimiter= ", f"-columns={','.join(cols)}", f),
        check=True,
        capture_output=True,
    ).stdout
    return pandas.read_csv(
        StringIO(txt.decode('ascii')),
        sep=' ',
        names=cols,
    )

v = sdds_to_numpy(sys.argv[1])
v2 = v + sdds_to_numpy(sys.argv[2]) / 10
v2['particleID'] = v['particleID']
v2.to_csv('out.csv', index=False, header=False)

subprocess.check_call(
    (
        "csv2sdds",
        "-columnData=name=x,type=double,units=m",
        "-columnData=name=xp,type=double",
        "-columnData=name=y,type=double,units=m",
        "-columnData=name=yp,type=double",
        "-columnData=name=t,type=double,units=s",
        "-columnData=name=p,type=double,units=m$be$nc",
        "-columnData=name=particleID,type=long",
        "out.csv",
        sys.argv[3],
    ),
)
