import Image from "next/image";
import { Section, SectionHeading } from "@/components/site/Section";
import { Reveal } from "@/components/site/Reveal";
import { galleryImages } from "@/lib/site";

/** Vetrina fotografica della community in home. */
export function Gallery() {
  return (
    <Section id="gallery">
      <SectionHeading
        eyebrow="Gallery"
        title="La nostra community"
        subtitle="Tornei, viaggi e allenamenti: i momenti che raccontano la Polisportiva Millennio."
      />
      <ul className="mt-12 grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 lg:grid-cols-4">
        {galleryImages.map((img, i) => (
          <Reveal as="li" key={img.src} delay={(i % 4) * 70}>
            <div className="group relative aspect-square overflow-hidden rounded-xl bg-slate-100">
              <Image
                src={img.src}
                alt={img.alt}
                fill
                sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
                className="object-cover transition-transform duration-500 group-hover:scale-110"
              />
            </div>
          </Reveal>
        ))}
      </ul>
    </Section>
  );
}
