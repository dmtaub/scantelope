#!/bin/bash
#dmtxread=/home/dmt/devel/libdmtx-utils/dmtxread/dmtxread

cd /tmp/
scanimage -d net:localhost:avision:libusb --batch=batch%d.tif --batch-count=1 --resolution 300 --format=tiff -l 14.5 -x 85 -t 10 -y 125
convert batch1.tif -crop 817x1251+91+112 inner1.tif
# this requires at least imagemagick 6.5.8-9
convert inner1.tif -density 300 -crop 8x12-17-19@\! -shave 10x10 +repage twistlow%d.tif
exit 0
#sudo scanimage -d avision:libusb --batch=batch%d.tif --batch-count=1 --resolution 600 --format=tiff -l 14.5 -x 85 -t 10 -y 125
#convert batch1.tif -density 600 -crop 1634x2502+182+224 inner2.tif
# this requires at least imagemagick 6.5.8-9
#convert inner2.tif -density 600 -crop 8x12-34-38@\! -shave 20x20 +repage twisthigh%d.tif

#-density argument added to preserve DPI

# messy file, but it has history!
# can combine these two convert lines into one
#ls circ*.png | xargs -I xxx convert -size 67x67 xc:black -fill xxx -draw "circle 33,33 23,23" xxx

# for some reason -s 12x12 doesn't work on some images
# while -s 12x12 is required for some images
# for some reason -N 1 sometimes makes it so dmtxread skips valid pages?! Without it, it finds it
cd ~/ginkgo/lab/datamatrix/
python process.py 0 /tmp/twistlow.tif

#$dmtxread -e 20 -E 32 -q 10 -t 30 -s 12x12 -m 300 -N 1 -P -n wells.tif > out1
#$dmtxread -D -e 20 -E 32 -q 10 -t 30 -m 300 -P -n wells.tif > out2
#cat out
#echo "number lineS:"

#cat out1 | wc -l
#cat out2 | wc -l
