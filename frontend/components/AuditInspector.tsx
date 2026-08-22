import type { AuditRecord } from "@/lib/api";
import { PERSONAS, type PersonaId } from "@/lib/personas";
import { SectionLabel } from "@/components/ui";

export function AuditInspector({ audit }: { audit: AuditRecord | null }) {
  if (!audit) {
    return (
      <div className="p-5 text-[13px] leading-relaxed text-[var(--ink-subtle)]">
        <SectionLabel>Audit trail</SectionLabel>
        Select an answer to see exactly which clauses were examined and cited — the record behind every decision.
      </div>
    );
  }
  const pct = audit.clauses_examined_count
    ? Math.round((audit.clauses_cited_count / audit.clauses_examined_count) * 100) : 0;
  const when = new Date(audit.timestamp).toLocaleString();

  return (
    <div className="flex h-full flex-col">
      <div className="border-b p-5">
        <SectionLabel>Audit trail</SectionLabel>
        <div className="flex items-baseline gap-2">
          <span className="mono text-[26px] w-strong text-[var(--ink)]">{audit.clauses_examined_count}</span>
          <span className="text-[13px] text-[var(--ink-muted)]">clauses examined</span>
        </div>
        <div className="mt-1 text-[12.5px] text-[var(--ink-muted)]">
          across {audit.insurers_examined.length} insurer{audit.insurers_examined.length !== 1 ? "s" : ""} ·
          <span className="mono"> {audit.clauses_cited_count}</span> cited ({pct}%)
        </div>
        {audit.referred_to && (
          <div className="mt-3 rounded-[8px] px-3 py-2 text-[12.5px]"
               style={{ background: PERSONAS[audit.referred_to as PersonaId]?.accentSoft }}>
            Referred to <span className="w-ui" style={{ color: PERSONAS[audit.referred_to as PersonaId]?.accent }}>
              {PERSONAS[audit.referred_to as PersonaId]?.name}</span>
          </div>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        <SectionLabel>Every clause read</SectionLabel>
        <ul className="space-y-1">
          {audit.clauses_examined.map((c, i) => (
            <li key={i} className="mono flex items-start gap-2 py-1 text-[11.5px] leading-snug">
              <span className={`mt-1 h-1.5 w-1.5 flex-none rounded-full`}
                    style={{ background: c.is_exclusion ? "var(--notcovered)" : "var(--hairline-strong)" }} />
              <span>
                <span className="w-ui text-[var(--ink)]">{c.insurer}</span>
                <span className="text-[var(--ink-subtle)]"> · </span>
                <span className="text-[var(--ink-muted)]">{c.section ?? "—"}{c.page != null ? ` · p${c.page}` : ""}</span>
                {c.is_exclusion && <span className="ml-1 text-[var(--notcovered)]">excl</span>}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="border-t p-4">
        <div className="mono text-[10.5px] text-[var(--ink-subtle)]">{when}</div>
      </div>
    </div>
  );
}