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
  Copy,
  Check,
  Zap,
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
  aeoScore?: number;
}

interface CitationResult {
  id: string;
  query: string;
  model: string;
  mentioned: boolean;
  position: number | null;
  sentiment: string;
  excerpt: string | null;
  checkedAt: string;
}

interface ModelSummary {
  queries_run: number;
  mentioned_count: number;
  mention_rate: number; // 0-100
  avg_position: number | null;
}

// summary is flat: { [model_name]: ModelSummary }
type CitationSummary = Record<string, ModelSummary>;

function AeoScoreBadge({ score }: { score: number }) {
  const color =
    score >= 70 ? "bg-chart-2/15 text-chart-2" :
    score >= 45 ? "bg-chart-5/15 text-chart-5" :
    "bg-destructive/10 text-destructive";
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-medium ${color}`}>
      AEO {score}
    </span>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={copy}
      className="inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
    >
      {copied ? <Check size={11} className="text-chart-2" /> : <Copy size={11} />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
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
  const firstCitationJob = initialJobs.find((j) => j.type === "citation_check") ?? null;

  const [seoJob, setSeoJob] = useState<JobSummary | null>(firstSeoJob);
  const [contentJob, setContentJob] = useState<JobSummary | null>(firstContentJob);
  const [citationJob, setCitationJob] = useState<JobSummary | null>(firstCitationJob);

  const isActive = (j: JobSummary | null) =>
    j?.status === "running" || j?.status === "queued";

  const [activeSeoJobId, setActiveSeoJobId] = useState<string | null>(
    isActive(firstSeoJob) ? firstSeoJob!.id : null
  );
  const [activeContentJobId, setActiveContentJobId] = useState<string | null>(
    isActive(firstContentJob) ? firstContentJob!.id : null
  );
  const [activeCitationJobId, setActiveCitationJobId] = useState<string | null>(
    isActive(firstCitationJob) ? firstCitationJob!.id : null
  );

  const [topics, setTopics] = useState<Topic[]>(
    (firstSeoJob?.outputData?.suggested_topics as Topic[] | undefined) ?? []
  );

  const [seoError, setSeoError] = useState<string | null>(null);
  const [contentError, setContentError] = useState<string | null>(null);
  const [citationError, setCitationError] = useState<string | null>(null);
  const [citationResults, setCitationResults] = useState<CitationResult[]>([]);
  const [llmsTxt, setLlmsTxt] = useState<string | null>(null);
  const [llmsTxtOpen, setLlmsTxtOpen] = useState(false);

  const { steps: seoSteps, done: seoDone } = useJobProgress(activeSeoJobId);
  const { steps: contentSteps, done: contentDone } = useJobProgress(activeContentJobId);
  const { steps: citationSteps, done: citationDone } = useJobProgress(activeCitationJobId);

  const fetchedSeoRef = useRef<string | null>(null);
  const fetchedContentRef = useRef<string | null>(null);
  const fetchedCitationRef = useRef<string | null>(null);

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

  useEffect(() => {
    if (!citationDone || !activeCitationJobId) return;
    if (fetchedCitationRef.current === activeCitationJobId) return;
    fetchedCitationRef.current = activeCitationJobId;
    const id = activeCitationJobId;
    setActiveCitationJobId(null);
    apiClient.get<JobSummary>(`/api/jobs/${id}`).then((job) => {
      setCitationJob(job);
      return apiClient.get<CitationResult[]>(
        `/api/projects/${projectId}/citation-results?job_id=${id}`
      );
    }).then((results) => {
      setCitationResults(results);
    }).catch(() => {});
  }, [citationDone, activeCitationJobId, projectId]);

  const seoRunning = activeSeoJobId !== null;
  const contentRunning = activeContentJobId !== null;
  const citationRunning = activeCitationJobId !== null;

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

  const handleRunCitation = async () => {
    setCitationError(null);
    try {
      const { jobId } = await apiClient.post<{ jobId: string }>(
        `/api/projects/${projectId}/run-citation-check`,
        {}
      );
      setCitationJob({
        id: jobId,
        type: "citation_check",
        status: "queued",
        progress: 0,
        progressSteps: [],
        outputData: null,
        errorMessage: null,
        startedAt: null,
        completedAt: null,
      });
      setCitationResults([]);
      setActiveCitationJobId(jobId);
      fetchedCitationRef.current = null;
    } catch (e) {
      setCitationError(e instanceof Error ? e.message : "Failed to start citation check");
    }
  };

  const fetchLlmsTxt = async () => {
    if (llmsTxt) { setLlmsTxtOpen(true); return; }
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/projects/${projectId}/llms.txt`);
      const text = await res.text();
      setLlmsTxt(text);
      setLlmsTxtOpen(true);
    } catch {}
  };

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
          <button
            onClick={fetchLlmsTxt}
            className="inline-flex items-center gap-2 h-8 px-3 border border-border rounded-md text-[12.5px] text-muted-foreground hover:text-foreground hover:bg-muted transition-colors text-left"
          >
            <span className="text-[10px] font-mono bg-muted px-1 rounded">llms.txt</span>
            Generate llms.txt
          </button>
        </div>

        {/* llms.txt panel */}
        {llmsTxtOpen && llmsTxt && (
          <div className="bg-card border border-border rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                llms.txt
              </p>
              <div className="flex items-center gap-2">
                <CopyButton text={llmsTxt} />
                <button
                  onClick={() => setLlmsTxtOpen(false)}
                  className="text-muted-foreground/50 hover:text-foreground"
                >
                  <X size={12} />
                </button>
              </div>
            </div>
            <pre className="text-[10px] text-muted-foreground bg-muted/50 rounded-md p-3 overflow-auto max-h-48 whitespace-pre-wrap font-mono leading-relaxed">
              {llmsTxt}
            </pre>
            <p className="text-[10px] text-muted-foreground mt-2">
              Place this file at <span className="font-mono">{project.websiteUrl.replace(/\/$/, "")}/llms.txt</span>
            </p>
          </div>
        )}
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
                    {article.aeoScore !== undefined && (
                      <AeoScoreBadge score={article.aeoScore} />
                    )}
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

        {/* ── AI Citation Check ────────────────────────── */}
        <CitationCard
          citationJob={citationJob}
          citationRunning={citationRunning}
          citationSteps={citationSteps}
          citationResults={citationResults}
          citationError={citationError}
          onRun={handleRunCitation}
        />
      </div>
    </div>
  );
}

