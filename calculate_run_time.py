import csv
import glob
import json
import sys

MAX_SECS = int(sys.argv[1])
TIME_WINDOW = int(sys.argv[2]) if len(sys.argv) > 2 else 5

with open('out.csv', 'w') as f:
    w = csv.writer(f)
    for n in glob.glob('/home/vagrant/src/radiasoft/sirepo/run/supervisor-job/*.json'):
        j = json.load(open(n))
        for x in j['history']:
            d = int( x['lastUpdateTime'])-int(x['computeJobStart'])
            if x['status'] == 'canceled' and d + TIME_WINDOW >= MAX_SECS and d <= MAX_SECS:
                w.writerow([n, x['status'], d])
