import { apiClient } from "@/lib/api-client";
import type { Project } from "@findme/types";
import { notFound } from "next/navigation";
import { ProjectDashboard } from "@/components/ProjectDashboard";

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

  let jobs: Parameters<typeof ProjectDashboard>[0]["initialJobs"] = [];
  try {
    jobs = await apiClient.get(`/api/projects/${id}/jobs`);
  } catch {}

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6">
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

      <ProjectDashboard projectId={id} project={project} initialJobs={jobs} />
    </div>
  );
}
