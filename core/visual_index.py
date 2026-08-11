import os
import json
import faiss
import numpy as np
import cv2

import config
from core.visual_encoder import VisualEncoder
from core.face_masker import mask_faces
from core.encoder import extract_faces
from core.video_processor import sample_video_frames

class VisualIndex:
    """Manages FAISS index for visual contextual similarity (Layer 3)."""
    
    def __init__(self, dimension=512, force_rebuild=False):
        # CLIP base patch32 produces 512-d embeddings
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(self.dimension)
        self.id_map = {}
        self.encoder = None # Lazy load
        
        if not force_rebuild:
            self.load()
            
    def _init_encoder(self):
        if self.encoder is None:
            print("[SWARAKSHA Layer 3] Initializing Visual Encoder (CLIP)...")
            self.encoder = VisualEncoder(config.CLIP_MODEL_NAME)
            
    def build_index(self):
        """Scans the VISUAL_REFERENCE_DIR and builds the FAISS index."""
        print("[SWARAKSHA Layer 3] Building Visual Index...")
        self._init_encoder()
        
        self.index = faiss.IndexFlatIP(self.dimension)
        self.id_map = {}
        
        if not os.path.exists(config.VISUAL_REFERENCE_DIR):
            return
            
        index_id = 0
        
        for root, _, files in os.walk(config.VISUAL_REFERENCE_DIR):
            for file in files:
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, config.VISUAL_REFERENCE_DIR).replace("\\", "/")
                ext = file.lower().split('.')[-1]
                
                if ext in ['jpg', 'jpeg', 'png', 'webp']:
                    index_id = self._index_image(filepath, rel_path, index_id)
                elif ext in ['mp4', 'mov', 'avi']:
                    index_id = self._index_video(filepath, rel_path, index_id)
                    
        self.save()
        print(f"[SWARAKSHA Layer 3] Visual Index built. Total items: {self.index.ntotal}")
        
    def _index_image(self, filepath, rel_path, start_id):
        img = cv2.imread(filepath)
        if img is None:
            return start_id
            
        # 1. Detect faces
        faces = extract_faces(img)
        # 2. Mask faces
        masked_img = mask_faces(img, faces)
        # 3. Generate embedding
        emb = self.encoder.encode_image(masked_img)
        
        # 4. Add to FAISS
        self.index.add(np.array([emb], dtype=np.float32))
        
        self.id_map[str(start_id)] = {
            "source_type": "image",
            "source_path": rel_path,
            "frame_number": None,
            "timestamp": None
        }
        return start_id + 1
        
    def _index_video(self, filepath, rel_path, start_id):
        # Sample frames
        for frame_data in sample_video_frames(filepath, config.VIDEO_SAMPLE_INTERVAL):
            frame = frame_data["frame"]
            faces = extract_faces(frame)
            masked_frame = mask_faces(frame, faces)
            emb = self.encoder.encode_image(masked_frame)
            
            self.index.add(np.array([emb], dtype=np.float32))
            
            self.id_map[str(start_id)] = {
                "source_type": "video",
                "source_path": rel_path,
                "frame_number": frame_data["frame_number"],
                "timestamp": frame_data["timestamp"]
            }
            start_id += 1
            
        return start_id

    def search(self, embedding, top_k=5, threshold=None):
        """Searches for similar visual contexts."""
        if self.index.ntotal == 0:
            return []
            
        threshold = threshold if threshold is not None else config.VISUAL_MATCH_THRESHOLD
        k = min(top_k, self.index.ntotal)
        
        embedding = np.asarray(embedding, dtype=np.float32).reshape(1, -1)
        similarities, indices = self.index.search(embedding, k)
        
        results = []
        for i in range(k):
            sim = float(similarities[0][i])
            faiss_idx = int(indices[0][i])
            
            if faiss_idx != -1 and sim >= threshold:
                map_entry = self.id_map.get(str(faiss_idx), {})
                results.append({
                    "similarity": sim,
                    "reference": map_entry
                })
                
        return results
        
    def save(self):
        os.makedirs(os.path.dirname(config.VISUAL_FAISS_INDEX_PATH), exist_ok=True)
        faiss.write_index(self.index, config.VISUAL_FAISS_INDEX_PATH)
        with open(config.VISUAL_FAISS_ID_MAP_PATH, 'w') as f:
            json.dump(self.id_map, f)
            
    def load(self):
        if os.path.exists(config.VISUAL_FAISS_INDEX_PATH):
            self.index = faiss.read_index(config.VISUAL_FAISS_INDEX_PATH)
        if os.path.exists(config.VISUAL_FAISS_ID_MAP_PATH):
            with open(config.VISUAL_FAISS_ID_MAP_PATH, 'r') as f:
                self.id_map = json.load(f)

# Global singleton
visual_index_manager = VisualIndex()
