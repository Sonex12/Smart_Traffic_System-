"""
checkarea.py - helps you choose MIN_AREA for config.py

Grabs one frame from the webcam, applies the SAT_MIN from config.py, and
prints the size (in pixels) of the largest blobs it finds. With cars on the
board, those blobs are your cars.

Set MIN_AREA to about half the size of the smallest car blob.

Run from the main project folder:
    python3 tools/checkarea.py
Close counter.py / smart_traffic.py first: only one program can use the
webcam at a time.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # so config.py is found

import cv2, numpy as np, config

cap = cv2.VideoCapture(0)
for _ in range(10): ok, f = cap.read()   # skip the first frames while the camera adjusts
cap.release()

print("config says SAT_MIN =", config.SAT_MIN, " MIN_AREA =", config.MIN_AREA)
s = cv2.cvtColor(f, cv2.COLOR_BGR2HSV)[:,:,1]
m = cv2.inRange(s, config.SAT_MIN, 255)
m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5,5), np.uint8))
cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print("blob sizes:", sorted(int(cv2.contourArea(c)) for c in cnts)[-12:])
