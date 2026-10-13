import type { KeyboardEvent as ReactKeyboardEvent, ReactNode } from "react";
import {
  ArrowRight,
  AudioWaveform,
  Ban,
  CircleAlert,
  CircleCheck,
  Compass,
  FileText,
  History,
  Info,
  Keyboard,
  Lightbulb,
  Link2,
  Loader2,
  MessageCircleCheck,
  Mic,
  MicOff,
  RotateCcw,
  Send,
  ServerCrash,
  ShieldCheck,
  Square,
  Trash2,
  Workflow,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { SECURITY_EXAMPLES, SECURITY_INFORMATION, SECURITY_PIPELINE, SECURITY_RULES } from "../../data/security";
import { MESSAGE_MAX_LENGTH, directionFor, guessScript } from "../../services/chat";
import { OUTCOME_TEXT, outcomeOf } from "../../services/security";
import type { SecurityOutcome } from "../../services/security";
import type { ChatResponseBody } from "../../types/chat";
import type { VoicePhase } from "../../types/voice";
import { VoiceAudioControls } from "../voice/VoiceAudioControls";
import type { VoiceSessionApi } from "../voice/useVoiceSession";
import { languageLabel, routeLabel, statusLabel } from "../assistant/labels";
import type { SecurityTestApi } from "./useSecurityTest";

export function SecurityPanelHead({
  id,
  icon: Icon,
  title,
  subtitle,
  action,
}: {
  id: string;
  icon: LucideIcon;
  title: string;
  subtitle: string;
  action?: ReactNode;
}) {
  return (
    <div className="sc-head">
      <span className="sc-head-tile" aria-hidden="true">
        <Icon size={21} strokeWidth={2.2} />
      </span>
      <div className="sc-head-copy">
        <h2 id={id}>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {action}
    </div>
  );
}

export function SecurityPipeline() {
  const navigate = useNavigate();
  return (
    <section className="sc-panel" aria-labelledby="sc-pipeline-title">
      <SecurityPanelHead
        id="sc-pipeline-title"
        icon={Workflow}
        title="Pipeline de sécurité"
        subtitle="Vérification avant le traitement métier et la génération de réponse"
      />
      <div className="sc-flow-host">
        <ol className="sc-flow" aria-label="Ordre réel des contrôles">
          {SECURITY_PIPELINE.map(({ icon: Icon, title, detail, tone, accent }, index) => (
            <li key={title} className={`sc-stage sc-tone-${tone} ${accent ? "sc-stage-accent" : ""}`}>
              {index > 0 && <ArrowRight className="sc-flow-arrow" size={14} aria-hidden="true" />}
              <span className="sc-stage-icon" aria-hidden="true">
                <Icon size={21} strokeWidth={2.1} />
              </span>
              <strong>
                <span className="sc-stage-index">{index + 1}.</span> {title}
              </strong>
              <small>{detail}</small>
            </li>
          ))}
        </ol>
      </div>
      <div className="sc-branch">
        <p>
          <Ban size={15} aria-hidden="true" />
          <span><strong>Demande sensible</strong> : 3 → 4 → réponse de sécurité → 8 → 9 → 10, sans mémoire, Supervisor ni RAG.</span>
        </p>
        <p>
          <Compass size={15} aria-hidden="true" />
          <span><strong>Hors domaine</strong> : décidé au Supervisor (6), réponse de recentrage localisée.</span>
        </p>
        <p>
          <FileText size={15} aria-hidden="true" />
          <span><strong>Sécurité ≠ grounding</strong> : la sécurité décide si la demande peut continuer ; le grounding vérifie ensuite les preuves d’une réponse documentaire.</span>
        </p>
      </div>

      <div className="sc-voice">
        <span className="sc-voice-icon" aria-hidden="true"><AudioWaveform size={22} /></span>
        <div className="sc-voice-copy">
          <strong>Sécurité identique pour le texte et la voix</strong>
          <p>
            Après transcription STT, une question vocale passe par les mêmes contrôles de sécurité, le même routage et les
            mêmes garde-fous que la question texte. L’audio brut n’est pas analysé : c’est le texte transcrit qui est contrôlé.
          </p>
          <p className="sc-voice-path">Micro → STT → texte transcrit → langue + script → <em>même garde de sécurité</em> → Supervisor → réponse localisée → TTS</p>
        </div>
        <button type="button" className="sc-button-outline" onClick={() => navigate("/voice")}>
          Voir Voice-to-Voice <ArrowRight size={15} aria-hidden="true" />
        </button>
      </div>
    </section>
  );
}

export type SecurityTestMode = "text" | "voice";

const VOICE_PHASE_TEXT: Record<VoicePhase, string> = {
  idle: "Prêt à écouter",
  requesting_permission: "Autorisation du microphone…",
  connecting: "Connexion au service vocal…",
  listening: "Écoute en cours… cliquez pour envoyer",
  processing: "Analyse de sécurité en cours…",
  speaking: "Réponse audio en cours…",
  error: "Erreur contrôlée",
};

function isVoiceBusy(phase: VoicePhase): boolean {
  return phase === "requesting_permission" || phase === "connecting" || phase === "listening" || phase === "processing" || phase === "speaking";
}

export function SecurityTester({
  test,
  voice,
  mode,
  onMode,
}: {
  test: SecurityTestApi;
  voice: VoiceSessionApi;
  mode: SecurityTestMode;
  onMode: (mode: SecurityTestMode) => void;
}) {
  const locked = test.pending || isVoiceBusy(voice.phase);
  return (
    <section className="sc-panel" aria-labelledby="sc-tester-title">
      <SecurityPanelHead
        id="sc-tester-title"
        icon={MessageCircleCheck}
        title="Tester la sécurité"
        subtitle="Envoyez une question au vrai backend — au clavier ou à la voix — et observez la décision"
      />
      <div className="sc-tabs" role="tablist" aria-label="Mode de test">
        <button
          type="button"
          role="tab"
          id="sc-tab-text"
          aria-selected={mode === "text"}
          aria-controls="sc-tabpanel"
          className={mode === "text" ? "active" : ""}
          onClick={() => onMode("text")}
          disabled={locked && mode !== "text"}
        >
          <Keyboard size={15} aria-hidden="true" /> Texte
        </button>
        <button
          type="button"
          role="tab"
          id="sc-tab-voice"
          aria-selected={mode === "voice"}
          aria-controls="sc-tabpanel"
          className={mode === "voice" ? "active" : ""}
          onClick={() => onMode("voice")}
          disabled={locked && mode !== "voice"}
        >
          <Mic size={15} aria-hidden="true" /> Voix
        </button>
      </div>
      <div id="sc-tabpanel" role="tabpanel" aria-labelledby={mode === "text" ? "sc-tab-text" : "sc-tab-voice"}>
        {mode === "text" ? <SecurityTextInput test={test} /> : <SecurityVoiceInput voice={voice} />}
      </div>
    </section>
  );
}

function SecurityVoiceInput({ voice }: { voice: VoiceSessionApi }) {
  const { phase, level, recordingSeconds, error, start, stop, reset, turns } = voice;
  const listening = phase === "listening";
  const busy = phase === "processing" || phase === "connecting" || phase === "requesting_permission";
  return (
    <div className="sc-voice-input">
      <div className="sc-voice-row">
        <button
          type="button"
          className={`sc-mic ${listening ? "is-listening" : ""}`}
          onClick={() => void (listening ? stop() : start())}
          disabled={busy}
          aria-pressed={listening}
          aria-label={listening ? "Arrêter l’enregistrement et envoyer la question" : "Poser la question à la voix"}
        >
          {busy ? (
            <Loader2 size={24} className="sc-spin" aria-hidden="true" />
          ) : listening ? (
            <Square size={20} aria-hidden="true" />
          ) : phase === "error" ? (
            <MicOff size={24} aria-hidden="true" />
          ) : (
            <Mic size={24} aria-hidden="true" />
          )}
        </button>
        <div className="sc-voice-status" role="status" aria-live="polite">
          <strong>{VOICE_PHASE_TEXT[phase]}</strong>
          {listening ? (
            <span className="sc-voice-level" title="Niveau réel du microphone">
              <i style={{ width: `${Math.round(level * 100)}%` }} />
              <em>{recordingSeconds.toFixed(1)} s</em>
            </span>
          ) : (
            <small>Cliquez, posez la question (ex. « Quelle action dois-je acheter ? »), puis cliquez à nouveau.</small>
          )}
        </div>
      </div>
      {error && (
        <p className="sc-validation" role="alert">{error}</p>
      )}
      <p className="sc-voice-hint">
        Micro → STT (Gemini Live) → texte transcrit → même garde de sécurité → réponse localisée → TTS ·{" "}
        <span className="sc-endpoint">WS /api/v1/voice/live</span>
      </p>
      <div className="sc-actions">
        <button type="button" className="sc-button-primary" onClick={() => void (listening ? stop() : start())} disabled={busy}>
          {listening ? <Square size={16} aria-hidden="true" /> : <Mic size={16} aria-hidden="true" />}
          {listening ? "Envoyer" : "Parler"}
        </button>
        <button type="button" className="sc-button-ghost" onClick={reset} disabled={phase === "idle" && turns.length === 0 && !error}>
          <RotateCcw size={16} aria-hidden="true" /> Réinitialiser
        </button>
      </div>
    </div>
  );
}

function SecurityTextInput({ test }: { test: SecurityTestApi }) {
  const onKeyDown = (event: ReactKeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void test.run(test.message);
    }
  };

  return (
    <>
      <label className="sc-field">
        <span>Votre question</span>
        <textarea
          value={test.message}
          rows={4}
          maxLength={MESSAGE_MAX_LENGTH}
          dir={directionFor(guessScript(test.message))}
          placeholder={"Tapez votre question ici…\n(ex. : « Quelle action dois-je acheter ? »)"}
          aria-invalid={test.validation}
          aria-describedby="sc-field-hint"
          onChange={(event) => test.setMessage(event.target.value)}
          onKeyDown={onKeyDown}
        />
        <small id="sc-field-hint">
          Ctrl + Entrée pour tester · nouvelle conversation à chaque test · <span className="sc-endpoint">POST /api/v1/chat</span>
        </small>
      </label>
      {test.validation && <p className="sc-validation" role="alert">Saisissez une question avant de lancer le test.</p>}
      <div className="sc-actions">
        <button type="button" className="sc-button-primary" onClick={() => void test.run(test.message)} disabled={test.pending}>
          {test.pending ? <Loader2 size={16} className="sc-spin" aria-hidden="true" /> : <Send size={16} aria-hidden="true" />}
          Tester
        </button>
        <button
          type="button"
          className="sc-button-ghost"
          onClick={test.reset}
          disabled={!test.message && !test.result && !test.error && !test.pending && !test.validation}
        >
          <RotateCcw size={16} aria-hidden="true" /> Réinitialiser
        </button>
      </div>
    </>
  );
}

