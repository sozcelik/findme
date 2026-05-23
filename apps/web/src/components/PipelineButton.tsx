"use client";

import { useState } from "react";
import { apiClient } from "@/lib/api-client";
import { useJobProgress } from "@/lib/use-job-progress";
import { AgentProgress } from "@/components/AgentProgress";
import type { AgentJob, ProgressStep } from "@findme/types";
import { Play, RotateCcw } from "lucide-react";

interface PipelineButtonProps {
  projectId: string;
  existingJob?: AgentJob | null;
}

export function PipelineButton({ projectId, existingJob }: PipelineButtonProps) {
  const [loading, setLoading] = useState(false);
  const [liveJobId, setLiveJobId] = useState<string | null>(null);
  const [liveJob, setLiveJob] = useState<AgentJob | null>(null);
  const { steps, done } = useJobProgress(liveJobId);

  async function handleRun() {
    setLoading(true);
    try {
      const { jobId } = await apiClient.post<{ jobId: string }>(
        `/api/projects/${projectId}/run-pipeline`,
        {}
      );
      setLiveJobId(jobId);
      setLiveJob({
        id: jobId,
        orgId: "",
        projectId,
        campaignId: null,
        type: "full_pipeline",
        status: "running",
        triggeredBy: null,
        celeryTaskId: null,
        inputData: null,
        outputData: null,
        progress: 0,
        progressSteps: [],
        errorMessage: null,
        creditsUsed: null,
        startedAt: new Date().toISOString(),
        completedAt: null,
      });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  const displayJob: AgentJob | null = liveJob
    ? {
        ...liveJob,
        progressSteps: steps as ProgressStep[],
        status: done ? "completed" : "running",
        progress: done ? 100 : Math.min(steps.filter((s) => s.status === "completed").length * 25, 95),
      }
    : existingJob ?? null;

  return (
    <div className="space-y-4">
      <button
        onClick={handleRun}
        disabled={loading || (!!liveJobId && !done)}
        className="inline-flex items-center gap-2 h-9 px-4 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? (
          <RotateCcw size={13} className="animate-spin" />
        ) : (
          <Play size={13} />
        )}
        {loading ? "Starting..." : liveJobId && !done ? "Running..." : "Run pipeline"}
      </button>

      {displayJob ? <AgentProgress job={displayJob} /> : null}
    </div>
  );
}
