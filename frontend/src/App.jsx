import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Activity, ArrowLeft, Camera, Check, FileVideo, FolderOpen, ImagePlus, LayoutDashboard, LoaderCircle, ScanFace, Shield, ShieldAlert, Sparkles, Trash2, UploadCloud, UserRound, Users, X, Eye, Image, Search } from 'lucide-react';
import './index.css';

const hostname = window.location.hostname || 'localhost';
const API_ROOT = `http://${hostname}:8000`;
const API_BASE = `${API_ROOT}/api`;

function App() {
  const [mode, setMode] = useState('start');
  const [backendOnline, setBackendOnline] = useState(false);
  const [cameraError, setCameraError] = useState('');
  const [stream, setStream] = useState(null);
  const [capturedFile, setCapturedFile] = useState(null);
  const [capturedFiles, setCapturedFiles] = useState([]);
  const [scanResult, setScanResult] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [referenceFiles, setReferenceFiles] = useState([]);
  const [personId, setPersonId] = useState('');
  const [personName, setPersonName] = useState('');
  const [personEmail, setPersonEmail] = useState('');
  const [registerResult, setRegisterResult] = useState(null);
  const [isRegistering, setIsRegistering] = useState(false);
  const [progress, setProgress] = useState(null);
  const [persons, setPersons] = useState([]);
  const [recentAdds, setRecentAdds] = useState({});
  const [videoFiles, setVideoFiles] = useState([]);
  const [videoResults, setVideoResults] = useState([]);
  const [isVideoScanning, setIsVideoScanning] = useState(false);
  const [activityLog, setActivityLog] = useState(['Waiting for an action.']);
  const [registrationNotice, setRegistrationNotice] = useState('');
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  useEffect(() => {
    axios.get(API_ROOT).then(() => setBackendOnline(true)).catch(() => setBackendOnline(false));
    axios.get(`${API_BASE}/persons`).then((response) => setPersons(response.data)).catch(() => {});
  }, []);

  useEffect(() => () => stream?.getTracks().forEach((track) => track.stop()), [stream]);

  const startCamera = async () => {
    setMode('live-register'); setCameraError(''); setScanResult(null); setCapturedFile(null); setCapturedFiles([]); setRegisterResult(null);
    try {
      const nextStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false });
      setStream(nextStream);
      if (videoRef.current) videoRef.current.srcObject = nextStream;
    } catch (error) {
      setCameraError(error.name === 'NotAllowedError' ? 'Camera access was blocked. Allow camera access in your browser, then try again.' : 'We could not open your camera. You can still upload an image below.');
    }
  };

  useEffect(() => {
    if (videoRef.current && stream) videoRef.current.srcObject = stream;
  }, [stream]);

  const stopCamera = () => { stream?.getTracks().forEach((track) => track.stop()); setStream(null); };
  const goHome = () => { stopCamera(); setMode('start'); setCapturedFile(null); setScanResult(null); setCameraError(''); setCapturedFiles([]); };
  const log = (message) => setActivityLog((current) => [...current.slice(-5), `${new Date().toLocaleTimeString()}  ${message}`]);

  const deletePerson = async (personId) => {
    const person = persons.find((item) => item.person_id === personId);
    if (!person || !window.confirm(`Remove ${person.name} and all stored face references?`)) return;
    try { await axios.delete(`${API_BASE}/persons/${personId}`); setPersons((current) => current.filter((item) => item.person_id !== personId)); log(`Removed protected identity: ${person.name}.`); }
    catch (error) { log(`Delete failed: ${error.response?.data?.detail || error.message}`); }
  };

  const captureFace = () => {
    const video = videoRef.current; const canvas = canvasRef.current;
    if (!video || !canvas || !video.videoWidth) return;
    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => setCapturedFiles((current) => [...current, new File([blob], `camera-capture-${Date.now()}.jpg`, { type: 'image/jpeg' })]), 'image/jpeg', .92);
  };

  const scanImage = async (event) => {
    event?.preventDefault(); if (!capturedFile || isScanning) return;
    setIsScanning(true); setScanResult(null); setProgress({ label: 'Uploading image', value: 20 }); log('Upload received.');
    const progressTimer = setInterval(() => setProgress((current) => current && current.value < 85 ? { label: current.value < 45 ? 'Detecting faces' : current.value < 70 ? 'Matching identities' : 'Checking authenticity', value: current.value + 5 } : current), 800);
    const formData = new FormData(); formData.append('file', capturedFile);
    try { log('Detecting faces and matching identities...'); const response = await axios.post(`${API_BASE}/scan`, formData); setScanResult(response.data); setProgress({ label: 'Scan complete', value: 100 }); log('Scan complete.'); }
    catch (error) { setScanResult({ overall_action: 'ERROR', faces_detected: 0, results: [], summary: error.code === 'ERR_NETWORK' ? 'Backend is not running. Start start_swaraksha.bat and try again.' : error.response?.data?.detail || 'The backend could not analyze this image.' }); }
    finally { clearInterval(progressTimer); setIsScanning(false); setTimeout(() => setProgress(null), 900); }
  };

  const uploadScan = (file) => { if (!file?.type.startsWith('image/')) return; stopCamera(); setCapturedFile(file); setCameraError(''); setMode('scan'); };

  const registerLive = async (event) => {
    event.preventDefault(); if (capturedFiles.length < 5 || !personId || !personName || isRegistering) return;
    setIsRegistering(true); setRegisterResult(null); setProgress({ label: 'Preparing live images', value: 15 }); log(`Received ${capturedFiles.length} live images.`);
    const progressTimer = setInterval(() => setProgress((current) => current && current.value < 85 ? { label: current.value < 40 ? 'Detecting faces' : current.value < 70 ? 'Generating embeddings' : 'Saving profile', value: current.value + 5 } : current), 900);
    const formData = new FormData(); formData.append('person_id', personId); formData.append('name', personName); if (personEmail) formData.append('email', personEmail); capturedFiles.forEach((file) => formData.append('files', file));
    try { log('Detecting faces and generating embeddings...'); const response = await axios.post(`${API_BASE}/register`, formData); setRegisterResult({ type: 'success', text: response.data.message }); setRecentAdds((current) => ({ ...current, [response.data.person_id]: response.data.faces_registered })); setRegistrationNotice(`${response.data.faces_registered} live reference image${response.data.faces_registered === 1 ? '' : 's'} added to ${personName}.`); setProgress({ label: 'Identity protected', value: 100 }); log(`Saved ${response.data.faces_registered} new reference images.`); const people = await axios.get(`${API_BASE}/persons`); setPersons(people.data); setCapturedFiles([]); setPersonId(''); setPersonName(''); setPersonEmail(''); setTimeout(() => { setProgress(null); stopCamera(); setMode('start'); }, 1500); }
    catch (error) { setRegisterResult({ type: 'error', text: error.code === 'ERR_NETWORK' ? 'Backend is not running.' : error.response?.data?.detail || 'The backend could not register this identity.' }); }
    finally { clearInterval(progressTimer); setIsRegistering(false); }
  };

  const registerReference = async (event) => {
    event.preventDefault(); if (!referenceFiles.length || !personId || !personName || isRegistering) return;
    setIsRegistering(true); setRegisterResult(null); setProgress({ label: 'Preparing reference images', value: 15 }); log(`Received ${referenceFiles.length} reference images.`);
    const progressTimer = setInterval(() => setProgress((current) => current && current.value < 85 ? { label: current.value < 40 ? 'Detecting faces in references' : current.value < 70 ? 'Generating identity embeddings' : 'Saving protected profile', value: current.value + 5 } : current), 900);
    const formData = new FormData(); formData.append('person_id', personId); formData.append('name', personName); if (personEmail) formData.append('email', personEmail); referenceFiles.forEach((file) => formData.append('files', file));
    try { log('Detecting faces and generating embeddings...'); const response = await axios.post(`${API_BASE}/register`, formData); setRegisterResult({ type: 'success', text: response.data.message }); setRecentAdds((current) => ({ ...current, [response.data.person_id]: response.data.faces_registered })); setRegistrationNotice(`${response.data.faces_registered} reference image${response.data.faces_registered === 1 ? '' : 's'} added to ${personName}.`); setProgress({ label: 'Identity protected', value: 100 }); log(`Saved ${response.data.faces_registered} new reference images.`); const people = await axios.get(`${API_BASE}/persons`); setPersons(people.data); setReferenceFiles([]); setPersonId(''); setPersonName(''); setPersonEmail(''); setTimeout(() => { setProgress(null); setMode('start'); }, 1000); }
    catch (error) { setRegisterResult({ type: 'error', text: error.code === 'ERR_NETWORK' ? 'Backend is not running. Start start_swaraksha.bat and try again.' : error.response?.data?.detail || 'The backend could not register this image.' }); }
    finally { clearInterval(progressTimer); setIsRegistering(false); }
  };

  const scanVideo = async (event) => {
    event.preventDefault(); if (!videoFiles.length || isVideoScanning) return;
    setIsVideoScanning(true); setVideoResults([]); setProgress({ label: 'Uploading videos', value: 15 }); log(`Video queue started: ${videoFiles.length} file(s).`);
    const progressTimer = setInterval(() => setProgress((current) => current && current.value < 90 ? { label: current.value < 30 ? 'Extracting video frames' : current.value < 50 ? 'Detecting faces & matching identities' : 'Running AI manipulation analysis', value: current.value + 4 } : current), 1100);
    try { for (const file of videoFiles) { log(`Sampling frames: ${file.name}`); const formData = new FormData(); formData.append('file', file); const response = await axios.post(`${API_BASE}/scan-video`, formData); setVideoResults((current) => [...current, { fileName: file.name, ...response.data }]); } setProgress({ label: 'Video queue complete', value: 100 }); log('Video queue complete.'); }
    catch (error) { setVideoResults((current) => [...current, { fileName: 'Upload error', final_status: 'ERROR', summary: error.response?.data?.detail || 'The backend could not analyze this video.' }]); }
    finally { clearInterval(progressTimer); setIsVideoScanning(false); setTimeout(() => setProgress(null), 900); }
  };

  const navItems = [['start', 'Home', LayoutDashboard], ['directory', 'Protected people', Users], ['live-register', 'Live Registration', ScanFace], ['video', 'Video lab', FileVideo], ['reverse', 'Reverse search', Search]];
  return <div className="app-shell">
    <aside className="sidebar"><button className="brand" onClick={goHome}><img className="brand-image" src="/icon2.png" alt="SWARAKSHA" /><span><strong>SWARAKSHA</strong><small>identity protection</small></span></button><div className="sidebar-label">Workspace</div><nav>{navItems.map(([id, label, Icon]) => <button className={mode === id ? 'active' : ''} key={id} onClick={() => { if (id === 'scan') startCamera(); else { stopCamera(); setMode(id); } }}><Icon size={17} />{label}</button>)}</nav><div className="sidebar-status"><span className={backendOnline ? 'online' : ''} /><div><strong>{backendOnline ? 'Backend connected' : 'Backend offline'}</strong><small>localhost:8000</small></div></div><div className="sidebar-process"><Activity size={15} /><span>Process monitor</span><b>{isScanning || isRegistering || isVideoScanning ? 'Active' : 'Idle'}</b></div></aside>
    <div className="page-shell"><header className="app-header"><div><span className="eyebrow">SWARAKSHA / {navItems.find(([id]) => id === mode)?.[1]}</span><h1>{mode === 'start' ? 'Your protection desk' : navItems.find(([id]) => id === mode)?.[1]}</h1></div><div className="connection"><i className={backendOnline ? 'online' : ''} />{backendOnline ? 'System ready' : 'Backend offline'}</div></header>
    <main className="main-content">
      {mode === 'start' && <StartScreen backendOnline={backendOnline} notice={registrationNotice} onScan={startCamera} onReference={() => { setMode('reference'); setRegisterResult(null); setRegistrationNotice(''); }} onUpload={uploadScan} onDirectory={() => setMode('directory')} onVideo={() => setMode('video')} onReverse={() => setMode('reverse')} />}
      {mode === 'scan' && <ScanScreen {...{ capturedFile, scanImage, isScanning, scanResult, uploadScan, goHome }} />}
      {mode === 'live-register' && <LiveRegistrationScreen {...{ stream, videoRef, canvasRef, cameraError, capturedFiles, setCapturedFiles, captureFace, registerLive, isRegistering, registerResult, personId, setPersonId, personName, setPersonName, personEmail, setPersonEmail, goHome, startCamera }} />}
      {mode === 'reference' && <ReferenceScreen {...{ referenceFiles, setReferenceFiles, personId, setPersonId, personName, setPersonName, personEmail, setPersonEmail, registerReference, isRegistering, registerResult, goHome }} />}
      {mode === 'directory' && <DirectoryScreen persons={persons} recentAdds={recentAdds} onDelete={deletePerson} onReference={() => setMode('reference')} goHome={goHome} />}
      {mode === 'video' && <VideoScreen {...{ videoFiles, setVideoFiles, videoResults, scanVideo, isVideoScanning, goHome }} />}
      {mode === 'reverse' && <ReverseSearchScreen goHome={goHome} />}
    </main>
    {progress && <ProgressBar progress={progress} />}
    <ActivityTerminal entries={activityLog} />
    <footer><Sparkles size={14} /> Your images are processed by the local SWARAKSHA backend. <span>Nothing is uploaded until you choose an action.</span></footer></div>
  </div>;
}

