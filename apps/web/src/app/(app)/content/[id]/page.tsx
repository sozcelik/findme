"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import type { ContentItem } from "@findme/types";
import Link from "next/link";
import { ArrowLeft, Save, CheckCircle2, Globe, Share2 } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const STATUS_OPTIONS = ["draft", "review", "approved", "published", "archived"] as const;

type CmsConnection = { id: string; name: string; type: string };
type SocialConnection = { id: string; platform: string; accountName: string | null };
type SocialPost = {
  id: string;
  platform: string;
  body: string;
  hashtags: string[];
  redditTitle: string | null;
  status: string;
  postedAt: string | null;
};

export default function ContentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [item, setItem] = useState<ContentItem | null>(null);
  const [body, setBody] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Publish / distribute
  const [cmsConnections, setCmsConnections] = useState<CmsConnection[]>([]);
  const [socialConnections, setSocialConnections] = useState<SocialConnection[]>([]);
  const [socialPosts, setSocialPosts] = useState<SocialPost[]>([]);
  const [selectedCms, setSelectedCms] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [distributing, setDistributing] = useState<string | null>(null);
  const [publishMessage, setPublishMessage] = useState<string | null>(null);

  useEffect(() => {
    apiClient.get<ContentItem & { bodyMarkdown: string }>(`/api/content/${id}`).then((data) => {
      setItem(data);
      setBody(data.bodyMarkdown ?? "");
    });

    Promise.all([
      fetch(`${API}/api/integrations/cms`).then((r) => r.ok ? r.json() : []),
      fetch(`${API}/api/integrations/social`).then((r) => r.ok ? r.json() : []),
      fetch(`${API}/api/content/${id}/social-posts`).then((r) => r.ok ? r.json() : []),
    ]).then(([cms, social, posts]) => {
      setCmsConnections(cms);
      setSocialConnections(social);
      setSocialPosts(posts);
      if (cms.length > 0) setSelectedCms(cms[0].id);
    });
  }, [id]);

  async function handleSave() {
    if (!item) return;
    setSaving(true);
    try {
      const updated = await apiClient.patch<ContentItem & { bodyMarkdown: string }>(
        `/api/content/${id}`,
        { bodyMarkdown: body }
      );
      setItem(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  async function handleStatusChange(status: string) {
    if (!item) return;
    const updated = await apiClient.patch<ContentItem>(`/api/content/${id}`, { status });
    setItem((prev) => (prev ? { ...prev, status: updated.status } : prev));
  }

  async function handlePublish() {
    if (!selectedCms) return;
    setPublishing(true);
    setPublishMessage(null);
    try {
      const res = await fetch(`${API}/api/content/${id}/publish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cmsConnectionId: selectedCms }),
      });
      if (!res.ok) throw new Error(await res.text());
      setPublishMessage("Publish queued. It will appear on your CMS shortly.");
    } catch (e: unknown) {
      setPublishMessage(`Error: ${e instanceof Error ? e.message : "Unknown error"}`);
    } finally {
      setPublishing(false);
    }
  }

  async function handleDistribute(post: SocialPost) {
    const conn = socialConnections.find((c) => c.platform === post.platform);
    if (!conn) {
      alert(`No connected ${post.platform} account. Go to Settings → Integrations.`);
      return;
    }
    setDistributing(post.id);
    try {
      const res = await fetch(`${API}/api/content/${id}/distribute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ socialConnectionId: conn.id, socialPostId: post.id }),
      });
      if (!res.ok) throw new Error(await res.text());
      setSocialPosts((prev) =>
        prev.map((p) => (p.id === post.id ? { ...p, status: "queued" } : p))
      );
    } catch (e: unknown) {
      alert(`Error: ${e instanceof Error ? e.message : "Unknown error"}`);
    } finally {
      setDistributing(null);
    }
  }

  if (!item) {
    return (
      <div className="p-8">
        <div className="h-4 bg-muted rounded w-48 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-5xl">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <Link
            href="/content"
            className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mb-2 transition-colors"
          >
            <ArrowLeft size={11} /> Content
          </Link>
          <h1 className="text-xl font-bold font-display tracking-tight leading-tight">
            {item.title}
          </h1>
          <div className="flex items-center gap-3 mt-1">
            {item.focusKeyword && (
              <span className="text-xs text-muted-foreground">
                Focus: <span className="font-medium">{item.focusKeyword}</span>
              </span>
            )}
            {item.wordCount && (
              <span className="text-xs font-mono text-muted-foreground">
                {item.wordCount.toLocaleString()} words
              </span>
            )}
            {item.generationCost && (
              <span className="text-xs font-mono text-muted-foreground">
                ${item.generationCost.toFixed(4)}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <select
            value={item.status}
            onChange={(e) => handleStatusChange(e.target.value)}
            className="h-8 rounded-md border border-input bg-background px-2 text-xs focus:outline-none focus:ring-2 focus:ring-ring"
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>

          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-1.5 h-8 px-3 bg-primary text-primary-foreground rounded-md text-xs font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {saved ? <CheckCircle2 size={12} /> : <Save size={12} />}
            {saved ? "Saved" : saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Editor — 2/3 width */}
        <div className="col-span-2 space-y-4">
          {item.metaDescription && (
            <div className="bg-muted/40 border border-border rounded-lg px-4 py-3">
              <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-0.5">
                Meta description
              </p>
              <p className="text-sm text-foreground/80">{item.metaDescription}</p>
            </div>
          )}

          <div>
            <label className="text-[13px] font-medium text-foreground block mb-1.5">
              Markdown content
            </label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={40}
              className="w-full rounded-lg border border-input bg-background px-4 py-3 text-sm font-mono leading-relaxed placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-y"
              spellCheck={false}
            />
          </div>
        </div>

        {/* Sidebar — 1/3 width */}
        <div className="space-y-6">
          {/* Publish to CMS */}
          <div className="border border-border rounded-lg p-4 space-y-3">
            <h3 className="text-sm font-medium flex items-center gap-2">
              <Globe size={14} /> Publish to CMS
            </h3>
            {cmsConnections.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No CMS connected.{" "}
                <Link href="/settings/integrations" className="text-primary hover:underline">
                  Add one
                </Link>
              </p>
            ) : (
              <>
                <select
                  value={selectedCms}
                  onChange={(e) => setSelectedCms(e.target.value)}
                  className="w-full border border-border rounded-md px-2 py-1.5 text-xs bg-background"
                >
                  {cmsConnections.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.type})
                    </option>
                  ))}
                </select>
                <button
                  onClick={handlePublish}
                  disabled={publishing || !selectedCms}
                  className="w-full text-xs px-3 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  {publishing ? "Queuing..." : "Publish"}
                </button>
                {publishMessage && (
                  <p className="text-xs text-muted-foreground">{publishMessage}</p>
                )}
              </>
            )}
          </div>

          {/* Social Posts */}
          <div className="border border-border rounded-lg p-4 space-y-3">
            <h3 className="text-sm font-medium flex items-center gap-2">
              <Share2 size={14} /> Social Distribution
            </h3>
            {socialPosts.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                No social posts generated yet. Run the pipeline to auto-generate them.
              </p>
            ) : (
              <div className="space-y-3">
                {socialPosts.map((post) => {
                  const isConnected = socialConnections.some((c) => c.platform === post.platform);
                  const isReddit = post.platform === "reddit";
                  return (
                    <div key={post.id} className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-medium capitalize">{post.platform}</span>
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                            post.status === "posted"
                              ? "bg-green-500/10 text-green-600"
                              : post.status === "failed"
                              ? "bg-destructive/10 text-destructive"
                              : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {post.status}
                        </span>
                      </div>
                      {isReddit && post.redditTitle && (
                        <p className="text-[11px] font-medium text-foreground/80">
                          {post.redditTitle}
                        </p>
                      )}
                      <p className="text-[11px] text-muted-foreground line-clamp-3">{post.body}</p>
                      {post.hashtags.length > 0 && (
                        <p className="text-[10px] text-primary/70">
                          {post.hashtags.map((h) => `#${h}`).join(" ")}
                        </p>
                      )}
                      {!isReddit && post.status === "draft" && (
                        isConnected ? (
                          <button
                            onClick={() => handleDistribute(post)}
                            disabled={distributing === post.id}
                            className="w-full text-[11px] px-2 py-1.5 rounded border border-primary/30 text-primary hover:bg-primary/10 disabled:opacity-50"
                          >
                            {distributing === post.id ? "Queuing..." : `Post to ${post.platform}`}
                          </button>
                        ) : (
                          <Link
                            href="/settings/integrations"
                            className="block text-center text-[11px] px-2 py-1.5 rounded border border-border text-muted-foreground hover:bg-muted"
                          >
                            Connect {post.platform}
                          </Link>
                        )
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
