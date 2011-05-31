#!/usr/bin/python
# Server for decoded DM -- Daniel Taub, dmtaub.com
# Server based on code from Jon Berg , turtlemeat.com


#import cgi
#import pri
import threading
import scan
scan.decode.findcode.low_res = False
scan.defaultfn[0]='highres'

from SocketServer import ThreadingMixIn
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

PORT=2233
from time import localtime, time, sleep
from datetime import datetime
from os.path import exists
from os import stat
from stat import * 

def getFileFromWell(well):
    if well[1:].isdigit():
        well = well.upper()
        return (ord(well[0])-65)+8*int(well[1:])
    elif well.find('-') != -1:
        splitv = '-'
    elif well.find('_')!= -1:
        splitv = '_'
    else:
        return -1

    w = well.split(splitv)
    if len(w) == 2:
        return int(w[0])+8*int(w[1])
    else:
        return -1

def modification_date(filename):
    t = path.getmtime(filename)
    retVal = str(datetime.fromtimestamp(t))
    return retVal.split('.')[0]



class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    pass


class MyHandler(BaseHTTPRequestHandler):
   
   def wwrite(self,data,line_break = '<br>'):
      #if line_break != None:
      #   self.wfile.write(data.replace('\n',line_break))
      #else:
         self.wfile.write(data)

   def do_GET(self):
       MyHandler.sc.enableScan()
       MyHandler.event.set()
       wwrite=self.wwrite
       try:
         #            print self.path
           if self.path.startswith("/scan/"):
               self.send_response(200)
               self.send_header('Content-type','text/plain')
               self.end_headers() 
               if self.path.endswith("list"):
                   l='\n'.join(MyHandler.sc.getScanners())
                   wwrite("scanners:\n%s"%l)
               elif self.path.endswith("start"):
                   if MyHandler.sc.getScanners() == []:
                       wwrite("No scanners found, try power cycling the scanner")
                   else:
                       MyHandler.sc.initScan()
                       wwrite("scan started")
#               elif self.path.endswith("stop"):
#                   MyHandler.sc.stopScan()
#                   wwrite("scan stopped")
               elif self.path.endswith("reset"):
                   MyHandler.sc.reset()
                   wwrite("reset decoded")
               elif self.path.endswith("status"):
                   wwrite(MyHandler.sc.getStatus())
               else:
                   wwrite("unknown scan command")

           elif self.path.startswith("/images") and self.path.endswith('.jpg'):
               fn = MyHandler.fileprot%getFileFromWell(self.path.split('/')[-1][:-4])
               print fn
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
               wwrite("TUBE,BARCODE,DECODE_TIME,FILEMOD_TIME\n",None)

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
                   wwrite("%s,%s,%s,%s\n"%(well,code,decTime,modTime),None)

           elif self.path.endswith('decode'):
               self.send_response(200)
               self.send_header('Content-type','text/plain')
               self.end_headers()
               wwrite("Decode Command\n")
               MyHandler.sc.decodeOnly = True
           else:
               self.send_error(404,'Command/File not found')

           MyHandler.event.clear()
           return
      
       except IOError:
           self.send_error(404,'File Not Found: %s' % self.path)
          
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
