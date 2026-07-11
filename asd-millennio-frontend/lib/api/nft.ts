import { apiClient } from "./client";

export interface AcquistoNFTResponse {
  id: string;
  stripe_session_id: string;
  stripe_checkout_url: string;
  importo_eur: number;
  slot_count: number;
}

export interface DashboardFundraising {
  totale_raccolto_eur: number;
  obiettivo_eur: number;
  percentuale: number;
  nft_emessi_totali: number;
  nft_per_fascia: Record<string, number>;
}

export async function avviaAcquistoNFT(payload: {
  selezione: { slot_id: string; ore: number[] }[];
  acquisto_per_minore?: boolean;
  minore_id?: string;
}): Promise<AcquistoNFTResponse> {
  const { data } = await apiClient.post<AcquistoNFTResponse>("/nft/acquisto", payload);
  return data;
}

export async function fetchDashboardFundraising(): Promise<DashboardFundraising> {
  const { data } = await apiClient.get<DashboardFundraising>("/nft/dashboard");
  return data;
}

export async function verificaAccesso(tokenId: number, slotKey: string) {
  const { data } = await apiClient.get("/nft/verify", {
    params: { token_id: tokenId, slot_key: slotKey },
  });
  return data;
}

export interface MioNFT {
  id: string;
  token_id: number | null;
  contract_address: string | null;
  mint_tx_hash: string | null;
  ipfs_uri: string | null;
  importo_eur: number;
  ore_totali: number;
  stato: string;
  data_primo_slot: string | null;
  polygonscan_url: string | null;
  certificato_disponibile: boolean;
  created_at: string;
}

export async function fetchMieiNFT(): Promise<MioNFT[]> {
  const { data } = await apiClient.get<MioNFT[]>("/nft/le-mie");
  return data;
}

// Scarica il certificato PDF: l'endpoint richiede il Bearer token, quindi non si può
// usare un semplice <a href>. Si recupera come blob e si forza il download.
export async function scaricaCertificato(id: string): Promise<void> {
  const res = await apiClient.get(`/nft/${id}/certificato`, { responseType: "blob" });
  const url = window.URL.createObjectURL(res.data as Blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `certificato-palasirio-${id}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
