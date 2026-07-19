import type { JobStatus, SubmissionAccepted } from "@sv/contracts/generated";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(message: string, public readonly status?: number) { super(message); }
}

async function readError(response: Response): Promise<ApiError> {
  const payload = await response.json().catch(() => null) as { error?: { message?: string } } | null;
  return new ApiError(payload?.error?.message ?? `Request failed (${response.status})`, response.status);
}

export async function createSubmission(data: FormData, idempotencyKey: string): Promise<SubmissionAccepted> {
  const response = await fetch(`${apiBase}/submissions`, { method: "POST", headers: { "Idempotency-Key": idempotencyKey }, body: data });
  if (!response.ok) throw await readError(response);
  return response.json() as Promise<SubmissionAccepted>;
}

export async function getJob(slug: string, signal?: AbortSignal): Promise<JobStatus> {
  const response = await fetch(`${apiBase}/jobs/${encodeURIComponent(slug)}`, { headers: { Accept: "application/json" }, signal });
  if (!response.ok) throw await readError(response);
  return response.json() as Promise<JobStatus>;
}

export async function retryJob(slug: string, idempotencyKey: string): Promise<{ id: string; state: string; attempt: number; statusUrl: string }> {
  const response = await fetch(`${apiBase}/jobs/${encodeURIComponent(slug)}/retry`, { method: "POST", headers: { "Idempotency-Key": idempotencyKey } });
  if (!response.ok) throw await readError(response);
  return response.json() as Promise<{ id: string; state: string; attempt: number; statusUrl: string }>;
}

export type DirectoryProject = { id: string; title: string | null; relationship: string; completed: boolean };
export type DirectoryPerson = { id: string; name: string; university: string | null; city: string | null; projects: DirectoryProject[] };
export async function searchPeople(query: string, signal?: AbortSignal): Promise<DirectoryPerson[]> { const response = await fetch(`${apiBase}/people/search?q=${encodeURIComponent(query)}`, { headers: { Accept: "application/json" }, signal }); if (!response.ok) throw new ApiError("People directory could not be loaded.", response.status); return (await response.json() as { people: DirectoryPerson[] }).people; }
