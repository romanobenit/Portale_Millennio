const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export interface GiornoDisponibile {
  data: string;               // YYYY-MM-DD
  template_id: string;
  giorno_settimana: number;
  ora_inizio: string;         // HH:MM:SS
  ora_fine: string;
  campi_totali: number;
  campi_disponibili: number;
  costo_ora: number;
  durata_ore: number;
  importo_totale: number;
  sport: string[];
}

export interface PrenotazioneCampo {
  id: string;
  socio_id: string;
  template_id: string;
  data: string;
  ora_inizio: string;
  ora_fine: string;
  campo: number;
  importo_eur: number;
  stato: "bloccata" | "confermata" | "cancellata" | "scaduta";
  stripe_session_id: string | null;
  bloccata_fino_a: string | null;
  cancellabile_fino_a: string | null;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface CheckoutCampoResponse {
  prenotazione_id: string;
  stripe_checkout_url: string;
  campo: number;
  importo_eur: number;
  bloccata_fino_a: string;
}

async function authFetch(url: string, token: string, init: RequestInit = {}): Promise<Response> {
  return fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init.headers ?? {}),
    },
  });
}

export async function fetchDisponibilita(
  dataInizio: string,
  dataFine: string,
): Promise<GiornoDisponibile[]> {
  const res = await fetch(
    `${API}/campi/disponibilita?data_inizio=${dataInizio}&data_fine=${dataFine}`,
  );
  if (!res.ok) throw new Error("Impossibile caricare le disponibilità");
  return res.json();
}

export async function prenota(
  token: string,
  templateId: string,
  data: string,
): Promise<CheckoutCampoResponse> {
  const res = await authFetch(`${API}/campi/prenota`, token, {
    method: "POST",
    body: JSON.stringify({ template_id: templateId, data }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message ?? "Errore nella prenotazione");
  }
  return res.json();
}

export async function fetchMiePrenotazioni(token: string): Promise<PrenotazioneCampo[]> {
  const res = await authFetch(`${API}/campi/le-mie-prenotazioni`, token);
  if (!res.ok) throw new Error("Impossibile caricare le prenotazioni");
  return res.json();
}

export async function cancellaPrenotazione(token: string, id: string): Promise<void> {
  const res = await authFetch(`${API}/campi/prenota/${id}`, token, { method: "DELETE" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.message ?? "Errore nella cancellazione");
  }
}
