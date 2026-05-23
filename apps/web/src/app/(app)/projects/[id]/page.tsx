import { apiClient } from "@/lib/api-client";
import type { Project, AgentJob } from "@findme/types";
import { notFound } from "next/navigation";
import { VisibilityScore } from "@/components/VisibilityScore";
import { PipelineButton } from "@/components/PipelineButton";
import Link from "next/link";
import { FileText, Tag } from "lucide-react";

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let project: Project;
  try {
    project = await apiClient.get<Project>(`/api/projects/${id}`);
  } catch {
    notFound();
  }

  let jobs: AgentJob[] = [];
  try {
    jobs = await apiClient.get<AgentJob[]>(`/api/projects/${id}/jobs`);
  } catch {}

  const latestJob = jobs[0] ?? null;

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold font-display tracking-tight">{project.name}</h1>
            <a
              href={project.websiteUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-muted-foreground hover:text-primary transition-colors"
            >
              {project.websiteUrl}
            </a>
          </div>
        </div>

        {/* Quick nav */}
        <div className="flex gap-2 mt-4">
          <Link
            href={`/projects/${id}/keywords`}
            className="inline-flex items-center gap-1.5 h-8 px-3 border border-border rounded-md text-[12.5px] text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <Tag size={12} />
            Keywords
          </Link>
          <Link
            href={`/content?project_id=${id}`}
            className="inline-flex items-center gap-1.5 h-8 px-3 border border-border rounded-md text-[12.5px] text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            <FileText size={12} />
            Content
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <VisibilityScore score={project.visibilityScore} />
          {project.businessDescription ? (
            <div className="bg-card border border-border rounded-xl p-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">
                About
              </p>
              <p className="text-xs text-foreground/80 leading-relaxed">
                {project.businessDescription}
              </p>
            </div>
          ) : null}
        </div>

        <div className="lg:col-span-2">
          <div className="bg-card border border-border rounded-xl p-5">
            <h2 className="text-sm font-semibold text-foreground mb-4">Pipeline</h2>
            <PipelineButton projectId={id} existingJob={latestJob} />
          </div>
        </div>
      </div>
    </div>
  );
}
