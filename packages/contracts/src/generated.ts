/**
 * Checked-in declarations generated from the v1 JSON Schema contract.
 * Schema files remain canonical; regenerate this file whenever their version changes.
 */
export type EvaluationCategory = "home" | "idea" | "market" | "financial" | "management";
export type EvidenceKind = "fact" | "inference";
export type JobState = "queued" | "validating" | "extracting" | "classifying" | "fact_extracting" | "council_preparing" | "pro_analysis" | "contra_analysis" | "judging" | "markdown_validating" | "repairing" | "scoring" | "indexing" | "ready" | "failed";
export type ValidationIssue = { code: string; path: string; message: string; severity: "warning" | "error" };
export type EvidenceReference = { kind: EvidenceKind; documentId: string; page?: number; section?: string; text: string };
export type FactRecord = { id: string; subject: "company" | "founder" | "investment" | "market" | "financial"; field: string; value: string | number | boolean | string[] | null; status: "fact" | "inference" | "missing_information"; evidence: EvidenceReference[]; missingReason?: string; sourceDocumentIds: string[] };
export type EvaluationItem = { id: string; category: EvaluationCategory; title: string; score: number | null; confidence: number | null; assessment: string; positiveArguments: string[]; negativeArguments: string[]; evidence: EvidenceReference[]; missingInformation: string[]; sourceReferences: EvidenceReference[]; validationErrors: ValidationIssue[] };
export type EvaluationDocument = { schemaVersion: 1; registryVersion: 1; company: string; slug: string; category: EvaluationCategory; generatedAt: string; sourceDocuments: string[]; items: EvaluationItem[]; validationErrors: ValidationIssue[] };
export type InvestmentTerms = { amount: number | null; currency: string | null; equityPercentage: number | null; preMoneyValuation: number | null; postMoneyValuation: number | null; impliedValuation: number | null; useOfFunds: string[] };
export type CategoryScores = { home: null; idea: number | null; market: number | null; financial: number | null; management: number | null };
export type CompanyEvaluation = { companyId: string; company: string; slug: string; stage: string | null; submissionDate: string; investment: InvestmentTerms; categories: Partial<Record<EvaluationCategory, EvaluationDocument>>; categoryScores: CategoryScores; overallScore: number | null; validationErrors: ValidationIssue[] };
export type ApiError = { error: { code: string; message: string; details: Array<{ path: string; code: string; message: string }>; requestId: string } };
export type JobStatus = { id: string; companySlug: string; state: JobState; stage: string; progress: number; attempt: 1 | 2; repairCount: 0 | 1; updatedAt: string; error: Record<string, unknown> | null; retryAllowed: boolean };
export type SubmissionAccepted = { company: { id: string; slug: string; name: string }; job: { id: string; state: "queued"; statusUrl: string }; acceptedAt: string };
export type CompanySummary = { slug: string; company: string; stage: string | null; submissionDate: string; overallScore: number | null; categoryScores: CategoryScores };
export type CompaniesList = { companies: CompanySummary[]; registryVersion: 1 };
export type RegistryEntry = { id: string; category: EvaluationCategory; title: string; scoreRequired: boolean; portfolioRequired: boolean; displayOrder: number; rubric: string };
