"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type DimensionKey =
  | "seoQuality"
  | "aiReadability"
  | "semanticClarity"
  | "socialAmplification"
  | "authoritySignals"
  | "distributionCoverage";

const DIMENSIONS: { key: DimensionKey; label: string; weight: number; color: string }[] = [
  { key: "seoQuality", label: "SEO Quality", weight: 30, color: "bg-indigo-500" },
  { key: "aiReadability", label: "AI Readability", weight: 20, color: "bg-violet-500" },
  { key: "semanticClarity", label: "Semantic Clarity", weight: 15, color: "bg-blue-500" },
  { key: "socialAmplification", label: "Social Amplification", weight: 15, color: "bg-cyan-500" },
  { key: "authoritySignals", label: "Authority Signals", weight: 15, color: "bg-emerald-500" },
  { key: "distributionCoverage", label: "Distribution Coverage", weight: 5, color: "bg-amber-500" },
];

type HistoryRow = {
  date: string;
  total: number;
  seoQuality: number;
  aiReadability: number;
  semanticClarity: number;
  socialAmplification: number;
  authoritySignals: number;
  distributionCoverage: number;
};

export default function VisibilityPage() {
  const params = useSearchParams();
  const projectId = params.get("projectId") ?? "";

  const [history, setHistory] = useState<HistoryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) {
      setLoading(false);
      return;
    }
    fetch(`${API}/api/analytics/visibility?project_id=${projectId}&days=30`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setHistory)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [projectId]);

  const latest = history[history.length - 1] ?? null;

  if (!projectId) {
    return (
      <div className="p-8">
        <p className="text-sm text-muted-foreground">
          Select a project to view its visibility score.
        </p>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-5xl space-y-10">
      <div>
        <h1 className="text-2xl font-semibold font-display">Visibility Score</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Composite score across six dimensions — updated daily.
        </p>
      </div>

      {loading && (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-12 rounded-lg bg-muted animate-pulse" />
          ))}
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}

      {!loading && !error && (
        <>
          {/* Score Hero */}
          <div className="flex items-center gap-8">
            <div className="relative flex items-center justify-center w-32 h-32">
              <svg className="w-32 h-32 -rotate-90" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="52" fill="none" stroke="currentColor" strokeWidth="10" className="text-muted/30" />
                <circle
                  cx="60"
                  cy="60"
                  r="52"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="10"
                  strokeDasharray={`${((latest?.total ?? 0) / 100) * 327} 327`}
                  strokeLinecap="round"
                  className="text-primary transition-all duration-700"
                />
              </svg>
              <div className="absolute text-center">
                <span className="text-3xl font-bold font-display">
                  {latest ? Math.round(latest.total) : "—"}
                </span>
                <span className="block text-xs text-muted-foreground">/100</span>
              </div>
            </div>

            <div className="flex-1 grid grid-cols-2 gap-3">
              {DIMENSIONS.map((d) => {
                const val = latest ? latest[d.key] : 0;
                return (
                  <div key={d.key}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-muted-foreground">{d.label}</span>
                      <span className="font-medium">{Math.round(val)}</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${d.color}`}
                        style={{ width: `${val}%` }}
                      />
                    </div>
                    <p className="text-[10px] text-muted-foreground mt-0.5">{d.weight}% weight</p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* History Chart */}
          {history.length > 1 && (
            <section>
              <h2 className="text-base font-medium mb-4">Score History (30 days)</h2>
              <div className="border border-border rounded-lg p-4">
                <SimpleLineChart data={history} />
              </div>
            </section>
          )}

          {/* History Table */}
          {history.length > 0 && (
            <section>
              <h2 className="text-base font-medium mb-4">Daily Breakdown</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th className="pb-2 font-medium text-muted-foreground">Date</th>
                      <th className="pb-2 font-medium text-muted-foreground">Total</th>
                      {DIMENSIONS.map((d) => (
                        <th key={d.key} className="pb-2 font-medium text-muted-foreground">
                          {d.label.split(" ")[0]}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[...history].reverse().map((row) => (
                      <tr key={row.date} className="border-b border-border/50 hover:bg-muted/30">
                        <td className="py-2 font-mono text-xs">{row.date}</td>
                        <td className="py-2 font-bold">{Math.round(row.total)}</td>
                        {DIMENSIONS.map((d) => (
                          <td key={d.key} className="py-2 text-muted-foreground">
                            {Math.round(row[d.key])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {history.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No visibility score history yet. Run the pipeline to generate your first score.
            </p>
          )}
        </>
      )}
    </div>
  );
}

function SimpleLineChart({ data }: { data: HistoryRow[] }) {
  if (data.length < 2) return null;

  const width = 800;
  const height = 160;
  const pad = { top: 16, right: 16, bottom: 32, left: 40 };

  const scores = data.map((d) => d.total);
  const minScore = Math.max(Math.min(...scores) - 5, 0);
  const maxScore = Math.min(Math.max(...scores) + 5, 100);

  const xStep = (width - pad.left - pad.right) / (data.length - 1);
  const yScale = (v: number) =>
    pad.top + (height - pad.top - pad.bottom) * (1 - (v - minScore) / (maxScore - minScore));

  const points = data.map((d, i) => ({
    x: pad.left + i * xStep,
    y: yScale(d.total),
  }));

  const pathD = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`)
    .join(" ");

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-40">
      {/* Y-axis labels */}
      {[0, 25, 50, 75, 100].map((v) => {
        if (v < minScore - 5 || v > maxScore + 5) return null;
        return (
          <text key={v} x={pad.left - 8} y={yScale(v) + 4} textAnchor="end" fontSize={10} fill="currentColor" className="text-muted-foreground">
            {v}
          </text>
        );
      })}

      {/* Grid lines */}
      {[25, 50, 75].map((v) => (
        <line
          key={v}
          x1={pad.left}
          x2={width - pad.right}
          y1={yScale(v)}
          y2={yScale(v)}
          stroke="currentColor"
          strokeWidth={0.5}
          className="text-border"
        />
      ))}

      {/* Line */}
      <path d={pathD} fill="none" stroke="currentColor" strokeWidth={2} className="text-primary" />

      {/* Dots */}
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3} fill="currentColor" className="text-primary" />
      ))}

      {/* X-axis labels (every 7th) */}
      {data.map((d, i) => {
        if (i % 7 !== 0 && i !== data.length - 1) return null;
        return (
          <text key={i} x={points[i].x} y={height - 4} textAnchor="middle" fontSize={9} fill="currentColor" className="text-muted-foreground">
            {d.date.slice(5)}
          </text>
        );
      })}
    </svg>
  );
}
