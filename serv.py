#!/usr/bin/python
#Based on code from Jon Berg , turtlemeat.com
import string,cgi,time

from os import curdir, sep, path, listdir
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
#import pri
PORT=2233
EXPECTED_LEN = 10

import threading
#from thread import allocate_lock as newLock
from time import sleep,strftime,time
from subprocess import Popen, PIPE
from pydmtx import DataMatrix, Image
import findcode
import cv

defaultfn='lowres.tif'
class DMDecoder():
   do_display = False
   verbose = False
   totalTime = time()
   failed = []
   files = None
   output = {}
   status = ''

   def resettime(self):
      self.totalTime = time()

   def reinit(self,files=None):
      if files != None:
         self.files = files
      else:
         self.__init__()
      self.totalTime = time()
      self.output={}
      self.failed =[]
      self.status = ''
      

   def __init__(self):
      splt = defaultfn.split('.') 
      pref = splt[0]
      if pref.find('/') != -1:
         self.myDir,self.pref = path.split(pref)
         self.ext = '.'+splt[1]
      else:
         self.pref = pref
         self.myDir = '/tmp'
         self.ext = '.'+splt[1]
         self.myDir += '/'
      if self.files == None:
       self.files = [i for i in listdir(self.myDir) if i.find(pref) != -1 and ''.join(i.split(pref)).rstrip(self.ext).isdigit()]
       self.files.sort()

   def parseImages(self):
      n=0
      m=0
#      import pdb;pdb.set_trace()
      lastCVTime = 0
      timeForCV = 0
      for filename in self.files:

          is_found = False    

          if filename.find('/') != -1:
            self.myDir,filename = path.split(filename)
            self.myDir += '/'
          
          lastCVTime = time()

          cv_orig,cv_smoo,cv_final = findcode.findAndOrient(self.myDir,
                                                            filename,
                                                            self.do_display, 
                                                            self.verbose)

          timeForCV += (time() - lastCVTime)

          for img,name in [[cv_smoo,"smooth"],
                           [cv_final,"clipped"],
                           [cv_orig,"original"]]:

             if is_found:
                break

             dmtx_im = Image.fromstring("L", cv.GetSize(img), img.tostring())

             padding = 0.1
             ncols,nrows = dmtx_im.size

             padw = (ncols)*padding
             padh = (nrows)*padding
            
             isize = (int(round(ncols+2*padw)),int(round(nrows+2*padh)))#cols*photow+padw,nrows*photoh+padh)

        # Create the new image. The background doesn't have to be white

             dmtx_image = Image.new('RGB',isize,0)
             bbox = (round(padw),round(padh),ncols+round(padw),nrows+round(padh))

             dmtx_image.paste(dmtx_im,map(int,bbox))

             (width, height) = dmtx_image.size
             dm_read = DataMatrix(max_count = 1, timeout = 300, min_edge = 20, max_edge = 32, threshold = 5, deviation = 10)
            #dm_read = DataMatrix(max_count = 1, timeout = 300, shape = DataMatrix.DmtxSymbol12x12, min_edge = 20, max_edge = 32, threshold = 5, deviation = 10)
             dmtx_code = dm_read.decode (width, height, buffer(dmtx_image.tostring()))
             
             if dmtx_code is not None and len(dmtx_code) == EXPECTED_LEN:
                how = "Quick Search: "+str(name)
                is_found = True


             out = dmtx_code

    #      if not is_found:
    #        dm_read = DataMatrix(max_count = 1, timeout = 300, min_edge = 20, max_edge = 32, threshold = 5, deviation = 10)
    #        dmtx_code = dm_read.decode (width, height, buffer(dmtx_image.tostring()))
    #        if dmtx_code is not None and len(dmtx_code) == EXPECTED_LEN:
    #            how = "Quick Search(2): "+str(name)
    #            is_found = True
    #      out = dmtx_code

          if is_found:
             n+=1
             self.output[filename] = out
          else:
             print filename, None
             self.failed.append(filename)
          m+=1



      self.status += "\nFound %d of %d in "%(n,m)
      #import pdb;pdb.set_trace()
      self.status += str(time()-self.totalTime)+" seconds.\n"
      self.status += "(OpenCV: "+str(timeForCV)+" sec)\n"

      if not(len(self.failed) == 0):# and verbose:
         dirr = ' '+self.myDir
         self.status+= "\nmissing: "+str(self.failed)+'\n'

      return self.output,self.failed,self.status

def strtime():
   return strftime("%Y-%m-%d %H:%M:%S<br><br>")

