import { apiClient } from "./client";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// Ogni voce è uno SLOT DA 1 ORA (ora_inizio–ora_fine), con i campi liberi in quell'ora.
export interface GiornoDisponibile {
  data: string;               // YYYY-MM-DD
  template_id: string;
  giorno_settimana: number;
  ora_inizio: string;         // HH:MM:SS
  ora_fine: string;           // HH:MM:SS
  campi_totali: number;
  campi_disponibili: number;
  costo_ora: number;
  durata_ore: number;         // sempre 1
  importo_totale: number;     // = costo_ora
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

export interface CheckoutCarrelloResponse {
  stripe_checkout_url: string;
  importo_totale: number;
  num_slot: number;
}

// Disponibilità: endpoint pubblico (nessun token).
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

// ─── Carrello (chiamate autenticate via apiClient, con auto-refresh token) ───

export async function aggiungiAlCarrello(
  templateId: string,
  data: string,
  oraInizio: string,
): Promise<PrenotazioneCampo> {
  const res = await apiClient.post<PrenotazioneCampo>("/campi/carrello", {
    template_id: templateId,
    data,
    ora_inizio: oraInizio,
  });
  return res.data;
}

export async function fetchCarrello(): Promise<PrenotazioneCampo[]> {
  const res = await apiClient.get<PrenotazioneCampo[]>("/campi/carrello");
  return res.data;
}

export async function checkoutCarrello(): Promise<CheckoutCarrelloResponse> {
  const res = await apiClient.post<CheckoutCarrelloResponse>("/campi/carrello/checkout", {});
  return res.data;
}

export async function fetchMiePrenotazioni(): Promise<PrenotazioneCampo[]> {
  const res = await apiClient.get<PrenotazioneCampo[]>("/campi/le-mie-prenotazioni");
  return res.data;
}

export async function cancellaPrenotazione(id: string): Promise<void> {
  await apiClient.delete(`/campi/prenota/${id}`);
}
