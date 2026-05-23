"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import type { Keyword } from "@findme/types";
import { Trash2, Plus, TrendingUp, Sparkles, ChevronDown, ChevronUp } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type SuggestedKeyword = {
  keyword: string;
  search_volume: number | null;
  cpc: number | null;
  keyword_difficulty: number | null;
  position: number | null;
  selected: boolean;
};

type Competitor = {
  domain: string;
  avg_position: number | null;
  intersections: number | null;
};

function DifficultyBadge({ score }: { score: number | null }) {
  if (score === null) return <span className="text-muted-foreground/50 text-xs">—</span>;
  const color =
    score < 30
      ? "text-emerald-600 bg-emerald-500/10"
      : score < 60
      ? "text-amber-600 bg-amber-500/10"
      : "text-destructive bg-destructive/10";
  return (
    <span className={`text-[11px] font-medium px-1.5 py-0.5 rounded ${color}`}>{score}</span>
  );
}

export default function KeywordsPage() {
  const { id: projectId } = useParams<{ id: string }>();

  // Saved keywords
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [loadingKeywords, setLoadingKeywords] = useState(true);

  // Audit / discovery
  const [discovering, setDiscovering] = useState(false);
  const [suggestions, setSuggestions] = useState<SuggestedKeyword[]>([]);
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [auditSource, setAuditSource] = useState<"dataforseo" | "mock" | null>(null);
  const [showCompetitors, setShowCompetitors] = useState(false);
  const [auditRan, setAuditRan] = useState(false);

  // Manual add
  const [input, setInput] = useState("");
  const [adding, setAdding] = useState(false);

  // Project URL (needed to trigger audit)
  const [projectUrl, setProjectUrl] = useState<string | null>(null);

  useEffect(() => {
    // Load project to get URL, and load existing keywords in parallel
    Promise.all([
      apiClient.get<{ websiteUrl: string }>(`/api/projects/${projectId}`),
      apiClient.get<Keyword[]>(`/api/projects/${projectId}/keywords`),
    ]).then(([project, kws]) => {
      setProjectUrl(project.websiteUrl ?? null);
      setKeywords(kws);
      setLoadingKeywords(false);

      // Auto-trigger discovery only if no keywords saved yet
      if (kws.length === 0 && project.websiteUrl) {
        runAudit(project.websiteUrl);
      }
    }).catch(() => setLoadingKeywords(false));
  }, [projectId]);

  async function runAudit(url: string) {
    setDiscovering(true);
    setAuditRan(false);
    try {
      const res = await fetch(`${API}/api/audit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setSuggestions(
        (data.keywords ?? []).map((k: Omit<SuggestedKeyword, "selected">) => ({
          ...k,
          selected: true,
        }))
      );
      setCompetitors(data.competitors ?? []);
      setAuditSource(data.source);
      setAuditRan(true);
    } catch {
      setAuditRan(true); // show manual form even on failure
    } finally {
      setDiscovering(false);
    }
  }

  function toggleSuggestion(keyword: string) {
    setSuggestions((prev) =>
      prev.map((s) => (s.keyword === keyword ? { ...s, selected: !s.selected } : s))
    );
  }

  function toggleAll(value: boolean) {
    setSuggestions((prev) => prev.map((s) => ({ ...s, selected: value })));
  }

  async function saveSuggestions() {
    const selected = suggestions.filter((s) => s.selected).map((s) => s.keyword);
    const manual = input
      .split("\n")
      .map((k) => k.trim())
      .filter(Boolean);
    const all = [...new Set([...selected, ...manual])];
    if (!all.length) return;

    setAdding(true);
    try {
      const created = await apiClient.post<Keyword[]>(
        `/api/projects/${projectId}/keywords`,
        { keywords: all }
      );
      setKeywords((prev) => [...created, ...prev]);
      setSuggestions([]);
      setInput("");
      setAuditRan(false);
    } finally {
      setAdding(false);
    }
  }

  async function handleAddManual(e: React.FormEvent) {
    e.preventDefault();
    const raw = input.split("\n").map((k) => k.trim()).filter(Boolean);
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

  const selectedCount = suggestions.filter((s) => s.selected).length;

  return (
    <div className="p-8 max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold font-display tracking-tight">Keywords</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Add keywords to track. Run the pipeline to fetch SERP data and generate content.
        </p>
      </div>

      {/* ── Discovery panel ── */}
      {discovering && (
        <div className="border border-border rounded-xl p-6 flex items-center gap-3 text-sm text-muted-foreground">
          <Sparkles size={15} className="animate-pulse text-primary shrink-0" />
          Analysing your domain to discover keywords and competitors…
        </div>
      )}

      {!discovering && auditRan && suggestions.length > 0 && (
        <div className="border border-primary/20 bg-primary/[0.03] rounded-xl overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <div className="flex items-center gap-2">
              <Sparkles size={14} className="text-primary" />
              <span className="text-sm font-medium">
                {suggestions.length} keywords found
                {auditSource === "mock" && (
                  <span className="ml-2 text-[10px] text-muted-foreground font-normal">(demo data — add DataForSEO credentials for real results)</span>
                )}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => toggleAll(true)}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                Select all
              </button>
              <span className="text-border">|</span>
              <button
                onClick={() => toggleAll(false)}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                Deselect all
              </button>
            </div>
          </div>

          {/* Keyword suggestion table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/30 border-b border-border">
                  <th className="w-8 px-4 py-2.5" />
                  <th className="text-left px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Keyword</th>
                  <th className="text-right px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Volume</th>
                  <th className="text-right px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Difficulty</th>
                  <th className="text-right px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">CPC</th>
                  <th className="text-right px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Pos.</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {suggestions.map((s) => (
                  <tr
                    key={s.keyword}
                    onClick={() => toggleSuggestion(s.keyword)}
                    className={`cursor-pointer transition-colors ${
                      s.selected ? "bg-card hover:bg-muted/30" : "bg-muted/10 opacity-50 hover:opacity-70"
                    }`}
                  >
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={s.selected}
                        onChange={() => toggleSuggestion(s.keyword)}
                        onClick={(e) => e.stopPropagation()}
                        className="rounded accent-primary"
                      />
                    </td>
                    <td className="px-4 py-3 font-medium">{s.keyword}</td>
                    <td className="px-4 py-3 text-right font-mono text-[12px] text-muted-foreground">
                      {s.search_volume?.toLocaleString() ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <DifficultyBadge score={s.keyword_difficulty} />
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-[12px] text-muted-foreground">
                      {s.cpc ? `$${s.cpc.toFixed(2)}` : "—"}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-[12px] text-muted-foreground">
                      {s.position ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Competitors section */}
          {competitors.length > 0 && (
            <div className="border-t border-border">
              <button
                onClick={() => setShowCompetitors(!showCompetitors)}
                className="w-full flex items-center justify-between px-5 py-3 text-sm text-muted-foreground hover:text-foreground hover:bg-muted/20 transition-colors"
              >
                <span className="font-medium">
                  {competitors.length} competitors detected
                </span>
                {showCompetitors ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
              {showCompetitors && (
                <div className="px-5 pb-4 grid grid-cols-3 gap-2">
                  {competitors.map((c) => (
                    <div key={c.domain} className="border border-border rounded-md px-3 py-2 text-xs">
                      <p className="font-medium truncate">{c.domain}</p>
                      <p className="text-muted-foreground mt-0.5">
                        {c.intersections} overlapping keywords
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Add own + Save */}
          <div className="border-t border-border px-5 py-4 space-y-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground block mb-1.5">
                Add your own keywords (optional)
              </label>
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={"keyword one\nkeyword two"}
                rows={3}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-none"
              />
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={saveSuggestions}
                disabled={adding || (selectedCount === 0 && !input.trim())}
                className="h-9 px-5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
              >
                {adding
                  ? "Saving…"
                  : `Save ${selectedCount + input.split("\n").filter((l) => l.trim()).length} keyword${selectedCount + input.split("\n").filter((l) => l.trim()).length !== 1 ? "s" : ""}`}
              </button>
              <button
                onClick={() => { setSuggestions([]); setAuditRan(false); }}
                className="text-sm text-muted-foreground hover:text-foreground"
              >
                Skip discovery
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Re-run discovery button (after first run or if keywords exist) ── */}
      {!discovering && !auditRan && projectUrl && keywords.length > 0 && (
        <button
          onClick={() => runAudit(projectUrl)}
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground border border-border rounded-md px-3 py-1.5 hover:bg-muted transition-colors"
        >
          <Sparkles size={12} />
          Re-run keyword discovery
        </button>
      )}

      {/* ── Manual add (shown when no suggestions panel is open) ── */}
      {!auditRan && (
        <form onSubmit={handleAddManual} className="bg-card border border-border rounded-xl p-5">
          <label className="text-[13px] font-medium text-foreground block mb-1.5">
            Add keywords manually
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
            {adding ? "Adding…" : "Add keywords"}
          </button>
        </form>
      )}

      {/* ── Saved keyword table ── */}
      {loadingKeywords ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : keywords.length === 0 && !discovering && !auditRan ? (
        <div className="border border-dashed border-border rounded-xl p-10 text-center">
          <TrendingUp size={24} className="text-muted-foreground/40 mx-auto mb-2" />
          <p className="text-sm text-muted-foreground">No keywords saved yet.</p>
        </div>
      ) : keywords.length > 0 ? (
        <div className="border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-muted/40 border-b border-border">
                <th className="text-left px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Keyword</th>
                <th className="text-right px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Volume</th>
                <th className="text-right px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Difficulty</th>
                <th className="text-right px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">CPC</th>
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
      ) : null}
    </div>
  );
}
