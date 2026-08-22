import type { Answer } from "@/lib/api";
import { PERSONAS, VERDICT_STYLE, type PersonaId } from "@/lib/personas";
import { ClauseRef, CitedPoint, SectionLabel } from "@/components/ui";

/* ── clarify (all personas) ── */
export function ClarifyView({ a }: { a: Answer }) {
  return (
    <div>
      <SectionLabel>A few details to pin this down</SectionLabel>
      <ol className="space-y-2">
        {a.questions.map((q, i) => (
          <li key={i} className="flex gap-3 rounded-[10px] border bg-[var(--surface)] px-4 py-3 text-[14.5px] leading-snug">
            <span className="mono w-ui text-[13px]" style={{ color: "var(--accent)" }}>{i + 1}</span>
            <span>{q}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

/* ── refer (out-of-lane handoff offer) ── */
export function ReferralView({ a, onHandoff }: { a: Answer; onHandoff: (to: PersonaId) => void }) {
  const r = a.referral!;
  const target = PERSONAS[r.to_persona as PersonaId];
  return (
    <div className="rounded-[12px] border bg-[var(--surface)] p-4">
      <SectionLabel>Out of my lane</SectionLabel>
      <p className="text-[14.5px] leading-relaxed text-[var(--ink)]">{r.reason}</p>
      <div className="mono mt-3 rounded-[8px] bg-[var(--surface-2)] p-3 text-[12px] text-[var(--ink-muted)]">
        {r.facts.topic && <div><span className="text-[var(--ink-subtle)]">topic </span>{r.facts.topic}</div>}
        {r.facts.insurers?.length > 0 && <div><span className="text-[var(--ink-subtle)]">insurers </span>{r.facts.insurers.join(", ")}</div>}
        {r.facts.circumstances && <div><span className="text-[var(--ink-subtle)]">details </span>{r.facts.circumstances}</div>}
      </div>
      <button
        onClick={() => onHandoff(r.to_persona as PersonaId)}
        className="mt-3 w-full rounded-[8px] px-4 py-2.5 text-[14px] w-ui text-white transition active:scale-[.99]"
        style={{ background: target?.accent ?? "var(--accent)" }}>
        Hand off to {r.to_name} →
      </button>
    </div>
  );
}

/* ── verdict (Ciara) ── */
export function VerdictView({ a }: { a: Answer }) {
  const v = (a.verdict && VERDICT_STYLE[a.verdict]) || VERDICT_STYLE["Unclear"];
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <span className="rounded-full px-3 py-1 text-[13px] w-ui" style={{ color: v.fg, background: v.bg }}>
          {a.verdict ?? "Unclear"}
        </span>
        {a.confidence != null && (
          <span className="mono text-[11px] text-[var(--ink-subtle)]">confidence {Math.round(a.confidence * 100)}%</span>
        )}
      </div>
      {a.answer && <p className="whitespace-pre-line text-[15px] leading-relaxed text-[var(--ink)]">{a.answer}</p>}
      {a.excess && (
        <div className="rounded-[8px] border bg-[var(--surface-2)] px-3 py-2 text-[13.5px]">
          <span className="eyebrow mr-2">Excess</span>{a.excess}
        </div>
      )}
      {a.citations && a.citations.length > 0 && (
        <div><SectionLabel>Grounded in</SectionLabel><ul className="space-y-2.5">{a.citations.map((c, i) => <CitedPoint key={i} c={c} />)}</ul></div>
      )}
      {a.exclusions_checked && a.exclusions_checked.length > 0 && (
        <div>
          <SectionLabel>Exclusions checked</SectionLabel>
          <ul className="flex flex-wrap gap-1.5">
            {a.exclusions_checked.map((e, i) => (
              <li key={i} className="rounded-[6px] border bg-[var(--surface)] px-2 py-1 text-[12px] text-[var(--ink-muted)]">{e}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/* ── wording read (Brian) ── */
function ListBlock({ label, items }: { label: string; items?: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div><SectionLabel>{label}</SectionLabel>
      <ul className="space-y-1.5">{items.map((g, i) => (
        <li key={i} className="text-[14px] leading-snug text-[var(--ink)] before:mr-2 before:text-[var(--ink-subtle)] before:content-['—']">{g}</li>
      ))}</ul>
    </div>
  );
}
export function WordingReadView({ a }: { a: Answer }) {
  return (
    <div className="space-y-5">
      {a.summary && <p className="text-[15px] leading-relaxed text-[var(--ink)]">{a.summary}</p>}
      <ListBlock label="Grants of cover" items={a.grants} />
      {a.notable_exclusions && a.notable_exclusions.length > 0 && (
        <div><SectionLabel>Notable exclusions</SectionLabel><ul className="space-y-2.5">{a.notable_exclusions.map((c, i) => <CitedPoint key={i} c={c} />)}</ul></div>
      )}
      {a.warranties_conditions && a.warranties_conditions.length > 0 && (
        <div><SectionLabel>Warranties & conditions</SectionLabel><ul className="space-y-2.5">{a.warranties_conditions.map((c, i) => <CitedPoint key={i} c={c} />)}</ul></div>
      )}
      <ListBlock label="Gaps a veteran would flag" items={a.gaps} />
      <ListBlock label="Endorsements, in plain English" items={a.endorsements_plain} />
    </div>
  );
}

/* ── comparison matrix (Darragh) ── */
export function ComparisonView({ a }: { a: Answer }) {
  const cols = a.insurers ?? [];
  return (
    <div className="space-y-4">
      {a.topic && <div className="text-[15px] w-ui text-[var(--ink)]">Comparing: {a.topic}</div>}
      <div className="overflow-x-auto rounded-[12px] border">
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="bg-[var(--surface-2)]">
              <th className="eyebrow sticky left-0 z-10 bg-[var(--surface-2)] px-3 py-2 text-left">Dimension</th>
              {cols.map((c) => <th key={c} className="px-3 py-2 text-left w-ui text-[var(--ink)] whitespace-nowrap">{c}</th>)}
            </tr>
          </thead>
          <tbody>
            {(a.rows ?? []).map((row, ri) => (
              <tr key={ri} className="border-t align-top">
                <td className="sticky left-0 z-10 bg-[var(--surface)] px-3 py-2.5 w-ui text-[var(--ink)] whitespace-nowrap">{row.dimension}</td>
                {cols.map((col) => {
                  const cell = row.cells.find((c) => c.insurer === col);
                  if (!cell) return <td key={col} className="px-3 py-2.5 text-[var(--ink-subtle)]">—</td>;
                  const sourced = !!cell.section;
                  return (
                    <td key={col} className="px-3 py-2.5"
                        style={cell.is_gap && sourced ? { background: "var(--partial-bg)" } : undefined}>
                      <div className={sourced ? "text-[var(--ink)] leading-snug" : "italic text-[var(--ink-subtle)] leading-snug"}>{cell.value}</div>
                      {sourced ? (
                        <div className="mono tnum mt-1 text-[10.5px] text-[var(--ink-subtle)]">{cell.section}{cell.page != null ? ` · p${cell.page}` : ""}</div>
                      ) : (
                        <div className="mono mt-1 text-[10px] text-[var(--ink-subtle)]">not shown — confirm directly</div>
                      )}
                      {cell.is_gap && sourced && <div className="mono mt-1 text-[10px] w-ui" style={{ color: "var(--partial)" }}>GAP</div>}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {a.gaps && a.gaps.length > 0 && (
        <div><SectionLabel>Gaps to raise</SectionLabel>
          <ul className="space-y-1.5">{a.gaps.map((g, i) => (
            <li key={i} className="text-[13.5px] leading-snug text-[var(--ink)] before:mr-2 before:content-['!'] before:text-[var(--partial)] before:w-ui">{g}</li>
          ))}</ul>
        </div>
      )}
      {a.summary && <p className="rounded-[10px] border bg-[var(--surface-2)] p-3 text-[14px] leading-relaxed text-[var(--ink-muted)]">{a.summary}</p>}
    </div>
  );
}