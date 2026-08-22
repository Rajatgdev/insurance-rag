// Talks to the FastAPI backend. Set NEXT_PUBLIC_API_URL in .env.local / Vercel.
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Role = "user" | "assistant";
export interface Message { role: Role; content: string }

export interface Citation { insurer: string; section: string; page: number | null; detail: string }
export interface HandoffFacts { topic: string; insurers: string[]; circumstances: string }
export interface ReferralNote { to_persona: string; to_name: string; reason: string; facts: HandoffFacts }

export interface ComparisonCell { insurer: string; value: string; section: string | null; page: number | null; is_gap: boolean }
export interface ComparisonRow { dimension: string; cells: ComparisonCell[] }

// One flat answer type covering all persona shapes (fields present per output_kind)
export interface Answer {
  mode: "clarify" | "answer" | "refer";
  questions: string[];
  referral: ReferralNote | null;
  // verdict (Ciara)
  verdict?: "Covered" | "Not covered" | "Partial" | "Unclear" | null;
  answer?: string | null;
  excess?: string | null;
  citations?: Citation[];
  exclusions_checked?: string[];
  confidence?: number | null;
  // wording read (Brian)
  summary?: string | null;
  grants?: string[];
  notable_exclusions?: Citation[];
  warranties_conditions?: Citation[];
  gaps?: string[];
  endorsements_plain?: string[];
  // comparison (Darragh)
  topic?: string | null;
  insurers?: string[];
  rows?: ComparisonRow[];
}

export interface ExaminedClause { insurer: string; section: string | null; page: number | null; is_exclusion: boolean }
export interface AuditRecord {
  persona: string; query: string;
  insurers_examined: string[];
  clauses_examined: ExaminedClause[];
  clauses_examined_count: number;
  clauses_cited_count: number;
  referred_to: string | null;
  timestamp: string;
}

export interface Envelope { persona: string; output_kind: string; answer: Answer; audit: AuditRecord }

export async function chat(
  messages: Message[], persona: string, handoff?: HandoffFacts,
): Promise<Envelope> {
  const res = await fetch(`${API}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, persona, handoff: handoff ?? null }),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}