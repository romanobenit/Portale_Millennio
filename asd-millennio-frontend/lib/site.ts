/**
 * Configurazione centrale del sito pubblico (single source of truth).
 * Contenuti reali confermati: nome, sede (Cercola), impianto (Palasirio), social.
 * I campi marcati [DA FORNIRE] vanno completati con i dati ufficiali dell'associazione.
 */

export interface NavItem {
  href: string;
  label: string;
}

export const siteConfig = {
  name: "ASD Millennio",
  legalName: "Millennio — Associazione Polisportiva Dilettantistica",
  shortName: "Millennio",
  founded: 2009,
  // URL pubblico del portale (override con NEXT_PUBLIC_APP_URL in build).
  url: process.env.NEXT_PUBLIC_APP_URL || "https://millennioasd.com",
  description:
    "Polisportiva dilettantistica a Cercola dal 2009. Volley, badminton, kung fu, pickleball e tanto sport per tutte le età, presso l'impianto Palasirio.",
  city: "Cercola (NA)",
  venue: "Palasirio",

  /** Recapiti ufficiali. */
  contact: {
    email: "millennioasd@gmail.com" as string,
    phone: "347 633 6545" as string,
    address: "Viale dei Fiori 3, 80040 Cercola (NA)" as string,
    mapsQuery: "Viale dei Fiori 3, 80040 Cercola NA",
  },

  /** Social ufficiali (verificati). */
  social: {
    facebook: "https://www.facebook.com/Millennioasd",
    instagram: "https://www.instagram.com/millennioasd2009/",
    tiktok: "https://www.tiktok.com/@domenicoromano153",
  },
} as const;

/** Navigazione principale (header). Le pagine interne vengono aggiunte negli step successivi. */
export const mainNav: NavItem[] = [
  { href: "/", label: "Home" },
  { href: "/chi-siamo", label: "Chi siamo" },
  { href: "/attivita", label: "Attività" },
  { href: "/corsi", label: "Corsi" },
  { href: "/eventi", label: "Eventi" },
  { href: "/news", label: "News" },
  { href: "/contatti", label: "Contatti" },
];

/** Link verso le aree del portale (riservate / funzionali, già esistenti). */
export const portalLinks = {
  areaSoci: "/dashboard",
  tesseramento: "/dashboard",
  prenotaCampo: "/dashboard/prenotazioni",
  raccoltaFondi: "/dashboard/nft",
} as const;

/**
 * Discipline sportive (confermate da contesto progetto + ricerca).
 * Le descrizioni sono generiche e vanno riviste/confermate dall'associazione,
 * insieme a orari, istruttori e foto [DA FORNIRE].
 */
export interface Disciplina {
  slug: string;
  nome: string;
  emoji: string;
  tag: string;
  /** Descrizione breve (card). */
  descr: string;
  /** Descrizione estesa (pagina di dettaglio). */
  lungo: string;
  /** Foto rappresentativa (in /public/images). Assente = mostra solo l'icona. */
  img?: string;
}

