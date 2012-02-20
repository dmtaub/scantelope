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
Configuration module for Scantelope.

"""

from ConfigParser import NoOptionError, SafeConfigParser as cfgParser
from os.path import exists, getmtime, isdir
from os import getenv, listdir, mkdir
HOMEDIR = getenv("HOME")
customDir = HOMEDIR+'/.scantelope'

from datetime import datetime

from socket import gethostname
CUSTOM_NAME = "custom_"+gethostname()

cfgParser.getpair = lambda self,section,key: map(int,self.get(section,key)[1:-1].split(','))

def modification_date(filename):
    t = getmtime(filename)
    retVal = str(datetime.fromtimestamp(t))
    return retVal.split('.')[0]

def generateCropA(dx,dy,x,y):
   def byOffset(off): 
      if type(off) is list:
         return '-crop {0}x{1}+{2}+{3}'.format(dx,dy,x+off[0],y+off[1])
      else:
         return (x,y),dx,dy
   return byOffset

def CropB(landscape,factor):
   if landscape:
      crop = '-crop 12x8-%d-%d@! -shave %dx%d'%(19*factor,17*factor,10*factor,10*factor)
   else:
      crop = '-crop 8x12-%d-%d@! -shave %dx%d'%(17*factor,19*factor,10*factor,10*factor)
   return crop

class Config():
   configfile = "scantelope.cfg"

   offset = [0,0]
   names = set()

   # should make data more generic with portrait and landscape modes, then sections in configuration file for each scanner
   data={}

   @staticmethod
   def generateData(res,dx,dy,x,y,options=''):
      landscape = (dx > dy)
      factor = res / 300     
      return [generateCropA(dx*factor,dy*factor,x*factor,y*factor),CropB(landscape,factor),options]

   @staticmethod
   def saveCalibrated(dx,dy,x,y,options):
      name=Config.createDataEntry(dx,dy,x,y)
      Config.switch('%s-%d'%(name,Config.res))
      def callback(c):
         Config.setConfig(c,name,[['origin',    str([x,y])],
                                  ['dx',    str(dx)],
                                  ['dy',   str(dy)],
                                  ['options', str(options)]])
      Config.saveFile(customDir+'/'+CUSTOM_NAME,[callback])
      print "\tAdded Calibration <",name,"> to presets."
     
   @staticmethod
   def createDataEntry(dx,dy,x,y,name=None):
      #should test for existence in config file?
      if name == None:
          name = CUSTOM_NAME
      for res in Config.validResolutions():
         Config.data['%s-%d'%(name,res)] = Config.generateData(res,dx,dy,x,y)
      Config.names.add(name)
      return name

   @staticmethod
   def validResolutions():
      return [300,600]

   @staticmethod
   def makeKey():
      key = Config.active + '-'+str(Config.res)
      if Config.has_key(key):
         Config.currentKey = key
         print "key set to",key
      else:
         raise KeyError(key+" missing from configuration")

   @staticmethod
   def setRes(res):
      Config.res = res
      Config.makeKey()
#      Config.makeKey(res = res)

   @staticmethod
   def setActive(name):
      Config.active = name
      Config.makeKey()
      Config.setMethods()

   @staticmethod
   def saveFile(filename=None,callbacks = []):
       if filename == None:
         filename = Config.configfile
       c=cfgParser()

       # preserve other sections
       if exists(filename):
           f=open(filename,'r')
           c.readfp(f)
           f.close()

       f=open(filename,'w')       

       Config.setConfig(c,'defaults',[['active',       Config.active],
                                      ['offset',    str(Config.offset)],
                                      ['resolution',   str(Config.res)]])
       for callback in callbacks:
          callback(c)

       c.write(f)
       f.close()
       Config.configModified = modification_date(customDir)
       print "Configuration file<%s> saved"%filename


   @staticmethod
   def setConfig(cparser,section,pairs):
      if not cparser.has_section(section):
         cparser.add_section(section)
      for k,v in pairs:
         cparser.set(section,k,v)

   @staticmethod
   def getConfig(cparser,section):
      try:
         origin = cparser.getpair(section,'origin')
         options = cparser.get(section,'options')
         dx = cparser.getint(section,'dx')
         dy = cparser.getint(section,'dy')
      except NoOptionError, e:
         print e
         return False
      name = Config.createDataEntry(dx,dy,origin[0],origin[1],section)
      print "\tAdded <",name,"> to presets."

   @staticmethod
   def loadLocalFiles():
     retVal = False
     if isdir(customDir):
       for filename in listdir(customDir):
         retVal |= Config.loadFile(customDir +'/'+filename)  
     else:
       mkdir(customDir)
     return retVal

   @staticmethod
   def loadFile(cfile=None):
      retVal = False
      if cfile == None:
        cfile=Config.configfile 
        hostnameMatch = False
      else:  
        hostnameMatch = (customDir+'/'+CUSTOM_NAME == cfile)
      # returns false if no file or no 'defaults' section
      print "Processing conf <%s>"%cfile
      if not exists(cfile):
         print "\tfile not found..."
      else:
         f=open(cfile,'r')
         c=cfgParser()
         c.readfp(f)
         
         for s in c.sections():
            if s == 'defaults':
               if hostnameMatch:
                 retVal = True
                 Config.active = c.get('defaults','active') or 'avision' #if (zero-length)
                 Config.offset = c.getpair('defaults','offset') or [0,0]
                 Config.res = c.getint('defaults','resolution') or 300
                 # switch here?
            else:
               Config.getConfig(c,s)
         #generate data dict based on cfg file
         if not retVal:
            print "\t(wrong hostname or no 'defaults' section)"
         else:
            print "\t*Default found!"
         f.close()
      return retVal

   @staticmethod
   def getWellAV(fn,pref):
      n=fn.split(pref)[1].split('.')[0]
      if not n.isdigit():
         print "error, n:",n
         return -1
      n = int(n)

      row = chr(ord('A')+int(n%8))
      col = (n / 8) + 1

      return "%s%02d"%(row,col)

   @staticmethod
   def getWellHP(fn,pref):
      n=fn.split(pref)[1].split('.')[0]
      if not n.isdigit():
         print "error, n:",n
         return -1
      n = int(n)

      col = chr(ord('A')+int(n/12))
      row = 12-(n % 12)

      return "%s%02d"%(col,row)

   @staticmethod
   def getFileFromWellAV(well):
       w = well.split('_')
       if len(w) == 2:
           return int(w[0])+8*int(w[1])
       else:
           return -1

   @staticmethod
   def getFileFromWellHP(well):
       w = well.split('_')
       if len(w) == 2:
           return 84-12*(7-int(w[0]))+(11-int(w[1]))
       else:
           return -1
   @staticmethod
   def hasCustom(key):
      #returns key if no custom entry found
       name,res=key.split('-')
       testKey = CUSTOM_NAME+'-'+res
       if Config.data.has_key(testKey):
           ret = testKey
       else:
           ret = key
       return ret

   @staticmethod
   def reloadConfig(key = 'avision-300'):
      Config.data = {}
      Config.loadFile()
      defaultLoaded = Config.loadLocalFiles()
      # maybe want to choose default key more intelligently (name of found scanners?)
#      Config.res = Config.validResolutions()[0]
      customHostKey = Config.hasCustom(key)
      if not defaultLoaded:
         Config.switch(customHostKey)
         Config.saveFile(customDir+'/'+CUSTOM_NAME)
      else:
         try:
            Config.makeKey()
         except KeyError, e:
            print "Error:", e, "defaulting to",key
            Config.switch(customHostKey)
         Config.setMethods()
         print 'Loaded configuration files'
      Config.configModified = modification_date(customDir)
      return Config.res

   @staticmethod
   def has_key(key):
      return Config.data.has_key(key)

   @staticmethod
   def keys():
      return Config.data.keys()

   @staticmethod
   def values():
      return Config.data.values()

   @staticmethod
   def setMethods():
      rect=Config.currentConfiguration()[0](0)
      landscape = (rect[1] > rect[2])
      if not landscape:    #Config.scanner in ['avision','custom']:
         Config.getWell = staticmethod(Config.getWellAV)
         Config.getFileFromWell = staticmethod(Config.getFileFromWellAV)
      else:                 #Config.scanner == 'hp3900':
         Config.getWell = staticmethod(Config.getWellHP)
         Config.getFileFromWell = staticmethod(Config.getFileFromWellHP)


   @staticmethod
   def switch(key):
      active,resolution = key.split('-')

      Config.res = int(resolution)      
      Config.active = active
      Config.currentKey = key
      print "key set to",key
      
      Config.setMethods()

      return Config.data[key]

   @staticmethod
   def currentConfiguration():
      return Config.data[Config.currentKey]

#initialize on import

