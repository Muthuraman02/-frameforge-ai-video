"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Clapperboard,
  Download,
  Film,
  Loader2,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  WandSparkles,
  Zap,
} from "lucide-react";

const styles = [
  "Cinematic",
  "Anime",
  "Realistic",
  "3D Animation",
  "Fantasy",
  "Documentary",
];

type JobStatus = "idle" | "queued" | "processing" | "completed" | "failed" | "cancelled";

interface JobStatusPayload {
  job_id: string;
  status: Exclude<JobStatus, "idle">;
  progress: number;
  message: string;
  video_url?: string | null;
  error?: string | null;
}

const POLL_INTERVAL_MS = 3000;
const POLL_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes

function resolveApiUrl(base: string, path: string): string {
  const cleanBase = base.replace(/\/$/, "");
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  return `${cleanBase}${path.startsWith("/") ? "" : "/"}${path}`;
}

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("Cinematic");
  const [ratio, setRatio] = useState("16:9");
  const [duration, setDuration] = useState("8 seconds");

  const [busy, setBusy] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);

  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const pollStartedAtRef = useRef<number>(0);
  const isMountedRef = useRef(true);

  function stopPolling() {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      stopPolling();
    };
  }, []);

  async function pollJobStatus(base: string, activeJobId: string) {
    if (!isMountedRef.current) return;

    if (Date.now() - pollStartedAtRef.current > POLL_TIMEOUT_MS) {
      stopPolling();
      setBusy(false);
      setJobStatus("failed");
      setErrorMsg("Video generation timed out while waiting for the backend. Please try again.");
      setMessage("Generation timed out.");
      return;
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const res = await fetch(resolveApiUrl(base, `/api/videos/${activeJobId}`), {
        method: "GET",
        signal: controller.signal,
        cache: "no-store",
      });

      if (!res.ok) {
        const errBody = await res.json().catch(() => null);
        throw new Error(
          errBody?.detail || `Could not check job status (HTTP ${res.status}).`
        );
      }

      const data: JobStatusPayload = await res.json();
      if (!isMountedRef.current) return;

      setJobStatus(data.status);
      setProgress(typeof data.progress === "number" ? data.progress : 0);
      setMessage(data.message || "");

      if (data.status === "completed") {
        stopPolling();
        setBusy(false);
        setErrorMsg(null);
        if (data.video_url) {
          setVideoUrl(resolveApiUrl(base, data.video_url));
        } else {
          setErrorMsg("Video completed, but no playable video URL was returned.");
        }
        return;
      }

      if (data.status === "failed" || data.status === "cancelled") {
        stopPolling();
        setBusy(false);
        setErrorMsg(data.error || data.message || "Video generation failed.");
        return;
      }

      pollTimerRef.current = setTimeout(() => {
        void pollJobStatus(base, activeJobId);
      }, POLL_INTERVAL_MS);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        return;
      }
      if (!isMountedRef.current) return;
      stopPolling();
      setBusy(false);
      setJobStatus("failed");
      setErrorMsg(
        err instanceof Error
          ? err.message
          : "Lost connection while checking video status."
      );
      setMessage("Status check failed.");
    }
  }

  async function generate() {
    if (!prompt.trim()) {
      setErrorMsg("Describe your video first.");
      setMessage("");
      return;
    }

    const base = process.env.NEXT_PUBLIC_API_BASE_URL;
    if (!base) {
      setErrorMsg(null);
      setMessage(
        "Studio interface is ready. Connect the video backend in Vercel using NEXT_PUBLIC_API_BASE_URL to enable generation."
      );
      return;
    }

    stopPolling();
    setBusy(true);
    setJobId(null);
    setJobStatus("queued");
    setProgress(0);
    setErrorMsg(null);
    setVideoUrl(null);
    setMessage("Submitting your prompt…");

    try {
      const r = await fetch(resolveApiUrl(base, "/api/videos"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: prompt.trim(),
          style,
          aspect_ratio: ratio,
          duration,
        }),
      });

      const d = await r.json().catch(() => null);
      if (!r.ok) {
        const detail =
          typeof d?.detail === "string"
            ? d.detail
            : Array.isArray(d?.detail) && d.detail[0]?.msg
              ? d.detail[0].msg
              : `Video service returned ${r.status}`;
        throw new Error(detail);
      }

      const createdJobId: string | undefined = d?.job_id;
      if (!createdJobId) {
        throw new Error("Backend did not return a valid job ID.");
      }

      setJobId(createdJobId);
      setJobStatus(d.status || "queued");
      setProgress(typeof d.progress === "number" ? d.progress : 0);
      setMessage(d.message || "Video generation queued");

      pollStartedAtRef.current = Date.now();
      pollTimerRef.current = setTimeout(() => {
        void pollJobStatus(base, createdJobId);
      }, POLL_INTERVAL_MS);
    } catch (e) {
      setBusy(false);
      setJobStatus("failed");
      setErrorMsg(e instanceof Error ? e.message : "Could not reach video backend.");
      setMessage("");
    }
  }

  const downloadUrl = videoUrl
    ? `${videoUrl}${videoUrl.includes("?") ? "&" : "?"}download=1`
    : null;

  return (
    <main className="min-h-screen px-4 py-6 sm:px-8">
      <header className="mx-auto flex max-w-6xl items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-violet-500 p-2">
            <Clapperboard size={22} />
          </div>
          <div>
            <div className="font-bold tracking-wide">FRAMEFORGE</div>
            <div className="text-xs text-slate-400">AI VIDEO STUDIO</div>
          </div>
        </div>
        <span className="rounded-full border border-white/10 px-3 py-2 text-xs text-slate-300">
          BETA STUDIO
        </span>
      </header>

      <section className="mx-auto max-w-6xl pt-16 text-center sm:pt-24">
        <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-violet-400/20 bg-violet-400/10 px-4 py-2 text-xs text-violet-200">
          <Sparkles size={14} /> YOUR IDEAS, IN MOTION
        </div>
        <h1 className="text-4xl font-black leading-tight tracking-tight sm:text-6xl">
          Create videos from
          <br />
          <span className="bg-gradient-to-r from-violet-300 via-fuchsia-300 to-cyan-300 bg-clip-text text-transparent">
            a single idea.
          </span>
        </h1>
        <p className="mx-auto mt-5 max-w-xl text-sm leading-6 text-slate-400 sm:text-base">
          Shape a scene, choose your visual style, and prepare an AI video
          generation. Your creative studio starts here.
        </p>
      </section>

      <section className="mx-auto mt-12 grid max-w-6xl gap-6 lg:grid-cols-[1.15fr_.85fr]">
        <div className="rounded-3xl border border-white/10 bg-[#111522]/90 p-5 shadow-2xl sm:p-7">
          <div className="mb-5 flex items-center gap-2 text-lg font-semibold">
            <WandSparkles className="text-violet-300" /> Create your video
          </div>

          <label className="mb-2 block text-sm text-slate-300">
            Describe your video
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="A lone astronaut walks across a glowing alien desert at sunset, cinematic camera movement..."
            className="min-h-36 w-full rounded-2xl border border-white/10 bg-[#090d18] p-4 text-sm leading-6 outline-none focus:border-violet-400"
          />

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-2 block text-sm text-slate-300">
                Visual style
              </label>
              <select
                value={style}
                onChange={(e) => setStyle(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-[#090d18] p-3 text-sm"
              >
                {styles.map((s) => (
                  <option key={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-2 block text-sm text-slate-300">
                Aspect ratio
              </label>
              <select
                value={ratio}
                onChange={(e) => setRatio(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-[#090d18] p-3 text-sm"
              >
                <option>16:9</option>
                <option>9:16</option>
                <option>1:1</option>
              </select>
            </div>
            <div className="sm:col-span-2">
              <label className="mb-2 block text-sm text-slate-300">
                Target duration
              </label>
              <select
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-[#090d18] p-3 text-sm"
              >
                <option>8 seconds</option>
                <option>12 seconds</option>
                <option>20 seconds</option>
              </select>
            </div>
          </div>

          <button
            onClick={generate}
            disabled={busy}
            className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 px-5 py-4 font-semibold shadow-lg disabled:opacity-60"
          >
            {busy ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                {jobStatus === "queued"
                  ? "Queued…"
                  : jobStatus === "processing"
                    ? `Generating (${progress}%)…`
                    : "Preparing…"}
              </>
            ) : (
              <>
                <Sparkles size={18} />
                Generate video
              </>
            )}
          </button>

          {(jobStatus !== "idle" || message || errorMsg) && (
            <div className="mt-4 space-y-3">
              {(jobStatus === "queued" || jobStatus === "processing") && (
                <div className="rounded-xl border border-violet-400/20 bg-violet-400/10 p-3.5">
                  <div className="flex items-center justify-between text-xs font-medium text-violet-200">
                    <span className="capitalize">{jobStatus}</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-black/40">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all duration-300"
                      style={{ width: `${Math.max(4, progress)}%` }}
                    />
                  </div>
                  {message && (
                    <p className="mt-2 text-xs text-violet-100/90">{message}</p>
                  )}
                  {jobId && (
                    <p className="mt-1 text-[11px] text-slate-400">
                      Job ID: {jobId}
                    </p>
                  )}
                </div>
              )}

              {jobStatus === "completed" && !errorMsg && (
                <div className="flex items-center gap-2 rounded-xl border border-emerald-400/25 bg-emerald-400/10 p-3 text-sm text-emerald-200">
                  <CheckCircle2 size={16} className="shrink-0" />
                  <span>{message || "Video generated successfully."}</span>
                </div>
              )}

              {errorMsg && (
                <div className="rounded-xl border border-rose-400/25 bg-rose-400/10 p-3.5 text-sm text-rose-200">
                  <div className="flex items-start gap-2">
                    <AlertCircle size={16} className="mt-0.5 shrink-0" />
                    <div className="flex-1">
                      <p>{errorMsg}</p>
                      <button
                        type="button"
                        onClick={generate}
                        disabled={busy}
                        className="mt-2 inline-flex items-center gap-1.5 rounded-lg border border-rose-300/30 bg-rose-500/20 px-3 py-1.5 text-xs font-medium text-rose-100 hover:bg-rose-500/30"
                      >
                        <RotateCcw size={13} /> Retry generation
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {jobStatus === "idle" && message && !errorMsg && (
                <p className="rounded-xl border border-violet-400/20 bg-violet-400/10 p-3 text-sm text-violet-100">
                  {message}
                </p>
              )}
            </div>
          )}

          <p className="mt-3 text-center text-xs text-slate-500">
            Video generation requires a connected backend and may use provider
            credits.
          </p>
        </div>

        <div className="flex flex-col gap-5">
          <div className="relative flex min-h-[310px] flex-1 flex-col items-center justify-center overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-[#1c1a35] via-[#111827] to-[#09131c] p-6 text-center">
            {videoUrl ? (
              <div className="flex w-full flex-col items-center gap-4">
                <video
                  key={videoUrl}
                  src={videoUrl}
                  controls
                  playsInline
                  preload="metadata"
                  className="max-h-[360px] w-full rounded-2xl border border-white/10 bg-black object-contain shadow-xl"
                />
                {downloadUrl && (
                  <a
                    href={downloadUrl}
                    download={`frameforge-${jobId || "video"}.mp4`}
                    className="inline-flex items-center gap-2 rounded-xl border border-violet-400/30 bg-violet-500/20 px-4 py-2.5 text-sm font-medium text-violet-100 transition hover:bg-violet-500/30"
                  >
                    <Download size={16} /> Download MP4
                  </a>
                )}
              </div>
            ) : busy ? (
              <div className="flex flex-col items-center">
                <div className="mb-5 rounded-2xl border border-violet-400/20 bg-violet-500/10 p-5">
                  <Loader2 size={42} className="animate-spin text-violet-300" />
                </div>
                <h2 className="text-lg font-semibold">
                  {jobStatus === "queued"
                    ? "Your video is queued"
                    : "Rendering your video"}
                </h2>
                <p className="mt-2 max-w-xs text-sm leading-6 text-slate-400">
                  {message || "Preparing frames and encoding MP4…"}
                </p>
                <div className="mt-5 rounded-full border border-white/10 bg-black/20 px-4 py-2 text-xs text-violet-200">
                  {progress}% complete
                </div>
              </div>
            ) : (
              <>
                <div className="mb-5 rounded-2xl border border-white/10 bg-white/5 p-5">
                  <Film size={42} className="text-violet-200" />
                </div>
                <h2 className="text-lg font-semibold">Your canvas is ready</h2>
                <p className="mt-2 max-w-xs text-sm leading-6 text-slate-400">
                  Your generated video preview will appear here when the backend
                  is connected.
                </p>
                <div className="mt-6 flex items-center gap-2 rounded-full border border-white/10 bg-black/20 px-4 py-2 text-xs text-slate-400">
                  <Play size={13} /> Preview area
                </div>
              </>
            )}
          </div>

          <div className="grid grid-cols-3 gap-3">
            {[
              ["Fast setup", Zap],
              ["Creative control", WandSparkles],
              ["Private by design", ShieldCheck],
            ].map(([label, Icon]: any) => (
              <div
                key={label}
                className="rounded-2xl border border-white/10 bg-[#111522] p-3 text-center"
              >
                <Icon size={18} className="mx-auto mb-2 text-violet-300" />
                <div className="text-xs text-slate-300">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="mx-auto mt-14 max-w-6xl border-t border-white/10 py-6 text-center text-xs text-slate-500">
        © 2026 FrameForge AI Video Studio
      </footer>
    </main>
  );
}
