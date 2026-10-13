import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  AudioWaveform,
  BrainCircuit,
  CircleCheck,
  FileCheck2,
  FileText,
  Layers,
  Link2,
  MessageCircleMore,
  MessageSquareText,
  Mic,
  Mic2,
  Search,
  ShieldCheck,
  Sparkles,
  UserRound,
  Workflow,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export function RagPanelHead({
  icon: Icon,
  title,
  subtitle,
  glyph = false,
  action,
  id,
}: {
  id?: string;
  icon: LucideIcon;
  title: string;
  subtitle: string;
  glyph?: boolean;
  action?: ReactNode;
}) {
  return (
    <div className="rg-head">
      <span className={glyph ? "rg-head-glyph" : "rg-head-tile"} aria-hidden="true">
        <Icon size={glyph ? 30 : 21} strokeWidth={2.2} />
      </span>
      <div className="rg-head-copy">
        <h2 id={id}>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {action}
    </div>
  );
}

const steps: { icon: LucideIcon; title: string; lines: string[]; tone: string }[] = [
  { icon: Search, title: "Recherche sémantique", lines: ["BGE-M3", "+ ChromaDB"], tone: "green" },
  { icon: FileText, title: "Contexte documentaire", lines: ["Top-k chunks", "approuvés"], tone: "purple" },
  { icon: Sparkles, title: "Génération", lines: ["Réponse basée sur les", "éléments récupérés"], tone: "orange" },
  { icon: ShieldCheck, title: "Grounding", lines: ["Validation des citations", "et de la preuve"], tone: "cyan" },
];

/** Explanatory pipeline: static by design, it never claims a stage is running. */
export function RagPipeline() {
  const navigate = useNavigate();
  return (
    <section className="rg-panel rg-pipeline" aria-labelledby="rg-pipeline-title">
      <RagPanelHead id="rg-pipeline-title" icon={Workflow} glyph title="Comment fonctionne le RAG ?" subtitle="De la question utilisateur à la réponse sourcée" />
      <ol className="rg-flow">
        <li className="rg-step rg-step-end">
          <UserRound size={30} strokeWidth={2.1} aria-hidden="true" className="rg-step-glyph" />
          <strong>Question utilisateur</strong>
          <small>
            Texte ou voix après STT
            <br />
            FR / EN / AR / Darija
          </small>
          <span className="rg-mini">
            <i aria-label="Texte" role="img"><MessageSquareText size={14} /></i>
            <i aria-label="Voix transcrite par Gemini STT" role="img"><Mic size={14} /></i>
          </span>
        </li>
        {steps.map(({ icon: Icon, title, lines, tone }) => (
          <li key={title} className={`rg-step rg-tone-${tone}`}>
            <ArrowRight className="rg-flow-arrow" size={15} aria-hidden="true" />
            <Icon size={30} strokeWidth={2.1} aria-hidden="true" className="rg-step-glyph" />
            <strong>{title}</strong>
            <small>
              {lines[0]}
              <br />
              {lines[1]}
            </small>
          </li>
        ))}
        <li className="rg-step rg-step-end">
          <ArrowRight className="rg-flow-arrow" size={15} aria-hidden="true" />
          <MessageCircleMore size={30} strokeWidth={2.1} aria-hidden="true" className="rg-step-glyph" />
          <strong>Réponse finale</strong>
          <small>
            Réponse sourcée
            <br />
            ou échec fermé
          </small>
          <span className="rg-mini rg-mini-boxed">
            <i aria-label="Réponse" role="img"><FileText size={14} /></i>
            <i aria-label="Citations" role="img"><Link2 size={14} /></i>
            <i aria-label="Validation" role="img"><CircleCheck size={14} /></i>
          </span>
        </li>
      </ol>

      <div className="rg-context">
        <div className="rg-context-title">
          <BrainCircuit size={18} aria-hidden="true" />
          <strong>RAG contextuel : question de suivi dans le même fil</strong>
        </div>
        <ol className="rg-context-steps">
          <li>
            <span>Tour précédent</span>“C’est quoi une action ?”
          </li>
          <li>
            <span>Question de suivi</span>“Et quels sont ses avantages ?”
          </li>
          <li className="rg-context-query">
            <span>Requête de recherche</span>“Quels sont les avantages d’une action ?”
          </li>
        </ol>
        <p className="rg-context-rule">
          <ShieldCheck size={16} aria-hidden="true" />
          La mémoire peut enrichir la requête de recherche, mais les réponses sont toujours fondées
          sur les sources récupérées du corpus approuvé. La mémoire n’est jamais une citation.
        </p>
      </div>

      <div className="rg-voice">
        <div className="rg-voice-copy">
          <div className="rg-context-title">
            <AudioWaveform size={18} aria-hidden="true" />
            <strong>Même moteur RAG pour le texte et la voix</strong>
          </div>
          <p>
            Une question vocale est d’abord transcrite par Gemini STT. Le texte obtenu utilise ensuite
            le même moteur RAG BGE-M3 + ChromaDB, les mêmes sources approuvées et les mêmes
            contrôles de grounding.
          </p>
          {/* Audio stages belong to the Voice pipeline; the RAG engine only ever sees text. */}
          <ol className="rg-voice-path" aria-label="Répartition des étapes entre pipeline vocal et RAG">
            <li className="rg-voice-stage">
              <span>Pipeline Voice</span>Micro → Gemini STT → texte
            </li>
            <li className="rg-voice-shared">
              <span>Moteur RAG partagé (texte uniquement)</span>Analyse → agents → BGE-M3 + ChromaDB → grounding
            </li>
            <li className="rg-voice-stage">
              <span>Pipeline Voice</span>Réponse texte → Gemini TTS → audio
            </li>
          </ol>
        </div>
        <button type="button" className="rg-voice-link" onClick={() => navigate("/voice")}>
          <Mic2 size={16} aria-hidden="true" /> Voir le pipeline Voice-to-Voice <ArrowRight size={15} aria-hidden="true" />
        </button>
      </div>
    </section>
  );
}

const points: { title: string; text: string; icon: LucideIcon }[] = [
  { icon: FileCheck2, title: "Sources approuvées", text: "Documents pédagogiques de l’AMMC" },
  { icon: Search, title: "Recherche sémantique BGE-M3", text: "Vecteurs de dimension 1024" },
  { icon: Layers, title: "ChromaDB comme base vectorielle", text: "Distance cosinus sur les chunks indexés" },
  { icon: Link2, title: "Réponses sourcées", text: "Citations vérifiées contre les extraits" },
  { icon: ShieldCheck, title: "Grounding en échec fermé", text: "Réduction des hallucinations, pas de preuve inventée" },
  { icon: BrainCircuit, title: "Requête contextuelle multilingue", text: "Reformulation FR des questions EN / AR / Darija et de suivi" },
  { icon: AudioWaveform, title: "Compatible Text-to-Text & Voice-to-Voice", text: "Après transcription STT, les interactions vocales réutilisent le même RAG et les mêmes sources vérifiées." },
];

export function RagKeyPoints() {
  return (
    <section className="rg-panel" aria-labelledby="rg-points-title">
      <RagPanelHead id="rg-points-title" icon={ShieldCheck} title="Points clés" subtitle="La qualité et la fiabilité du RAG" />
      <ul className="rg-points">
        {points.map(({ title, text }) => (
          <li key={title}>
            <CircleCheck size={22} strokeWidth={2.4} aria-hidden="true" />
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