function StartScreen({ backendOnline, notice, onScan, onReference, onUpload, onDirectory, onVideo, onReverse }) { return <section className="start-screen"><div className="intro"><div className="hero-art"><img src="/icon2.png" alt="SWARAKSHA shield" /></div><span className="kicker">Identity protection console</span><h1>Protect a face. Check a file.</h1><p>Use a live camera, trusted reference images, or a video to inspect identity matches and authenticity.</p><div className={`backend-note ${backendOnline ? 'ready' : ''}`}><span className="status-dot" />{backendOnline ? 'Protection service ready' : 'Start the backend to enable protection'}</div>{notice && <div className="backend-note ready"><Check size={14} />{notice}</div>}</div><div className="choice-grid"><button className="choice-card primary-choice" onClick={onScan}><span className="choice-icon"><ScanFace size={23} /></span><span><strong>Register via Camera</strong><small>Use your camera to register a new user.</small></span><b>→</b></button><button className="choice-card" onClick={onReference}><span className="choice-icon"><ImagePlus size={23} /></span><span><strong>Add reference images</strong><small>Register five or more trusted face images.</small></span><b>→</b></button><label className="upload-link"><UploadCloud size={16} /> Or upload an image to scan<input type="file" accept="image/*" onChange={(event) => onUpload(event.target.files[0])} /></label><button className="utility-link" onClick={onDirectory}><FolderOpen size={15} /> View protected directory</button><button className="utility-link" onClick={onVideo}><FileVideo size={15} /> Submit a video for checking</button><button className="utility-link" onClick={onReverse}><Search size={15} /> Reverse Image Search (Layer 3)</button></div></section> }

