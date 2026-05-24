"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Scissors, Youtube, ArrowRight } from "lucide-react";
import { submitSchema, type SubmitFormValues } from "@/lib/schemas";
import { submitJob } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Props {
  onJobCreated: (jobId: string) => void;
}

export function SubmitForm({ onJobCreated }: Props) {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<SubmitFormValues>({
    resolver: zodResolver(submitSchema),
  });

  const onSubmit = async (data: SubmitFormValues) => {
    try {
      const res = await submitJob(data.url);
      onJobCreated(res.job_id);
    } catch (err) {
      setError("url", {
        message: err instanceof Error ? err.message : "Помилка сервера",
      });
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="w-full max-w-xl mx-auto space-y-3">
      <div className="relative">
        <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
          <Youtube className="w-4 h-4 text-white/20" />
        </div>
        <input
          {...register("url")}
          type="url"
          placeholder="https://youtube.com/watch?v=..."
          disabled={isSubmitting}
          className={cn(
            "w-full bg-surface-1 border text-white text-sm",
            "pl-11 pr-4 py-3.5 rounded-xl outline-none",
            "placeholder:text-white/20 transition-all duration-200",
            "focus:border-brand/50 focus:ring-1 focus:ring-brand/20",
            errors.url
              ? "border-red-500/50"
              : "border-white/8 hover:border-white/15"
          )}
        />
      </div>

      {errors.url && (
        <p className="text-xs text-red-400 pl-1 animate-fade-in">
          {errors.url.message}
        </p>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className={cn(
          "w-full flex items-center justify-center gap-2",
          "bg-brand hover:bg-brand-dark active:scale-[0.98]",
          "text-white font-medium text-sm rounded-xl py-3.5",
          "transition-all duration-150",
          "disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
        )}
      >
        {isSubmitting ? (
          <>
            <Scissors className="w-4 h-4 animate-spin" />
            Надсилаємо...
          </>
        ) : (
          <>
            <Scissors className="w-4 h-4" />
            Нарізати Short
            <ArrowRight className="w-3.5 h-3.5 ml-0.5" />
          </>
        )}
      </button>

      <p className="text-center text-xs text-white/20">
        Ліміт: 5 відео на день · max 30 хв · потрібні субтитри
      </p>
    </form>
  );
}
