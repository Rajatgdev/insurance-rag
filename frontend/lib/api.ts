// Calls the FastAPI backend. Set NEXT_PUBLIC_API_URL in Vercel / .env.local
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function askPersona(persona: string, message: string) {
  const res = await fetch(`${API}/persona/${persona}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
