# -*- coding: utf-8 -*-
"""
File to process video files with previously selected ROIs

by Brian Basnight, Jesse Trinity, Jason Coleman (Coleman Lab UF Pediatrics)

Notes: For use with VOR data from Pi Camera (h264 files)
For stimuluas detection to work, paramaters set for
    1) Screens on left and right of video frame
    2) 100 reversals, 30sec gray, 5 sessions, 5min delay (~100s each session; 100flips, 100flops)

"""

import pickle
from glob import glob
import tkFileDialog
import Tkinter as tk
import cv2
import numpy as np
from scipy.io import matlab
import os

# Set options here
crop_chamber = False
redo_option = False #REDO.p file will be deleted if present in selected directory and set to 'False'
preview_frames = 300 # number of frames to preview (default = 300)
cannystate = False
cannyThresh = 'hi' #change to opposite ('hi' or 'lo') if no stim detected or "Problem with stimFrames" error occurs

# DO NOT ALTER CODE BELOW THIS LINE

#GUI stuff
root = tk.Tk()
root.withdraw()
directory = tkFileDialog.askdirectory()


#if opencv version 3.0 or greater, then true; if 2.x then false (JEC)
print ('opencv version: '+ str(cv2.__version__))
print (' ')
opcv_versioncheck = cv2.__version__
if str.find(opcv_versioncheck,'3') == 0:
    opcv_version3 = True 
elif str.find(opcv_versioncheck,'2') == 0:
    opcv_version3 = False #if opencv version 3.0 or greater, then true; if 2.


#Setup file lists
videoName = str(directory) +"/*.h264"
roiName = str(directory) +"/*.p"
redoName = str(directory) +"/REDO.pickle"

videoList = glob(videoName)
roiList = glob(roiName)

if redo_option == True:
    redo_filenames = pickle.load( open(str(directory)+'/REDO.pickle', 'rb') )
    videoList = redo_filenames['redoFiles']
    roiList = redo_filenames['redoFiles']
    roiList = [extension.replace('h264', 'p') for extension in roiList]
elif redo_option == False:
    if os.path.isfile(str(directory) +"/REDO.pickle"):
        os.remove(str(directory) +"/REDO.pickle")
        
  
videoList.sort()
roiList.sort()

print "directory: " + directory

#gets upper left and lower right points
def getPointExtremes(n):
    n = np.array(n)
    s = n.sum(axis=1)
    ul = n[np.argmin(s)]
    lr = n[np.argmax(s)]
    return ul, lr

#uses canny edge detection to decide if either screen showed activity
def detectStimulus(frame,preview_cannnylines,cannyThresh):
            left_on = False
            right_on = False
            stim_left = frame[80:400, 40:90]
            stim_right = frame[80:400, 550:600]
            
            grayscale_left = cv2.cvtColor(stim_left,cv2.COLOR_BGR2GRAY)
            if cannyThresh == 'hi':
                canny_left = cv2.Canny(grayscale_left,50,100,apertureSize = 3)
            if cannyThresh == 'lo':
                canny_left = cv2.Canny(grayscale_left,10,20,apertureSize = 3) #(JEC)
            lines_left = cv2.HoughLinesP(canny_left,1,np.pi/180,30,30,10)
            
            grayscale_right = cv2.cvtColor(stim_right,cv2.COLOR_BGR2GRAY)
            if cannyThresh == 'hi':
                canny_right = cv2.Canny(grayscale_right,50,100,apertureSize = 3)
            if cannyThresh == 'lo':
                canny_right = cv2.Canny(grayscale_right,10,20,apertureSize = 3) #(JEC)
            lines_right = cv2.HoughLinesP(canny_right,1,np.pi/180,30,30,10)
            
            if preview_cannnylines == True:
                cv2.imshow('left',canny_left)
                cv2.imshow('right',canny_right)
            
            if lines_left is not None:
                if len(lines_left > 20):
                    left_on = True
            
            if lines_right is not None:
                if len(lines_right > 20):
                    right_on = True
            
            return left_on, right_on

