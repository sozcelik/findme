export type Plan = "starter" | "growth" | "pro" | "enterprise";

export interface Org {
  id: string;
  name: string;
  slug: string;
  plan: Plan;
  stripeCustomerId: string | null;
  stripeSubscriptionId: string | null;
  subscriptionStatus: string | null;
  monthlyCreditLimit: number;
  creditsUsedThisMonth: number;
  createdAt: string;
}

export type UserRole = "owner" | "admin" | "member" | "viewer";

export interface User {
  id: string;
  orgId: string;
  email: string;
  fullName: string | null;
  role: UserRole;
  createdAt: string;
}

export type ProjectStatus = "active" | "paused" | "archived";

export interface Project {
  id: string;
  orgId: string;
  name: string;
  websiteUrl: string;
  businessDescription: string | null;
  targetAudience: string | null;
  industry: string | null;
  language: string;
  visibilityScore: number | null;
  visibilityUpdatedAt: string | null;
  status: ProjectStatus;
  createdAt: string;
}

export type SearchIntent = "informational" | "navigational" | "commercial" | "transactional";

export interface Keyword {
  id: string;
  projectId: string;
  orgId: string;
  keyword: string;
  searchVolume: number | null;
  cpc: number | null;
  keywordDifficulty: number | null;
  searchIntent: SearchIntent | null;
  currentPosition: number | null;
  bestPosition: number | null;
  serpFeatures: Record<string, unknown> | null;
  lastAnalyzedAt: string | null;
}

export type ContentType = "article" | "landing_page" | "faq" | "social_post" | "email" | "ai_optimized";
export type ContentStatus = "draft" | "review" | "approved" | "published" | "archived";

export interface ContentItem {
  id: string;
  projectId: string;
  orgId: string;
  type: ContentType;
  title: string;
  slug: string | null;
  bodyMarkdown: string | null;
  metaTitle: string | null;
  metaDescription: string | null;
  focusKeyword: string | null;
  wordCount: number | null;
  readabilityScore: number | null;
  seoScore: number | null;
  aiVisibilityScore: number | null;
  status: ContentStatus;
  campaignId: string | null;
  aiModelUsed: string | null;
  generationCost: number | null;
  publishedAt: string | null;
}

export type JobType =
  | "full_pipeline"
  | "seo_analysis"
  | "content_gen"
  | "publish"
  | "social"
  | "outreach"
  | "visual"
  | "visibility_check";

export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface ProgressStep {
  name: string;
  status: "pending" | "running" | "completed" | "failed";
  message: string | null;
  startedAt: string | null;
  completedAt: string | null;
}

export interface AgentJob {
  id: string;
  orgId: string;
  projectId: string;
  campaignId: string | null;
  type: JobType;
  status: JobStatus;
  triggeredBy: string | null;
  celeryTaskId: string | null;
  inputData: Record<string, unknown> | null;
  outputData: Record<string, unknown> | null;
  progress: number;
  progressSteps: ProgressStep[];
  errorMessage: string | null;
  creditsUsed: number | null;
  startedAt: string | null;
  completedAt: string | null;
}

export interface VisibilityScore {
  id: string;
  projectId: string;
  orgId: string;
  scoreDate: string;
  totalScore: number;
  seoQuality: number;
  aiReadability: number;
  semanticClarity: number;
  socialAmplification: number;
  authoritySignals: number;
  distributionCoverage: number;
}

export interface NavItem {
  key: string;
  label: string;
  href: string;
  icon?: string;
}
