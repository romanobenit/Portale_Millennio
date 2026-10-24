interface Props {
  punti: { data: string; rating: number }[];
  obiettivo?: number | null;
}

/** Linea dell'andamento del punteggio, partita dopo partita (parte da 1200). */
export function AndamentoRating({ punti, obiettivo }: Props) {
  if (punti.length === 0) {
    return <p className="text-xs text-gray-400">Il grafico compare dopo la prima partita confermata.</p>;
  }
  const valori = [1200, ...punti.map((p) => p.rating)];
  const tutti = obiettivo ? [...valori, obiettivo] : valori;
  const min = Math.min(...tutti) - 10;
  const max = Math.max(...tutti) + 10;
  const W = 300;
  const H = 80;
  const x = (i: number) => (valori.length === 1 ? W / 2 : (i / (valori.length - 1)) * W);
  const y = (v: number) => H - ((v - min) / (max - min)) * H;
  const linea = valori.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const ultimo = valori[valori.length - 1];

  return (
    <svg viewBox={`-4 -4 ${W + 8} ${H + 8}`} className="h-20 w-full" role="img"
      aria-label={`Andamento del punteggio: da 1200 a ${Math.round(ultimo)}`}>
      {obiettivo && (
        <>
          <line x1={0} x2={W} y1={y(obiettivo)} y2={y(obiettivo)} stroke="#9ca3af" strokeDasharray="4 4" strokeWidth={1} />
          <text x={W} y={y(obiettivo) - 3} textAnchor="end" fontSize={9} fill="#6b7280">obiettivo {obiettivo}</text>
        </>
      )}
      <path d={linea} fill="none" stroke="#1d4ed8" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={x(valori.length - 1)} cy={y(ultimo)} r={3.5} fill="#1d4ed8" />
    </svg>
  );
}
