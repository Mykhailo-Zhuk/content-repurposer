export type JobStatus =
  | "queued"
  | "downloading"
  | "analyzing"
  | "rendering"
  | "done"
  | "failed";

export interface JobResult {
  video_url: string;
  title: string;
  description: string;
  tags: string[];
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  progress: number;
  message: string;
  result?: JobResult;
  error?: string;
}

export interface SubmitResponse {
  job_id: string;
  status: JobStatus;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_BASE = `${API_URL}/api`;

export async function submitJob(url: string): Promise<SubmitResponse> {
  const res = await fetch(`${API_BASE}/jobs/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Помилка сервера");
  }

  return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`);

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "Job not found");
  }

  return res.json();
}

export function getDownloadUrl(jobId: string): string {
  return `${API_BASE}/jobs/${jobId}/download`;
}
