# SWARAKSHA — Layer 3: Visual Forensics

Layer 3 provides an advanced counter-forensic capability to detect sophisticated DeepFakes where the attacker has taken an existing non-consensual image/video of another person and face-swapped the protected person's face onto it.

In these attacks, Layer 1 (Identity Detection) correctly identifies the protected person. Layer 2 (AI Detection) correctly identifies the face as AI-generated. However, proving *malice* and *source manipulation* requires finding the original unmanipulated source material.

## How it Works (Context Matching)

1. **Evidence Repository**: SWARAKSHA maintains a local `reference_visuals/` directory containing known adult content, template videos, or specific visual contexts often used by attackers.
2. **Visual Indexing**: A background process scans this directory, extracts and *masks* all faces (replacing them with black pixels), and generates a 512-dimensional semantic embedding of the *background and context* using OpenAI's CLIP model. These embeddings are stored in a FAISS vector database.
3. **Trigger**: When a video scan flags a frame as both containing a protected identity (Layer 1) and being AI-manipulated (Layer 2), Layer 3 is triggered.
4. **Suspicious Frame Masking**: The protected face in the suspicious frame is masked out.
5. **Context Retrieval**: The masked suspicious frame is embedded using CLIP and compared against the FAISS visual index.
6. **Discrepancy Check**: If a strong context match is found (high visual similarity), the system then performs a direct face comparison between the suspicious frame and the original reference frame.
7. **Flagging**: If the contexts match but the faces are completely different (low face similarity), a `POSSIBLE_FACE_REPLACEMENT` discrepancy is flagged, providing concrete evidence of a face-swap attack.

## Architecture

- `core/visual_encoder.py`: Wraps `openai/clip-vit-base-patch32` for image embedding.
- `core/visual_index.py`: Manages the FAISS index for fast similarity search across reference material.
- `core/face_masker.py`: Handles bounding box extraction and pixel masking for both DeepFace and RetinaFace outputs.
- `core/forensic_analyzer.py`: The risk engine that computes discrepancies between context similarity and face similarity.

This layer runs entirely locally, preserving privacy while delivering powerful forensic evidence.
