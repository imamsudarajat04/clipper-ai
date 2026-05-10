"use client";

import type { Clip } from "@/lib/types";
import { clsx } from "clsx";
import { Clock, Star, Download, Copy, Play } from "lucide-react";
import { clipMediaUrl } from "@/lib/api";

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color =
    score >= 0.8
      ? "text-green-400 bg-green-500/10 border-green-500/20"
      : score >= 0.5
      ? "text-accent bg-accent-muted border-accent/20"
      : "text-white/40 bg-white/5 border-white/10";

  return (
    <span
      className={clsx(
        "text-[11px] font-semibold px-2 py-0.5 rounded-full border",
        color
      )}
    >
      {pct}%
    </span>
  );
}

interface Props {
  clip: Clip;
  index: number;
}

export function ClipCard({ clip, index }: Props) {
  const downloadUrl = clip.clip_filename ? clipMediaUrl(clip.clip_filename) : null;

  const copyTimestamp = () => {
    const ts = `${formatTime(clip.start_time)} → ${formatTime(clip.end_time)}`;
    navigator.clipboard.writeText(ts);
  };

  return (
    <div className="group rounded-2xl border border-surface-border bg-surface-card p-5 space-y-4 hover:border-accent/30 hover:shadow-card-hover transition-all duration-300 animate-slide-up">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="flex items-center justify-center w-7 h-7 rounded-lg bg-accent-muted text-accent text-xs font-bold">
            {index + 1}
          </span>
          <div>
            <div className="flex items-center gap-2">
              <Clock className="w-3.5 h-3.5 text-white/30" />
              <span className="text-xs text-white/60 font-mono">
                {formatTime(clip.start_time)} → {formatTime(clip.end_time)}
              </span>
            </div>
            <p className="text-[11px] text-white/30 mt-0.5">
              {clip.duration.toFixed(1)}s · {clip.detection_source}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Star className="w-3.5 h-3.5 text-white/20" />
          <ScoreBadge score={clip.confidence_score} />
        </div>
      </div>

      {/* Summary */}
      {clip.summary && (
        <p className="text-sm text-white/70 leading-relaxed line-clamp-2">{clip.summary}</p>
      )}

      {/* Keywords */}
      {clip.keywords.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {clip.keywords.slice(0, 5).map((kw) => (
            <span
              key={kw}
              className="text-[10px] px-2 py-0.5 rounded-full bg-surface border border-surface-border text-white/40"
            >
              {kw}
            </span>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-1 border-t border-surface-border">
        {downloadUrl ? (
          <a
            href={downloadUrl}
            download
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-accent text-white hover:brightness-110 transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            Download
          </a>
        ) : (
          <button
            disabled
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-border text-white/30 cursor-not-allowed"
          >
            <Play className="w-3.5 h-3.5" />
            Preview
          </button>
        )}

        <button
          onClick={copyTimestamp}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-surface-border text-white/50 hover:text-white hover:border-white/30 transition-all"
        >
          <Copy className="w-3.5 h-3.5" />
          Copy Timestamp
        </button>
      </div>
    </div>
  );
}
