"use client";

import { useState } from "react";
import { submitUrl } from "@/lib/api";
import {
  DEFAULT_SETTINGS,
  DetectionMode,
  ProcessRequest,
  ProcessSettings,
} from "@/lib/types";
import { clsx } from "clsx";
import {
  Bot,
  Activity,
  Layers,
  Settings2,
  ChevronDown,
  ChevronUp,
  Scissors,
} from "lucide-react";

const MODES: { id: DetectionMode; label: string; desc: string; icon: React.ReactNode }[] = [
  {
    id: "ai",
    label: "AI",
    desc: "Whisper → Groq LLM analysis",
    icon: <Bot className="w-4 h-4" />,
  },
  {
    id: "signal",
    label: "Signal",
    desc: "Audio energy + scene change",
    icon: <Activity className="w-4 h-4" />,
  },
  {
    id: "hybrid",
    label: "Hybrid",
    desc: "AI + Signal cross-validated",
    icon: <Layers className="w-4 h-4" />,
  },
];

interface Props {
  onJobSubmitted: (jobId: string) => void;
  isLoading: boolean;
}

export function UrlInputPanel({ onJobSubmitted, isLoading }: Props) {
  const [url, setUrl] = useState("");
  const [settings, setSettings] = useState<ProcessSettings>(DEFAULT_SETTINGS);
  const [showSettings, setShowSettings] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!url.trim()) return;

    try {
      const payload: ProcessRequest = { url: url.trim(), settings };
      const job = await submitUrl(payload);
      onJobSubmitted(job.job_id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Submission failed");
    }
  };

  const updateSettings = (patch: Partial<ProcessSettings>) =>
    setSettings((s) => ({ ...s, ...patch }));

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* URL Input */}
      <div className="space-y-2">
        <label htmlFor="youtube-url" className="text-xs font-semibold text-white/50 uppercase tracking-widest">
          YouTube URL
        </label>
        <div className="relative">
          <input
            id="youtube-url"
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://youtube.com/watch?v=..."
            required
            disabled={isLoading}
            className={clsx(
              "w-full rounded-xl border bg-surface px-4 py-3 text-sm text-white placeholder-white/20",
              "focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent/60",
              "transition-all duration-200",
              "border-surface-border disabled:opacity-50"
            )}
          />
        </div>
        {error && (
          <p className="text-xs text-red-400 flex items-center gap-1">
            <span>⚠</span> {error}
          </p>
        )}
      </div>

      {/* Detection Mode */}
      <div className="space-y-2">
        <span className="text-xs font-semibold text-white/50 uppercase tracking-widest">
          Detection Mode
        </span>
        <div className="grid grid-cols-3 gap-2">
          {MODES.map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => updateSettings({ mode: m.id })}
              disabled={isLoading}
              className={clsx(
                "flex flex-col items-center gap-1.5 rounded-xl border p-3 text-center",
                "transition-all duration-200 cursor-pointer",
                settings.mode === m.id
                  ? "border-accent bg-accent-muted text-accent"
                  : "border-surface-border bg-surface text-white/40 hover:text-white/70 hover:border-white/20"
              )}
            >
              {m.icon}
              <span className="text-xs font-semibold">{m.label}</span>
              <span className="text-[10px] leading-tight hidden sm:block">{m.desc}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Advanced Settings Toggle */}
      <div>
        <button
          type="button"
          onClick={() => setShowSettings((v) => !v)}
          className="flex items-center gap-2 text-xs text-white/40 hover:text-white/70 transition-colors"
        >
          <Settings2 className="w-3.5 h-3.5" />
          Advanced Settings
          {showSettings ? (
            <ChevronUp className="w-3.5 h-3.5" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5" />
          )}
        </button>

        {showSettings && (
          <div className="mt-3 space-y-4 rounded-xl border border-surface-border bg-surface p-4 animate-fade-in">
            {/* Min clip duration */}
            <div className="space-y-1">
              <div className="flex justify-between items-center">
                <label className="text-xs text-white/50">Min Clip Duration</label>
                <span className="text-xs text-accent font-mono">{settings.min_clip_duration}s</span>
              </div>
              <input
                type="range"
                min={3}
                max={60}
                value={settings.min_clip_duration}
                onChange={(e) => updateSettings({ min_clip_duration: Number(e.target.value) })}
                className="w-full accent-[#e85d3a]"
              />
            </div>

            {/* Max clips */}
            <div className="space-y-1">
              <div className="flex justify-between items-center">
                <label className="text-xs text-white/50">Max Clips</label>
                <span className="text-xs text-accent font-mono">{settings.max_clips}</span>
              </div>
              <input
                type="range"
                min={1}
                max={30}
                value={settings.max_clips}
                onChange={(e) => updateSettings({ max_clips: Number(e.target.value) })}
                className="w-full accent-[#e85d3a]"
              />
            </div>

            {/* Score threshold */}
            <div className="space-y-1">
              <div className="flex justify-between items-center">
                <label className="text-xs text-white/50">Score Threshold</label>
                <span className="text-xs text-accent font-mono">
                  {settings.score_threshold.toFixed(1)}
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.1}
                value={settings.score_threshold}
                onChange={(e) => updateSettings({ score_threshold: Number(e.target.value) })}
                className="w-full accent-[#e85d3a]"
              />
            </div>

            {/* Auto-trim silence */}
            <label className="flex items-center justify-between cursor-pointer">
              <span className="text-xs text-white/50">Auto-trim Silence</span>
              <div
                onClick={() => updateSettings({ auto_trim_silence: !settings.auto_trim_silence })}
                className={clsx(
                  "relative w-9 h-5 rounded-full transition-colors cursor-pointer",
                  settings.auto_trim_silence ? "bg-accent" : "bg-surface-border"
                )}
              >
                <div
                  className={clsx(
                    "absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200",
                    settings.auto_trim_silence ? "translate-x-4.5" : "translate-x-0.5"
                  )}
                />
              </div>
            </label>

            {/* Output format */}
            <div className="flex items-center justify-between">
              <span className="text-xs text-white/50">Output Format</span>
              <div className="flex gap-1">
                {(["mp4", "webm"] as const).map((f) => (
                  <button
                    key={f}
                    type="button"
                    onClick={() => updateSettings({ output_format: f })}
                    className={clsx(
                      "px-3 py-1 rounded-lg text-xs font-mono transition-colors",
                      settings.output_format === f
                        ? "bg-accent text-white"
                        : "bg-surface-border text-white/40 hover:text-white/70"
                    )}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={isLoading || !url.trim()}
        className={clsx(
          "w-full flex items-center justify-center gap-2 rounded-xl py-3.5 text-sm font-semibold",
          "bg-accent-gradient text-white shadow-accent",
          "hover:brightness-110 active:scale-[0.98] transition-all duration-200",
          "disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
        )}
      >
        <Scissors className="w-4 h-4" />
        {isLoading ? "Processing…" : "Detect Highlights"}
      </button>
    </form>
  );
}
