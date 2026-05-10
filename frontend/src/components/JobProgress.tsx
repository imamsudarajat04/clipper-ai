"use client";

import { useJobSSE } from "@/hooks/useJobSSE";
import { JobStatus } from "@/lib/types";
import { clsx } from "clsx";

const STAGE_LABELS: Record<string, string> = {
  queued: "Queued",
  download: "Downloading Video",
  extract: "Extracting Audio",
  transcribe: "Transcribing",
  analyze: "Analyzing Highlights",
  done: "Complete",
  error: "Error",
};

const STAGE_ORDER = ["queued", "download", "extract", "transcribe", "analyze", "done"];

interface Props {
  jobId: string | null;
  onDone?: () => void;
}

export function JobProgress({ jobId, onDone }: Props) {
  const { status, percent, message, stage, isDone, error, isConnected } = useJobSSE(jobId);

  if (isDone && onDone) {
    setTimeout(onDone, 600);
  }

  if (!jobId) return null;

  const isFailed = status === "failed";
  const currentStageIdx = STAGE_ORDER.indexOf(stage);

  return (
    <div className="rounded-2xl border border-surface-border bg-surface-card p-6 space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-white/80">
          {isFailed ? "❌ Pipeline Failed" : isDone ? "✅ Done" : "⚡ Processing…"}
        </span>
        <span
          className={clsx(
            "text-xs font-mono px-2 py-0.5 rounded-full",
            isFailed
              ? "bg-red-500/15 text-red-400"
              : isDone
              ? "bg-green-500/15 text-green-400"
              : "bg-accent-muted text-accent"
          )}
        >
          {percent}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-2 w-full rounded-full bg-surface-border overflow-hidden">
        <div
          className={clsx(
            "h-full rounded-full transition-all duration-700 ease-out",
            isFailed
              ? "bg-red-500"
              : isDone
              ? "bg-green-500"
              : "bg-gradient-to-r from-accent to-accent-light"
          )}
          style={{ width: `${percent}%` }}
        />
      </div>

      {/* Stage steps */}
      <div className="flex justify-between">
        {STAGE_ORDER.filter((s) => s !== "queued").map((s, i) => {
          const idx = STAGE_ORDER.indexOf(s);
          const isComplete = currentStageIdx > idx;
          const isActive = currentStageIdx === idx && !isDone;
          return (
            <div key={s} className="flex flex-col items-center gap-1">
              <div
                className={clsx(
                  "w-2 h-2 rounded-full transition-all duration-300",
                  isComplete || isDone
                    ? "bg-accent"
                    : isActive
                    ? "bg-accent animate-pulse-slow"
                    : "bg-surface-border"
                )}
              />
              <span
                className={clsx(
                  "text-[10px] hidden sm:block",
                  isComplete || isDone
                    ? "text-accent"
                    : isActive
                    ? "text-white/70"
                    : "text-white/25"
                )}
              >
                {STAGE_LABELS[s]?.split(" ")[0]}
              </span>
            </div>
          );
        })}
      </div>

      {/* Status message */}
      <p
        className={clsx(
          "text-sm",
          isFailed ? "text-red-400" : "text-white/50"
        )}
      >
        {error ?? message}
      </p>

      {/* Job ID */}
      <p className="text-[10px] text-white/20 font-mono break-all">job: {jobId}</p>
    </div>
  );
}
