# Display webcam or video
# Adds a mask to the video for detecting apriltags
# see https://pyimagesearch.com/2020/11/02/apriltag-with-python/
# but for windows needed robotpy_apriltag instead of apriltag
# see https://robotpy.readthedocs.io/projects/apriltag/en/latest/robotpy_apriltag.html
# and https://github.com/robotpy/examples/blob/main/AprilTagsVision/vision.py
import cv2
import robotpy_apriltag as apriltag
import numpy as np

# Instantiate once
tags = []  # The list where the tags will be stored
outlineColor = (0, 255, 0)  # Color of Tag Outline
crossColor = (0, 0, 255)  # Color of Cross
image = np.zeros((480, 640, 3), dtype=np.uint8)
grayImage = np.zeros(shape=(480, 640), dtype=np.uint8)

# load the input image and convert it to grayscale
print("[INFO] loading image...")
image = cv2.imread("images/kitchenApriltags.jpg")
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY, dst=grayImage)

# define the AprilTags detector options and then detect AprilTags
print("[INFO] detecting AprilTags...")
# There are six april tag families: Tag36h11, TagStandard41h12
# TagStandard52h13, TagCircle21h7, TagCircle49h12, TagCustom48h12
# Tag36h11 is most common
detector = apriltag.AprilTagDetector()
detector.addFamily("tag36h11")

detections = detector.detect(gray)

print("[INFO] {} total AprilTags detected".format(len(detections)))

# loop over the AprilTag detection results
tagNum = 1
for detection in detections:
	# Remember the tag we saw
    tags.append(detection.getId())

    # Draw lines around the tag
    for i in range(4):
        j = (i + 1) % 4
        point1 = (int(detection.getCorner(i).x), int(detection.getCorner(i).y))
        point2 = (int(detection.getCorner(j).x), int(detection.getCorner(j).y))
        image = cv2.line(image, point1, point2, outlineColor, 2)

    # Mark the center of the tag
    cx = int(detection.getCenter().x)
    cy = int(detection.getCenter().y)
    ll = 10
    image = cv2.line(
        image,
        (cx - ll, cy),
        (cx + ll, cy),
        crossColor,
        2,
    )
    image = cv2.line(
        image,
        (cx, cy - ll),
        (cx, cy + ll),
        crossColor,
        2,
    )

    # Identify the tag
    image = cv2.putText(
        image,
        str(tagNum),
        (cx + ll, cy),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        crossColor,
        3,
    )

    tagNum += 1

# show the output image after AprilTag detection
cv2.imshow("Image", image)
cv2.waitKey(0)