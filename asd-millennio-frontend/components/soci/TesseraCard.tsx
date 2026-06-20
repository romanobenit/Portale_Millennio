"use client";

import type { Tessera } from "@/lib/api/soci";
import { Badge } from "@/components/ui/Badge";
import { format } from "date-fns";
import { it } from "date-fns/locale";

interface TesseraCardProps {
  tessera: Tessera;
}

const STATO_BADGE: Record<string, "green" | "orange" | "gray" | "red" | "blue"> = {
  attiva: "green",
  in_attesa_pagamento: "orange",
  bozza: "gray",
  scaduta: "red",
  sospesa: "red",
};

const SPORT_LABEL: Record<string, string> = {
  volley: "Pallavolo",
  badminton: "Badminton",
  kung_fu: "Kung Fu",
  pickleball: "Pickleball",
};

export function TesseraCard({ tessera }: TesseraCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="font-mono text-sm text-gray-500">{tessera.numero_tessera}</div>
          <div className="font-semibold text-gray-900 text-lg mt-0.5">
            {SPORT_LABEL[tessera.sport] ?? tessera.sport}
          </div>
        </div>
        <Badge variant={STATO_BADGE[tessera.stato] ?? "gray"}>
          {tessera.stato.replace(/_/g, " ")}
        </Badge>
      </div>

      {tessera.data_scadenza && (
        <div className="text-sm text-gray-600">
          Scade il{" "}
          <span className="font-medium">
            {format(new Date(tessera.data_scadenza), "d MMMM yyyy", { locale: it })}
          </span>
        </div>
      )}

      {tessera.anno_sportivo && (
        <div className="text-xs text-gray-400 mt-1">Anno sportivo {tessera.anno_sportivo}</div>
      )}

      {tessera.pdf_url && (
        <a
          href={tessera.pdf_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 inline-block text-sm text-blue-700 hover:underline"
        >
          Scarica tessera PDF
        </a>
      )}
    </div>
  );
}
