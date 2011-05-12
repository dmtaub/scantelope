#!/usr/bin/python
# This is a standalone program. Pass an image name as a first parameter of the program.
# has some manual settings for lowres:
low_res = True

from numpy import array, zeros
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
    imports = """cvStartWindowThread()
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
        copy_img = cvCreateImage( cvGetSize(img), img.depth, img.nChannels );
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
                #cvPutText(im , name, cvPoint(0,im.height-5), 
                #        cvFont(1), white) 
                cvNamedWindow( name, 1 )
                cvShowImage( name, im )
                cvMoveWindow( name, offset,cls.yoff)
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

def innerData(rotated, th = 0,verbose=False):

    h=rotated.height
    w=rotated.width
    
    cmprssd_col = cvCreateMat(h,1,CV_32F);
    cmprssd_row = cvCreateMat(1,w,CV_32F);

    # reduce dimensions by summation:

    cvReduce(rotated ,cmprssd_col,1,CV_REDUCE_AVG );
    cvReduce(rotated ,cmprssd_row,0,CV_REDUCE_AVG );

#    thrsh(cmprssd_row)
#    thrsh(cmprssd_col)

    for i in range(w): 
        #print cmprssd_row[0,i]
        if cmprssd_row[0,i] > th:
            break
        
    for j in reversed(range(h)): 
        if cmprssd_col[j,0] > th:
            break
        
    if verbose:
        print i,j
    return i,j

   



def cornerFromImage(rotated, verbose=False):

    size = int(rotated.height / (e-1)) # worked with 37 and 2 / 39x4
    offset = size / 19
    
    cmprssd_col = cvCreateMat(rotated.height,1,CV_32F);
    cmprssd_row = cvCreateMat(1,rotated.width,CV_32F);
    d_cmprssd_col = cvCreateMat(rotated.height,1,CV_32F);
    d_cmprssd_row = cvCreateMat(1,rotated.width,CV_32F);

    # reduce dimensions by summation:

    cvReduce(rotated ,cmprssd_col,1);
    cvReduce(rotated ,cmprssd_row,0);

    row_minmax = cvMinMaxLoc(cmprssd_row)
    col_minmax = cvMinMaxLoc(cmprssd_col)

    if verbose:
        print "cmpr_row:",row_minmax
        print "cmpr_col:",col_minmax

        
    # also get minmax vals of first difference (in,out,xorder,yorder,aperature=3)
    cvSobel(cmprssd_row,d_cmprssd_row,1,0) 
    cvSobel(cmprssd_col,d_cmprssd_col,0,1)

    row_minmax_p = cvMinMaxLoc(d_cmprssd_row)
    col_minmax_p = cvMinMaxLoc(d_cmprssd_col)

    if verbose:
        print "d/cmpr_row:",row_minmax_p
        print "d/cmpr_col:",col_minmax_p

    row = row_minmax[3].x
    col = col_minmax[3].y

    row_p = (row_minmax_p[3].x, row_minmax_p[2].x)
    col_p = (col_minmax_p[3].y, col_minmax_p[2].y)

    #ToDisplay.add("rot",rotated)

    # return all max indices
    # to detect corner of L shape
    return row,col,row_p,col_p


def rectContour(img,do_display):
    img_cpy = cvCreateImage( cvGetSize(img), img.depth, 1 );
    
    storage = cvCreateMemStorage(0);    
   
    if do_display:
        color_img = cvCreateImage( cvGetSize(img), img.depth, 3 );
        cvCvtColor(img,color_img,CV_GRAY2BGR)

        newimg = ToDisplay.add("pre_contour",img)

    cont_thrsh = 60 # 60 good for large img
    cvThreshold(img,img_cpy,cont_thrsh,255,CV_THRESH_BINARY)
    cvDilate(img,img)

    if do_display:
        newimg = ToDisplay.add("thresh"+str(cont_thrsh),img_cpy)
    
    numtours,tours=cvFindContours(img_cpy,storage)

    #cvDrawContours(color_src, tours, (255,0,0), (0,0,255), 20)

    for points in tours.hrange():
        el=cvBoundingRect(points)
        if abs(el.width - el.height) < 3 and el.height > 30:
            print el.x,el.y,el.width,el.height
            
            cvRectangle( color_img, cvPoint(el.x,el.y),cvPoint(el.width,el.height), CV_RGB(0,255,0), 1);

    if do_display:
        newimg = ToDisplay.add("contour",img_cpy)
        newimg = ToDisplay.add("rect",color_img)

def dumbClip(center,size):
    x=center[0]-size/2
    y=center[1]-size/2

    return cvRect(x,y,size,size)

def simpleClip(rotated,verbose,do_display,center,size,off):

        #cvThreshold(rotated,rotated,50,255,CV_THRESH_BINARY)
    x,y,xpair,ypair = cornerFromImage(rotated,verbose)

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

def manual_scan(img,do_display,center, verbose = True):

    def getX(colwise_fft,w3,w4):

        h = colwise_fft.height
        w = colwise_fft.width

        rel_row = colwise_fft[:,w3:w4]
        row_minmax = cvMinMaxLoc(rel_row)    
        xval=row_minmax[3].y
        return xval

    def drawRects(sx,ex,fy,img,dy=2,lt=1):
        startx = cvPoint(sx,fy-dy)
        endx = cvPoint(ex,fy+dy)
        cvRectangle(img,startx,endx,black)

    def getTopleft(xval,yval,center,size,off,verbose):
        #print xval,yval
        topleft = [xval,yval]
        if xval < center[0]:
            if yval > center[1]:
                orientation = "top right"
                angle = 180
                topleft[0]-=off
                topleft[1]-=(size-off)
            else:
                orientation = "bottom right"
                angle = 90
                topleft[0]-=off
                topleft[1]-=off
        else: 
            if yval > center[1]:
                orientation = "top left"
                angle = 90
                topleft[0]-=(size-off)
                topleft[1]-=(size-off)
            else:
                orientation = "bottom left"
                angle = 0
                topleft[0]-=(size-off)
                topleft[1]-=off
        if verbose:
            print orientation
        #print topleft
        return angle,topleft
    
    trans_img = cvCreateImage( cvSize(img.height,img.width), 8, 1 )
    cvTranspose(img,trans_img)

    hi = img.height
    wi = img.width
    
    # works soso on highres
    #w3 = int(wi*.91)
    #w4 = int(wi*.93)
    # works soso on lowres
    w3 = int(wi*.89)
    w4 = w3+1#int(wi*.92)
    
    linewise_fft = getDFT(img,CV_DXT_ROWS,False)
    yval = getX(linewise_fft,w3,w4)

    colwise_fft = getDFT(trans_img,CV_DXT_ROWS,False)
    xval = getX(colwise_fft,w3,w4)
  
    if do_display:
        
        newimg = ToDisplay.add("linewise_fft",linewise_fft)
        drawRects(w3,w4,yval,newimg)

        ToDisplay.add("tranny",trans_img)
 
        newimg = ToDisplay.add("colwise_fft",colwise_fft)
        drawRects(w3,w4,xval,newimg)

    size = img.width*11/20
    off = 2

    angle,topleft=getTopleft(xval,yval,center,size,off,verbose)
    pattern_rect = cvRect(topleft[0],topleft[1],size,size)

    recalc = False
    if 0:
        sr = cvGetSubRect(img,pattern_rect)
        xm,ym = findCenterMoment(sr,verbose)
#        print sr.width, sr.height

        # if values invalid, mask bright regions and try again
        if abs(xm-sr.width/2) > 2:
            if verbose:
                print "invalid x"
            drawRects(w3,w4,xval,colwise_fft,1,-1)
            xval = getX(colwise_fft,w3,w4)
            recalc = True
            if do_display:  
                newimg = ToDisplay.add("colwise_fft2",colwise_fft)
                drawRects(w3,w4,xval,newimg)



        # if values invalid, mask bright regions and try again
        if abs(ym-sr.height/2) > 2:
            if verbose:
                print "invalid y"
            drawRects(w3,w4,yval,linewise_fft,1,-1)
            yval = getX(linewise_fft,w3,w4)
            recalc = True
            if do_display:  
                newimg = ToDisplay.add("linewise_fft2",linewise_fft)
                drawRects(w3,w4,yval,newimg)

    if recalc:  
        angle,topleft=getTopleft(xval,yval,center,size,off,verbose)
        pattern_rect = cvRect(topleft[0],topleft[1],size,size)

    if do_display:
         newimg= ToDisplay.add("trimmed",img)
         cvCircle( newimg, cvPoint(xval,yval), 3, gray, 1 ,8, 0)
         cvCircle( newimg, cvPoint(*topleft), 4, white, 1 ,8, 0)
         cvCircle( newimg, cvPoint(xval+size,yval+size),3 ,white, 1, 8, 0)
        
    return angle,pattern_rect



 

def harrisCenter(img_clip,do_display,cont_thrsh = 60,post_thrsh = 2,har_param = 20): #thrsh 60 good for large

    img = cvCreateImage( cvGetSize(img_clip),img_clip.depth, 1 );
    cvThreshold(img_clip,img,cont_thrsh,255,CV_THRESH_BINARY)
    #cvDilate(rotated_src,rotated_src)

    if do_display:
        newimg = ToDisplay.add("thrsh"+str(cont_thrsh),img)

    har_dst = cvCreateImage( cvGetSize(img), 32, 1);
    cvCornerHarris(img,har_dst,har_param)
    cvScale(har_dst,har_dst,255)

    if post_thrsh != None:
        cvThreshold(har_dst,har_dst,post_thrsh,255*255,CV_THRESH_BINARY)    
        cvErode(har_dst,har_dst,None,10)
    
    if do_display:
        ToDisplay.add("harris",har_dst)
    

    return findCenterMoment(har_dst)

def houghLines(img,color_img):
    storage = cvCreateMemStorage(0);
    x=cvHoughLines2(img,storage,CV_HOUGH_STANDARD,1,CV_PI/180,30,0,0)
    
    v =False
    h =False
    for i in range(x.total):
        rho,theta = x[i][0],x[i][1]
        
        if theta == 0.0:
            if v == True:
                continue
            v = True
        elif abs(theta-1.57) < .07:
            print rho
            if h == True:
                continue
            h = True
        else:
            continue

        print theta
        a = cos(theta);
        b = sin(theta);
        x0 = a*rho
        y0 = b*rho
        if do_display:
            pt1 = cvPoint(cvRound(x0 + 1000*(-b)), cvRound(y0 + 1000*(a)))
            pt2 = cvPoint(cvRound(x0 - 1000*(-b)), cvRound(y0 - 1000*(a)))
            cvLine( color_img, pt1, pt2, CV_RGB(255,0,0), 3, 8 )
            ToDisplay.add("hough color",color_src)

def scanOrientation(img,do_display):
    h=img.height
    w=img.width
    if low_res:
        rsz = 4
    else:
        rsz = 8
    top = cvGetSubRect(img,cvRect(0,0,w,rsz))
    bottom = cvGetSubRect(img,cvRect(0,h-rsz,w,rsz))
    left = cvGetSubRect(img,cvRect(0,0,rsz,h))
    right = cvGetSubRect(img,cvRect(w-rsz,0,rsz,h))
    t=[cvSum(top)[0],0]
    b=[cvSum(bottom)[0],1]
    l=[cvSum(left)[0],2]
    r=[cvSum(right)[0],4]
    
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
    tpl = cvLoadImage(fn,0)
    img_width  = img.width;
    img_height = img.height;
    tpl_width  = tpl.width;
    tpl_height = tpl.height;
    res_width  = img_width - tpl_width + 1;
    res_height = img_height - tpl_height + 1;

    res = cvCreateImage( cvSize( res_width, res_height ), IPL_DEPTH_32F, 1 );
    cvMatchTemplate( img, tpl, res, CV_TM_SQDIFF );
    minval,maxval,minloc,maxloc = cvMinMaxLoc(res)

    if do_display:
        if display_img == None:
            display_img = img
        newimg = ToDisplay.add("squarematch",display_img)
        cvRectangle( newimg,  cvPoint( minloc.x, minloc.y ), 
                 cvPoint( minloc.x + tpl_width, minloc.y + tpl_height ),
                 CV_RGB( 0, 0, 255), 1, 0, 0 )
    return(minloc.x-margin,minloc.y-margin,tpl_width+2*margin,tpl_height+2*margin)

def eqlz(src):
    if src.depth == 8:
        cvEqualizeHist(src,src)
    return src
def smoo(src,dst=None,n=3):
    if dst == None:
        dst = src
    cvSmooth(src,dst,CV_GAUSSIAN,n,n)
    return src
def thrsh(src,v=22):
    cvThreshold(src,src,v,255,CV_THRESH_BINARY)
    return src

def findAndOrient(myDir,filename, do_display = False, hacked = False, verbose = False):
    
    src=cvLoadImage(myDir+filename, 0);
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

    radius = mincirc + 1
    half_thick = src.height / 4
    
    circle_masked = maskOutFromCenter(src,tube_center,radius,half_thick)
    #mom_masked = maskOutFromCenter(src,light_center,radius,half_thick)
#    if do_display:
#        ToDisplay.add("circ",circle_masked)

    #rotated = rotateImage(circle_masked,theta,tube_center)
    rotated_src = rotateImage(src,theta,tube_center)

    if do_display:
        newimg = ToDisplay.add("rot_src",rotated_src)

    #rotated_thrsh = cvCreateImage( cvGetSize(rotated_src), rotated_src.depth, 1 );
    #cont_thrsh = 60 # 60 good for large img
    #cvThreshold(rotated_src,rotated_thrsh,cont_thrsh,255,CV_THRESH_BINARY)
    #cvDilate(rotated_src,rotated_src)

    #if do_display:
    #    newimg = ToDisplay.add("rot_thresh"+str(cont_thrsh),rotated_thrsh)

    #size = int(src.height / (e-1)) # worked w/ 37x2 or 39x4
    #off = size/19    
    #angle, code_region = simpleClip(thrsh(rotated,16),verbose,do_display,tube_center,size,off)

    
    #exec interactive('plot3d(rotated2)')
    
    color_src = cvCreateImage( cvGetSize(rotated_src), rotated_src.depth, 3 );
    cvCvtColor(rotated_src,color_src,CV_GRAY2BGR)

    if low_res:
        template_fn = "template2b.png"
    else:
        template_fn = "template2b_large.png"
    code_region = templateMatch(rotated_src,do_display,template_fn )
    rotated2 = cvGetSubRect(rotated_src,code_region)

    angle = scanOrientation(rotated2,do_display)
    
    new_center = (rotated2.width/2,rotated2.height/2)
    rotated2 = rotateImage(rotated2,angle,new_center)

    if do_display:
        ToDisplay.add("color",color_src)

    if verbose:
        print orientation

    if hacked:
        cvSaveImage(myDir+"r"+filename,rotated2)
        cvSmooth(rotated2,rotated2, CV_GAUSSIAN, 3, 3)
        cvSaveImage(myDir+"rs"+filename,rotated2)
#    else:
#        cvSmooth(rotated2,rotated2, CV_GAUSSIAN, 3, 3)


    if do_display:
        newimg = ToDisplay.add("final",rotated2)
    
    if do_display:
        ToDisplay.showIm()
    return rotated2


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
 
def matrixFromImage(img,do_display,verbose):
   
    if do_display:
        ToDisplay.clear()
        
    img_cpy = cvCreateImage( cvGetSize(img), img.depth, img.nChannels );
    #img_smoo = cvCreateImage( cvGetSize(img), img.depth, img.nChannels );
    cont_thrsh = 60 # 60 good for large img
    cvThreshold(img,img_cpy,cont_thrsh,255,CV_THRESH_BINARY)
    #smoo(img,img_smoo)
    #thrsh(img_smoo,50)

    if do_display:
        newimg = ToDisplay.add("first",img)
        #newimg = ToDisplay.add("second",img_cpy)
        #newimg = ToDisplay.add("third",img_smoo )


    x,y = innerData(img_cpy,200,verbose)

    if low_res:
        sub = cvGetSubRect(img,cvRect(x+2 ,max(0, y-31 ),30,30  ))
    else:
        sub = cvGetSubRect(img,cvRect(x+4 ,max(0, y-63 ),59,   59   ))
    if 1:
        h=sub.height
        w=sub.width

        #smoo(sub)
        if do_display:
          newimg = ToDisplay.add("second",sub)


        dwn = cvCreateImage( cvSize(10,10), img.depth, img.nChannels )
        cvResize(sub,dwn,CV_INTER_AREA)
        thrsh(dwn,50 )

        retmat =  zeros(100)
        #exec interactive()
        idata = dwn.imageData
        for i in range(len(idata)):
            retmat[i] = ord(idata[i])
        retmat.resize(10,10)
        #for i in 
        if do_display:
          newimg = ToDisplay.add("third",dwn)
#    else:
#        pass

    if do_display:
        ToDisplay.showIm()

    return retmat