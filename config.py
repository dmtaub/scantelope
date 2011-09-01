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
from os.path import exists

cfgParser.getpair = lambda self,section,key: map(int,self.get(section,key)[1:-1].split(','))


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

   # should make data more generic with portrait and landscape modes, then sections in configuration file for each scanner
   data={}
   olddefaults={'avision-600':[generateCropA(1634,2502,182,224),
                        '-crop 8x12-34-38@! -shave 20x20',
                        '-l 14.5 -x 85 -t 10 -y 125'],
          
          'avision-300':[generateCropA(817,1251,91,112),
                        '-crop 8x12-17-19@! -shave 10x10',
                        '-l 14.5 -x 85 -t 10 -y 125'],
          'hp3900-300': [generateCropA(1250,836,134,82),
                         '-crop 12x8-19-17@! -shave 10x10',
                         '--mode Gray -l 45 -t 10 -x 130 -y 90 --opt_nowarmup=yes --opt_nogamma=yes'],
          'hp3900-600': [generateCropA(2500,1672,268,164),
                         '-crop 12x8-38-34@! -shave 10x10',
                         '--mode Gray -l 45 -t 10 -x 130 -y 90 --opt_nowarmup=yes --opt_nogamma=yes']} #90=275


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
      Config.saveFile([callback])
      print "Added <",name,"> to presets."
     
   @staticmethod
   def createDataEntry(dx,dy,x,y,name='custom'):
      #should test for existence in config file?
      for res in Config.validResolutions():
         Config.data['%s-%d'%(name,res)] = Config.generateData(res,dx,dy,x,y)
      return name

   @staticmethod
   def validResolutions():
      return [300,600]

   @staticmethod
   def makeKey():
      key = Config.scanner + '-'+str(Config.res)
      if Config.has_key(key):
         Config.currentKey = key
      else:
         raise KeyError(key+" missing from configuration")

   @staticmethod
   def setRes(res):
      Config.res = res
      Config.makeKey()
#      Config.makeKey(res = res)


   @staticmethod
   def saveFile(callbacks = []):
       c=cfgParser()

       # preserve other sections
       if exists(Config.configfile):
           f=open(Config.configfile,'r')
           c.readfp(f)
           f.close()

       f=open(Config.configfile,'w')       

       Config.setConfig(c,'defaults',[['scanner',       Config.scanner],
                                      ['offset',    str(Config.offset)],
                                      ['resolution',   str(Config.res)]])
       for callback in callbacks:
          callback(c)

       c.write(f)
       f.close()
       print "Configuration file saved"

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
      print "Added <",name,"> to presets."

   @staticmethod
   def loadFile():
      # returns false if no file or no 'defaults' section
      retVal = False
      if not exists(Config.configfile):
         print "Configuration file not found..."
      else:
         f=open(Config.configfile,'r')
         c=cfgParser()
         c.readfp(f)
         
         for s in c.sections():
            if s == 'defaults':
               retVal = True
               Config.scanner = c.get('defaults','scanner') or 'avision' #if (zero-length)
               Config.offset = c.getpair('defaults','offset')
               Config.res = c.getint('defaults','resolution')
                 # switch here?
            else:
               Config.getConfig(c,s)
         #generate data dict based on cfg file
         if not retVal:
            print "Missing 'defaults' section"
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
   def readInitialConfig(key = 'avision-300'):
      # maybe want to choose default key more intelligently (name of found scanners?)
#      Config.res = Config.validResolutions()[0]
      if not Config.loadFile():
         Config.switch(key)
         Config.saveFile()
      else:
         Config.makeKey()
         Config.setMethods()
         print 'Loaded configuration'

      return Config.res, Config.getWell, Config.getFileFromWell

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
      if Config.scanner in ['avision','custom']:
         Config.getWell = staticmethod(Config.getWellAV)
         Config.getFileFromWell = staticmethod(Config.getFileFromWellAV)
      elif Config.scanner == 'hp3900':
         Config.getWell = staticmethod(Config.getWellHP)
         Config.getFileFromWell = staticmethod(Config.getFileFromWellHP)


   @staticmethod
   def switch(key):
      scanner,resolution = key.split('-')

      Config.res = int(resolution)      
      Config.scanner = scanner
      Config.currentKey = key
      
      Config.setMethods()

      return Config.data[key]

   @staticmethod
   def currentConfiguration():
      return Config.data[Config.currentKey]

   # deprecated
   @staticmethod
   def configByScannerAndRes(scanner,res):   
      #maybe remember last settings and only return those unless some new change.
      # can split this into two functions, init and gette
      key = scanner+"-"+str(res)

      if Config.has_key(key):
         cfg=Config.switch(key)
      else:
         print "no configuration for %s at %d dpi"%(scanner,res)
         print "using first listed configuration for %s"%scanner
         ok = [i for i in Config.keys() if i.find(scanner) != -1]
         if i == []:
            print "no luck finding that scanner"
            import pdb;pdb.set_trace()
         else:
            cfg = Config.switch(ok[0])
      #print cfg
      #density = "-density %d "%Config.res
      #return cfg+[density,Config.res]
      return cfg+[Config.res]



#initialize on import

