"use client";

import { useState } from "react";
import { chat, type Envelope, type HandoffFacts, type Message, type ReferralNote } from "@/lib/api";
import { PERSONAS, type PersonaId } from "@/lib/personas";
import { PersonaRail, type ThreadMeta } from "@/components/PersonaRail";
import { Conversation, type Turn } from "@/components/Conversation";
import { AuditInspector } from "@/components/AuditInspector";

interface Thread {
  meta: ThreadMeta;
  turns: Turn[];
  seededHandoff?: HandoffFacts;   // consumed on the first send after a handoff
}

let SEQ = 1;
const newId = () => `t${SEQ++}`;

function shortTitle(s: string) {
  const t = s.trim().replace(/\s+/g, " ");
  return t.length > 42 ? t.slice(0, 42) + "…" : t || "New thread";
}

// Turn carried facts into a readable opening line (mirrors the backend seed).
function seedText(f: HandoffFacts): string {
  const parts: string[] = [];
  if (f.topic) parts.push(f.topic);
  if (f.insurers?.length) parts.push(`across ${f.insurers.join(", ")}`);
  if (f.circumstances) parts.push(`— ${f.circumstances}`);
  return parts.join(" ") || "(handoff)";
}

export default function Page() {
  const [active, setActive] = useState<PersonaId>("ciara");
  const [threads, setThreads] = useState<Record<string, Thread>>({});
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [selectedTurn, setSelectedTurn] = useState<number | null>(null);

  const threadList = Object.values(threads).map((t) => t.meta);
  const current = activeThreadId ? threads[activeThreadId] ?? null : null;

  function selectPersona(p: PersonaId) {
    setActive(p);
    const mine = Object.values(threads).filter((t) => t.meta.persona === p);
    setActiveThreadId(mine.length ? mine[mine.length - 1].meta.id : null);
    setSelectedTurn(null);
  }

  // Core send. Optionally target a specific thread + carry seeded facts (used by handoff).
  async function sendTo(threadId: string, text: string, persona: PersonaId, seeded?: HandoffFacts) {
    const existing = threads[threadId];
    const priorTurns = existing ? existing.turns : [];
    const nextTurns: Turn[] = [...priorTurns, { who: "user", text }];

    setThreads((prev) => {
      const cur = prev[threadId];
      return {
        ...prev,
        [threadId]: {
          ...cur,
          turns: nextTurns,
          seededHandoff: undefined,
          meta: { ...cur.meta, title: priorTurns.length === 0 ? shortTitle(text) : cur.meta.title },
        },
      };
    });
    setInput("");
    setBusy(true);

    const history: Message[] = nextTurns.map((t) =>
      t.who === "user"
        ? { role: "user" as const, content: t.text }
        : { role: "assistant" as const, content: summarize(t.env) });

    try {
      const env = await chat(history, persona, seeded);
      setThreads((prev) => {
        const cur = prev[threadId];
        if (!cur) return prev;
        const turns = [...cur.turns, { who: "bot", env } as Turn];
        return { ...prev, [threadId]: { ...cur, turns } };
      });
      setSelectedTurn(nextTurns.length); // the bot turn we just appended
    } catch {
      setThreads((prev) => {
        const cur = prev[threadId];
        if (!cur) return prev;
        const env: Envelope = {
          persona, output_kind: "verdict",
          answer: { mode: "answer", questions: [], verdict: "Unclear", answer: "Couldn't reach the policy service — is the backend running on :8000?", citations: [], exclusions_checked: [], confidence: null, referral: null },
          audit: { persona, query: text, insurers_examined: [], clauses_examined: [], clauses_examined_count: 0, clauses_cited_count: 0, referred_to: null, timestamp: new Date().toISOString() },
        };
        return { ...prev, [threadId]: { ...cur, turns: [...cur.turns, { who: "bot", env }] } };
      });
    } finally {
      setBusy(false);
    }
  }

  function send() {
    const text = input.trim();
    if (!text || busy) return;

    let tid = activeThreadId;
    if (!tid || threads[tid]?.meta.persona !== active) {
      tid = newId();
      const id = tid;
      setThreads((prev) => ({ ...prev, [id]: { meta: { id, persona: active, title: "New thread" }, turns: [] } }));
      setActiveThreadId(tid);
    }
    void sendTo(tid, text, active);
  }

  function newThread(p: PersonaId) {
    const id = newId();
    setThreads((prev) => ({ ...prev, [id]: { meta: { id, persona: p, title: "New thread" }, turns: [] } }));
    setActive(p);
    setActiveThreadId(id);
    setSelectedTurn(null);
  }

  // A confirmed referral: open a fresh thread for the target, seed it, and immediately
  // send the carried facts AS the user's first turn — so the question appears and is answered.
  function handoff(ref: ReferralNote) {
    const to = ref.to_persona as PersonaId;
    const id = newId();
    const question = seedText(ref.facts);
    setThreads((prev) => ({
      ...prev,
      [id]: { meta: { id, persona: to, title: shortTitle(ref.facts.topic || "Handoff"), originName: PERSONAS[active].name }, turns: [] },
    }));
    setActive(to);
    setActiveThreadId(id);
    setSelectedTurn(null);
    // send after state commit
    setTimeout(() => void sendTo(id, question, to, ref.facts), 0);
  }

  const selectedEnv =
    current && selectedTurn != null && current.turns[selectedTurn]?.who === "bot"
      ? (current.turns[selectedTurn] as { env: Envelope }).env
      : null;

  // The referral to act on when the handoff button is pressed = latest refer turn in this thread.
  function currentReferral(): ReferralNote | null {
    if (!current) return null;
    for (let i = current.turns.length - 1; i >= 0; i--) {
      const t = current.turns[i];
      if (t.who === "bot" && t.env.answer.mode === "refer" && t.env.answer.referral) return t.env.answer.referral;
    }
    return null;
  }

  return (
    <main className="grid h-screen grid-cols-[248px_1fr_320px] overflow-hidden"
          style={{ ["--accent" as string]: PERSONAS[active].accent, ["--accent-soft" as string]: PERSONAS[active].accentSoft }}>
      <aside className="min-h-0 border-r"><PersonaRail
        active={active} threads={threadList} activeThreadId={activeThreadId}
        onSelectPersona={selectPersona}
        onSelectThread={(id) => { setActive(threads[id].meta.persona); setActiveThreadId(id); setSelectedTurn(null); }}
        onNewThread={newThread} /></aside>

      <section className="min-h-0 min-w-0"><Conversation
        persona={active}
        turns={current?.turns ?? []}
        busy={busy} input={input} setInput={setInput} onSend={send}
        selectedTurn={selectedTurn} onSelectTurn={setSelectedTurn}
        onHandoff={() => { const r = currentReferral(); if (r) handoff(r); }} /></section>

      <aside className="min-h-0 border-l bg-[var(--surface)]"><AuditInspector audit={selectedEnv?.audit ?? null} /></aside>
    </main>
  );
}

function summarize(env: Envelope): string {
  const a = env.answer;
  if (a.mode === "clarify") return a.questions.join(" ");
  if (a.mode === "refer") return `Referred to ${a.referral?.to_name}.`;
  if (env.output_kind === "verdict") return `${a.verdict}. ${a.answer ?? ""}`;
  if (env.output_kind === "wording_read") return a.summary ?? "Wording read.";
  return `Comparison of ${a.topic ?? "cover"} across ${(a.insurers ?? []).join(", ")}.`;
}