#!/usr/bin/python
# This is a standalone program. Pass an image name as a first parameter of the program.

from numpy import array
import sys,os
from math import sin,cos,sqrt, atan, degrees,e
#import cv
from opencv.cv import *
from opencv.highgui import *
from dft import cvShiftDFT
import pydmtx
from pdb import set_trace as st

def showlines(src,dst,color_dst, show_src = False, show_dst = True, show_color_dst = True):   
    width = max([(src and src.width), (dst and dst.width),(color_dst and color_dst.width)])
    step = width +2
    offset = 0
    if show_src == True:
        cvNamedWindow( "Source", 1 );
        cvShowImage( "Source", src );
        cvMoveWindow("Source",offset,0);
        offset+=step;
    if show_dst == True:
        cvNamedWindow( "Thresh", 1 );
        cvShowImage( "Thresh", dst );
        cvMoveWindow("Thresh",offset,0);
        offset+=step;
    if show_color_dst == True:
        cvNamedWindow( "Blob", 1 );
        cvShowImage( "Blob", color_dst );
        cvMoveWindow("Blob",offset,0);
        offset+=step;

    cvWaitKey(0);

def getDFT(im):

    im_sz = cvGetSize(im)
    
    realInput = cvCreateImage( im_sz, IPL_DEPTH_64F, 1)
    imaginaryInput = cvCreateImage( im_sz, IPL_DEPTH_64F, 1)
    complexInput = cvCreateImage( im_sz, IPL_DEPTH_64F, 2)
    cvZero(realInput)

    cvScale(im, realInput, 1.0, 0.0)
    cvZero(imaginaryInput)
    cvMerge(realInput, imaginaryInput, None, None, complexInput)

    dft_M = cvGetOptimalDFTSize( im_sz.height - 1 )
    dft_N = cvGetOptimalDFTSize( im_sz.width - 1 )
    
    dft_A = cvCreateMat( dft_M, dft_N, CV_64FC2 )
    image_Re = cvCreateImage( cvSize(dft_N, dft_M), IPL_DEPTH_64F, 1)
    image_Im = cvCreateImage( cvSize(dft_N, dft_M), IPL_DEPTH_64F, 1)

    # copy A to dft_A and pad dft_A with zeros
    #st()
    tmp = cvGetSubRect( dft_A, cvRect(0,0, im.width, im.height))
    cvCopy( complexInput, tmp, None )
    if(dft_A.width > im.width):
        tmp = cvGetSubRect( dft_A, cvRect(im.width,0, dft_N - im.width, im.height))
        cvZero( tmp )

    # no need to pad bottom part of dft_A with zeros because of
    # use nonzero_rows parameter in cvDFT() call below

    cvDFT( dft_A, dft_A, CV_DXT_FORWARD, complexInput.height )


    # Split Fourier in real and imaginary parts
    cvSplit( dft_A, image_Re, image_Im, None, None )

    # Compute the magnitude of the spectrum Mag = sqrt(Re^2 + Im^2)
    cvPow( image_Re, image_Re, 2.0)
    cvPow( image_Im, image_Im, 2.0)
    cvAdd( image_Re, image_Im, image_Re, None)
    cvPow( image_Re, image_Re, 0.5 )

    # Compute log(1 + Mag)
    cvAddS( image_Re, cvScalarAll(1.0), image_Re, None ) # 1 + Mag
    cvLog( image_Re, image_Re ) # log(1 + Mag)



    # Rearrange the quadrants of Fourier image so that the origin is at
    # the image center
    cvShiftDFT( image_Re, image_Re )

    min, max, pt1, pt2 = cvMinMaxLoc(image_Re)
    cvScale(image_Re, image_Re, 1.0/(max-min), 1.0*(-min)/(max-min))


    return image_Re

def match_templates(img):
    
    tpl1=cvLoadImage("template4a.png", 0);
    tpl2=cvLoadImage("template4b.png", 0);

    #print "Opening image %s" % filename
    if not tpl1:
        print "Error opening template 4a"
        sys.exit(-1)
    if not tpl1:
        print "Error opening template 4b"
        sys.exit(-1)

    
    templates = [tpl1, tpl2]
    
    numtemplates = len(templates)
    output = [[]]*numtemplates

    for i in range(numtemplates):
        tpl = templates[i]
        res_width = img.width - tpl.width + 1
        res_height = img.height - tpl.height + 1
        
        res = cvCreateImage( cvSize( res_width, res_height ), IPL_DEPTH_32F, 1 )
        
        cvMatchTemplate( img, tpl, res, CV_TM_SQDIFF )
        minval,nmaxval,minloc,nmaxloc = cvMinMaxLoc(res)
