import type { CompaniesList, CompanyEvaluation } from "@sv/contracts/generated";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error { constructor(message: string, public readonly status?: number) { super(message); } }

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, { signal, headers: { Accept: "application/json" } });
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { error?: { message?: string } } | null;
    throw new ApiError(body?.error?.message ?? `Request failed (${response.status})`, response.status);
  }
  return response.json() as Promise<T>;
}
export const getCompanies = (signal?: AbortSignal) => request<CompaniesList>("/companies", signal);
export const getCompany = (slug: string, signal?: AbortSignal) => request<CompanyEvaluation>(`/companies/${encodeURIComponent(slug)}`, signal);
