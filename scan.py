#!/usr/bin/python

from os import path, listdir
#import pri

import threading

from time import sleep,strftime,time
from subprocess import Popen, PIPE
from datetime import datetime
import decode

defaultfn=['lowres','tif']
defaultdir= '/tmp/'


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

def modification_date(filename):
    t = path.getmtime(filename)
    retVal = str(datetime.fromtimestamp(t))
    return retVal.split('.')[0]

def strtime():
   return strftime("%Y-%m-%d %H:%M:%S")

class ScanControl(threading.Thread):
   listCodes = []
   def __init__(self):
      threading.Thread.__init__(self)

      self.lock = threading.RLock()

      if decode.findcode.low_res == True:
          self.res = 300
      else:
          self.res = 600
      self.forceRepeat = False
      self.getFilenames()
      self.dm = decode.DMDecoder(self.myDir,self.files)#,res = self.res)
      self.daemon = True #This kills this thread when the main thread stops  
      self.isScanning = False
      self.refreshInterval = 1 #in seconds
      self.scanners = [] 
      
      
      self.setStatus(strtime()+'\ninitialized')
      
      self.whichScanner = 0
      self.setDecoded({})
      self.filetime = ''
      self.mostRecentUpdate = datetime.now()
      self.timeout = -1
      self.lastActive = time()
      self.decodeOnly = False

   def resetTimer(self):
      self.lastActive = time()

   def timeoutExpired(self):
      if self.timeout == -1:
         return false
      else:
         return abs(time()-self.lastActive) > self.timeout

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

   def getCodes(self):
       self.acquire()
       retVal = self.listCodes[:]
       self.release()
       return retVal

   def setCodes(self,val):
       self.acquire()
       self.listCodes = val
       self.release()

   def getFilenames(self):
       self.acquire() # ***
       
       self.pref=pref = defaultfn[0]
       self.myDir = defaultdir
       self.ext = '.'+defaultfn[1]
       
       self.files = [i for i in listdir(self.myDir) if i.find(pref) != -1 and ''.join(i.split(pref)).rstrip(self.ext).isdigit()]
       self.files.sort()
       self.release() # ***

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
      self.resetDecoded()
      self.dm.__init__(self.myDir,self.files)

   def resetDecoded(self):
      self.setDecoded({})

   def startScan(self):
      self.acquire() # ***
      self.refreshInterval = 1
      self.isScanning = True
      self.dm.__init__()
      self.release() # ***

      self.setStatus(strtime()+'\nstarted')
      

   def stopScan(self):
      self.acquire() # ***
      self.isScanning = False
      self.refreshInterval = 2
      self.release() # ***
      self.setStatus(strtime()+'\nstopped')

   def autoStopScan(self):
      self.acquire() # ***
      self.isScanning = False
      self.refreshInterval = 2
      self.release() # ***
      self.updateStatus(strtime()+'\nautostopped')

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
      
      proc=Popen(['scanimage','-d',self.scanners[self.whichScanner]]+('--batch=/tmp/batch%d.tif --batch-count=1 --resolution '+str(self.res)+' --format=tiff -l 14.5 -x 85 -t 10 -y 125').split(),stdout=PIPE,stderr=PIPE)
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

      if self.res == 300:
          cropA = '-crop 817x1251+91+112'
          cropB = '-crop 8x12-17-19@! -shave 10x10'
          density = '-density 300 '
      elif self.res == 600:
          cropA = '-crop 1634x2502+182+224'
          cropB = '-crop 8x12-34-38@! -shave 20x20'
          density = '-density 600 '

      proc=Popen(('convert /tmp/batch1.tif '+density+cropA+' /tmp/inner1.tif').split(),stdout=PIPE,stderr=PIPE)
      out,err = proc.communicate()
      self.updateStatus(out+"\n"+err+'\n')

      proc=Popen((('convert /tmp/inner1.tif '+density+cropB+' +repage '+self.myDir+self.pref+'%d'+self.ext)).split(),stdout=PIPE,stderr=PIPE)
      out,err = proc.communicate()

      self.updateStatus(out+"\n"+err+'\n')
      

   def _doDecode(self):
       output,failed,status=self.dm.parseImages()
       self.updateStatus(status)
       flag = False
       self.acquire()
       if self.forceRepeat:
          self.decoded = {}
          flag = True
       for k,v in output.items():
           self.decoded[k] = [v,strtime(),
                              modification_date(self.dm.myDir+k)]
           flag = True
       self.release()
       # if any new output, update field for getting new output
       if flag:
           self.mostRecentUpdate = datetime.now()

       if self.forceRepeat:
           if self.timeoutExpired():
              self.autoStopScan()
              self.updateStatus("\nTimer has run down\n")
           else:
              self.updateStatus("\nscanning forced, repeating...\n")
           self.dm.__init__(self.myDir,self.files)
       elif len(failed) == 0:
           self.autoStopScan()
           self.updateStatus("\nall found!\n")
           self.dm.__init__(self.myDir,self.files)
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
           elif self.decodeOnly:
               self.dm.resettime()
               self._doDecode()
               if not self.forceRepeat:
                   self.decodeOnly = False
           elif self.scanners == []: # or is scanner error..
               self.findScanners()
           sleep(self.refreshInterval) 
