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
#    but WITHOUT ANY WARRANTY; without even th:e implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
'search and decode' module for Scantelope.
  This works as a standalone program. 
 Pass an image file name as a first parameter of the program.
"""
# has some manual settings for lowres:
low_res = True

from numpy import array, zeros, arange
import sys,os
from math import sin,cos,sqrt, atan, degrees,e
import cv

from dft import getDFT
import pydmtx
from pdb import set_trace as st

white = cv.CV_RGB(255,255,255)
black = cv.CV_RGB(0,0,0)
gray = cv.CV_RGB(126,126,126)

# to use plotting for a given image, do this anywhere where there's an image: 
#     exec interactive('plot3d(rotated2)')
def plot3d(r):
    from matplotlib.pyplot import figure
    from pylab import meshgrid,ravel
    import mpl_toolkits.mplot3d.axes3d as p3
    ax=p3.Axes3D(figure())
    X=range(r.width)
    Y=range(r.height)
    x,y=meshgrid(X,Y)
    z=array(r[:,:])
    ax.plot_wireframe(*(x,y,z))

#figure()
#rh = rotated.height-1
#for i in range(rotated.height):
#  a=array(rotated[rh-i,:])
#  plot(i+a.transpose(),'k')

def interactive(cust=""):
    imports = """cv.StartWindowThread()
from IPython.Shell import IPShellEmbed
ipshell = IPShellEmbed()
ipshell.IP.runlines('from pylab import ion; ion()')

