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

def getWellAV(fn,pref):
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

def getWellHP(fn,pref):
   n=fn.split(pref)[1].split('.')[0]
   if not n.isdigit():
      print "error, n:",n
      return -1
   n = int(n)
   #return n
   
   col = chr(ord('A')+int(n/12))
   row = 12-(n % 12)
   #print n, row, col
   return "%s%02d"%(col,row)

def getFileFromWellAV(well):
    w = well.split('_')
    if len(w) == 2:
        return int(w[0])+8*int(w[1])
    else:
        return -1

def getFileFromWellHP(well):
    w = well.split('_')
    if len(w) == 2:
        return 84-12*(7-int(w[0]))+(11-int(w[1]))
    else:
        return -1

class Config():
   data={'avision-600':['-crop 1634x2502+182+224',
                        '-crop 8x12-34-38@! -shave 20x20',
                        '-l 14.5 -x 85 -t 10 -y 125'],
          
          'avision-300':['-crop 817x1251+91+112',
                        '-crop 8x12-17-19@! -shave 10x10',
                        '-l 14.5 -x 85 -t 10 -y 125'],
          'hp3900-300': ['-crop 1250x836+134+82',
                         '-crop 12x8-19-17@! -shave 10x10',
                         '--mode Gray -l 45 -t 10 -x 130 -y 90 --opt_nowarmup=yes --opt_nogamma=yes'],
          'hp3900-600': ['-crop 2500x1672+268+164',
                         '-crop 12x8-38-34@! -shave 10x10',
                         '--mode Gray -l 45 -t 10 -x 130 -y 90 --opt_nowarmup=yes --opt_nogamma=yes']} #90=275
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
   def switch(key):
      Config.currentkey = key
      g=globals()
      if key.find('avision') != -1:
         g['getWell'] = getWellAV
         g['getFileFromWell'] = getFileFromWellAV
      elif key.find('hp') != -1: 
         g['getWell'] = getWellHP
         g['getFileFromWell'] = getFileFromWellHP
      return Config.data[key]

   @staticmethod
   def configByScanner(scan):   
      #maybe remember last settigns and only return those unless some new change.
      # can split this into two functions
      sn = scan.scannerNames[scan.whichScanner]
      key = sn+"-"+str(scan.res)

      if Config.has_key(key):
         cfg=Config.switch(key)
      else:
         print "no configuration for %s at %d dpi"%(sn,scan.res)
         print "using first listed configuration for %s"%sn
         ok = [i for i in Config.keys() if i.find(sn) != -1]
         if i == []:
            print "no luck finding that scanner"
            import pdb;pdb.set_trace()
         else:
            cfg = Config.switch(ok[0])
            scan.setNextRes(int(ok[0].split('-')[-1]))
      #print cfg
      density = "-density %d "%scan.res
      return cfg+[density]



#initialize on import

