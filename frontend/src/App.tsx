import { useEffect, useRef, useState } from "react";

type Route = "recyclable" | "reusable" | "refuse_processing" | "needs_review";
type Detection = {
  box: { x1: number; y1: number; x2: number; y2: number };
  object_label: string;
  material: string;
  confidence: number;
  route: Route;
  reason: string;
  needs_review: boolean;
  possible_outputs: string[];
  reuse_ideas: string[];
};
type Classification = {
  request_id: string;
  model_version: string;
  policy_version: string;
  policy_mode: "illustrative";
  facility_id: string;
  detections: Detection[];
  notice: string;
};
type Health = { status: string; model_available: boolean; policy_mode: string };
type InputMode = "camera" | "upload";

// Empty means same-origin in production (CloudFront routes /api and /health to the ALB).
const API = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
const routeLabel: Record<Route, string> = {
  recyclable: "Recyclable",
  reusable: "Reusable",
  refuse_processing: "Refuse processing",
  needs_review: "Needs review",
};

function readableLabel(label: string): string {
  const normalized = label.toLowerCase().replace(/^[ms]_/, "").replaceAll("_", " ");
  if (normalized === "unknown" || normalized === "unknown item") return "Unknown item";
  if (normalized === "trash") return "General waste";
  return normalized;
}

