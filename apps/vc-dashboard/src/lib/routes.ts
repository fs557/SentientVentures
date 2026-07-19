import type { EvaluationCategory } from "@sv/contracts/generated";

export const categories: EvaluationCategory[] = ["home", "idea", "market", "financial", "management"];
export type Route = { slug: string | null; category: EvaluationCategory };
export function routeFromPath(pathname: string): Route {
  const parts = pathname.split("/").filter(Boolean);
  const category = categories.includes(parts[2] as EvaluationCategory) ? parts[2] as EvaluationCategory : "home";
  return parts[0] === "companies" && parts[1] ? { slug: decodeURIComponent(parts[1]), category } : { slug: null, category };
}
export const companyPath = (slug: string, category: EvaluationCategory) => `/companies/${encodeURIComponent(slug)}/${category}`;
