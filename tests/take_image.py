import cv2
camera_port = 0
ramp_frames = 30
while True:
	camera = cv2.VideoCapture(camera_port)
	if camera:
		print(camera_port)
		break
	camera_port += 1

def get_image():
	return camera.read()[1]

for i in range(ramp_frames):
	temp = get_image()

print("taking for realz image")
camera_capture = get_image()
file = "/Users/nikhil/Desktop/test.png"
cv2.imwrite(file, camera_capture)
del(camera)
