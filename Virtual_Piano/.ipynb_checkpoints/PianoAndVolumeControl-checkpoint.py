import cv2
import numpy as np
import pygame
from pygame import mixer
import os
import handDetectorModule as htm

import time
import math

from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# Initialize pygame mixer for sound
pygame.init()
mixer.init()

# Define the path to the sounds directory
sounds_dir = 'tunes'

# Load sound files
white_key_files = ['a.wav', 's.wav', 'd.wav', 'f.wav', 'g.wav', 'h.wav', 'j.wav', 'k.wav', 'l.wav', ';.wav']
black_key_files = ['w.wav', 'e.wav', 't.wav', 'y.wav', 'u.wav', 'o.wav', 'p.wav']

white_key_sounds = [mixer.Sound(os.path.join(sounds_dir, file)) for file in white_key_files]
black_key_sounds = [mixer.Sound(os.path.join(sounds_dir, file)) for file in black_key_files]

# Function to draw piano keys
def draw_piano(image, white_key_width, black_key_width, black_key_height, highlighted_key=None, is_black=False):
    for i in range(10):
        x = i * white_key_width
        color = (0, 255, 0) if highlighted_key == i and not is_black else (255, 255, 255)
        cv2.rectangle(image, (x, 0), (x + white_key_width, height), color, -1)
        cv2.rectangle(image, (x, 0), (x + white_key_width, height), (0, 0, 0), 2)

    black_key_positions = [1, 2, 4, 5, 6, 8, 9]
    for pos in black_key_positions:
        x = pos * white_key_width - black_key_width // 2
        if x >= 0 and x + black_key_width <= width:
            color = (0, 255, 0) if highlighted_key == pos and is_black else (0, 0, 0)
            cv2.rectangle(image, (x, 0), (x + black_key_width, black_key_height), color, -1)

# Set dimensions and resolution
width = 650  # Example width 640 in cap.set
height = 300  # Example height 400 in cap.set
white_key_width = width // 10
black_key_width = int(white_key_width * 0.6)
black_key_height = int(height * 0.6)

# Start webcam capture
cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)

# Initialize hand detector
detector = htm.handDetector(detectionCon = 0.7)

devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(
    IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))
volRange = volume.GetVolumeRange()
minVol = volRange[0]
maxVol = volRange[1]
vol = 0
volBar = 400
volPer = 0

# Initialize variables for sound control
currently_playing_key = -1
last_key_index = None

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # Use the hand detector to find hands
    img_with_hands = detector.findHands(frame)
    lmList = detector.findPosition(img_with_hands)
    if len(lmList) != 0:
        x1, y1 = lmList[4][1], lmList[4][2]
        x2, y2 = lmList[8][1], lmList[8][2]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        cv2.circle(img_with_hands, (x1, y1), 10, (255, 0, 0), cv2.FILLED)
        cv2.circle(img_with_hands, (x2, y2), 10, (255, 0, 0), cv2.FILLED)
        cv2.line(img_with_hands, (x1, y1), (x2, y2), (255, 0, 0), 3)
        cv2.circle(img_with_hands, (cx, cy), 10, (255, 0, 0), cv2.FILLED)

        length = math.hypot(x2 - x1, y2 - y1)

        vol = np.interp(length, (20, 250), [minVol, maxVol])
        volBar = np.interp(length, (20, 250), [400, 150])
        volPer = np.interp(length, (20, 250), [0, 100])
        volume.SetMasterVolumeLevel(vol, None)

        if length < 50:
            cv2.circle(img_with_hands, (cx, cy), 10, (0, 255, 0), cv2.FILLED)

    # Create a blank piano image with the same dimensions as the camera frame
    piano_image = np.ones((height, width, 3), dtype=np.uint8) * 255

    # Calculate the position to center the piano horizontally at the top of the frame
    piano_x = (width - white_key_width * 10) // 2
    piano_y = 0  # Align piano at the top

    # Determine which key, if any, should be highlighted
    highlighted_key_index = None
    is_black_key = False

    if len(lmList) != 0:
        # Little finger tip (20)
        little_finger_tip = lmList[20][1:]  # Get the x, y coordinates
        # Thumb tip (4)
        thumb_tip = lmList[4][1:]

        # Determine if little finger is on a white or black key
        key_index = int((little_finger_tip[0] - piano_x) // white_key_width)
        is_black_key = (key_index in [1, 2, 4, 5, 6, 8, 9]) and (little_finger_tip[0] % white_key_width > (white_key_width - black_key_width) // 2)

        if 0 <= key_index < 10:
            # Highlight the key
            highlighted_key_index = key_index
            if is_black_key:
                black_key_index = [1, 2, 4, 5, 6, 8, 9].index(key_index)
                if currently_playing_key != black_key_index:
                    if currently_playing_key != -1 and last_key_index is not None:
                        white_key_sounds[last_key_index].stop()  # Stop the previous sound if needed
                    black_key_sounds[black_key_index].play()  # Play the new black key sound
                    currently_playing_key = black_key_index
                    last_key_index = None
            else:
                if currently_playing_key is not None:
                    black_key_sounds[currently_playing_key].stop()  # Stop the previous black key sound if needed
                if last_key_index != key_index:
                    white_key_sounds[key_index].play()  # Play the new white key sound
                    currently_playing_key = None
                    last_key_index = key_index

    # Draw the piano keys with highlighting
    draw_piano(piano_image, white_key_width, black_key_width, black_key_height, highlighted_key_index, is_black_key)

    # Overlay the piano image onto the frame
    overlay = img_with_hands.copy()
    overlay[piano_y:piano_y + height, piano_x:piano_x + width] = piano_image[piano_y:piano_y + height, piano_x:piano_x + width]

    bar_x, bar_y, bar_w, bar_h = 1000, 100, 50, 300
    color = (255, 0, 0)
    thickness = 2

    cv2.rectangle(overlay, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), color, thickness)
    cv2.rectangle(overlay, (bar_x, int(volBar)), (bar_x + bar_w, bar_y + bar_h), color, cv2.FILLED)
    cv2.putText(overlay, f'{int(volPer)}%', (1000, 450), cv2.FONT_HERSHEY_COMPLEX, 1, color, 3)
    
    # Display the image
    cv2.imshow("Piano and Webcam", overlay)

    # Exit on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release resources
cap.release()
cv2.destroyAllWindows()
pygame.quit()