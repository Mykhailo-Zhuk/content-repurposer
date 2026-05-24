"use client";

import { useQuery } from "@tanstack/react-query";
import { getJobStatus, type JobStatusResponse } from "@/lib/api";

const TERMINAL_STATUSES = new Set(["done", "failed"]);

export function useJobPolling(jobId: string | null) {
  return useQuery<JobStatusResponse>({
    queryKey: ["job", jobId],
    queryFn: () => getJobStatus(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status || TERMINAL_STATUSES.has(status)) return false;
      return 2000; // poll every 2s while processing
    },
    retry: 3,
  });
}