interface CitationCardProps {
  citationJob: JobSummary | null;
  citationRunning: boolean;
  citationSteps: import("@findme/types").ProgressStep[];
  citationResults: CitationResult[];
  citationError: string | null;
  onRun: () => void;
}

const MODEL_LABELS: Record<string, string> = {
  claude: "Claude",
  "gpt-4o-mini": "GPT-4o",
  perplexity: "Perplexity",
};

function MentionRateBadge({ rate, model }: { rate: number; model: string }) {
  const color =
    rate >= 50 ? "text-chart-2" :
    rate >= 20 ? "text-chart-5" :
    "text-destructive";
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span className={`text-base font-bold font-mono ${color}`}>{rate}%</span>
      <span className="text-[10px] text-muted-foreground">{MODEL_LABELS[model] ?? model}</span>
    </div>
  );
}

function CitationCard({
  citationJob,
  citationRunning,
  citationSteps,
  citationResults,
  citationError,
  onRun,
}: CitationCardProps) {
  const summary = citationJob?.outputData?.summary as CitationSummary | undefined;
  const modelsChecked = (citationJob?.outputData?.models_checked as string[] | undefined) ?? [];

  const queriesByModel: Record<string, CitationResult[]> = {};
  for (const r of citationResults) {
    if (!queriesByModel[r.model]) queriesByModel[r.model] = [];
    queriesByModel[r.model].push(r);
  }

  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <Zap size={14} className="text-muted-foreground" />
          <h2 className="text-sm font-semibold text-foreground">AI Citation Check</h2>
        </div>
        <div className="flex items-center gap-2.5">
          {citationJob && !citationRunning && (
            <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
              citationJob.status === "completed" ? "bg-chart-2/15 text-chart-2" :
              citationJob.status === "failed" ? "bg-destructive/10 text-destructive" :
              "bg-muted text-muted-foreground"
            }`}>
              {citationJob.status}
            </span>
          )}
          <button
            onClick={onRun}
            disabled={citationRunning}
            className="inline-flex items-center gap-1.5 h-7 px-3 rounded-md text-[12px] font-medium bg-primary/10 text-primary hover:bg-primary/15 transition-colors disabled:opacity-50 disabled:pointer-events-none"
          >
            {citationRunning ? (
              <Loader2 size={12} className="animate-spin" />
            ) : citationJob ? (
              <RefreshCw size={12} />
            ) : (
              <Play size={12} />
            )}
            {citationRunning ? "Checking…" : citationJob ? "Re-check" : "Run Check"}
          </button>
        </div>
      </div>

      <p className="text-[11px] text-muted-foreground mb-4">
        Ask Claude, GPT-4o, and Perplexity your category queries — see if they mention your brand.
      </p>

      {/* Live progress */}
      {citationRunning && citationSteps.length > 0 && (
        <div className="divide-y divide-border mb-4 border border-border rounded-lg px-3">
          {citationSteps.map((step) => (
            <StepRow key={step.name} step={step} />
          ))}
        </div>
      )}
      {citationRunning && citationSteps.length === 0 && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground py-2 mb-3">
          <Loader2 size={12} className="animate-spin" />
          Queued…
        </div>
      )}

      {/* Error */}
      {(citationError ?? (citationJob?.status === "failed" ? citationJob.errorMessage : null)) && (
        <p className="text-xs text-destructive bg-destructive/5 rounded-md px-3 py-2 mb-3">
          {citationError ?? citationJob?.errorMessage}
        </p>
      )}

      {/* Results */}
      {citationJob?.status === "completed" && summary && (
        <div className="space-y-5">
          {/* Per-model mention rates */}
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-3">
              Mention Rates
            </p>
            <div className="flex gap-6">
              {modelsChecked.map((model) => {
                const m = summary[model];
                return m ? (
                  <MentionRateBadge key={model} model={model} rate={m.mention_rate} />
                ) : null;
              })}
            </div>
            <p className="text-[11px] text-muted-foreground mt-3">
              {(citationJob.outputData?.queries_run as number | undefined) ?? 0} queries across {modelsChecked.length} models
            </p>
          </div>

          {/* Query results grouped by model */}
          {citationResults.length > 0 && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                Query Details
              </p>
              <div className="space-y-3">
                {modelsChecked.map((model) => {
                  const rows = queriesByModel[model] ?? [];
                  if (rows.length === 0) return null;
                  return (
                    <div key={model} className="border border-border rounded-lg overflow-hidden">
                      <div className="px-3 py-2 bg-muted/30 border-b border-border">
                        <span className="text-[11px] font-semibold text-foreground">
                          {MODEL_LABELS[model] ?? model}
                        </span>
                      </div>
                      <div className="divide-y divide-border">
                        {rows.map((r) => (
                          <div key={r.id} className="px-3 py-2.5 flex items-start gap-3">
                            <div className="mt-0.5 shrink-0">
                              {r.mentioned ? (
                                <CheckCircle2 size={13} className="text-chart-2" />
                              ) : (
                                <Circle size={13} className="text-muted-foreground/30" />
                              )}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-[12px] text-foreground leading-snug">{r.query}</p>
                              {r.excerpt && (
                                <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-2">
                                  "{r.excerpt}"
                                </p>
                              )}
                            </div>
                            {r.mentioned && r.sentiment !== "none" && (
                              <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded font-medium ${
                                r.sentiment === "positive" ? "bg-chart-2/15 text-chart-2" :
                                r.sentiment === "negative" ? "bg-destructive/10 text-destructive" :
                                "bg-muted text-muted-foreground"
                              }`}>
                                {r.sentiment}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!citationJob && !citationRunning && (
        <div className="py-4 text-center border border-dashed border-border rounded-lg">
          <p className="text-xs text-muted-foreground">
            Check how often Claude, GPT-4o, and Perplexity mention your brand in category queries.
          </p>
        </div>
      )}
    </div>
  );
}
