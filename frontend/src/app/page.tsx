"use client";

import { useState, useCallback } from "react";
import { UrlInputPanel } from "@/components/UrlInputPanel";
import { JobProgress } from "@/components/JobProgress";
import { ClipCard } from "@/components/ClipCard";
import { ExportPanel } from "@/components/ExportPanel";
import { ApiError, getClips } from "@/lib/api";
import type { ClipsResponse } from "@/lib/types";
import { Scissors, History, Settings, Sun, Moon } from "lucide-react";
import { clsx } from "clsx";

type NavTab = "new" | "history" | "settings";

function Topbar({
  activeTab,
  onTab,
  darkMode,
  onToggleDark,
}: {
  activeTab: NavTab;
  onTab: (t: NavTab) => void;
  darkMode: boolean;
  onToggleDark: () => void;
}) {
  const TABS: { id: NavTab; label: string; icon: React.ReactNode }[] = [
    { id: "new", label: "New Clip", icon: <Scissors className="w-3.5 h-3.5" /> },
    { id: "history", label: "History", icon: <History className="w-3.5 h-3.5" /> },
    { id: "settings", label: "Settings", icon: <Settings className="w-3.5 h-3.5" /> },
  ];

  return (
    <header className="sticky top-0 z-50 border-b border-surface-border bg-surface/80 backdrop-blur-xl">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        {/* Logo */}
        <div className="flex items-center gap-2.5 flex-shrink-0">
          <div className="w-8 h-8 rounded-lg bg-accent-gradient flex items-center justify-center shadow-accent">
            <Scissors className="w-4 h-4 text-white" />
          </div>
          <span className="text-base font-bold text-white tracking-tight">
            Clipper<span className="text-accent">AI</span>
          </span>
        </div>

        {/* Nav pills */}
        <nav className="flex items-center gap-1 bg-surface-elevated rounded-xl p-1 border border-surface-border">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => onTab(t.id)}
              className={clsx(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200",
                activeTab === t.id
                  ? "bg-accent text-white shadow-accent"
                  : "text-white/40 hover:text-white/70"
              )}
            >
              {t.icon}
              <span className="hidden sm:inline">{t.label}</span>
            </button>
          ))}
        </nav>

        {/* Theme toggle */}
        <button
          onClick={onToggleDark}
          className="w-8 h-8 rounded-lg border border-surface-border flex items-center justify-center text-white/40 hover:text-white hover:border-accent/40 transition-all"
          aria-label="Toggle theme"
        >
          {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>
    </header>
  );
}

// Paginator for clip results (3 per page)
function ClipPaginator({ clips, jobId }: { clips: ClipsResponse; jobId: string }) {
  const PER_PAGE = 3;
  const [page, setPage] = useState(0);
  const total = clips.clips.length;
  const totalPages = Math.ceil(total / PER_PAGE);
  const visible = clips.clips.slice(page * PER_PAGE, (page + 1) * PER_PAGE);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white/70">
          {total} Highlight{total !== 1 ? "s" : ""} Detected
        </h2>
        {totalPages > 1 && (
          <div className="flex items-center gap-2 text-xs text-white/40">
            <button
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
              className="px-2 py-1 rounded-lg border border-surface-border hover:border-accent/40 disabled:opacity-30 transition-all"
            >
              ←
            </button>
            <span>
              {page + 1} / {totalPages}
            </span>
            <button
              disabled={page >= totalPages - 1}
              onClick={() => setPage((p) => p + 1)}
              className="px-2 py-1 rounded-lg border border-surface-border hover:border-accent/40 disabled:opacity-30 transition-all"
            >
              →
            </button>
          </div>
        )}
      </div>

      <div className="space-y-3">
        {visible.map((clip) => (
          <ClipCard key={clip.index} clip={clip} index={clip.index} />
        ))}
      </div>

      <ExportPanel result={clips} jobId={jobId} />
    </div>
  );
}

