import { apiClient } from "@/lib/api-client";
import type { Project } from "@findme/types";
import Link from "next/link";

export default async function ProjectsPage() {
  let projects: Project[] = [];
  try {
    projects = await apiClient.get<Project[]>("/api/projects");
  } catch {}

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-display tracking-tight">Projects</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">{projects.length} project{projects.length !== 1 ? "s" : ""}</p>
        </div>
        <Link
          href="/projects/new"
          className="inline-flex items-center h-9 px-4 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          New project
        </Link>
      </div>

      {projects.length === 0 ? (
        <div className="border border-dashed border-border rounded-xl p-12 text-center">
          <p className="text-sm text-muted-foreground">No projects yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="divide-y divide-border border border-border rounded-lg overflow-hidden">
          {projects.map((project) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}`}
              className="flex items-center justify-between px-5 py-4 bg-card hover:bg-muted/50 transition-colors"
            >
              <div>
                <p className="text-sm font-medium text-foreground">{project.name}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{project.websiteUrl}</p>
              </div>
              <div className="flex items-center gap-4">
                {project.visibilityScore !== null ? (
                  <div className="text-right">
                    <p className="text-[11px] text-muted-foreground">Visibility</p>
                    <p className="text-sm font-bold font-mono text-primary">
                      {Math.round(project.visibilityScore)}
                    </p>
                  </div>
                ) : null}
                <span className="text-xs px-2 py-0.5 rounded-full border border-border text-muted-foreground capitalize">
                  {project.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
