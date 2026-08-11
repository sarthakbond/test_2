import os
import cv2
import numpy as np

def create_test_dataset(output_dir="reference_visuals"):
    """
    Creates a simple mock dataset to test Layer 3 Contextual Matching.
    Creates 2 dummy images in reference_visuals/
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a synthetic image 1: Solid blue background with a white "face" circle
    img1 = np.zeros((400, 400, 3), dtype=np.uint8)
    img1[:] = (255, 0, 0) # Blue background
    cv2.circle(img1, (200, 200), 50, (255, 255, 255), -1) # White circle for face
    cv2.putText(img1, "Reference 1", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Create synthetic image 2: Solid green background with a white "face" circle
    img2 = np.zeros((400, 400, 3), dtype=np.uint8)
    img2[:] = (0, 255, 0) # Green background
    cv2.circle(img2, (200, 200), 50, (255, 255, 255), -1) # White circle for face
    cv2.putText(img2, "Reference 2", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    cv2.imwrite(os.path.join(output_dir, "test_ref_blue.jpg"), img1)
    cv2.imwrite(os.path.join(output_dir, "test_ref_green.jpg"), img2)
    
    print(f"Created 2 mock reference images in {output_dir}/")
    print("Restart the Swaraksha backend to index these visual references.")

if __name__ == "__main__":
    create_test_dataset()