export const discipline: Disciplina[] = [
  {
    slug: "badminton",
    nome: "Badminton",
    emoji: "🏸",
    tag: "Sport con la racchetta",
    descr: "Velocità e tecnica: corsi per principianti e appassionati.",
    lungo:
      "Il cuore storico della Polisportiva: Millennio è un punto di riferimento per la Federazione Italiana Badminton (FIBa) in Campania. Proponiamo corsi per tutte le età e tutti i livelli — dai primi palleggi all'agonismo — con eventi e progetti nelle scuole come la Baddy Cup e il Trofeo Vesuvio.",
    img: "/images/5.jpeg",
  },
  {
    slug: "kung-fu",
    nome: "Kung Fu",
    emoji: "🥋",
    tag: "Arte marziale",
    descr: "Arte marziale per disciplina, equilibrio e difesa personale.",
    lungo:
      "Il settore arti marziali con il Wushu-Kung Fu: un percorso di disciplina, coordinazione ed equilibrio, pensato per la crescita personale oltre che fisica, adatto a bambini, ragazzi e adulti.",
    img: "/images/8.jpeg",
  },
  {
    slug: "volley",
    nome: "Volley",
    emoji: "🏐",
    tag: "Sport di squadra",
    descr: "Allenamenti e partite per tutti i livelli, dai più piccoli agli adulti.",
    lungo:
      "Il nostro settore più giovane: la pallavolo per diffondere lo sport di squadra sul territorio cercolese. Allenamenti per imparare i fondamentali, fare squadra e divertirsi insieme.",
    img: "/images/4.jpeg",
  },
  {
    slug: "pickleball",
    nome: "Pickleball",
    emoji: "🎾",
    tag: "Sport con la racchetta",
    descr: "Lo sport con la racchetta in più rapida crescita: facile e divertente.",
    lungo:
      "Lo sport con la racchetta in più rapida crescita al mondo: regole semplici, scambi divertenti e adatto davvero a tutti. Perfetto per iniziare a qualsiasi età e mantenersi in movimento.",
  },
];

/** Cerca una disciplina per slug (usato dalle pagine di dettaglio). */
export function getDisciplina(slug: string): Disciplina | undefined {
  return discipline.find((d) => d.slug === slug);
}

/** Punti di forza ("Perché sceglierci"). Testi generici da confermare. */
export const valori = [
  { titolo: "Per tutte le età", descr: "Programmi pensati per bambini, ragazzi e adulti." },
  { titolo: "Istruttori qualificati", descr: "Tecnici preparati che seguono ogni atleta." },
  { titolo: "Impianto Palasirio", descr: "Spazi attrezzati nel cuore di Cercola." },
  { titolo: "Una comunità dal 2009", descr: "Una grande famiglia sportiva da oltre 15 anni." },
] as const;

// ─── Pagina "Chi siamo" — contenuti ufficiali forniti dall'associazione ──────

/** Storia: paragrafi introduttivi. */
export const storiaIntro = [
  "La Polisportiva Millennio è un punto di riferimento storico per la Federazione Italiana Badminton (FIBa) in Campania: negli anni è diventata un pilastro per lo sviluppo di questo sport nella regione, collaborando con le scuole del territorio per dare vita a progetti di rete sociali e inclusivi — come la Baddy Cup e il periodico Trofeo Vesuvio — e promuovendo il badminton anche attraverso viaggi sportivi nelle maggiori capitali europee.",
  "Millennio ha inoltre promosso le arti marziali con il Wushu-Kung Fu e, da tempi recentissimi, ha dato il via al settore della pallavolo per diffondere questo sport di squadra sul territorio cercolese.",
];

/** Tappe della storia (timeline). Solo il 2009 ha una data certa; le altre sono fasi. */
export interface TappaStoria {
  label: string;
  titolo: string;
  descr: string;
}
export const storiaTappe: TappaStoria[] = [
  { label: "2009", titolo: "La nascita", descr: "Fondazione della Polisportiva Millennio a Cercola." },
  { label: "Badminton", titolo: "Punto di riferimento FIBa in Campania", descr: "Lo sviluppo del badminton nella regione e i progetti di rete con le scuole: la Baddy Cup e il Trofeo Vesuvio." },
  { label: "Oltre i confini", titolo: "Viaggi sportivi in Europa", descr: "La promozione del badminton attraverso trasferte nelle maggiori capitali europee." },
  { label: "Arti marziali", titolo: "Wushu-Kung Fu", descr: "L'avvio del settore arti marziali, tra disciplina, equilibrio e crescita personale." },
  { label: "Oggi", titolo: "Nasce il settore pallavolo", descr: "Da tempi recentissimi, la pallavolo per diffondere lo sport di squadra sul territorio cercolese." },
];

/** Visione: intro, tre pilastri e claim conclusivo. */
export const visioneIntro =
  "La Polisportiva Millennio di Cercola immagina un territorio dove lo sport è un diritto accessibile a tutti, senza barriere o limiti.";

