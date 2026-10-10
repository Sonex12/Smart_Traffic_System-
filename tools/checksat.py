"""
checksat.py - helps you choose SAT_MIN for config.py

Grabs one frame from the webcam (with the cars on the board), saves it as
frame.png, and saves a black-and-white mask for several saturation
thresholds (mask_70.png, mask_55.png, mask_40.png, mask_25.png).

Open the masks and pick the threshold where the cars show up as clean
white blobs and the road stays black. Put that number in config.py as
SAT_MIN.

Run from the main project folder:
    python3 tools/checksat.py
Close counter.py / smart_traffic.py first: only one program can use the
webcam at a time.
"""
import cv2, numpy as np

cap = cv2.VideoCapture(0)
for _ in range(10): ok, f = cap.read()   # skip the first frames while the camera adjusts
cap.release()
cv2.imwrite("frame.png", f)

s = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)[:,:,1]   # saturation channel
print("saturation: median", int(np.median(s)),
      " 99th pct", int(np.percentile(s,99)))

for t in (70, 55, 40, 25):
    m = cv2.inRange(s, t, 255)
    cv2.imwrite(f"mask_{t}.png", m)
    print(f"SAT_MIN {t}: {100*np.count_nonzero(m)/m.size:.1f}% of frame passes")
