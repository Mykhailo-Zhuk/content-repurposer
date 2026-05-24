"use client";

import { useState } from "react";
import { Scissors } from "lucide-react";
import { SubmitForm } from "@/components/features/SubmitForm";
import { JobStatusCard } from "@/components/features/JobStatusCard";
import { useJobPolling } from "@/hooks/useJobPolling";

export default function Home() {
  const [jobId, setJobId] = useState<string | null>(null);
  const { data: job } = useJobPolling(jobId);

  const handleReset = () => setJobId(null);

  return (
    <main className="min-h-screen bg-surface flex flex-col">
      {/* Top bar */}
      <header className="border-b border-white/5 px-6 py-4">
        <div className="max-w-xl mx-auto flex items-center gap-2">
          <div className="w-7 h-7 bg-brand rounded-lg flex items-center justify-center">
            <Scissors className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="font-display text-base font-bold text-white tracking-wide uppercase">
            Repurposer
          </span>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-16 space-y-10">
        {/* Hero */}
        <div className="text-center space-y-3 max-w-lg">
          <h1
            className="font-display font-black text-5xl md:text-6xl text-white leading-none tracking-tight uppercase"
            style={{ fontFamily: "var(--font-display)" }}
          >
            YouTube → <span className="text-brand">Shorts</span>
          </h1>
          <p className="text-sm text-white/40 max-w-sm mx-auto leading-relaxed">
            Вставляєш посилання — AI знаходить найкращий момент і нарізає готовий short
          </p>
        </div>

        {/* Form or Status */}
        {!jobId ? (
          <SubmitForm onJobCreated={setJobId} />
        ) : (
          <div className="w-full max-w-xl space-y-4">
            {job && <JobStatusCard job={job} />}
            {job?.status === "done" || job?.status === "failed" ? (
              <button
                onClick={handleReset}
                className="w-full max-w-xl text-xs text-white/30 hover:text-white/60 transition-colors py-2"
              >
                ← Обробити інше відео
              </button>
            ) : null}
          </div>
        )}

        {/* Features */}
        {!jobId && (
          <div className="grid grid-cols-3 gap-3 max-w-xl w-full">
            {[
              { label: "AI аналіз", desc: "Gemini знаходить пік відео" },
              { label: "Вертикальний", desc: "1080×1920 для будь-якої платформи" },
              { label: "Опис + теги", desc: "Готово до публікації" },
            ].map((f) => (
              <div
                key={f.label}
                className="bg-surface-1 border border-white/5 rounded-xl p-4 space-y-1"
              >
                <p className="text-xs font-medium text-white/70">{f.label}</p>
                <p className="text-xs text-white/25 leading-snug">{f.desc}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
