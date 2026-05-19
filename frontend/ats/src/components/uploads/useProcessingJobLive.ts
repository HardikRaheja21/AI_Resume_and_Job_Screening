import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getProcessingAuthHeaders,
  getProcessingEvents,
  getProcessingJob,
  getProcessingStreamUrl,
} from "@/api/processing";
import type { ProcessingEvent, ProcessingJob } from "@/api/types";
import { isTerminal } from "@/components/uploads/processingUtils";

type StreamState = "connecting" | "live" | "reconnecting" | "polling" | "closed";

function parseSseEvents(buffer: string) {
  const chunks = buffer.split("\n\n");
  const complete = chunks.slice(0, -1);
  const remainder = chunks[chunks.length - 1] || "";
  const parsed = complete
    .map((chunk) => {
      const dataLine = chunk
        .split("\n")
        .find((line) => line.startsWith("data:"))
        ?.replace(/^data:\s?/, "");
      if (!dataLine) return null;
      try {
        return JSON.parse(dataLine) as Partial<ProcessingEvent> & Partial<ProcessingJob>;
      } catch {
        return null;
      }
    })
    .filter((payload): payload is Partial<ProcessingEvent> & Partial<ProcessingJob> => Boolean(payload));
  return { parsed, remainder };
}

export function useProcessingJobLive(initialJob: ProcessingJob) {
  const queryClient = useQueryClient();
  const [streamState, setStreamState] = useState<StreamState>("connecting");
  const [streamEvents, setStreamEvents] = useState<ProcessingEvent[]>([]);
  const [fallbackPolling, setFallbackPolling] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const job = useQuery({
    queryKey: ["processingJob", initialJob.id],
    queryFn: () => getProcessingJob(initialJob.id),
    initialData: initialJob,
    refetchInterval: fallbackPolling && !isTerminal(initialJob.status) ? 1600 : false,
    retry: 2,
  });

  const events = useQuery({
    queryKey: ["processingEvents", initialJob.id],
    queryFn: () => getProcessingEvents(initialJob.id),
    refetchInterval: fallbackPolling && !isTerminal(job.data?.status) ? 2500 : false,
    retry: 2,
  });

  useEffect(() => {
    if (isTerminal(job.data?.status)) {
      setStreamState("closed");
      abortRef.current?.abort();
    }
  }, [job.data?.status]);

  useEffect(() => {
    if (isTerminal(initialJob.status)) {
      setStreamState("closed");
      return;
    }

    let cancelled = false;
    let reconnectTimer: number | undefined;
    let reconnectAttempt = 0;

    async function connect() {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setStreamState(reconnectAttempt ? "reconnecting" : "connecting");

      try {
        const response = await fetch(getProcessingStreamUrl(initialJob.id), {
          headers: getProcessingAuthHeaders(),
          signal: controller.signal,
        });
        if (!response.ok || !response.body) throw new Error(`Stream failed with ${response.status}`);
        setStreamState("live");
        setFallbackPolling(false);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (!cancelled) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const result = parseSseEvents(buffer);
          buffer = result.remainder;
          result.parsed.forEach((payload) => {
            if ("processing_job_id" in payload || "step" in payload) {
              setStreamEvents((current) => [...current.slice(-40), payload as ProcessingEvent]);
            }
            if ("id" in payload && payload.id === initialJob.id && ("status" in payload || "progress" in payload)) {
              queryClient.setQueryData<ProcessingJob>(["processingJob", initialJob.id], (current) => ({
                ...(current || initialJob),
                ...(payload as Partial<ProcessingJob>),
              }));
            } else {
              void queryClient.invalidateQueries({ queryKey: ["processingJob", initialJob.id] });
            }
          });
        }
        throw new Error("Stream closed");
      } catch {
        if (cancelled || controller.signal.aborted || isTerminal(job.data?.status)) return;
        reconnectAttempt += 1;
        if (reconnectAttempt >= 2) {
          setFallbackPolling(true);
          setStreamState("polling");
          return;
        }
        setStreamState("reconnecting");
        reconnectTimer = window.setTimeout(connect, Math.min(5000, 1000 * reconnectAttempt));
      }
    }

    void connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      abortRef.current?.abort();
    };
  }, [initialJob, initialJob.id, initialJob.status, job.data?.status, queryClient]);

  const combinedEvents = useMemo(() => {
    const byId = new Map<string, ProcessingEvent>();
    [...(events.data || []), ...streamEvents].forEach((event, index) => {
      byId.set(String(event.id || `${event.processing_job_id}-${event.step}-${index}`), event);
    });
    return Array.from(byId.values()).sort((a, b) => new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime());
  }, [events.data, streamEvents]);

  return {
    job: job.data,
    events: combinedEvents,
    streamState,
    isLoading: job.isLoading,
    isError: job.isError,
    refetch: () => {
      void job.refetch();
      void events.refetch();
    },
  };
}
