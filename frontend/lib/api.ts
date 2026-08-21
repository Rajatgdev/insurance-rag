// Talks to the FastAPI backend. Set NEXT_PUBLIC_API_URL in .env.local / Vercel.
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Role = "user" | "assistant";
export interface Message { role: Role; content: string }

export interface Citation { insurer: string; section: string; page: number | null; detail: string }
export interface CoPilotResponse {
  mode: "clarify" | "answer";
  questions: string[];
  verdict: "Covered" | "Not covered" | "Partial" | "Unclear" | null;
  answer: string | null;
  citations: Citation[];
  exclusions_checked: string[];
  confidence: number | null;
}

export async function chat(messages: Message[], persona = "generic"): Promise<CoPilotResponse> {
  const res = await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, persona }),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}