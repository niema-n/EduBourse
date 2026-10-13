import { useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import {
  Activity, ArrowRight, AudioWaveform, BarChart3, Bell, BookOpen, Bot, BrainCircuit,
  ChartNoAxesColumnIncreasing, CheckCircle2, ChevronDown, CircleCheckBig, CircleHelp,
  CircleUserRound, Code2, Compass, Database, DatabaseBackup, ExternalLink, FileAudio,
  FileCheck2, Globe2, GraduationCap, Headphones, House, Info, Link2, LockKeyhole, Menu,
  MessageCircle, MessagesSquare, Mic2, PanelLeftClose, PanelLeftOpen, RotateCcw, Search,
  Send, ServerCog, ShieldCheck, TriangleAlert, Trophy, Users, UsersRound, Volume2,
  Workflow, X,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { PanelHead } from "./components/PanelHead";
import type { Tone } from "./components/PanelHead";
import { ChatError, createThreadId, sendChatMessage } from "./services/chat";
import type { ChatCitation } from "./types/chat";
import { AgentsPage } from "./pages/AgentsPage";
import { ArchitecturePage } from "./pages/ArchitecturePage";
import { MultilingualPage } from "./pages/MultilingualPage";
import { IntegrationsPage } from "./pages/IntegrationsPage";
import { SecurityPage } from "./pages/SecurityPage";
import { VoicePage } from "./pages/VoicePage";
import { RagPage } from "./pages/RagPage";
import { AssistantPage } from "./pages/AssistantPage";
import { ValidationPage } from "./pages/ValidationPage";
import { AboutPage } from "./pages/AboutPage";

const navItems: { label: string; path: string; icon: LucideIcon }[] = [
  { label: "Tableau de bord", path: "/dashboard", icon: House },
  { label: "Assistant IA", path: "/assistant", icon: MessageCircle },
  { label: "Agents", path: "/agents", icon: Users },
  { label: "Architecture", path: "/architecture", icon: Workflow },
  { label: "RAG & Sources", path: "/rag", icon: Database },
  { label: "Multilingue", path: "/multilingue", icon: Globe2 },
  { label: "Voice-to-Voice", path: "/voice", icon: AudioWaveform },
  { label: "Sécurité", path: "/security", icon: ShieldCheck },
  { label: "MCP & n8n", path: "/integrations", icon: Link2 },
  { label: "Validation", path: "/validation", icon: CircleCheckBig },
  { label: "À propos", path: "/about", icon: Info },
];

const kpis: { icon: LucideIcon; mark: LucideIcon; label: string; value: string; detail: string; tone: Tone; pulse?: boolean }[] = [
  { icon: Code2, mark: BarChart3, label: "Routes supportées", value: "10", detail: "Toutes les routes opérationnelles", tone: "blue" },
  { icon: Globe2, mark: Users, label: "Langues", value: "FR / EN / AR / Darija", detail: "4 langues supportées", tone: "blue" },
  { icon: Database, mark: FileCheck2, label: "RAG Index", value: "353 embeddings", detail: "Documents indexés et prêts", tone: "cyan" },
  { icon: Activity, mark: Activity, label: "Statut système", value: "Healthy", detail: "Tous les services opérationnels", tone: "green", pulse: true },
];

const architectureStages: { icon: LucideIcon; title: string; lines: [string, string]; tone: Tone; highlight?: boolean }[] = [
  { icon: ShieldCheck, title: "Sécurité", lines: ["Filtrage", "et protection"], tone: "green" },
  { icon: Database, title: "Memory", lines: ["Contexte", "de session"], tone: "blue" },
  { icon: BrainCircuit, title: "Supervisor", lines: ["Routage intelligent", "(LangGraph)"], tone: "purple", highlight: true },
  { icon: UsersRound, title: "Agent", lines: ["Agent spécialisé", "(métier)"], tone: "cyan" },
  { icon: FileCheck2, title: "Grounding", lines: ["RAG & sources", "fiables"], tone: "green" },
];

const voiceSteps: { icon: LucideIcon; label: string; tone: Tone }[] = [
  { icon: Mic2, label: "Microphone", tone: "blue" },
  { icon: FileAudio, label: "STT", tone: "blue" },
  { icon: Globe2, label: "Multilingue", tone: "cyan" },
  { icon: ShieldCheck, label: "Sécurité", tone: "green" },
  { icon: BrainCircuit, label: "LangGraph", tone: "purple" },
  { icon: UsersRound, label: "Agent", tone: "cyan" },
  { icon: Database, label: "RAG", tone: "orange" },
  { icon: FileCheck2, label: "Grounding", tone: "green" },
  { icon: Volume2, label: "TTS", tone: "blue" },
  { icon: AudioWaveform, label: "Audio", tone: "red" },
];

const agents: { icon: LucideIcon; label: string; tone: Tone }[] = [
  { icon: GraduationCap, label: "Pédagogie", tone: "blue" },
  { icon: BookOpen, label: "Formation", tone: "green" },
  { icon: ChartNoAxesColumnIncreasing, label: "CISI", tone: "cyan" },
  { icon: CircleHelp, label: "Quiz", tone: "purple" },
  { icon: Trophy, label: "Championnat", tone: "orange" },
  { icon: Compass, label: "Orientation", tone: "blue" },
  { icon: Headphones, label: "Support", tone: "green" },
  { icon: ShieldCheck, label: "Sécurité", tone: "cyan" },
  { icon: TriangleAlert, label: "Out of Domain", tone: "red" },
  { icon: RotateCcw, label: "Fallback", tone: "red" },
];

const integrations: { icon: LucideIcon; name: string; detail: string; status: string; tone: Tone }[] = [
  { icon: ServerCog, name: "Backend", detail: "FastAPI", status: "Opérationnel", tone: "blue" },
  { icon: Link2, name: "MCP", detail: "Model Context Protocol", status: "Connecté", tone: "purple" },
  { icon: Workflow, name: "n8n", detail: "Automatisation", status: "Connecté", tone: "red" },
  { icon: Database, name: "ChromaDB", detail: "Vector Database", status: "Opérationnel", tone: "orange" },
  { icon: DatabaseBackup, name: "PostgreSQL", detail: "Base de données", status: "Opérationnel", tone: "cyan" },
];

const validations = ["MCP sécurisé", "DNS rebinding protection", "Grounded réponses", "Multilingue validé"];

const dashboardInitialQuestion = "C'est quoi une action ?";
const dashboardInitialAnswer =
  "Une action est un titre de propriété qui représente une part du capital d'une entreprise. En achetant une action, vous devenez actionnaire, c'est-à-dire copropriétaire d'une partie de l'entreprise. Vous pouvez ainsi bénéficier d'une partie de ses bénéfices (via les dividendes) et d'une plus-value si le prix de l'action augmente.";

const dashboardInitialSources: Array<Pick<ChatCitation, "title" | "page_start" | "page_end">> = [
  { title: "Bourse pour les débutants", page_start: 0, page_end: 0 },
  { title: "AMF - Les instruments financiers", page_start: 0, page_end: 0 },
  { title: "Investopedia (FR)", page_start: 0, page_end: 0 },
];

const pageLabels = Object.fromEntries(navItems.map(({ path, label }) => [path, label]));

const pageSubtitles: Record<string, string> = {
  "/assistant": "Assistant éducatif multilingue connecté au backend EduBourse",
  "/agents": "Vue détaillée des agents métier et de l’orchestration",
  "/architecture": "Vue d'ensemble de l'architecture technique et du flux de traitement",
  "/rag": "Des connaissances fiables, vérifiées et utilisées pour sourcer les réponses",
  "/multilingue": "Détection linguistique, normalisation, réponses localisées et parcours voice-to-voice.",
  "/voice": "Parlez naturellement, dans votre langue. Une conversation vocale intelligente, multilingue et sécurisée.",
  "/security": "Des réponses éducatives, sûres et encadrées pour l'éducation financière.",
  "/integrations": "Intégrations, outils et automatisations au service du pipeline EduBourse.",
  "/validation": "Preuves, tests et vérifications du projet EduBourse.",
  "/about": "Un assistant intelligent au service de l'éducation financière et de la compréhension des marchés de capitaux.",
};

/** Pages with their own layout: excluded from placeholders and titled with the brand. */
const BUILT_PAGES = ["/assistant", "/agents", "/architecture", "/rag", "/multilingue", "/voice", "/security", "/integrations", "/validation", "/about"];

const PAGE_CLASSES: Record<string, string> = {
  "/assistant": "page-assistant",
  "/agents": "page-agents",
  "/architecture": "page-architecture",
  "/rag": "page-rag",
  "/multilingue": "page-multilingual",
  "/voice": "page-voice",
  "/security": "page-security",
  "/integrations": "page-integrations",
  "/validation": "page-validation",
  "/about": "page-about",
};

const PAGE_KICKERS: Record<string, string> = {
  "/rag": "RAG & Sources",
  "/multilingue": "Multilingue",
  "/voice": "Voice-to-Voice",
  "/security": "Sécurité",
  "/integrations": "MCP & n8n",
  "/validation": "Validation",
  "/about": "À propos",
};

/* ---------------- shared panels (dashboard + presentation) ---------------- */

function KpiSection() {
  return (
    <section className="kpi-grid" aria-label="Indicateurs du projet">
      {kpis.map(({ icon: Icon, mark: Mark, label, value, detail, tone, pulse }) => (
        <article className="kpi-card" key={label}>
          <span className={`kpi-icon tone-${tone}`}><Icon size={26} /></span>
          <div className="kpi-copy">
            <span className="kpi-label">{label}</span>
            <strong className="kpi-value">{value}</strong>
            <small>{detail}</small>
          </div>
          {pulse
            ? <span className="kpi-pulse" aria-hidden="true" />
            : <Mark className="kpi-mark" size={22} aria-hidden="true" />}
        </article>
      ))}
    </section>
  );
}

function AssistantPanel() {
  const [question, setQuestion] = useState("");
  const [lastQuestion, setLastQuestion] = useState(dashboardInitialQuestion);
  const [answer, setAnswer] = useState(dashboardInitialAnswer);
  const [route, setRoute] = useState("pedagogie");
  const [citations, setCitations] = useState<Array<Pick<ChatCitation, "title" | "page_start" | "page_end">>>(dashboardInitialSources);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const threadId = useRef(createThreadId());
  const canSend = question.trim().length > 0;
  const submitQuestion = async () => {
    const text = question.trim();
    if (!text || pending) return;
    setPending(true);
    setError(null);
    setLastQuestion(text);
    try {
      const { response } = await sendChatMessage({ message: text, thread_id: threadId.current });
      setAnswer(response.answer);
      setRoute(response.route);
      setCitations(
        response.citations.length > 0
          ? response.citations.slice(0, 3).map(({ title, page_start, page_end }) => ({ title, page_start, page_end }))
          : [],
      );
      setQuestion("");
    } catch (caught) {
      setError(
        caught instanceof ChatError && caught.kind === "timeout"
          ? "La réponse prend trop de temps. Réessayez dans un instant."
          : "Impossible de joindre l'assistant pour le moment.",
      );
      setCitations([]);
    } finally {
      setPending(false);
    }
  };
  const now = new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  return (
    <section className="panel assistant-panel">
      <PanelHead
        icon={MessagesSquare}
        title="Assistant IA"
        subtitle="Posez vos questions sur la bourse, l'investissement et la finance"
        action={<span className="route-badge"><GraduationCap size={15} /> Route : {route}</span>}
      />

      <div className="chat">
        <div className="chat-row user">
          <div className="bubble user-bubble">{lastQuestion}</div>
          <span className="chat-avatar user-avatar"><CircleUserRound size={20} /></span>
        </div>
        <div className="chat-meta right"><span>{now}</span></div>

        <div className="chat-row bot">
          <span className="chat-avatar bot-avatar"><Bot size={20} /></span>
          <div className="bubble bot-bubble">
            {pending ? "Recherche de la meilleure réponse..." : error ?? answer}
          </div>
        </div>
        <div className="chat-meta between"><span>{now}</span><span>{now}</span></div>

        {citations.length > 0 && !error && (
          <div className="sources-row">
            <span className="sources-label">Sources :</span>
            {citations.map(({ title, page_start, page_end }, index) => (
              <span className="source-chip" key={`${title}-${index}`}>
                <i>{index + 1}</i>
                {title}
                {page_start > 0 && <small>{page_start === page_end ? `p. ${page_start}` : `p. ${page_start}-${page_end}`}</small>}
              </span>
            ))}
          </div>
        )}
      </div>

      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          submitQuestion();
        }}
      >
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Posez une autre question..."
          aria-label="Votre question"
        />
        <button type="submit" className="send-button" aria-label="Envoyer la question" disabled={!canSend || pending}>
          {pending ? <RotateCcw size={18} className="spin" /> : <Send size={18} />}
        </button>
      </form>
    </section>
  );
}

