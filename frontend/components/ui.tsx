import type { Citation } from "@/lib/api";

/** The signature motif: a clause reference rendered as a technical identifier. */
export function ClauseRef({ c }: { c: Citation }) {
  return (
    <span className="mono inline-flex items-center gap-1 rounded-[5px] border bg-[var(--surface-2)] px-1.5 py-0.5 text-[11px] text-[var(--ink-muted)]">
      <span className="w-ui text-[var(--ink)]">{c.insurer}</span>
      <span className="text-[var(--ink-subtle)]">·</span>
      <span>{c.section}</span>
      {c.page != null && <><span className="text-[var(--ink-subtle)]">·</span><span>p{c.page}</span></>}
    </span>
  );
}

/** A cited point: the clause ref + its one-line detail. */
export function CitedPoint({ c }: { c: Citation }) {
  return (
    <li className="flex flex-col gap-1 border-l-2 pl-3" style={{ borderColor: "var(--accent)" }}>
      <ClauseRef c={c} />
      <span className="text-[13.5px] leading-snug text-[var(--ink-muted)]">{c.detail}</span>
    </li>
  );
}

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return <div className="eyebrow mb-2">{children}</div>;
}