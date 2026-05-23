"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import type { Project } from "@findme/types";

export default function NewProjectPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const fd = new FormData(e.currentTarget);
    try {
      const project = await apiClient.post<Project>("/api/projects", {
        name: fd.get("name"),
        websiteUrl: fd.get("websiteUrl"),
        businessDescription: fd.get("businessDescription") || null,
        targetAudience: fd.get("targetAudience") || null,
        industry: fd.get("industry") || null,
      });
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold font-display tracking-tight">New project</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Add your website to start tracking and improving visibility.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <Field label="Project name" name="name" required placeholder="My Company" />
        <Field label="Website URL" name="websiteUrl" type="url" required placeholder="https://example.com" />
        <Field label="Business description" name="businessDescription" as="textarea" placeholder="What does your business do?" />
        <Field label="Target audience" name="targetAudience" placeholder="e.g. B2B SaaS founders" />
        <Field label="Industry" name="industry" placeholder="e.g. Software, E-commerce" />

        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={loading}
            className="h-9 px-5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {loading ? "Creating..." : "Create project"}
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="h-9 px-5 border border-border rounded-md text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

function Field({
  label,
  name,
  type = "text",
  required,
  placeholder,
  as,
}: {
  label: string;
  name: string;
  type?: string;
  required?: boolean;
  placeholder?: string;
  as?: "textarea";
}) {
  const base =
    "mt-1.5 w-full rounded-md border border-input bg-background px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring transition-shadow";

  return (
    <div>
      <label className="text-[13px] font-medium text-foreground" htmlFor={name}>
        {label}
        {required ? <span className="text-destructive ml-0.5">*</span> : null}
      </label>
      {as === "textarea" ? (
        <textarea
          id={name}
          name={name}
          placeholder={placeholder}
          rows={3}
          className={`${base} py-2 resize-none`}
        />
      ) : (
        <input
          id={name}
          name={name}
          type={type}
          required={required}
          placeholder={placeholder}
          className={`${base} h-9`}
        />
      )}
    </div>
  );
}