function ArchitecturePanel() {
  return (
    <section className="panel">
      <PanelHead
        icon={BrainCircuit}
        title="Architecture LangGraph & Routage des agents"
        subtitle="Un système multi-agents orchestré et sécurisé"
        action={<Link to="/architecture" className="ghost-link">Voir détail <ArrowRight size={15} /></Link>}
      />
      <div className="stage-flow">
        {architectureStages.map(({ icon: Icon, title, lines, tone, highlight }, index) => (
          <div className="stage-wrap" key={title}>
            <div className={`stage ${highlight ? "stage-highlight" : ""}`}>
              <span className={`stage-icon tone-${tone}`}><Icon size={22} /></span>
              <strong>{title}</strong>
              <small>{lines[0]}<br />{lines[1]}</small>
            </div>
            {index < architectureStages.length - 1 && <ArrowRight className="stage-arrow" size={16} />}
          </div>
        ))}
      </div>
    </section>
  );
}

function VoicePanel() {
  return (
    <section className="panel">
      <PanelHead
        icon={Mic2}
        title="Pipeline Voice-to-Voice"
        subtitle="De la voix à la voix, en temps réel et multilingue"
        action={<Link to="/voice" className="ghost-link">Voir détail <ArrowRight size={15} /></Link>}
      />
      <div className="voice-flow">
        {voiceSteps.map(({ icon: Icon, label, tone }, index) => (
          <div className="voice-wrap" key={label}>
            <div className="voice-step">
              <span className={`voice-icon tone-${tone}`}><Icon size={20} /></span>
              <small>{label}</small>
            </div>
            {index < voiceSteps.length - 1 && <ArrowRight className="voice-arrow" size={14} />}
          </div>
        ))}
      </div>
    </section>
  );
}

