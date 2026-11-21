"use client";
import { useState } from "react";
import { Sparkles, Film, WandSparkles, Download, Play, ChevronDown, Clapperboard, Zap, ShieldCheck } from "lucide-react";

const styles = ["Cinematic", "Anime", "Realistic", "3D Animation", "Fantasy", "Documentary"];
export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [style, setStyle] = useState("Cinematic");
  const [ratio, setRatio] = useState("16:9");
  const [duration, setDuration] = useState("8 seconds");
  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState("");
  async function generate() {
    if (!prompt.trim()) { setMessage("Describe the video you want to create first."); return; }
    const base = process.env.NEXT_PUBLIC_API_BASE_URL;
    if (!base) { setMessage("Frontend is ready. Connect your video-generation backend by setting NEXT_PUBLIC_API_BASE_URL in Vercel."); return; }
    setStatus("working"); setMessage("Sending your prompt to the video engine…");
    try {
      const res = await fetch(base.replace(/\/$/, "") + "/api/videos", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prompt, style, aspect_ratio: ratio, duration }) });
      if (!res.ok) throw new Error("The video service returned " + res.status);
      const data = await res.json();
      setMessage(data.message || "Your generation request was accepted. Job ID: " + (data.job_id || "created"));
    } catch (e) { setMessage(e instanceof Error ? e.message : "Could not reach the video service."); }
    finally { setStatus("idle"); }
  }
  return <main className="min-h-screen px-4 py-6 sm:px-8">
    <header className="mx-auto flex max-w-6xl items-center justify-between">
      <div className="flex items-center gap-3"><div className="rounded-xl bg-violet-500 p-2"><Clapperboard size={22}/></div><div><div className="font-bold tracking-wide">FRAMEFORGE</div><div className="text-xs text-slate-400">AI VIDEO STUDIO</div></div></div>
      <div className="rounded-full border border-white/10 px-3 py-2 text-xs text-slate-300">BETA STUDIO</div>
    </header>
    <section className="mx-auto max-w-6xl pt-16 text-center sm:pt-24">
      <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-violet-400/20 bg-violet-400/10 px-4 py-2 text-xs text-violet-200"><Sparkles size={14}/> YOUR IDEAS, IN MOTION</div>
      <h1 className="text-4xl font-black leading-tight tracking-tight sm:text-6xl">Create videos from<br/><span className="bg-gradient-to-r from-violet-300 via-fuchsia-300 to-cyan-300 bg-clip-text text-transparent">a single idea.</span></h1>
      <p className="mx-auto mt-5 max-w-xl text-sm leading-6 text-slate-400 sm:text-base">Shape a scene, choose your visual style, and prepare an AI video generation. Your creative studio starts here.</p>
    </section>
    <section className="mx-auto mt-12 grid max-w-6xl gap-6 lg:grid-cols-[1.15fr_.85fr]">
      <div className="rounded-3xl border border-white/10 bg-[#111522]/90 p-5 shadow-2xl shadow-black/30 sm:p-7">
        <div className="mb-5 flex items-center gap-2 text-lg font-semibold"><WandSparkles className="text-violet-300"/> Create your video</div>
        <label className="mb-2 block text-sm font-medium text-slate-300">Describe your video</label>
        <textarea value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder="A lone astronaut walks across a glowing alien desert at sunset, cinematic camera movement…" className="min-h-36 w-full resize-y rounded-2xl border border-white/10 bg-[#090d18] p-4 text-sm leading-6 outline-none transition focus:border-violet-400"/>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          <div><label className="mb-2 block text-sm text-slate-300">Visual style</label><select value={style} onChange={e=>setStyle(e.target.value)} className="w-full rounded-xl border border-white/10 bg-[#090d18] p-3 text-sm">{styles.map(s=><option key={s}>{s}</option>)}</select></div>
          <div><label className="mb-2 block text-sm text-slate-300">Aspect ratio</label><select value={ratio} onChange={e=>setRatio(e.target.value)} className="w-full rounded-xl border border-white/10 bg-[#090d18] p-3 text-sm"><option>16:9</option><option>9:16</option><option>1:1</option></select></div>
          <div className="sm:col-span-2"><label className="mb-2 block text-sm text-slate-300">Target duration</label><select value={duration} onChange={e=>setDuration(e.target.value)} className="w-full rounded-xl border border-white/10 bg-[#090d18] p-3 text-sm"><option>8 seconds</option><option>12 seconds</option><option>20 seconds</option></select></div>
        </div>
        <button onClick={generate} disabled={status==="working"} className="mt-6 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 px-5 py-4 font-semibold shadow-lg shadow-violet-900/30 transition hover:brightness-110 disabled:opacity-60"><Sparkles size={18}/>{status==="working"?"Preparing…":"Generate video"}</button>
        {message && <p className="mt-4 rounded-xl border border-violet-400/20 bg-violet-400/10 p-3 text-sm text-violet-100">{message}</p>}
        <p className="mt-3 text-center text-xs text-slate-500">Generation requires a connected backend and may use provider credits.</p>
      </div>
      <div className="flex flex-col gap-5">
        <div className="relative flex min-h-[310px] flex-1 flex-col items-center justify-center overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-[#1c1a35] via-[#111827] to-[#09131c] p-8 text-center">
          <div className="absolute -right-16 -top-16 h-56 w-56 rounded-full bg-violet-600/20 blur-3xl"/>
          <div className="relative mb-5 rounded-2xl border border-white/10 bg-white/5 p-5"><Film size={42} className="text-violet-200"/></div>
          <h2 className="relative text-lg font-semibold">Your canvas is ready</h2><p className="relative mt-2 max-w-xs text-sm leading-6 text-slate-400">Your generated video preview will appear here when the backend is connected.</p>
          <div className="relative mt-6 flex items-center gap-2 rounded-full border border-white/10 bg-black/20 px-4 py-2 text-xs text-slate-400"><Play size={13}/> Preview area</div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {[["Fast setup",Zap],["Creative control",WandSparkles],["Private by design",ShieldCheck]].map(([label,Icon]: any)=><div key={label} className="rounded-2xl border border-white/10 bg-[#111522] p-3 text-center"><Icon size={18} className="mx-auto mb-2 text-violet-300"/><div className="text-xs text-slate-300">{label}</div></div>)}
        </div>
      </div>
    </section>
    <footer className="mx-auto mt-14 max-w-6xl border-t border-white/10 py-6 text-center text-xs text-slate-500">© 2026 FrameForge AI Video Studio · Built for creators</footer>
  </main>;
}