# -*- coding: utf-8 -*-
"""
File for selecting mouse ROI and box corners. Saves to same directory as
the h264 file.

by Brian Basnight, Jesse Trinity, Jason Coleman (Coleman Lab UF Pediatrics)

NOTES:
    p: pauses the video
    m: change modes between ROI selection and corner selection 
    s: saves the regions you picked
    q or esc: quit (does not save)
    
    If you mess up, just hit p twice to unpause and pause - you will
    start over in ROI selection mode
    
    Make sure to set "redo_option" to True if re-processing files after 'vetTracking'.

    FUTURE:
    1) Maybe implement slider to rapidly scrub/select frame for ROI selection
        Mouse needs to be away from walls for mouse selection
        Mouse ideally in motion at pause
"""

import Tkinter as tk
import tkFileDialog
import cv2
import pickle
import os

# Set options here
redo_option = False #Set to 'False' for first run; Set to 'True' to only run failed files from 'vetTracking'


# DO NOT ALTER CODE BELOW THIS LINE

frame = None
selecting = False
selectionMode = True
frameNumber = 0
corners = []
roiPoints = []

def check_cv():
    #check which open cv version
    #opcv_version3 = 1 #if opencv version 3.0 or greater, then true; if 2.4.x then false
    #if opencv version 3.0 or greater, then true; if 2.x then false (JEC)
    print ('opencv version: '+ str(cv2.__version__))
    opcv_versioncheck = cv2.__version__
    if str.find(opcv_versioncheck,'3') == 0:
        opcv_version3 = True 
    elif str.find(opcv_versioncheck,'2') == 0:
        opcv_version3 = False #if opencv version 3.0 or greater, then true; if 2.4.x then false
        print ('Possible issues using less than opencv v3.0.0')
        
    return 

#open file
if redo_option == False:
    root = tk.Tk()
    root.withdraw()
    file_paths = tkFileDialog.askopenfilenames(parent=root,filetypes = 
        [('H264','*.h264')],title='Choose a H264 video file to process...')    
if redo_option == True:
    redo_filenames = pickle.load( open(str(directory)+'/REDO.pickle', 'rb') )
    file_paths = redo_filenames['redoFiles']
    
print ('opencv version: '+ str(cv2.__version__))

#event bind select mouse ROI
def selectROI(event, x, y, flags, param):
    global roiPoints
    
    if event == cv2.EVENT_LBUTTONDOWN and len(roiPoints) < 4:
        roiPoints.append((x, y))
        cv2.circle(frame, (x, y), 4, (0, 255, 0), 2)
        cv2.imshow(frame_title, frame)
        print "ROI point " +str(len(roiPoints)) + ": " + str(x)+ " " + str(y)

#event bind select stim box corners
def selectCorners(event,x,y,flags,param):
    global corners
    
    if event == cv2.EVENT_LBUTTONDOWN and len(corners)<2:
        corners.append((x,y))
    elif event == cv2.EVENT_LBUTTONUP and len(corners)<2:
        corners.append((x,y))
        cv2.rectangle(frame,corners[0],(x,y),(0,0,255),1)
        cv2.imshow(frame_title,frame)
        print "corners: " + str(corners)

    pass

for i in range(len(file_paths)):
    file_path = file_paths[i]
    cap = cv2.VideoCapture(file_path)
    frame_title = os.path.split(file_path)[1]
    
    cv2.namedWindow(frame_title)
    
    
    #loop as long as video file is opened
    while cap.isOpened():
        
        #Get next valid frame
        ret, frame = cap.read()
        if not ret:
            print "Next frame not captured"
            break
        frameNumber+=1
        
        key = cv2.waitKey(25) & 0xFF
        cv2.imshow(frame_title,frame)
        
        #wait for user to pause video 
        if key == ord("p"):
            print "Video #"+str(i)+" of "+str(len(file_paths))+ " paused at frame " + str(frameNumber)
            cv2.setMouseCallback(frame_title,selectROI)
            
    
            while cap.isOpened(): 
                key = cv2.waitKey(1) & 0xFF
                
                #listen for mode selection (user presses 'm')
                if key == ord('m'):
                    if selectionMode == True:
                        cv2.setMouseCallback(frame_title,selectCorners)
                        print "Switching to corner selection mode."
                    elif selectionMode == False:
                        cv2.setMouseCallback(frame_title,selectROI)
                        print "switching to ROI selection mode."
                    selectionMode = not selectionMode
                    
                #press 'q' or 'esc' to quit 
                elif key == ord('q') or key == 27:
                    roiPoints = []
                    corners = []
                    frameNumber = 0
                    selectionMode = True
                    cv2.destroyAllWindows()
                    cap.release()
                
                #press 's' to save                
                elif key == ord('s'):
                    saved = {"corners":corners,"roiPoints":roiPoints,"roiFrame":frameNumber}
                    pickle.dump(saved,open(file_path[:-5] + ".p","wb"))
                    print str(i)+". Variables saved to " + file_path[:-5] + ".p"
                    print(" ")
                
                #press 'p' to unpause
                elif key == ord("p"):
                    roiPoints = []
                    corners = []
                    selectionMode = True
                    break
                
        #listen for quit command
        if key == ord('q') or key == 27:
            cv2.destroyAllWindows()
            cap.release()
print(" ")                    
print ("all selected files processed")