// Empty state for results panel
function EmptyResults() {
  return (
    <div className="flex flex-col items-center justify-center h-64 space-y-3 text-center">
      <div className="w-14 h-14 rounded-2xl bg-surface-elevated border border-surface-border flex items-center justify-center">
        <Scissors className="w-6 h-6 text-white/20" />
      </div>
      <p className="text-sm text-white/30">
        Paste a YouTube URL and hit <span className="text-accent">Detect Highlights</span>
      </p>
      <p className="text-xs text-white/15 max-w-xs">
        Clips will appear here once the pipeline completes
      </p>
    </div>
  );
}

export default function HomePage() {
  const [darkMode, setDarkMode] = useState(true);
  const [activeTab, setActiveTab] = useState<NavTab>("new");
  const [jobId, setJobId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [clipsResult, setClipsResult] = useState<ClipsResponse | null>(null);
  const [clipLoadError, setClipLoadError] = useState<string | null>(null);

  const handleJobSubmitted = useCallback((id: string) => {
    setJobId(id);
    setIsProcessing(true);
    setClipsResult(null);
    setClipLoadError(null);
  }, []);

  const handleDone = useCallback(async () => {
    if (!jobId) return;
    setIsProcessing(false);
    try {
      const result = await getClips(jobId);
      setClipLoadError(null);
      setClipsResult(result);
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        setClipLoadError(err.message);
        setClipsResult(null);
        return;
      }
      setClipLoadError(null);
      setClipsResult({
        job_id: jobId,
        total: 0,
        detection_mode: "hybrid",
        clips: [],
      });
    }
  }, [jobId]);

  return (
    <div className={darkMode ? "dark" : ""}>
      <div className="min-h-screen bg-surface text-white">
        <Topbar
          activeTab={activeTab}
          onTab={setActiveTab}
          darkMode={darkMode}
          onToggleDark={() => setDarkMode((v) => !v)}
        />

        <main className="mx-auto max-w-6xl px-4 sm:px-6 py-8">
          {activeTab === "new" && (
            <div className="grid grid-cols-1 lg:grid-cols-[420px_1fr] gap-6 items-start">
              {/* Left panel — Input */}
              <div className="space-y-5">
                <div className="rounded-2xl border border-surface-border bg-surface-card p-6">
                  <h1 className="text-lg font-bold text-white mb-1">
                    Detect Highlights
                  </h1>
                  <p className="text-xs text-white/40 mb-6">
                    Paste a YouTube URL to extract the best moments automatically.
                  </p>
                  <UrlInputPanel
                    onJobSubmitted={handleJobSubmitted}
                    isLoading={isProcessing}
                  />
                </div>

                {/* Job progress */}
                {jobId && (
                  <JobProgress jobId={jobId} onDone={handleDone} />
                )}
              </div>

              {/* Right panel — Results */}
              <div className="rounded-2xl border border-surface-border bg-surface-card p-6 min-h-[400px]">
                {clipLoadError ? (
                  <div className="flex flex-col items-center justify-center min-h-[280px] space-y-3 text-center px-2">
                    <p className="text-sm font-medium text-red-400">Pipeline failed</p>
                    <p className="text-xs text-white/50 max-w-lg whitespace-pre-wrap break-words">
                      {clipLoadError}
                    </p>
                  </div>
                ) : clipsResult ? (
                  clipsResult.total > 0 ? (
                    <ClipPaginator clips={clipsResult} jobId={jobId!} />
                  ) : (
                    <div className="flex flex-col items-center justify-center h-64 space-y-3 text-center">
                      <p className="text-sm text-white/40">
                        Pipeline complete — no clips in this run
                      </p>
                      <p className="text-xs text-white/20 max-w-md">
                        Try lowering <span className="text-white/50">Score threshold</span> in Advanced
                        Settings, switch detection mode to <span className="text-white/50">signal</span>, or use a
                        different video. Check worker logs if this persists.
                      </p>
                    </div>
                  )
                ) : (
                  <EmptyResults />
                )}
              </div>
            </div>
          )}

          {activeTab === "history" && (
            <div className="flex items-center justify-center h-64">
              <p className="text-white/30 text-sm">History — coming soon</p>
            </div>
          )}

          {activeTab === "settings" && (
            <div className="flex items-center justify-center h-64">
              <p className="text-white/30 text-sm">Settings — coming soon</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