#looks through the list of frame numbers and figures out where the stim
#blocks begin/end by comparing the number of the next/previous index
def getOnsets(l,minframes):
    onsets = []
    offsets = []
    current = 0
    for item in l:
        if(item - current >20):
            onsets.append(item)
            if (current !=0):
                offsets.append(current)
    
        current = item
    try:
        offsets.append(l[-1])
    except IndexError:
        if len(onsets)<1 or len(offsets)<1:
            print "list is empty"
        return offsets
    
    list_pairs = map(lambda x,y:(x,y),onsets,offsets)
    list_pairs = [x for x in list_pairs if x[1]-x[0] >minframes]
    on_off_pairs = np.array(list_pairs)
    
    return on_off_pairs


term_crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,10,1)

def main():
    
    #Run for every video in videoList
    for i in range(len(videoList)):
        
        print str(i)+") Processing " + videoList[i]
        frame_title = os.path.split(videoList[i])[1]
        
        #load video and pickle file
        cap = cv2.VideoCapture(videoList[i])
        getROI = pickle.load( open( roiList[i], "rb" ) )
        
        #video variables
        roiFrame = getROI["roiFrame"]
        corners = getROI["corners"]
        roiPoints = getROI["roiPoints"]
        
#        print roiFrame
#        print roiPoints
          
        dist_all = []
        mouse_centroid = []
        directionalPoints = []
        directionAngle = []
        frameNumber = 0
        dist = 0
        avg_index = 0
        
        stimFrames = np.array([])
        stimLocation = ''
        left_stim_list = []
        right_stim_list = []
        
        
        #get upper left and lower right points of corners and roiPoints
        if len(corners) > 1:
            cornUL, cornLR = getPointExtremes(corners)
        
        roiUL, roiLR = getPointExtremes(roiPoints)
        
        roiBox = (roiUL[0],roiUL[1], roiLR[0], roiLR[1])
             
        #skip all frames before roiFrame
        for j in range(roiFrame):
            ret, frame = cap.read()
            frameNumber +=1
        
        #get mouse initial orientation
        mid = tuple((np.mean(roiPoints,axis=0).astype(int)))
        front = tuple((np.mean(roiPoints[:2],axis=0).astype(int)))
        
        direction = np.array((front[0]-mid[0],front[1]-mid[1]))
#        print direction
        refVector = np.array((0,1))
        
        cosAngle = np.dot(refVector,direction)/np.linalg.norm(refVector)/np.linalg.norm(direction)
        angle = (np.arccos(cosAngle))*180/np.pi
        if direction[0] > 0:
            angle = 360 - angle
#        print angle
        r = (0.0,0.0,angle)
        last_r=r
        
        #set up ROI for tracking
        roi = frame[roiUL[1]:roiLR[1],roiUL[0]:roiLR[0]]
        roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        roiHist = cv2.calcHist([roi], [0], None, [16], [0,180])
        roiHist = cv2.normalize(roiHist, roiHist, 0, 255, cv2.NORM_MINMAX)
               
        #Read the video
        while cap.isOpened():
            
            #get next frame
            ret, frame = cap.read()
            if not ret:
                break
            frameNumber +=1
#            print frameNumber
            
            #detect stimulus and add frameNumber to appropriate list
            left_on, right_on = detectStimulus(frame, cannystate, 'hi')
            
            if (left_on == True):
                left_stim_list.append(frameNumber)
            if (right_on == True):
                right_stim_list.append(frameNumber)
            
            #crop frame if desired
            if crop_chamber == True:
                frame = frame[cornUL[1]:cornLR[1],cornUL[0]:cornLR[0]]
            
            #image processing steps
            #add white/black branch here (based on corner selection?)
            bwTemp = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            segmentedImage = cv2.GaussianBlur(bwTemp, (11, 11), 0)
            backProj = cv2.calcBackProject([segmentedImage], [0], roiHist, [0, 180], 1)
            
            (r, roiBox) = cv2.CamShift(backProj, roiBox, term_crit)
            
            #make sure camshift hasn't rotated 180
            #Angle is measured clockwise from +y (straight down)
