"""
Standalone helper to find good HSV thresholds for YOUR cones under
YOUR lighting. Point the camera at one cone at a time, drag the
trackbars until only that cone is white in the mask window, then
copy the printed values into config.py's COLOR_RANGES.

Run:
    python tools/hsv_tuner.py
"""
import cv2
import numpy as np


def nothing(x):
    pass


def main():
    cap = cv2.VideoCapture(0)
    cv2.namedWindow("Trackbars")
    cv2.createTrackbar("H Min", "Trackbars", 0, 179, nothing)
    cv2.createTrackbar("H Max", "Trackbars", 179, 179, nothing)
    cv2.createTrackbar("S Min", "Trackbars", 70, 255, nothing)
    cv2.createTrackbar("S Max", "Trackbars", 255, 255, nothing)
    cv2.createTrackbar("V Min", "Trackbars", 70, 255, nothing)
    cv2.createTrackbar("V Max", "Trackbars", 255, 255, nothing)

    print("Adjust trackbars until only your cone shows up white in the Mask window.")
    print("Press ESC to quit and print the final values.")

    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        frame = cv2.flip(frame, 1)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        h_min = cv2.getTrackbarPos("H Min", "Trackbars")
        h_max = cv2.getTrackbarPos("H Max", "Trackbars")
        s_min = cv2.getTrackbarPos("S Min", "Trackbars")
        s_max = cv2.getTrackbarPos("S Max", "Trackbars")
        v_min = cv2.getTrackbarPos("V Min", "Trackbars")
        v_max = cv2.getTrackbarPos("V Max", "Trackbars")

        lower = np.array([h_min, s_min, v_min])
        upper = np.array([h_max, s_max, v_max])
        mask = cv2.inRange(hsv, lower, upper)
        result = cv2.bitwise_and(frame, frame, mask=mask)

        cv2.imshow("Camera", frame)
        cv2.imshow("Mask", mask)
        cv2.imshow("Result", result)

        if cv2.waitKey(1) & 0xFF == 27:
            print(f"\nLower: ({h_min}, {s_min}, {v_min})")
            print(f"Upper: ({h_max}, {s_max}, {v_max})")
            print(f'Paste into config.py, e.g.: [(({h_min}, {s_min}, {v_min}), ({h_max}, {s_max}, {v_max}))]')
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
