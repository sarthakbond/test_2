"""
 SWARAKSHA — FastAPI Backend
Endpoints for face registration, recognition, and AI-generated image detection.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import tempfile
import sys
import cv2
import numpy as np
from typing import List, Optional

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config
from core.encoder import generate_frame_embeddings, preload_models
from core.face_index import FaceIndex
from core.ai_detector import AIImageDetector
from db.database import DatabaseManager
from core.video_processor import extract_video_metadata, sample_video_frames
from core.metadata_analyzer import MetadataAnalyzer
from core.visual_index import visual_index_manager
from core.face_masker import mask_faces
from core.forensic_analyzer import compare_faces, get_reference_image, analyze_forensic_risk
from core.notifier import send_alert_email
from core.pose_estimator import estimate_pose

app = FastAPI(
    title="SWARAKSHA API",
    description="Face Registration, Recognition & AI Image Detection",
    version="2.0.0",
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global instances (initialized on startup) ──────────────────────────────

db: DatabaseManager = None
face_index: FaceIndex = None
ai_detector: AIImageDetector = None
metadata_analyzer: MetadataAnalyzer = None


@app.on_event("startup")
async def startup_event():
    global db, face_index, ai_detector, metadata_analyzer
    print("[SWARAKSHA] ═══════════════════════════════════════")
    print("[SWARAKSHA] Starting up...")

    # 1. Database
    print("[SWARAKSHA] Initializing database...")
    db = DatabaseManager()
    persons = db.list_persons()
    print(f"  ✓ Database ready — {len(persons)} registered person(s)")

    # 2. Face encoder models (RetinaFace + ArcFace)
    preload_models()

    # 3. FAISS face index
    print("[SWARAKSHA] Loading FAISS face index...")
    face_index = FaceIndex(db=db)
    print(f"  ✓ FAISS index ready — {face_index.total_embeddings} embedding(s)")

    # 4. AI Image Detector (downloads model on first run ~340MB)
    print("[SWARAKSHA] Loading AI Image Detector...")
    ai_detector = AIImageDetector()

    # 5. Metadata Forensics Analyzer (no model needed)
    print("[SWARAKSHA] Initializing Metadata Forensics Analyzer...")
    metadata_analyzer = MetadataAnalyzer()
    print("  ✓ Metadata Analyzer ready")

    # 6. Visual Index (Layer 3)
    visual_index_manager.build_index()

    print("[SWARAKSHA] ═══════════════════════════════════════")
    print("[SWARAKSHA] All systems operational!")
    print("[SWARAKSHA] ═══════════════════════════════════════")


# ── Helper ──────────────────────────────────────────────────────────────────

def _decode_image(contents: bytes) -> np.ndarray:
    """Decode uploaded file bytes into a BGR numpy array."""
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image file — could not decode.")
    return img


# ── Response Models ─────────────────────────────────────────────────────────

class PersonResponse(BaseModel):
    person_id: str
    name: str
    email: Optional[str] = None
    created_at: Optional[str] = None
    image_count: int = 0

class AutoCaptureResponse(BaseModel):
    captured: bool
    pose: Optional[str] = None
    reason: Optional[str] = None


class RegisterResponse(BaseModel):
    message: str
    person_id: str
    name: str
    faces_registered: int
    total_embeddings: int


class FaceMatch(BaseModel):
    person_id: str
    name: str
    similarity: float
    similarity_percent: float
    bbox: dict  # {x, y, w, h}


class RecognizeResponse(BaseModel):
    faces_detected: int
    matches: List[FaceMatch]
    unmatched_faces: int


class ScanFaceResult(BaseModel):
    person_id: Optional[str] = None
    name: Optional[str] = None
    similarity: Optional[float] = None
    bbox: dict
    ai_check: Optional[dict] = None
    action: str  # "BLOCK" or "ALLOW"
    reason: str


class ScanResponse(BaseModel):
    faces_detected: int
    results: List[ScanFaceResult]
    overall_action: str  # "BLOCK" if any face is flagged, "ALLOW" otherwise
    summary: str
    metadata_forensics: Optional[dict] = None


class VideoMetadata(BaseModel):
    duration: float
    fps: float
    total_frames: int
    sampled_frames: int

class VideoIdentityResult(BaseModel):
    protected_identity_detected: bool
    person_ids: List[str]
    frames_with_identity: int
    identity_frame_ratio: float

class VideoAIAnalysis(BaseModel):
    frames_analyzed: int
    frames_flagged: int
    flagged_frame_ratio: float
    aggregate_score: float
    status: str

class VideoFrameAIResult(BaseModel):
    performed: bool
    result: Optional[str] = None
    score: Optional[float] = None
    reason: Optional[str] = None
    error: Optional[str] = None

class VideoFrameIdentityMatch(BaseModel):
    person_id: str
    similarity: float

class VideoFrameResult(BaseModel):
    frame_number: int
    timestamp: float
    faces_detected: int
    identity_matches: List[VideoFrameIdentityMatch]
    protected_identity_detected: bool
    ai_analysis: VideoFrameAIResult

class Layer3Match(BaseModel):
    query_frame: int
    query_timestamp: float
    reference: dict
    context_similarity: float
    face_similarity: float
    face_discrepancy: bool

class Layer3Result(BaseModel):
    performed: bool
    query_frames: int = 0
    visual_matches_found: int = 0
    strong_matches: int = 0
    context_discrepancies: int = 0
    status: str = "NOT_ANALYZED"
    matches: List[Layer3Match] = []

class VideoScanDetailedResponse(BaseModel):
    video: VideoMetadata
    identity: VideoIdentityResult
    ai_analysis: VideoAIAnalysis
    final_status: str
    frames: List[VideoFrameResult]
    summary: str
    metadata_forensics: Optional[dict] = None
    layer_3: Optional[Layer3Result] = None


# ── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/")
def health_check():
    """Health check endpoint."""
    return {
        "status": "SWARAKSHA API is running",
        "version": "2.0.0",
        "registered_persons": len(db.list_persons()) if db else 0,
        "total_embeddings": face_index.total_embeddings if face_index else 0,
    }


@app.post("/api/register", response_model=RegisterResponse)
async def register_person(
    person_id: str = Form(...),
    name: str = Form(...),
    email: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
):
    """
    Register a person's identity by uploading one or more face photos.
    Multiple photos from different angles improve recognition accuracy.
    """
    if not files:
        raise HTTPException(status_code=400, detail="At least one image file is required.")

    # Create person in database (or skip if already exists)
    try:
        db.add_person(person_id, name, email)
    except ValueError:
        # Person already exists — we'll just add more images
        pass

    faces_registered = 0

    for file in files:
        contents = await file.read()
        img = _decode_image(contents)

        # Detect faces and generate embeddings
        faces = generate_frame_embeddings(img)
        if not faces:
            continue  # Skip images with no face detected

        # Take the primary (highest confidence) face from each image
        emb = faces[0]["embedding"]
        image_name = file.filename or "unknown"

        # Add to FAISS index + database
        face_index.add(person_id, emb, image_name)
        faces_registered += 1

    if faces_registered == 0:
        raise HTTPException(
            status_code=400,
            detail="No faces could be detected in any of the uploaded images.",
        )

    return RegisterResponse(
        message=f"Successfully registered {faces_registered} face(s) for '{name}'.",
        person_id=person_id,
        name=name,
        faces_registered=faces_registered,
        total_embeddings=face_index.total_embeddings,
    )

@app.post("/api/auto-capture", response_model=AutoCaptureResponse)
async def auto_capture(
    requested_pose: str = Form(...),
    file: UploadFile = File(...)
):
    """Analyze a frame and return whether it matches the requested pose."""
    contents = await file.read()
    img = _decode_image(contents)
    
    detected_pose = estimate_pose(img)
    
    if not detected_pose:
        return AutoCaptureResponse(captured=False, reason="No face detected or landmarks missing")
        
    prompt_to_pose = {
        "Look straight at the camera": ["straight"],
        "Turn head slightly Left": ["left", "right"],
        "Turn head slightly Right": ["right", "left"],
        "Tilt head slightly Up": ["up"],
        "Tilt head slightly Down": ["down"],
        "Scan Complete - Ready to save": ["straight"]
    }
    
    expected = prompt_to_pose.get(requested_pose, ["straight"])
    
    if detected_pose in expected:
        return AutoCaptureResponse(captured=True, pose=detected_pose)
    else:
        return AutoCaptureResponse(captured=False, pose=detected_pose, reason=f"Expected {expected}, got {detected_pose}")



@app.post("/api/recognize", response_model=RecognizeResponse)
async def recognize_faces(file: UploadFile = File(...)):
    """
    Upload an image to recognize all registered persons in it.
    Works with single or multiple faces in the same image.
    """
    contents = await file.read()
    img = _decode_image(contents)

    # Detect all faces
    faces = generate_frame_embeddings(img)
    if not faces:
        return RecognizeResponse(faces_detected=0, matches=[], unmatched_faces=0)

    matches = []
    unmatched = 0

    for face_data in faces:
        emb = face_data["embedding"]
        area = face_data["facial_area"]

        # Search FAISS index
        search_results = face_index.search(emb, k=1)

        if search_results:
            best = search_results[0]
            person = db.get_person(best["person_id"])
            person_name = person["name"] if person else best["person_id"]

            matches.append(FaceMatch(
                person_id=best["person_id"],
                name=person_name,
                similarity=round(best["similarity"], 4),
                similarity_percent=round(max(0.0, best["similarity"]) * 100, 2),
                bbox=area,
            ))
        else:
            unmatched += 1

    return RecognizeResponse(
        faces_detected=len(faces),
        matches=matches,
        unmatched_faces=unmatched,
    )


def _scan_frame(img: np.ndarray) -> ScanResponse:
    """
    Full protection scan: recognize faces AND check for AI-generated content.
    If a registered person's face is detected in an AI-generated image, it's BLOCKED.
    """
    # Detect all faces
    faces = generate_frame_embeddings(img)
    if not faces:
        return ScanResponse(
            faces_detected=0,
            results=[],
            overall_action="ALLOW",
            summary="No faces detected in the image.",
        )

    results = []
    any_blocked = False

    for face_data in faces:
        emb = face_data["embedding"]
        area = face_data["facial_area"]

        # Search FAISS for identity match
        search_results = face_index.search(emb, k=1)

        if not search_results:
            # Unknown face — no identity match, skip AI check
            results.append(ScanFaceResult(
                bbox=area,
                action="ALLOW",
                reason="Face not in protected database — no match found.",
            ))
            continue

        best = search_results[0]
        person = db.get_person(best["person_id"])
        person_name = person["name"] if person else best["person_id"]

        # Identity matched! Now crop the face and run AI detection.
        x, y, w, h = area.get('x', 0), area.get('y', 0), area.get('w', 0), area.get('h', 0)

        # Add some padding around the crop for better AI detection
        pad = int(max(w, h) * 0.2)
        img_h, img_w = img.shape[:2]
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(img_w, x + w + pad)
        y2 = min(img_h, y + h + pad)
        face_crop = img[y1:y2, x1:x2]

        ai_result = ai_detector.analyze(face_crop)

        if ai_result["is_ai"]:
            any_blocked = True
            results.append(ScanFaceResult(
                person_id=best["person_id"],
                name=person_name,
                similarity=round(best["similarity"], 4),
                bbox=area,
                ai_check=ai_result,
                action="BLOCK",
                reason=f"⚠️ ALERT: AI-generated image of protected person '{person_name}' detected! "
                       f"(AI confidence: {ai_result['ai_confidence']:.1%})",
            ))
        else:
            results.append(ScanFaceResult(
                person_id=best["person_id"],
                name=person_name,
                similarity=round(best["similarity"], 4),
                bbox=area,
                ai_check=ai_result,
                action="ALLOW",
                reason=f"Protected person '{person_name}' identified. Image passed authenticity check.",
            ))

    blocked_count = sum(1 for r in results if r.action == "BLOCK")
    overall = "BLOCK" if any_blocked else "ALLOW"

    if any_blocked:
        summary = f"🚨 BLOCKED: {blocked_count} AI-generated face(s) of protected person(s) detected!"
    else:
        summary = f"✅ CLEAR: {len(faces)} face(s) analyzed. No AI manipulation detected."

    return ScanResponse(
        faces_detected=len(faces),
        results=results,
        overall_action=overall,
        summary=summary,
    )


@app.post("/api/scan", response_model=ScanResponse)
async def scan_image(file: UploadFile = File(...)):
    """Scan one uploaded image for protected identities and manipulation."""
    contents = await file.read()
    img = _decode_image(contents)
    result = _scan_frame(img)

    # Run metadata forensics on the uploaded file bytes
    try:
        meta_result = metadata_analyzer.analyze_image_bytes(contents, filename=file.filename or "image.jpg")
        print(f"[METADATA] Image scan: {meta_result['confidence']} confidence, {len(meta_result['flags'])} flag(s)")
        for flag in meta_result['flags']:
            print(f"  → {flag}")
        result.metadata_forensics = meta_result

        # If metadata strongly suggests AI but the model missed it, upgrade the action
        if meta_result['confidence'] == 'high' and result.overall_action == 'ALLOW':
            has_protected = any(r.person_id for r in result.results)
            if has_protected:
                result.overall_action = 'BLOCK'
                result.summary += " ⚠️ Metadata forensics detected strong AI-generation markers."
    except Exception as e:
        print(f"[METADATA] Error during metadata analysis: {e}")

    return result


@app.post("/api/scan-video", response_model=VideoScanDetailedResponse)
async def scan_video(file: UploadFile = File(...)):
    """Sample an uploaded video and scan each sampled frame."""
    suffix = os.path.splitext(file.filename or "upload.mp4")[1] or ".mp4"
    valid_extensions = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
    if suffix.lower() not in valid_extensions:
        raise HTTPException(status_code=400, detail="Unsupported video format.")
        
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(await file.read())
            temp_path = temp_file.name

        print(f"[VIDEO] Received video: {file.filename}")
        
        # 0. Metadata Forensics on the video file
        video_meta_forensics = None
        try:
            video_meta_forensics = metadata_analyzer.analyze_video_file(temp_path)
            print(f"[METADATA] Video scan: {video_meta_forensics['confidence']} confidence, {len(video_meta_forensics['flags'])} flag(s)")
            for flag in video_meta_forensics['flags']:
                print(f"  → {flag}")
        except Exception as e:
            print(f"[METADATA] Error during video metadata analysis: {e}")

        # 1. Video Metadata
        try:
            metadata = extract_video_metadata(temp_path)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid or corrupted video: {e}")
            
        print(f"[VIDEO] Duration: {metadata['duration']} sec, FPS: {metadata['fps']}")
        
        sample_interval = getattr(config, 'VIDEO_SAMPLE_INTERVAL', 2.0)
        print(f"[VIDEO] Sampling every {sample_interval} sec")

        # 2. Extract Sampled Frames
        sampled_frames = list(sample_video_frames(temp_path, sample_interval))
        print(f"[VIDEO] Sampled {len(sampled_frames)} frames")

        frames_results = []
        relevant_frames = [] # Tuples of (frame_result, list of protected face crops)
        person_ids_detected = set()

        # 3. Face Detection & Identity Matching (Layer 1)
        for frame_data in sampled_frames:
            frame_num = frame_data["frame_number"]
            timestamp = frame_data["timestamp"]
            frame_img = frame_data["frame"]
            
            # Detect faces
            faces = generate_frame_embeddings(frame_img)
            print(f"[FACE] Frame {frame_num}: {len(faces)} faces")
            
            identity_matches = []
            protected_detected = False
            protected_face_crops = []
            
            if faces:
                for face in faces:
                    emb = face["embedding"]
                    area = face["facial_area"]
                    search_results = face_index.search(emb, k=1)
                    
                    if search_results:
                        best = search_results[0]
                        sim = best["similarity"]
                        pid = best["person_id"]
                        
                        identity_matches.append(VideoFrameIdentityMatch(
                            person_id=pid,
                            similarity=round(sim, 4)
                        ))
                        
                        protected_detected = True
                        person_ids_detected.add(pid)
                        print(f"[IDENTITY] Frame {frame_num}: {pid} similarity={sim:.4f}")
                        
                        # Crop face for potential AI analysis later
                        x, y, w, h = area.get('x', 0), area.get('y', 0), area.get('w', 0), area.get('h', 0)
                        pad = int(max(w, h) * 0.2)
                        img_h, img_w = frame_img.shape[:2]
                        x1 = max(0, x - pad)
                        y1 = max(0, y - pad)
                        x2 = min(img_w, x + w + pad)
                        y2 = min(img_h, y + h + pad)
                        protected_face_crops.append(frame_img[y1:y2, x1:x2])
                    else:
                        print(f"[IDENTITY] Frame {frame_num}: no registered match")
            
            frame_res = VideoFrameResult(
                frame_number=frame_num,
                timestamp=timestamp,
                faces_detected=len(faces),
                identity_matches=identity_matches,
                protected_identity_detected=protected_detected,
                ai_analysis=VideoFrameAIResult(performed=False, reason="NO_PROTECTED_IDENTITY")
            )
            frames_results.append(frame_res)
            
            if protected_detected:
                relevant_frames.append((frame_res, protected_face_crops, faces, frame_img))

        print(f"[VIDEO] Protected identity found in {len(relevant_frames)}/{len(sampled_frames)} frames")

        # 4. AI Detection (Layer 2) on Relevant Frames only
        flagged_frames_count = 0
        total_ai_scores = []
        
        for frame_res, crops in relevant_frames:
            print(f"[AI] Frame {frame_res.frame_number}: analyzing")
            frame_flagged = False
            max_score = 0.0
            
            for crop in crops:
                try:
                    ai_result = ai_detector.analyze(crop)
                    score = ai_result["ai_confidence"]
                    max_score = max(max_score, score)
                    if ai_result["is_ai"]:
                        frame_flagged = True
                except Exception as e:
                    frame_res.ai_analysis = VideoFrameAIResult(
                        performed=False,
                        error=str(e)
                    )
                    break
            else:
                # Loop completed without errors
                total_ai_scores.append(max_score)
                if frame_flagged:
                    flagged_frames_count += 1
                
                print(f"[AI] Frame {frame_res.frame_number}: score={max_score:.4f}")
                frame_res.ai_analysis = VideoFrameAIResult(
                    performed=True,
                    result="AI_GENERATED" if frame_flagged else "REAL",
                    score=round(max_score, 4)
                )

        # 5. Video-Level Aggregation
        frames_with_identity_count = len(relevant_frames)
        identity_ratio = frames_with_identity_count / len(sampled_frames) if sampled_frames else 0.0
        
        frames_analyzed = len(total_ai_scores)
        flagged_ratio = flagged_frames_count / frames_analyzed if frames_analyzed else 0.0
        
        # Calculate aggregate AI score (median)
        if total_ai_scores:
            aggregate_score = float(np.median(total_ai_scores))
        else:
            aggregate_score = 0.0
            
        print(f"[VIDEO] AI analysis completed: {frames_analyzed} frames")

        # --- LAYER 3: Visual Forensics ---
        l3_matches = []
        l3_query_frames = 0
        l3_strong_matches = 0
        l3_context_discrepancies = 0
        l3_status = "NOT_ANALYZED"

        if flagged_frames_count > 0:
            print("[SWARAKSHA] Layer 3 Context Check running for suspicious frames...")
            for frame_res, crops, faces, frame_img in relevant_frames:
                if frame_res.ai_analysis.result == "AI_GENERATED":
                    l3_query_frames += 1
                    # Mask protected faces in the query frame
                    masked_frame = mask_faces(frame_img, faces)
                    
                    # Generate visual embedding
                    visual_index_manager._init_encoder()
                    query_emb = visual_index_manager.encoder.encode_image(masked_frame)
                    
                    # Search FAISS index
                    search_results = visual_index_manager.search(query_emb, top_k=5)
                    
                    for match in search_results:
                        l3_strong_matches += 1
                        ref_meta = match["reference"]
                        # Get reference image to compare faces
                        ref_img = get_reference_image(ref_meta)
                        face_sim = compare_faces(frame_img, ref_img)
                        
                        # If face_sim is low (<0.4), it's a discrepancy!
                        discrepancy = face_sim < 0.4
                        if discrepancy:
                            l3_context_discrepancies += 1
                            
                        l3_matches.append(Layer3Match(
                            query_frame=frame_res.frame_number,
                            query_timestamp=frame_res.timestamp,
                            reference=ref_meta,
                            context_similarity=match["similarity"],
                            face_similarity=face_sim,
                            face_discrepancy=discrepancy
                        ))
                        
            if l3_matches:
                if l3_context_discrepancies > 0:
                    l3_status = "POSSIBLE_FACE_REPLACEMENT"
                else:
                    l3_status = "CONTEXT_MATCH_SAME_PERSON"
            else:
                l3_status = "NO_CONTEXT_MATCHES"
                
        layer_3_result = Layer3Result(
            performed=(l3_query_frames > 0),
            query_frames=l3_query_frames,
            visual_matches_found=len(l3_matches),
            strong_matches=l3_strong_matches,
            context_discrepancies=l3_context_discrepancies,
            status=l3_status,
            matches=l3_matches
        )

        # 6. Video Decision
        # Check if metadata forensics found strong AI markers
        meta_boost = (video_meta_forensics and video_meta_forensics.get('confidence') in ('medium', 'high'))
        
        has_context_discrepancy = layer_3_result.context_discrepancies > 0

        if frames_with_identity_count == 0:
            final_status = "NO_THREAT_DETECTED"
            ai_status = "NOT_ANALYZED"
            summary = f"CLEAR: {len(sampled_frames)} frame(s) sampled, no protected identity detected."
            if meta_boost:
                summary += " ⚠️ However, file metadata contains AI-generation markers."
        else:
            # ONLY flag POTENTIAL_AI_MANIPULATION if has_context_discrepancy is True.
            # (Identity AND AI manipulation AND Context Discrepancy)
            is_ai_detected = (flagged_ratio >= 0.3 or (flagged_frames_count > 0 and aggregate_score >= config.AI_DETECTOR_THRESHOLD) or meta_boost)
            
            if has_context_discrepancy and is_ai_detected:
                final_status = "HIGH_RISK_CONTENT"
                ai_status = "POTENTIAL_AI_MANIPULATION"
                reasons = ["Identity matched", "AI generation detected", "Context discrepancy confirmed"]
                summary = f"🚨 REVIEW REQUIRED: High Risk content detected. {', '.join(reasons)}."
                
                # TRIGGER EMAIL ALERT
                if person_ids_detected:
                    for pid in person_ids_detected:
                        person = db.get_person(pid)
                        if person and person.get('email'):
                            send_alert_email(person['email'], person['name'], file.filename, summary)
                            print(f"[SWARAKSHA] Triggered email alert to {person['email']}")
                            
            else:
                # If not all 3 flags trigger, we downgrade
                final_status = "REVIEW_REQUIRED" if (is_ai_detected or flagged_frames_count > 0) else "NO_THREAT_DETECTED"
                ai_status = "POTENTIAL_AI_MANIPULATION" if flagged_frames_count > 0 else "NO_STRONG_AI_EVIDENCE"
                
                if final_status == "REVIEW_REQUIRED":
                    summary = "⚠️ REVIEW REQUIRED: Some anomalies detected, but not all 3 flags were triggered."
                else:
                    summary = f"✅ CLEAR: Protected identity found in {frames_with_identity_count} frames. No strong evidence of multi-layer manipulation."
                
        print(f"[VIDEO] Final status: {final_status}")

        return VideoScanDetailedResponse(
            video=VideoMetadata(
                duration=metadata["duration"],
                fps=metadata["fps"],
                total_frames=metadata["total_frames"],
                sampled_frames=len(sampled_frames)
            ),
            identity=VideoIdentityResult(
                protected_identity_detected=(frames_with_identity_count > 0),
                person_ids=list(person_ids_detected),
                frames_with_identity=frames_with_identity_count,
                identity_frame_ratio=round(identity_ratio, 4)
            ),
            ai_analysis=VideoAIAnalysis(
                frames_analyzed=frames_analyzed,
                frames_flagged=flagged_frames_count,
                flagged_frame_ratio=round(flagged_ratio, 4),
                aggregate_score=round(aggregate_score, 4),
                status=ai_status
            ),
            final_status=final_status,
            summary=summary,
            frames=frames_results,
            metadata_forensics=video_meta_forensics,
            layer_3=layer_3_result
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/api/reverse-search")
async def reverse_image_search(file: UploadFile = File(...)):
    """Reverse search an image against the Layer 3 visual index."""
    contents = await file.read()
    img = _decode_image(contents)
    
    # Optional: Detect and mask faces to focus purely on context
    faces = generate_frame_embeddings(img)
    if faces:
        img = mask_faces(img, faces)
        
    visual_index_manager._init_encoder()
    query_emb = visual_index_manager.encoder.encode_image(img)
    search_results = visual_index_manager.search(query_emb, top_k=5)
    
    return {"matches": search_results}


@app.get("/api/persons", response_model=List[PersonResponse])
async def list_persons():
    """List all registered persons."""
    persons = db.list_persons()
    return [PersonResponse(**p) for p in persons]


@app.delete("/api/persons/{person_id}")
async def delete_person(person_id: str):
    """Remove a registered person and all their face data."""
    person = db.get_person(person_id)
    if not person:
        raise HTTPException(status_code=404, detail=f"Person '{person_id}' not found.")

    removed = face_index.remove_person(person_id)

    return {
        "message": f"Successfully removed '{person['name']}' and {removed} face embedding(s).",
        "person_id": person_id,
    }
