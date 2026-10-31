import { clsx } from "clsx";
import type { RigaClassifica } from "@/lib/api/pickleball";

interface Props {
  righe: RigaClassifica[];
  evidenzia?: string; // socio_id
}

export function TabellaClassifica({ righe, evidenzia }: Props) {
  if (righe.length === 0) {
    return <p className="py-6 text-center text-sm text-gray-500">Nessuna partita confermata per ora.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-xs uppercase tracking-wide text-gray-500">
            <th className="py-2 pr-2">#</th>
            <th className="py-2 pr-2">Giocatore</th>
            <th className="py-2 pr-2 text-right">Punti</th>
            <th className="py-2 pr-2 text-right">V / P</th>
            <th className="hidden py-2 pr-2 text-right sm:table-cell">Massimo</th>
            <th className="hidden py-2 text-right sm:table-cell">DUPR</th>
          </tr>
        </thead>
        <tbody>
          {righe.map((r) => (
            <tr
              key={r.socio_id}
              className={clsx("border-b border-gray-100", r.socio_id === evidenzia && "bg-blue-50 font-semibold")}
            >
              <td className="py-2 pr-2 text-gray-500">{r.posizione}</td>
              <td className="py-2 pr-2">
                {r.nome}
                {r.inattivo && (
                  <span className="ml-1.5 rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700"
                    title="Nessuna partita negli ultimi mesi: non compare nella classifica dei soci">
                    inattivo
                  </span>
                )}
                {r.provvisorio && (
                  <span className="ml-1.5 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-500"
                    title="Meno di 10 partite: il punteggio si sta ancora assestando">
                    provvisorio
                  </span>
                )}
              </td>
              <td className="py-2 pr-2 text-right tabular-nums">{Math.round(r.rating)}</td>
              <td className="py-2 pr-2 text-right tabular-nums">
                {r.vittorie} / {r.partite - r.vittorie}
              </td>
              <td className="hidden py-2 pr-2 text-right tabular-nums text-gray-500 sm:table-cell">
                {Math.round(r.rating_max)}
              </td>
              <td className="hidden py-2 text-right tabular-nums text-gray-500 sm:table-cell">
                {r.dupr !== null ? r.dupr.toFixed(2) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
