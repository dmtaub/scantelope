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
Scanner interface module (threaded) for Scantelope.

"""
import threading

from time import sleep,strftime,time
from subprocess import Popen, PIPE
from datetime import datetime
import decode
from config import Config, modification_date
defaultfn=['split','tif']
defaultdir= '/tmp/'

def strtime():
   return strftime("%Y-%m-%d %H:%M:%S")

class ScanControl(threading.Thread):
   listCodes = []
   def __init__(self,event):
       threading.Thread.__init__(self)

       self.lock = threading.RLock()
       self.event = event
       
       self.forceRepeat = False
       self.getFilenames()
       self.dm = decode.DMDecoder(self.myDir,self.files)#,res = self.res)
       self.daemon = True #This kills this thread when the main thread stops  
       
       self.scanners = {} 
       self.scannerNames = {0:"none"}

       self.isScanning = False
       self.calibrating= False
       
       res = Config.reloadConfig()
       
       self.setNextRes(res)
       self.setResFromNext()
       
#      self.whichScanner = 0
       self.nextScanner = 0 #bypasses checks since scanners dict is empty
       self.setScannerFromNext()       
       self.nextConfig = None
      
       self.setDecoded({})
       self.mostRecentUpdate = datetime.now()      
       self.decodeOnly = False       

       self.setStatus(strtime()+'\ninitialized\n')

   def testUpdatedConfig(self):
       self.setScannerFromNext()
       self.setResFromNext()
       self.setConfigFromNext()

   def setResFromNext(self):
       self.acquire()
       if self.nextRes != None:
           Config.setRes(self.nextRes)
           if Config.res == 300:
               low_res = True
           else:
               low_res = False
           decode.findcode.low_res = low_res         
           self.nextRes = None
       self.release()

   def setNextRes(self,res):
       if res in Config.validResolutions():
           self.acquire()
           self.nextRes = res
           self.release()
           return True
       else:
           return False

   def setScannerFromNext(self):
       self.acquire()
       if self.nextScanner != None:
           self.whichScanner = self.nextScanner
           self.nextScanner = None
       self.release()
  
   def setNextScanner(self,w):
       if len(self.scanners) > w and w >= 0:
           self.acquire()
           self.nextScanner = w
           self.release()
           ret = True
       else:
           ret = False
       return ret

   def setConfigFromNext(self):
       modDate= modification_date(Config.configfile)
       if modDate != Config.configModified:
           print "Configuration modified, reloading..."
           self.acquire()
           Config.reloadConfig(Config.currentKey)
           self.release()

       self.acquire()
       if self.nextConfig != None:
           Config.setActive(self.nextConfig)
           self.nextConfig = None
       self.release()

   def setNextConfig(self,config):
       if config in Config.names:
           self.acquire()
           self.nextConfig = config
           self.release()
           return True
       else:
           return False

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
       
       self.files = self.files = [pref+str(i)+self.ext for i in range(96)] 
       self.files.sort()
       self.release() # ***

   def getScanners(self):
       #self.findScanners()
       self.acquire()
       retVal = self.scanners#.values()
       self.release()
       return retVal

   def setStatus(self,val):
       self.acquire()
       self.status = val
       self.release()

   def getStatus(self):
       self.acquire()
       if self.nextRes or self.nextScanner:
           nr = self.nextRes or Config.res
           name = self.nextScanner != None and self.scannerNames[self.nextScanner] or "same"
           next = " -> %s %ddpi\n"%(name,nr)
       else:
           next = "\n"
       c = self.scannerNames[self.whichScanner]+" as "+Config.active+" at "+str(Config.res)+"dpi"+next
       c += self.status[:]
       self.release()
       return c

   def updateStatus(self,val):
       self.acquire()
       self.status += val
       self.release()

   def reset(self):
       self.resetDecoded()
       self.acquire()
       self.dm.__init__(self.myDir,self.files)
       self.mostRecentUpdate = datetime.now()
       self.release()

   def resetDecoded(self):
       self.setDecoded({})

   def initScan(self):
       self.acquire() # ***
       self.dm.__init__()
       self.release() # ***
       print "legacy code reached"
       self.setStatus(strtime()+'\ndecoder initialized\n')
      

#   def stopScan(self):
#      self.setStatus(strtime()+'\nstopped')

   def autoStopScan(self):
       self.updateStatus(strtime()+'\nautostopped')
       self.isScanning = False #event.clear()
      

   def acquire(self):
       self.lock.acquire()
   def release(self):
       self.lock.release()
        
   def findScanners(self):
       print "finding scanners..."
       proc=Popen(['scanimage',"-f","%d%n"],stdout=PIPE)
       out, err = proc.communicate()
       if out == '':
           scanners = []
       else:
           scanners = out.strip().split()
           # look for network sane scanners first, or default to local
           ss = filter(lambda x: x[:3] == 'net',scanners)
           if not ss:
               idx = 0
           else:
               scanners = ss
               idx = 2
           scannerIds = dict(zip(range(len(scanners)),scanners))
           scannerNames = dict(zip(range(len(scanners)),
                                   map(lambda x: x.split(':')[idx],scanners)))  
           self.acquire()
           self.scanners = scannerIds
           self.scannerNames = scannerNames or self.scannerNames
           self.release()

   def calibrateNext(self):
       self.acquire()
       self.calibrating = True
       self.release()

   def _calibrate(self):
       self.updateStatus("calibrating\n\n")
       x,y,dx,dy = decode.findcode.calibrate("/tmp/calib1.tif")
       #print (x,y,dx,dy)
       self.acquire()
       Config.saveCalibrated(dx,dy,x,y,'')
       self.calibrating = False
       self.release()

   def _shellOut(self):
       self.testUpdatedConfig()
       
       cropA,cropB,position = Config.currentConfiguration()

       if self.calibrating:
           self._shell_obtain_fullscan()
           self._calibrate()
           return False
       else:
           self._shell_obtain_images(cropA,cropB,position)
           return True
   
   def _shell_obtain_fullscan(self):
       proc=Popen(['scanimage','-d',self.scanners[self.whichScanner]]+('--batch=/tmp/calib%d.tif --batch-count=1 --resolution '+str(Config.res)+' --format=tiff ').split(),stdout=PIPE,stderr=PIPE)
       out,err = proc.communicate()
       self.updateStatus(out+"\n"+err+'\n')


   def _shell_obtain_images(self,cropA,cropB,position):
       proc=Popen(['scanimage','-d',self.scanners[self.whichScanner]]+('--batch=/tmp/batch%d.tif --batch-count=1 --resolution '+str(Config.res)+' --format=tiff '+position).split(),stdout=PIPE,stderr=PIPE)
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

       density = "-density %d "%Config.res
      
       proc=Popen(('convert /tmp/batch1.tif '+density+cropA(Config.offset)+' /tmp/inner1.tif').split(),stdout=PIPE,stderr=PIPE)
       out,err = proc.communicate()
       self.updateStatus(out+"\n"+err+'\n')

      # could do this stuff in openCV or PIL as well...
       proc=Popen((('convert /tmp/inner1.tif /tmp/inner.jpg')).split(),stdout=PIPE,stderr=PIPE)
       out,err = proc.communicate()
       self.updateStatus(out+"\n"+err+'\n')

       proc=Popen((('convert /tmp/inner1.tif '+density+cropB+' +repage '+self.myDir+self.pref+'%d'+self.ext)).split(),stdout=PIPE,stderr=PIPE)
       out,err = proc.communicate()

       self.updateStatus(out+"\n"+err+'\n')
      

   def _doDecode(self):
       try:
           output,failed,status=self.dm.parseImages()
       except Exception, e:
           print "ERROR in parseImages:",str(e)
           self.setStatus("\nERROR in parseImages, specify a different configuration via use/*name*\n\n")
           return
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
           self.updateStatus("\nscanning forced, repeating...\n")
           self.dm.__init__(self.myDir,self.files)
       elif len(failed) == 0:
           self.autoStopScan()
           self.updateStatus("\nall found!\n")
           self.dm.__init__(self.myDir,self.files)
       else:
           self.updateStatus("\nkeep looking...\n")
           #print failed
           self.dm.__init__(files=failed)

       return output,failed

   def enableScan(self):
       self.acquire()
       self.isScanning = True
       self.release()

   def run(self):
       #self.findScanners()
       origNumScanners = len(self.scanners)
       while 1:
           if self.isScanning:
               if self.scanners.has_key(self.whichScanner):
                   self.setStatus('\n'.join(self.getStatus().strip().split('\n')[-10:])+strtime())
                   if self._shellOut():
                       self._doDecode()
               elif self.decodeOnly:
                   self._doDecode()
                   if not self.forceRepeat:
                       self.decodeOnly = False
               elif len(self.scanners) < origNumScanners:
                   self.findScanners() #look if disconnected
                #maybe limit to looking 5 times and then wait 50 times before trying again
               #print "WAIT"
               self.event.wait() #stop here until event set from serv.py
               #print "DONE WAIT"
               self.event.clear() #means that it will wait the next time arount
           # sleep?
