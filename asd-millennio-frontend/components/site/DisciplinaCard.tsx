import Image from "next/image";
import Link from "next/link";
import type { Disciplina } from "@/lib/site";

/** Card disciplina, riutilizzata in home e nella pagina Attività. */
export function DisciplinaCard({ d }: { d: Disciplina }) {
  return (
    <Link
      href={`/attivita/${d.slug}`}
      className="group flex h-full flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition-all hover:-translate-y-1 hover:border-brand-200 hover:shadow-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-600"
    >
      {d.img ? (
        <div className="relative aspect-[4/3] overflow-hidden bg-slate-100">
          <Image
            src={d.img}
            alt=""
            fill
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
            className="object-cover transition-transform duration-300 group-hover:scale-105"
            style={d.imgPosizione ? { objectPosition: d.imgPosizione } : undefined}
          />
          <span
            className="absolute left-3 top-3 flex h-9 w-9 items-center justify-center rounded-lg bg-white/90 text-xl shadow-sm"
            aria-hidden="true"
          >
            {d.emoji}
          </span>
        </div>
      ) : (
        <div className="flex aspect-[4/3] items-center justify-center bg-brand-50 text-5xl" aria-hidden="true">
          {d.emoji}
        </div>
      )}

      <div className="flex flex-1 flex-col p-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-brand-600">{d.tag}</p>
        <h3 className="mt-1 font-display text-xl font-bold text-slate-900">{d.nome}</h3>
        <p className="mt-2 flex-1 text-slate-600">{d.descr}</p>
        <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-brand-600">
          Scopri di più
          <span className="transition-transform group-hover:translate-x-1" aria-hidden="true">
            →
          </span>
        </span>
      </div>
    </Link>
  );
}