class ScanControl(threading.Thread):
   def __init__(self):
      threading.Thread.__init__(self)
      self.dm = DMDecoder()
      self.daemon = True #This kills this thread when the main thread stops  
      self.isScanning = False
      self.refreshInterval = 1 #in seconds
      self.scanners = [] 
      self.status = strtime()+'initialized'
      self.lock = threading.Lock()
      self.whichScanner = 0
      self.decoded ={}

   def startScan(self):
      self.refreshInterval = 1
      self.isScanning = True
      self.status = strtime()+'started'
      self.dm.__init__()
   def stopScan(self):
      self.isScanning = False
      self.refreshInterval = 2
      self.status = strtime()+'stopped'
   def autoStopScan(self):
      self.isScanning = False
      self.refreshInterval = 2
      self.status += '\n'+strtime()+'stopped'

   def acquire(self):
      self.lock.acquire()
        
   def release(self):
      self.lock.release()
        
   def getScanners(self):
      proc=Popen(['scanimage',"-f","%d%n"],stdout=PIPE)
      out, err = proc.communicate()
      if out == '':
         self.scanners = []
      else:
         self.scanners = out.strip().split()
         self.scanners = filter(lambda x: x[:3] == 'net',self.scanners)
         
   def run(self):
      self.getScanners()
      while 1:
         #print "hi"

         if self.isScanning and len(self.scanners) > self.whichScanner:
            self.dm.resettime()
            self.status = self.status.strip().split('\n')[-1]+'\n'+strtime()
            proc=Popen(['scanimage','-d',self.scanners[self.whichScanner]]+'--batch=/tmp/batch%d.tif --batch-count=1 --resolution 300 --format=tiff -l 14.5 -x 85 -t 10 -y 125'.split(),stdout=PIPE,stderr=PIPE)
            out,err = proc.communicate()
             #self.acquire()
            self.status+= (out+"\n"+err+'\n')
             #self.release()

            i=Image.open('/tmp/batch1.tif')
            i.filename =None
            try:
               i.load()
            except:
               pass
            if i != None:
               i.save('/tmp/batch2.tif')



#            
            proc=Popen('convert /tmp/batch2.tif -crop 817x1251+91+112 /tmp/inner1.tif'.split(),stdout=PIPE,stderr=PIPE)
            out,err = proc.communicate()
             #self.acquire()
            self.status+= (out+"\n"+err+'\n')

#            import pdb;pdb.set_trace()
            proc=Popen('convert /tmp/inner1.tif -density 300 -crop 8x12-17-19@! -shave 10x10 +repage /tmp/lowres%d.tif'.split(),stdout=PIPE,stderr=PIPE)
            out,err = proc.communicate()
             #self.acquire()
            self.status+= out+"\n"+err+'\n'

            output,failed,status=self.dm.parseImages()
            self.status += status

            for k,v in output.items():
               self.decoded[k] = v

            if len(self.decoded) == 96:
               self.status += "\nall found!\n"
               self.autoStopScan()
               self.dm.reinit()
            else:
               self.status += "\nkeep looking...\n"
               self.dm.reinit(failed)

            sleep(self.refreshInterval) 
            
         elif self.scanners == []:
            self.getScanners()
         


class MyHandler(BaseHTTPRequestHandler):

   def wwrite(self,data):
      self.wfile.write(data.replace('\n','<br>'))
      
   def do_GET(self):
      wwrite=self.wwrite
      try:
         #            print self.path
         if self.path.startswith("/scan/"):
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers() 
            if self.path.endswith("list"):
               l='\n'.join(MyHandler.sc.scanners)
               wwrite("scanners:\n%s"%l)
            elif self.path.endswith("start"):
               MyHandler.sc.startScan()
               wwrite("scan started")
            elif self.path.endswith("stop"):
               MyHandler.sc.stopScan()
               wwrite("scan stopped")
            elif self.path.endswith("status"):
               wwrite(MyHandler.sc.status)
            else:
               wwrite("unknown scan command")
               return
         elif self.path.endswith("test"):   #our dynamic content
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.end_headers()
            wwrite("hey, today is the " + str(time.localtime()[7]))
            wwrite(" day in the year " + str(time.localtime()[0]))
            return
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
      MyHandler.sc=ScanControl()
      MyHandler.sc.start()
      server = HTTPServer(('', PORT), MyHandler)
      print 'started httpserver...'
      server.serve_forever()
   except KeyboardInterrupt:
      print '^C received, shutting down server'
      server.socket.close()
      
if __name__ == '__main__':
   main()

