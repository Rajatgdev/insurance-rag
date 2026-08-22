export type PersonaId = "ciara" | "brian" | "darragh";

export interface PersonaMeta {
  id: PersonaId;
  name: string;
  role: string;
  lane: string;
  accent: string;       // identity colour — recolours the workbench when active
  accentSoft: string;   // tinted background
  blurb: string;        // what this seat does
}

export const PERSONAS: Record<PersonaId, PersonaMeta> = {
  ciara: {
    id: "ciara", name: "Ciara", role: "Claims assessor", lane: "claim",
    accent: "#3a5cc7", accentSoft: "#eaeefb",
    blurb: "Is a specific claim payable under one policy? Cited coverage verdict.",
  },
  brian: {
    id: "brian", name: "Brian", role: "Underwriter", lane: "wording",
    accent: "#6d4aa8", accentSoft: "#f0ebf9",
    blurb: "A veteran read of one wording — grants, exclusions, gaps.",
  },
  darragh: {
    id: "darragh", name: "Darragh", role: "Broker", lane: "comparison",
    accent: "#0e6b7a", accentSoft: "#e5f2f4",
    blurb: "Compare cover across insurers, with the gaps to raise.",
  },
};

export const PERSONA_ORDER: PersonaId[] = ["ciara", "brian", "darragh"];

export const VERDICT_STYLE: Record<string, { fg: string; bg: string }> = {
  "Covered":     { fg: "var(--covered)",    bg: "var(--covered-bg)" },
  "Not covered": { fg: "var(--notcovered)", bg: "var(--notcovered-bg)" },
  "Partial":     { fg: "var(--partial)",    bg: "var(--partial-bg)" },
  "Unclear":     { fg: "var(--unclear)",    bg: "var(--unclear-bg)" },
};