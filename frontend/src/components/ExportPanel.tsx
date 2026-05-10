"use client";

import type { ClipsResponse } from "@/lib/types";
import { Download, FileJson, FileText, Share2 } from "lucide-react";

interface Props {
  result: ClipsResponse;
  jobId: string;
}

function downloadJson(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function downloadTxt(data: ClipsResponse, filename: string) {
  const lines = data.clips.map((c, i) => {
    const m = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
    return `[${i + 1}] ${m(c.start_time)} → ${m(c.end_time)}  score=${(c.confidence_score * 100).toFixed(0)}%  ${c.summary ?? ""}`;
  });
  const blob = new Blob([lines.join("\n")], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function copyShareLink(jobId: string) {
  const url = `${window.location.origin}/?job=${jobId}`;
  navigator.clipboard.writeText(url);
}

export function ExportPanel({ result, jobId }: Props) {
  return (
    <div className="rounded-2xl border border-surface-border bg-surface-card p-5 space-y-4">
      <h3 className="text-sm font-semibold text-white/80">Export</h3>

      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={() => downloadJson(result, `clipper-${jobId}.json`)}
          className="flex items-center gap-2 justify-center px-3 py-2.5 rounded-xl border border-surface-border text-xs text-white/60 hover:text-white hover:border-accent/40 hover:bg-accent-muted transition-all"
        >
          <FileJson className="w-4 h-4" />
          JSON
        </button>

        <button
          onClick={() => downloadTxt(result, `clipper-${jobId}.txt`)}
          className="flex items-center gap-2 justify-center px-3 py-2.5 rounded-xl border border-surface-border text-xs text-white/60 hover:text-white hover:border-accent/40 hover:bg-accent-muted transition-all"
        >
          <FileText className="w-4 h-4" />
          Timestamps .txt
        </button>

        <button
          disabled
          title="Coming in Phase 2"
          className="flex items-center gap-2 justify-center px-3 py-2.5 rounded-xl border border-surface-border text-xs text-white/20 cursor-not-allowed"
        >
          <Download className="w-4 h-4" />
          Merged Reel
        </button>

        <button
          onClick={() => copyShareLink(jobId)}
          className="flex items-center gap-2 justify-center px-3 py-2.5 rounded-xl border border-surface-border text-xs text-white/60 hover:text-white hover:border-accent/40 hover:bg-accent-muted transition-all"
        >
          <Share2 className="w-4 h-4" />
          Share Link
        </button>
      </div>

      <p className="text-[10px] text-white/20">
        {result.total} clip{result.total !== 1 ? "s" : ""} · {result.detection_mode} mode
        {result.video_title ? ` · ${result.video_title}` : ""}
      </p>
    </div>
  );
}
