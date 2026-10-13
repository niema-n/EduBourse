import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import { ArrowRight, History, Loader2, MessageCircle, Search, SearchCheck, SearchX, TriangleAlert } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { LANGUAGE_LABELS, RagError, searchRag } from "../../services/rag";
import type { RagSearchResult } from "../../types/rag";
import { RagPanelHead } from "./RagPanels";
import { SearchHitCard } from "./SearchHitCard";

const SUGGESTIONS = [
  "C’est quoi une action ?",
  "Quels sont les risques d’une obligation ?",
  "Comment fonctionne un OPCVM ?",
  "Comment fonctionne une introduction en bourse ?",
  "شنو هي البورصة؟",
];

const ARABIC_RE = /[\u0600-\u06ff]/;

type HistoryItem = { query: string; retrievalQuery: string | null; language: string };

const HISTORY_KEY = "edubourse.rag.searchHistory.v1";
const HISTORY_LIMIT = 5;

/** Reads the tab's search history; any malformed or blocked storage yields an empty list. */
function loadHistory(): HistoryItem[] {
  try {
    const parsed: unknown = JSON.parse(window.sessionStorage.getItem(HISTORY_KEY) ?? "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter(
        (item): item is HistoryItem =>
          !!item &&
          typeof item.query === "string" &&
          item.query.trim() !== "" &&
          (item.retrievalQuery === null || typeof item.retrievalQuery === "string") &&
          typeof item.language === "string",
      )
      .slice(0, HISTORY_LIMIT);
  } catch {
    return [];
  }
}

function saveHistory(items: HistoryItem[]) {
  try {
    window.sessionStorage.setItem(HISTORY_KEY, JSON.stringify(items));
  } catch {
    // Storage full or blocked: history stays in memory for this visit.
  }
}

