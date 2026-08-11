from transformers import CLIPVisionModelWithProjection, CLIPImageProcessor
import torch
from PIL import Image
import numpy as np

class VisualEncoder:
    """
    Generates semantic visual embeddings for images using a pre-trained CLIP model.
    """
    def __init__(self, model_name="openai/clip-vit-base-patch32"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = CLIPImageProcessor.from_pretrained(model_name)
        self.model = CLIPVisionModelWithProjection.from_pretrained(model_name).to(self.device)
        self.model.eval()

    def encode_image(self, image):
        """
        Generates an L2-normalized visual embedding for the given image.
        
        Args:
            image: numpy array (BGR from OpenCV) or PIL Image.
            
        Returns:
            numpy array of the visual embedding (e.g., 512 dimensions for CLIP base).
        """
        if isinstance(image, np.ndarray):
            # Convert BGR (OpenCV) to RGB (PIL)
            image = Image.fromarray(image[..., ::-1])
            
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            embeds = outputs.image_embeds
            # L2 Normalize
            embeds = embeds / embeds.norm(p=2, dim=-1, keepdim=True)
            
        return embeds.cpu().numpy()[0]
