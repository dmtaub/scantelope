#!/usr/bin/python
# This is a standalone program. Pass an image name as a first parameter of the program.

from numpy import array
import sys,os
from math import sin,cos,sqrt, atan, degrees,e
#import cv
from opencv.cv import *
from opencv.highgui import *
from dft import getDFT
import pydmtx
from pdb import set_trace as st

white = CV_RGB(255,255,255)
black = CV_RGB(0,0,0)
gray = CV_RGB(126,126,126)

class ToDisplay:
    """ class to store and display 8bit 1 channel images """
    imgs = {}
    names = []
    def __init__(self):
        pass
    
    @classmethod
    def clear(cls):
        cls.names = []
        cls.imgs = {} #free mem?

    @classmethod
    def add(cls,name,img,apply_to_copy = None):
        cls.names.append(name)
        copy_img = cvCreateImage( cvGetSize(img), img.depth, 1 );
        cvCopy(img,copy_img)
        if apply_to_copy != None:
            copy_img = apply_to_copy(copy_img)
        cls.imgs[name] = copy_img
        return copy_img

    @classmethod
    def showIm(cls):
        offset = 0

#        for name,im in cls.imgs.iteritems():
        for name in cls.names:  #preserve order of dict in python 2.6
                im = cls.imgs[name]
                width = im.width
                step = width +2
                cvPutText(im , name, cvPoint(0,im.height-5), 
                        cvFont(1), white) 
                cvNamedWindow( name, 1 )
                cvShowImage( name, im )
                cvMoveWindow( name, offset,0)
                offset+=step

        key = cvWaitKey(1000)
        if key == ' ':  #pause on spacebar
            key = cvWaitKey(0)
        if key == '\n':
            sys.exit(0)

       
def getAngle(dft_img, do_display = False,verbose = False):
        # create 8-bit image from DFT output
        scale_dst = cvCreateImage( cvGetSize(dft_img), 8, 1 );
        cvCvtScale( dft_img, scale_dst, 255);
        
        # create mask for 2d fft to select only in the scale we care about
        mask = cvCreateImage( cvGetSize(dft_img), 8, 1);
        cvZero(mask);

        center = (scale_dst.width/2,scale_dst.height/2)
        
        # thick = 7 rad = 25 in original
        maxr = (dft_img.height)/2
        thickness = maxr/4
        radius = maxr - thickness

        if verbose:
            print "dft mask r=",radius," width=",thickness

        cvCircle( mask, cvPoint(*center), radius, CV_RGB(255,255,255), thickness, 8, 0);
        
        # smooth fft image and find maximum value in masked region
        cvSmooth(scale_dst,scale_dst, CV_GAUSSIAN, 5, 5)
        minmax=cvMinMaxLoc(scale_dst,mask);
        myMax = minmax[3];

        #calculate angle of rotation
        try:
            theta = atan(float(myMax.y-center[1])/float(myMax.x-center[0]))
        # would be more compatible to test for zero in denom
        except ZeroDivisionError: 
            theta = 0

        if verbose:
            print "detected angle=",theta

        # calculate and display maximum 
        if do_display:
            h=sqrt(myMax.x**2+myMax.y**2)
            myX = int(cos(theta)*h);
            myY = int(sin(theta)*h);        
            newimg=ToDisplay.add("DFT",dft_img)
            cvCircle( newimg, myMax, 4, gray, 1, 8, 0);

        return degrees(theta)

def rotateImage(src,theta,center=None):
    # create rotated image
    #src = tmp
    if center == None:
        center = (src.width/2,src.height/2)
    rotated = cvCreateImage( cvGetSize(src), 8, 1 );
    rot_mat = cvCreateMat(2, 3, cv.CV_32FC1)

    cv2DRotationMatrix(center,theta,1.0,rot_mat)
    cvWarpAffine(src,rotated,rot_mat)
    return rotated

def findCenterMoment(src,verbose=False):
    # find test tube circle to determine what 'center' is
    # Use cvMoments 

    c=CvMoments()
    m=cvMoments(src,c)
    xbar=int(round(c.m10/c.m00))
    ybar=int(round(c.m01/c.m00))
    center = (xbar,ybar)
    if verbose:
        print "momCenter=",center
    return center

def findCenterCircles(src,mincirc,maxcirc,verbose=False):
    storage = cvCreateMemStorage(0);

    circles =  cv.cvHoughCircles( src, storage, CV_HOUGH_GRADIENT, 
                                  1, 100, 20, 20,mincirc,maxcirc );

    if verbose:
        print "mincirc =",mincirc,"maxcirc =",maxcirc
        print "found",circles.total,"circle(s)"

    for i in range(circles.total):
        center = (int(round(circles[i][0])), int(round(circles[i][1])))
        if verbose:
            print "circCenter= ",center

    return tuple(center)

            
def maskOutFromCenter(src,center,radius,half_lw):
    masked = cvCreateImage( cvGetSize(src), 8, 1 );        
    cvCopy(src,masked)        
        # mask out everything outside a radius around center point
    cvCircle(masked ,center, radius+half_lw, black, half_lw+half_lw,16, 0)
        #dst = masked_r       
#            cvEqualizeHist(masked_r,masked_r)
    return masked

