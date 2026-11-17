/**
 * Job polling hook — 202 job status polling for plan generation / exports.
 * Typed against the contract (GET /api/v1/jobs/{job_id}).
 */

import { useEffect, useRef, useState } from 'react';
import { apiGet } from '../../api/client';
import type { components } from '../../api/generated/schema';

type JobStatus = components['schemas']['JobStatusResponse'];

const TERMINAL: readonly string[] = ['succeeded', 'failed', 'needs_attention', 'cancelled'];

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
        const next = await apiGet('/api/v1/jobs/{job_id}', { job_id: jobId });
        if (cancelled) return;
        setJob(next);
        if (TERMINAL.includes(next.status)) {
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