function ScanScreen({ capturedFile, scanImage, isScanning, scanResult, uploadScan, goHome }) { const preview = capturedFile ? URL.createObjectURL(capturedFile) : null; return <section className="work-screen"><BackButton onClick={goHome} /><div className="work-heading"><span className="kicker">Image Check</span><h2>Scan an Image</h2><p>Upload a file to check for protected identities and AI manipulation.</p></div><div className="scan-workspace"><div className="camera-panel">{capturedFile ? <img className="captured-preview" src={preview} alt="Captured face" /> : <div className="camera-empty"><ImagePlus size={27} /><strong>No image selected</strong></div>}<div className="camera-actions">{capturedFile ? <><button className="button primary" onClick={scanImage} disabled={isScanning}>{isScanning ? <LoaderCircle className="spin" size={16} /> : <Shield size={16} />}{isScanning ? 'Checking...' : 'Check this image'}</button></> : null}</div></div><div className="result-card">{scanResult ? <Result result={scanResult} /> : <><div className="result-placeholder"><ShieldAlert size={25} /><strong>Your result will appear here</strong><p>We’ll look for a protected identity and signs of AI-generated manipulation.</p></div><label className="small-upload">Choose a file<input type="file" accept="image/*" onChange={(event) => uploadScan(event.target.files[0])} /></label></>}</div></div></section> }

