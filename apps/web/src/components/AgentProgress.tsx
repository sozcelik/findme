"use client";

import { useJobProgress } from "@/lib/use-job-progress";
import type { AgentJob, ProgressStep } from "@findme/types";
import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";

const STEP_LABELS: Record<string, string> = {
  seo_analysis: "SEO Analysis",
  content_strategy: "Content Strategy",
  content_generation: "Content Generation",
  visibility_score: "Visibility Score",
};

function StepRow({ step }: { step: ProgressStep }) {
  return (
    <div className="flex items-start gap-3 py-2">
      <div className="mt-0.5 shrink-0">
        {step.status === "completed" ? (
          <CheckCircle2 size={15} className="text-chart-2" />
        ) : step.status === "running" ? (
          <Loader2 size={15} className="text-primary animate-spin" />
        ) : step.status === "failed" ? (
          <XCircle size={15} className="text-destructive" />
        ) : (
          <Circle size={15} className="text-muted-foreground/40" />
        )}
      </div>
      <div>
        <p className="text-[13px] font-medium text-foreground leading-tight">
          {STEP_LABELS[step.name] ?? step.name}
        </p>
        {step.message ? (
          <p className="text-xs text-muted-foreground mt-0.5">{step.message}</p>
        ) : null}
      </div>
    </div>
  );
}

interface AgentProgressProps {
  job: AgentJob;
}

export function AgentProgress({ job }: AgentProgressProps) {
  const { steps: liveSteps, done } = useJobProgress(
    job.status === "running" ? job.id : null
  );

  const steps = liveSteps.length > 0 ? liveSteps : job.progressSteps;
  const isRunning = job.status === "running" && !done;

  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-foreground">Pipeline run</h2>
        <span
          className={[
            "text-[11px] px-2 py-0.5 rounded-full font-medium",
            job.status === "completed"
              ? "bg-chart-2/15 text-chart-2"
              : job.status === "failed"
              ? "bg-destructive/10 text-destructive"
              : job.status === "running"
              ? "bg-primary/10 text-primary"
              : "bg-muted text-muted-foreground",
          ].join(" ")}
        >
          {isRunning ? "Running" : job.status}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-muted rounded-full overflow-hidden mb-4">
        <div
          className="h-full bg-primary rounded-full transition-all duration-500"
          style={{ width: `${job.progress}%` }}
        />
      </div>

      {/* Steps */}
      <div className="divide-y divide-border">
        {steps.map((step) => (
          <StepRow key={step.name} step={step} />
        ))}
      </div>

      {job.errorMessage ? (
        <p className="mt-3 text-xs text-destructive bg-destructive/5 rounded-md px-3 py-2">
          {job.errorMessage}
        </p>
      ) : null}
    </div>
  );
}
