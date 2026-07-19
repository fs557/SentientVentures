import type { ReactNode } from "react";

export function StatusNotice({ tone, title, children }: { tone: "error" | "empty" | "loading" | "warning"; title: string; children: ReactNode }): ReactNode {
  return <section className={`sv-status sv-status--${tone}`} role={tone === "error" ? "alert" : "status"} aria-live="polite"><h2>{title}</h2><div>{children}</div></section>;
}
