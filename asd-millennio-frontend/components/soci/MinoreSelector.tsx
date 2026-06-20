"use client";

import type { Socio } from "@/lib/api/soci";

interface MinoreSelectorProps {
  minori: Socio[];
  acquistaPerMinore: boolean;
  minoreSelezionato: string | null;
  onToggle: (val: boolean) => void;
  onSeleziona: (minoreId: string | null) => void;
}

export function MinoreSelector({
  minori,
  acquistaPerMinore,
  minoreSelezionato,
  onToggle,
  onSeleziona,
}: MinoreSelectorProps) {
  if (minori.length === 0) return null;

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 space-y-3">
      <label className="flex items-start gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={acquistaPerMinore}
          onChange={(e) => {
            onToggle(e.target.checked);
            if (!e.target.checked) onSeleziona(null);
          }}
          className="mt-0.5 h-4 w-4 rounded border-gray-300"
        />
        <span className="text-sm font-medium text-amber-900">
          Acquisto per conto di un minorenne
        </span>
      </label>

      {acquistaPerMinore && (
        <div>
          <label className="block text-xs font-medium text-amber-800 mb-1">
            Seleziona il minorenne
          </label>
          <select
            value={minoreSelezionato ?? ""}
            onChange={(e) => onSeleziona(e.target.value || null)}
            className="w-full rounded-lg border border-amber-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
          >
            <option value="">— Seleziona —</option>
            {minori.map((m) => (
              <option key={m.id} value={m.id}>
                {m.cognome} {m.nome}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-amber-700">
            Come tutore legale, stai acquistando il diritto d&apos;uso per conto del minorenne selezionato.
          </p>
        </div>
      )}
    </div>
  );
}