#            print last_r[2]-r[2]
            if (240 > abs(last_r[2]-r[2]) > 120):
                lstr = list(r)
                lstr[2] = (lstr[2] + 180)%360
                r = tuple(lstr)
            
            last_r = r
            
            directionAngle.append(r[2])

            #check opencv version
            if opcv_version3 == 1:
                pts = np.int0(cv2.boxPoints(r))
            else:
                pts = np.int0(cv2.cv.BoxPoints(r))
            
            #Update the distance the mouse has travelled
            avg = (pts[0,0] + pts[0,1] + pts[1,0] + pts[1,1])/4
    
            if avg_index == 0:
                oldAvg = avg
                dist = 0
    
            if avg_index != 0:
                dist += abs(oldAvg - avg)
                    
            dist_all.append(dist)
            mouse_centroid.append(pts)
                
            oldAvg = avg
            avg_index+=1
            
            #calculate directional points
            mid = tuple((np.mean(pts,axis=0).astype(int)))
            front = tuple((np.mean([pts[3],pts[0]],axis=0).astype(int)))
            right = tuple((np.mean([pts[0],pts[1]],axis=0).astype(int)))
            back = tuple((np.mean([pts[1],pts[2]],axis=0).astype(int)))
            left = tuple((np.mean([pts[2],pts[3]],axis=0).astype(int)))
            
            directionalPoints.append(np.array([front,right,back,left]))

            #draw the roi
            cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
#            print "r: " + str(r)
#            print "roiBox: " + str(roiBox)
#            print "pts: " + str(pts)
            
            #draw red to the front of the mouse
            cv2.line(frame,(pts[3][0],pts[3][1]),(pts[0][0],pts[0][1]),(0,0,255),2)
            
            #draw blue to the right of the mouse
            cv2.line(frame,(pts[0][0],pts[0][1]),(pts[1][0],pts[1][1]),(255,0,0),2)
            
            #draw directional lines
            cv2.line(frame,mid,front,(0,0,255),2)
            cv2.line(frame,mid,right,(255,0,0),2)
            
            
            #show the frame for 300 frames
            if frameNumber <= roiFrame + preview_frames:
                cv2.imshow(frame_title,frame)
                key = cv2.waitKey(1) & 0xFF
            elif frameNumber > roiFrame + preview_frames:
                cv2.destroyAllWindows()
            
            #quit video if user presses q
            if key == ord('q'):
                cv2.destroyAllWindows()
                cap.release()
            
            #quit batch if user presses esc
            elif key == 27:
                cv2.destroyAllWindows()
                cap.release()
                return
            
            elif key == ord('p'):
                while True:
                    pause = cv2.waitKey(-1)
                    if key == ord('p'):
                        break
        
        #detect onsets/offsets on the screen which showed more activity
        leftFrames = getOnsets(left_stim_list,2000) #e.g., stim frames are ~2580 for 100 reversals
        rightFrames = getOnsets(right_stim_list,2000)
        
        if (len(leftFrames)>len(rightFrames)):
            stimLocation = 'left'
            stimFrames = leftFrames

        elif(len(rightFrames)>len(leftFrames)):
            stimLocation = 'right'
            stimFrames = rightFrames

        elif len(leftFrames)==len(rightFrames):
            print "No stimulus detected: check stimulus parameters"
            
        # Final check added by (JEC)    
        if (len(stimFrames)<5) or (len(stimFrames)>5):
            print "Problem with stimFrames output: check stimulus parameters"
            print "     May need to adjust 'cannyThresh' value for 'def detectStimulus'"
            
        print "stims:"
        print stimFrames
        print "distance traveled: " + str(dist)
        print " "
        
        #save to matlab file
        saveName = videoList[i].replace("\\","/")
        savedVariables = {"crop_chamber":crop_chamber, "corners": corners, "file": saveName,"dist_all":dist_all,
                          "mouse_centroid":mouse_centroid,"roiPts":roiPoints,
                          "roiFrame":roiFrame,"totalFrames":frameNumber,
                          "stimLocation":stimLocation,"stimFrames":stimFrames,
                          "directionalPoints":directionalPoints,"directionAngle":directionAngle}
        matlab.savemat(saveName+'.mat', savedVariables)
        
        #Release the file
        cv2.destroyAllWindows()
        cap.release()

main()