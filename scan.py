#!/usr/bin/python

from os import path, listdir
#import pri

import threading

from time import sleep,strftime
from subprocess import Popen, PIPE
from datetime import datetime
import decode

defaultfn=['lowres','tif']
defaultdir= '/tmp/'


def modification_date(filename):
    t = path.getmtime(filename)
    retVal = str(datetime.fromtimestamp(t))
    return retVal.split('.')[0]

def strtime():
   return strftime("%Y-%m-%d %H:%M:%S")

class ScanControl(threading.Thread):
   def __init__(self):
      threading.Thread.__init__(self)

      self.forceRepeat = False
      self.getFilenames()
      self.dm = decode.DMDecoder(self.myDir,self.files)
      self.daemon = True #This kills this thread when the main thread stops  
      self.isScanning = False
      self.refreshInterval = 1 #in seconds
      self.scanners = [] 
      self.lock = threading.RLock()
      
      self.setStatus(strtime()+'\ninitialized')
      
      self.whichScanner = 0
      self.setDecoded({})
      self.filetime = ''
      self.mostRecentUpdate = datetime.now()


      self.decodeOnly = False

   def getDecoded(self):
       self.acquire()
       retVal = self.decoded.copy()
       self.release()
       return retVal

   def getNewDecoded(self,time):
       if self.mostRecentUpdate > time:
           #print time, "<",self.mostRecentUpdate
           #print "new update available"
           return self.getDecoded()
       else:
           return -1

   def setDecoded(self,val):
       self.acquire()
       self.decoded = val
       self.release()

   def getFilenames(self):
       self.pref=pref = defaultfn[0]
       self.myDir = defaultdir
       self.ext = '.'+defaultfn[1]
       
       self.files = [i for i in listdir(self.myDir) if i.find(pref) != -1 and ''.join(i.split(pref)).rstrip(self.ext).isdigit()]
       self.files.sort()

   def getScanners(self):
       self.acquire()
       retVal = self.scanners[:]
       self.release()
       return retVal

   def setStatus(self,val):
      self.acquire()
      self.status = val
      self.release()

   def getStatus(self):
      self.acquire()
      c = self.status[:]
      self.release()
      return c

   def updateStatus(self,val):
      self.acquire()
      self.status += val
      self.release()

   def reset(self):
      self.setDecoded({})
      self.dm.__init__(self.myDir,self.files)

   def startScan(self):
      self.refreshInterval = 1
      self.isScanning = True
      self.setStatus(strtime()+'\nstarted')
      self.dm.__init__()

   def stopScan(self):
      self.isScanning = False
      self.refreshInterval = 2
      self.setStatus(strtime()+'\nstopped')

   def autoStopScan(self):
      self.isScanning = False
      self.refreshInterval = 2
      self.updateStatus(strtime()+'\nstopped')

   def acquire(self):
      self.lock.acquire()
   def release(self):
      self.lock.release()
        
   def findScanners(self):
       proc=Popen(['scanimage',"-f","%d%n"],stdout=PIPE)
       out, err = proc.communicate()
       
       if out == '':
           scanners = []
       else:
           scanners = out.strip().split()
           scanners = filter(lambda x: x[:3] == 'net',scanners)
       
       self.acquire()
       self.scanners = scanners
       self.release()
   
   def _shellOut(self):

      proc=Popen(['scanimage','-d',self.scanners[self.whichScanner]]+'--batch=/tmp/batch%d.tif --batch-count=1 --resolution 300 --format=tiff -l 14.5 -x 85 -t 10 -y 125'.split(),stdout=PIPE,stderr=PIPE)
      out,err = proc.communicate()

      self.updateStatus(out+"\n"+err+'\n')

      ## fix tif routine:
      # i=Image.open('/tmp/batch1.tif')
      # i.filename =None
      # try:
      #    i.load()
      # except:
      #    pass
      # if i != None:
      #    i.save('/tmp/batch2.tif')

      proc=Popen('convert /tmp/batch1.tif -crop 817x1251+91+112 /tmp/inner1.tif'.split(),stdout=PIPE,stderr=PIPE)
      out,err = proc.communicate()
      self.updateStatus(out+"\n"+err+'\n')

      proc=Popen(('convert /tmp/inner1.tif -density 300 -crop 8x12-17-19@! -shave 10x10 +repage '+self.myDir+self.pref+'%d'+self.ext).split(),stdout=PIPE,stderr=PIPE)
      out,err = proc.communicate()

      self.updateStatus(out+"\n"+err+'\n')


   def _doDecode(self):
       output,failed,status=self.dm.parseImages()
       self.updateStatus(status)
       flag = False
       self.acquire()
       for k,v in output.items():
           self.decoded[k] = [v,strtime(),
                              modification_date(self.dm.myDir+k)]
           flag = True
       self.release()
       # if any new output, update field for getting new output
       if flag:
           self.mostRecentUpdate = datetime.now()

       if self.forceRepeat:
           self.updateStatus("\n scanning forced, repeating...\n")
           self.dm.__init__()
       elif len(failed) == 0:
           self.updateStatus("\nall found!\n")
           self.autoStopScan()
           self.dm.__init__()
       else:
           self.updateStatus("\nkeep looking...\n")
           print failed
           self.dm.__init__(files=failed)

       return output,failed

   def run(self):
       self.findScanners()
       while 1:
           if self.isScanning and len(self.scanners) > self.whichScanner:
               self.dm.resettime()
               self.setStatus(self.getStatus().strip().split('\n')[-1]+'\n'+strtime())
               
               self._shellOut()
               self._doDecode()
               sleep(self.refreshInterval) 
           elif self.decodeOnly:
               self.dm.resettime()
               self._doDecode()
               self.decodeOnly = False
           elif self.scanners == []: # or is scanner error..
               self.findScanners()
