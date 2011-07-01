# 
# Copyright (c) 2011 Ginkgo Bioworks Inc.
# Copyright (c) 2011 Daniel Taub
#
# This file is part of Lab Server DMTube.
#
# Lab Server DMTube is free software: you can redistribute it and/or modify
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
decode module for Lab Server DMTube.

"""
#from os import curdir, sep, path

EXPECTED_LEN = 10


from time import time
from pydmtx import DataMatrix, Image
import findcode
import cv


class DMDecoder():
   do_display = False
   verbose = False
   totalTime = time()

   def resettime(self):
      self.totalTime = time()

   def __init__(self,myDir = None,files = None):
       if myDir != None:
           self.myDir = myDir
       if files != None:
           self.files = files
       self.output = {}
       self.failed = []
       self.status = ''

       self.resettime()

   def parseImages(self, files = None):
      if files != None:
          self.files = files

      n=0
      m=0
      failNum=0
      lastCVTime = 0
      timeForCV = 0
      print "len self.files in decode: ",len(self.files)
      stop = False
#      import pdb;pdb.set_trace()
      
      for filename in self.files:

          is_found = False    

#          if filename.find('/') != -1:
#            self.myDir,filename = path.split(filename)
#            self.myDir += '/'
          
          lastCVTime = time()

          cv_orig,cv_smoo,cv_final = findcode.findAndOrient(self.myDir,
                                                            filename,
                                                            self.do_display, 
                                                            self.verbose)
          timeForCV += (time() - lastCVTime)
          cv.SaveImage(self.myDir+filename.replace('tif','jpg'),cv_final)

          test = cv.Avg(cv_final) 
          if stop == True:
             pdb.set_trace()
          if test[0] < 130 and test[0] > 45:   # hard threshold works for avision
           for img,name in [#[cv_smoo,"smooth"], #seems to introduce many errors
                           [cv_final,"clipped"],
                           [cv_orig,"original"]]:
             if is_found:
                break

             dmtx_im = Image.fromstring("L", cv.GetSize(img), img.tostring())

             if name != "original":
                 padding = 0.1
             else:
                 padding = 0

             ncols,nrows = dmtx_im.size
             padw = (ncols)*padding
             padh = (nrows)*padding
             isize = (int(round(ncols+2*padw)),int(round(nrows+2*padh)))

             # Create a new color image onto which we can paste findcode output
             dmtx_image = Image.new('RGB',isize,0)
             bbox = (round(padw),round(padh),ncols+round(padw),nrows+round(padh))
             dmtx_image.paste(dmtx_im,map(int,bbox))
             (width, height) = dmtx_image.size
             
             # Send to datamatrix library
             if findcode.low_res: 
                dm_read = DataMatrix(max_count = 1, timeout = 300, min_edge = 20, max_edge = 32, threshold = 5, deviation = 10)
             else:
                dm_read = DataMatrix(max_count = 1, timeout = 300, min_edge = 20, max_edge = 32, threshold = 5, deviation = 10, shrink = 2)


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
          else:
             failNum+=1
          if is_found:
             n+=1
             self.output[filename] = out
          else:
             print filename, None, test[0]
             self.failed.append(filename)
          m+=1
      print failNum, "failed to produce images worth decoding"
      self.status += "\nFound %d of %d in "%(n,m)

      self.status += str(time()-self.totalTime)+" seconds.\n"
      self.status += "(OpenCV: "+str(timeForCV)+" sec)\n"

      if not(len(self.failed) == 0):# and verbose:
         dirr = ' '+self.myDir
         self.status+= "\nmissing: "+str(self.failed)+'\n'

      return self.output,self.failed,self.status
