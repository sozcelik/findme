import { apiClient } from "@/lib/api-client";
import type { ContentItem } from "@findme/types";
import Link from "next/link";
import { FileText } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-muted text-muted-foreground",
  review: "bg-chart-5/15 text-chart-5",
  approved: "bg-chart-2/15 text-chart-2",
  published: "bg-primary/10 text-primary",
  archived: "bg-muted text-muted-foreground/60",
};

export default async function ContentPage({
  searchParams,
}: {
  searchParams: Promise<{ project_id?: string }>;
}) {
  const { project_id } = await searchParams;
  const qs = project_id ? `?project_id=${project_id}` : "";

  let items: ContentItem[] = [];
  try {
    items = await apiClient.get<ContentItem[]>(`/api/content${qs}`);
  } catch {}

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold font-display tracking-tight">Content</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          {items.length} item{items.length !== 1 ? "s" : ""}
          {project_id ? " for this project" : " across all projects"}
        </p>
      </div>

      {items.length === 0 ? (
        <div className="border border-dashed border-border rounded-xl p-12 text-center">
          <FileText size={24} className="text-muted-foreground/30 mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">
            No content yet. Run the pipeline on a project to generate articles.
          </p>
        </div>
      ) : (
        <div className="divide-y divide-border border border-border rounded-lg overflow-hidden">
          {items.map((item) => (
            <Link
              key={item.id}
              href={`/content/${item.id}`}
              className="flex items-center justify-between px-5 py-4 bg-card hover:bg-muted/40 transition-colors"
            >
              <div className="min-w-0 flex-1 mr-4">
                <p className="text-sm font-medium text-foreground truncate">{item.title}</p>
                <div className="flex items-center gap-3 mt-0.5">
                  {item.focusKeyword ? (
                    <span className="text-xs text-muted-foreground">{item.focusKeyword}</span>
                  ) : null}
                  {item.wordCount ? (
                    <span className="text-xs text-muted-foreground font-mono">
                      {item.wordCount.toLocaleString()} words
                    </span>
                  ) : null}
                </div>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                {item.aiModelUsed ? (
                  <span className="text-[10px] font-mono text-muted-foreground/60">
                    {item.aiModelUsed}
                  </span>
                ) : null}
                <span
                  className={`text-[11px] px-2 py-0.5 rounded-full font-medium capitalize ${
                    STATUS_COLORS[item.status] ?? "bg-muted text-muted-foreground"
                  }`}
                >
                  {item.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
