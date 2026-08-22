import { PERSONAS, PERSONA_ORDER, type PersonaId } from "@/lib/personas";

export interface ThreadMeta { id: string; persona: PersonaId; title: string; originName?: string }

export function PersonaRail({
  active, threads, activeThreadId, onSelectPersona, onSelectThread, onNewThread,
}: {
  active: PersonaId;
  threads: ThreadMeta[];
  activeThreadId: string | null;
  onSelectPersona: (p: PersonaId) => void;
  onSelectThread: (id: string) => void;
  onNewThread: (p: PersonaId) => void;
}) {
  return (
    <div className="flex h-full flex-col bg-[var(--surface)]">
      <div className="border-b px-4 py-4">
        <div className="text-[15px] w-strong text-[var(--ink)]">Motor Co-Pilot</div>
        <div className="eyebrow mt-0.5">Irish private motor</div>
      </div>

      {/* seats */}
      <div className="flex flex-col gap-1 p-3">
        {PERSONA_ORDER.map((pid) => {
          const p = PERSONAS[pid];
          const on = pid === active;
          return (
            <button key={pid} onClick={() => onSelectPersona(pid)}
              className="flex items-start gap-3 rounded-[10px] px-3 py-2.5 text-left transition"
              style={{ background: on ? p.accentSoft : "transparent" }}>
              <span className="mt-0.5 h-7 w-7 flex-none rounded-full text-center text-[13px] w-strong leading-7 text-white"
                    style={{ background: p.accent, opacity: on ? 1 : 0.4 }}>
                {p.name[0]}
              </span>
              <span className="min-w-0">
                <span className="block text-[13.5px] w-ui" style={{ color: on ? p.accent : "var(--ink)" }}>{p.name}</span>
                <span className="block truncate text-[11.5px] text-[var(--ink-subtle)]">{p.role}</span>
              </span>
            </button>
          );
        })}
      </div>

      {/* threads for active seat */}
      <div className="min-h-0 flex-1 overflow-y-auto border-t px-3 py-3">
        <div className="mb-2 flex items-center justify-between px-1">
          <span className="eyebrow">{PERSONAS[active].name}’s threads</span>
          <button onClick={() => onNewThread(active)}
            className="mono rounded-[6px] border px-2 py-0.5 text-[11px] text-[var(--ink-muted)] transition hover:text-[var(--ink)]">+ new</button>
        </div>
        <div className="flex flex-col gap-0.5">
          {threads.filter((t) => t.persona === active).map((t) => (
            <button key={t.id} onClick={() => onSelectThread(t.id)}
              className="truncate rounded-[7px] px-2.5 py-2 text-left text-[13px] transition"
              style={{ background: t.id === activeThreadId ? "var(--surface-2)" : "transparent",
                       color: t.id === activeThreadId ? "var(--ink)" : "var(--ink-muted)" }}>
              {t.originName && <span className="mono mr-1 text-[10px] text-[var(--ink-subtle)]">↳</span>}
              {t.title}
            </button>
          ))}
          {threads.filter((t) => t.persona === active).length === 0 && (
            <div className="px-2.5 py-2 text-[12px] text-[var(--ink-subtle)]">No threads yet.</div>
          )}
        </div>
      </div>
    </div>
  );
}