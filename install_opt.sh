#!/bin/sh 
# run this as root
# to install into /opt

ARCH=i386
#ARCH=amd64
#ARCH=arm
SCANUSER=`/usr/bin/whoami`
PREFIX=/opt/scantelope

# 0a IMAGEMAGIC  6.5.8-9 or later:
cd ImageMagick-6.7.0-10
./configure --prefix=$PREFIX
make install
cd ..

# 0b OPENCV 2.2 or later:
cd OpenCV-2.3.0/
cd release
cmake -D CMAKE_BUILD_TYPE=RELEASE -D CMAKE_INSTALL_PREFIX=$PREFIX -D BUILD_PYTHON_SUPPORT=ON -D BUILD_EXAMPLES=ON ..
make install
cd ../..

# 0c libdmtx and wrappers:
cd libdmtx 
./configure --prefix=$PREFIX
make install
cd ..

cd dmtx-wrappers
./configure --prefix=$PREFIX
make install
cd python
./configure --prefix=$PREFIX
make install
/sbin/ldconfig $PREFIX/lib
cd ../..

# 1) install sane drivers
cp drivers/avision/$ARCH/libsane-avision.so.1 /usr/lib/sane/libsane-avision.so.1.bin
ln -sf /usr/lib/sane/libsane-avision.so.1.bin /usr/lib/sane/libsane-avision.so.1

# 2) set up user/group permissions
addgroup scanner
adduser $SCANUSER scanner
adduser saned scanner

# 3) set up udev rules
cp 10-saned.rules /etc/udev/rules.d/

# 4) copy application files
mkdir /opt/scantelope/
cp *.py /opt/scantelope/
cp *.png /opt/scantelope/
cp README /opt/scantelope/
cp install.sh /opt/scantelope/
cp COPYING /opt/scantelope/
cp scantelope.sh /opt/scantelope/
