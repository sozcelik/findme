"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type CmsConnection = {
  id: string;
  type: string;
  name: string;
  status: string;
  lastTestedAt: string | null;
  lastError: string | null;
};

type SocialConnection = {
  id: string;
  platform: string;
  accountName: string | null;
  status: string;
};

const CMS_TYPES = ["wordpress", "webflow", "shopify"] as const;
type CmsType = (typeof CMS_TYPES)[number];

const CMS_FIELDS: Record<CmsType, { key: string; label: string; type?: string }[]> = {
  wordpress: [
    { key: "site_url", label: "Site URL" },
    { key: "username", label: "Username" },
    { key: "app_password", label: "Application Password", type: "password" },
  ],
  webflow: [
    { key: "api_token", label: "API Token", type: "password" },
    { key: "collection_id", label: "Collection ID" },
  ],
  shopify: [
    { key: "shop_domain", label: "Shop Domain (myshop.myshopify.com)" },
    { key: "access_token", label: "Access Token", type: "password" },
    { key: "blog_id", label: "Blog ID" },
  ],
};

export default function IntegrationsPage() {
  const [cmsConnections, setCmsConnections] = useState<CmsConnection[]>([]);
  const [socialConnections, setSocialConnections] = useState<SocialConnection[]>([]);
  const [showCmsForm, setShowCmsForm] = useState(false);
  const [cmsType, setCmsType] = useState<CmsType>("wordpress");
  const [cmsName, setCmsName] = useState("");
  const [cmsConfig, setCmsConfig] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAll();
  }, []);

  async function fetchAll() {
    const [cmsRes, socialRes] = await Promise.all([
      fetch(`${API}/api/integrations/cms`),
      fetch(`${API}/api/integrations/social`),
    ]);
    if (cmsRes.ok) setCmsConnections(await cmsRes.json());
    if (socialRes.ok) setSocialConnections(await socialRes.json());
  }

  async function saveCms() {
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/integrations/cms`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: cmsType, name: cmsName, config: cmsConfig }),
      });
      if (!res.ok) throw new Error(await res.text());
      setShowCmsForm(false);
      setCmsName("");
      setCmsConfig({});
      await fetchAll();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function testCms(id: string) {
    setTesting(id);
    try {
      const res = await fetch(`${API}/api/integrations/cms/${id}/test`);
      const data = await res.json();
      alert(data.ok ? "Connection successful!" : `Failed: ${data.error ?? "Unknown error"}`);
      await fetchAll();
    } finally {
      setTesting(null);
    }
  }

  async function deleteCms(id: string) {
    if (!confirm("Delete this connection?")) return;
    await fetch(`${API}/api/integrations/cms/${id}`, { method: "DELETE" });
    await fetchAll();
  }

  async function connectSocial(platform: string) {
    const res = await fetch(`${API}/api/integrations/social/${platform}/oauth-url`);
    if (!res.ok) {
      alert("OAuth not configured for this platform");
      return;
    }
    const { url } = await res.json();
    window.location.href = url;
  }

  async function disconnectSocial(id: string) {
    if (!confirm("Disconnect this account?")) return;
    await fetch(`${API}/api/integrations/social/${id}`, { method: "DELETE" });
    await fetchAll();
  }

  const connectedPlatforms = new Set(socialConnections.map((c) => c.platform));

  return (
    <div className="space-y-10">
      {/* CMS Section */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium">CMS Connections</h2>
          <button
            onClick={() => setShowCmsForm(!showCmsForm)}
            className="text-sm px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
          >
            + Add CMS
          </button>
        </div>

        {showCmsForm && (
          <div className="border border-border rounded-lg p-6 mb-4 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium block mb-1">CMS Type</label>
                <select
                  value={cmsType}
                  onChange={(e) => {
                    setCmsType(e.target.value as CmsType);
                    setCmsConfig({});
                  }}
                  className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background"
                >
                  {CMS_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t.charAt(0).toUpperCase() + t.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium block mb-1">Connection Name</label>
                <input
                  value={cmsName}
                  onChange={(e) => setCmsName(e.target.value)}
                  placeholder="e.g. My Blog"
                  className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {CMS_FIELDS[cmsType].map((f) => (
                <div key={f.key}>
                  <label className="text-sm font-medium block mb-1">{f.label}</label>
                  <input
                    type={f.type ?? "text"}
                    value={cmsConfig[f.key] ?? ""}
                    onChange={(e) => setCmsConfig((prev) => ({ ...prev, [f.key]: e.target.value }))}
                    className="w-full border border-border rounded-md px-3 py-2 text-sm bg-background"
                  />
                </div>
              ))}
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <div className="flex gap-2">
              <button
                onClick={saveCms}
                disabled={saving || !cmsName}
                className="text-sm px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save Connection"}
              </button>
              <button
                onClick={() => setShowCmsForm(false)}
                className="text-sm px-4 py-2 rounded-md border border-border hover:bg-muted"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {cmsConnections.length === 0 && !showCmsForm ? (
          <p className="text-sm text-muted-foreground">No CMS connections yet.</p>
        ) : (
          <div className="space-y-2">
            {cmsConnections.map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between border border-border rounded-lg px-4 py-3"
              >
                <div>
                  <span className="font-medium text-sm">{c.name}</span>
                  <span className="ml-2 text-xs text-muted-foreground capitalize">{c.type}</span>
                  {c.status === "error" && c.lastError && (
                    <p className="text-xs text-destructive mt-0.5">{c.lastError}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      c.status === "active"
                        ? "bg-green-500/10 text-green-600"
                        : "bg-destructive/10 text-destructive"
                    }`}
                  >
                    {c.status}
                  </span>
                  <button
                    onClick={() => testCms(c.id)}
                    disabled={testing === c.id}
                    className="text-xs px-2 py-1 rounded border border-border hover:bg-muted disabled:opacity-50"
                  >
                    {testing === c.id ? "Testing..." : "Test"}
                  </button>
                  <button
                    onClick={() => deleteCms(c.id)}
                    className="text-xs px-2 py-1 rounded border border-destructive/30 text-destructive hover:bg-destructive/10"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Social Section */}
      <section>
        <h2 className="text-lg font-medium mb-4">Social Accounts</h2>
        <div className="space-y-3">
          {(["linkedin", "twitter"] as const).map((platform) => {
            const conn = socialConnections.find((c) => c.platform === platform);
            return (
              <div
                key={platform}
                className="flex items-center justify-between border border-border rounded-lg px-4 py-3"
              >
                <div>
                  <span className="font-medium text-sm capitalize">{platform}</span>
                  {conn && (
                    <span className="ml-2 text-xs text-muted-foreground">
                      @{conn.accountName}
                    </span>
                  )}
                </div>
                {conn ? (
                  <div className="flex items-center gap-2">
                    <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/10 text-green-600">
                      connected
                    </span>
                    <button
                      onClick={() => disconnectSocial(conn.id)}
                      className="text-xs px-2 py-1 rounded border border-destructive/30 text-destructive hover:bg-destructive/10"
                    >
                      Disconnect
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => connectSocial(platform)}
                    className="text-sm px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
                  >
                    Connect
                  </button>
                )}
              </div>
            );
          })}

          {/* Reddit — draft-only notice */}
          <div className="flex items-center justify-between border border-border rounded-lg px-4 py-3 opacity-60">
            <div>
              <span className="font-medium text-sm">Reddit</span>
              <span className="ml-2 text-xs text-muted-foreground">draft generation only</span>
            </div>
            <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
              manual post
            </span>
          </div>
        </div>
      </section>
    </div>
  );
}