const FACE_PROMPTS = [
  "Look straight at the camera",
  "Turn head slightly Left",
  "Turn head slightly Right",
  "Tilt head slightly Up",
  "Tilt head slightly Down",
  "Scan Complete - Ready to save"
];

function LiveRegistrationScreen({ stream, videoRef, canvasRef, cameraError, capturedFiles, setCapturedFiles, captureFace, registerLive, isRegistering, registerResult, personId, setPersonId, personName, setPersonName, personEmail, setPersonEmail, goHome, startCamera }) { 
  const progressCount = Math.min(capturedFiles.length, 5);
  const currentPrompt = FACE_PROMPTS[progressCount];
  const isComplete = progressCount >= 5;
  const progressPercent = (progressCount / 5) * 100;
  
  const radius = 130;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progressPercent / 100) * circumference;

  // Auto-capture loop
  useEffect(() => {
    if (!stream || isComplete || isRegistering) return;
    
    let isProcessing = false;
    const interval = setInterval(async () => {
      if (isProcessing) return;
      isProcessing = true;
      
      try {
        if (!videoRef.current || !canvasRef.current) {
          isProcessing = false;
          return;
        }
        
        const canvas = canvasRef.current;
        const video = videoRef.current;
        
        if (video.videoWidth === 0 || video.videoHeight === 0) {
          isProcessing = false;
          return;
        }
        
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.85));
        if (!blob) {
          isProcessing = false;
          return;
        }
        
        const formData = new FormData();
        formData.append('file', blob, 'frame.jpg');
        formData.append('requested_pose', currentPrompt);
        
        const res = await fetch('http://127.0.0.1:8000/api/auto-capture', {
          method: 'POST',
          body: formData
        });
        
        if (res.ok) {
          const data = await res.json();
          if (data.captured) {
            const file = new File([blob], `auto_capture_${Date.now()}.jpg`, { type: 'image/jpeg' });
            setCapturedFiles(prev => [...prev, file]);
          }
        }
      } catch (err) {
        console.error("Auto-capture error:", err);
      }
      isProcessing = false;
    }, 600); // check every 600ms
    
    return () => clearInterval(interval);
  }, [stream, isComplete, isRegistering, currentPrompt, setCapturedFiles, videoRef, canvasRef]);

  return <section className="work-screen reference-screen">
    <BackButton onClick={goHome} />
    <div className="work-heading">
      <span className="kicker">Live Registration</span>
      <h2>Register via Camera</h2>
      <p>Follow the prompts to capture your face from multiple angles.</p>
    </div>
    
    <div className="scan-workspace" style={{display: 'flex', gap: '30px', alignItems: 'center'}}>
      <div className="face-id-container" style={{flex: 1}}>
        <div className={`face-id-prompt ${isComplete ? 'complete' : 'pulsing'}`}>
          {currentPrompt}
        </div>
        
        <div className="face-id-ring-wrapper">
          <div className={`face-id-ring ${isComplete ? 'complete' : ''}`}>
            <svg>
              <circle className="track" cx="136" cy="136" r={radius} />
              <circle className="progress" cx="136" cy="136" r={radius} strokeDasharray={circumference} strokeDashoffset={strokeDashoffset} />
            </svg>
          </div>
          
          <div className="face-id-camera">
            {stream ? <video ref={videoRef} autoPlay playsInline muted /> : <div className="camera-empty"><Camera size={27} /><strong>Camera unavailable</strong><span>{cameraError || 'Preparing...'}</span></div>}
          </div>
        </div>

        <div className="camera-actions" style={{justifyContent: 'center', width: '100%', margin: 0, flexDirection: 'column', gap: '15px', alignItems: 'center'}}>
          <button type="button" className={`button primary face-id-btn ${isComplete ? 'secondary' : ''}`} disabled>
            {isComplete ? <><Camera size={17} /> Scan Complete</> : <><LoaderCircle className="spin" size={17} /> Scanning ({progressCount}/5)...</>}
          </button>
          
          {!isComplete && (
            <label style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 15px', background: 'rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff', fontSize: '13px', transition: 'all 0.2s', marginTop: '10px' }}>
              <UploadCloud size={15} /> <span>Or select a photo manually</span>
              <input type="file" accept="image/*" style={{ display: 'none' }} onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setCapturedFiles(prev => [...prev, e.target.files[0]]);
                }
              }} />
            </label>
          )}
        </div>
        {cameraError && <div className="camera-error" style={{marginTop: '15px'}}><ShieldAlert size={16} />{cameraError}<button onClick={startCamera}>Try camera again</button></div>}
      </div>
      
      <form className="reference-form" onSubmit={registerLive} style={{flex: 1, margin: 0}}>
        <div className="reference-fields" style={{gridTemplateColumns: '1fr'}}>
          <label>Person ID<input value={personId} onChange={(e) => setPersonId(e.target.value)} placeholder="e.g. AARTI_001" required /></label>
          <label>Name<input value={personName} onChange={(e) => setPersonName(e.target.value)} placeholder="e.g. Aarti Sharma" required /></label>
          <label>Email Address<input type="email" value={personEmail} onChange={(e) => setPersonEmail(e.target.value)} placeholder="e.g. alert@example.com" required /></label>
        </div>
        
        {registerResult && <div className={`form-result ${registerResult.type}`}><Check size={16} />{registerResult.text}</div>}
        <button className="button primary submit-reference" disabled={capturedFiles.length === 0 || !personId || !personName || !personEmail || isRegistering} style={{marginTop: '25px'}}>
          {isRegistering ? <LoaderCircle className="spin" size={16} /> : <UserRound size={16} />}
          {isRegistering ? 'Adding identity...' : `Register User`}
        </button>
      </form>
    </div>
    <canvas ref={canvasRef} hidden />
  </section>;
}

