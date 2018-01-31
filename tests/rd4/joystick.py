#!/usr/bin/python

from PCA9685 import PCA9685 as PWM
import time

class Joystick:
    def __init__(self):
        self.pwm = PWM(0x40)
        self.pwm.set_pwm_freq(60)
        self.backwardMax = 350
        self.forwardMax = 300
        self.neutralbackandforth = 333
        self.rightMax= 397
        self.leftMax= 466
        self.neutralleftandright = 436
        #used to control eye lights via servo controllers. Workaround for lack of physical resources. Instead, probably implement like the error light in controller.py
        self.leftrightservo = 0
        self.forwardbackwardservo = 1
        self.leftEyeLed = 13
        self.rightEyeLed = 14

    #not actually to do with joystick. Workaround for lack of physical resources. Better solution is to buy more parts and implement like the error light in controller.py
    def showEyes(self, left, right):
        if left:
            self.pwm.set_pwm(self.leftEyeLed, 0, 4095)
        else:
            self.pwm.set_pwm(self.leftEyeLed, 0, 1)
        if right:
            self.pwm.set_pwm(self.rightEyeLed, 0, 4095)
        else:
            self.pwm.set_pwm(self.rightEyeLed, 0, 1)

    def reverse(self):
        self.pwm.set_pwm(self.leftrightservo, 0, self.neutralleftandright)
        self.pwm.set_pwm(self.forwardbackwardservo, 0, self.backwardMax)
        print("reverse")

    def stop(self):
        self.pwm.set_pwm(self.forwardbackwardservo, 0, self.neutralbackandforth)
        self.pwm.set_pwm(self.leftrightservo, 0, self.neutralleftandright)
        print("stop")

    def forward(self, x, y):
        print("x: ", x, " y: ", y)
        stopTurningUpperLimit = 0.01
        stopTurningLowerLimit = -0.01
        rightMaxPos = 0.08
        leftMaxPos = -0.08
        forwardStopCutoff = -0.09
        maxForwardCutoff = 0.01
        if x>stopTurningLowerLimit and x<stopTurningUpperLimit:
            self.pwm.set_pwm(self.leftrightservo, 0, self.neutralleftandright)
        elif x >= stopTurningUpperLimit:
            if x > rightMaxPos:
                self.pwm.set_pwm(self.leftrightservo, 0, self.rightMax)
                print("max right")
            else:
                rightPosDiff = rightMaxPos - stopTurningUpperLimit
                rightTickDiff = self.rightMax - self.neutralleftandright
                rightSlope = rightTickDiff/rightPosDiff
                rightB = self.rightMax - (rightSlope*rightMaxPos)
                rightTickPos = int(x*rightSlope + rightB)
                self.pwm.set_pwm(self.leftrightservo, 0, rightTickPos)
                #print( "x: ", x)
                #print( "TickPos: ", rightTickPos)
        else:
            if x < leftMaxPos:
                self.pwm.set_pwm(self.leftrightservo, 0, self.leftMax)
                print( "max left")
            else:
                leftPosDiff = leftMaxPos - stopTurningLowerLimit
                leftTickDiff = self.leftMax - self.neutralleftandright
                leftSlope = leftTickDiff/leftPosDiff
                leftB = self.leftMax - (leftSlope*leftMaxPos)
                leftTickPos = int(x*leftSlope + leftB)
                self.pwm.set_pwm(self.leftrightservo, 0, leftTickPos)
                #print( "x: ", x)
                #print( "TickPos: ", leftTickPos)
        #now calculates back and forth movement
        if y < forwardStopCutoff:
            self.pwm.set_pwm(self.forwardbackwardservo, 0, self.neutralbackandforth)
            print( "stop")
        else:
            if y > maxForwardCutoff:
                self.pwm.set_pwm(self.forwardbackwardservo, 0, self.forwardMax)
            else:
                forwardPosDiff = maxForwardCutoff - forwardStopCutoff
                forwardTickDiff = self.forwardMax - self.neutralbackandforth
                forwardSlope= forwardTickDiff/forwardPosDiff
                forwardB = self.forwardMax - (forwardSlope*maxForwardCutoff)
                forwardTickPos = int(y*forwardSlope + forwardB)
                self.pwm.set_pwm(self.forwardbackwardservo, 0, forwardTickPos)
                #print( "y: ", y)
                #print( "TickPos: ", forwardTickPos)

    def shutdown(self):
        self.pwm = None
        print("releasing PWM control")
        # x: 0 go straight
        #- means go left
        #+ means go right, -.5 to .5, be prepared for it to be outside that range or not up to it
        #y: same range, 0 doesnt mean anything -.2 stop .2 full speed 
        


if __name__ == "__main__":
    
    stick = Joystick()
