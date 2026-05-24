import { cn } from "@/lib/utils";

interface ProgressBarProps {
  progress: number;
  animated?: boolean;
  className?: string;
}

export function ProgressBar({ progress, animated = true, className }: ProgressBarProps) {
  return (
    <div className={cn("w-full bg-surface-2 rounded-full h-1.5 overflow-hidden", className)}>
      <div
        className={cn(
          "h-full rounded-full transition-all duration-500 ease-out",
          animated && progress < 100 ? "progress-animated" : "bg-brand"
        )}
        style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
      />
    </div>
  );
}
