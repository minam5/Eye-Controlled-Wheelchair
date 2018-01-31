import numpy as np
import cv2
import time
from picamera.array import PiRGBArray
from picamera import PiCamera
import math

#magic numbers
camw, camh = 360, 160
minEyeSize = 50
cascadeScale = 1.2
cascadeMinNeighbors = 20
eyeGroupCenterMaxError = 80
redFac = .6 # eye group reduction factor
addFac = 1 - redFac # eye group addition factor
maxAveragePoints = 210
windowClose = np.ones((8,8),np.uint8)
windowOpen = np.ones((2,2),np.uint8)
windowErode = np.ones((5,5),np.uint8)
windowDilate = np.ones((4,4), np.uint8)
MIN_PUPIL_SIZE = 300
maxIgnoreTimeClosed = 1

def setup():
    #setup camera
    camera = PiCamera()
    camera.resolution = (camw, camh)
    rawCapture = PiRGBArray(camera)
    time.sleep(.1)
    #setup eye detector
    classifier = cv2.CascadeClassifier('haarcascade_eye.xml')
    return camera, rawCapture, classifier

def run_loop():
    camera, rawCapture, classifier = setup()
    #setup eye grouping. Format of each group: [boxCenterX, boxCenterY, boxWidth, boxHeight, sumPupilX, sumPupilY, n, lastTime]
    eyeGroups = []
    #repeatedly take pics
    for cap in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
        keep_going = sense_eyes(cap, rawCapture, classifier, eyeGroups)
        if not keep_going:
            break

def sense_eyes(cap, rawCapture, classifier, eyeGroups):
    now = time.time()
    out, frame, detected = detect_eyes(cap, rawCapture, classifier)
    
    dx, dy, n = 0, 0, 0
    #for each detected eye
    for (x, y, w, h) in detected:
        #assign group to eye and update some group numbers
        group = group_eye(eyeGroups, x, y, w, h)
        
        #find pupil
        
        #filter for pupil
        pupilFrame = cv2.equalizeHist(frame[y+int(h*.25):(y+h), x:(x+w)])
        _, pupilFrame = cv2.threshold(pupilFrame,55,255,cv2.THRESH_BINARY_INV) #50 ..nothin 70 is better
        pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_ERODE, windowErode)
        pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_OPEN, windowOpen)
        pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_DILATE, windowDilate)
        pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_CLOSE, windowClose)
        pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_OPEN, windowClose)
        
        #identify largest blob and most circular blob
        threshold = cv2.inRange(pupilFrame,250,255)     #get the blobs
        _, contours, hierarchy = cv2.findContours(threshold,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        circle = np.array([[[20,  1]],[[19,  2]],[[14,  2]],[[13,  3]],[[12,  3]],[[11,  4]],[[10,  4]],[[ 4, 10]],[[ 4, 11]],[[ 3, 12]],[[ 3, 13]],[[ 2, 14]],[[ 2, 19]],[[ 1, 20]],[[ 2, 21]],[[ 2, 26]],[[ 3, 27]],[[ 3, 28]],[[ 4, 29]],[[ 4, 30]],[[10, 36]],[[11, 36]],[[12, 37]],[[13, 37]],[[14, 38]],[[19, 38]],[[20, 39]],[[21, 38]],[[26, 38]],[[27, 37]],[[28, 37]],[[29, 36]],[[30, 36]],[[36, 30]],[[36, 29]],[[37, 28]],[[37, 27]],[[38, 26]],[[38, 21]],[[39, 20]],[[38, 19]],[[38, 14]],[[37, 13]],[[37, 12]],[[36, 11]],[[36, 10]],[[30,  4]],[[29,  4]],[[28,  3]],[[27,  3]],[[26,  2]],[[21,  2]]], dtype=np.int)
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
        
        #choose between large and circle (possibly make circle smarter or add third option)
        #for now, just choose circle
        useBlob = circleBlob
        if useBlob is not None:
            #use chosen blob to find direction
            moments = cv2.moments(useBlob)
            if moments['m00'] > 0:
                cx,cy = int(moments['m10']/moments['m00']), int(moments['m01']/moments['m00'])
                cv2.circle(out, (x + cx, y + cy + int(h * .25)), 5, (0,0,255), -1)

                #finish updating group
                if group[6] < maxAveragePoints:
                    group[4] += cx
                    group[5] += cy
                    group[6] += 1
                else:
                    group[4] = (group[4] * (maxAveragePoints - 1)) / group[6] + cx
                    group[5] = (group[5] * (maxAveragePoints - 1)) / group[6] + cx
                    group[6] = maxAveragePoints
                group[7] = now

                #determine relative direction and strength
                dx += -(cx - group[4] / group[6]) / group[2]
                dy += -(cy - group[5] / group[6]) / group[3]
                n += 1
    if n > 0:
        print("direction: (", dx / n, ", ", dy/n, "), aka ", ("left" if dx < 0 else "right"))
    else:
        pass
        #print("no eye")
    for i, group in enumerate(eyeGroups):
        if now - group[7] > maxIgnoreTimeClosed:
            print("eye ", i, " is closed")
    for group in eyeGroups:
        cv2.rectangle(out, (int(group[0] - group[2] / 2), int(group[1] - group[3] / 2)), ((int(group[0] + group[2] / 2), int(group[1] + group[3] / 2))), (0, 0, 255), 1)
    cv2.imshow("frame", out)
    if cv2.waitKey(5) & 0xFF == ord('q'):
        return False
    else:
        return True

def detect_eyes(cap, rawCapture, classifier):
    #save picture and convert to gray
    out = cap.array
    frame = cv2.cvtColor(out,cv2.COLOR_BGR2GRAY)
    #prepare for next picture
    rawCapture.truncate(0)
    #make sure cam dimensions are accurate and not rounded
    camh, camw = frame.shape
    #prepare flipped frame
    revFrame = cv2.flip(frame, 1)
    
    #cascade classify both normal and flipped frames
    detected = classifier.detectMultiScale(frame, cascadeScale, cascadeMinNeighbors, minSize=(minEyeSize,minEyeSize))
    revDetected = classifier.detectMultiScale(revFrame, cascadeScale, cascadeMinNeighbors, minSize=(minEyeSize, minEyeSize))
    #unflip detected areas from flipped frame detection and add to detected
    for (x, y, w, h) in revDetected:
        np.append(detected, [(camw-x-w, y, w, h)])
    return out, frame, detected

def group_eye(eyeGroups, x, y, w, h):
    found = False
    for group in eyeGroups:
        if math.sqrt((x + w/2 - group[0]) ** 2 + (y + h/2 - group[1]) ** 2) <= eyeGroupCenterMaxError:
            found = True
            group[0] = group[0] * redFac + (x + w/2) * addFac
            group[1] = group[1] * redFac + (y + h/2) * addFac
            group[2] = group[2] * redFac + w * addFac
            group[3] = group[3] * redFac + h * addFac
            break
    if not found:
        group = [x + w/2, y + h/2, w, h, 0, 0, 0, 0]
        eyeGroups.append(group)
    return group