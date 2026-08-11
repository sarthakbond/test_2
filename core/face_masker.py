import numpy as np
from PIL import Image

def mask_faces(image, faces, padding=0.2):
    """
    Masks the given faces in an image with black pixels.
    
    Args:
        image: Numpy array or PIL Image.
        faces: List of dictionaries or objects containing bounding box info.
               Expected format from DeepFace/RetinaFace: 
               {'facial_area': {'x': int, 'y': int, 'w': int, 'h': int}}
               or similar dictionaries with x, y, w, h keys.
        padding: Float indicating how much to expand the box relative to its size.
        
    Returns:
        Masked image in the same format as input (numpy array or PIL Image).
    """
    is_pil = isinstance(image, Image.Image)
    if is_pil:
        img_array = np.array(image)
    else:
        img_array = image.copy()
        
    height, width = img_array.shape[:2]
    
    for face in faces:
        if isinstance(face, dict) and 'facial_area' in face:
            area = face['facial_area']
            x, y, w, h = area.get('x', 0), area.get('y', 0), area.get('w', 0), area.get('h', 0)
        elif isinstance(face, dict) and all(k in face for k in ['x', 'y', 'w', 'h']):
            x, y, w, h = face['x'], face['y'], face['w'], face['h']
        elif isinstance(face, tuple) and len(face) == 4:
            x, y, w, h = face
        else:
            continue
            
        pad_x = int(w * padding)
        pad_y = int(h * padding)
        
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(width, x + w + pad_x)
        y2 = min(height, y + h + pad_y)
        
        img_array[y1:y2, x1:x2] = 0  # Fill with black
        
    if is_pil:
        return Image.fromarray(img_array)
    return img_array
