#!/bin/sh 

# modify these two lines for your configuration
ARCH=i386
SCANUSER=`/usr/bin/whoami`

sudo apt-get install -y --force-yes cmake python-numpy g++ python-dev git-core autoconf automake libtool sane libtiff4

cd /tmp
mkdir dm
cd dm

wget ftp://ftp.imagemagick.org/pub/ImageMagick/ImageMagick-6.7.0-10.tar.gz 
tar xvzf ImageMagick-6.7.0-10.tar.gz
cd ImageMagick-6.7.0-10
./configure 
make
sudo make install
cd ..

wget http://voxel.dl.sourceforge.net/project/opencvlibrary/opencv-unix/2.3/OpenCV-2.3.0.tar.bz2
tar xvjf OpenCV-2.3.0.tar.bz2
cd OpenCV-2.3.0/
mkdir release
cd release
cmake -D CMAKE_BUILD_TYPE=RELEASE -D CMAKE_INSTALL_PREFIX=/usr/local -D BUILD_PYTHON_SUPPORT=ON -D BUILD_EXAMPLES=ON ..
make
sudo make install
cd ../..

#wget http://surfnet.dl.sourceforge.net/project/libdmtx/libdmtx/0.7.4/libdmtx-0.7.4.tar.gz
#tar xvzf libdmtx-0.7.4.tar.gz  
#cd libdmtx-0.7.4
#./configure
#make
#sudo make install
#cd ..

#wget "http://libdmtx.git.sourceforge.net/git/gitweb.cgi?p=libdmtx/dmtx-wrappers;a=snapshot 
#;h=e7af61b885c99822a90e3b6113b32a5f56e8609a;sf=tgz" -O wrap.tgz 
#tar xvzf wrap.tgz
#cd dmtx-wrappers-e7af61b/python
#make
#sudo make install
#cd ../..

git clone git://libdmtx.git.sourceforge.net/gitroot/libdmtx/libdmtx
cd libdmtx 
mkdir m4
./autogen.sh
./configure
make
sudo make install
cd ..

git clone git://libdmtx.git.sourceforge.net/gitroot/libdmtx/dmtx-wrappers
cd dmtx-wrappers
mkdir m4
./autogen.sh
./configure
make
sudo make install
sudo /sbin/ldconfig /usr/local/lib
cd ..
# optional for command-line datamatrix tools:
# git clone git://libdmtx.git.sourceforge.net/gitroot/libdmtx/dmtx-utils

sudo cp 10-saned.rules /etc/udev/rules.d/
sudo cp drivers/avision/$ARCH/libsane-avision.so.1 /usr/lib/sane/libsane-avision.so.1.bin
sudo ln -sf /usr/lib/sane/libsane-avision.so.1.bin /usr/lib/sane/libsane-avision.so.1

sudo addgroup scanner
sudo adduser $SCANUSER scanner