export const visionePilastri = [
  { titolo: "Libertà di scelta", descr: "Un palinsesto di attività ampio e diversificato, perché ogni ragazzo possa assecondare le proprie inclinazioni naturali." },
  { titolo: "Inclusione totale", descr: "Abbattiamo ogni ostacolo per chi ha difficoltà e valorizziamo gli sport individuali, accogliendo anche chi non si ritrova nei giochi di squadra." },
  { titolo: "Ambiente familiare", descr: "Benessere e divertimento in un clima sereno, dove l'agonismo non è mai un obbligo." },
] as const;

export const visioneTagline =
  "Crediamo in uno sport che unisce: mettiamo al centro il divertimento e lo stare insieme in modo armonioso, uno spazio inclusivo dove la gioia del gioco e il rispetto reciproco guidano la crescita di ogni atleta, dentro e fuori dal campo.";

// ─── Eventi ──────────────────────────────────────────────────────────────────

export interface Evento {
  titolo: string;
  tag: string;
  ricorrenza: string;
  descr: string;
}

/** Eventi storici dell'associazione (date da confermare → mostrate come ricorrenze). */
export const eventi: Evento[] = [
  {
    titolo: "Baddy Cup",
    tag: "Badminton · Scuole",
    ricorrenza: "Progetto di rete",
    descr:
      "Il torneo di badminton nato dai progetti di rete con le scuole del territorio: sport, inclusione e socialità per i più giovani.",
  },
  {
    titolo: "Trofeo Vesuvio",
    tag: "Badminton · Torneo",
    ricorrenza: "Appuntamento periodico",
    descr:
      "Il torneo periodico che riunisce atleti e appassionati di badminton: una tradizione per la Polisportiva Millennio.",
  },
  {
    titolo: "Viaggi sportivi in Europa",
    tag: "Trasferte",
    ricorrenza: "Iniziativa ricorrente",
    descr:
      "Trasferte nelle maggiori capitali europee per promuovere il badminton e vivere lo sport oltre i confini.",
  },
];

// ─── Corsi ───────────────────────────────────────────────────────────────────

/** Passi per iscriversi (processo generico, da confermare). */
export const comeIscriversi = [
  { titolo: "Scegli la disciplina", descr: "Sfoglia le attività e individua lo sport più adatto a te." },
  { titolo: "Vieni a provare", descr: "Contattaci per fissare una prova e conoscere i nostri tecnici." },
  { titolo: "Tessera e si parte", descr: "Completa il tesseramento e inizia ad allenarti al Palasirio." },
];

// ─── News ────────────────────────────────────────────────────────────────────

export interface NewsItem {
  slug: string;
  titolo: string;
  data: string; // ISO
  estratto: string;
}

/** Notizie/comunicazioni. Vuoto finché non vengono forniti contenuti. */
export const news: NewsItem[] = [];

// ─── Gallery ─────────────────────────────────────────────────────────────────

export interface GalleryImage {
  src: string;
  alt: string;
}

/** Foto vetrina della community (in /public/images). */
export const galleryImages: GalleryImage[] = [
  { src: "/images/6.jpeg", alt: "Studenti e atleti durante un evento di badminton nelle scuole" },
  { src: "/images/2.jpeg", alt: "Giovani atleti Millennio durante un viaggio sportivo in Europa" },
  { src: "/images/8.jpeg", alt: "Bambini del corso di Kung Fu con i maestri e i diplomi" },
  { src: "/images/7.jpeg", alt: "Squadra di pallavolo Millennio in cerchio prima della partita" },
  { src: "/images/5.jpeg", alt: "Partecipanti alla Baddy Cup di badminton in palestra" },
  { src: "/images/3.jpeg", alt: "Giovani atleti Millennio in maglia sociale su un campo all'aperto" },
  { src: "/images/4.jpeg", alt: "Giovani atlete del settore pallavolo Millennio a un torneo" },
  { src: "/images/9.jpeg", alt: "Squadra di pallavolo Millennio dopo una partita" },
];
