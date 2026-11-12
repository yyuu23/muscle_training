/**
 * Job polling hook — 202 job status polling for plan generation / exports
 */

import { useEffect, useRef, useState } from 'react';
import { apiFetch } from '../../api/client';

export interface JobStatus {
  job_id: string;
  status: 'queued' | 'running' | 'waiting_external' | 'succeeded' | 'failed' | 'needs_attention' | 'cancelled';
  phase?: string | null;
  error_code?: string | null;
  result_ref?: Record<string, unknown> | null;
}

export function useJobPolling(jobId: string | null, intervalMs = 2000) {
  const [job, setJob] = useState<JobStatus | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!jobId) {
      setJob(null);
      return;
    }

    let cancelled = false;
    const poll = async () => {
      try {
        const next = await apiFetch<JobStatus>(`/jobs/${jobId}`);
        if (cancelled) return;
        setJob(next);
        if (next.status === 'succeeded' || next.status === 'failed' || next.status === 'needs_attention') {
          if (timer.current !== null) clearInterval(timer.current);
          timer.current = null;
        }
      } catch {
        if (!cancelled && timer.current === null) return;
      }
    };

    void poll();
    timer.current = window.setInterval(poll, intervalMs);
    return () => {
      cancelled = true;
      if (timer.current !== null) clearInterval(timer.current);
      timer.current = null;
    };
  }, [jobId, intervalMs]);

  return job;
}