#        output[i] = [minloc.x,minloc.y]

        if i == 0:
            code_region = cvRect(minloc.x,minloc.y-2,4,4)
        if i == 1:
            code_region = cvRect(minloc.x+1,minloc.y,4,4)
        corner = cvGetSubRect(img,code_region)
        cvSmooth(corner,corner)
        nminval,maxval,nminloc,maxloc = cvMinMaxLoc(corner)
        output[i] = [code_region.x + maxloc.x, code_region.y + maxloc.y]

    return output

def find(dir,filename, do_display = False, hacked = False):
    
    src=cvLoadImage(dir+filename, 0);
    

    #print "Opening image %s" % filename
    if not src:
        print "Error opening image %s" % dir+filename
        sys.exit(-1)

    storage = cvCreateMemStorage(0);
    lines = 0;
    numLines = 0
    #sz = min(src.width*2,src.height*2)
    #big_src = cvCreateImage( cvSize(sz,sz), 8, 1 )
    #cvZero(big_src)
    #bsr=cvGetSubRect(big_src,cvRect(big_src.width / 4, big_src.height /4,
    #                            src.width, src.height))
    #cvCopy(src,bsr)
    #tmp =src
    #src = big_src
    #dst = getDFT(big_src)
    dst = getDFT(src)
    do_label = True

    if do_label:
        scale_dst = cvCreateImage( cvGetSize(dst), 8, 1 );

        center = (scale_dst.width/2,scale_dst.height/2)
        
        cvCvtScale( dst, scale_dst, 255);
        
        # create mask for 2d fft to select only in the scale we care about
        mask = cvCreateImage( cvGetSize(dst), 8, 1);
        cvZero(mask);
        
        # thick = 7 rad = 25 in original
        maxr = (dst.height)/2
        thickness = maxr/4
        radius = maxr - thickness
        #print radius,thickness
        cvCircle( mask, cvPoint(*center), radius, CV_RGB(255,255,255), thickness, 8, 0);
        
        # smooth fft image and find maximum value in masked region
        cvSmooth(scale_dst,scale_dst, CV_GAUSSIAN, 5, 5)
        minmax=cvMinMaxLoc(scale_dst,mask);
        myMax = minmax[3];
        
        try:
        #calculate angle of rotation
            theta = atan(float(myMax.y-center[1])/float(myMax.x-center[0]))#float(myMax)/float(compressed.height)*360;
        except ZeroDivisionError: # would be more compatible to test for zero in denom
            theta = 0
        # calculate and display maximum 
        if do_display:
            h=sqrt(myMax.x**2+myMax.y**2)
            myX = int(cos(theta)*h);
            myY = int(sin(theta)*h);        
            cvCircle( dst, myMax, 4, CV_RGB(255,0,0), 1, 8, 0);
        
        # create rotated image
        #src = tmp
        rotated = cvCreateImage( cvGetSize(src), 8, 1 );
        rot_mat = cvCreateMat(2, 3, cv.CV_32FC1)
        center = (src.width/2,src.height/2)
        cv2DRotationMatrix(center,degrees(theta),1.0,rot_mat)
        cvWarpAffine(src,rotated,rot_mat)
        
        # find test tube circle to determine what 'center' is for orientation detection
        #
        # Use cvMoments instead?
        # c=CvMoments()
        # m=cvMoments(rotated,c)
        # xbar=int(round(c.m10/c.m00))
        # ybar=int(round(c.m01/c.m00))
        #
        masked_r = cvCreateImage( cvGetSize(rotated), 8, 1 );
        cvCopy(rotated,masked_r)
        
        maxcirc = (src.height + 1) /2 +2
        mincirc = int((src.height + 1) / e)
        useradius= mincirc #- 1 
        #st()
        
        circles =  cv.cvHoughCircles( masked_r, storage, CV_HOUGH_GRADIENT, 1, 100, 20, 20,mincirc,maxcirc );
        
        cvEqualizeHist(rotated,masked_r)
        
        for i in range(circles.total):
            #st()
            cc = cvPoint(cvRound(circles[i][0]), cvRound(circles[i][1]));
            rad = cvRound(circles[i][2])
            half_lw = src.height / 4
            # mask out everything outside the detected circle
            cvCircle( masked_r, cc, useradius+half_lw, CV_RGB(0,0,0), half_lw+half_lw,16, 0)
        #dst = masked_r
        
        if circles.total:
            # create binary image
            #cvThreshold(masked_r,masked_r,220,255,CV_THRESH_BINARY)
        
            cmprssd_row = cvCreateMat(rotated.height,1,CV_32F);
            cmprssd_col = cvCreateMat(1,rotated.width,CV_32F);

            # reduce dimensions by averaging, and use maximum vals of first difference to detect corner of L shape
            cvReduce(masked_r,cmprssd_row,1);
            row = cvMinMaxLoc(cmprssd_row)[3].y
            cvSobel(cmprssd_row,cmprssd_row,0,1)
            #row_d = cvMinMaxLoc(cmprssd_row)[3].y

            cvReduce(masked_r,cmprssd_col,0);
            col = cvMinMaxLoc(cmprssd_col)[3].x
            cvSobel(cmprssd_col,cmprssd_col,1,0)
            #col_d = cvMinMaxLoc(cmprssd_col)[3].x

            
            size = int(src.height / (e-1)) # worked with 37 and 2 / 39x4
            off = size / 19
            #st()

            #print row, col, cc.y,cc.x, center
            # this should be invarient to position of L
            topleft = [None,None]
            if row < cc.y:
                y_inc = size
                yoff = -off
                row = cvMinMaxLoc(cmprssd_row)[3].y
                topleft[1] = row
            else:
                y_inc = -size
                yoff = off
                row = cvMinMaxLoc(cmprssd_row)[2].y
                topleft[1] = row + y_inc + yoff
            if col < cc.x:
                x_inc = size
                xoff = -off
                col = cvMinMaxLoc(cmprssd_col)[3].x
                topleft[0] = col
            else:
                x_inc = -size
                xoff = off
                col = cvMinMaxLoc(cmprssd_col)[2].x
                topleft[0] = col + x_inc + xoff
                

            h=rotated.height
            w=rotated.width
            #print topleft, row, cc.y
            # get 3 corners
            
            
            #cvEqualizeHist(rotated,rotated)
            #(topright,bottomleft) = match_templates(rotated)


            #print topright[0] -topleft[0]
            #print bottomleft[1] - topleft[1]
            #print "topleft",topleft
            #print "topright",topright
            #print "bottomleft",bottomleft
            #print 
            # display corners

            if not hacked and do_display:
                cvCircle( rotated, cvPoint(row,col)
                          , 3, CV_RGB(155,155,155), 1 ,8, 0)
                #cvCircle( rotated, cvPoint(topleft[0],topleft[1])
                #          , 3, CV_RGB(225,225,225), 1 ,8, 0)
                
                #cvCircle( rotated, cvPoint(bottomleft[0],bottomleft[1])
                #          , 3, CV_RGB(255,255,255), 1 ,8, 0)
                #cvCircle( rotated, cvPoint(topleft[0],topleft[1])
                #          , 3, CV_RGB(255,255,255), 1 ,8, 0)
        
        # snip out estimated data matrix
            
            code_region = cvRect(topleft[0],topleft[1],size,size)