export function SemanticSearch({ onSearched }: { onSearched: () => void }) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<RagSearchResult | null>(null);
  const [error, setError] = useState<RagError["kind"] | null>(null);
  const [validation, setValidation] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>(loadHistory);
  const abortRef = useRef<AbortController | null>(null);
  const requestSeq = useRef(0);

  useEffect(() => () => abortRef.current?.abort(), []);
  useEffect(() => saveHistory(history), [history]);

  const run = async (text: string) => {
    const value = text.trim();
    if (!value) {
      setValidation(true);
      return;
    }
    abortRef.current?.abort();
    const requestId = requestSeq.current + 1;
    requestSeq.current = requestId;
    setValidation(false);
    setError(null);
    setPending(true);
    setResult(null);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const data = await searchRag(value, topK, controller.signal);
      if (requestSeq.current !== requestId) return;
      setResult(data);
      setHistory((items) =>
        [{ query: data.query, retrievalQuery: data.retrieval_query, language: data.language }, ...items.filter((item) => item.query !== data.query)].slice(0, HISTORY_LIMIT),
      );
      onSearched();
    } catch (caught) {
      if (controller.signal.aborted) return;
      if (requestSeq.current !== requestId) return;
      setResult(null);
      setError(caught instanceof RagError ? caught.kind : "network");
    } finally {
      if (requestSeq.current === requestId) {
        abortRef.current = null;
        setPending(false);
      }
    }
  };

  const onKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      event.preventDefault();
      void run(query);
    }
  };

  const pick = (text: string) => {
    setQuery(text);
    void run(text);
  };

  return (
    <section className="rg-panel rg-search" aria-labelledby="rg-search-title">
      <RagPanelHead id="rg-search-title" icon={SearchCheck} glyph title="Tester la recherche sémantique" subtitle="Interroge le vrai corpus indexé, sans génération de réponse" />

      <div className="rg-chips" role="list" aria-label="Exemples de questions">
        {SUGGESTIONS.map((text) => (
          <button key={text} type="button" role="listitem" className="rg-chip" onClick={() => pick(text)} disabled={pending} dir={ARABIC_RE.test(text) ? "rtl" : undefined}>
            {text}
          </button>
        ))}
      </div>

      <div className="rg-search-bar">
        <label className="rg-search-input">
          <span className="visually-hidden">Rechercher dans le corpus</span>
          <Search size={17} aria-hidden="true" />
          <input
            value={query}
            maxLength={1000}
            onChange={(event) => {
              const next = event.target.value;
              setQuery(next);
              if (result && result.query.trim() !== next.trim()) {
                setResult(null);
                setError(null);
              }
              if (validation) setValidation(false);
            }}
            onKeyDown={onKeyDown}
            placeholder="Rechercher dans le corpus..."
            dir={ARABIC_RE.test(query) ? "rtl" : "ltr"}
            aria-invalid={validation}
          />
        </label>
        <label className="rg-topk">
          <span className="visually-hidden">Nombre de résultats</span>
          <select
            value={topK}
            onChange={(event) => {
              setTopK(Number(event.target.value));
              setResult(null);
              setError(null);
            }}
            disabled={pending}
          >
            {[3, 5, 10].map((value) => (
              <option key={value} value={value}>Top {value}</option>
            ))}
          </select>
        </label>
        <button type="button" className="rg-search-button" onClick={() => void run(query)} disabled={pending}>
          {pending ? <Loader2 size={16} className="rg-spin" aria-hidden="true" /> : <Search size={16} aria-hidden="true" />}
          Rechercher
        </button>
      </div>
      {validation && <p className="rg-validation" role="alert">Saisissez une question avant de lancer la recherche.</p>}

      <div className="rg-results" aria-live="polite" aria-busy={pending}>
        {pending ? (
          <p className="rg-state">
            <Loader2 size={18} className="rg-spin" aria-hidden="true" /> Recherche dans le corpus… (la première recherche charge le modèle BGE-M3)
          </p>
        ) : error ? (
          <p className="rg-state rg-state-error" role="alert">
            <TriangleAlert size={18} aria-hidden="true" />
            {error === "invalid" ? "La question saisie n’est pas valide (1 à 1000 caractères)." : "Impossible d’interroger le corpus pour le moment."}
          </p>
        ) : !result ? (
          <p className="rg-state">Entrez une question pour explorer les sources utilisées par EduBourse.</p>
        ) : (
          <>
            <dl className="rg-query-meta">
              <div>
                <dt>Question utilisateur</dt>
                <dd dir={result.script === "arabic" ? "rtl" : "ltr"}>{result.query}</dd>
              </div>
              <div>
                <dt>Langue détectée</dt>
                <dd><span className="rg-lang">{LANGUAGE_LABELS[result.language] ?? result.language}</span></dd>
              </div>
              <div className="rg-query-internal">
                <dt>Requête interne utilisée pour la recherche</dt>
                <dd dir="ltr">
                  {result.retrieval_query ?? result.query}
                  <small>{result.retrieval_query ? " · reformulée en français pour le corpus" : " · question utilisée telle quelle"}</small>
                </dd>
              </div>
            </dl>
            {result.results.length === 0 ? (
              <p className="rg-state"><SearchX size={18} aria-hidden="true" /> Aucun résultat pertinent trouvé.</p>
            ) : (
              <ol className="rg-hits">
                {result.results.map((hit) => (
                  <SearchHitCard key={hit.chunk_id} hit={hit} />
                ))}
              </ol>
            )}
            <button type="button" className="rg-ask" onClick={() => navigate("/assistant", { state: { prefill: result.query } })}>
              <MessageCircle size={16} aria-hidden="true" /> Poser à l’Assistant
            </button>
          </>
        )}
      </div>

      {history.length > 0 && (
        <div className="rg-history">
          <p className="rg-history-title"><History size={15} aria-hidden="true" /> Recherches de la session</p>
          <ul>
            {history.map((item) => (
              <li key={item.query}>
                <button type="button" onClick={() => pick(item.query)} disabled={pending}>
                  <q dir={ARABIC_RE.test(item.query) ? "rtl" : "ltr"}>{item.query}</q>
                  <ArrowRight size={13} aria-hidden="true" />
                  <span title="Requête interne utilisée pour la recherche">{item.retrievalQuery ?? "requête utilisée telle quelle"}</span>
                  <em>{LANGUAGE_LABELS[item.language] ?? item.language}</em>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="rg-search-note">
        Chaque recherche RAG est indépendante de l’historique de conversation ; les extraits affichés correspondent uniquement à la question lancée.
      </p>
    </section>
  );
}
