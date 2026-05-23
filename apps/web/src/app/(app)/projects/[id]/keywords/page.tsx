"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import type { Keyword } from "@findme/types";
import { Trash2, Plus, TrendingUp } from "lucide-react";

function DifficultyBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-muted-foreground/50 text-xs">—</span>;
  const color =
    score < 30
      ? "text-chart-2 bg-chart-2/10"
      : score < 60
      ? "text-chart-5 bg-chart-5/10"
      : "text-destructive bg-destructive/10";
  return (
    <span className={`text-[11px] font-medium px-1.5 py-0.5 rounded ${color}`}>{score}</span>
  );
}

export default function KeywordsPage() {
  const { id: projectId } = useParams<{ id: string }>();
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    setLoading(true);
    apiClient
      .get<Keyword[]>(`/api/projects/${projectId}/keywords`)
      .then(setKeywords)
      .finally(() => setLoading(false));
  }, [projectId]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const raw = input
      .split("\n")
      .map((k) => k.trim())
      .filter(Boolean);
    if (!raw.length) return;
    setAdding(true);
    try {
      const created = await apiClient.post<Keyword[]>(
        `/api/projects/${projectId}/keywords`,
        { keywords: raw }
      );
      setKeywords((prev) => [...created, ...prev]);
      setInput("");
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id: string) {
    await apiClient.delete(`/api/projects/${projectId}/keywords/${id}`);
    setKeywords((prev) => prev.filter((k) => k.id !== id));
  }

  return (
    <div className="p-8 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold font-display tracking-tight">Keywords</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Add keywords to track. Run the pipeline to fetch SERP data and volume.
        </p>
      </div>

      {/* Add keywords */}
      <form onSubmit={handleAdd} className="mb-6 bg-card border border-border rounded-xl p-5">
        <label className="text-[13px] font-medium text-foreground block mb-1.5">
          Add keywords
        </label>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={"keyword one\nkeyword two\nkeyword three"}
          rows={4}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none"
        />
        <p className="text-[11px] text-muted-foreground mt-1 mb-3">One keyword per line</p>
        <button
          type="submit"
          disabled={adding || !input.trim()}
          className="inline-flex items-center gap-1.5 h-8 px-3 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          <Plus size={13} />
          {adding ? "Adding..." : "Add keywords"}
        </button>
      </form>

      {/* Keyword table */}
      {loading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : keywords.length === 0 ? (
        <div className="border border-dashed border-border rounded-xl p-10 text-center">
          <TrendingUp size={24} className="text-muted-foreground/40 mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">No keywords yet. Add some above.</p>
        </div>
      ) : (
        <div className="border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/40 border-b border-border">
                <th className="text-left px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Keyword
                </th>
                <th className="text-right px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Volume
                </th>
                <th className="text-right px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  Difficulty
                </th>
                <th className="text-right px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  CPC
                </th>
                <th className="w-8" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {keywords.map((kw) => (
                <tr key={kw.id} className="bg-card hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3 font-medium text-foreground">{kw.keyword}</td>
                  <td className="px-4 py-3 text-right font-mono text-[12px] text-muted-foreground">
                    {kw.searchVolume?.toLocaleString() ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <DifficultyBadge score={kw.keywordDifficulty ?? null} />
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-[12px] text-muted-foreground">
                    {kw.cpc ? `$${kw.cpc.toFixed(2)}` : "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDelete(kw.id)}
                      className="text-muted-foreground/40 hover:text-destructive transition-colors"
                    >
                      <Trash2 size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
