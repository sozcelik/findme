"use client";

import { useState, useEffect } from "react";
import type { ProgressStep } from "@findme/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useJobProgress(jobId: string | null) {
  const [steps, setSteps] = useState<ProgressStep[]>([]);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    setSteps([]);
    setDone(false);

    const es = new EventSource(`${API_URL}/api/jobs/${jobId}/stream`);

    es.onmessage = (e) => {
      const step = JSON.parse(e.data) as ProgressStep;
      setSteps((prev) => [...prev.filter((s) => s.name !== step.name), step]);
    };

    es.addEventListener("done", () => {
      setDone(true);
      es.close();
    });

    es.onerror = () => {
      setDone(true);
      es.close();
    };

    return () => es.close();
  }, [jobId]);

  return { steps, done };
}
