#!/usr/bin/python
#
# Copyright (c) 2011 Ginkgo Bioworks Inc.
# Copyright (c) 2011 Daniel Taub
#
# This file is part of Scantelope.
#
# Scantelope is free software: you can redistribute it and/or modify
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
Server module for Scantelope.
This is the main application module.

INTERFACE:
    http://localhost:2233{command}

replace {command} with:       in order to:

      /scan/status             show current server settings and most recent log message
      /scan/list               list available scanners
      /scan/select/{0,1...n}   select scanner from list 

      /config/                 view current "inner" image and show options
      /config/use/{name}       use configuration "name" for current scanner
      /config/res/{600|300}    select resolution 
      /config/xoff/{integer}   select xoffset
      /config/yoff/{integer}   select yoffst

      /config/save             saves current configuration to a file
      /config/calibrate        automatically configure box position/boundaries and saves

      /                        view CSV of most-recently decoded 
      /images/n_m.jpg          view image from row n (0-7) and column m (0-11)
      /images/inner.jpg        view full plate image
"""

import threading
import scan
Config = scan.Config

from SocketServer import ThreadingMixIn
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

PORT=2233
from time import localtime, time, sleep
from datetime import datetime
from os.path import exists
from os import stat
from stat import * 


def modification_date(filename):
    t = path.getmtime(filename)
    retVal = str(datetime.fromtimestamp(t))
    return retVal.split('.')[0]



class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    pass


def resetTimer(): 
    MyHandler.sc.enableScan()
    MyHandler.event.set()
      

class MyHandler(BaseHTTPRequestHandler):
   
   def wwrite(self,data,line_break = None):
      if line_break != None:
         self.wfile.write(data + line_break) # could be <br> or \n
      else:
         self.wfile.write(data)

   def tag(self, text, tag = 'html'):
          return "<{0}>{1}</{0}>".format(tag,text)

   def hwrite(self,data):
      self.wwrite(self.tag(data),None)

   def do_GET(self):
       wwrite=self.wwrite
       hwrite=self.hwrite
       try:
           if self.path.startswith("/config"):
               self.send_response(200)
               self.send_header('Content-type','text/html')
               self.end_headers()
               status = ""
               if self.path[8:17] == "calibrate":
                   MyHandler.sc.calibrateNext()
                   status = ("calibrating...")
               elif self.path[8:11] == "res":
                   which = self.path[11:].strip('/')
                   if which.isdigit() and MyHandler.sc.setNextRes(int(which)):
                       status = ("selected resolution "+which)
                   else:
                       status = ("invalid resolution")
               elif self.path[8:11] == "use":
                   which = self.path[11:].strip('/')
                   if MyHandler.sc.setNextConfig(which):                   
                       status =("selected configuration: "+which)
                   else:
                       status = ("unknown configuration.")
               elif self.path[8:12] == "xoff":
                   # might like some additional error checks on these...
                   which = self.path[12:].strip('/')
                   if which.replace('-','',1).isdigit():
                       Config.offset[0] = int(which)
                       status =("selected xoffset "+which)
                   else:
                       status = ("invalid xoffset")
               elif self.path[8:12] == "yoff":
                   which = self.path[12:].strip('/')
                   if which.replace('-','',1).isdigit():
                       Config.offset[1] = int(which)
                       status = ("selected yoffset "+which)
                   else:
                       status = ("invalid yoffset")
               elif self.path[8:13] == "save":
                   Config.saveFile()
                   status = "Saved!"
               elif self.path[8:] == "":
                   pass
               else:
                   status = "unknown config command [%s]"%self.path[8:]
               thetime = datetime.now().isoformat()
               hwrite("""<head><META HTTP-EQUIV="refresh" CONTENT="5; /config/">
<title>Configuration Options</title></head>
<body>
<h2>%s</h2>
<br>
<u>valid commands:</u><br>
  use - set configuration to one of: %s = %s<br>
<br>
  res - resolution                  =  %d<br>
 xoff - x offset (for all scanners) =  %d<br>
 yoff - y offset                    =  %d<br>
<br>
 save - saves configuration file<br>
 calibrate - initiates automatic calibration (and saves custom settings)<br>
