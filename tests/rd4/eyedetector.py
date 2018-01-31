import numpy as np
import cv2
import time
from picamera.array import PiRGBArray
from picamera import PiCamera
import sys
from eye import Eye
from controller import WheelChairController

class EyeDetector:
    def __init__(self):
        #magic numbers
        self.camw, self.camh = 450, 200
        self.minEyeSize = 60
        self.cascadeScale = 1.2
        self.cascadeMinNeighbors = 20
        self.circle = np.array([[[20,  1]],[[19,  2]],[[14,  2]],[[13,  3]],[[12,  3]],
                [[11,  4]],[[10,  4]],[[ 4, 10]],[[ 4, 11]],[[ 3, 12]],[[ 3, 13]],
                [[ 2, 14]],[[ 2, 19]],[[ 1, 20]],[[ 2, 21]],[[ 2, 26]],[[ 3, 27]],
                [[ 3, 28]],[[ 4, 29]],[[ 4, 30]],[[10, 36]],[[11, 36]],[[12, 37]],
                [[13, 37]],[[14, 38]],[[19, 38]],[[20, 39]],[[21, 38]],[[26, 38]],
                [[27, 37]],[[28, 37]],[[29, 36]],[[30, 36]],[[36, 30]],[[36, 29]],
                [[37, 28]],[[37, 27]],[[38, 26]],[[38, 21]],[[39, 20]],[[38, 19]],
                [[38, 14]],[[37, 13]],[[37, 12]],[[36, 11]],[[36, 10]],[[30,  4]],
                [[29,  4]],[[28,  3]],[[27,  3]],[[26,  2]],[[21,  2]]], dtype=np.int)
        self.classifier = cv2.CascadeClassifier('haarcascade_eye.xml')
        self.windowClose = np.ones((8,8),np.uint8)
        self.windowOpen = np.ones((2,2),np.uint8)
        self.windowErode = np.ones((5,5),np.uint8)
        self.windowDilate = np.ones((4,4), np.uint8)
        self.MIN_PUPIL_SIZE = 420
        self.newEyeCoordTime = 1.5
        self.maxWrongNumEyes = 15
        self.maxTimeEyeMissing = 5

        self.eyeGroups = []
        self.wrongNumEyes = 100 #start out wrong, wait until it works out
        self.controller = WheelChairController()

        #setup camera
        self.camera = PiCamera()
        self.camera.resolution = (self.camw, self.camh)
        self.raw = PiRGBArray(self.camera)
        time.sleep(.1)

    def run(self):
        #repeatedly take pics
        for cap in self.camera.capture_continuous(self.raw, format="bgr", use_video_port=True):
            if self.sense_eyes(cap): #returns true if should stop
                break
            if self.controller.should_shut_down():
                break
        self.controller.sig_error_reset() #stop and turn on light for shutdown

    def sense_eyes(self, cap):
        now = time.time()
        out, frame, detected = self.detect_eyes(cap)


        dx, dy, n = 0, 0, 0
        #for each detected eye
        for (x, y, w, h) in detected:
            #assign group to eye and update some group numbers
            group = self.group_eye(x, y, w, h, now)
        
            #find pupil
        
            #filter for pupil
            pupilFrame = cv2.equalizeHist(frame[y+int(h*.25):(y+h), x:(x+w)])
            # for threshold 50 ..nothin 70 is better
            _, pupilFrame = cv2.threshold(pupilFrame,55,255,cv2.THRESH_BINARY_INV)
            pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_ERODE, self.windowErode)
            pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_OPEN, self.windowOpen)
            pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_DILATE, self.windowDilate)
            pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_CLOSE, self.windowClose)
            pupilFrame = cv2.morphologyEx(pupilFrame, cv2.MORPH_OPEN, self.windowClose)
        
            #identify largest blob and most circular blob
            threshold = cv2.inRange(pupilFrame,250,255)     #get the blobs
            _, contours, hierarchy = cv2.findContours(threshold,cv2.RETR_LIST,
                                                        cv2.CHAIN_APPROX_SIMPLE)
            largeBlob = None
            maxArea = 0
            largeMatch = 0
            circleBlob = None
            bestMatch = 1000
            matchArea = 0
            for cnt in contours:
                match = cv2.matchShapes(self.circle, cnt, 1, 0)
                #cv2.drawContours(out[y+int(h*.25):(y+h), x:(x+w)], [cnt], 0,
                                    #(127*match, 255 * (1-match), 127*match), 1)
                area = cv2.contourArea(cnt)
                if area >= self.MIN_PUPIL_SIZE:
                    if area > maxArea:
                        maxArea, largeBlob, largeMatch = area, cnt, match
                    if match < bestMatch:
                        bestMatch, circleBlob, matchArea = match, cnt, area

            useBlob = self.choose_blob(largeBlob, maxArea, largeMatch, circleBlob,
                                        bestMatch, matchArea)
            if useBlob is not None:
                #use chosen blob to find direction
                mmt = cv2.moments(useBlob)
                cx,cy = int(mmt['m10']/mmt['m00']), int(mmt['m01']/mmt['m00'])
                cv2.circle(out, (x + cx, y + cy + int(h * .25)), 5, (0,0,255), -1)

                ddx, ddy = group.update_group2(cx, cy, now)
                dx += ddx
                dy += ddy
                n += 1
        if n > 0:
            self.controller.sig_direction(dx / n, dy / n)
        else:
            self.controller.sig_no_eye(now)

        #cv2.imshow("frame", out)
        #if cv2.waitKey(5) & 0xFF == ord('q'):
        #    return True

        useGroups = []
        i = 0
        while i < len(self.eyeGroups):
            group = self.eyeGroups[i]
            group.update_group3(now)
            tsf = now - group.lastFound
            if now - group.created >= self.newEyeCoordTime and tsf < self.maxTimeEyeMissing:
                useGroups.append(group)
            if tsf > self.maxTimeEyeMissing or (tsf > 2 * self.newEyeCoordTime and len(self.eyeGroups) > 2): #twice as long as coord time. Eye doesn't exist
                del self.eyeGroups[i]
                i -= 1
            i += 1

        #print("total eyes: ", len(self.eyeGroups))
        if len(useGroups) != 2:
            self.wrongNumEyes += 1
            if self.wrongNumEyes > self.maxWrongNumEyes:
                if len(useGroups) > 2:
                    self.eyeGroups = []
                self.controller.sig_error_reset()
        else:
            self.wrongNumEyes = 0
            self.controller.sig_turn_off_error_light()
        if len(useGroups) > 2:
            useGroups.sort(key=lambda group: group.lastFound)
            useGroups = useGroups[-2:]
        self.controller.process_blink_commands(useGroups, now)

    def detect_eyes(self, cap):
        #save picture and convert to gray
        out = cap.array
        frame = cv2.cvtColor(out,cv2.COLOR_BGR2GRAY)
        #prepare for next picture
        self.raw.truncate(0)
        #make sure cam dimensions are accurate and not rounded
        self.camh, self.camw = frame.shape
        #prepare flipped frame
        revFrame = cv2.flip(frame, 1)
    
        #cascade classify both normal and flipped frames
        detected = self.classifier.detectMultiScale(frame, self.cascadeScale,
                    self.cascadeMinNeighbors, minSize=(self.minEyeSize, self.minEyeSize))
        revDetected = self.classifier.detectMultiScale(revFrame, self.cascadeScale,
                    self.cascadeMinNeighbors, minSize=(self.minEyeSize, self.minEyeSize))
        #unflip detected areas from flipped frame detection and add to detected
        for (x, y, w, h) in revDetected:
            np.append(detected, [(self.camw-x-w, y, w, h)])
        return out, frame, detected


    def group_eye(self, x, y, w, h, now):
        found = False
        for group in self.eyeGroups:
            if group.update_group1(x, y, w, h, now):
                found = True
                break
        if not found:
            group = Eye(x + w/2, y + h/2, w, h, now)
            self.eyeGroups.append(group)
        return group

    def choose_blob(self, largeBlob, maxArea, largeMatch, circleBlob, bestMatch,
                    matchArea):
        return circleBlob if (largeBlob is circleBlob) or matchArea > .3 * maxArea \
                else largeBlob

    def __del__(self):
        self.camera.close()
        self.controller.sig_error_reset() #stop and turn on light for shutdown. Redundancy
        self.controller.release_assets()

if __name__ == "__main__":
    print("begin")
    main = EyeDetector()
    print("loaded")
    main.run()
    main = None #remove reference so that __del__() runs immediately
    print("Control program has ended. System will shutdown unless kill signal sent within 3 seconds")
    time.sleep(3)
    sys.exit(0)
