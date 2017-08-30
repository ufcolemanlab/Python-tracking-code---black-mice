# -*- coding: utf-8 -*-
"""
Created on Sun Aug 27 17:36:00 2017

@author: Jesse Trinity, Jason Coleman 
"""

import cv2
import numpy as np
import scipy.io as sio
import Tkinter as tk
import tkFileDialog
from glob import glob


def get_frame(number, cap):
    for i in range(number):
        (ret, img) = cap.read()
        if ret == False:
            print "invalid frame"
            print(str(number))
    return img
    

def show_onset(filename, number, cap):
    frameMinus2 = get_frame(number-2, cap)
    frameMinus1 = get_frame(1, cap)
    frame0 = get_frame(1, cap)
    framePlus1 = get_frame(1, cap)
    framePlus2 = get_frame(1, cap)

    print([frameMinus2, frameMinus1, frame0, framePlus1, framePlus2])    
    
    images = np.hstack([frameMinus2, frameMinus1, frame0, framePlus1, framePlus2])
    cv2.imshow("frame: " + str(number), images)
    cv2.imwrite(filename.replace(".h264", "") + '_frame'+str(number)+'.png', images)
    #if cv2.waitKey(-1) & 0xFF == ord('q'):
    cv2.destroyAllWindows()
    cap.release()
    number=[]
    
    
def get_matfile_info(filename):
    
    """
    Returns all data within the MAT file to a tuple 'var'
        where var[0] = all tracking data (see tuple[0].keys())
              var[1] = stimFrames as ON/OFF pairs in an array
              var[2] = stimFrames as list of on, off, on, etc. frames
    """
    
    data_matfile = sio.loadmat(filename)
    stimFrameArray = np.concatenate(data_matfile['stimFrames'])
    stimFrameList = stimFrameArray.tolist()
    
    return data_matfile, stimFrameArray, stimFrameList
    
    
def get_frame_imgs():
    
    #Open file(s) dialog - TKinter
    root = tk.Tk()
    root.withdraw()
    dirname = tkFileDialog.askdirectory()
    
    #Setup file lists
    filetype_vid = str(dirname) +"/*.h264"
    filetype_mat = str(dirname) +"/*.mat"
    
    filenames_vid = glob(filetype_vid)
    filenames_mat = glob(filetype_mat)
    
    filenames_vid.sort()
    filenames_mat.sort()
    
    #Create and save PNG files of "onset/offset" and surrounding frames
    for i in range(len(filenames_vid)):        
        matfiledata = get_matfile_info(filenames_mat[i])
        stimFrameList = matfiledata[2]         
        
        for j in range(len(stimFrameList)):
            cap = cv2.VideoCapture(filenames_vid[i])            
            show_onset(filenames_vid[i], stimFrameList[j], cap)            
            print(str(stimFrameList[j]))
get_frame_imgs()