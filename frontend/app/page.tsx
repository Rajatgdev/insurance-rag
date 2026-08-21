// Root chat page.
"use client";

import { useState, useRef, useEffect } from "react";
import { chat, type Message, type CoPilotResponse } from "@/lib/api";

type Turn =
  | { who: "user"; text: string }
  | { who: "bot"; res: CoPilotResponse };

const VERDICT: Record<string, { fg: string; bg: string; bd: string }> = {
  "Covered":     { fg: "#0e7c5a", bg: "#e7f4ee", bd: "#bfe3d3" },
  "Not covered": { fg: "#b4322a", bg: "#fbeceb", bd: "#f0cbc7" },
  "Partial":     { fg: "#b7791f", bg: "#fbf3e3", bd: "#eeddb8" },
  "Unclear":     { fg: "#52616b", bg: "#eef1f2", bd: "#d3dadd" },
};

const EXAMPLES = [
  "My AXA windscreen cracked from a stone, comprehensive cover — am I covered?",
  "Zurich policy, is driving in the UK covered?",
  "Can I claim on RSA if a learner driver damaged the car?",
];

export default function Page() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [turns, busy]);

  function history(next: Turn[]): Message[] {
    return next.map((t) =>
      t.who === "user"
        ? { role: "user" as const, content: t.text }
        : { role: "assistant" as const, content: t.res.mode === "clarify"
            ? t.res.questions.join(" ")
            : `${t.res.verdict}. ${t.res.answer ?? ""}` });
  }

  async function send(text: string) {
    const q = text.trim();
    if (!q || busy) return;
    const next: Turn[] = [...turns, { who: "user", text: q }];
    setTurns(next);
    setInput("");
    setBusy(true);
    try {
      const res = await chat(history(next));
      setTurns([...next, { who: "bot", res }]);
    } catch {
      setTurns([...next, { who: "bot", res: {
        mode: "answer", questions: [], verdict: "Unclear",
        answer: "I couldn't reach the policy service. Is the backend running on :8000?",
        citations: [], exclusions_checked: [], confidence: null } }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-5">
      <header className="flex items-baseline justify-between border-b border-[#d3dadd] py-5">
        <h1 className="text-lg font-medium tracking-tight">
          Motor Co-Pilot
        </h1>
        <span className="font-mono text-[11px] uppercase tracking-widest text-[#0e4a44]">
          Irish private motor
        </span>
      </header>

      <div className="transcript flex-1 space-y-6 overflow-y-auto py-8">
        {turns.length === 0 && (
          <div className="pt-10">
            <p className="max-w-md text-[15px] leading-relaxed text-[#3c4a48]">
              Ask about a motor policy. I check the cover <em>and</em> the exclusions before I
              answer — and I'll ask which insurer first, because the carve-outs differ.
            </p>
            <div className="mt-6 space-y-2">
              {EXAMPLES.map((e) => (
                <button key={e} onClick={() => send(e)}
                  className="block w-full rounded-lg border border-[#d3dadd] bg-white/60 px-4 py-2.5 text-left text-sm text-[#3c4a48] transition hover:border-[#0e4a44] hover:text-[#12211f]">
                  {e}
                </button>
              ))}
            </div>
          </div>
        )}

        {turns.map((t, i) =>
          t.who === "user" ? (
            <div key={i} className="flex justify-end">
              <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-[#0e4a44] px-4 py-2.5 text-[15px] text-white">
                {t.text}
              </div>
            </div>
          ) : (
            <BotTurn key={i} res={t.res} />
          )
        )}

        {busy && (
          <div className="font-mono text-[12px] text-[#6b7a78]">reading the policy…</div>
        )}
        <div ref={endRef} />
      </div>

      <div className="sticky bottom-0 bg-[#eef1f1] pb-6 pt-2">
        <div className="flex items-end gap-2 rounded-xl border border-[#cdd6d5] bg-white p-2 focus-within:border-[#0e4a44]">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
            rows={1}
            placeholder="Describe the situation…"
            className="max-h-32 flex-1 resize-none bg-transparent px-2 py-1.5 text-[15px] outline-none placeholder:text-[#9aa7a5]"
          />
          <button onClick={() => send(input)} disabled={busy || !input.trim()}
            className="rounded-lg bg-[#0e4a44] px-4 py-2 text-sm font-medium text-white transition disabled:opacity-40">
            Ask
          </button>
        </div>
      </div>
    </main>
  );
}

function BotTurn({ res }: { res: CoPilotResponse }) {
  if (res.mode === "clarify") {
    return (
      <div className="max-w-[85%]">
        <p className="mb-2 font-mono text-[11px] uppercase tracking-widest text-[#6b7a78]">
          A few details to pin this down
        </p>
        <ul className="space-y-2">
          {res.questions.map((q, i) => (
            <li key={i} className="flex gap-3 rounded-lg border border-[#d3dadd] bg-white px-4 py-3 text-[15px] leading-snug">
              <span className="font-mono text-[13px] text-[#0e4a44]">{i + 1}</span>
              <span>{q}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  const v = (res.verdict && VERDICT[res.verdict]) || VERDICT["Unclear"];
  return (
    <div className="max-w-[85%] space-y-3">
      <div className="flex items-center gap-3">
        <span className="rounded-full border px-3 py-1 text-[13px] font-medium"
          style={{ color: v.fg, background: v.bg, borderColor: v.bd }}>
          {res.verdict ?? "Unclear"}
        </span>
        {res.confidence != null && (
          <span className="font-mono text-[11px] text-[#6b7a78]">
            confidence {Math.round(res.confidence * 100)}%
          </span>
        )}
      </div>

      {res.answer && (
        <p className="whitespace-pre-line text-[15px] leading-relaxed text-[#22302e]">{res.answer}</p>
      )}

      {res.citations.length > 0 && (
        <div className="space-y-1.5 border-l-2 border-[#0e4a44] pl-3">
          {res.citations.map((c, i) => (
            <div key={i} className="text-[13px]">
              <span className="font-mono text-[11px] text-[#0e4a44]">
                {c.insurer} · {c.section}{c.page != null ? ` · p${c.page}` : ""}
              </span>
              <p className="text-[#4a5654]">{c.detail}</p>
            </div>
          ))}
        </div>
      )}

      {res.exclusions_checked.length > 0 && (
        <details className="text-[13px] text-[#6b7a78]">
          <summary className="cursor-pointer font-mono text-[11px] uppercase tracking-widest">
            exclusions checked ({res.exclusions_checked.length})
          </summary>
          <ul className="mt-1 list-disc space-y-0.5 pl-5">
            {res.exclusions_checked.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </details>
      )}
    </div>
  );
}