function App() {
  const [mode, setMode] = useState<InputMode>("camera");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<Classification | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState<Health | null>(null);
  const [cameraOn, setCameraOn] = useState(false);
  const [pollingPaused, setPollingPaused] = useState(false);
  const [lastFrameAt, setLastFrameAt] = useState<string | null>(null);
  const [cameraReady, setCameraReady] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const inFlightRef = useRef(false);

  useEffect(() => {
    let active = true;
    const refreshHealth = () => fetch(`${API}/health`)
      .then((response) => {
        if (!response.ok) throw new Error("API unavailable");
        return response.json();
      })
      .then((payload) => { if (active) setHealth(payload as Health); })
      .catch(() => { if (active) setHealth(null); });
    void refreshHealth();
    const timer = window.setInterval(refreshHealth, 5000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  useEffect(() => {
    if (!file) { setPreview(null); return; }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    if (!cameraOn || mode !== "camera") return;
    let active = true;
    let stream: MediaStream | null = null;
    setCameraReady(false);
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setError("This browser cannot access a camera. Use localhost or HTTPS, or switch to image upload.");
      setCameraOn(false);
      return;
    }
    navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false })
      .then((cameraStream) => {
        stream = cameraStream;
        if (!active) { cameraStream.getTracks().forEach((track) => track.stop()); return; }
        if (videoRef.current) {
          videoRef.current.srcObject = cameraStream;
          void videoRef.current.play().catch(() => undefined);
        }
        setCameraReady(true);
      })
      .catch((cause: unknown) => {
        if (!active) return;
        const name = cause instanceof DOMException ? cause.name : "";
        setError(name === "NotAllowedError"
          ? "Camera permission was denied. Allow camera access in your browser settings and try again."
          : "Could not open the camera. Check that it is connected and not being used by another app.");
        setCameraOn(false);
      });
    return () => {
      active = false;
      stream?.getTracks().forEach((track) => track.stop());
      if (videoRef.current) videoRef.current.srcObject = null;
      setCameraReady(false);
    };
  }, [cameraOn, mode]);

  useEffect(() => {
    if (!cameraOn || mode !== "camera" || pollingPaused) return;
    let stopped = false;
    const sendFrame = async () => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || video.videoWidth === 0 || video.videoHeight === 0 || inFlightRef.current) return;
      inFlightRef.current = true;
      try {
        const maxEdge = 960;
        const scale = Math.min(1, maxEdge / Math.max(video.videoWidth, video.videoHeight));
        canvas.width = Math.round(video.videoWidth * scale);
        canvas.height = Math.round(video.videoHeight * scale);
        const context = canvas.getContext("2d");
        if (!context) return;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.78));
        if (!blob || stopped) return;
        const body = new FormData();
        body.append("image", blob, "webcam-frame.jpg");
        body.append("facility_id", "example_facility");
        const response = await fetch(`${API}/api/v1/live-frame`, { method: "POST", body });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || "Live frame classification failed.");
        if (!stopped) {
          setResult(payload as Classification);
          setLastFrameAt(new Date().toLocaleTimeString());
          setError(null);
        }
      } catch (cause) {
        if (stopped) return;
        setError(cause instanceof Error ? cause.message : "Could not connect to the backend.");
        setPollingPaused(true);
      } finally {
        inFlightRef.current = false;
      }
    };
    const timer = window.setInterval(() => { void sendFrame(); }, 1100);
    void sendFrame();
    return () => { stopped = true; window.clearInterval(timer); };
  }, [cameraOn, mode, pollingPaused]);

  function chooseFile(next: File | undefined) {
    setError(null);
    setResult(null);
    if (!next) { setFile(null); return; }
    if (!next.type.startsWith("image/")) { setFile(null); setError("Choose an image file (JPEG, PNG, or WebP)."); return; }
    if (next.size > 10 * 1024 * 1024) { setFile(null); setError("The image must be 10 MB or smaller."); return; }
    setFile(next);
  }

  async function classifyUpload() {
    if (!file) return;
    setBusy(true);
    setError(null);
    setResult(null);
    const body = new FormData();
    body.append("image", file);
    body.append("facility_id", "example_facility");
    try {
      const response = await fetch(`${API}/api/v1/classifications`, { method: "POST", body });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "The classification request failed.");
      setResult(payload as Classification);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not reach the API. Check that the backend is running.");
    } finally {
      setBusy(false);
    }
  }

  function startCamera() {
    setError(null);
    setResult(null);
    setPollingPaused(false);
    setMode("camera");
    setCameraOn(true);
  }

  const apiOnline = health?.status === "ok";
  const modelReady = Boolean(health?.model_available);

  return (
    <main className="min-h-screen px-4 py-8 sm:px-8 lg:px-12">
      <div className="mx-auto max-w-6xl">
        <header className="flex items-center justify-between gap-4">
          <a className="flex items-center gap-3 no-underline" href="#top" aria-label="RION home">
            <span className="grid h-11 w-11 place-items-center rounded-2xl bg-emerald-900 text-xl text-white">↻</span>
            <span><span className="block text-sm font-bold tracking-wide text-emerald-950">RION</span><span className="text-xs text-slate-500">Resource Intelligence &amp; Optimization Network</span></span>
          </a>
          <div className="rounded-full border border-emerald-900/10 bg-white px-3 py-2 text-xs text-slate-600" aria-live="polite">
            API {apiOnline ? "online" : "offline"} · Model {modelReady ? "ready" : "not trained"}
          </div>
        </header>

        <section id="top" className="grid gap-10 pb-12 pt-14 lg:grid-cols-[1.1fr_.9fr] lg:items-end lg:pt-20">
          <div>
            <p className="mb-4 text-xs font-bold uppercase tracking-[.22em] text-emerald-700">Live camera · connected to the Python API</p>
            <h1 className="max-w-2xl text-4xl font-semibold leading-tight tracking-tight text-emerald-950 sm:text-6xl">Point at an item.<br /><span className="text-emerald-600">See its next step.</span></h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-slate-600">The browser captures a small frame from your camera and sends it to the FastAPI backend about once a second. YOLO locates items; a second trained image model refines the item category and shows example reuse or recycling guidance.</p>
          </div>
          <aside className="rounded-3xl border border-amber-300/80 bg-amber-50 p-5 text-sm leading-6 text-amber-950">
            <div className="mb-1 flex items-center gap-2 font-bold"><span aria-hidden="true">ⓘ</span> Example guidance only</div>
            <p>Camera access requires permission. The bundled facility rules are illustrative. A photo cannot confirm resin codes, contamination, hidden composites, or local acceptance; ask a person to review uncertain items.</p>
          </aside>
        </section>

        <section className="grid gap-6 lg:grid-cols-[.95fr_1.05fr]">
          <div className="rounded-[2rem] border border-emerald-950/10 bg-white p-5 shadow-sm sm:p-7">
            <div className="mb-6 flex items-start justify-between gap-4">
              <div><p className="text-xs font-bold uppercase tracking-widest text-emerald-700">01 / Choose an input</p><h2 className="mt-2 text-2xl font-semibold text-emerald-950">Scan live or upload</h2></div>
              <span className={`rounded-full px-3 py-1 text-xs font-medium ${apiOnline ? "bg-emerald-50 text-emerald-800" : "bg-rose-50 text-rose-800"}`}>Backend {apiOnline ? "connected" : "not reachable"}</span>
            </div>
            <div className="mb-4 grid grid-cols-2 rounded-2xl bg-slate-100 p-1" role="tablist" aria-label="Image input method">
              <button role="tab" aria-selected={mode === "camera"} onClick={startCamera} className={`rounded-xl px-3 py-3 text-sm font-semibold ${mode === "camera" ? "bg-white text-emerald-950 shadow-sm" : "text-slate-600"}`}>Live webcam</button>
              <button role="tab" aria-selected={mode === "upload"} onClick={() => { setMode("upload"); setCameraOn(false); setPollingPaused(true); setError(null); }} className={`rounded-xl px-3 py-3 text-sm font-semibold ${mode === "upload" ? "bg-white text-emerald-950 shadow-sm" : "text-slate-600"}`}>Upload photo</button>
            </div>

            {mode === "camera" ? <>
              <div className="relative flex min-h-72 items-center justify-center overflow-hidden rounded-3xl bg-slate-950">
                {cameraOn ? <video ref={videoRef} autoPlay muted playsInline className="absolute inset-0 h-full w-full object-fill" aria-label="Live camera preview" /> : <div className="px-8 text-center text-white"><span className="text-4xl text-emerald-300">◎</span><p className="mt-3 font-semibold">Camera scanner is ready</p><p className="mt-2 text-sm leading-6 text-slate-300">Start the camera and allow browser access. For best results, show one item against a clear background.</p></div>}
                {cameraOn && result?.detections.map((item, index) => <div key={`${item.object_label}-${index}`} className="pointer-events-none absolute border-2 border-lime-300 shadow-[0_0_0_1px_rgba(0,0,0,.35)]" style={{ left: `${item.box.x1 * 100}%`, top: `${item.box.y1 * 100}%`, width: `${(item.box.x2 - item.box.x1) * 100}%`, height: `${(item.box.y2 - item.box.y1) * 100}%` }}><span className="absolute -top-6 left-0 whitespace-nowrap rounded-t bg-lime-300 px-2 py-1 text-[10px] font-bold text-emerald-950">{readableLabel(item.object_label)} · {(item.confidence * 100).toFixed(0)}%</span></div>)}
                <canvas ref={canvasRef} className="hidden" />
                {cameraOn && <div className="absolute bottom-3 left-3 rounded-full bg-black/60 px-3 py-1.5 text-xs font-medium text-white">{cameraReady ? pollingPaused ? "Preview on · detection paused" : "Live scanning" : "Opening camera…"}</div>}
              </div>
              <div className="mt-4 flex gap-3">
                {!cameraOn ? <button onClick={startCamera} className="flex-1 rounded-2xl bg-emerald-900 px-5 py-4 font-semibold text-white transition hover:bg-emerald-800">Start camera</button> : <>
                  <button onClick={() => { setCameraOn(false); setPollingPaused(true); }} className="rounded-2xl border border-slate-200 px-5 py-4 font-semibold text-slate-700 hover:bg-slate-50">Stop camera</button>
                  {pollingPaused && <button onClick={() => { setError(null); setPollingPaused(false); }} className="flex-1 rounded-2xl bg-emerald-900 px-5 py-4 font-semibold text-white">Resume detection</button>}
                </>}
              </div>
              <p className="mt-3 text-xs leading-5 text-slate-500">{lastFrameAt ? `Last backend result: ${lastFrameAt}. ` : ""}Frames are processed in memory and not saved by this app. The server needs a trained checkpoint; when absent, the app pauses scanning and reports the backend error.</p>
            </> : <>
              <label className="group relative flex min-h-72 cursor-pointer flex-col items-center justify-center overflow-hidden rounded-3xl border-2 border-dashed border-emerald-900/20 bg-[#f7faf7] text-center transition hover:border-emerald-600">
                {preview ? <img src={preview} alt="Selected material to classify" className="absolute inset-0 h-full w-full object-contain" /> : <><span className="mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-white text-2xl shadow-sm">＋</span><span className="font-semibold text-emerald-950">Drop an image or browse files</span><span className="mt-2 text-sm text-slate-500">JPEG · PNG · WebP · maximum 10 MB</span></>}
                <input className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => chooseFile(event.target.files?.[0])} />
              </label>
              {file && <div className="mt-3 flex items-center justify-between text-xs text-slate-500"><span className="max-w-[75%] truncate">{file.name}</span><button className="font-semibold text-emerald-800 underline" onClick={() => chooseFile(undefined)}>Remove</button></div>}
              <button onClick={classifyUpload} disabled={!file || busy} className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-emerald-900 px-5 py-4 font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-45">{busy ? "Analyzing image…" : "Identify material"}<span aria-hidden="true">→</span></button>
            </>}
            {error && <p role="alert" className="mt-4 rounded-2xl bg-rose-50 px-4 py-3 text-sm leading-6 text-rose-800">{error}</p>}
          </div>

          <div className="rounded-[2rem] bg-emerald-950 p-5 text-white shadow-sm sm:p-7">
            <div className="mb-6 flex items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-widest text-emerald-300">02 / Understand the route</p><h2 className="mt-2 text-2xl font-semibold">Sorting guidance</h2></div>{result && <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-emerald-100">{result.detections.length} detection{result.detections.length === 1 ? "" : "s"}</span>}</div>
            {!result ? <div className="grid min-h-64 place-items-center rounded-3xl border border-white/10 bg-white/[.04] px-8 text-center"><div><span className="text-4xl text-emerald-300">⌁</span><p className="mt-3 font-medium">Waiting for a backend result</p><p className="mt-2 max-w-sm text-sm leading-6 text-emerald-100/65">Start scanning or upload an image. Each detection includes an estimated material, confidence, route, and possible next-use examples.</p></div></div> : <div className="space-y-4">
              {result.detections.length === 0 && <div className="rounded-2xl bg-white/10 p-5 text-sm leading-6">No object was detected above the configured confidence threshold. Try a closer, clearer image or ask a person to review it.</div>}
              {result.detections.map((item, index) => <article key={`${item.object_label}-${index}`} className="rounded-3xl bg-white p-5 text-emerald-950">
                <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-widest text-emerald-700">{readableLabel(item.object_label)}</p><h3 className="mt-1 text-2xl font-semibold">{readableLabel(item.material)}</h3></div><span className={`rounded-full px-3 py-2 text-xs font-bold ${item.route === "recyclable" ? "bg-emerald-100 text-emerald-900" : item.route === "reusable" ? "bg-sky-100 text-sky-900" : item.route === "refuse_processing" ? "bg-rose-100 text-rose-900" : "bg-amber-100 text-amber-950"}`}>{routeLabel[item.route]}</span></div>
                <p className="mt-4 text-sm leading-6 text-slate-600">{item.reason}</p><p className="mt-3 text-xs font-semibold text-slate-500">Model confidence: {(item.confidence * 100).toFixed(1)}%</p>
                {item.possible_outputs.length > 0 && <div className="mt-4"><p className="text-xs font-bold uppercase tracking-wider text-emerald-800">Possible recycled outputs</p><ul className="mt-1 list-inside list-disc text-sm leading-6 text-slate-600">{item.possible_outputs.map((output) => <li key={output}>{output}</li>)}</ul></div>}
                {item.reuse_ideas.length > 0 && <div className="mt-4"><p className="text-xs font-bold uppercase tracking-wider text-emerald-800">Reuse ideas</p><ul className="mt-1 list-inside list-disc text-sm leading-6 text-slate-600">{item.reuse_ideas.map((idea) => <li key={idea}>{idea}</li>)}</ul></div>}
                {item.needs_review && <p className="mt-4 rounded-xl bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">Needs human review. Do not treat the model output as a facility acceptance decision.</p>}
              </article>)}
              <p className="px-1 text-xs leading-5 text-emerald-100/70">Policy {result.policy_version} · Model {result.model_version} · Request {result.request_id.slice(0, 8)}</p>
            </div>}
          </div>
        </section>
        <footer className="flex flex-col justify-between gap-3 py-8 text-xs text-slate-500 sm:flex-row"><span>RION · Browser webcam connected to FastAPI</span><span>Routes are policy decisions; material labels are model estimates.</span></footer>
      </div>
    </main>
  );
}

export default App;