const OUTCOME_ICON: Record<SecurityOutcome, LucideIcon> = {
  educational: CircleCheck,
  protected: ShieldCheck,
  out_of_domain: Compass,
  fallback: CircleAlert,
  error: ServerCrash,
};

type ResultView = {
  pending: boolean;
  pendingTitle: string;
  pendingDetail: string;
  errorMessage: string | null;
  question: string | null;
  response: ChatResponseBody | null;
  duration: { label: string; value: string };
};

function textView(test: SecurityTestApi): ResultView {
  return {
    pending: test.pending,
    pendingTitle: "Analyse de sécurité en cours…",
    pendingDetail: "Langue, garde de sécurité, routage et réponse du backend.",
    errorMessage: test.error ? "Impossible de vérifier cette demande pour le moment." : null,
    question: test.result?.question ?? null,
    response: test.result?.response ?? null,
    duration: {
      label: "Aller-retour navigateur",
      value: test.result ? `${(test.result.durationMs / 1000).toFixed(1)} s` : "Non disponible",
    },
  };
}

function voiceView(voice: VoiceSessionApi): ResultView {
  const turn = voice.turns[voice.turns.length - 1];
  const response = turn?.response ?? null;
  const waiting = !response && (voice.phase === "listening" || voice.phase === "processing" || voice.phase === "connecting" || voice.phase === "requesting_permission");
  return {
    pending: waiting,
    pendingTitle: voice.phase === "listening" ? "Écoute en cours…" : "Analyse de sécurité en cours…",
    pendingDetail:
      voice.phase === "listening"
        ? "Parlez, puis cliquez sur le micro pour envoyer."
        : turn?.transcript
          ? `Transcription : « ${turn.transcript} » — garde de sécurité et routage en cours.`
          : "Transcription STT puis même pipeline que le texte.",
    errorMessage: !response && voice.error ? voice.error : null,
    question: turn?.transcript ?? null,
    response,
    duration: {
      label: "Fin de parole → fin audio (navigateur)",
      value: turn?.clientTotalMs != null ? `${(turn.clientTotalMs / 1000).toFixed(1)} s` : "Non disponible",
    },
  };
}

