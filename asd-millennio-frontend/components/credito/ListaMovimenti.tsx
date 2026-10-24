import { clsx } from "clsx";
import { ETICHETTA_MOVIMENTO, formattaEuro, type MovimentoCredito } from "@/lib/api/credito";

export function ListaMovimenti({ movimenti }: { movimenti: MovimentoCredito[] }) {
  if (movimenti.length === 0) {
    return <p className="py-6 text-center text-sm text-gray-500">Nessun movimento.</p>;
  }
  return (
    <ul className="divide-y divide-gray-100">
      {movimenti.map((m) => {
        const importo = Number(m.importo_eur);
        return (
          <li key={m.id} className="flex items-start justify-between gap-3 py-3">
            <div className="min-w-0 text-sm">
              <p className="font-medium text-gray-900">{ETICHETTA_MOVIMENTO[m.tipo] ?? m.tipo}</p>
              {m.causale && <p className="text-xs text-gray-600">{m.causale}</p>}
              <p className="text-xs text-gray-400">
                {new Date(m.created_at).toLocaleString("it-IT", { dateStyle: "medium", timeStyle: "short" })}
              </p>
            </div>
            <div className="shrink-0 text-right">
              <p className={clsx("text-sm font-semibold tabular-nums", importo >= 0 ? "text-green-700" : "text-red-700")}>
                {formattaEuro(importo, true)}
              </p>
              <p className="text-xs tabular-nums text-gray-400">saldo {formattaEuro(m.saldo_dopo_eur)}</p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
