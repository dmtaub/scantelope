#!/usr/bin/python

#Based on code from Jon Berg , turtlemeat.com

#import cgi
#import pri

import scan

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

PORT=2233
from time import localtime
from datetime import datetime

def modification_date(filename):
    t = path.getmtime(filename)
    retVal = str(datetime.fromtimestamp(t))
    return retVal.split('.')[0]

def getWell(fn,pref):
   n=fn.split(pref)[1].split('.')[0]
   if not n.isdigit():
      print "error, n:",n
      return -1
   n = int(n)
   #return n
   
   row = chr(ord('A')+int(n%8))
   col = (n / 8) + 1
   #print n, row, col
   return "%s%02d"%(row,col)

class MyHandler(BaseHTTPRequestHandler):

   listCodes = []
   def wwrite(self,data,line_break = '<br>'):
      #if line_break != None:
      #   self.wfile.write(data.replace('\n',line_break))
      #else:
         self.wfile.write(data)

   def do_GET(self):
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
                       MyHandler.sc.startScan()
                       wwrite("scan started")
               elif self.path.endswith("stop"):
                   MyHandler.sc.stopScan()
                   wwrite("scan stopped")
               elif self.path.endswith("reset"):
                   MyHandler.sc.reset()
                   wwrite("reset decoded")
               elif self.path.endswith("status"):
                   wwrite(MyHandler.sc.getStatus())
               else:
                   wwrite("unknown scan command")
               return
           elif self.path.endswith("test"):   #our dynamic content
               self.send_response(200)
               self.send_header('Content-type','text/html')
               self.end_headers()
               wwrite("hey, today is the " + str(localtime()[7]))
               wwrite(" day in the year " + str(localtime()[0]))
               return
           elif self.path.strip('/') == '':
               self.send_response(200)
               self.send_header('Content-type','text/plain')
               self.end_headers()
               wwrite("TUBE,BARCODE,DECODE_TIME,FILEMOD_TIME\n",None)

               decoded = MyHandler.sc.getNewDecoded(MyHandler.lastUpdateTime)
               if decoded == -1:
                   listCodes = MyHandler.listCodes
               else:
                   MyHandler.lastUpdateTime = datetime.now()
                   listCodes = decoded.iteritems()
                   listCodes = map(lambda x: (getWell(x[0],MyHandler.sc.pref),
                                              x[1][0],x[1][1],x[1][2]),
                                   listCodes)
                   listCodes.sort()
                   MyHandler.listCodes = listCodes
               
               for well,code,decTime,modTime in listCodes:
                   wwrite("%s,%s,%s,%s\n"%(well,code,decTime,modTime),None)
               return
           elif self.path.endswith('decode'):
               self.send_response(200)
               self.send_header('Content-type','text/plain')
               self.end_headers()
               wwrite("Decode Command\n")
               MyHandler.sc.decodeOnly = True
           else:
               self.send_error(404,'Command/File not found')
               return
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
   try:
      MyHandler.lastUpdateTime = datetime.now()
      MyHandler.sc=scan.ScanControl()
      MyHandler.sc.start()
      server = HTTPServer(('', PORT), MyHandler)
      print 'started httpserver...'
      server.serve_forever()
   except KeyboardInterrupt:
      print '^C received, shutting down server'
      server.socket.close()
      
if __name__ == '__main__':
   main()
