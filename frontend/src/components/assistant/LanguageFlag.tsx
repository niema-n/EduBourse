/**
 * Circular flag badges drawn as inline SVG.
 *
 * Deliberately not <img> tags: the brief forbids downloading external flag
 * assets, so every shape here is vector geometry rendered by the browser with
 * no network request.
 */

type FlagProps = { title: string };

function Disc({ id, children, title }: { id: string; children: React.ReactNode; title: string }) {
  return (
    <svg className="lang-flag" viewBox="0 0 60 60" role="img" aria-label={title}>
      <title>{title}</title>
      <defs>
        <clipPath id={id}>
          <circle cx="30" cy="30" r="30" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${id})`}>{children}</g>
      <circle cx="30" cy="30" r="29.2" fill="none" stroke="rgb(19 55 93 / 14%)" strokeWidth="1.6" />
    </svg>
  );
}

/** France: vertical tricolour. */
export function FlagFR({ title }: FlagProps) {
  return (
    <Disc id="flag-fr" title={title}>
      <rect x="0" y="0" width="20" height="60" fill="#002395" />
      <rect x="20" y="0" width="20" height="60" fill="#ffffff" />
      <rect x="40" y="0" width="20" height="60" fill="#ed2939" />
    </Disc>
  );
}

/** United Kingdom: Union Jack. */
export function FlagEN({ title }: FlagProps) {
  return (
    <Disc id="flag-en" title={title}>
      <rect x="0" y="0" width="60" height="60" fill="#012169" />
      <path d="M0 0 60 60M60 0 0 60" stroke="#ffffff" strokeWidth="13" />
      <path d="M0 0 60 60M60 0 0 60" stroke="#c8102e" strokeWidth="7" />
      <path d="M30 0v60M0 30h60" stroke="#ffffff" strokeWidth="20" />
      <path d="M30 0v60M0 30h60" stroke="#c8102e" strokeWidth="12" />
    </Disc>
  );
}

/** Arabic is a language, not a country: a green disc carrying the letter ain. */
export function FlagAR({ title }: FlagProps) {
  return (
    <Disc id="flag-ar" title={title}>
      <rect x="0" y="0" width="60" height="60" fill="#0f9a6f" />
      <text
        x="30"
        y="30"
        fill="#ffffff"
        fontSize="34"
        fontWeight="700"
        textAnchor="middle"
        dominantBaseline="central"
      >
        ع
      </text>
    </Disc>
  );
}

/** Morocco: red field with the green interlaced pentagram. */
export function FlagMA({ title }: FlagProps) {
  return (
    <Disc id="flag-ma" title={title}>
      <rect x="0" y="0" width="60" height="60" fill="#c1272d" />
      <polygon
        points="30,17 37.9,41.3 17.2,26.3 42.8,26.3 22.1,41.3"
        fill="none"
        stroke="#006233"
        strokeWidth="2.6"
        strokeLinejoin="round"
      />
    </Disc>
  );
}
