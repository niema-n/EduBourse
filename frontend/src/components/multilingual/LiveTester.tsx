import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import { FlaskConical, Link2, Loader2, Play, RotateCcw, TriangleAlert } from "lucide-react";

import { EXAMPLES } from "../../data/multilingual";
import { ChatError, MESSAGE_MAX_LENGTH, directionFor, guessScript, sendChatMessage } from "../../services/chat";
import { createMultilingualThreadId } from "../../services/multilingual";
import type { BackendStatus } from "../../services/multilingual";
import type { ChatErrorKind, ChatResponseBody } from "../../types/chat";
import { errorMessage, languageLabel, routeLabel, statusLabel } from "../assistant/labels";
import { MlPanelHead } from "./MlPanels";

type Outcome = { message: string; response: ChatResponseBody; durationMs: number };

function groundedText(grounded: boolean | null): string {
  if (grounded === null) return "Non applicable à cette route";
  return grounded ? "Oui — réponse sourcée" : "Non — preuve insuffisante";
}

/**
 * Sends one real message to POST /api/v1/chat and shows only the fields the
 * backend returned. Each test uses a fresh thread so languages never mix.
 */
export function LiveTester({ onBackendStatus }: { onBackendStatus: (status: BackendStatus) => void }) {
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [error, setError] = useState<ChatErrorKind | null>(null);
  const [validation, setValidation] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const run = async (text: string) => {
    const value = text.trim();
    if (!value) {
      setValidation(true);
      return;
    }
    if (pending) return;
    setValidation(false);
    setError(null);
    setOutcome(null);
    setPending(true);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const { response, requestDurationMs } = await sendChatMessage(
        { message: value, thread_id: createMultilingualThreadId() },
        controller.signal,
      );
      if (controller.signal.aborted) return;
      setOutcome({ message: value, response, durationMs: requestDurationMs });
      onBackendStatus("connected");
    } catch (caught) {
      // Only Réinitialiser or leaving the page abort this controller: stay silent.
      if (controller.signal.aborted) return;
      const kind = caught instanceof ChatError ? caught.kind : "network";
      setError(kind);
      if (kind === "network") onBackendStatus("unavailable");
    } finally {
      // A reset may already have started a newer test; never clear its spinner.
      if (abortRef.current === controller) {
        abortRef.current = null;
        setPending(false);
      }
    }
  };

  const reset = () => {
    const controller = abortRef.current;
    abortRef.current = null;
    controller?.abort();
    setMessage("");
    setOutcome(null);
    setError(null);
    setValidation(false);
    setPending(false);
  };

  const onKeyDown = (event: ReactKeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void run(message);
    }
  };

  const pick = (text: string) => {
    setMessage(text);
    void run(text);
  };

  const response = outcome?.response;
  const answerDir = response ? directionFor(response.script) : "ltr";

  return (
    <section className="ml-panel ml-tester" aria-labelledby="ml-tester-title">
      <MlPanelHead
        id="ml-tester-title"
        icon={FlaskConical}
        title="Test multilingue live"
        subtitle="Envoie un vrai message au backend et affiche les métadonnées renvoyées"
        action={<span className="ml-endpoint">POST /api/v1/chat</span>}
      />

      <div className="ml-examples" role="group" aria-label="Exemples rapides">
        {EXAMPLES.map(({ code, text, tone }) => (
          <button
            key={text}
            type="button"
            className={`ml-example ml-tone-${tone}`}
            onClick={() => pick(text)}
            disabled={pending}
            title="Remplir le champ et lancer le test"
          >
            <i className="ml-pill">{code}</i>
            <span dir={directionFor(guessScript(text))}>{text}</span>
          </button>
        ))}
      </div>

      <label className="ml-field">
        <span>Votre message</span>
        <textarea
          value={message}
          rows={3}
          maxLength={MESSAGE_MAX_LENGTH}
          dir={directionFor(guessScript(message))}
          placeholder="Écrivez une question en FR, EN, AR ou Darija…"
          aria-invalid={validation}
          aria-describedby="ml-field-hint"
          onChange={(event) => {
            setMessage(event.target.value);
            if (validation) setValidation(false);
          }}
          onKeyDown={onKeyDown}
        />
        <small id="ml-field-hint">Ctrl + Entrée pour lancer le test · une nouvelle conversation à chaque test</small>
      </label>
      {validation && <p className="ml-validation" role="alert">Saisissez un message avant de lancer le test.</p>}

      <div className="ml-actions">
        <button type="button" className="ml-button-primary" onClick={() => void run(message)} disabled={pending}>
          {pending ? <Loader2 size={16} className="ml-spin" aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
          Tester
        </button>
        <button type="button" className="ml-button-ghost" onClick={reset} disabled={!message && !outcome && !error && !pending}>
          <RotateCcw size={16} aria-hidden="true" /> Réinitialiser
        </button>
      </div>

      <div className="ml-result" aria-live="polite" aria-busy={pending}>
        {pending ? (
          <p className="ml-state">
            <Loader2 size={18} className="ml-spin" aria-hidden="true" /> Analyse de la langue et traitement par le backend…
          </p>
        ) : error ? (
          <div className="ml-state ml-state-error" role="alert">
            <TriangleAlert size={18} aria-hidden="true" />
            <span>
              <strong>Backend : erreur</strong>
              {errorMessage(error)}
            </span>
          </div>
        ) : !response || !outcome ? (
          <p className="ml-state">Choisissez un exemple ou écrivez un message pour voir la détection en direct.</p>
        ) : (
          <>
            <dl className="ml-meta">
              <div>
                <dt>Langue détectée</dt>
                <dd><span className="ml-badge ml-badge-blue">{languageLabel(response.language)}</span> <code>{response.language}</code></dd>
              </div>
              <div>
                <dt>Script détecté</dt>
                <dd>{response.script === "arabic" ? "Arabe" : "Latin"} · {answerDir.toUpperCase()}</dd>
              </div>
              <div>
                <dt>Route</dt>
                <dd>{routeLabel(response.route)} <code>{response.route}</code></dd>
              </div>
              <div>
                <dt>Statut</dt>
                <dd>
                  <span className={`ml-badge ${response.status === "ok" ? "ml-badge-green" : response.status === "error" ? "ml-badge-red" : "ml-badge-orange"}`}>
                    {response.status}
                  </span>{" "}
                  {statusLabel(response.status)}
                  {response.blocked && " · bloquée"}
                </dd>
              </div>
              <div>
                <dt>Mode</dt>
                <dd>Texte <small>(voix : via /api/v1/voice/live)</small></dd>
              </div>
              <div>
                <dt>Backend</dt>
                <dd><span className="ml-badge ml-badge-green">Connecté</span> <small>{Math.round(outcome.durationMs)} ms aller-retour</small></dd>
              </div>
              <div>
                <dt>Grounded</dt>
                <dd>{groundedText(response.grounded)}</dd>
              </div>
              <div className="ml-meta-wide">
                <dt>Thread ID</dt>
                <dd><code className="ml-thread">{response.thread_id}</code></dd>
              </div>
            </dl>

            <div className="ml-answer">
              <p className="ml-answer-label">
                Question : <q dir={directionFor(guessScript(outcome.message))}>{outcome.message}</q>
              </p>
              <p className="ml-answer-text" dir={answerDir} lang={response.language === "ary" ? "ar" : response.language}>
                {response.answer}
              </p>
            </div>

            {response.citations.length > 0 && (
              <div className="ml-citations">
                <p><Link2 size={14} aria-hidden="true" /> Citations ({response.citations.length})</p>
                <ul>
                  {response.citations.map((citation) => (
                    <li key={`${citation.evidence_id}-${citation.chunk_id}`}>
                      <strong>{citation.title}</strong>
                      <span>{citation.page_start === citation.page_end ? `p. ${citation.page_start}` : `p. ${citation.page_start}–${citation.page_end}`}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}