function ReferenceScreen({ referenceFiles, setReferenceFiles, personId, setPersonId, personName, setPersonName, personEmail, setPersonEmail, registerReference, isRegistering, registerResult, goHome }) { const addFiles = (files) => setReferenceFiles((current) => [...current, ...[...files].filter((file) => file.type.startsWith('image/'))]); return <section className="work-screen reference-screen"><BackButton onClick={goHome} /><div className="work-heading"><span className="kicker">Create a protected identity</span><h2>Upload reference images</h2><p>Take photos from multiple angles (like setting up Face ID/recognition on a smartphone). Add five or more clear photos from different angles for best results.</p></div><form className="reference-form" onSubmit={registerReference}><div className={`reference-upload ${referenceFiles.length ? 'has-files' : ''}`}>{referenceFiles.length ? <><div className="reference-grid">{referenceFiles.map((file, index) => <div className="reference-thumb" key={`${file.name}-${index}`}><img src={URL.createObjectURL(file)} alt={`Reference ${index + 1}`} /><button type="button" onClick={() => setReferenceFiles(referenceFiles.filter((_, fileIndex) => fileIndex !== index))}><X size={13} /></button></div>)}<label className="add-more"><ImagePlus size={20} /><span>Add more</span><input type="file" accept="image/*" multiple onChange={(event) => addFiles(event.target.files)} /></label></div><small className="reference-count">{referenceFiles.length} image{referenceFiles.length === 1 ? '' : 's'} selected · add at least 5 for best results</small></> : <label><UploadCloud size={27} /><strong>Choose 5 or more face images</strong><span>JPG or PNG · use different angles and lighting</span><input type="file" accept="image/*" multiple onChange={(event) => addFiles(event.target.files)} /></label>}</div><div className="reference-fields"><label>Person ID<input value={personId} onChange={(event) => setPersonId(event.target.value)} placeholder="e.g. AARTI_001" required /></label><label>Name<input value={personName} onChange={(event) => setPersonName(event.target.value)} placeholder="e.g. Aarti Sharma" required /></label><label>Email Address<input type="email" value={personEmail} onChange={(event) => setPersonEmail(event.target.value)} placeholder="e.g. alert@example.com" required /></label></div>{registerResult && <div className={`form-result ${registerResult.type}`}><Check size={16} />{registerResult.text}</div>}<button className="button primary submit-reference" disabled={referenceFiles.length < 5 || !personId || !personName || !personEmail || isRegistering}>{isRegistering ? <LoaderCircle className="spin" size={16} /> : <UserRound size={16} />}{isRegistering ? 'Adding identity...' : `Protect identity with ${referenceFiles.length} image${referenceFiles.length === 1 ? '' : 's'}`}</button></form></section> }

