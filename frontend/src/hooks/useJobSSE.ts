"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Job, JobStatus } from "@/lib/types";
import { sseUrl } from "@/lib/api";

interface SSEState {
  job: Job | null;
  status: JobStatus | null;
  percent: number;
  message: string;
  stage: string;
  isConnected: boolean;
  isDone: boolean;
  error: string | null;
}

const INITIAL_STATE: SSEState = {
  job: null,
  status: null,
  percent: 0,
  message: "",
  stage: "",
  isConnected: false,
  isDone: false,
  error: null,
};

export function useJobSSE(jobId: string | null) {
  const [state, setState] = useState<SSEState>(INITIAL_STATE);
  const esRef = useRef<EventSource | null>(null);

  const reset = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    setState(INITIAL_STATE);
  }, []);

  useEffect(() => {
    if (!jobId) return;

    const es = new EventSource(sseUrl(jobId));
    esRef.current = es;

    setState((s) => ({ ...s, isConnected: true, error: null }));

    es.addEventListener("progress", (e) => {
      try {
        const data: Job & {
          stage: string;
          percent: number;
          message: string;
        } = JSON.parse(e.data);

        setState({
          job: data,
          status: data.status,
          percent: data.percent ?? 0,
          message: data.message ?? "",
          stage: data.stage ?? "",
          isConnected: true,
          isDone: false,
          error: null,
        });
      } catch {
        // malformed JSON — ignore
      }
    });

    es.addEventListener("done", () => {
      setState((s) => ({ ...s, isDone: true, percent: 100, isConnected: false }));
      es.close();
    });

    es.addEventListener("error", () => {
      setState((s) => ({
        ...s,
        isConnected: false,
        error: "Lost connection to server",
      }));
      es.close();
    });

    return () => {
      es.close();
    };
  }, [jobId]);

  return { ...state, reset };
}
