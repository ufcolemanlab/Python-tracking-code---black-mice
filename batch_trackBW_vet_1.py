# -*- coding: utf-8 -*-
"""
File to process video files with previously selected ROIs

Notes:
    1) Maybe implement slider
        mouse needs to be away from walls for mouse selection
        mouse ideally in motion at pause
    2) Maybe a "vet mode" that allows you to see tracking for 100 frames each video
        select Y or N to keep *.p file or redo - creates list of redos for selectROI script
"""

import pickle
from glob import glob
import tkFileDialog
import Tkinter as tk
import cv2
import numpy as np
import os


crop_chamber = False

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
videoName = str(directory) +"/vid*.h264"
roiName = str(directory) +"/vid*.p"

videoList = glob(videoName)
roiList = glob(roiName)

videoList.sort()
roiList.sort()


global redoFiles
redoFiles=[]

print "directory: " + directory

#gets upper left and lower right points
def getPointExtremes(n):
    n = np.array(n)
    s = n.sum(axis=1)
    ul = n[np.argmin(s)]
    lr = n[np.argmax(s)]
    return ul, lr

#uses canny edge detection to decide if either screen showed activity
def detectStimulus(frame):
            left_on = False
            right_on = False
            stim_left = frame[80:400, 40:90]
            stim_right = frame[80:400, 550:600]
            
            grayscale_left = cv2.cvtColor(stim_left,cv2.COLOR_BGR2GRAY)
            #canny_left = cv2.Canny(grayscale_left,50,100,apertureSize = 3)
            canny_left = cv2.Canny(grayscale_left,20,40,apertureSize = 3) #(JEC)
            lines_left = cv2.HoughLinesP(canny_left,1,np.pi/180,30,30,10)
            
            grayscale_right = cv2.cvtColor(stim_right,cv2.COLOR_BGR2GRAY)
            #canny_right = cv2.Canny(grayscale_right,50,100,apertureSize = 3)
            canny_right = cv2.Canny(grayscale_right,20,40,apertureSize = 3) #(JEC)
            lines_right = cv2.HoughLinesP(canny_right,1,np.pi/180,30,30,10)
            
            if lines_left is not None:
                if len(lines_left > 5):
                    left_on = True
            
            if lines_right is not None:
                if len(lines_right >5):
                    right_on = True
            
            return left_on, right_on

#looks through the list of frame numbers and figures out where the stim
#blocks begin/end by comparing the number of the next/previous index
def getOnsets(list):
    onsets = []
    offsets = []
    current = 0
    for item in list:
        if(item - current >20):
            onsets.append(item)
            if (current !=0):
                offsets.append(current)
    
        current = item
    offsets.append(list[len(list)-1])
    
    on_off_pairs = np.array(map(lambda x,y:(x,y),onsets,offsets))
    
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
        
        print(str(roiFrame))
       
        dist_all = []
        mouse_centroid = []
        frameNumber = 0
        dist = 0
        avg_index = 0
        
#        stimFrames = np.array([])
#        stimLocation = ''
#        left_stim_list = []
#        right_stim_list = []
        
        #get upper left and lower right points of corners and roiPoints
        if len(corners) > 1:
            cornUL, cornLR = getPointExtremes(corners)
        
        roiUL, roiLR = getPointExtremes(roiPoints)
        
        roiBox = (roiUL[0],roiUL[1], roiLR[0], roiLR[1])
             
        #skip all frames before roiFrame
        for j in range(roiFrame):
            ret, frame = cap.read()
            frameNumber +=1
        print("frameNumber: "+str(frameNumber))
        
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
                
#            #detect stimulus and add frameNumber to appropriate list
#            left_on, right_on = detectStimulus(frame)
#            
#            if (left_on == True):
#                left_stim_list.append(frameNumber)
#            if (right_on == True):
#                right_stim_list.append(frameNumber)
#            
            #crop frame if desired
            if crop_chamber == True:
                frame = frame[cornUL[1]:cornLR[1],cornUL[0]:cornLR[0]]
            
            #image processing steps
            #add white/black branch here(based on corner selection?)
            bwTemp = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            segmentedImage = cv2.GaussianBlur(bwTemp, (11, 11), 0)
            backProj = cv2.calcBackProject([segmentedImage], [0], roiHist, [0, 180], 1)
            
            (r, roiBox) = cv2.CamShift(backProj, roiBox, term_crit)
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

            #draw the roi
            cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
            
            #show the frame for 300 frames
            #if frameNumber <= roiFrame + 1000:
            cv2.imshow(frame_title,frame)
            key = cv2.waitKey(1) & 0xFF
            #elif frameNumber > roiFrame + 1000:
                #cv2.destroyAllWindows()
                #break
            
            #print('PRESS Y to keep ROI')
            if key == ord('y'):
                cv2.destroyAllWindows()
                cap.release()
                print("OK: "+str(frameNumber)+" "+frame_title)
                print(" ")
            #print('PRESS N to REDO ROI')    
            elif key == ord('n'):
                redoFiles.append(videoList[i])
                cv2.destroyAllWindows()
                cap.release()
                print("redo: "+str(frameNumber)+" "+frame_title)
                print(" ")
            
            #quit if user presses 'q' or 'esc'
            if key == ord('q') or key == 27:
                cv2.destroyAllWindows()
                cap.release()
                return

#        #detect onsets/offsets on the screen which showed more activity
#        if (len(left_stim_list)>len(right_stim_list)):
#            stimLocation = 'left'
#            stimFrames = getOnsets(left_stim_list)
#        elif (len(left_stim_list)<len(right_stim_list)):
#            stimLocation = 'right'
#            stimFrames = getOnsets(right_stim_list)
#        else:
#            print "No stimulus detected: check stimulus parameters"
#            
#        # Final check added by (JEC)    
#        if (len(stimFrames)<5) or (len(stimFrames)<5):
#            print "Problem with stimFrames output: check stimulus parameters"
#            print "     May need to adjust 'canny_left' and 'canny_right' thresholds in 'def detectStimulus'"
#            
#        
#        print "stims:"
#        print stimFrames
#        print "distance travelled: " + str(dist)
#        print " "
#        
#        #save to matlab file
#        savedVariables = {"crop_chamber":crop_chamber, "corners": corners, "file": saveName,"dist_all":dist_all,
#                          "mouse_centroid":mouse_centroid,"roiPts":roiPoints,
#                          "roiFrame":roiFrame,"totalFrames":frameNumber,
#                          "stimLocation":stimLocation,"stimFrames":stimFrames}
#        matlab.savemat(saveName+'.mat', savedVariables)
    
    
    #Release the file
    cv2.destroyAllWindows()
    cap.release()
    
    print(" ")
    print("fin.")
    print(str(i+1)+" files vetted.")
    if len(redoFiles) > 0:
        dir_name = os.path.split(videoList[0])[0]
        saveName = dir_name+"/REDO"
        saved = {"redoFiles":redoFiles, "frameNumber":frameNumber}
        pickle.dump(saved,open(saveName + ".pickle","wb"))
        print("  ** Need to redo: "+str(redoFiles)+" **")
        print("  ** Filenames saved to " + saveName + ".pickle")
        print(" ")
        print("Re-run selectROI_*.py and batch_track_*.py with 'REDO.pickle' in same directory as video & roi files.")
        print("  Set 'redo_option' in both scripts to 'True'")
    else:
        print("  All files are good for analysis.")
        print("Proceed with batch_track_*.py script.")
        print("  Set 'redo_option' to 'False'")
        print(" ")


main()



