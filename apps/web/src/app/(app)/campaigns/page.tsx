"use client";

import { useEffect, useState } from "react";
import { Play, Pause, Trash2, Plus } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Campaign = {
  id: string;
  projectId: string;
  name: string;
  status: string;
  scheduleCron: string | null;
  targetKeywords: string[];
  publishToCms: boolean;
  distributeSocial: boolean;
  lastRunAt: string | null;
  nextRunAt: string | null;
  createdAt: string;
};

type Project = { id: string; name: string };

const CRON_PRESETS = [
  { label: "Daily at 03:00 UTC", value: "0 3 * * *" },
  { label: "Weekly (Mon 03:00 UTC)", value: "0 3 * * 1" },
  { label: "Bi-weekly (Mon/Thu)", value: "0 3 * * 1,4" },
  { label: "Monthly (1st)", value: "0 3 1 * *" },
];

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState<string | null>(null);

  // Form state
  const [form, setForm] = useState({
    projectId: "",
    name: "",
    scheduleCron: "0 3 * * 1",
    publishToCms: false,
    distributeSocial: false,
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/campaigns`).then((r) => r.ok ? r.json() : []),
      fetch(`${API}/api/projects`).then((r) => r.ok ? r.json() : []),
    ]).then(([c, p]) => {
      setCampaigns(c);
      setProjects(p);
      if (p.length > 0) setForm((f) => ({ ...f, projectId: p[0].id }));
    }).finally(() => setLoading(false));
  }, []);

  async function createCampaign() {
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/campaigns`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          projectId: form.projectId,
          name: form.name,
          scheduleCron: form.scheduleCron || null,
          publishToCms: form.publishToCms,
          distributeSocial: form.distributeSocial,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const created = await res.json();
      setCampaigns((prev) => [created, ...prev]);
      setShowForm(false);
      setForm((f) => ({ ...f, name: "" }));
    } finally {
      setSaving(false);
    }
  }

  async function runNow(campaignId: string) {
    setRunning(campaignId);
    try {
      await fetch(`${API}/api/campaigns/${campaignId}/run`, { method: "POST" });
      setCampaigns((prev) =>
        prev.map((c) => (c.id === campaignId ? { ...c, status: "running" } : c))
      );
    } finally {
      setRunning(null);
    }
  }

  async function togglePause(campaign: Campaign) {
    const newStatus = campaign.status === "paused" ? "running" : "paused";
    await fetch(`${API}/api/campaigns/${campaign.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    });
    setCampaigns((prev) =>
      prev.map((c) => (c.id === campaign.id ? { ...c, status: newStatus } : c))
    );
  }

  async function deleteCampaign(campaignId: string) {
    if (!confirm("Delete this campaign?")) return;
    await fetch(`${API}/api/campaigns/${campaignId}`, { method: "DELETE" });
    setCampaigns((prev) => prev.filter((c) => c.id !== campaignId));
  }

  const projectName = (id: string) => projects.find((p) => p.id === id)?.name ?? id;

  return (
    <div className="p-8 max-w-5xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-semibold font-display">Campaigns</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Schedule automated pipeline runs for your projects.
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90"
        >
          <Plus size={14} /> New Campaign
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="border border-border rounded-lg p-6 mb-6 space-y-4">
          <h2 className="text-sm font-medium">New Campaign</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-medium block mb-1 text-muted-foreground">Project</label>
              <select
                value={form.projectId}
                onChange={(e) => setForm((f) => ({ ...f, projectId: e.target.value }))}
                className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs font-medium block mb-1 text-muted-foreground">Campaign Name</label>
              <input
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Weekly SEO Pipeline"
                className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium block mb-1 text-muted-foreground">Schedule</label>
            <select
              value={form.scheduleCron}
              onChange={(e) => setForm((f) => ({ ...f, scheduleCron: e.target.value }))}
              className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background"
            >
              {CRON_PRESETS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
          </div>

          <div className="flex gap-6">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={form.publishToCms}
                onChange={(e) => setForm((f) => ({ ...f, publishToCms: e.target.checked }))}
                className="rounded"
              />
              Auto-publish to CMS
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={form.distributeSocial}
                onChange={(e) => setForm((f) => ({ ...f, distributeSocial: e.target.checked }))}
                className="rounded"
              />
              Auto-distribute to social
            </label>
          </div>

          <div className="flex gap-2">
            <button
              onClick={createCampaign}
              disabled={saving || !form.name || !form.projectId}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm hover:bg-primary/90 disabled:opacity-50"
            >
              {saving ? "Creating..." : "Create Campaign"}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="px-4 py-2 border border-border rounded-md text-sm hover:bg-muted"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Campaign List */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 rounded-lg bg-muted animate-pulse" />
          ))}
        </div>
      ) : campaigns.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <p className="text-sm">No campaigns yet. Create one to automate your pipeline runs.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {campaigns.map((campaign) => (
            <div
              key={campaign.id}
              className="border border-border rounded-lg px-5 py-4 flex items-center justify-between gap-4"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">{campaign.name}</span>
                  <StatusBadge status={campaign.status} />
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                  <span>{projectName(campaign.projectId)}</span>
                  {campaign.scheduleCron && (
                    <span className="font-mono">{campaign.scheduleCron}</span>
                  )}
                  {campaign.publishToCms && <span>→ CMS</span>}
                  {campaign.distributeSocial && <span>→ Social</span>}
                </div>
                {campaign.lastRunAt && (
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    Last run: {new Date(campaign.lastRunAt).toLocaleString()}
                    {campaign.nextRunAt && (
                      <> · Next: {new Date(campaign.nextRunAt).toLocaleString()}</>
                    )}
                  </p>
                )}
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => runNow(campaign.id)}
                  disabled={running === campaign.id || campaign.status === "running"}
                  className="text-xs px-3 py-1.5 rounded border border-border hover:bg-muted disabled:opacity-50 flex items-center gap-1.5"
                >
                  <Play size={11} />
                  {running === campaign.id ? "Starting..." : "Run Now"}
                </button>
                <button
                  onClick={() => togglePause(campaign)}
                  className="text-xs p-1.5 rounded border border-border hover:bg-muted"
                  title={campaign.status === "paused" ? "Resume" : "Pause"}
                >
                  <Pause size={12} />
                </button>
                <button
                  onClick={() => deleteCampaign(campaign.id)}
                  className="text-xs p-1.5 rounded border border-destructive/30 text-destructive hover:bg-destructive/10"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    running: "bg-green-500/10 text-green-600",
    completed: "bg-blue-500/10 text-blue-600",
    paused: "bg-amber-500/10 text-amber-600",
    draft: "bg-muted text-muted-foreground",
  };
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${styles[status] ?? styles.draft}`}>
      {status}
    </span>
  );
}