function AgentsPanel() {
  return (
    <section className="panel">
      <PanelHead icon={Users} title="Agents spécialisés" subtitle="8 agents métiers + 2 cas particuliers" />
      <div className="agent-grid">
        {agents.map(({ icon: Icon, label, tone }) => (
          <div className={`agent-tile tone-${tone}`} key={label}>
            <span className="agent-icon"><Icon size={22} /></span>
            <strong>{label}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

function IntegrationsPanel() {
  return (
    <section className="panel">
      <PanelHead icon={Link2} title="Intégrations & Infrastructure" subtitle="Services et outils connectés" />
      <div className="infra-grid">
        {integrations.map(({ icon: Icon, name, detail, status, tone }) => (
          <div className="infra-card" key={name}>
            <span className={`infra-icon tone-${tone}`}><Icon size={20} /></span>
            <strong>{name}</strong>
            <small>{detail}</small>
            <span className="infra-status"><CheckCircle2 size={13} /> {status}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function ValidationPanel() {
  return (
    <section className="panel">
      <PanelHead icon={CircleCheckBig} tone="green" title="Validation" subtitle="Tests de sécurité et de qualité" />
      <ul className="validation-list">
        {validations.map((label) => (
          <li key={label}>
            <span><CheckCircle2 size={16} /> {label}</span>
            <em><CheckCircle2 size={13} /> Validé</em>
          </li>
        ))}
      </ul>
      <div className="validation-banner">
        <CheckCircle2 size={18} />
        <div>
          <strong>Tous les tests de validation sont passés avec succès&nbsp;!</strong>
          <small>Plateforme prête pour la démonstration.</small>
        </div>
      </div>
    </section>
  );
}

/* ---------------- dashboard ---------------- */

function Dashboard() {
  return (
    <div className="dashboard">
      <KpiSection />
      <div className="grid-top">
        <AssistantPanel />
        <div className="right-column">
          <ArchitecturePanel />
          <VoicePanel />
        </div>
      </div>
      <div className="grid-bottom">
        <AgentsPanel />
        <IntegrationsPanel />
        <ValidationPanel />
      </div>
    </div>
  );
}

/* ---------------- command palette ---------------- */

type SearchEntry = { label: string; group: string; hint: string; icon: LucideIcon; path: string };

const searchIndex: SearchEntry[] = [
  ...navItems.map(({ label, path, icon }) => ({ label, group: "Navigation", hint: "Ouvrir la page", icon, path })),
  ...agents.map(({ label, icon }) => ({ label, group: "Agents spécialisés", hint: "Route métier", icon, path: "/agents" })),
  ...architectureStages.map(({ title, icon, lines }) => ({ label: title, group: "Architecture", hint: `${lines[0]} ${lines[1]}`, icon, path: "/architecture" })),
  ...voiceSteps.map(({ label, icon }) => ({ label, group: "Pipeline Voice-to-Voice", hint: "Étape du pipeline", icon, path: "/voice" })),
  ...integrations.map(({ name, detail, icon }) => ({ label: name, group: "Intégrations", hint: detail, icon, path: "/integrations" })),
  ...kpis.map(({ label, value, icon }) => ({ label, group: "Indicateurs", hint: value, icon, path: "/dashboard" })),
];

/** Fold accents/case while keeping a map back to the original character offsets. */
function fold(value: string) {
  let folded = "";
  const map: number[] = [];
  for (let index = 0; index < value.length; index += 1) {
    const piece = value[index].normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    for (let step = 0; step < piece.length; step += 1) map.push(index);
    folded += piece;
  }
  map.push(value.length);
  return { folded, map };
}

function Highlight({ text, query }: { text: string; query: string }) {
  const needle = fold(query.trim()).folded;
  if (!needle) return <>{text}</>;
  const { folded, map } = fold(text);
  const at = folded.indexOf(needle);
  if (at < 0) return <>{text}</>;
  const start = map[at];
  const end = map[at + needle.length];
  return (
    <>
      {text.slice(0, start)}
      <mark>{text.slice(start, end)}</mark>
      {text.slice(end)}
    </>
  );
}

function SearchPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const results = useMemo(() => {
    const needle = fold(query.trim()).folded;
    if (!needle) return searchIndex.filter((entry) => entry.group === "Navigation");
    return searchIndex.filter((entry) => fold(`${entry.label} ${entry.group} ${entry.hint}`).folded.includes(needle));
  }, [query]);

  const groups = useMemo(() => {
    const out: { group: string; items: { entry: SearchEntry; index: number }[] }[] = [];
    results.forEach((entry, index) => {
      const last = out[out.length - 1];
      if (last && last.group === entry.group) last.items.push({ entry, index });
      else out.push({ group: entry.group, items: [{ entry, index }] });
    });
    return out;
  }, [results]);

  useEffect(() => { setActive(0); }, [query]);

  useEffect(() => {
    if (!open) return undefined;
    setQuery("");
    setActive(0);
    const focusTimer = window.setTimeout(() => inputRef.current?.focus(), 20);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.clearTimeout(focusTimer);
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  useEffect(() => {
    listRef.current?.querySelector(".palette-item.active")?.scrollIntoView({ block: "nearest" });
  }, [active, results.length]);

  if (!open) return null;

  const choose = (entry: SearchEntry) => {
    onClose();
    navigate(entry.path);
  };

  const onKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((value) => (results.length ? (value + 1) % results.length : 0));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((value) => (results.length ? (value - 1 + results.length) % results.length : 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (results[active]) choose(results[active]);
    } else if (event.key === "Escape") {
      event.preventDefault();
      onClose();
    }
  };

  return (
    <div className="palette-backdrop" onMouseDown={onClose}>
      <div
        className="palette"
        role="dialog"
        aria-modal="true"
        aria-label="Rechercher une fonctionnalité"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="palette-search">
          <Search size={19} />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Rechercher une page, un agent, un service..."
            aria-label="Rechercher une fonctionnalité"
          />
          <button className="palette-close" onClick={onClose} aria-label="Fermer la recherche"><X size={17} /></button>
        </div>

        <div className="palette-results" ref={listRef}>
          {results.length === 0 ? (
            <div className="palette-empty">
              <Search size={26} />
              <strong>Aucun résultat pour «&nbsp;{query.trim()}&nbsp;»</strong>
              <small>Essayez « agents », « RAG », « sécurité » ou « voice ».</small>
            </div>
          ) : (
            groups.map(({ group, items }) => (
              <div className="palette-group" key={group}>
                <p className="palette-group-title">{group}</p>
                {items.map(({ entry, index }) => (
                  <button
                    key={`${group}-${entry.label}`}
                    className={`palette-item ${index === active ? "active" : ""}`}
                    onMouseEnter={() => setActive(index)}
                    onClick={() => choose(entry)}
                  >
                    <span className="palette-item-icon"><entry.icon size={17} /></span>
                    <span className="palette-item-copy">
                      <strong><Highlight text={entry.label} query={query} /></strong>
                      <small>{entry.hint}</small>
                    </span>
                    <ArrowRight size={15} className="palette-item-go" />
                  </button>
                ))}
              </div>
            ))
          )}
        </div>

        <div className="palette-footer">
          <span><kbd>↑</kbd><kbd>↓</kbd> naviguer</span>
          <span><kbd>↵</kbd> ouvrir</span>
          <span><kbd>Échap</kbd> fermer</span>
          <span className="palette-count">{results.length} résultat{results.length > 1 ? "s" : ""}</span>
        </div>
      </div>
    </div>
  );
}

/* ---------------- shell ---------------- */

function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const { pathname } = useLocation();
  const isDashboard = pathname === "/" || pathname === "/dashboard";
  const pageTitle = pageLabels[pathname] ?? "Tableau de bord";

  useEffect(() => {
    const onKey = (event: globalThis.KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen((value) => !value);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      {mobileOpen && <button className="scrim" aria-label="Fermer le menu" onClick={() => setMobileOpen(false)} />}

      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <span className="brand-mark brand-mark-logo">
            <img src="/logo-bourse-casablanca.svg" alt="" aria-hidden="true" />
          </span>
          <span className="brand-copy">
            <strong>EduBourse</strong>
            <em>AI Assistant</em>
            <small>Apprendre aujourd&apos;hui,<br />investir demain.</small>
          </span>
          <button className="icon-button mobile-close" aria-label="Fermer le menu" onClick={() => setMobileOpen(false)}>
            <X size={20} />
          </button>
        </div>

        <nav className="main-nav" aria-label="Navigation principale">
          {navItems.map(({ label, path, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
              onClick={() => setMobileOpen(false)}
            >
              <Icon size={20} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-promo">
            <span className="promo-art"><BarChart3 size={44} /></span>
            <strong>L&apos;éducation financière pour un avenir meilleur.</strong>
          </div>
          <div className="sidebar-meta">
            <strong>EduBourse AI Assistant</strong>
          </div>
          <button className="collapse-button" onClick={() => setCollapsed((value) => !value)}>
            {collapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
            <span>{collapsed ? "Ouvrir" : "Réduire"}</span>
          </button>
        </div>
      </aside>

      <div className={`main-area ${PAGE_CLASSES[pathname] ?? ""}`}>
        <header className="topbar">
          <div className="topbar-leading">
            <button className="icon-button menu-trigger" aria-label="Ouvrir le menu" onClick={() => setMobileOpen(true)}>
              <Menu size={22} />
            </button>
            <div>
              <h1>{isDashboard || (BUILT_PAGES.includes(pathname) && pathname !== "/assistant")
                ? <>EduBourse <em>AI Assistant</em></>
                : pathname === "/assistant" ? <>Assistant <em>IA</em></> : pageTitle}</h1>
              {isDashboard
                ? <p className="topbar-subtitle">Plateforme d&apos;éducation financière multilingue pilotée par IA</p>
                : pageSubtitles[pathname] && (
                  <>
                    {PAGE_KICKERS[pathname] && <p className="topbar-kicker">{PAGE_KICKERS[pathname]}</p>}
                    <p className="topbar-subtitle">{pageSubtitles[pathname]}</p>
                  </>
                )}
            </div>
          </div>

          <div className="topbar-trailing">
            <div className="topbar-actions">
              <button
                className="search-control"
                onClick={() => setPaletteOpen(true)}
                aria-label="Rechercher une fonctionnalité"
                aria-haspopup="dialog"
              >
                <Search size={17} />
                <span>Rechercher une fonctionnalité...</span>
                <kbd>⌘ K</kbd>
              </button>
              <button className="icon-button notification-button" aria-label="Notifications">
                <Bell size={21} />
                <i />
              </button>
              <div className="profile" aria-label="Profil EduBourse">
                <span className="profile-avatar">NS</span>
                <span className="profile-copy">
                  <strong>Niema Nassime</strong>
                  <small>Étudiant PFA</small>
                </span>
                <ChevronDown size={16} />
              </div>
            </div>
            <p className="topbar-quote">
              <span>&ldquo;Des connaissances <strong>d&apos;aujourd&apos;hui</strong></span>
              <span>pour une liberté financière demain.&rdquo;</span>
            </p>
          </div>
        </header>

        <main className="content">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/assistant" element={<AssistantPage />} />
            <Route path="/agents" element={<AgentsPage />} />
            <Route path="/architecture" element={<ArchitecturePage />} />
            <Route path="/rag" element={<RagPage />} />
            <Route path="/multilingue" element={<MultilingualPage />} />
            <Route path="/voice" element={<VoicePage />} />
            <Route path="/security" element={<SecurityPage />} />
            <Route path="/integrations" element={<IntegrationsPage />} />
            <Route path="/validation" element={<ValidationPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/a-propos" element={<Navigate to="/about" replace />} />
            {/* English/French aliases kept so older links keep working. */}
            <Route path="/securite" element={<Navigate to="/security" replace />} />
            {/* Former sidebar path, kept so existing links keep working. */}
            <Route path="/multilingual" element={<Navigate to="/multilingue" replace />} />
            {navItems.slice(1).filter(({ path }) => !BUILT_PAGES.includes(path)).map(({ path, label, icon: Icon }) => (
              <Route key={path} path={path} element={<PlaceholderPage title={label} icon={Icon} />} />
            ))}
          </Routes>
        </main>

        <footer className="app-footer">
          <span><strong>EduBourse AI Assistant</strong> — Une IA au service de votre culture financière</span>
          <span>Apprendre &nbsp;·&nbsp; Comprendre &nbsp;·&nbsp; Investir &nbsp;·&nbsp; Réussir</span>
        </footer>
      </div>

      <SearchPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  );
}

function PlaceholderPage({ title, icon: Icon }: { title: string; icon: LucideIcon }) {
  return (
    <section className="placeholder-page">
      <div className="placeholder-icon"><Icon size={30} /></div>
      <p className="eyebrow">EduBourse workspace</p>
      <h2>{title}</h2>
      <p className="placeholder-copy">Cette section sera développée dans la prochaine phase.</p>
      <div className="placeholder-card">
        <LockKeyhole size={17} />
        <span>Le périmètre actuel reste volontairement en lecture seule.</span>
      </div>
      <Link to="/dashboard" className="button-link">Retour au tableau de bord <ArrowRight size={16} /></Link>
    </section>
  );
}

export default function App() {
  return <AppShell />;
}