#         code_region = cvRect(topright[0],topright[1]-2,4,8)
            #print topleft,size,(rotated.height,rotated.width)
            rotated = cvGetSubRect(rotated,code_region)

            if hacked:
                cvSaveImage(dir+"r"+filename,rotated)
                cvSmooth(rotated,rotated, CV_GAUSSIAN, 3, 3)
                #cvEqualizeHist(rotated,rotated)
                cvSaveImage(dir+"rs"+filename,rotated)
            
        else:
            cvEqualizeHist(rotated,rotated)
            rotated=masked_r
            print 'could not find any circles',
        if hacked:
            cvSaveImage(dir+"u"+filename,rotated)
            cvSmooth(rotated,rotated, CV_GAUSSIAN, 3, 3)
            cvSaveImage(dir+"us"+filename,rotated)

        
#         n = 10
#         big = cvCreateImage(cvSize(rotated.width*n,rotated.height*n),rotated.depth,1)
#         cvResize(rotated,big)
#         rotated=big
    if do_display:
        showlines(src,dst,rotated,show_src=True)
    return src,dst,rotated,numLines


if __name__ == "__main__":
    filename = "split0.png"
    if len(sys.argv)>1:
        for f in sys.argv[1:]:
            if f.find('/') != -1:
                dir,fn = os.path.split(f)
                src,dst,rotated,numLines = find(dir+"/",fn, do_display = True)
            else:
                src,dst,rotated,numLines = find("/tmp/",f, do_display = True)   
    else:
        src,dst,rotated,numLines = find("/tmp/",filename, do_display = True)
