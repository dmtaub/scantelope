#!/usr/bin/python
#
# Copyright (c) 2011 Ginkgo Bioworks Inc.
# Copyright (c) 2011 Daniel Taub
#
# This file is part of DMTube.
#
# DMTube is free software: you can redistribute it and/or modify
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
batch processing script, unused in server.

"""

import sys,os, subprocess
from pydmtx import DataMatrix, Image
from pdb import set_trace as st
import findcode
import time
import cv
findcode.low_res = True
EXPECTED_LEN = 10

if findcode.low_res:
  SHRINK = 1
else:
  SHRINK = 2
myDir='/tmp/'
pref='split'
ext='.png'


if __name__ == '__main__':
  do_display = False
  verbose = False
  totalTime = time.time()
  failed = []
  files = None
  if len(sys.argv) > 1:
    do_display = bool(int(sys.argv[1]))
    if len(sys.argv) > 2:
      # if only one arg and it has no number in it, assume it's the prefix and suffix only
      if len(sys.argv) == 3 and not reduce(lambda x,y:x or y,map(lambda x: x.isdigit(),sys.argv[2]),False):
        splt = sys.argv[2].split('.') 
        pref = splt[0]
        if pref.find('/') != -1:
          myDir,pref = os.path.split(pref)
        ext = '.'+splt[1]
      else:
        files = sys.argv[2:]
        
  myDir += '/'
  if files == None:
      files = [i for i in os.listdir(myDir) if i.find(pref) != -1 and ''.join(i.split(pref)).rstrip(ext).isdigit()]
      files.sort()
      
  n=0
  m=0

  lastCVTime = 0
  timeForCV = 0
  for filename in files:

      is_found = False    
        
      if filename.find('/') != -1:
        myDir,filename = os.path.split(filename)
        myDir += '/'
 
      lastCVTime = time.time()

      cv_orig,cv_smoo,cv_final = findcode.findAndOrient(myDir,filename,do_display, verbose)

      timeForCV += (time.time() - lastCVTime)
      
      for img,name in [#[cv_smoo,"smooth"],
                       [cv_final,"clipped"],
                       [cv_orig,"original"]]:
        
        if is_found:
          break
        
        dmtx_im = Image.fromstring("L", cv.GetSize(img), img.tostring())

        padding = 0.2
        ncols,nrows = dmtx_im.size

        padw = (ncols)*padding
        padh = (nrows)*padding

        isize = (round(ncols+2*padw),round(nrows+2*padh))#cols*photow+padw,nrows*photoh+padho)

    # Create the new image. The background doesn't have to be white

        dmtx_image = Image.new('RGB',isize,0)
        bbox = (round(padw),round(padh),ncols+round(padw),nrows+round(padh))

         
        dmtx_image.paste(dmtx_im,bbox)
# 	dmtx_im.save("/tmp/t1.png")
#	dmtx_image.save("/tmp/t2.png")

#	import pdb;pdb.set_trace()
        (width, height) = dmtx_image.size
        dm_read = DataMatrix(max_count = 1, timeout = 300, min_edge = 20, max_edge = 32, threshold = 5, deviation = 10, shrink = SHRINK)
        #dm_read = DataMatrix(max_count = 1, timeout = 300, shape = DataMatrix.DmtxSymbol12x12, min_edge = 20, max_edge = 32, threshold = 5, deviation = 10)
        dmtx_code = dm_read.decode (width, height, buffer(dmtx_image.tostring()))

        if dmtx_code is not None and len(dmtx_code) == EXPECTED_LEN:
            how = "Quick Search: "+str(name)
            is_found = True
        else:
          dmtx_im.save("/tmp/t1.png")
          dmtx_image.save("/tmp/t2.png")
          #import pdb;pdb.set_trace()



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
        print filename, out, how
      else:
        print filename, None
        failed.append(filename)
      m+=1

        

  print "\nFound %d of %d in "%(n,m),time.time()-totalTime," seconds.",
  print "(OpenCV:",timeForCV," sec)\n"
  
  if not(len(failed) == 0):# and verbose:
    dirr = ' '+myDir
    print dirr+dirr.join(failed)
