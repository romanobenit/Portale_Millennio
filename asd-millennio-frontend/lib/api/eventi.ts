import { apiClient } from "./client";

export type Modalita = "online" | "in_sede";

export interface EventoPubblico {
  id: string;
  titolo: string | null;
  sport: string[];
  data: string; // YYYY-MM-DD
  ora_inizio: string; // HH:MM:SS
  ora_fine: string;
  prezzo_eur: string; // Decimal serializzato come stringa
  posti_max: number;
  partecipanti: number;
  posti_liberi: number;
  in_lista_attesa: number;
  completo: boolean;
  stato: "programmato" | "annullato";
}

export interface PrenotazioneEvento {
  id: string;
  evento_id: string;
  modalita: Modalita;
  stato: "in_attesa_pagamento" | "confermata" | "annullata" | "scaduta" | "rimborsata";
  importo_eur: string;
  pagato_in_sede: boolean;
  pagato_con_credito: boolean;
  presenza: "presente" | "assente" | null;
  created_at: string;
}

export interface MiaPrenotazione extends PrenotazioneEvento {
  evento: EventoPubblico;
  annullabile: boolean;
}

export interface MieiEventi {
  prenotazioni: MiaPrenotazione[];
  lista_attesa: string[];
  assenze: number;
  solo_online: boolean;
  abilitato_fino_al: string | null; // null = non abilitato ai campi
  saldo_credito_eur: string; // credito interno disponibile
}

export interface EventoDirigenza extends EventoPubblico {
  presenze_manuali: number;
  confermati_online: number;
  confermati_in_sede: number;
  note: string | null;
}

export interface Partecipante {
  prenotazione_id: string;
  socio_id: string;
  nome: string;
  cognome: string;
  modalita: Modalita;
  stato: PrenotazioneEvento["stato"];
  importo_eur: string;
  pagato_in_sede: boolean;
  presenza: "presente" | "assente" | null;
  inserita_da_staff: boolean;
  assenze: number;
  solo_online: boolean;
}

export interface InAttesa {
  socio_id: string;
  nome: string;
  cognome: string;
  iscritto_at: string;
  notificato_at: string | null;
}

export interface EventoDettaglio {
  evento: EventoDirigenza;
  partecipanti: Partecipante[];
  lista_attesa: InAttesa[];
}

export interface SocioRicerca {
  id: string;
  nome: string;
  cognome: string;
  codice_fiscale: string;
  abilitato_fino_al: string | null;
  assenze: number;
  solo_online: boolean;
}

export interface EventoInput {
  titolo?: string | null;
  sport: string[];
  data: string;
  ora_inizio: string;
  ora_fine: string;
  prezzo_eur: number;
  posti_max: number;
  note?: string | null;
}

// ── pubblico (nessun token: usabile anche dalle pagine del sito) ─────────────

