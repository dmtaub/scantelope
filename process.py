#!/usr/bin/python
import sys,os, subprocess
from PIL import Image, ImageOps
from pydmtx import DataMatrix
from pdb import set_trace as st
import findcode
import time
dir='/tmp/'
pref='split'
ext='.png'

if __name__ == '__main__':
  do_display = False
  hacked = True
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
          dir,pref = os.path.split(pref)
        ext = '.'+splt[1]
      else:
        files = sys.argv[2:]
        
  dir += '/'
  if files == None:
      files = [i for i in os.listdir(dir) if i.find(pref) != -1 and ''.join(i.split(pref)).rstrip(ext).isdigit()]
      files.sort()
      
  n=0
  m=0


  lastCVTime = 0
  timeForCV = 0
  for filename in files:

      is_found = False    
        
      if filename.find('/') != -1:
        dir,filename = os.path.split(filename)
        dir += '/'

      if hacked:
        is_found = False    
        buf=subprocess.PIPE

        shrink =" -S 1 -e 20 -E 32"
        if filename.find('high') != -1:
          shrink = " -S 2 -e 20 -E 32"


        s= ("-q 10 -t 5 -m 200 -N 1"+shrink+" -s 12x12").split() #" -s 12x12 -e 20 -E 32
  



      lastCVTime = time.time()
      findcode.find(dir,filename,do_display, hacked,verbose)#[3] > 0:
      timeForCV += (time.time() - lastCVTime)
        
      if hacked:
        if not is_found:
          os.system('convert %s -bordercolor black -border 50%% %s'%(dir+"rs"+filename,dir+"rs"+filename))
          i=subprocess.Popen(['dmtxread']+s+['%s'%(dir+"rs"+filename)],stdout=buf)
          out, err = i.communicate()
          is_found = len(out) > 2
          if is_found:
            how = "rotated, cut out, and smoothed"

        if 0:#not is_found:
          os.system('convert %s -bordercolor black -border 50%% %s'%(dir+"q"+filename,dir+"q"+filename))
          i=subprocess.Popen(['dmtxread']+s+['%s'%(dir+"q"+filename)],stdout=buf)
          out, err = i.communicate()
          is_found = len(out) > 2
          if is_found:
            how = "histEq: rotated, cut out, and smoothed"

        if not is_found:
          os.system('convert %s -bordercolor black -border 50%% %s'%(dir+"r"+filename,dir+"r"+filename))
          i=subprocess.Popen(['dmtxread']+s+['%s'%(dir+"r"+filename)],stdout=buf)
          out, err = i.communicate()
          is_found = len(out) > 2
          if is_found:
            how = "rotated and cut out"

        # one might think it better to test original first, but since time spent in CV functions 
        # is negligible, and dmtxread can take some time looking for a barcode in a noisy image, 
        # it ends up being fastest to check the most-processed images first. Have not explored 
        # time of rotated vs original
        
        if not is_found:
          i=subprocess.Popen(['dmtxread']+s+['%s'%(dir+filename)],stdout=buf)
          out, err = i.communicate()
          is_found = len(out) > 2
          if is_found:
            how = "original image"


        if 0:#not is_found:
          i=subprocess.Popen(['dmtxread']+s+['%s'%(dir+"u"+filename)],stdout=buf)
          out, err = i.communicate()
          is_found = len(out) > 2
          if is_found:
            how = "rotated"

        if 0:#not is_found:
          i=subprocess.Popen(['dmtxread']+s+['%s'%(dir+"us"+filename)],stdout=buf)
          out, err = i.communicate()
          is_found = len(out) > 2
          if is_found:
            how = "rotated and smoothed"

        if 0:#not is_found:
          i=subprocess.Popen(['dmtxread']+s+['%s'%(dir+"t"+filename)],stdout=buf)
          out, err = i.communicate()
          is_found = len(out) > 2
          if is_found:
            how = "thresholded"

      if is_found:
        n+=1
        print filename, out, how
      else:
        print filename, None
        failed.append(filename)
      m+=1

        

  print "\nFound %d of %d in "%(n,m),time.time()-totalTime," seconds.",
  print "(OpenCV:",timeForCV," sec)\n"
  
 #if verbose:
  dirr = ' '+dir
  print dirr+dirr.join(failed)
