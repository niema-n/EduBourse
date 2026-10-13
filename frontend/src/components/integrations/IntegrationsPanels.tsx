import { useState } from "react";
import type { ReactNode } from "react";
import {
  ArrowRight,
  AudioWaveform,
  Ban,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CircleCheck,
  CircleX,
  ExternalLink,
  FlaskConical,
  HeartPulse,
  History,
  Info,
  Link2,
  Loader2,
  MessageSquareText,
  Mic,
  MicOff,
  Network,
  RefreshCw,
  RotateCcw,
  Send,
  ServerCrash,
  ShieldCheck,
  Square,
  Trash2,
  Workflow,
  Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import {
  ASK_FLOW,
  INTEGRATION_EXAMPLES,
  INTEGRATION_INFORMATION,
  MCP_CAN,
  MCP_CANNOT,
  MCP_FACTS,
  MCP_RESOURCES,
  MCP_TOOLS,
  N8N_FACTS,
  WORKFLOW_DETAILS,
} from "../../data/integrations";
import { directionFor, guessScript } from "../../services/chat";
import { integrationErrorText } from "../../services/integrations";
import type { IntegrationStatus, TesterTab } from "../../types/integrations";
import type { VoicePhase } from "../../types/voice";
import { VoiceAudioControls } from "../voice/VoiceAudioControls";
import type { VoiceSessionApi } from "../voice/useVoiceSession";
import type { IntegrationTestsApi } from "./useIntegrationTests";

export type StatusState = { data: IntegrationStatus | null; loading: boolean; failed: boolean };

export function IntegrationsPanelHead({
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
    <div className="ig-head">
      <span className="ig-head-tile" aria-hidden="true">
        <Icon size={21} strokeWidth={2.2} />
      </span>
      <div className="ig-head-copy">
        <h2 id={id}>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {action}
    </div>
  );
}

function LiveBadge({ state, ok, okLabel, koLabel }: { state: StatusState; ok: boolean | undefined; okLabel: string; koLabel: string }) {
  if (state.loading) return <span className="ig-badge ig-badge-wait"><Loader2 size={12} className="ig-spin" aria-hidden="true" /> Vérification…</span>;
  if (state.failed || ok === undefined) return <span className="ig-badge ig-badge-muted">Non vérifié</span>;
  return ok ? (
    <span className="ig-badge ig-badge-ok"><CheckCircle2 size={12} aria-hidden="true" /> {okLabel}</span>
  ) : (
    <span className="ig-badge ig-badge-ko"><CircleX size={12} aria-hidden="true" /> {koLabel}</span>
  );
}

export function ArchitectureCard() {
  return (
    <section className="ig-panel" aria-labelledby="ig-arch-title">
      <IntegrationsPanelHead
        id="ig-arch-title"
        icon={Network}
        title="Architecture MCP & n8n"
        subtitle="Les intégrations étendent EduBourse sans dupliquer sa logique métier"
      />
      <div className="ig-flow-host">
        <ol className="ig-flow" aria-label="Chemin réel d’une question arrivant par n8n et MCP">
          {ASK_FLOW.map(({ icon: Icon, title, detail, tone }, index) => (
            <li key={title} className={`ig-stage ig-tone-${tone}`}>
              {index > 0 && <ArrowRight className="ig-flow-arrow" size={14} aria-hidden="true" />}
              <span className="ig-stage-icon" aria-hidden="true"><Icon size={20} strokeWidth={2.1} /></span>
              <strong>{title}</strong>
              <small>{detail}</small>
            </li>
          ))}
        </ol>
      </div>

      <div className="ig-arch-notes">
        <p className="ig-health-path">
          <HeartPulse size={16} aria-hidden="true" />
          <span>
            <strong>Chemin santé</strong> : MCP <code>get_backend_health</code> → <code>GET /api/v1/health/live</code> → champs bornés (status, app, version).
          </span>
        </p>
        <p>
          <Link2 size={16} aria-hidden="true" />
          <span>
            <strong>Réseaux</strong> : n8n ↔ MCP et MCP ↔ backend partagent des réseaux d’intégration dédiés ; MCP ne résout ni PostgreSQL ni ChromaDB.
          </span>
        </p>
        <p>
          <MessageSquareText size={16} aria-hidden="true" />
          <span>
            <strong>Voix</strong> : le Voice-to-Voice ne passe pas par MCP ni n8n ; il utilise le WebSocket canonique du backend.
          </span>
        </p>
      </div>

      <div className="ig-callout">
        <ShieldCheck size={22} aria-hidden="true" />
        <div>
          <strong>MCP et n8n ne remplacent pas le backend.</strong>
          <p>
            Ils orchestrent ou exposent des intégrations, mais les règles métier, la sécurité, le routage, le RAG et le
            grounding restent centralisés dans le backend EduBourse.
          </p>
        </div>
      </div>
    </section>
  );
}

export function McpCard({ status, onRefresh }: { status: StatusState; onRefresh: () => void }) {
  const [docsOpen, setDocsOpen] = useState(false);
  const mcp = status.data?.mcp;
  return (
    <section className="ig-panel" aria-labelledby="ig-mcp-title">
      <IntegrationsPanelHead
        id="ig-mcp-title"
        icon={Wrench}
        title="MCP EduBourse"
        subtitle="1 serveur · capacités contrôlées"
        action={<LiveBadge state={status} ok={mcp ? mcp.reachable && mcp.auth_enforced : undefined} okLabel="Disponible" koLabel="Indisponible" />}
      />
      <dl className="ig-facts">
        <div><dt>Protocole</dt><dd>{MCP_FACTS.protocol}</dd></div>
        <div><dt>Implémentation</dt><dd>{MCP_FACTS.implementation}</dd></div>
        <div><dt>Transport</dt><dd>{MCP_FACTS.transport}</dd></div>
        <div><dt>Endpoint</dt><dd><code>{MCP_FACTS.endpoint}</code></dd></div>
        <div>
          <dt>Authentification</dt>
          <dd>
            Authentification requise{" "}
            {mcp && (mcp.auth_enforced ? <span className="ig-inline-ok">· refus sans jeton vérifié</span> : <span className="ig-inline-ko">· non vérifiée</span>)}
          </dd>
        </div>
        <div>
          <dt>Pont backend</dt>
          <dd>{mcp ? (mcp.bridge_configured ? "Configuré côté serveur (jeton non exposé)" : "Non configuré") : "Non vérifié"}</dd>
        </div>
      </dl>

      <div className="ig-caps">
        <div>
          <p className="ig-caps-title">Tools ({MCP_TOOLS.length})</p>
          <ul>
            {MCP_TOOLS.map((tool) => (
              <li key={tool.name}><code>{tool.name}</code><small>{tool.description}</small></li>
            ))}
          </ul>
        </div>
        <div>
          <p className="ig-caps-title">Resources ({MCP_RESOURCES.length})</p>
          <ul>
            {MCP_RESOURCES.map((resource) => (
              <li key={resource.uri}><code>{resource.uri}</code><small>{resource.description}</small></li>
            ))}
          </ul>
        </div>
      </div>

      <div className="ig-actions-row">
        <button type="button" className="ig-button-soft" aria-expanded={docsOpen} aria-controls="ig-mcp-docs" onClick={() => setDocsOpen((open) => !open)}>
          <BookOpen size={15} aria-hidden="true" /> Voir la documentation MCP {docsOpen ? <ChevronUp size={15} aria-hidden="true" /> : <ChevronDown size={15} aria-hidden="true" />}
        </button>
        <button type="button" className="ig-button-ghost ig-button-small" onClick={onRefresh} disabled={status.loading}>
          <RefreshCw size={14} aria-hidden="true" className={status.loading ? "ig-spin" : ""} /> Rafraîchir l’état
        </button>
      </div>
      {docsOpen && (
        <div id="ig-mcp-docs" className="ig-docs">
          <div className="ig-boundaries">
            <div>
              <p className="ig-caps-title"><CircleCheck size={14} aria-hidden="true" /> Ce que MCP peut faire</p>
              <ul>{MCP_CAN.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
            <div>
              <p className="ig-caps-title ig-title-ko"><Ban size={14} aria-hidden="true" /> Ce que MCP ne fait pas directement</p>
              <ul>{MCP_CANNOT.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          </div>
          <p className="ig-doc-note"><strong>Architecture d’authentification</strong> : {MCP_FACTS.auth}. Ce n’est pas une authentification par utilisateur ; le jeton reste côté serveur (n8n et pont backend).</p>
          <p className="ig-doc-note">{MCP_FACTS.hosts}. Délai métier de <code>ask_edubourse</code> : {MCP_FACTS.businessTimeout}.</p>
        </div>
      )}
    </section>
  );
}

function workflowBadge(registered: boolean | null, loading: boolean): ReactNode {
  if (loading) return <span className="ig-badge ig-badge-wait">Vérification…</span>;
  if (registered === null) return <span className="ig-badge ig-badge-muted">Manuel · défini dans le projet</span>;
  return registered ? <span className="ig-badge ig-badge-ok">Webhook actif</span> : <span className="ig-badge ig-badge-ko">Webhook non enregistré</span>;
}

export function N8nCard({ status }: { status: StatusState }) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const n8n = status.data?.n8n;
  const workflows = status.data?.workflows ?? [
    { key: "health", name: "EduBourse - Health Webhook", trigger: "webhook" as const, webhook_path: "edubourse-health", registered: null },
    { key: "backend_health", name: "EduBourse - Backend Health Bridge", trigger: "webhook" as const, webhook_path: "edubourse-backend-health", registered: null },
    { key: "mcp_ask", name: "EduBourse - MCP Ask", trigger: "webhook" as const, webhook_path: "edubourse-mcp-ask", registered: null },
    { key: "rag_update", name: "EduBourse - RAG Update", trigger: "manual" as const, webhook_path: null, registered: null },
  ];
  return (
    <section className="ig-panel" aria-labelledby="ig-n8n-title">
      <IntegrationsPanelHead
        id="ig-n8n-title"
        icon={Workflow}
        title="n8n Automatisation"
        subtitle={`Orchestration de workflows · version ${N8N_FACTS.version} (${N8N_FACTS.versionSource})`}
        action={<LiveBadge state={status} ok={n8n?.reachable} okLabel="Disponible" koLabel="Indisponible" />}
      />
      <ul className="ig-workflows">
        {workflows.map((workflow) => (
          <li key={workflow.key}>
            <span className="ig-workflow-copy">
              <strong>{workflow.name}</strong>
              <small>{WORKFLOW_DETAILS[workflow.key]?.purpose}</small>
            </span>
            {status.failed ? <span className="ig-badge ig-badge-muted">Non vérifié</span> : workflowBadge(workflow.registered, status.loading)}
          </li>
        ))}
      </ul>
      <p className="ig-doc-note">
        RAG Update = <strong>validation / contrôle du corpus approuvé</strong> uniquement (<code>mode=validate</code>). Aucune ingestion
        incrémentale n’est implémentée et aucune action de mise à jour n’est proposée depuis cette page.
      </p>
      <div className="ig-actions-row">
        <button type="button" className="ig-button-soft" aria-expanded={detailsOpen} aria-controls="ig-n8n-details" onClick={() => setDetailsOpen((open) => !open)}>
          <Workflow size={15} aria-hidden="true" /> Voir les workflows n8n {detailsOpen ? <ChevronUp size={15} aria-hidden="true" /> : <ChevronDown size={15} aria-hidden="true" />}
        </button>
        <a className="ig-button-ghost ig-button-small" href={N8N_FACTS.url} target="_blank" rel="noopener noreferrer">
          Ouvrir n8n <ExternalLink size={14} aria-hidden="true" />
        </a>
      </div>
      {detailsOpen && (
        <div id="ig-n8n-details" className="ig-docs">
          {workflows.map((workflow) => (
            <div key={workflow.key} className="ig-workflow-detail">
              <p className="ig-caps-title">{workflow.name}</p>
              <ol>{(WORKFLOW_DETAILS[workflow.key]?.steps ?? []).map((step) => <li key={step}>{step}</li>)}</ol>
            </div>
          ))}
          <p className="ig-doc-note">Délai de l’appel MCP dans « MCP Ask » : {N8N_FACTS.askTimeout}. Les identifiants restent dans n8n.</p>
        </div>
      )}
    </section>
  );
}

const TABS: { kind: TesterTab; label: string; icon: LucideIcon; button: string; path: string }[] = [
  { kind: "mcp_health", label: "MCP Health", icon: HeartPulse, button: "Tester le health MCP", path: "Backend → MCP get_backend_health → backend health" },
  { kind: "mcp_ask", label: "MCP Ask", icon: Wrench, button: "Tester ask_edubourse", path: "Backend → MCP ask_edubourse → /api/v1/chat" },
  { kind: "n8n_mcp_ask", label: "n8n MCP Ask", icon: Workflow, button: "Tester le workflow MCP Ask", path: "Backend → n8n webhook → MCP ask_edubourse → /api/v1/chat" },
  {
    kind: "voice",
    label: "Voice-to-Voice",
    icon: AudioWaveform,
    button: "Parler",
    path: "Micro → WebSocket /api/v1/voice/live → STT → même pipeline canonique → TTS (ne passe pas par MCP ni n8n)",
  },
];

const VOICE_PHASE_TEXT: Record<VoicePhase, string> = {
  idle: "Prêt à écouter",
  requesting_permission: "Autorisation du microphone…",
  connecting: "Connexion au service vocal…",
  listening: "Écoute en cours… cliquez pour envoyer",
  processing: "Traitement de votre question…",
  speaking: "Réponse audio en cours…",
  error: "Erreur contrôlée",
};

function voiceBusy(phase: VoicePhase): boolean {
  return ["requesting_permission", "connecting", "listening", "processing", "speaking"].includes(phase);
}

function IntegrationVoiceInput({ voice }: { voice: VoiceSessionApi }) {
  const { phase, level, recordingSeconds, error, start, stop, reset, turns } = voice;
  const listening = phase === "listening";
  const busy = phase === "processing" || phase === "connecting" || phase === "requesting_permission";
  return (
    <div className="ig-voice">
      <div className="ig-voice-row">
        <button
          type="button"
          className={`ig-mic ${listening ? "is-listening" : ""}`}
          onClick={() => void (listening ? stop() : start())}
          disabled={busy}
          aria-pressed={listening}
          aria-label={listening ? "Arrêter l’enregistrement et envoyer la question" : "Poser la question à la voix"}
        >
          {busy ? <Loader2 size={24} className="ig-spin" aria-hidden="true" /> : listening ? <Square size={20} aria-hidden="true" /> : phase === "error" ? <MicOff size={24} aria-hidden="true" /> : <Mic size={24} aria-hidden="true" />}
        </button>
        <div className="ig-voice-status" role="status" aria-live="polite">
          <strong>{VOICE_PHASE_TEXT[phase]}</strong>
          {listening ? (
            <span className="ig-voice-level" title="Niveau réel du microphone">
              <i style={{ width: `${Math.round(level * 100)}%` }} />
              <em>{recordingSeconds.toFixed(1)} s</em>
            </span>
          ) : (
            <small>Cliquez, posez votre question (ex. « C’est quoi une action ? »), puis cliquez à nouveau.</small>
          )}
        </div>
      </div>
      {error && <p className="ig-validation" role="alert">{error}</p>}
      <p className="ig-doc-note">
        Le Voice-to-Voice utilise son WebSocket canonique : la transcription passe par la même sécurité, le même routage et le même RAG
        que le texte, sans intermédiaire MCP ou n8n.
      </p>
      <div className="ig-actions">
        <button type="button" className="ig-button-primary" onClick={() => void (listening ? stop() : start())} disabled={busy}>
          {listening ? <Square size={16} aria-hidden="true" /> : <Mic size={16} aria-hidden="true" />}
          {listening ? "Envoyer" : "Parler"}
        </button>
        <button type="button" className="ig-button-ghost" onClick={reset} disabled={phase === "idle" && turns.length === 0 && !error}>
          <RotateCcw size={16} aria-hidden="true" /> Réinitialiser
        </button>
      </div>
    </div>
  );
}

export function TesterCard({ tests, voice }: { tests: IntegrationTestsApi; voice: VoiceSessionApi }) {
  const tab = TABS.find((item) => item.kind === tests.kind) ?? TABS[0];
  const isVoice = tests.kind === "voice";
  const ask = tests.kind !== "mcp_health" && !isVoice;
  const locked = tests.pending || voiceBusy(voice.phase);
  return (
    <section className="ig-panel" aria-labelledby="ig-tester-title">
      <IntegrationsPanelHead id="ig-tester-title" icon={FlaskConical} title="Tester les intégrations" subtitle="Appels réels exécutés côté serveur, sans jeton dans le navigateur" />
      <div className="ig-tabs" role="tablist" aria-label="Type de test">
        {TABS.map(({ kind, label, icon: Icon }) => (
          <button
            key={kind}
            type="button"
            role="tab"
            aria-selected={tests.kind === kind}
            className={tests.kind === kind ? "active" : ""}
            onClick={() => tests.setKind(kind)}
            disabled={locked && tests.kind !== kind}
          >
            <Icon size={15} aria-hidden="true" /> {label}
          </button>
        ))}
      </div>
      <p className="ig-path"><Network size={14} aria-hidden="true" /> {tab.path}</p>

      {ask && (
        <>
          <label className="ig-field">
            <span>Question</span>
            <textarea
              value={tests.message}
              rows={3}
              maxLength={1000}
              dir={directionFor(guessScript(tests.message))}
              placeholder="Écrivez une question EduBourse…"
              aria-invalid={tests.validation}
              onChange={(event) => tests.setMessage(event.target.value)}
            />
          </label>
          {tests.validation && <p className="ig-validation" role="alert">Saisissez une question avant de lancer le test.</p>}
          <div className="ig-examples" role="group" aria-label="Exemples de questions (remplissent le champ)">
            {INTEGRATION_EXAMPLES.map((example) => (
              <button key={example} type="button" onClick={() => tests.setMessage(example)} disabled={tests.pending}>
                <span dir={directionFor(guessScript(example))}>{example}</span>
              </button>
            ))}
          </div>
          <label className="ig-check">
            <input
              type="checkbox"
              checked={tests.sameThread}
              disabled={!tests.currentThread || tests.pending}
              onChange={(event) => tests.setSameThread(event.target.checked)}
            />
            <span>
              Continuer sur le même thread{tests.currentThread ? <> (<code>{tests.currentThread.slice(0, 20)}…</code>)</> : " (après un premier test)"}
            </span>
          </label>
        </>
      )}

      {isVoice && <IntegrationVoiceInput voice={voice} />}

      {!isVoice && (
      <div className="ig-actions">
        <button type="button" className="ig-button-primary" onClick={() => void tests.run()} disabled={tests.pending}>
          {tests.pending ? <Loader2 size={16} className="ig-spin" aria-hidden="true" /> : <Send size={16} aria-hidden="true" />}
          {tab.button}
        </button>
        <button type="button" className="ig-button-ghost" onClick={tests.reset} disabled={!tests.pending && !tests.result && !tests.failure && !tests.message}>
          <RotateCcw size={16} aria-hidden="true" /> Réinitialiser
        </button>
      </div>
      )}
    </section>
  );
}

function formatDuration(ms: number): string {
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
}

const KIND_LABEL: Record<TesterTab, string> = { mcp_health: "MCP Health", mcp_ask: "MCP Ask", n8n_mcp_ask: "n8n MCP Ask", voice: "Voice-to-Voice" };

function VoiceResult({ voice }: { voice: VoiceSessionApi }) {
  const turn = voice.turns[voice.turns.length - 1];
  const response = turn?.response ?? null;
  const waiting = !response && ["listening", "processing", "connecting", "requesting_permission"].includes(voice.phase);
  if (waiting) {
    return (
      <div className="ig-empty">
        <Loader2 size={28} className="ig-spin" aria-hidden="true" />
        <strong>{voice.phase === "listening" ? "Écoute en cours…" : "Test Voice-to-Voice en cours…"}</strong>
        <span>{turn?.transcript ? `Transcription : « ${turn.transcript} » — traitement par le pipeline canonique.` : "Transcription STT puis même pipeline que le texte."}</span>
      </div>
    );
  }
  if (!response) {
    return voice.error ? (
      <div className="ig-outcome ig-outcome-error" role="alert">
        <ServerCrash size={20} aria-hidden="true" />
        <div><strong>Voice-to-Voice : échec contrôlé</strong><span>{voice.error}</span></div>
      </div>
    ) : (
      <div className="ig-empty">
        <span className="ig-empty-icon" aria-hidden="true"><Mic size={26} /></span>
        <strong>Aucun test vocal pour l’instant</strong>
        <span>Cliquez sur le micro et posez votre question à voix haute.</span>
      </div>
    );
  }
  return (
    <>
      <div className={`ig-outcome ${response.blocked ? "ig-outcome-protected" : "ig-outcome-ok"}`}>
        {response.blocked ? <ShieldCheck size={20} aria-hidden="true" /> : <CheckCircle2 size={20} aria-hidden="true" />}
        <div>
          <strong>{response.blocked ? "Réponse vocale · protection activée" : "Réponse vocale EduBourse reçue"}</strong>
          <span>Via le WebSocket canonique, sans MCP ni n8n.</span>
        </div>
      </div>
      {turn?.transcript && (
        <p className="ig-question">Vous avez dit (STT) : <q dir={directionFor(guessScript(turn.transcript))}>{turn.transcript}</q></p>
      )}
      <p className="ig-answer" dir={response.script === "arabic" ? "rtl" : "ltr"}>{response.answer}</p>
      <VoiceAudioControls session={voice} className="ig-audio" buttonClassName="ig-button-ghost ig-button-small" errorClassName="ig-validation" />
      {turn?.errorMessage && <p className="ig-validation">{turn.errorMessage}</p>}
      <dl className="ig-meta">
        <div><dt>Intégration</dt><dd>Voice-to-Voice</dd></div>
        <div><dt>Statut</dt><dd>{response.status}</dd></div>
        <div><dt>Route</dt><dd><code>{response.route}</code></dd></div>
        <div><dt>Blocked</dt><dd>{response.blocked ? "Oui" : "Non"}</dd></div>
        <div><dt>Langue · script</dt><dd>{response.language} · {response.script}</dd></div>
        <div><dt>Grounded · citations</dt><dd>{response.grounded === null ? "N/A" : response.grounded ? "Oui" : "Non"} · {response.citations.length}</dd></div>
        <div className="ig-meta-wide"><dt>Thread ID</dt><dd><code>{response.thread_id}</code></dd></div>
        <div className="ig-meta-wide">
          <dt>Fin de parole → fin audio (navigateur)</dt>
          <dd>{turn?.clientTotalMs != null ? formatDuration(turn.clientTotalMs) : "Non disponible"}</dd>
        </div>
      </dl>
    </>
  );
}

export function ResultCard({ tests, voice }: { tests: IntegrationTestsApi; voice: VoiceSessionApi }) {
  const { result, pending, failure } = tests;
  if (tests.kind === "voice") {
    return (
      <section className="ig-panel" aria-labelledby="ig-result-title">
        <IntegrationsPanelHead id="ig-result-title" icon={MessageSquareText} title="Résultat du test" subtitle="Transcription STT et réponse renvoyées par le backend" />
        <div aria-live="polite"><VoiceResult voice={voice} /></div>
      </section>
    );
  }
  return (
    <section className="ig-panel" aria-labelledby="ig-result-title">
      <IntegrationsPanelHead id="ig-result-title" icon={MessageSquareText} title="Résultat du test" subtitle="Champs réellement renvoyés par l’intégration" />
      <div aria-live="polite" aria-busy={pending}>
        {pending ? (
          <div className="ig-empty">
            <Loader2 size={28} className="ig-spin" aria-hidden="true" />
            <strong>Test d’intégration en cours…</strong>
            <span>{tests.kind === "mcp_health" ? "Appel MCP get_backend_health." : "La première question peut charger le modèle RAG (jusqu’à ~3 min)."}</span>
          </div>
        ) : failure ? (
          <div className="ig-outcome ig-outcome-error" role="alert">
            <ServerCrash size={20} aria-hidden="true" />
            <div><strong>Erreur d’intégration</strong><span>{integrationErrorText(failure)}</span></div>
          </div>
        ) : !result ? (
          <div className="ig-empty">
            <span className="ig-empty-icon" aria-hidden="true"><FlaskConical size={26} /></span>
            <strong>Aucun test pour l’instant</strong>
            <span>Choisissez un type de test puis lancez-le.</span>
          </div>
        ) : result.kind === "mcp_health" ? (
          <>
            <div className={`ig-outcome ${result.response.status === "ok" ? "ig-outcome-ok" : "ig-outcome-error"}`} role={result.response.status === "ok" ? undefined : "alert"}>
              {result.response.status === "ok" ? <CheckCircle2 size={20} aria-hidden="true" /> : <ServerCrash size={20} aria-hidden="true" />}
              <div>
                <strong>{result.response.status === "ok" ? "MCP get_backend_health : succès" : "MCP get_backend_health : échec"}</strong>
                <span>{result.response.status === "ok" ? "Le backend a répondu à travers MCP authentifié." : integrationErrorText(result.response.error)}</span>
              </div>
            </div>
            <dl className="ig-meta">
              <div><dt>Intégration</dt><dd>{KIND_LABEL[result.kind]}</dd></div>
              <div><dt>Statut backend</dt><dd>{result.response.backend_health?.status ?? "Non disponible"}</dd></div>
              <div><dt>Application</dt><dd>{result.response.backend_health?.app ?? "Non disponible"}</dd></div>
              <div><dt>Version</dt><dd>{result.response.backend_health?.version ?? "Non disponible"}</dd></div>
              <div className="ig-meta-wide"><dt>Durée (mesurée par le backend)</dt><dd>{formatDuration(result.response.duration_ms)}</dd></div>
            </dl>
          </>
        ) : (
          <>
            {result.response.status === "ok" && result.response.result ? (
              <div className={`ig-outcome ${result.response.result.blocked ? "ig-outcome-protected" : "ig-outcome-ok"}`}>
                {result.response.result.blocked ? <ShieldCheck size={20} aria-hidden="true" /> : <CheckCircle2 size={20} aria-hidden="true" />}
                <div>
                  <strong>{result.response.result.blocked ? "Réponse reçue · protection activée" : "Réponse EduBourse reçue"}</strong>
                  <span>{KIND_LABEL[result.kind]} a relayé la décision du pipeline canonique, sans la modifier.</span>
                </div>
              </div>
            ) : (
              <div className="ig-outcome ig-outcome-error" role="alert">
                <ServerCrash size={20} aria-hidden="true" />
                <div><strong>{KIND_LABEL[result.kind]} : échec contrôlé</strong><span>{integrationErrorText(result.response.error)}</span></div>
              </div>
            )}
            <p className="ig-question">Question : <q dir={directionFor(guessScript(result.question))}>{result.question}</q></p>
            {result.response.result && (
              <p className="ig-answer" dir={result.response.result.script === "arabic" ? "rtl" : "ltr"}>{result.response.result.answer}</p>
            )}
            <dl className="ig-meta">
              <div><dt>Intégration</dt><dd>{KIND_LABEL[result.kind]}</dd></div>
              <div><dt>Statut</dt><dd>{result.response.result?.status ?? result.response.status}</dd></div>
              <div><dt>Route</dt><dd>{result.response.result?.route ? <code>{result.response.result.route}</code> : "Non disponible"}</dd></div>
              <div><dt>Blocked</dt><dd>{result.response.result?.blocked == null ? "Non disponible" : result.response.result.blocked ? "Oui" : "Non"}</dd></div>
              <div><dt>Langue · script</dt><dd>{result.response.result?.language ? `${result.response.result.language} · ${result.response.result.script}` : "Non disponible"}</dd></div>
              <div>
                <dt>Grounded · citations</dt>
                <dd>
                  {result.response.result
                    ? `${result.response.result.grounded === null ? "N/A" : result.response.result.grounded ? "Oui" : "Non"} · ${result.response.result.citations.length}`
                    : "Non disponible"}
                </dd>
              </div>
              <div className="ig-meta-wide"><dt>Thread ID (transmis au backend)</dt><dd><code>{result.response.thread_id}</code></dd></div>
              <div className="ig-meta-wide"><dt>Durée (mesurée par le backend)</dt><dd>{formatDuration(result.response.duration_ms)}</dd></div>
            </dl>
          </>
        )}
      </div>
    </section>
  );
}

export function HistoryCard({ tests }: { tests: IntegrationTestsApi }) {
  return (
    <section className="ig-panel" aria-labelledby="ig-history-title">
      <IntegrationsPanelHead
        id="ig-history-title"
        icon={History}
        title="Historique des tests de cette session"
        subtitle="Tests lancés depuis cette page uniquement"
        action={
          <button type="button" className="ig-button-ghost ig-button-small" onClick={tests.clearHistory} disabled={tests.history.length === 0}>
            <Trash2 size={14} aria-hidden="true" /> Effacer
          </button>
        }
      />
      {tests.history.length === 0 ? (
        <p className="ig-history-empty">Aucun test dans cette session.</p>
      ) : (
        <ul className="ig-history">
          {tests.history.map((item) => (
            <li key={item.id}>
              <span className="ig-history-time">{new Date(item.at).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
              <span className="ig-history-kind">{KIND_LABEL[item.kind]}</span>
              <span className={`ig-badge ${item.status === "ok" ? "ig-badge-ok" : "ig-badge-ko"}`}>{item.status}</span>
              {item.route && <code>{item.route}</code>}
              {item.preview && <span className="ig-history-preview" dir={directionFor(guessScript(item.preview))}>{item.preview}</span>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function InformationCard() {
  return (
    <section className="ig-panel" aria-labelledby="ig-info-title">
      <IntegrationsPanelHead id="ig-info-title" icon={Info} title="Informations importantes" subtitle="À propos de MCP et n8n dans EduBourse" />
      <ul className="ig-info">
        {INTEGRATION_INFORMATION.map((item) => (
          <li key={item}><CircleCheck size={15} aria-hidden="true" /><span>{item}</span></li>
        ))}
      </ul>
    </section>
  );
}
