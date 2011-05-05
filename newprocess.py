#!/usr/bin/python
import sys,os, subprocess
#from pydmtx import DataMatrix, Image
from pdb import set_trace as st
import findcode
import time
from opencv.highgui import cvSaveImage
from ginkgoDmtx import ModuleECC200, ImageDecode

myDir='/tmp/'
pref='twistlow'
ext='.tif'


if __name__ == '__main__':
  do_display = False
  hacked = False
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
      cv_im = findcode.findAndOrient(myDir,filename,do_display, hacked,verbose)#[3] > 0:
      myMat = findcode.matrixFromImage(cv_im,do_display,verbose)
      timeForCV += (time.time() - lastCVTime)
      
      


      #      dmtx_image = Image.open(myDir+filename)
      fn = "/tmp/im.tif"
      #cvSaveImage(fn,cv_im)
#      st()
#       myMat= [
# [1,0,1,1,1,1,1,0,1,0],
# [0,0,1,1,0,0,1,0,0,0],
# [1,1,1,0,0,1,1,1,1,0],
# [1,1,0,0,1,1,1,0,0,1],
# [0,1,0,0,0,1,0,1,1,0],
# [1,0,1,1,0,1,1,1,0,0],
# [1,0,0,1,1,0,0,1,0,1],
# [1,0,0,0,1,0,1,0,0,1],
# [1,1,1,0,0,1,0,1,1,0],
# [0,0,1,1,0,0,0,0,0,1]]

      g = ModuleECC200()
      dmtx_code = g.decode(myMat,False)

      if dmtx_code is not None:
          how = "Rolled My Own"
          is_found = True
      else:
          pass
      out = dmtx_code 
 
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
