"use client";

import { Download, CheckCircle, XCircle, Loader2, Tag } from "lucide-react";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { getDownloadUrl, type JobStatusResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

const STATUS_STEPS = [
  { key: "queued", label: "Черга" },
  { key: "downloading", label: "Завантаження" },
  { key: "analyzing", label: "AI аналіз" },
  { key: "rendering", label: "Рендер" },
  { key: "done", label: "Готово" },
];

const STATUS_ORDER = STATUS_STEPS.map((s) => s.key);

interface Props {
  job: JobStatusResponse;
}

export function JobStatusCard({ job }: Props) {
  const currentIdx = STATUS_ORDER.indexOf(job.status);
  const isFailed = job.status === "failed";
  const isDone = job.status === "done";

  return (
    <div className="animate-slide-up w-full max-w-xl mx-auto">
      <div className="bg-surface-1 border border-white/5 rounded-2xl p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          {isFailed ? (
            <XCircle className="text-red-500 w-5 h-5 flex-shrink-0" />
          ) : isDone ? (
            <CheckCircle className="text-green-400 w-5 h-5 flex-shrink-0" />
          ) : (
            <Loader2 className="text-brand w-5 h-5 flex-shrink-0 animate-spin" />
          )}
          <p className="text-sm font-medium text-white/80">{job.message}</p>
        </div>

        {/* Progress bar */}
        {!isFailed && (
          <ProgressBar progress={job.progress} animated={!isDone} />
        )}

        {/* Steps */}
        {!isFailed && (
          <div className="flex items-center justify-between">
            {STATUS_STEPS.filter((s) => s.key !== "failed").map((step, i) => {
              const stepIdx = STATUS_ORDER.indexOf(step.key);
              const isComplete = stepIdx < currentIdx || isDone;
              const isActive = stepIdx === currentIdx && !isDone;

              return (
                <div key={step.key} className="flex flex-col items-center gap-1.5">
                  <div
                    className={cn(
                      "w-2 h-2 rounded-full transition-all duration-300",
                      isComplete
                        ? "bg-brand"
                        : isActive
                        ? "bg-brand/60 animate-pulse-slow"
                        : "bg-white/10"
                    )}
                  />
                  <span
                    className={cn(
                      "text-[10px] font-medium",
                      isComplete || isActive ? "text-white/60" : "text-white/20"
                    )}
                  >
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {/* Error */}
        {isFailed && job.error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
            <p className="text-sm text-red-400">{job.error}</p>
          </div>
        )}

        {/* Result */}
        {isDone && job.result && (
          <div className="space-y-4 animate-fade-in">
            <div className="border-t border-white/5 pt-4 space-y-3">
              <h3 className="font-display text-xl font-bold text-white tracking-tight">
                {job.result.title}
              </h3>
              <p className="text-sm text-white/50 leading-relaxed">
                {job.result.description}
              </p>
              {job.result.tags.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {job.result.tags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center gap-1 text-xs bg-white/5 text-white/40 px-2.5 py-1 rounded-full"
                    >
                      <Tag className="w-2.5 h-2.5" />
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <a
              href={getDownloadUrl(job.job_id)}
              download
              className="flex items-center justify-center gap-2 w-full bg-brand hover:bg-brand-dark active:scale-[0.98] transition-all duration-150 text-white font-medium text-sm rounded-xl py-3 px-4"
            >
              <Download className="w-4 h-4" />
              Завантажити Short
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
