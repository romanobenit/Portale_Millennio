import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-700 to-blue-900 flex flex-col px-4 text-white">
      {/* Header con login */}
      <header className="flex justify-between items-center py-4 max-w-5xl w-full mx-auto">
        <span className="text-lg font-bold tracking-tight">ASD Millennio</span>
        <Link
          href="/dashboard"
          className="rounded-lg bg-white/20 border border-white/40 px-4 py-2 text-sm font-semibold text-white hover:bg-white/30 transition-colors"
        >
          Accedi
        </Link>
      </header>

      {/* Contenuto centrato */}
      <div className="flex-1 flex items-center justify-center">
        <div className="max-w-2xl text-center space-y-6">
          <h1 className="text-5xl font-bold tracking-tight">ASD Millennio</h1>
          <p className="text-xl text-blue-100">
            Piattaforma digitale per la gestione dell&apos;impianto Palasirion —
            tesseramento, calendario e raccolta fondi NFT.
          </p>
          <div className="flex flex-wrap gap-4 justify-center pt-4">
            <Link
              href="/dashboard"
              className="rounded-lg bg-white px-6 py-3 text-base font-semibold text-blue-800 hover:bg-blue-50 transition-colors"
            >
              Diventa tesserato
            </Link>
            <Link
              href="/dashboard/nft"
              className="rounded-lg border-2 border-white px-6 py-3 text-base font-semibold text-white hover:bg-blue-800 transition-colors"
            >
              Raccolta fondi / NFT Palasirion
            </Link>
            <Link
              href="/dashboard/prenotazioni"
              className="rounded-lg bg-green-500 px-6 py-3 text-base font-semibold text-white hover:bg-green-400 transition-colors"
            >
              Prenota il tuo campo
            </Link>
          </div>
          <p className="text-xs text-blue-200 pt-6">
            I token NFT non sono strumenti finanziari ai sensi della Direttiva MiFID II.
            Rappresentano esclusivamente diritti d&apos;uso del Palasirion.
          </p>
        </div>
      </div>
    </main>
  );
}
