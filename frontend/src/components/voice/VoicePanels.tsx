import type { ReactNode } from "react";
import { ArrowRight, CircleCheck, Info, Lightbulb, SlidersHorizontal, Workflow } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

import { VOICE_BACKEND_FACTS, VOICE_INFORMATION, VOICE_PIPELINE } from "../../data/voice";

export function VoicePanelHead({
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
    <div className="vc-head">
      <span className="vc-head-tile" aria-hidden="true">
        <Icon size={21} strokeWidth={2.2} />
      </span>
      <div className="vc-head-copy">
        <h2 id={id}>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {action}
    </div>
  );
}

/** Explanatory flow of the real backend path; it never claims a stage is running now. */
export function VoicePipeline() {
  return (
    <section className="vc-panel" aria-labelledby="vc-pipeline-title">
      <VoicePanelHead
        id="vc-pipeline-title"
        icon={Workflow}
        title="Pipeline Voice-to-Voice"
        subtitle="Du microphone à la réponse vocale localisée — le même pipeline métier que le texte"
      />
      <div className="vc-flow-host">
        <ol className="vc-flow" aria-label="Étapes du pipeline Voice-to-Voice">
          {VOICE_PIPELINE.map(({ icon: Icon, title, detail, tone }, index) => (
            <li key={title} className={`vc-stage vc-tone-${tone}`}>
              {index > 0 && <ArrowRight className="vc-flow-arrow" size={14} aria-hidden="true" />}
              <span className="vc-stage-icon" aria-hidden="true">
                <Icon size={21} strokeWidth={2.1} />
              </span>
              <strong>
                <span className="vc-stage-index">{index + 1}.</span> {title}
              </strong>
              <small>{detail}</small>
            </li>
          ))}
        </ol>
      </div>
      <p className="vc-shared-note">
        <CircleCheck size={16} aria-hidden="true" />
        Seules les étapes 1, 2, 10 et 11 sont propres à la voix. Les étapes 3 à 9 sont exactement celles de l’Assistant texte.
      </p>
    </section>
  );
}

export const PLAYBACK_RATES = [0.75, 1, 1.25, 1.5] as const;

export function VoiceSettings({ rate, onRate }: { rate: number; onRate: (rate: number) => void }) {
  return (
    <section className="vc-panel" aria-labelledby="vc-settings-title">
      <VoicePanelHead
        id="vc-settings-title"
        icon={SlidersHorizontal}
        title="Paramètres voix"
        subtitle="Configuration réelle du backend et lecture locale"
      />
      <dl className="vc-settings">
        <div>
          <dt>Voix de synthèse</dt>
          <dd>
            {VOICE_BACKEND_FACTS.ttsVoice} <small>· {VOICE_BACKEND_FACTS.ttsProvider}, fixée côté backend</small>
          </dd>
        </div>
        <div>
          <dt>Langue de sortie</dt>
          <dd>
            Détection automatique <small>· même langue et même script que votre question</small>
          </dd>
        </div>
      </dl>
      <label className="vc-rate">
        <span>Vitesse de réécoute</span>
        <select value={rate} onChange={(event) => onRate(Number(event.target.value))}>
          {PLAYBACK_RATES.map((value) => (
            <option key={value} value={value}>{value.toFixed(2).replace(/0$/, "")}x</option>
          ))}
        </select>
        <small>Réglage du navigateur pour la réécoute ; il ne modifie pas la synthèse du backend.</small>
      </label>
    </section>
  );
}

export function VoiceInformation() {
  return (
    <section className="vc-panel" aria-labelledby="vc-info-title">
      <VoicePanelHead id="vc-info-title" icon={Info} title="Informations importantes" subtitle="Ce qui se passe réellement" />
      <ul className="vc-info">
        {VOICE_INFORMATION.map((item) => (
          <li key={item}>
            <CircleCheck size={16} aria-hidden="true" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
      <div className="vc-links">
        <Link to="/multilingue" className="vc-link">Voir Multilingue <ArrowRight size={14} aria-hidden="true" /></Link>
        <Link to="/assistant" className="vc-link">Voir l’Assistant texte <ArrowRight size={14} aria-hidden="true" /></Link>
      </div>
    </section>
  );
}

export function VoiceTip() {
  return (
    <aside className="vc-tip">
      <Lightbulb size={20} aria-hidden="true" />
      <div>
        <strong>Conseil d’utilisation</strong>
        <p>Cliquez sur le micro, posez une question courte, puis cliquez sur « Arrêter ». La langue est détectée automatiquement.</p>
      </div>
    </aside>
  );
}