ToDisplay.showIm()
"""
    return compile(imports+"\n"+cust+"\nipshell()" , '<IPlot>', 'exec')
# run as: exec interactive()

class ToDisplay:
    """ class to store and display 8bit 1 channel images """
    imgs = {}
    names = []
    def __init__(self,yoffset):
        pass
    
    @classmethod
    def clear(cls,yoff = 0):
        cls.names = []
        cls.imgs = {} #free mem?
        cls.yoff = yoff
    @classmethod
    def add(cls,name,img,apply_to_copy = None):
        cls.names.append(name)

        if 'depth' not in dir(img):
            depth = 8
        else:
            depth = img.depth

        
        if 'nChannels' not in dir(img):
            nch = 1
        else:
            nch = img.nChannels

        copy_img = cv.CreateImage( cv.GetSize(img), depth, nch );
        cv.Copy(img,copy_img)
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
                #cv.PutText(im , name, cv.Point(0,im.height-5), 
                #        cv.Font(1), white) 
                cv.NamedWindow( name, 1 )
                cv.ShowImage( name, im )
                cv.MoveWindow( name, offset,cls.yoff)
                offset+=step

        key = chr(cv.WaitKey(1000)% 0x100)
        
        if key == ' ':  #pause on spacebar
            key = chr(cv.WaitKey(0) % 0x100)
        if key == '\n':
            sys.exit(0)

       
def getAngle(dft_img, do_display = False,verbose = False):
        # create 8-bit image from DFT output
        scale_dst = cv.CreateImage( cv.GetSize(dft_img), 8, 1 );
        cv.CvtScale( dft_img, scale_dst, 255);
        
        # create mask for 2d fft to select only in the scale we care about
        mask = cv.CreateImage( cv.GetSize(dft_img), 8, 1);
        cv.Zero(mask);

        center = (scale_dst.width/2,scale_dst.height/2)
        
        # thick = 7 rad = 25 in original
        maxr = (dft_img.height)/2
        thickness = maxr/4
        radius = maxr - thickness

        if verbose:
            print "dft mask r=",radius," width=",thickness

        cv.Circle( mask, center, radius, cv.CV_RGB(255,255,255), thickness, 8, 0);
        
        # smooth fft image and find maximum value in masked region
        cv.Smooth(scale_dst,scale_dst, cv.CV_GAUSSIAN, 5, 5)
        minmax=cv.MinMaxLoc(scale_dst,mask);
        myMax = minmax[3];

        #calculate angle of rotation
        try:
            theta = atan(float(myMax[1]-center[1])/float(myMax[0]-center[0]))
        # would be more compatible to test for zero in denom
        except ZeroDivisionError: 
            theta = 0

        if verbose:
            print "detected angle=",theta

        # calculate and display maximum 
        if do_display:
            h=sqrt(myMax[0]**2+myMax[1]**2)
            myX = int(cos(theta)*h);
            myY = int(sin(theta)*h);        
            newimg=ToDisplay.add("DFT",dft_img)
            cv.Circle( newimg, myMax, 4, gray, 1, 8, 0);

        return degrees(theta)

def rotateImage(src,theta,center=None):
    # create rotated image
    #src = tmp
    if center == None:
        center = (src.width/2,src.height/2)
    rotated = cv.CreateImage( cv.GetSize(src), 8, 1 );
    rot_mat = cv.CreateMat(2, 3, cv.CV_32FC1)

    cv.GetRotationMatrix2D(center,theta,1.0,rot_mat)
    cv.WarpAffine(src,rotated,rot_mat)
    return rotated

def findCenterMoment(src,verbose=False):
    # find test tube circle to determine what 'center' is
    aa=array(src[:,:])
    rowise_mean = aa.mean(1)
    colwise_mean = aa.mean(0)

 #   print src.width, len(colwise_mean)
 #   print src.height, len(rowise_mean)
    xr =arange(src.width)
    yr = arange(src.height)
    xw = colwise_mean * xr
    yw = rowise_mean * yr

    xbar = xw.sum()/colwise_mean.sum()
    ybar = yw.sum()/rowise_mean.sum()

    
    center = (int(round(xbar)),int(round(ybar)))
    
    if verbose:
        print "momCenter=",center
    return center

def maskOutFromCenter(src,center,radius,half_lw):
    masked = cv.CreateImage( cv.GetSize(src), 8, 1 );        
    cv.Copy(src,masked)        

    # mask out everything outside a radius around center point
    cv.Circle(masked ,center, radius+half_lw, black, half_lw+half_lw,16, 0)

    return masked

def scanOrientation(img,do_display):
    h=img.height
    w=img.width
    if low_res:
        rsz = 4
    else:
        rsz = 8
    top = cv.GetSubRect(img,(0,0,w,rsz))
    bottom = cv.GetSubRect(img,(0,h-rsz,w,rsz))
    left = cv.GetSubRect(img,(0,0,rsz,h))
    right = cv.GetSubRect(img,(w-rsz,0,rsz,h))
    t=[cv.Sum(top)[0],0]
    b=[cv.Sum(bottom)[0],1]
    l=[cv.Sum(left)[0],2]
    r=[cv.Sum(right)[0],4]
    
    s=[t,b,l,r]

    m1=max(s)
    s.remove(m1)
    m2=max(s)

    d=m1[1]+m2[1]

    if d == 2:
        angle=90
    elif d == 4:
        angle = 180
    elif d == 3:
        angle = 0
    else:#if d == 5:
        angle = -90

#    ToDisplay.add('img',img)
#    exec interactive('ToDisplay.showIm()')
    return angle

def templateMatch(img,do_display,fn = "template3.png", margin = 0,display_img = None):
    tpl = cv.LoadImage(fn,0)
    img_width  = img.width;
    img_height = img.height;
    tpl_width  = tpl.width;
    tpl_height = tpl.height;
    res_width  = img_width - tpl_width + 1;
    res_height = img_height - tpl_height + 1;

    res = cv.CreateImage( ( res_width, res_height ), cv.IPL_DEPTH_32F, 1 );
    cv.MatchTemplate( img, tpl, res, cv.CV_TM_SQDIFF );
    minval,maxval,minloc,maxloc = cv.MinMaxLoc(res)

    if do_display:
        
        if display_img == None:
            display_img = img
        newimg = ToDisplay.add("squarematch",display_img)
        cv.Rectangle( newimg,  minloc, 
                  ( minloc[0] + tpl_width, minloc[1] + tpl_height ),
                 cv.CV_RGB( 0, 0, 255), 1, 0, 0 )
    return(minloc[0]-margin,minloc[1]-margin,tpl_width+2*margin,tpl_height+2*margin)

def eqlz(src):
    if src.depth == 8:
        cv.EqualizeHist(src,src)
    return src
def smoo(src,dst=None,n=3):
    if dst == None:
        dst = src
    cv.Smooth(src,dst,cv.CV_GAUSSIAN,n,n)
    return src
def thrsh(src,v=22):
    cv.Threshold(src,src,v,255,cv.CV_THRESH_BINARY)
    return src

def findAndOrient(myDir,filename, do_display = False, verbose = False):
    
    src=cv.LoadImage(myDir+filename, 0);
    if do_display:
        ToDisplay.clear(100)
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
    #tube_center = harrisCenter(src,do_display)

    radius = mincirc + 1
    half_thick = src.height / 4
    
    circle_masked = maskOutFromCenter(src,tube_center,radius,half_thick)
    
    #rotated = rotateImage(circle_masked,theta,tube_center)
    rotated_src = rotateImage(src,theta,tube_center)

    if do_display:
        newimg = ToDisplay.add("rot_src",rotated_src)

    color_src = cv.CreateImage( cv.GetSize(rotated_src), rotated_src.depth, 3 );
    cv.CvtColor(rotated_src,color_src,cv.CV_GRAY2BGR)

    if low_res:
        template_fn = "template2b.png"
    else:
        template_fn = "template2b_large.png"
    code_region = templateMatch(rotated_src,do_display,template_fn )
    rotated2 = cv.GetSubRect(rotated_src,code_region)

    angle = scanOrientation(rotated2,do_display)
    
    new_center = (rotated2.width/2,rotated2.height/2)
    rotated2 = rotateImage(rotated2,angle,new_center)

    smoothed = cv.CreateImage( cv.GetSize(rotated2), rotated2.depth, 1 );
    smoo(rotated2,smoothed) 

    if do_display:
        ToDisplay.add("color",color_src)

    if do_display:
        newimg = ToDisplay.add("final",rotated2)
    
    if do_display:
        ToDisplay.showIm()

    return src,smoothed,rotated2

if __name__ == "__main__":
    filename = "split0.png"
    if len(sys.argv)>1:
        for f in sys.argv[1:]:
            if f.find('/') != -1:
                myDir,fn = os.path.split(f)
                output = findAndOrient(myDir+"/",fn, do_display = True)
            else:
                output = findAndOrient("/tmp/",f, do_display = True)   
    else:
        output = findAndOrient("/tmp/",filename, do_display = True)