def getTopLeft(rotated, verbose=False):

    size = int(rotated.height / (e-1)) # worked with 37 and 2 / 39x4
    offset = size / 19
    
    cmprssd_col = cvCreateMat(rotated.height,1,CV_32F);
    cmprssd_row = cvCreateMat(1,rotated.width,CV_32F);

    # reduce dimensions by summation:

    cvReduce(rotated ,cmprssd_col,1);
    cvReduce(rotated ,cmprssd_row,0);

    row_minmax = cvMinMaxLoc(cmprssd_row)
    col_minmax = cvMinMaxLoc(cmprssd_col)

    if verbose:
        print "cmpr_row:",row_minmax
        print "cmpr_col:",col_minmax

        
    # also get minmax vals of first difference (in,out,xorder,yorder,aperature=3)
    cvSobel(cmprssd_row,cmprssd_row,1,0) 
    cvSobel(cmprssd_col,cmprssd_col,0,1)

    row_minmax_p = cvMinMaxLoc(cmprssd_row)
    col_minmax_p = cvMinMaxLoc(cmprssd_col)

    if verbose:
        print "d/cmpr_row:",row_minmax_p
        print "d/cmpr_col:",col_minmax_p

    row = row_minmax[3].x
    col = col_minmax[3].y

    row_p = (row_minmax_p[3].x, row_minmax_p[2].x)
    col_p = (col_minmax_p[3].y, col_minmax_p[2].y)
    
    # return all max indices
    # to detect corner of L shape
    return row,col,row_p,col_p

def dumbClip(rotated,verbose,do_display,center,size,off):

        #cvThreshold(rotated,rotated,50,255,CV_THRESH_BINARY)
    x,y,xpair,ypair = getTopLeft(rotated,verbose)

    # this is a pretty dumb way to find the corner. 
    # doesnt work for (e.g twistlow34)
    maxx=max(x,max(xpair))
    maxy=max(y,max(ypair))
#    print y,ypair
#    print "center=",center
    
    if verbose:
        print "size,offset=",(size,off)
        #print "center=",center
        #print "x,y   =",(maxx,maxy)
    #size = maxcirc


    topleft = [maxx,maxy]
    if maxx < center[0]:
        if maxy > center[1]:
            orientation = "bottom left"
            angle = 0
            topleft[1]-=size
        else:
            orientation = "top left"
            angle = 90
            topleft[1]-=off
            topleft[0]-=off
    else: 
        if maxy > center[1]:
            orientation = "bottom right"
            angle = -90
            topleft[1]-=(size-off)
            topleft[0]-=(size-off)
        else:
            orientation = "top right"
            angle = 180
            topleft[0]-=(size-off)
            topleft[1]-=off
    #print orientation

    if do_display:
        newimg = ToDisplay.add("cleaned",rotated)

        cvCircle( newimg, cvPoint(maxx,maxy), 3, gray, 1 ,8, 0)
        cvCircle( newimg, cvPoint(*topleft), 3, white, 1 ,8, 0)

    return angle,cvRect(topleft[0],topleft[1],size,size)
#    new_center = squareCut(rotated,circ_center,size)

def eqlz(src):
    if src.depth == 8:
        cvEqualizeHist(src,src)
    return src
def smoo(src,n=3):
    cvSmooth(src,src,CV_GAUSSIAN,n,n)
    return src
def thrsh(src,v=22):
    cvThreshold(src,src,v,255,CV_THRESH_BINARY)
    return src

def find(myDir,filename, do_display = False, hacked = False, verbose = False):
    
    src=cvLoadImage(myDir+filename, 0);
    if do_display:
        ToDisplay.clear()
        ToDisplay.add("input",src)

    if verbose:
        print "Opening image %s" % filename
    if not src:
        print "Error opening image %s" % myDir+filename
        sys.exit(-1)

    dst = getDFT(src)

    theta = getAngle(dst,do_display,verbose)

    maxcirc = (src.height + 1) /2 +2
    mincirc = int((src.height + 1) / e)

    #tube_center = findCenterCircles(src,mincirc,maxcirc,verbose)
    tube_center = findCenterMoment(src,verbose)

    radius = mincirc + 1
    half_thick = src.height / 4
    
    circle_masked = maskOutFromCenter(src,tube_center,radius,half_thick)
    #mom_masked = maskOutFromCenter(src,light_center,radius,half_thick)
#    if do_display:
#        ToDisplay.add("circ",circle_masked)
    
    rotated = rotateImage(circle_masked,theta,tube_center)

    rotated_src = rotateImage(src,theta,tube_center)

    size = int(src.height / (e-1)) # worked with 37 and 2 / 39x4
    off = size/19

    angle, code_region = dumbClip(thrsh(rotated,16),verbose,do_display,tube_center,size,off)
    rotated2 = cvGetSubRect(rotated_src,code_region)
    new_center = (rotated2.width/2,rotated2.height/2)
    rotated2 = rotateImage(rotated2,angle,new_center)

    if do_display:
        newimg = ToDisplay.add("final",rotated2)

    if verbose:
        print orientation

    if hacked:
        cvSaveImage(myDir+"r"+filename,rotated2)
        cvSmooth(rotated2,rotated2, CV_GAUSSIAN, 3, 3)
        cvSaveImage(myDir+"rs"+filename,rotated2)
#        eqlz(rotated2)
#        cvSaveImage(myDir+"q"+filename,rotated2)

#        cvSaveImage(myDir+"t"+filename,masked_r)
#        cvSaveImage(myDir+"u"+filename,rotated)
#        cvSmooth(rotated,rotated, CV_GAUSSIAN, 3, 3)
#        cvSaveImage(myDir+"us"+filename,rotated)

    if do_display:
        ToDisplay.showIm()
    return rotated


if __name__ == "__main__":
    filename = "split0.png"
    if len(sys.argv)>1:
        for f in sys.argv[1:]:
            if f.find('/') != -1:
                myDir,fn = os.path.split(f)
                output = find(myDir+"/",fn, do_display = True)
            else:
                output = find("/tmp/",f, do_display = True)   
    else:
        output = find("/tmp/",filename, do_display = True)