function ProgressBar({ progress }) { return <div className="progress-dock"><div className="progress-copy"><LoaderCircle className="spin" size={15} /><strong>{progress.label}</strong><span>{progress.value}%</span></div><div className="progress-track"><i style={{ width: `${progress.value}%` }} /></div></div> }
function ActivityTerminal({ entries }) { return <section className="activity-terminal"><div><span className="terminal-dot red" /><span className="terminal-dot yellow" /><span className="terminal-dot green" /><strong>SWARAKSHA process</strong></div>{entries.map((entry, index) => <p key={`${entry}-${index}`}>{entry}</p>)}</section> }
function DirectoryScreen({ persons, recentAdds, onDelete, onReference, goHome }) { return <section className="work-screen directory-screen"><BackButton onClick={goHome} /><div className="work-heading"><span className="kicker">Protected directory</span><h2>Registered identities</h2><p>Manage the people currently available to match during scans.</p></div><div className="directory-card">{persons.length ? persons.map((person) => <div className="directory-row" key={person.person_id}><span className="directory-avatar"><UserRound size={18} /></span><span><strong>{person.name}</strong><small>{person.person_id} · {recentAdds[person.person_id] || person.image_count || 0} added this enrollment · {person.image_count || 0} total stored</small></span><Check size={17} /><button className="delete-person" title={`Delete ${person.name}`} onClick={() => onDelete(person.person_id)}><Trash2 size={16} /></button></div>) : <div className="directory-empty"><Users size={27} /><strong>No identities registered yet</strong><p>Add reference images to create the first protected profile.</p><button className="button primary" onClick={onReference}><ImagePlus size={15} /> Add reference images</button></div>}</div></section> }
function VideoScreen({ videoFiles, setVideoFiles, videoResults, scanVideo, isVideoScanning, goHome }) { const addVideos = (files) => setVideoFiles((current) => [...current, ...[...files].filter((file) => file.type.startsWith('video/'))]); return <section className="work-screen video-screen"><BackButton onClick={goHome} /><div className="work-heading"><span className="kicker">Video protection scan</span><h2>Video lab</h2><p>Queue multiple videos and compare their sampled-frame results in one run.</p></div><div className="video-layout"><form className="reference-form" onSubmit={scanVideo}><label className="video-drop"><FileVideo size={30} /><strong>Choose one or more videos</strong><span>MP4, MOV, AVI · files are sampled automatically</span><input type="file" accept="video/*" multiple onChange={(event) => addVideos(event.target.files)} /></label>{videoFiles.length > 0 && <div className="video-queue">{videoFiles.map((file, index) => <div key={`${file.name}-${index}`}><FileVideo size={14} /><span>{file.name}</span><button type="button" onClick={() => setVideoFiles(videoFiles.filter((_, fileIndex) => fileIndex !== index))}><X size={14} /></button></div>)}</div>}<button className="button primary submit-reference" disabled={!videoFiles.length || isVideoScanning}>{isVideoScanning ? <LoaderCircle className="spin" size={16} /> : <Shield size={16} />}{isVideoScanning ? 'Checking queue...' : `Check ${videoFiles.length} video${videoFiles.length === 1 ? '' : 's'}`}</button></form><div className="video-results">{videoResults.length ? videoResults.map((result, index) => <VideoResultCard key={`${result.fileName}-${index}`} result={result} />) : <div className="directory-card directory-empty"><FileVideo size={27} /><strong>Results will appear here</strong><p>Each queued video gets its own summary after processing.</p></div>}</div></div></section> }

