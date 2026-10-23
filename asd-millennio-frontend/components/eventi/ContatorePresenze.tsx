import { clsx } from "clsx";

export function ContatorePresenze({
  partecipanti,
  postiMax,
  inListaAttesa,
  completo,
  tono = "chiaro",
}: {
  partecipanti: number;
  postiMax: number;
  inListaAttesa: number;
  completo: boolean;
  tono?: "chiaro" | "scuro";
}) {
  const percentuale = Math.min(100, Math.round((partecipanti / postiMax) * 100));
  const scuro = tono === "scuro";
  return (
    <div className="min-w-[9rem]">
      <div className="flex items-baseline justify-between gap-2">
        <span className={clsx("text-xs font-medium", scuro ? "text-white/80" : "text-slate-500")}>Presenze</span>
        <span className={clsx("text-sm font-bold tabular-nums", scuro ? "text-white" : "text-slate-900")}>
          {partecipanti} / {postiMax}
        </span>
      </div>
      <div
        className={clsx("mt-1 h-1.5 w-full overflow-hidden rounded-full", scuro ? "bg-white/25" : "bg-slate-200")}
        role="progressbar"
        aria-valuenow={partecipanti}
        aria-valuemin={0}
        aria-valuemax={postiMax}
        aria-label="Presenze sull'evento"
      >
        <div
          className={clsx("h-full rounded-full", completo ? "bg-amber-400" : scuro ? "bg-white" : "bg-emerald-500")}
          style={{ width: `${percentuale}%` }}
        />
      </div>
      {completo && (
        <p className={clsx("mt-1 text-xs font-semibold", scuro ? "text-amber-200" : "text-amber-700")}>
          Completo · {inListaAttesa} in lista d&apos;attesa
        </p>
      )}
    </div>
  );
}
