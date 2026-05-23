import { z } from "zod";

export const CreateProjectSchema = z.object({
  name: z.string().min(1).max(100),
  websiteUrl: z.string().url(),
  businessDescription: z.string().max(2000).nullable().optional(),
  targetAudience: z.string().max(500).nullable().optional(),
  industry: z.string().max(100).nullable().optional(),
  language: z.string().default("en"),
});
export type CreateProjectInput = z.infer<typeof CreateProjectSchema>;

export const RunPipelineSchema = z.object({
  keywordIds: z.array(z.string()).optional(),
  contentTypes: z.array(z.string()).optional(),
});
export type RunPipelineInput = z.infer<typeof RunPipelineSchema>;

export const ProgressStepSchema = z.object({
  name: z.string(),
  status: z.enum(["pending", "running", "completed", "failed"]),
  message: z.string().nullable(),
  startedAt: z.string().nullable(),
  completedAt: z.string().nullable(),
});

export const AgentJobSchema = z.object({
  id: z.string(),
  orgId: z.string(),
  projectId: z.string(),
  type: z.string(),
  status: z.enum(["queued", "running", "completed", "failed", "cancelled"]),
  progress: z.number().min(0).max(100),
  progressSteps: z.array(ProgressStepSchema),
  outputData: z.record(z.unknown()).nullable(),
  errorMessage: z.string().nullable(),
  creditsUsed: z.number().nullable(),
  startedAt: z.string().nullable(),
  completedAt: z.string().nullable(),
});
export type AgentJobResponse = z.infer<typeof AgentJobSchema>;
