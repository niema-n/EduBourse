import type { ReactNode } from "react";
import { ArrowRight, AudioWaveform, CircleCheck, Info, Languages, ShieldCheck, Star, Workflow } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { MlVoiceTester } from "./MlVoiceTester";

import { KEY_POINTS, LANGUAGE_RULES, PIPELINE_STAGES, VOICE_EXPLAINER, VOICE_STAGES } from "../../data/multilingual";
import type { MlStage } from "../../data/multilingual";

export function MlPanelHead({
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
    <div className="ml-head">
      <span className="ml-head-tile" aria-hidden="true">
        <Icon size={21} strokeWidth={2.2} />
      </span>
      <div className="ml-head-copy">
        <h2 id={id}>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {action}
    </div>
  );
}

/** Static, explanatory flow: it never claims that a stage is currently running. */
function StageFlow({ stages, className, label }: { stages: MlStage[]; className: string; label: string }) {
  return (
    <div className="ml-flow-host">
      <ol className={`ml-flow ${className}`} aria-label={label}>
        {stages.map(({ icon: Icon, title, detail, tone }, index) => (
          <li key={title} className={`ml-stage ml-tone-${tone}`}>
            {index > 0 && <ArrowRight className="ml-flow-arrow" size={14} aria-hidden="true" />}
            <span className="ml-stage-icon" aria-hidden="true">
              <Icon size={22} strokeWidth={2.1} />
            </span>
            <strong>{title}</strong>
            <small>{detail}</small>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function PipelineOverview() {
  return (
    <section className="ml-panel" aria-labelledby="ml-pipeline-title">
      <MlPanelHead
        id="ml-pipeline-title"
        icon={Workflow}
        title="Vue d’ensemble du pipeline multilingue"
        subtitle="De l’entrée utilisateur à la réponse localisée dans la bonne langue"
      />
      <StageFlow stages={PIPELINE_STAGES} className="ml-flow-main" label="Étapes du pipeline multilingue" />
      <div className="ml-notes">
        <p>
          <CircleCheck size={16} aria-hidden="true" />
          Le système conserve la langue de l’utilisateur pour la réponse finale.
        </p>
        <p>
          <ShieldCheck size={16} aria-hidden="true" />
          La mémoire et le routage restent pilotés par le backend.
        </p>
        <span className="ml-lang-pills" aria-label="Langues prises en charge">
          <i className="ml-pill ml-tone-blue">FR</i>
          <i className="ml-pill ml-tone-cyan">EN</i>
          <i className="ml-pill ml-tone-green">AR</i>
          <i className="ml-pill ml-tone-orange">Darija</i>
        </span>
      </div>
    </section>
  );
}

export function VoicePanel() {
  const navigate = useNavigate();
  return (
    <section className="ml-panel ml-voice" aria-labelledby="ml-voice-title">
      <MlPanelHead
        id="ml-voice-title"
        icon={AudioWaveform}
        title="Voice-to-Voice"
        subtitle="Du microphone à la réponse vocale localisée"
      />
      <StageFlow stages={VOICE_STAGES} className="ml-flow-voice" label="Étapes du pipeline Voice-to-Voice" />

      <ul className="ml-voice-explainer">
        {VOICE_EXPLAINER.map(({ title, text }, index) => (
          <li key={title}>
            <span className="ml-voice-index" aria-hidden="true">{index + 1}</span>
            <span>
              <strong>{title}</strong>
              <small>{text}</small>
            </span>
          </li>
        ))}
      </ul>

      <dl className="ml-voice-status">
        <div>
          <dt>Backend</dt>
          <dd><span className="ml-badge ml-badge-green">Connecté à la demande</span> WebSocket <code>/api/v1/voice/live</code></dd>
        </div>
        <div>
          <dt>Interface micro (frontend)</dt>
          <dd><span className="ml-badge ml-badge-green">Disponible</span> Micro PCM 16 kHz · Gemini Live STT · Gemini TTS (voix Kore)</dd>
        </div>
      </dl>

      <MlVoiceTester />

      <div className="ml-voice-actions">
        <button type="button" className="ml-button-outline" onClick={() => navigate("/voice")}>
          Voir la page Voice-to-Voice <ArrowRight size={15} aria-hidden="true" />
        </button>
      </div>
    </section>
  );
}

export function LanguageRules() {
  return (
    <section className="ml-panel" aria-labelledby="ml-rules-title">
      <MlPanelHead
        id="ml-rules-title"
        icon={Languages}
        title="Règles de détection et localisation"
        subtitle="Langue, script attendu et comportement de sortie"
      />
      <div className="ml-rules-host">
        <ul className="ml-rules">
          {LANGUAGE_RULES.map((rule) => (
            <li key={rule.name} className={`ml-rule ml-tone-${rule.tone}`}>
              <div className="ml-rule-top">
                <i className="ml-pill">{rule.code}</i>
                <strong dir={rule.direction}>{rule.name}</strong>
              </div>
              <dl>
                <div>
                  <dt>Script attendu</dt>
                  <dd>{rule.script} · {rule.direction.toUpperCase()}</dd>
                </div>
                <div>
                  <dt>Sortie</dt>
                  <dd dir={rule.outputDir}>{rule.output}</dd>
                </div>
                <div>
                  <dt>Exemple</dt>
                  <dd dir={rule.direction}>« {rule.example} »</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      </div>
      <div className="ml-notes ml-notes-compact">
        <p>
          <Info size={16} aria-hidden="true" />
          La localisation de sortie doit préserver la langue de l’utilisateur.
        </p>
        <p>
          <ShieldCheck size={16} aria-hidden="true" />
          Les réponses du backend restent contrôlées par les politiques de sécurité.
        </p>
      </div>
    </section>
  );
}

export function MlKeyPoints() {
  return (
    <section className="ml-panel" aria-labelledby="ml-points-title">
      <MlPanelHead id="ml-points-title" icon={Star} title="Points clés" subtitle="Les atouts du support multilingue" />
      <ul className="ml-points">
        {KEY_POINTS.map(({ title, text }) => (
          <li key={title}>
            <CircleCheck size={20} strokeWidth={2.4} aria-hidden="true" />
            <span>
              <strong>{title}</strong>
              <small>{text}</small>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
