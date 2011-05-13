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

      lastCVTime = 0
      timeForCV = 0
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

          if is_found:
             n+=1
             self.output[filename] = out
          else:
             print filename, None
             self.failed.append(filename)
          m+=1

      self.status += "\nFound %d of %d in "%(n,m)

      self.status += str(time()-self.totalTime)+" seconds.\n"
      self.status += "(OpenCV: "+str(timeForCV)+" sec)\n"

      if not(len(self.failed) == 0):# and verbose:
         dirr = ' '+self.myDir
         self.status+= "\nmissing: "+str(self.failed)+'\n'

      return self.output,self.failed,self.status
