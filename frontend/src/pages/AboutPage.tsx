import {
  Accessibility, ArrowRight, AudioWaveform, BadgeCheck, BarChart3, BookOpen, Boxes, BrainCircuit, Braces,
  CheckCircle2, Code2, Compass, Container, Cpu, Database, Eye, FileText, Globe2, GraduationCap, Heart,
  HeartHandshake, Info, Landmark, Layers, Lightbulb, MessageSquareText, Mic2, Network, Scale, School,
  Server, Settings2, ShieldCheck, Sparkles, Target, TrendingUp, UserRound, Workflow, Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import {
  FEATURES, LANGUAGES, PILLARS, PIPELINE, PROJECT_FACTS, ROUTES, SCOPE, SECURITY_POINTS, TECHNOLOGIES,
  VALUES, VOICE_FLOW,
} from "../data/about";
import type { TechKey } from "../data/about";

import "../about.css";

const PILLAR_ICONS: Record<string, LucideIcon> = {
  education: GraduationCap,
  trust: ShieldCheck,
  access: Accessibility,
  languages: Globe2,
};

const TECH_ICONS: Record<TechKey, { icon: LucideIcon; tone: string }> = {
  react: { icon: Code2, tone: "cyan" },
  fastapi: { icon: Zap, tone: "green" },
  python: { icon: Braces, tone: "blue" },
  langgraph: { icon: Network, tone: "purple" },
  groq: { icon: Cpu, tone: "orange" },
  gemini: { icon: AudioWaveform, tone: "blue" },
  chroma: { icon: Database, tone: "orange" },
  bge: { icon: Layers, tone: "purple" },
  postgres: { icon: Server, tone: "blue" },
  mcp: { icon: Boxes, tone: "purple" },
  n8n: { icon: Workflow, tone: "pink" },
  docker: { icon: Container, tone: "cyan" },
};

const VALUE_ICONS: Record<string, LucideIcon> = {
  pedagogy: BookOpen,
  transparency: Eye,
  responsibility: Scale,
  accessibility: Accessibility,
  reliability: BadgeCheck,
};

function CardHead({ icon: Icon, title, tone = "blue", id }: { icon: LucideIcon; title: string; tone?: string; id: string }) {
  return (
    <div className="ab-head">
      <span className={`ab-head-icon ab-tone-${tone}`} aria-hidden="true"><Icon size={20} /></span>
      <h2 id={id}>{title}</h2>
    </div>
  );
}

function LinkButton({ to, children, variant = "ghost" }: { to: string; children: ReactNode; variant?: "ghost" | "primary" | "light" }) {
  const navigate = useNavigate();
  return (
    <button type="button" className={`ab-button ab-button-${variant}`} onClick={() => navigate(to)}>
      {children}
    </button>
  );
}

function Flow({ steps, label }: { steps: string[]; label: string }) {
  return (
    <ol className="ab-flow" aria-label={label}>
      {steps.map((step, index) => (
        <li key={step}>
          <span>{step}</span>
          {index < steps.length - 1 && <ArrowRight size={13} aria-hidden="true" />}
        </li>
      ))}
    </ol>
  );
}

/** Decorative CSS illustration: stacked books and a rising chart, no external image. */
function HeroArt() {
  return (
    <div className="ab-art" aria-hidden="true">
      <div className="ab-art-chart">
        {[38, 56, 48, 72, 90].map((height, index) => <i key={index} style={{ height: `${height}%` }} />)}
        <TrendingUp className="ab-art-trend" size={34} />
      </div>
      <div className="ab-books">
        <span>S’INFORMER</span>
        <span>APPRENDRE</span>
        <span>COMPRENDRE</span>
        <span>INVESTIR</span>
      </div>
    </div>
  );
}

export function AboutPage() {
  const facts = PROJECT_FACTS;
  const infoCards: { icon: LucideIcon; tone: string; label: string; title: string; lines: string[] }[] = [
    { icon: UserRound, tone: "blue", label: "Étudiante", title: facts.student, lines: [facts.level, facts.specialization] },
    { icon: School, tone: "purple", label: "Établissement", title: facts.institutionShort, lines: [facts.institution] },
    { icon: FileText, tone: "green", label: "Projet", title: facts.type, lines: [facts.name] },
    { icon: Landmark, tone: "orange", label: "Contexte", title: facts.context.join(" · "), lines: ["Éducation financière & innovation digitale"] },
  ];

  return (
    <div className="about-page">
      <div className="ab-row ab-row-hero">
        <section className="ab-card ab-hero" aria-labelledby="ab-hero-title">
          <div className="ab-hero-copy">
            <div className="ab-hero-brand">
              <span className="ab-hero-mark" aria-hidden="true"><BarChart3 size={34} /></span>
              <div>
                <h2 id="ab-hero-title">EduBourse <em>AI Assistant</em></h2>
                <p>{facts.tagline}</p>
              </div>
            </div>
            <p className="ab-hero-text">
              EduBourse est un assistant intelligent d’éducation financière développé dans le cadre d’un Projet de Fin
              d’Année. Il aide les utilisateurs à mieux comprendre les marchés de capitaux, les instruments financiers
              et les concepts d’investissement grâce à des réponses pédagogiques, multilingues, sourcées et encadrées.
            </p>
            <span className="ab-status"><Sparkles size={14} aria-hidden="true" /> {facts.status}</span>
            <ul className="ab-pillars">
              {PILLARS.map(({ key, title, text }) => {
                const Icon = PILLAR_ICONS[key];
                return (
                  <li key={key}>
                    <Icon size={26} aria-hidden="true" />
                    <strong>{title}</strong>
                    <small dir="auto">{text}</small>
                  </li>
                );
              })}
            </ul>
          </div>
          <HeroArt />
        </section>

        <section className="ab-card ab-mission" aria-label="Mission et vision">
          <article>
            <span className="ab-round ab-tone-pink" aria-hidden="true"><Target size={24} /></span>
            <div>
              <h2>Notre mission</h2>
              <p>
                Rendre l’éducation financière plus accessible, compréhensible et interactive grâce à l’intelligence
                artificielle, tout en conservant un cadre pédagogique, sécurisé et fondé sur des sources approuvées.
              </p>
            </div>
          </article>
          <article>
            <span className="ab-round ab-tone-green" aria-hidden="true"><Lightbulb size={24} /></span>
            <div>
              <h2>Notre vision</h2>
              <p>
                Contribuer à une meilleure culture financière en donnant aux utilisateurs des outils pour comprendre
                les marchés, poser leurs questions et développer progressivement leurs connaissances.
              </p>
            </div>
          </article>
        </section>
      </div>

      <section className="ab-info" aria-label="Informations du projet">
        {infoCards.map(({ icon: Icon, tone, label, title, lines }) => (
          <article key={label} className="ab-card ab-info-card">
            <span className={`ab-info-icon ab-tone-${tone}`} aria-hidden="true"><Icon size={28} /></span>
            <div>
              <h2>{label}</h2>
              <strong>{title}</strong>
              {lines.map((line) => <small key={line}>{line}</small>)}
            </div>
          </article>
        ))}
      </section>

      <div className="ab-row ab-row-three">
        <section className="ab-card" aria-labelledby="ab-features">
          <CardHead icon={Settings2} title="Fonctionnalités principales" id="ab-features" />
          <ul className="ab-checks">
            {FEATURES.map((feature) => (
              <li key={feature}><CheckCircle2 size={17} aria-hidden="true" />{feature}</li>
            ))}
          </ul>
          <h3 className="ab-subhead">Routes du graphe LangGraph</h3>
          <ul className="ab-chips" aria-label="Routes du graphe">
            {ROUTES.map((route) => <li key={route}><code>{route}</code></li>)}
          </ul>
        </section>

        <section className="ab-card" aria-labelledby="ab-tech">
          <CardHead icon={Code2} title="Technologies clés" id="ab-tech" />
          <ul className="ab-tech">
            {TECHNOLOGIES.map(({ key, name, role }) => {
              const { icon: Icon, tone } = TECH_ICONS[key];
              return (
                <li key={key}>
                  <span className={`ab-tech-icon ab-tone-${tone}`} aria-hidden="true"><Icon size={19} /></span>
                  <div>
                    <strong>{name}</strong>
                    <small>{role}</small>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>

        <div className="ab-stack">
          <section className="ab-card" aria-labelledby="ab-values">
            <CardHead icon={Heart} title="Nos valeurs" tone="pink" id="ab-values" />
            <ul className="ab-values">
              {VALUES.map(({ key, title, text }) => {
                const Icon = VALUE_ICONS[key];
                return (
                  <li key={key}>
                    <span className="ab-value-icon" aria-hidden="true"><Icon size={17} /></span>
                    <div>
                      <strong>{title}</strong>
                      <small>{text}</small>
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>
          <section className="ab-card" aria-labelledby="ab-thanks">
            <CardHead icon={HeartHandshake} title="Remerciements" tone="orange" id="ab-thanks" />
            <p className="ab-text">
              Merci aux personnes ayant accompagné, encadré et soutenu la réalisation de ce projet, ainsi qu’aux équipes
              ayant contribué à son cadrage pédagogique et technique.
            </p>
          </section>
        </div>
      </div>

      <div className="ab-row ab-row-three">
        <section className="ab-card" aria-labelledby="ab-archi">
          <CardHead icon={BrainCircuit} title="Architecture responsable" tone="purple" id="ab-archi" />
          <p className="ab-text">
            La logique métier reste centralisée dans le backend EduBourse. Sécurité, contexte conversationnel, routage,
            agents spécialisés, RAG et grounding sont appliqués par le pipeline canonique.
          </p>
          <Flow steps={PIPELINE} label="Pipeline canonique" />
          <LinkButton to="/architecture"><Network size={16} aria-hidden="true" /> Voir l’architecture <ArrowRight size={15} aria-hidden="true" /></LinkButton>
        </section>

        <section className="ab-card" aria-labelledby="ab-voice">
          <CardHead icon={Mic2} title="Une même intelligence, deux interfaces" tone="blue" id="ab-voice" />
          <p className="ab-text">
            Text-to-Text et Voice-to-Voice reposent sur les mêmes règles métier : la voix est transcrite, traitée par le
            même pipeline EduBourse, puis restituée en audio.
          </p>
          <div className="ab-modes">
            <span><MessageSquareText size={16} aria-hidden="true" /> Text-to-Text</span>
            <span><AudioWaveform size={16} aria-hidden="true" /> Voice-to-Voice</span>
          </div>
          <Flow steps={VOICE_FLOW} label="Parcours Voice-to-Voice" />
          <LinkButton to="/voice"><Mic2 size={16} aria-hidden="true" /> Découvrir Voice-to-Voice <ArrowRight size={15} aria-hidden="true" /></LinkButton>
        </section>

        <section className="ab-card" aria-labelledby="ab-lang">
          <CardHead icon={Globe2} title="Langues & sources" tone="green" id="ab-lang" />
          <p className="ab-text"><strong>4 langues métier</strong>, 5 variantes langue / écriture :</p>
          <ul className="ab-langs">
            {LANGUAGES.map(({ label, variants }) => (
              <li key={label}>
                <strong dir="auto">{label}</strong>
                <span>{variants.map((variant) => <code key={variant}>{variant}</code>)}</span>
              </li>
            ))}
          </ul>
          <p className="ab-text ab-rag">
            <Database size={16} aria-hidden="true" />
            Corpus documentaire approuvé et grounding avec citations lorsque applicable.
          </p>
          <LinkButton to="/rag"><Database size={16} aria-hidden="true" /> Voir RAG & Sources <ArrowRight size={15} aria-hidden="true" /></LinkButton>
        </section>
      </div>

      <div className="ab-row ab-row-three">
        <section className="ab-card" aria-labelledby="ab-security">
          <CardHead icon={ShieldCheck} title="Un usage éducatif" tone="green" id="ab-security" />
          <p className="ab-text">EduBourse est conçu pour l’éducation financière, pas pour le conseil en investissement.</p>
          <ul className="ab-checks ab-checks-compact">
            {SECURITY_POINTS.map((point) => (
              <li key={point}><ShieldCheck size={16} aria-hidden="true" />{point}</li>
            ))}
          </ul>
        </section>

        <section className="ab-card" aria-labelledby="ab-frame">
          <CardHead icon={GraduationCap} title="Cadre du projet" tone="purple" id="ab-frame" />
          <p className="ab-text">
            Ce projet a été réalisé dans le cadre d’un Projet de Fin d’Année en 4ème année IA & Sciences des Données à
            l’EMSI, autour des usages de l’intelligence artificielle appliqués à l’éducation financière.
          </p>
          <p className="ab-text">
            Le projet s’inscrit dans le contexte de l’École de la Bourse et de la Bourse de Casablanca, et de
            l’écosystème marocain des marchés de capitaux.
          </p>
          <p className="ab-not">
            <Info size={15} aria-hidden="true" />
            EduBourse n’est ni un assistant généraliste, ni un conseiller en investissement, ni un gestionnaire de
            portefeuille, ni un robot de trading.
          </p>
        </section>

        <section className="ab-card" aria-labelledby="ab-scope">
          <CardHead icon={Compass} title="Périmètre" tone="orange" id="ab-scope" />
          <ul className="ab-scope">
            {SCOPE.map((item) => <li key={item}>{item}</li>)}
          </ul>
          <LinkButton to="/validation"><BadgeCheck size={16} aria-hidden="true" /> Voir la validation du projet <ArrowRight size={15} aria-hidden="true" /></LinkButton>
        </section>
      </div>

      <section className="ab-cta" aria-labelledby="ab-cta-title">
        <div>
          <h2 id="ab-cta-title">Explorer EduBourse</h2>
          <p>Posez une question, parcourez l’architecture ou consultez les preuves de validation du projet.</p>
        </div>
        <div className="ab-cta-actions">
          <LinkButton to="/assistant" variant="light"><MessageSquareText size={17} aria-hidden="true" /> Tester l’Assistant</LinkButton>
          <LinkButton to="/architecture" variant="primary"><Network size={17} aria-hidden="true" /> Voir l’Architecture</LinkButton>
          <LinkButton to="/validation" variant="primary"><BadgeCheck size={17} aria-hidden="true" /> Voir la Validation</LinkButton>
        </div>
      </section>
    </div>
  );
}