function VideoResultCard({ result }) {
  if (result.final_status === 'ERROR' || !result.video) {
    return <article className="video-result-card error"><div className="video-result-heading"><FileVideo size={16} /><strong>{result.fileName}</strong><span className="bad-text">ERROR</span></div><p>{result.summary}</p></article>;
  }
  const { video, identity, ai_analysis, final_status, frames, summary } = result;
  const isDanger = final_status === 'POTENTIAL_AI_MANIPULATION';
  const personNames = identity.person_ids.length ? identity.person_ids.join(', ') : 'None';
  return (
    <article className="video-result-card">
      <div className="video-result-heading">
        <FileVideo size={16} /><strong>{result.fileName}</strong>
        <span className={isDanger ? 'bad-text' : 'good-text'}>{final_status.replace(/_/g, ' ')}</span>
      </div>
      <p style={{marginBottom: "12px"}}>{summary}</p>
      <div className="video-stats-grid">
        <div className="stat-row"><span>Protected Identity:</span> <strong>{personNames}</strong></div>
        <div className="stat-row"><span>Identity Match:</span> <strong>{identity.protected_identity_detected ? `${Math.round(identity.identity_frame_ratio*100)}% of frames` : 'No'}</strong></div>
        <div className="stat-row"><span>Identity Frames:</span> <strong>{identity.frames_with_identity} / {video.sampled_frames}</strong></div>
        <div className="stat-row"><span>AI analysis:</span> <strong>{ai_analysis.frames_flagged} / {ai_analysis.frames_analyzed} suspicious</strong></div>
      </div>
      <div className="video-overall" style={{ borderLeftColor: isDanger ? '#d32f2f' : '#6b4c9a' }}>
        <strong>Overall:</strong> <span className={isDanger ? 'bad-text' : 'good-text'}>{isDanger ? '⚠ POTENTIAL AI MANIPULATION' : '✅ NO THREAT DETECTED'}</span>
        <br/><small>Consent: {final_status.replace(/_/g, ' ')}</small>
      </div>
      <div className="timeline-container">
        <p className="timeline-label">Frame Timeline</p>
        <div className="timeline-track">
          {frames && frames.map((f, i) => {
            let dotClass = "dot-none";
            let title = `Frame ${f.frame_number} (${f.timestamp}s): No protected identity`;
            if (f.protected_identity_detected) {
               if (f.ai_analysis && f.ai_analysis.result === 'AI_GENERATED') {
                  dotClass = "dot-danger"; title = `Frame ${f.frame_number} (${f.timestamp}s): Manipulated! (Score: ${f.ai_analysis.score})`;
               } else {
                  dotClass = "dot-safe"; title = `Frame ${f.frame_number} (${f.timestamp}s): Protected identity, Real`;
               }
            }
            return <div key={i} className={`timeline-dot ${dotClass}`} title={title}></div>
          })}
        </div>
      </div>
      {result.layer_3 && <Layer3Panel layer3={result.layer_3} />}
      {result.metadata_forensics && <VideoMetadataPanel meta={result.metadata_forensics} />}
    </article>
  );
}

function Layer3Panel({ layer3 }) {
  if (!layer3 || !layer3.performed) return null;
  const isDiscrepancy = layer3.context_discrepancies > 0;
  return (
    <div className={`metadata-panel ${isDiscrepancy ? 'metadata-warning' : 'metadata-clean'}`} style={{marginTop: '12px'}}>
      <div className="metadata-header">
        <strong><Eye size={14} style={{display: 'inline-block', verticalAlign: 'middle', marginRight: '4px'}}/> Visual Forensic Context (Layer 3)</strong>
        <span className={isDiscrepancy ? 'bad-text' : 'good-text'}>{layer3.status.replace(/_/g, ' ')}</span>
      </div>
      <div style={{fontSize: '0.85rem', color: 'var(--text-dim)', marginBottom: '8px', lineHeight: '1.4'}}>
        Analyzed {layer3.query_frames} suspicious frames. Found {layer3.strong_matches} contextual matches.
      </div>
      {layer3.matches && layer3.matches.length > 0 ? (
         <div className="layer3-matches" style={{display: 'flex', flexDirection: 'column', gap: '8px'}}>
            {layer3.matches.map((match, i) => (
               <div key={i} className="layer3-match-row" style={{borderLeft: `3px solid ${match.face_discrepancy ? '#d32f2f' : '#2e7d32'}`, paddingLeft: '10px', background: 'var(--card-bg-subtle)', padding: '8px', borderRadius: '4px', fontSize: '0.85rem'}}>
                 <div style={{fontWeight: '600', marginBottom: '4px'}}>Frame {match.query_frame} ({match.query_timestamp}s)</div>
                 <div style={{color: 'var(--text-dim)'}}>Matched Reference: {match.reference.source_path} {match.reference.source_type === 'video' ? `(Frame ${match.reference.frame_number})` : ''}</div>
                 <div style={{display: 'flex', gap: '12px', margin: '4px 0'}}>
                    <span><strong>Context Sim:</strong> {(match.context_similarity*100).toFixed(1)}%</span>
                    <span><strong>Face Sim:</strong> {(match.face_similarity*100).toFixed(1)}%</span>
                 </div>
                 {match.face_discrepancy && <div className="bad-text" style={{marginTop: '4px'}}><strong>⚠ DISCREPANCY:</strong> Same background context, but completely different face!</div>}
               </div>
            ))}
         </div>
      ) : (
        <p className="metadata-clean-msg">No context matches found in the visual reference database.</p>
      )}
    </div>
  );
}

