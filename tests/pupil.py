#Identify pupils. Based on beta 1

import numpy as np
import cv2
import time

cap = cv2.VideoCapture(0)   #640,480
w = 1280
h = 720
writ = cv2.VideoWriter("/Users/nikhil/Desktop/out.mp4", cv2.VideoWriter_fourcc('M', 'P', '4', 'V'), 6, (w, h))
while(cap.isOpened()):
    ret, frame = cap.read()
    if ret==True:
        
        #downsample
        #frameD = cv2.pyrDown(cv2.pyrDown(frame))
        #frameDBW = cv2.cvtColor(frameD,cv2.COLOR_RGB2GRAY)

        #detect face
        out = frame
        frame = cv2.cvtColor(frame,cv2.COLOR_RGB2GRAY)
        faces = cv2.CascadeClassifier('haarcascade_eye.xml')
        detected = faces.detectMultiScale(frame, 1.1, 20, minSize=(50,50))

        #faces = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
        #detected2 = faces.detectMultiScale(frameDBW, 1.3, 5)

        pupilFrame = frame
        pupilO = frame
        windowClose = np.ones((8,8),np.uint8)
        windowOpen = np.ones((2,2),np.uint8)
        windowErode = np.ones((2,2),np.uint8)
        windowDilate = np.ones((2,2), np.uint8)

        #draw square
        for (x,y,w,h) in detected:
            cv2.rectangle(out, (x,y), ((x+w),(y+h)), (0,0,255),1) 
            cv2.line(out, (x,y), ((x+w,y+h)), (0,0,255),1)
            cv2.line(out, (x+w,y), ((x,y+h)), (0,0,255),1)
            pupilFrame = cv2.equalizeHist(frame[y+int(h*.25):(y+h), x:(x+w)])
            pupilO = pupilFrame
            _, pupilFrame = cv2.threshold(pupilFrame,55,255,cv2.THRESH_BINARY_INV) #50 ..nothin 70 is better
            pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_ERODE, windowErode)
            pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_ERODE, windowErode)
            pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_ERODE, windowErode)
            pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_ERODE, windowErode)
            pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_OPEN, windowOpen)
            pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_DILATE, windowDilate)
            pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_DILATE, windowDilate)
            pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_DILATE, windowDilate)
            pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_CLOSE, windowClose)
            pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_OPEN, windowClose)
            
            #pupilFrame = np.ones(pupilFrame.shape) * 255 - pupilFrame
            

            #so above we do image processing to get the pupil..
            #now we find the biggest blob and get the centriod

            threshold = cv2.inRange(pupilFrame,250,255)     #get the blobs
            _, contours, hierarchy = cv2.findContours(threshold,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
            
            
            circle = np.array([[[20,  1]],[[19,  2]],[[14,  2]],[[13,  3]],[[12,  3]],[[11,  4]],[[10,  4]],[[ 4, 10]],[[ 4, 11]],[[ 3, 12]],[[ 3, 13]],[[ 2, 14]],[[ 2, 19]],[[ 1, 20]],[[ 2, 21]],[[ 2, 26]],[[ 3, 27]],[[ 3, 28]],[[ 4, 29]],[[ 4, 30]],[[10, 36]],[[11, 36]],[[12, 37]],[[13, 37]],[[14, 38]],[[19, 38]],[[20, 39]],[[21, 38]],[[26, 38]],[[27, 37]],[[28, 37]],[[29, 36]],[[30, 36]],[[36, 30]],[[36, 29]],[[37, 28]],[[37, 27]],[[38, 26]],[[38, 21]],[[39, 20]],[[38, 19]],[[38, 14]],[[37, 13]],[[37, 12]],[[36, 11]],[[36, 10]],[[30,  4]],[[29,  4]],[[28,  3]],[[27,  3]],[[26,  2]],[[21,  2]]], dtype=np.int)
            MIN_PUPIL_SIZE = 300
            BETTER_PUPIL_SIZE = 400
            
            largeBlob = None
            maxArea = 0
            largeMatch = 0
            circleBlob = None
            bestMatch = 1000
            matchArea = 0
            for cnt in contours:
                match = cv2.matchShapes(circle, cnt, 1, 0)
                #cv2.drawContours(out[y+int(h*.25):(y+h), x:(x+w)], [cnt], 0, (127*match, 255 * (1-match), 127*match), 1)
                area = cv2.contourArea(cnt)
                if area >= MIN_PUPIL_SIZE:
                    if area > maxArea:
                        maxArea, largeBlob, largeMatch = area, cnt, match
                    if match < bestMatch:
                        bestMatch, circleBlob, matchArea = match, cnt, area
            
#             if largeBlob is circleBlob or bestMatch > .5:
#                 useBlob = largeBlob
#             elif maxArea < BETTER_PUPIL_SIZE or largeMatch > .6 or matchArea >= BETTER_PUPIL_SIZE:
#                 useBlob = circleBlob
#             else:
#                 useBlob = largeBlob
#             
# 
#             if useBlob is not None and len(useBlob) > 0:
#                 center = cv2.moments(useBlob)
#                 cx,cy = int(center['m10']/center['m00']), int(center['m01']/center['m00'])
#                 cv2.circle(out,(x + cx,y+cy+int(h*.25)),5,(0, 255, 0),-1)
#                 cv2.circle(pupilO,(cx,cy),5,255,-1)
            for i, useBlob in enumerate([largeBlob, circleBlob]):
                center = cv2.moments(useBlob)
                if center['m00'] == 0:
                    cx, cy = 0, 0
                else:
                    cx,cy = int(center['m10']/center['m00']), int(center['m01']/center['m00'])
                cv2.circle(out,(x + cx,y+cy+int(h*.25)),5,(255 * (1 - i), 255 * i, 0),-1)
                cv2.circle(pupilO,(cx,cy),5,255,-1)

        #show picture
        cv2.imshow('frame',out)
        writ.write(out)
        cv2.imshow('frame2', pupilFrame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    #else:
        #break

# Release everything if job is finished
cap.release()
writ = None
cv2.destroyAllWindows()
