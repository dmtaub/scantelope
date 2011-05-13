#!/usr/bin/python

import scan
from datetime import datetime
from time import sleep

sc= scan.ScanControl()
sc.forceRepeat = True
sc.start()
sc.startScan()
sc.refreshInterval = 20
lastt = datetime.now()
out = {}
f=open('/home/dmt/testing2.txt','a')

while 1:
    sleep(2)
    d = sc.getNewDecoded(lastt)
    if d == -1:
        continue
    else:
        print 
        lastt=datetime.now()
    for k,v in d.items():
        if out.has_key(k):
            if out[k] != v[0]:
                f.write("%s current: %s != %s at %s\n"%(k,
                                                        v[0],out[k],
                                                        scan.strtime()))
                f.flush()
                out[k] = v[0]
        else:
            out[k] = v[0]
