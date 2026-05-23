interface VisibilityScoreProps {
  score: number | null;
}

const DIMENSIONS = [
  { key: "seoQuality", label: "SEO Quality", weight: 30 },
  { key: "aiReadability", label: "AI Readability", weight: 20 },
  { key: "semanticClarity", label: "Semantic Clarity", weight: 15 },
  { key: "socialAmplification", label: "Social Amplification", weight: 15 },
  { key: "authoritySignals", label: "Authority Signals", weight: 15 },
  { key: "distributionCoverage", label: "Distribution Coverage", weight: 5 },
];

function scoreColor(score: number) {
  if (score >= 75) return "text-chart-2";
  if (score >= 50) return "text-chart-5";
  return "text-destructive";
}

export function VisibilityScore({ score }: VisibilityScoreProps) {
  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <h2 className="text-sm font-semibold text-foreground mb-4">Visibility Score</h2>

      {score !== null ? (
        <>
          <div className="flex items-end gap-2 mb-5">
            <span className={`text-5xl font-bold font-mono leading-none ${scoreColor(score)}`}>
              {Math.round(score)}
            </span>
            <span className="text-sm text-muted-foreground mb-1">/100</span>
          </div>

          <div className="space-y-2.5">
            {DIMENSIONS.map(({ key, label, weight }) => (
              <div key={key}>
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-[11px] text-muted-foreground">{label}</span>
                  <span className="text-[10px] text-muted-foreground/60">{weight}%</span>
                </div>
                <div className="h-1 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary/60 rounded-full"
                    style={{ width: `${score}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="py-6 text-center">
          <p className="text-4xl font-bold font-mono text-muted-foreground/30">—</p>
          <p className="mt-2 text-xs text-muted-foreground">Run a pipeline to calculate your score</p>
        </div>
      )}
    </div>
  );
}
