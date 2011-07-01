#!/usr/bin/python
#
# Copyright (c) 2011 Ginkgo Bioworks Inc.
# Copyright (c) 2011 Daniel Taub
#
# This file is part of DMTube.
#
# DMTube is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
test module for Lab Server DMTube.

"""

import scan
from datetime import datetime
from time import sleep
import threading

scanEvent = threading.Event()

MaxReps = 10

sc= scan.ScanControl(scanEvent)

#supports low res (300) or high (600) (in dpi)
sc.setNextRes(600)
sc.setResFromNext()

# if true, clears decoded before repeating
# if false, attempts to exhaustively decode the wells
sc.forceRepeat = True

# do not actually scan, but use images from most recent
#decodeOnly = True

sc.enableScan()
sc.start()

# each time set, allows a waiting scan to proceed
scanEvent.set() 

# If false, compare each decoding to 'comp' below
# updateFromImages = False
# If true, this allows decoding to the 'correct' decoding to be updated,
# testing for consistency across scans instead of a fixed correctness
updateFromImages = True

lastt = datetime.now()
out = {}
f=open('dmLog.txt','a')

comp = '''TUBE,BARCODE,STATUS
A01,1013784893,OK
A02,1013787009,OK
A03,1013784760,OK
A04,1013785475,OK
A05,1013775373,OK
A06,1013783702,OK
A07,1013785714,OK
A08,1013784120,OK
A09,1013786817,OK
A10,1013784123,OK
A11,1013786812,OK
A12,1013786596,OK
B01,1013784819,OK
B02,1013786989,OK
B03,1013812015,OK
B04,0074044056,OK
B05,0074043744,OK
B06,1013785770,OK
B07,1013785762,OK
B08,1013786587,OK
B09,1013784062,OK
B10,1013785426,OK
B11,1013786768,OK
B12,1013786725,OK
C01,1013784600,OK
C02,1013787010,OK
C03,1013833983,OK
C04,1013775324,OK
C05,1013785387,OK
C06,1013785781,OK
C07,1013785668,OK
C08,1013783959,OK
C09,1013786593,OK
C10,1013786747,OK
C11,1013786742,OK
C12,1013786795,OK
D01,1013786916,OK
D02,0074043014,OK
D03,1013785458,OK
D04,1013785431,OK
D05,1013785764,OK
D06,1013785794,OK
D07,1013785788,OK
D08,1013784055,OK
D09,1013784114,OK
D10,1013786771,OK
D11,1013786753,OK
D12,1013786748,OK
E01,1013786941,OK
E02,1013759285,OK
E03,0074043074,OK
E04,1013785417,OK
E05,1013783726,OK
E06,1013785805,OK
E07,1013786610,OK
E08,1013784048,OK
E09,1013784121,OK
E10,1013786772,OK
E11,1013786766,OK
E12,1013786797,OK
F01,1013786988,OK
F02,1013784709,OK
F03,0074043734,OK
F04,1013775372,OK
F05,1013785813,OK
F06,1013783674,OK
F07,1013785430,OK
F08,1013784079,OK
F09,1013784039,OK
F10,1013786729,OK
F11,1013786741,OK
F12,1013786803,OK
G01,1013786986,OK
G02,1013784752,OK
G03,1013785452,OK
G04,1013785402,OK
G05,1013785808,OK
G06,1013783725,OK
G07,1013786620,OK
G08,1013784098,OK
G09,1013786569,OK
G10,1013785396,OK
G11,1013786754,OK
G12,1013786726,OK
H01,1013786964,OK
H02,1013784775,OK
H03,1013785419,OK
H04,1013775396,OK
H05,1013783697,OK
H06,1013785716,OK
H07,1013786595,OK
H08,1013784078,OK
H09,1013784107,OK
H10,1013786769,OK
H11,1013786765,OK
H12,1013786818,OK
'''

if not updateFromImages:
    for line in comp.strip().split('\n'):
        a,b,c = line.split(',')
        out[a] = b

notDone = True

while notDone:
    sleep(2)

    d = sc.getNewDecoded(lastt)

    if d == -1:
        continue
    else:
        MaxReps -= 1
        if MaxReps < 0:
            notDone = False
        scanEvent.set()
        #sc.enableScan()
        lastt=datetime.now()

    # maybe create set of keys in out and remove entries through loop, adding 
    # compliment to log from else after loop
    for k,v in d.items():
        #import pdb;pdb.set_trace()
        v0 = v[0]
        k = scan.getWell(k,sc.pref)

        if out.has_key(k):
            if out[k] != v0:
                f.write("%s current: %s != %s at %s\n"%(k,v0,out[k],scan.strtime()))
                f.flush()
                if updateFromImages:
                    out[k] = v0
            else:
                pass#print v[0]
        else:
            f.write("%s no value setting = %s at %s\n"%(k,v0,scan.strtime()))
            f.flush()
            out[k] = v0
