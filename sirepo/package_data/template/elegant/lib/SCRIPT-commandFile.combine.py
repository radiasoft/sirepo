#!/usr/bin/env python
import subprocess
import sys

if len(sys.argv) != 4:
    raise RuntimeError(
        f"Expected 3 args, got {len(sys.argv) - 1}\nusage: {sys.argv[0]} <infile> <infile> <outfile>",
    )
subprocess.check_call(
    ("sddscombine", sys.argv[1], sys.argv[2], "-merge", sys.argv[3]),
)
