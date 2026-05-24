"use client";

import { useState, useEffect, useRef } from "react";
import { useJobProgress } from "@/lib/use-job-progress";
import { apiClient } from "@/lib/api-client";
import { VisibilityScore } from "@/components/VisibilityScore";
import Link from "next/link";
import {
  Loader2,
  Play,
  RefreshCw,
  CheckCircle2,
  Circle,
  XCircle,
  ChevronRight,
  Plus,
  X,
  Tag,
  BarChart2,
  ArrowRight,
} from "lucide-react";
import type { Project, ProgressStep } from "@findme/types";

interface JobSummary {
  id: string;
  type: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  progress: number;
  progressSteps: ProgressStep[];
  outputData: Record<string, unknown> | null;
  errorMessage: string | null;
  startedAt: string | null;
  completedAt: string | null;
}

interface Topic {
  title: string;
  keyword: string;
}

interface ArticleRef {
  id: string;
  title: string;
  wordCount: number;
}

interface Props {
  projectId: string;
  project: Project;
  initialJobs: JobSummary[];
}

function StatusBadge({ status }: { status: JobSummary["status"] }) {
  const map: Record<string, string> = {
    completed: "bg-chart-2/15 text-chart-2",
    failed: "bg-destructive/10 text-destructive",
    running: "bg-primary/10 text-primary",
    queued: "bg-muted text-muted-foreground",
    cancelled: "bg-muted text-muted-foreground",
  };
  return (
    <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${map[status] ?? map.queued}`}>
      {status}
    </span>
  );
}

function StepRow({ step }: { step: ProgressStep }) {
  return (
    <div className="flex items-start gap-3 py-2">
      <div className="mt-0.5 shrink-0">
        {step.status === "completed" ? (
          <CheckCircle2 size={14} className="text-chart-2" />
        ) : step.status === "running" ? (
          <Loader2 size={14} className="text-primary animate-spin" />
        ) : step.status === "failed" ? (
          <XCircle size={14} className="text-destructive" />
        ) : (
          <Circle size={14} className="text-muted-foreground/30" />
        )}
      </div>
      <div>
        <p className="text-[12.5px] font-medium text-foreground leading-tight">{step.name}</p>
        {step.message ? (
          <p className="text-[11px] text-muted-foreground mt-0.5">{step.message}</p>
        ) : null}
      </div>
    </div>
  );
}

function StatPill({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="bg-muted/50 rounded-lg px-3 py-2 text-center">
      <p className="text-lg font-bold font-mono text-foreground leading-none">{String(value ?? "—")}</p>
      <p className="text-[10px] text-muted-foreground mt-0.5">{label}</p>
    </div>
  );
}

export function ProjectDashboard({ projectId, project, initialJobs }: Props) {
  const firstSeoJob = initialJobs.find((j) => j.type === "seo_analysis") ?? null;
  const firstContentJob = initialJobs.find((j) => j.type === "content_gen") ?? null;

  const [seoJob, setSeoJob] = useState<JobSummary | null>(firstSeoJob);
  const [contentJob, setContentJob] = useState<JobSummary | null>(firstContentJob);

  const isActive = (j: JobSummary | null) =>
    j?.status === "running" || j?.status === "queued";

  const [activeSeoJobId, setActiveSeoJobId] = useState<string | null>(
    isActive(firstSeoJob) ? firstSeoJob!.id : null
  );
  const [activeContentJobId, setActiveContentJobId] = useState<string | null>(
    isActive(firstContentJob) ? firstContentJob!.id : null
  );

  const [topics, setTopics] = useState<Topic[]>(
    (firstSeoJob?.outputData?.suggested_topics as Topic[] | undefined) ?? []
  );

  const [seoError, setSeoError] = useState<string | null>(null);
  const [contentError, setContentError] = useState<string | null>(null);

  const { steps: seoSteps, done: seoDone } = useJobProgress(activeSeoJobId);
  const { steps: contentSteps, done: contentDone } = useJobProgress(activeContentJobId);

  const fetchedSeoRef = useRef<string | null>(null);
  const fetchedContentRef = useRef<string | null>(null);

  useEffect(() => {
    if (!seoDone || !activeSeoJobId) return;
    if (fetchedSeoRef.current === activeSeoJobId) return;
    fetchedSeoRef.current = activeSeoJobId;
    const id = activeSeoJobId;
    setActiveSeoJobId(null);
    apiClient.get<JobSummary>(`/api/jobs/${id}`).then((job) => {
      setSeoJob(job);
      const t = (job.outputData?.suggested_topics as Topic[] | undefined) ?? [];
      if (t.length > 0) setTopics(t);
    });
  }, [seoDone, activeSeoJobId]);

  useEffect(() => {
    if (!contentDone || !activeContentJobId) return;
    if (fetchedContentRef.current === activeContentJobId) return;
    fetchedContentRef.current = activeContentJobId;
    const id = activeContentJobId;
    setActiveContentJobId(null);
    apiClient.get<JobSummary>(`/api/jobs/${id}`).then((job) => {
      setContentJob(job);
    });
  }, [contentDone, activeContentJobId]);

  const seoRunning = activeSeoJobId !== null;
  const contentRunning = activeContentJobId !== null;

  const handleRunSeo = async () => {
    setSeoError(null);
    try {
      const { jobId } = await apiClient.post<{ jobId: string }>(
        `/api/projects/${projectId}/run-seo-analysis`,
        {}
      );
      setSeoJob({
        id: jobId,
        type: "seo_analysis",
        status: "queued",
        progress: 0,
        progressSteps: [],
        outputData: null,
        errorMessage: null,
        startedAt: null,
        completedAt: null,
      });
      setActiveSeoJobId(jobId);
      fetchedSeoRef.current = null;
    } catch (e) {
      setSeoError(e instanceof Error ? e.message : "Failed to start SEO analysis");
    }
  };

  const handleRunContent = async () => {
    setContentError(null);
    try {
      const { jobId } = await apiClient.post<{ jobId: string }>(
        `/api/projects/${projectId}/run-content-generation`,
        { topics }
      );
      setContentJob({
        id: jobId,
        type: "content_gen",
        status: "queued",
        progress: 0,
        progressSteps: [],
        outputData: null,
        errorMessage: null,
        startedAt: null,
        completedAt: null,
      });
      setActiveContentJobId(jobId);
      fetchedContentRef.current = null;
    } catch (e) {
      setContentError(e instanceof Error ? e.message : "Failed to start content generation");
    }
  };

  const updateTopic = (i: number, field: keyof Topic, value: string) => {
    setTopics((prev) => prev.map((t, idx) => (idx === i ? { ...t, [field]: value } : t)));
  };
  const removeTopic = (i: number) => setTopics((prev) => prev.filter((_, idx) => idx !== i));
  const addTopic = () => setTopics((prev) => [...prev, { title: "", keyword: "" }]);

  const seoOutputData = seoJob?.outputData;
  const articles = (contentJob?.outputData?.articles as ArticleRef[] | undefined) ?? [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Sidebar */}
      <div className="lg:col-span-1 space-y-4">
        <VisibilityScore score={project.visibilityScore} />

        {project.businessDescription ? (
          <div className="bg-card border border-border rounded-xl p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">
              About
            </p>
            <p className="text-xs text-foreground/80 leading-relaxed">{project.businessDescription}</p>
          </div>
        ) : null}

        <div className="flex flex-col gap-1.5">
          <Link
            href={`/projects/${projectId}/keywords`}
            className="inline-flex items-center gap-2 h-8 px-3 border border-border rounded-md text-[12.5px] text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <Tag size={12} />
            Manage Keywords
          </Link>
          <Link
            href={`/visibility?projectId=${projectId}`}
            className="inline-flex items-center gap-2 h-8 px-3 border border-border rounded-md text-[12.5px] text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <BarChart2 size={12} />
            Visibility History
          </Link>
        </div>
      </div>

      {/* Pipeline cards */}
      <div className="lg:col-span-2 space-y-4">

        {/* ── SEO Analysis ─────────────────────────────── */}
        <div className="bg-card border border-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-sm font-semibold text-foreground">SEO Analysis</h2>
            <div className="flex items-center gap-2.5">
              {seoJob && !seoRunning && <StatusBadge status={seoJob.status} />}
              <button
                onClick={handleRunSeo}
                disabled={seoRunning}
                className="inline-flex items-center gap-1.5 h-7 px-3 rounded-md text-[12px] font-medium bg-primary/10 text-primary hover:bg-primary/15 transition-colors disabled:opacity-50 disabled:pointer-events-none"
              >
                {seoRunning ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : seoJob ? (
                  <RefreshCw size={12} />
                ) : (
                  <Play size={12} />
                )}
                {seoRunning ? "Running…" : seoJob ? "Re-run" : "Run Analysis"}
              </button>
            </div>
          </div>

          <p className="text-[11px] text-muted-foreground mb-4">
            Analyze keywords, find competitors, and generate content topics.
          </p>

          {/* Live progress */}
          {seoRunning && seoSteps.length > 0 && (
            <div className="divide-y divide-border mb-4 border border-border rounded-lg px-3">
              {seoSteps.map((step) => (
                <StepRow key={step.name} step={step} />
              ))}
            </div>
          )}

          {/* Error */}
          {(seoError ?? (seoJob?.status === "failed" ? seoJob.errorMessage : null)) && (
            <p className="text-xs text-destructive bg-destructive/5 rounded-md px-3 py-2 mb-3">
              {seoError ?? seoJob?.errorMessage}
            </p>
          )}

          {/* Results */}
          {seoJob?.status === "completed" && seoOutputData && (
            <div className="space-y-5">
              {/* Stats */}
              <div className="grid grid-cols-2 gap-3">
                <StatPill label="Keywords analyzed" value={seoOutputData.keywords_analyzed} />
                <StatPill label="Competitors found" value={seoOutputData.competitors_found} />
              </div>

              {/* Editable topic list */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Suggested Topics
                  </p>
                  <span className="text-[11px] text-muted-foreground">{topics.length} topics</span>
                </div>

                {topics.length === 0 ? (
                  <p className="text-xs text-muted-foreground py-2">
                    No topics parsed from brief — add topics manually below.
                  </p>
                ) : (
                  <div className="space-y-2 mb-2">
                    {topics.map((topic, i) => (
                      <div key={i} className="flex items-start gap-2">
                        <div className="flex-1 space-y-1">
                          <input
                            value={topic.title}
                            onChange={(e) => updateTopic(i, "title", e.target.value)}
                            placeholder="Article title…"
                            className="w-full bg-muted/50 border border-border rounded-md px-2.5 py-1.5 text-[13px] text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/40"
                          />
                          <input
                            value={topic.keyword}
                            onChange={(e) => updateTopic(i, "keyword", e.target.value)}
                            placeholder="Focus keyword…"
                            className="w-full bg-muted/30 border border-border/60 rounded-md px-2.5 py-1 text-[11.5px] text-muted-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:ring-1 focus:ring-primary/30"
                          />
                        </div>
                        <button
                          onClick={() => removeTopic(i)}
                          className="mt-1.5 p-1 rounded text-muted-foreground/50 hover:text-destructive hover:bg-destructive/10 transition-colors"
                        >
                          <X size={13} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                <button
                  onClick={addTopic}
                  className="inline-flex items-center gap-1.5 text-[12px] text-muted-foreground hover:text-foreground transition-colors"
                >
                  <Plus size={12} />
                  Add topic
                </button>
              </div>

              {/* Generate content CTA */}
              {topics.filter((t) => t.title.trim()).length > 0 && (
                <button
                  onClick={handleRunContent}
                  disabled={contentRunning}
                  className="w-full inline-flex items-center justify-center gap-2 h-9 px-4 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:pointer-events-none"
                >
                  {contentRunning ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <ArrowRight size={14} />
                  )}
                  {contentRunning
                    ? "Generating…"
                    : `Generate Content — ${topics.filter((t) => t.title.trim()).length} article${topics.filter((t) => t.title.trim()).length !== 1 ? "s" : ""}`}
                </button>
              )}
            </div>
          )}

          {/* Empty state */}
          {!seoJob && !seoRunning && (
            <div className="py-4 text-center border border-dashed border-border rounded-lg">
              <p className="text-xs text-muted-foreground">
                Run SEO analysis to discover keyword opportunities and generate content topics.
              </p>
            </div>
          )}
        </div>

        {/* ── Content Generation ───────────────────────── */}
        {(contentJob || (seoJob?.status === "completed" && topics.length > 0)) && (
          <div className="bg-card border border-border rounded-xl p-5">
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-sm font-semibold text-foreground">Generated Content</h2>
              <div className="flex items-center gap-2.5">
                {contentJob && !contentRunning && <StatusBadge status={contentJob.status} />}
                {contentJob?.status === "completed" && (
                  <Link
                    href={`/content?project_id=${projectId}`}
                    className="text-[11.5px] text-primary hover:underline"
                  >
                    View all
                  </Link>
                )}
              </div>
            </div>

            <p className="text-[11px] text-muted-foreground mb-4">
              AI-generated articles based on your approved topics.
            </p>

            {/* Live progress */}
            {contentRunning && contentSteps.length > 0 && (
              <div className="divide-y divide-border mb-4 border border-border rounded-lg px-3">
                {contentSteps.map((step) => (
                  <StepRow key={step.name} step={step} />
                ))}
              </div>
            )}

            {contentRunning && contentSteps.length === 0 && (
              <div className="flex items-center gap-2 text-xs text-muted-foreground py-2">
                <Loader2 size={12} className="animate-spin" />
                Queued…
              </div>
            )}

            {/* Error */}
            {(contentError ?? (contentJob?.status === "failed" ? contentJob.errorMessage : null)) && (
              <p className="text-xs text-destructive bg-destructive/5 rounded-md px-3 py-2 mb-3">
                {contentError ?? contentJob?.errorMessage}
              </p>
            )}

            {/* Articles list */}
            {contentJob?.status === "completed" && articles.length > 0 && (
              <div className="space-y-1">
                {articles.map((article) => (
                  <Link
                    key={article.id}
                    href={`/content/${article.id}`}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-muted/50 transition-colors group"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] font-medium text-foreground truncate">{article.title}</p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        {article.wordCount?.toLocaleString()} words
                      </p>
                    </div>
                    <span className="shrink-0 text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-medium">
                      draft
                    </span>
                    <ChevronRight
                      size={14}
                      className="shrink-0 text-muted-foreground/40 group-hover:text-muted-foreground transition-colors"
                    />
                  </Link>
                ))}
              </div>
            )}

            {contentJob?.status === "completed" && articles.length === 0 && (
              <p className="text-xs text-muted-foreground py-2">No articles generated.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
