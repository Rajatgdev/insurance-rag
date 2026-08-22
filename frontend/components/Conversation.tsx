import { useRef, useEffect } from "react";
import type { Envelope } from "@/lib/api";
import { PERSONAS, type PersonaId } from "@/lib/personas";
import { ClarifyView, ReferralView, VerdictView, WordingReadView, ComparisonView } from "@/components/renderers";

export type Turn =
  | { who: "user"; text: string }
  | { who: "bot"; env: Envelope };

function BotBody({ env, onHandoff }: { env: Envelope; onHandoff: (to: PersonaId) => void }) {
  const a = env.answer;
  if (a.mode === "clarify") return <ClarifyView a={a} />;
  if (a.mode === "refer") return <ReferralView a={a} onHandoff={onHandoff} />;
  if (env.output_kind === "verdict") return <VerdictView a={a} />;
  if (env.output_kind === "wording_read") return <WordingReadView a={a} />;
  return <ComparisonView a={a} />;
}

export function Conversation({
  persona, turns, busy, input, setInput, onSend, onSelectTurn, selectedTurn, onHandoff,
}: {
  persona: PersonaId;
  turns: Turn[];
  busy: boolean;
  input: string;
  setInput: (s: string) => void;
  onSend: () => void;
  onSelectTurn: (i: number) => void;
  selectedTurn: number | null;
  onHandoff: (to: PersonaId) => void;
}) {
  const endRef = useRef<HTMLDivElement>(null);
  const p = PERSONAS[persona];
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [turns.length, busy]);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex flex-none items-center gap-2.5 border-b bg-[var(--surface)] px-6 py-3.5">
        <span className="h-6 w-6 rounded-full text-center text-[12px] w-strong leading-6 text-white" style={{ background: p.accent }}>{p.name[0]}</span>
        <span className="text-[14px] w-ui text-[var(--ink)]">{p.name}</span>
        <span className="text-[12.5px] text-[var(--ink-subtle)]">· {p.role}</span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-6">
        <div className="mx-auto max-w-2xl space-y-5">
          {turns.length === 0 && (
            <div className="pt-16 text-center">
              <p className="mx-auto max-w-md text-[14.5px] leading-relaxed text-[var(--ink-muted)]">{p.blurb}</p>
              <p className="mt-2 text-[12.5px] text-[var(--ink-subtle)]">Ask a question below — I’ll check the cover and the exclusions, and show my work.</p>
            </div>
          )}

          {turns.map((t, i) =>
            t.who === "user" ? (
              <div key={i} className="flex justify-end">
                <div className="max-w-[82%] rounded-[14px] rounded-br-[4px] px-4 py-2.5 text-[14.5px] leading-snug text-white" style={{ background: p.accent }}>{t.text}</div>
              </div>
            ) : (
              <div key={i} role="button" tabIndex={0}
                onClick={() => onSelectTurn(i)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelectTurn(i); } }}
                className="block w-full cursor-pointer rounded-[14px] border bg-[var(--surface)] p-4 text-left transition"
                style={{ boxShadow: selectedTurn === i ? `0 0 0 1.5px ${p.accent}` : "0 1px 2px rgba(20,25,28,.04)" }}>
                <BotBody env={t.env} onHandoff={onHandoff} />
              </div>
            )
          )}

          {busy && <div className="thinking mono text-[12px] text-[var(--ink-subtle)]">reading the policy…</div>}
          <div ref={endRef} />
        </div>
      </div>

      <div className="flex-none border-t bg-[var(--surface)] px-6 py-4">
        <div className="mx-auto flex max-w-2xl items-end gap-2 rounded-[12px] border bg-[var(--surface)] p-2"
             style={{ boxShadow: "0 1px 2px rgba(20,25,28,.04)" }}>
          <textarea
            value={input} onChange={(e) => setInput(e.target.value)} rows={1}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSend(); } }}
            placeholder={`Ask ${p.name}…`}
            className="max-h-32 flex-1 resize-none bg-transparent px-2 py-1.5 text-[14.5px] outline-none placeholder:text-[var(--ink-subtle)]" />
          <button onClick={onSend} disabled={busy || !input.trim()}
            className="rounded-[8px] px-4 py-2 text-[14px] w-ui text-white transition active:scale-[.98] disabled:opacity-40"
            style={{ background: p.accent }}>Ask</button>
        </div>
      </div>
    </div>
  );
}