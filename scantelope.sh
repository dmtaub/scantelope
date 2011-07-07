#!/bin/sh 
export LD_LIBRARY_PATH=/opt/scantelope/lib/
export PYTHONPATH="/opt/scantelope/lib/python2.6/dist-packages:/opt/scantelope/lib/python2.6/site-packages"
start-stop-daemon -b --start --chdir /opt/scantelope --exec /opt/scantelope/serv.py 
