import cv2

img = cv2.imread("/Users/nikhil/Desktop/test.png",0)
#not needed since loads in B/W
#img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
thresh = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 3)
_, contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
cv2.imwrite("/Users/nikhil/Desktop/thresholded.png", thresh)
img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
cv2.drawContours(img, contours, -1, (0, 255, 0), 3)
cv2.imwrite("/Users/nikhil/Desktop/contoured.png", img)
print("done")
