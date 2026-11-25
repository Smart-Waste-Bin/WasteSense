// NotchedHeroCard.tsx
type NotchedHeroCardProps = {
  src: string;
  alt: string;
};

export default function NotchedHeroCard({ src, alt }: NotchedHeroCardProps) {
  return (
    <>
      {/* Hidden SVG that only defines the clip shape. Don't use display:none, it breaks clipPath in some browsers */}
      <svg
        width="0"
        height="0"
        className="absolute"
        aria-hidden="true"
        focusable="false"
      >
        <defs>
          <clipPath id="notched-card" clipPathUnits="objectBoundingBox">
            {/* Path drawn on a 561x657 canvas, scaled to 0–1 (1/561, 1/657) */}
            <path
              transform="scale(0.0017825 0.0015221)"
              d="M138 0 H521 Q561 0 561 40 V515 Q561 555 521 555 H510
                 Q470 555 470 595 V617 Q470 657 430 657 H40
                 Q0 657 0 617 V115 Q0 75 40 75 H58
                 Q98 75 98 35 Q98 0 138 0 Z"
            />
          </clipPath>
        </defs>
      </svg>

      <div className="relative aspect-[561/657] w-full max-w-[561px] [clip-path:url(#notched-card)]">
        <img src={src} alt={alt} className="h-full w-full object-cover" />

        {/* Optional gradient so the text stays readable */}
        <div className="absolute inset-x-0 top-0 h-1/4 bg-gradient-to-b from-black/30 to-transparent" />
      </div>
    </>
  );
}