<br>%s<br><img width=500 src="/images%s/inner.jpg"/>
<br>%s
</body>
"""%(status,
str(list(Config.names)).replace("'",''),
Config.active,
Config.res,
Config.offset[0],
Config.offset[1],
thetime,thetime,MyHandler.sc.getStatus().replace('\n','<br>')))

           elif self.path.startswith("/scan"):
               self.send_response(200)
               self.send_header('Content-type','text/plain')
               self.end_headers() 
               if self.path.endswith("list"):
                   l='\n'.join(MyHandler.sc.getScanners().values())
                   wwrite(l)
               elif self.path[6:12] == "select":
                   which = self.path[12:].strip('/')
                   if which.isdigit() and MyHandler.sc.setNextScanner(int(which)):
                       wwrite("selected scanner "+which)
                   else:
                       wwrite("invalid scanner index")
               elif self.path.endswith("reset"):
                   MyHandler.sc.reset()
                   wwrite("reset decoded")
               elif self.path.endswith("status"):
                   wwrite(MyHandler.sc.getStatus())
               else:
                   wwrite("unknown scan command")

           elif self.path.startswith("/images") and self.path.endswith('.jpg'):
               subpath = self.path.split('/')[-1][:-4]
               if subpath.find('_') != -1:
                   fn = MyHandler.fileprot%scan.getFileFromWell(subpath)
               else:
                   proto= MyHandler.sc.myDir+'%s.jpg'
                   fn = proto%subpath
               #print fn
               if exists(fn):
                   f = open(fn,"rb")
                   size = stat(fn)[ST_SIZE]

                   self.send_response(200)
                   self.send_header('Content-type','image/jpeg')
                   self.send_header('Content-length',size)
                   self.end_headers() 
                   self.wfile.write(f.read())
                   
                   f.close()
               else:
                   self.send_response(404)
                   self.send_header('Content-type','text/plain')
                   self.end_headers() 
                   wwrite("error: file not found")

           elif self.path.strip('/') == '':
               self.send_response(200)
               self.send_header('Content-type','text/plain')
               self.end_headers()
               wwrite("TUBE,BARCODE,DECODE_TIME,FILEMOD_TIME\n")

               decoded = MyHandler.sc.getNewDecoded(MyHandler.lastUpdateTime)
               if decoded == -1:
                   listCodes = MyHandler.sc.getCodes() #***
               else:
                   MyHandler.lastUpdateTime = datetime.now()
                   listCodes = decoded.iteritems()
                   listCodes = map(lambda x: (scan.getWell(x[0],MyHandler.sc.pref),
                                              x[1][0],x[1][1],x[1][2]),
                                   listCodes)
                   listCodes.sort()
                   MyHandler.sc.setCodes(listCodes) #***
               
               for well,code,decTime,modTime in listCodes:
                   wwrite("%s,%s,%s,%s\n"%(well,code,decTime,modTime))

           elif self.path.endswith('decode'):
               self.send_response(200)
               self.send_header('Content-type','text/plain')
               self.end_headers()
               wwrite("Decode Command\n")
               MyHandler.sc.decodeOnly = True
           else:
               self.send_error(404,'Command/File not found')

           resetTimer()
           #MyHandler.event.clear()
           return
      
       except IOError:
           self.send_error(404,'File Not Found: %s' % self.path)

    ## in case post is needed, use the following (from Jon Berg , turtlemeat.com)
    #
    # def do_POST(self):
    #     global rootnode
    #     try:
    #         ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
    #         if ctype == 'multipart/form-data':
    #             query=cgi.parse_multipart(self.rfile, pdict)
    #         self.send_response(301)
            
    #         self.end_headers()
    #         upfilecontent = query.get('upfile')
    #         print "filecontent", upfilecontent[0]
    #         self.wfile.write("<HTML>POST OK.<BR><BR>");
    #         self.wfile.write(upfilecontent[0]);
            
    #     except :
    #         pass

def main():

      MyHandler.event = threading.Event()

   
      MyHandler.lastUpdateTime = datetime.now()
      MyHandler.sc=scan.ScanControl(MyHandler.event)
      MyHandler.sc.forceRepeat = True
      MyHandler.fileprot = MyHandler.sc.myDir+MyHandler.sc.pref+'%s.jpg'
      MyHandler.sc.findScanners()
      MyHandler.sc.start()

      server = ThreadingHTTPServer(('', PORT), MyHandler)
      print 'started httpserver...'

      running = True
      try:
          while running:
              server.handle_request() # blocks until request 
      except KeyboardInterrupt:
          print '^C received, shutting down server'
          server.socket.close()
      finally:
          print 'Shutting down server'
          server.socket.close()
      
if __name__ == '__main__':
   main()