function VideoMetadataPanel({ meta }) {
  if (!meta || (!meta.flags?.length && meta.confidence === 'none')) return null;
  const isWarning = meta.confidence === 'high' || meta.confidence === 'medium';
  return (
    <div className={`metadata-panel ${isWarning ? 'metadata-warning' : 'metadata-clean'}`}>
      <div className="metadata-header">
        <strong>🗂️ File Metadata Forensics</strong>
        <span className={isWarning ? 'bad-text' : 'good-text'}>{meta.confidence.toUpperCase()}</span>
      </div>
      {meta.flags && meta.flags.length > 0 ? (
        <ul className="metadata-flags">
          {meta.flags.map((flag, i) => <li key={i}>{flag}</li>)}
        </ul>
      ) : (
        <p className="metadata-clean-msg">No AI metadata markers detected in video file.</p>
      )}
    </div>
  );
}

function BackButton({ onClick }) { return <button className="back-button" onClick={onClick}><ArrowLeft size={16} /> Back</button> }
function Result({ result }) { const error = result.overall_action === 'ERROR'; const blocked = result.overall_action === 'BLOCK'; const meta = result.metadata_forensics; return <div className="scan-result"><div className={`verdict ${error ? 'error' : blocked ? 'blocked' : 'cleared'}`}>{error ? <ShieldAlert size={21} /> : blocked ? <ShieldAlert size={21} /> : <Check size={21} />}<div><small>{error ? 'Connection problem' : blocked ? 'Action required' : 'Protection check complete'}</small><strong>{error ? 'Could not analyze' : blocked ? 'Potential manipulation found' : 'No threat detected'}</strong></div></div><p>{result.summary}</p>{!error && <div className="result-stats"><span><b>{result.faces_detected}</b> faces detected</span><span><b>{result.results?.filter((item) => item.name).length || 0}</b> identities matched</span></div>}{result.results?.map((item, index) => <div className="face-result" key={index}><span className={item.action === 'BLOCK' ? 'bad' : 'good'}>{item.action === 'BLOCK' ? <ShieldAlert size={14} /> : <Check size={14} />}</span><div><strong>{item.name || 'Unknown face'}</strong><small>{item.reason}</small></div></div>)}{meta && <MetadataPanel meta={meta} />}</div> }


function MetadataPanel({ meta }) {
  if (!meta || (!meta.flags?.length && meta.confidence === 'none')) return null;
  const isWarning = meta.confidence === 'high' || meta.confidence === 'medium';
  return (
    <div className={`metadata-panel ${isWarning ? 'metadata-warning' : 'metadata-clean'}`}>
      <div className="metadata-header">
        <strong>🗂️ Metadata Forensics</strong>
        <span className={isWarning ? 'bad-text' : 'good-text'}>{meta.confidence.toUpperCase()}</span>
      </div>
      {meta.flags && meta.flags.length > 0 ? (
        <ul className="metadata-flags">
          {meta.flags.map((flag, i) => <li key={i}>{flag}</li>)}
        </ul>
      ) : (
        <p className="metadata-clean-msg">No AI metadata markers detected in file.</p>
      )}
    </div>
  );
}

function ReverseSearchScreen({ goHome }) {
  const [file, setFile] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!file || isSearching) return;
    setIsSearching(true); setError(null); setResults(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const response = await axios.post(`${API_BASE}/reverse-search`, formData);
      setResults(response.data.matches);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to search image.');
    } finally {
      setIsSearching(false);
    }
  };

  return <section className="work-screen">
    <BackButton onClick={goHome} />
    <div className="work-heading">
      <span className="kicker">Visual Forensics</span>
      <h2>Reverse Image Search</h2>
      <p>Upload an image to search its background context in the reference index.</p>
    </div>
    <form className="reference-form" onSubmit={handleSearch}>
      <label className="video-drop"><ImagePlus size={30} /><strong>Choose an image</strong><input type="file" accept="image/*" onChange={(e) => setFile(e.target.files[0])} /></label>
      {file && <div className="video-queue"><div><ImagePlus size={14} /><span>{file.name}</span><button type="button" onClick={() => setFile(null)}><X size={14} /></button></div></div>}
      <button className="button primary submit-reference" disabled={!file || isSearching}>
        {isSearching ? <LoaderCircle className="spin" size={16} /> : <Search size={16} />}
        {isSearching ? 'Searching...' : 'Search Context'}
      </button>
    </form>
    {error && <div className="camera-error"><ShieldAlert size={16} />{error}</div>}
    {results && (
      <div className="directory-card" style={{marginTop: '20px'}}>
        <h3 style={{marginBottom: '10px'}}>Top Matches</h3>
        {results.length === 0 ? <p>No matches found in the visual index.</p> : results.map((match, i) => (
          <div key={i} className="directory-row" style={{borderLeft: '3px solid var(--accent)', paddingLeft: '10px', margin: '10px 0'}}>
            <div>
              <strong>Source:</strong> {match.reference.source_path}<br/>
              {match.reference.source_type === 'video' && <small>Frame: {match.reference.frame_number}<br/></small>}
              <strong>Similarity:</strong> {(match.similarity * 100).toFixed(1)}%
            </div>
          </div>
        ))}
      </div>
    )}
  </section>;
}

export default App;
