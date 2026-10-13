import { useId, useState } from "react";
import { ChevronDown, ChevronUp, Languages } from "lucide-react";

import { authorityLabel, categoryLabel } from "../../services/rag";
import type { RagSearchHit } from "../../types/rag";

const SOURCE_LANGUAGE_NAMES: Record<string, string> = { fr: "français", en: "anglais", ar: "arabe" };

/** Label of a machine-translated preview, in the reader's language. */
function translationLabel(hit: RagSearchHit): { badge: string; note: string; arabic: boolean } {
  const arabic = hit.translated_script === "arabic";
  if (hit.translated_language === "en") {
    return { badge: "EN — traduction", note: "Traduction automatique — source originale en français", arabic };
  }
  if (hit.translated_language === "ar") {
    return { badge: "AR — ترجمة", note: "ترجمة تلقائية — المصدر الأصلي بالفرنسية", arabic };
  }
  return arabic
    ? { badge: "Darija — ترجمة", note: "ترجمة إلى الدارجة — المصدر الأصلي بالفرنسية", arabic }
    : { badge: "Darija — traduction", note: "Traduction en Darija — source originale en français", arabic };
}

/**
 * One retrieved chunk. The original excerpt is the evidence and is always shown
 * or one click away; a translated preview is only ever labelled as a translation.
 */
export function SearchHitCard({ hit }: { hit: RagSearchHit }) {
  const [showOriginal, setShowOriginal] = useState(false);
  const originalId = useId();
  const translated = hit.translation_status === "translated" && !!hit.translated_excerpt;
  const unavailable = hit.translation_status === "unavailable";
  const label = translated ? translationLabel(hit) : null;
  const sourceLanguage = SOURCE_LANGUAGE_NAMES[hit.source_language ?? ""] ?? hit.source_language ?? "inconnue";
  const toggleText = label?.arabic
    ? showOriginal ? "إخفاء النص الأصلي" : "عرض النص الأصلي"
    : showOriginal ? "Masquer l’extrait original" : "Voir l’extrait original";

  return (
    <li className="rg-hit" data-translation={hit.translation_status}>
      <div className="rg-hit-top">
        <span className="rg-rank">#{hit.rank}</span>
        <strong>{hit.title}</strong>
        <span
          className="rg-score"
          title={hit.score_type === "cosine_distance" ? "Distance cosinus : plus la valeur est basse, plus l’extrait est proche" : "Score de fusion RRF"}
        >
          {hit.score_type === "cosine_distance" ? `distance ${hit.score.toFixed(3)}` : `RRF ${hit.score.toFixed(4)}`}
        </span>
      </div>
      <div className="rg-hit-meta">
        <span>{authorityLabel(hit.authority)}</span>
        <span>{hit.page_start === hit.page_end ? `p. ${hit.page_start}` : `p. ${hit.page_start}–${hit.page_end}`}</span>
        {hit.categories.map((category) => (
          <span key={category} className="rg-cat">{categoryLabel(category)}</span>
        ))}
      </div>
      {hit.heading && <p className="rg-hit-heading">{hit.heading}</p>}

      {translated && label ? (
        <>
          <div className="rg-translation">
            <p className="rg-translation-head">
              <span className="rg-translation-badge">
                <Languages size={13} aria-hidden="true" /> {label.badge}
              </span>
              <span className="rg-translation-note" dir={label.arabic ? "rtl" : "ltr"}>{label.note}</span>
            </p>
            <p className="rg-translation-text" dir={label.arabic ? "rtl" : "ltr"} lang={hit.translated_language ?? undefined}>
              {hit.translated_excerpt}
            </p>
          </div>
          <button
            type="button"
            className="rg-original-toggle"
            aria-expanded={showOriginal}
            aria-controls={originalId}
            onClick={() => setShowOriginal((value) => !value)}
          >
            {showOriginal ? <ChevronUp size={14} aria-hidden="true" /> : <ChevronDown size={14} aria-hidden="true" />}
            <span dir={label.arabic ? "rtl" : "ltr"}>{toggleText}</span>
          </button>
          {showOriginal && (
            <div id={originalId} className="rg-original">
              <p className="rg-original-label">
                Extrait source original · {authorityLabel(hit.authority)} · {sourceLanguage}
              </p>
              <p className="rg-hit-excerpt" dir="ltr" lang={hit.source_language ?? undefined}>{hit.excerpt}</p>
            </div>
          )}
        </>
      ) : (
        <div className="rg-original rg-original-inline">
          <p className="rg-original-label">
            Extrait source original · {authorityLabel(hit.authority)} · {sourceLanguage}
          </p>
          {unavailable && <p className="rg-translation-missing">Traduction indisponible — extrait original affiché.</p>}
          <p className="rg-hit-excerpt" dir="ltr" lang={hit.source_language ?? undefined}>{hit.excerpt}</p>
        </div>
      )}
    </li>
  );
}
