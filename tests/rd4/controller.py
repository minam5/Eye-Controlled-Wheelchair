import RPi.GPIO as io
import time
from joystick import Joystick
from eye import Eye

class WheelChairController:

    def __init__(self):
        #channel numbers
        self.errorLightOut = 4
        self.errorLightLow = 18
        self.switchOut = 13
        self.switchDetect = 20

        #constants
        self.rs_stopped = 0
        self.rs_forward = 1
        self.rs_reverse = 2

        self.ss_nothing = 0 #nothing has happened yet
        self.ss_start = 1 #both eyes open complete
        self.ss_forward1 = 2 #one eye open complete
        self.ss_forward2 = 3 #both eyes closed complete
        self.ss_reverse1 = 4 #both eyes closed complete

        self.redFac = .75
        self.addFac = 1 - self.redFac

        self.maxSwitchTime = 7 #leave room for waiting and messing up
        self.maxReverseTime = 5

        self.defaultPrevX = 0
        self.defaultPrevY = -.5


        #vars
        self.runState = self.rs_stopped
        self.runTime = 0
        self.switchState = self.ss_nothing
        self.switchTime = 0
        self.prevX = self.defaultPrevX
        self.prevY = self.defaultPrevY

        self.joystick = Joystick()
        io.setmode(io.BCM)
        io.setup(self.errorLightOut, io.OUT, initial=io.LOW)
        io.setup(self.errorLightLow, io.OUT, initial=io.LOW)
        io.setup(self.switchOut, io.OUT, initial=io.HIGH)
        io.setup(self.switchDetect, io.IN, pull_up_down=io.PUD_DOWN)


        time.sleep(.2) #wait for io to definitely turn on before attempting to sense
        if self.should_shut_down():
            print("waiting for switch on")
            io.wait_for_edge(self.switchDetect, io.RISING) #wait for switch to turn on.
        self.set_led(io.HIGH) #indicate success
        time.sleep(.3) #wait so people know for sure that its working

    def sig_no_eye(self, now):
        #print("sig no eye")
        pass #probs just for debugging

    def sig_direction(self, x, y):
        #print("go ", x, ", ", y)
        self.prevX = self.prevX * self.redFac + x * self.addFac
        self.prevY = self.prevY * self.redFac + y * self.addFac
        if self.runState == self.rs_forward:
            self.joystick.forward(self.prevX, self.prevY)

    def sig_error_reset(self):
        #print("turn on error light")
        self.joystick.stop()
        self.set_led(io.HIGH)

    def sig_turn_off_error_light(self):
        self.set_led(io.LOW)

    def process_blink_commands(self, useGroups, now):
        temp = sorted(useGroups, key=lambda group: group.boxCenterX)
        eyes = len(useGroups)

        isLeft = True
        left = False
        right = False
        for group in temp:
            if group.lastOpen == now:
                if isLeft:
                    left = True
                    isLeft = False
                else:
                    right = True
        self.joystick.showEyes(left, right)

        counts1 = self.count_blinks(useGroups, 1, now) #be, bd, ne, nd

        if now - self.switchTime > self.maxSwitchTime and not (self.switchState == self.ss_start and counts1[3] == 2): # don't timeout if during start (because that would be confusing) if eyes are mostly open still
            if self.switchState != self.ss_nothing:
                print("canceled switch due to timeout")
            self.switchState = self.ss_nothing

        if (self.runState == self.rs_reverse and now - self.runTime > self.maxReverseTime) or eyes == 0:
            self.stop(now)
            print("no eye stop")
        elif eyes == 2: #other eyes == 1 case is just continue forward
            countsHalf = self.count_blinks(useGroups, .5, now)
            if self.runState == self.rs_forward:
                if counts1[3] < 2 or countsHalf[1] == 2: #not both ~open1 or both =closed.5
                    self.stop(now)
                    print("forward stop")
            elif self.runState == self.rs_reverse:
                if counts1[3] == 2 or countsHalf[1] == 2: #both ~open1 or both =closed.5
                    self.stop(now)
                    print("reverse stop")
            elif self.runState == self.rs_stopped:
                if self.switchState == self.ss_nothing:
                    if counts1[2] == 2: #both =open1
                        self.switchState = self.ss_start
                        print("ss_start")
                        self.switchTime = now
                    else:
                        print("still nothing")
                elif self.switchState == self.ss_start:
                    if counts1[0] == 2: #both =closed1
                        self.switchState = self.ss_reverse1
                        self.switchTime = now
                        print("ss_reverse1")
                    elif counts1[1] == 1 and counts1[3] == 1: #one ~open1, one ~closed1
                        self.switchState = self.ss_forward1
                        self.swtichTime = now
                        print("ss_forward1")
                    else:
                        print("still start")
                elif self.switchState == self.ss_reverse1:
                    if counts1[1] == 1 and counts1[3] == 1: #one ~open1, one ~closed1
                        self.start_reverse(now)
                    elif counts1[2] == 2: #both =open1
                        self.switchState = self.ss_start
                        self.switchTime = now
                        print("cancel")
                    else:
                        print("still reverse1")
                elif self.switchState == self.ss_forward1:
                    if counts1[0] == 2: #both =closed1
                        self.switchState = self.ss_forward2
                        self.switchTime = now
                        print("ss_forward2")
                    elif counts1[2] == 2: #both =open1
                        self.switchState = self.ss_start
                        self.switchTime = now
                        print("cancel")
                    else:
                        print("still forward1")
                elif self.switchState == self.ss_forward2:
                    if counts1[2] == 2: #both =open1
                        self.start_forward(now)
                    elif counts1[0] == 1 and counts1[2] == 1: #one =open1, one =closed1
                        self.switchState = self.ss_start
                        self.switchTime = now
                        print("cancel")
                    else:
                        print("still forward2")
                else:
                    #something went terribly wrong
                    print("aww nuts")
                    self.stop(now)
            else:
                #something went terribly wrong
                print("awww nutz")
                self.stop(now)

    def count_blinks(self, useGroups, timeReq, now):
        #return format: [blinking_exact, blinking_denoised, notBlinking_exact, notBlinking_denoised]
        be = sum((now - group.lastOpen) > timeReq for group in useGroups)
        bd = sum((now - group.lastDefOpen) > timeReq for group in useGroups)
        ne = sum((now - group.lastClosed) > timeReq for group in useGroups)
        nd = sum((now - group.lastDefClosed) > timeReq for group in useGroups)
        return [be, bd, ne, nd]

    def stop(self, now):
        self.runState = self.rs_stopped
        self.switchState = self.ss_nothing
        self.joystick.stop()
        self.runTime = now

    def start_forward(self, now):
        self.runState = self.rs_forward
        self.switchState = self.ss_nothing
        self.joystick.forward(self.prevX, self.prevY)
        self.runTime = now
        print("start forward")

    def start_reverse(self, now):
        self.runState = self.rs_reverse
        self.switchState = self.ss_nothing
        self.joystick.reverse()
        self.runTime = now
        print("start reverse")

    def should_shut_down(self):
        return io.input(self.switchDetect) == io.LOW

    def set_led(self, state):
        io.output(self.errorLightOut, state)

    def release_assets(self):
        print("releasing all assets")
        self.joystick.stop()
        self.joystick.shutdown()
        io.cleanup()
