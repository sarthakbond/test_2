import numpy as np
import cv2
from retinaface import RetinaFace

def estimate_pose(img: np.ndarray) -> str:
    """
    Detects the face in the image and returns its pose:
    'straight', 'left', 'right', 'up', 'down', or None if no face.
    """
    # Convert BGR to RGB for RetinaFace
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    try:
        faces = RetinaFace.detect_faces(rgb_img)
    except Exception:
        return None
        
    if not isinstance(faces, dict) or len(faces) == 0:
        return None
        
    # Get the first face (usually face_1)
    face_key = list(faces.keys())[0]
    face_data = faces[face_key]
    
    if "landmarks" not in face_data:
        return None
        
    landmarks = face_data["landmarks"]
    
    re = landmarks.get("right_eye")
    le = landmarks.get("left_eye")
    n = landmarks.get("nose")
    rm = landmarks.get("mouth_right")
    lm = landmarks.get("mouth_left")
    
    if not all([re, le, n, rm, lm]):
        return None
        
    # Pitch (Up/Down)
    eye_y = (re[1] + le[1]) / 2.0
    mouth_y = (rm[1] + lm[1]) / 2.0
    
    nose_to_eye_y = n[1] - eye_y
    nose_to_mouth_y = mouth_y - n[1]
    
    pitch_ratio = nose_to_eye_y / nose_to_mouth_y if nose_to_mouth_y > 0 else 1.0
    
    # Yaw (Left/Right)
    # Right eye is on the left side of the image (lower X), Left eye is on the right side of the image (higher X)
    nose_to_re_x = n[0] - re[0]
    le_to_nose_x = le[0] - n[0]
    
    yaw_ratio = nose_to_re_x / le_to_nose_x if le_to_nose_x > 0 else 1.0
    
    print(f"[POSE] Pitch ratio: {pitch_ratio:.2f} | Yaw ratio: {yaw_ratio:.2f}")
    
    if yaw_ratio > 1.15:
        return "left"  # Looking left
    elif yaw_ratio < 0.85:
        return "right" # Looking right
    elif pitch_ratio < 0.85:
        return "up"    # Looking up
    elif pitch_ratio > 1.15:
        return "down"  # Looking down
        
    return "straight"