export async function fetchProssimiEventi(): Promise<EventoPubblico[]> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/eventi`, { cache: "no-store" });
  if (!res.ok) throw new Error("Impossibile caricare gli eventi");
  return res.json();
}

// ── socio ────────────────────────────────────────────────────────────────────

export async function fetchMieiEventi(): Promise<MieiEventi> {
  const { data } = await apiClient.get<MieiEventi>("/eventi/mie");
  return data;
}

export async function prenotaEvento(
  eventoId: string,
  modalita: Modalita,
  usaCredito = false,
): Promise<{ prenotazione: PrenotazioneEvento; stripe_checkout_url: string | null }> {
  const { data } = await apiClient.post(`/eventi/${eventoId}/prenota`, { modalita, usa_credito: usaCredito });
  return data;
}

/** rimborso: per gli ingressi pagati con carta, sulla carta o in credito interno. */
export async function annullaPrenotazioneEvento(
  prenotazioneId: string,
  rimborso: "carta" | "credito" = "carta",
): Promise<PrenotazioneEvento> {
  const { data } = await apiClient.post<PrenotazioneEvento>(`/eventi/prenotazioni/${prenotazioneId}/annulla`, {
    rimborso,
  });
  return data;
}

export async function iscriviListaAttesa(eventoId: string): Promise<void> {
  await apiClient.post(`/eventi/${eventoId}/lista-attesa`);
}

export async function esciListaAttesa(eventoId: string): Promise<void> {
  await apiClient.delete(`/eventi/${eventoId}/lista-attesa`);
}

// ── dirigenza / staff ────────────────────────────────────────────────────────

export async function fetchEventiDirigenza(dataInizio: string, dataFine: string): Promise<EventoDirigenza[]> {
  const { data } = await apiClient.get<EventoDirigenza[]>("/dirigenza/eventi", {
    params: { data_inizio: dataInizio, data_fine: dataFine },
  });
  return data;
}

export async function fetchEventoDettaglio(eventoId: string): Promise<EventoDettaglio> {
  const { data } = await apiClient.get<EventoDettaglio>(`/dirigenza/eventi/${eventoId}`);
  return data;
}

export async function creaEvento(input: EventoInput): Promise<EventoDirigenza> {
  const { data } = await apiClient.post<EventoDirigenza>("/dirigenza/eventi", input);
  return data;
}

export async function aggiornaEvento(eventoId: string, input: Partial<EventoInput>): Promise<EventoDirigenza> {
  const { data } = await apiClient.put<EventoDirigenza>(`/dirigenza/eventi/${eventoId}`, input);
  return data;
}

export async function annullaEvento(eventoId: string): Promise<EventoDirigenza> {
  const { data } = await apiClient.post<EventoDirigenza>(`/dirigenza/eventi/${eventoId}/annulla`);
  return data;
}

export async function impostaPresenzeManuali(eventoId: string, valore: number): Promise<EventoDirigenza> {
  const { data } = await apiClient.put<EventoDirigenza>(`/dirigenza/eventi/${eventoId}/presenze-manuali`, {
    presenze_manuali: valore,
  });
  return data;
}

export async function aggiungiPartecipante(eventoId: string, socioId: string): Promise<void> {
  await apiClient.post(`/dirigenza/eventi/${eventoId}/partecipanti`, { socio_id: socioId });
}

export async function segnaPrenotazione(
  prenotazioneId: string,
  patch: { presenza?: "presente" | "assente" | null; pagato_in_sede?: boolean },
): Promise<PrenotazioneEvento> {
  const { data } = await apiClient.patch<PrenotazioneEvento>(`/dirigenza/eventi/prenotazioni/${prenotazioneId}`, patch);
  return data;
}

export async function cercaSoci(q: string): Promise<SocioRicerca[]> {
  const { data } = await apiClient.get<SocioRicerca[]>("/dirigenza/eventi/soci", { params: { q } });
  return data;
}

export async function azzeraAssenze(socioId: string): Promise<void> {
  await apiClient.post(`/dirigenza/eventi/soci/${socioId}/azzera-assenze`);
}

// ── formattazione condivisa ──────────────────────────────────────────────────

const SPORT_LABEL: Record<string, string> = {
  pickleball: "Pickleball",
  badminton: "Badminton",
  volley: "Pallavolo",
  kung_fu: "Kung Fu",
};

export function etichettaSport(sport: string[]): string {
  return sport.map((s) => SPORT_LABEL[s] ?? s).join(" / ");
}

export function formattaDataEvento(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("it-IT", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

export function formattaOra(hhmmss: string): string {
  return hhmmss.slice(0, 5);
}

export function formattaPrezzo(eur: string | number): string {
  const n = Number(eur);
  return n === 0 ? "Gratis" : `€${n.toFixed(2).replace(".", ",")}`;
}

export function formattaData(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("it-IT");
}

/** Motivo per cui non si può prenotare l'evento del giorno `dataEvento` (null = si può). */
export function motivoNonPrenotabile(abilitatoFinoAl: string | null, dataEvento: string): string | null {
  if (!abilitatoFinoAl) {
    return "Per prenotare serve la tessera Millennio oppure l'iscrizione community con la tessera di un'altra ASD.";
  }
  if (dataEvento > abilitatoFinoAl) {
    return `La tessera vale fino al ${formattaData(abilitatoFinoAl)}: per questo evento va rinnovata o aggiornata.`;
  }
  return null;
}
