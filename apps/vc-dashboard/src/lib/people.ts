export type PersonProject = { id: string; title: string | null; relationship: string; completed: boolean };

export type Person = { 
  id: string; 
  name: string; 
  firstName: string | null; 
  lastName: string | null; 
  avatarUrl: string | null; 
  tagline: string | null; 
  university: string | null; 
  fieldOfStudy: string | null; 
  professionalSituation: string | null; 
  country: string | null; 
  city: string | null; 
  projects: PersonProject[] 
};

export interface HistoricalScore {
  timestamp: string;
  score: number;
}

export interface DetailedPerson extends Person {
  academicDegree: string | null;
  graduationYear: string | null;
  nationality: string | null;
  githubUrl: string | null;
  linkedinUrl: string | null;
  careerOpportunities: string | null;
  passionHobby: string | null;
  activeFounderScore: number | null;
}

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export async function searchPeople(query: string, signal?: AbortSignal): Promise<Person[]> { 
  const response = await fetch(`${apiBase}/people/search?q=${encodeURIComponent(query)}`, { signal, headers: { Accept: "application/json" } }); 
  if (!response.ok) throw new Error("People directory could not be loaded."); 
  return (await response.json() as { people: Person[] }).people; 
}

export async function fetchPersonProfile(userId: string, signal?: AbortSignal): Promise<DetailedPerson> {
  const response = await fetch(`${apiBase}/people/${encodeURIComponent(userId)}`, { signal, headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("Person profile could not be loaded.");
  return await response.json() as DetailedPerson;
}

export async function fetchPersonScores(userId: string, signal?: AbortSignal): Promise<HistoricalScore[]> {
  const response = await fetch(`${apiBase}/people/${encodeURIComponent(userId)}/scores`, { signal, headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("Person scores history could not be loaded.");
  return await response.json() as HistoricalScore[];
}

export async function fetchPersonNetwork(userId: string, signal?: AbortSignal): Promise<{ nodes: any[]; links: any[] }> {
  const response = await fetch(`${apiBase}/people/${encodeURIComponent(userId)}/network`, { signal, headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("Person network graph could not be loaded.");
  const data = await response.json();
  return {
    nodes: data.nodes || [],
    links: data.links || data.edges || []
  };
}
