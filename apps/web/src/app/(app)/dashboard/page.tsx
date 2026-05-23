import { apiClient } from "@/lib/api-client";
import type { Project } from "@findme/types";
import Link from "next/link";

export default async function DashboardPage() {
  let projects: Project[] = [];
  try {
    projects = await apiClient.get<Project[]>("/api/projects");
  } catch {}

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold font-display tracking-tight">Dashboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Your visibility across Google, AI search, and social platforms.
        </p>
      </div>

      {projects.length === 0 ? (
        <div className="border border-dashed border-border rounded-xl p-12 text-center">
          <p className="text-sm text-muted-foreground mb-4">No projects yet.</p>
          <Link
            href="/projects/new"
            className="inline-flex items-center h-9 px-4 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            Create your first project
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}`}
              className="block bg-card border border-border rounded-lg p-5 hover:border-primary/40 transition-colors group"
            >
              <div className="flex items-start justify-between mb-3">
                <h2 className="text-sm font-semibold text-foreground group-hover:text-primary transition-colors">
                  {project.name}
                </h2>
                {project.visibilityScore !== null ? (
                  <span className="text-[11px] font-mono font-bold text-primary bg-accent px-1.5 py-0.5 rounded">
                    {Math.round(project.visibilityScore)}
                  </span>
                ) : null}
              </div>
              <p className="text-xs text-muted-foreground truncate">{project.websiteUrl}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
