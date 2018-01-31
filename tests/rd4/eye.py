import math

class Eye:
    def __init__(self, boxCenterX, boxCenterY, boxWidth, boxHeight, now):
        self.boxCenterX = boxCenterX
        self.boxCenterY = boxCenterY
        self.boxWidth = boxWidth
        self.boxHeight = boxHeight
        self.sumPupilX = 0
        self.sumPupilY = 0
        self.numPupil = 0
        self.lastOpen = now
        self.lastClosed = now
        self.lastFound = now
        self.lastDefOpen = now #noise reduced
        self.lastDefClosed = now #noise reduced
        self.lastDefOpenCounter = now
        self.lastDefClosedCounter = now
        self.created = now

        #magic numbers
        self.eyeGroupCenterMaxError = 80
        self.redFac = .6 # eye group reduction factor
        self.addFac = 1 - self.redFac # eye group addition factor
        self.noiseFramesPermitted = 3
        self.maxAveragePoints = 210

    def update_group1(self, x, y, w, h, now):
        if math.sqrt((x + w/2 - self.boxCenterX) ** 2 + (y + h/2 - self.boxCenterY) ** 2) <= self.eyeGroupCenterMaxError:
            self.boxCenterX = self.boxCenterX * self.redFac + (x + w/2) * self.addFac
            self.boxCenterY = self.boxCenterY * self.redFac + (y + h/2) * self.addFac
            self.boxWidth = self.boxWidth * self.redFac + w * self.addFac
            self.boxHeight = self.boxHeight * self.redFac + h * self.addFac
            self.lastFound = now
            return True
        return False

    def update_group2(self, cx, cy, now):
        if self.numPupil < self.maxAveragePoints:
            self.sumPupilX += cx
            self.sumPupilY += cy
            self.numPupil += 1
        else:
            self.sumPupilX = self.sumPupilX * (self.maxAveragePoints - 1) / self.numPupil + cx
            self.sumPupilY = self.sumPupilY * (self.maxAveragePoints - 1) / self.numPupil + cy
            self.numPupil = self.maxAveragePoints
        self.lastOpen = now
        self.lastDefOpenCounter += 1
        if self.lastDefOpenCounter > self.noiseFramesPermitted:
            self.lastDefOpen = now
        self.lastDefClosedCounter = 0

        ddx = -(cx - self.sumPupilX / self.numPupil) / self.boxWidth
        ddy = -(cy - self.sumPupilY / self.numPupil) / self.boxHeight
        return ddx, ddy

    def update_group3(self, now):
        if self.lastOpen != now:
            #was closed this frame
            self.lastClosed = now
            self.lastDefClosedCounter += 1
            if self.lastDefClosedCounter > self.noiseFramesPermitted:
                self.lastDefClosed = now
            self.lastDefOpenCounter = 0
