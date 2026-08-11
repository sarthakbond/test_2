import os
import cv2
import numpy as np
from deepface import DeepFace
import config

def get_reference_image(reference_meta):
    """Retrieves the reference image (or video frame) as a numpy array."""
    filepath = os.path.join(config.VISUAL_REFERENCE_DIR, reference_meta["source_path"])
    if not os.path.exists(filepath):
        return None
        
    if reference_meta["source_type"] == "image":
        return cv2.imread(filepath)
    else:
        # Video: extract specific frame
        cap = cv2.VideoCapture(filepath)
        cap.set(cv2.CAP_PROP_POS_FRAMES, reference_meta["frame_number"] or 0)
        ok, frame = cap.read()
        cap.release()
        return frame if ok else None

def compare_faces(query_img, reference_img):
    """
    Compares faces in two images using DeepFace.
    Returns the similarity score (0.0 to 1.0).
    """
    if query_img is None or reference_img is None:
        return 0.0
        
    try:
        # Convert BGR to RGB for DeepFace
        q_rgb = cv2.cvtColor(query_img, cv2.COLOR_BGR2RGB)
        r_rgb = cv2.cvtColor(reference_img, cv2.COLOR_BGR2RGB)
        
        result = DeepFace.verify(
            img1_path=q_rgb,
            img2_path=r_rgb,
            model_name=config.FACE_MODEL,
            detector_backend=config.DETECTOR_BACKEND,
            enforce_detection=False,
            distance_metric=config.DISTANCE_METRIC
        )
        
        # DeepFace cosine distance is [0, 2]. Similarity is 1 - distance.
        # Note: If it uses cosine similarity internally, distance might be 1 - cosine.
        # But for cosine in DeepFace, distance = 1 - cos(theta)
        distance = result.get("distance", 1.0)
        similarity = max(0.0, 1.0 - distance)
        return similarity
    except Exception as e:
        print(f"[SWARAKSHA Layer 3] Face comparison error: {e}")
        return 0.0

def analyze_forensic_risk(identity_detected: bool, 
                          ai_detected: bool, 
                          context_match: bool, 
                          face_discrepancy: bool) -> str:
    """
    Rule-based risk engine to classify the forensic status.
    """
    if identity_detected and context_match and face_discrepancy:
        if ai_detected:
            return "HIGH_RISK_CONTENT"
        else:
            return "POSSIBLE_FACE_REPLACEMENT"
            
    if identity_detected and ai_detected and not context_match:
        return "POTENTIAL_AI_MANIPULATION"
        
    if identity_detected and context_match and not face_discrepancy:
        return "CONTEXT_MATCH_SAME_PERSON"
        
    if identity_detected and not ai_detected:
        return "NO_THREAT_DETECTED"
        
    return "UNKNOWN_STATUS"