export function SecurityResult({
  test,
  voice,
  mode,
}: {
  test: SecurityTestApi;
  voice: VoiceSessionApi;
  mode: SecurityTestMode;
}) {
  const view = mode === "text" ? textView(test) : voiceView(voice);
  const { response, question } = view;
  const outcome = response ? outcomeOf(response) : null;
  const OutcomeIcon = outcome ? OUTCOME_ICON[outcome] : ShieldCheck;

  return (
    <section className="sc-panel" aria-labelledby="sc-result-title">
      <SecurityPanelHead
        id="sc-result-title"
        icon={FileText}
        title="Résultat du test"
        subtitle={mode === "text" ? "Informations retournées par le backend" : "Transcription STT et décision retournées par le backend"}
      />
      <div aria-live="polite" aria-busy={view.pending}>
        {view.pending ? (
          <div className="sc-empty">
            <Loader2 size={30} className="sc-spin" aria-hidden="true" />
            <strong>{view.pendingTitle}</strong>
            <span>{view.pendingDetail}</span>
          </div>
        ) : view.errorMessage ? (
          <div className="sc-outcome sc-outcome-error" role="alert">
            <ServerCrash size={22} aria-hidden="true" />
            <div>
              <strong>Erreur de service</strong>
              <span>{view.errorMessage}</span>
            </div>
          </div>
        ) : !response || !outcome ? (
          <div className="sc-empty">
            <span className="sc-empty-icon" aria-hidden="true">{mode === "text" ? <ShieldCheck size={28} /> : <Mic size={28} />}</span>
            <strong>Aucun test pour l’instant</strong>
            <span>
              {mode === "text"
                ? "Posez une question ou choisissez un exemple pour voir le résultat ici."
                : "Cliquez sur le micro et posez votre question à voix haute."}
            </span>
          </div>
        ) : (
          <>
            <div className={`sc-outcome sc-outcome-${outcome}`}>
              <OutcomeIcon size={22} aria-hidden="true" />
              <div>
                <strong>{OUTCOME_TEXT[outcome].label}</strong>
                <span>{OUTCOME_TEXT[outcome].detail}</span>
              </div>
            </div>
            {question && (
              <p className="sc-question">
                {mode === "voice" ? "Vous avez dit (STT)" : "Question"} : <q dir={directionFor(guessScript(question))}>{question}</q>
              </p>
            )}
            <p className="sc-answer" dir={directionFor(response.script)} lang={response.language === "ary" ? "ar" : response.language}>
              {response.answer}
            </p>
            {mode === "voice" && (
              <VoiceAudioControls session={voice} className="sc-audio" buttonClassName="sc-button-ghost sc-button-small" errorClassName="sc-validation" />
            )}
            <dl className="sc-meta">
              <div><dt>Canal</dt><dd>{mode === "voice" ? "Voix (STT → texte)" : "Texte"}</dd></div>
              <div><dt>Langue détectée</dt><dd>{languageLabel(response.language)} ({response.language})</dd></div>
              <div><dt>Script</dt><dd>{response.script === "arabic" ? "Arabe · RTL" : "Latin · LTR"}</dd></div>
              <div><dt>Route</dt><dd>{routeLabel(response.route)} <code>{response.route}</code></dd></div>
              <div><dt>Statut</dt><dd>{response.status} · {statusLabel(response.status)}</dd></div>
              <div><dt>Blocked</dt><dd>{response.blocked ? "Oui — traitement métier bloqué" : "Non"}</dd></div>
              <div>
                <dt>Grounded</dt>
                <dd>{response.grounded === null ? "Non applicable à cette route" : response.grounded ? "Oui" : "Non"}</dd>
              </div>
              <div><dt>Citations</dt><dd>{response.citations.length}</dd></div>
              <div className="sc-meta-wide"><dt>{view.duration.label}</dt><dd>{view.duration.value}</dd></div>
              <div className="sc-meta-wide"><dt>Thread ID</dt><dd><code>{response.thread_id}</code></dd></div>
            </dl>
            {response.citations.length > 0 && (
              <ul className="sc-citations" aria-label="Citations renvoyées">
                {response.citations.map((citation) => (
                  <li key={`${citation.evidence_id}-${citation.chunk_id}`}>
                    <Link2 size={13} aria-hidden="true" />
                    <span>{citation.title}</span>
                    <small>{citation.page_start === citation.page_end ? `p. ${citation.page_start}` : `p. ${citation.page_start}–${citation.page_end}`}</small>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </section>
  );
}

export function SecurityExamples({
  test,
  onPick,
  disabled = false,
}: {
  test: SecurityTestApi;
  onPick: (text: string) => void;
  disabled?: boolean;
}) {
  return (
    <section className="sc-panel" aria-labelledby="sc-examples-title">
      <SecurityPanelHead id="sc-examples-title" icon={Lightbulb} title="Exemples de questions" subtitle="Cliquez : la question est envoyée au backend en mode texte, ou dites-la en mode voix" />
      <div className="sc-examples" role="group" aria-label="Exemples de questions">
        {SECURITY_EXAMPLES.map(({ label, text, kind }) => (
          <button
            key={text}
            type="button"
            className={`sc-example sc-example-${kind}`}
            onClick={() => onPick(text)}
            disabled={test.pending || disabled}
          >
            <em>{label}</em>
            <span dir={directionFor(guessScript(text))}>{text}</span>
          </button>
        ))}
      </div>
      <p className="sc-note">Les étiquettes décrivent l’intention de l’exemple ; la décision affichée vient uniquement du backend.</p>
    </section>
  );
}

export function SecurityRules() {
  return (
    <section className="sc-panel" aria-labelledby="sc-rules-title">
      <SecurityPanelHead id="sc-rules-title" icon={ShieldCheck} title="Règles de sécurité" subtitle="Principes appliqués par le backend EduBourse" />
      <ul className="sc-rules">
        {SECURITY_RULES.map(({ title, detail }) => (
          <li key={title}>
            <CircleCheck size={19} strokeWidth={2.4} aria-hidden="true" />
            <span>
              <strong>{title}</strong>
              <small>{detail}</small>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function SecurityHistory({ test }: { test: SecurityTestApi }) {
  const { history } = test;
  return (
    <section className="sc-panel" aria-labelledby="sc-history-title">
      <SecurityPanelHead
        id="sc-history-title"
        icon={History}
        title="Historique des tests de cette session"
        subtitle="Tests lancés depuis cette page uniquement (onglet courant)"
        action={
          <button type="button" className="sc-button-ghost sc-button-small" onClick={test.clearHistory} disabled={history.length === 0}>
            <Trash2 size={14} aria-hidden="true" /> Effacer l’historique
          </button>
        }
      />
      {history.length === 0 ? (
        <p className="sc-history-empty">Aucun test dans cette session.</p>
      ) : (
        <div className="sc-table-wrap">
          <table className="sc-table">
            <thead>
              <tr>
                <th scope="col">Heure</th>
                <th scope="col">Langue</th>
                <th scope="col">Route</th>
                <th scope="col">Statut</th>
                <th scope="col">Question (extrait)</th>
              </tr>
            </thead>
            <tbody>
              {history.map((item) => (
                <tr key={item.id}>
                  <td>{new Date(item.at).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</td>
                  <td>{item.language}</td>
                  <td><code>{item.route}</code></td>
                  <td><span className={`sc-pill sc-pill-${item.outcome}`}>{item.status}</span></td>
                  <td dir={directionFor(guessScript(item.preview))}>
                    <span className={`sc-channel sc-channel-${item.channel}`}>{item.channel === "voix" ? "Voix" : "Texte"}</span> {item.preview}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function SecurityInformation() {
  return (
    <section className="sc-panel" aria-labelledby="sc-info-title">
      <SecurityPanelHead id="sc-info-title" icon={Info} title="Informations importantes" subtitle="À propos de la sécurité" />
      <ul className="sc-info">
        {SECURITY_INFORMATION.map((item) => (
          <li key={item}>
            <CircleCheck size={16} aria-hidden="true" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
