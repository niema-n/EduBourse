import {
  AlertTriangle, ArrowRight, AudioWaveform, BadgeCheck, BarChart3, CheckCircle2, CircleDashed, Database,
  FlaskConical, Globe2, Info, Link2, ListChecks, Loader2, MessageSquareText, RefreshCw, ServerCog,
  ShieldCheck, XCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import {
  AUTOMATED_CHECKS, IMPORTANT_INFORMATION, KNOWN_LIMITATIONS, LANGUAGE_VARIANTS, MANUAL_EXAMPLES, MCP_EVIDENCE,
  QUALITY_GUARANTEES, SECURITY_EVIDENCE, TECHNOLOGIES, VALIDATED_POINTS, VALIDATION_SNAPSHOT, VOICE_CHECKS,
} from "../../data/validation";
import type { EvidenceStatus } from "../../data/validation";
import type { RuntimeSnapshot } from "../../services/validation";

const STATUS_META: Record<EvidenceStatus, { label: string; icon: LucideIcon }> = {
  pass: { label: "Validé", icon: CheckCircle2 },
  warn: { label: "À confirmer", icon: AlertTriangle },
  info: { label: "Information", icon: CircleDashed },
  fail: { label: "Échec", icon: XCircle },
};

export function StatusBadge({ status, label }: { status: EvidenceStatus; label?: string }) {
  const { label: fallback, icon: Icon } = STATUS_META[status];
  return (
    <span className={`vl-badge vl-badge-${status}`}>
      <Icon size={13} aria-hidden="true" /> {label ?? fallback}
    </span>
  );
}

function StatusIcon({ status }: { status: EvidenceStatus }) {
  const Icon = STATUS_META[status].icon;
  return <Icon size={16} className={`vl-icon-${status}`} aria-label={STATUS_META[status].label} />;
}

function Head({ icon: Icon, title, subtitle, tone = "blue", action }: { icon: LucideIcon; title: string; subtitle: string; tone?: string; action?: ReactNode }) {
  return (
    <div className="vl-head">
      <span className={`vl-head-tile vl-tile-${tone}`} aria-hidden="true"><Icon size={21} /></span>
      <div className="vl-head-copy">
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {action}
    </div>
  );
}

/* ---------------- summary ---------------- */

const SUMMARY: { label: string; value: string; status: EvidenceStatus }[] = [
  { label: "Tests automatisés", value: "PASS", status: "pass" },
  { label: "Frontend (TS + build)", value: "PASS", status: "pass" },
  { label: "Sécurité", value: "PASS", status: "pass" },
  { label: "RAG", value: "PASS", status: "pass" },
  { label: "Multilingue", value: "PASS", status: "pass" },
  { label: "MCP & n8n", value: "PASS", status: "pass" },
  { label: "Voix · pipeline technique", value: "PASS", status: "pass" },
  { label: "Voix · écoute humaine", value: "À confirmer", status: "warn" },
];

export function SummaryCard() {
  return (
    <section className="vl-panel vl-summary" aria-labelledby="vl-summary-title">
      <div className="vl-summary-lead">
        <span className="vl-summary-icon" aria-hidden="true"><BadgeCheck size={30} /></span>
        <div>
          <h2 id="vl-summary-title">Le socle EduBourse est validé pour la démonstration PFA.</h2>
          <p>
            Dernière validation automatisée : {VALIDATION_SNAPSHOT.runDate} · une vérification humaine
            de l’audio Voice-to-Voice reste à effectuer.
          </p>
        </div>
      </div>
      <ul className="vl-summary-grid">
        {SUMMARY.map(({ label, value, status }) => (
          <li key={label} className={`vl-summary-item vl-summary-${status}`}>
            <StatusIcon status={status} />
            <span>{label}</span>
            <strong>{value}</strong>
          </li>
        ))}
      </ul>
      <div className="vl-legend" aria-label="Légende des statuts">
        <span><CheckCircle2 size={13} className="vl-icon-pass" aria-hidden="true" /> Validé / Disponible</span>
        <span><AlertTriangle size={13} className="vl-icon-warn" aria-hidden="true" /> Limitation / vérification humaine</span>
        <span><CircleDashed size={13} className="vl-icon-info" aria-hidden="true" /> Non vérifié / information statique</span>
        <span><XCircle size={13} className="vl-icon-fail" aria-hidden="true" /> Échec réel uniquement</span>
      </div>
    </section>
  );
}

/* ---------------- automated validation ---------------- */

export function AutomatedTestsCard() {
  return (
    <section className="vl-panel vl-automated">
      <Head icon={BarChart3} title="Résultats des validations automatisées" subtitle="Instantané de la dernière exécution réelle, pas un calcul du navigateur" />
      <div className="vl-table-wrap">
        <table className="vl-table">
          <caption className="vl-sr">Validations automatisées et leurs preuves</caption>
          <colgroup>
            <col className="vl-col-label" />
            <col className="vl-col-result" />
            <col />
            <col className="vl-col-status" />
          </colgroup>
          <thead>
            <tr>
              <th scope="col">Validation</th>
              <th scope="col">Résultat</th>
              <th scope="col">Preuve</th>
              <th scope="col">Statut</th>
            </tr>
          </thead>
          <tbody>
            {AUTOMATED_CHECKS.map(({ label, result, evidence, status }, index) => (
              <tr key={label} className={index === 0 ? "vl-row-total" : undefined}>
                <th scope="row" data-label="Validation">{label}</th>
                <td data-label="Résultat">{result}</td>
                <td data-label="Preuve" className="vl-evidence-cell">
                  {evidence.split(" · ").map((part) => <code key={part}>{part}</code>)}
                </td>
                <td data-label="Statut"><StatusBadge status={status} label={status === "pass" ? "Pass" : undefined} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="vl-foot vl-foot-ok">
        <CheckCircle2 size={16} aria-hidden="true" />
        <span>
          <strong>{VALIDATION_SNAPSHOT.backendPassed} tests backend réussis, {VALIDATION_SNAPSHOT.backendFailed} échec</strong>
          {" "}· Dernière validation automatisée : {VALIDATION_SNAPSHOT.runDate} ({VALIDATION_SNAPSHOT.backendDuration})
        </span>
      </p>
      <p className="vl-note">
        Les lignes par domaine ne donnent volontairement aucun nombre de tests : leurs fichiers font partie de la
        suite complète, passée sans échec.
      </p>
    </section>
  );
}

/* ---------------- runtime ---------------- */

type RuntimeRow = { name: string; status: "ok" | "down" | "pending" | "unknown"; detail: string; source: string };

function runtimeRows(snapshot: RuntimeSnapshot): RuntimeRow[] {
  const { backend, postgres, rag, integrations } = snapshot;
  const rows: RuntimeRow[] = [];

  rows.push({
    name: "Backend API",
    status: backend.state === "pending" ? "pending" : backend.state === "ok" && backend.data ? "ok" : "down",
    detail: "FastAPI · liveness",
    source: "GET /api/v1/health/live",
  });

  rows.push({
    name: "PostgreSQL",
    status: postgres.state === "pending" ? "pending" : postgres.state === "ok" ? (postgres.data ? "ok" : "down") : "unknown",
    detail: "Connexion testée par le backend (SELECT 1)",
    source: "GET /api/v1/health",
  });

  if (rag.state === "ok") {
    const live = rag.data.live_chunk_count;
    rows.push({
      name: "Index RAG (ChromaDB)",
      status: rag.data.index_status === "available" ? "ok" : "down",
      detail: `${rag.data.collection_name} · ${live ?? "?"} chunks en ligne`,
      source: "GET /api/v1/rag/overview",
    });
  } else {
    rows.push({ name: "Index RAG (ChromaDB)", status: rag.state === "pending" ? "pending" : "unknown", detail: "Métadonnées de l’index", source: "GET /api/v1/rag/overview" });
  }

  if (integrations.state === "ok") {
    const { mcp, n8n, workflows } = integrations.data;
    const webhooks = workflows.filter((workflow) => workflow.trigger === "webhook");
    const registered = webhooks.filter((workflow) => workflow.registered === true).length;
    rows.push({
      name: "Serveur MCP",
      status: mcp.reachable && mcp.auth_enforced ? "ok" : "down",
      detail: mcp.auth_enforced ? "Joignable · authentification exigée" : "Sonde MCP",
      source: "GET /api/v1/integrations/status",
    });
    rows.push({ name: "n8n", status: n8n.reachable ? "ok" : "down", detail: "Sonde /healthz", source: "GET /api/v1/integrations/status" });
    rows.push({
      name: "Webhooks n8n",
      status: registered === webhooks.length ? "ok" : "down",
      detail: `${registered}/${webhooks.length} webhooks actifs · 1 workflow manuel`,
      source: "GET /api/v1/integrations/status",
    });
  } else {
    const status = integrations.state === "pending" ? "pending" : "unknown";
    rows.push({ name: "Serveur MCP", status, detail: "Sonde via le pont backend", source: "GET /api/v1/integrations/status" });
    rows.push({ name: "n8n", status, detail: "Sonde via le pont backend", source: "GET /api/v1/integrations/status" });
  }

  rows.push({ name: "Frontend", status: "ok", detail: "Cette page est servie et exécutée", source: window.location.origin });
  return rows;
}

const RUNTIME_LABEL: Record<RuntimeRow["status"], string> = {
  ok: "Disponible",
  down: "Indisponible",
  pending: "Vérification…",
  unknown: "Non vérifié",
};

export function RuntimeStatusCard({ snapshot, checking, checkedAt, onRefresh }: { snapshot: RuntimeSnapshot; checking: boolean; checkedAt: Date | null; onRefresh: () => void }) {
  const rows = runtimeRows(snapshot);
  const down = rows.filter((row) => row.status === "down");
  return (
    <section className="vl-panel vl-runtime">
      <Head icon={ServerCog} title="État actuel des composants" subtitle="Vérification en direct, séparée des résultats de tests" />
      <ul className="vl-runtime-list" aria-live="polite" aria-busy={checking}>
        {rows.map(({ name, status, detail, source }) => (
          <li key={name}>
            <div className="vl-runtime-name">
              <strong>{name}</strong>
              <small>{detail}</small>
            </div>
            <span className={`vl-runtime-status vl-runtime-${status}`}>
              {status === "pending" ? <Loader2 size={13} className="vl-spin" aria-hidden="true" /> : <i aria-hidden="true" />}
              {RUNTIME_LABEL[status]}
            </span>
            <code className="vl-runtime-source">{source}</code>
          </li>
        ))}
      </ul>
      {down.length > 0 && (
        <p className="vl-alert" role="alert">
          <XCircle size={15} aria-hidden="true" /> {down.map((row) => row.name).join(", ")} : indisponible lors de la dernière vérification.
        </p>
      )}
      <div className="vl-runtime-foot">
        <button type="button" className="vl-button-ghost" onClick={onRefresh} disabled={checking}>
          <RefreshCw size={16} className={checking ? "vl-spin" : undefined} aria-hidden="true" />
          {checking ? "Vérification…" : "Rafraîchir les états"}
        </button>
        <small>
          {checkedAt ? `Dernière vérification : ${checkedAt.toLocaleTimeString("fr-FR")}` : "Vérification en cours"}
          <br />Groq et Gemini ne sont pas sondés (quotas préservés).
        </small>
      </div>
    </section>
  );
}

/* ---------------- guarantees ---------------- */

export function GuaranteesCard() {
  return (
    <section className="vl-panel">
      <Head icon={ShieldCheck} tone="green" title="Garanties validées" subtitle="Propriétés prouvées par l’implémentation et les tests" />
      <ul className="vl-check-list">
        {QUALITY_GUARANTEES.map((item) => (
          <li key={item}><CheckCircle2 size={16} className="vl-icon-pass" aria-hidden="true" />{item}</li>
        ))}
      </ul>
      <h3 className="vl-subtitle">Décisions observées sur le pipeline canonique</h3>
      <ul className="vl-security-list">
        {SECURITY_EVIDENCE.map(({ question, route, outcome }) => (
          <li key={question}>
            <q dir="auto">{question}</q>
            <span><code>{route}</code> {outcome}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/* ---------------- manual tests ---------------- */

const NAV_BUTTONS: { label: string; path: string; icon: LucideIcon }[] = [
  { label: "Voir RAG & Sources", path: "/rag", icon: Database },
  { label: "Voir Multilingue", path: "/multilingue", icon: Globe2 },
  { label: "Voir Voice-to-Voice", path: "/voice", icon: AudioWaveform },
  { label: "Voir Sécurité", path: "/security", icon: ShieldCheck },
  { label: "Voir MCP & n8n", path: "/integrations", icon: Link2 },
];

export function ManualExamplesCard() {
  const navigate = useNavigate();
  return (
    <section className="vl-panel">
      <Head icon={MessageSquareText} title="Tests manuels rapides" subtitle="Ouvre l’Assistant avec la question pré-remplie (non envoyée)" />
      <ul className="vl-examples">
        {MANUAL_EXAMPLES.map(({ text, expected, tone }) => (
          <li key={text}>
            <button type="button" className={`vl-example vl-example-${tone}`} onClick={() => navigate("/assistant", { state: { prefill: text } })}>
              {tone === "blocked" ? <AlertTriangle size={15} aria-hidden="true" /> : <CheckCircle2 size={15} aria-hidden="true" />}
              <span dir="auto">{text}</span>
              <small>Attendu : {expected}</small>
            </button>
          </li>
        ))}
      </ul>
      <button type="button" className="vl-button-primary" onClick={() => navigate("/assistant")}>
        <FlaskConical size={17} aria-hidden="true" /> Tester dans l’Assistant
      </button>
      <div className="vl-nav-grid">
        {NAV_BUTTONS.map(({ label, path, icon: Icon }) => (
          <button key={path} type="button" className="vl-button-ghost vl-button-small" onClick={() => navigate(path)}>
            <Icon size={15} aria-hidden="true" /> {label} <ArrowRight size={14} aria-hidden="true" />
          </button>
        ))}
      </div>
    </section>
  );
}

/* ---------------- points & limitations ---------------- */

export function PointsCard() {
  return (
    <section className="vl-panel">
      <Head icon={ListChecks} title="Points validés et limites connues" subtitle="Ce qui est confirmé, et ce qui ne l’est pas encore" />
      <div className="vl-points">
        <div>
          <h3 className="vl-subtitle vl-subtitle-ok"><CheckCircle2 size={15} aria-hidden="true" /> Points validés</h3>
          <ul className="vl-check-list vl-check-compact">
            {VALIDATED_POINTS.map((item) => (
              <li key={item}><CheckCircle2 size={15} className="vl-icon-pass" aria-hidden="true" />{item}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="vl-subtitle vl-subtitle-warn"><AlertTriangle size={15} aria-hidden="true" /> Limites connues</h3>
          <ul className="vl-check-list vl-check-compact">
            {KNOWN_LIMITATIONS.map((item) => (
              <li key={item}><AlertTriangle size={15} className="vl-icon-warn" aria-hidden="true" />{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

/* ---------------- voice ---------------- */

export function VoiceValidationCard() {
  const pending = VOICE_CHECKS.filter((check) => check.status === "warn").length;
  const passed = VOICE_CHECKS.length - pending;
  return (
    <section className="vl-panel">
      <Head
        icon={AudioWaveform}
        tone="pink"
        title="Validation Voice-to-Voice"
        subtitle="Pipeline technique validé de bout en bout"
        action={<StatusBadge status={pending ? "warn" : "pass"} label={pending ? `${pending} à confirmer` : `${passed}/${VOICE_CHECKS.length} validés`} />}
      />
      <ul className="vl-voice-list">
        {VOICE_CHECKS.map(({ label, detail, status }) => (
          <li key={label} className={status === "warn" ? "vl-voice-warn" : undefined}>
            <StatusIcon status={status} />
            <div>
              <strong>{label}</strong>
              <small>{detail}</small>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

/* ---------------- technical evidence ---------------- */

export function EvidenceCard({ snapshot }: { snapshot: RuntimeSnapshot }) {
  const rag = snapshot.rag.state === "ok" ? snapshot.rag.data : null;
  return (
    <section className="vl-panel vl-evidence">
      <Head icon={FlaskConical} tone="purple" title="Preuves techniques" subtitle="Valeurs lues depuis le backend ou relevées lors de la validation" />
      <div className="vl-evidence-grid">
        <article>
          <h3><Database size={16} aria-hidden="true" /> RAG & Sources</h3>
          <dl className="vl-facts">
            <div><dt>Chunks indexés</dt><dd>{rag ? rag.indexed_chunk_count : "353"}</dd></div>
            <div><dt>Sources approuvées</dt><dd>{rag ? rag.source_count : "13"}</dd></div>
            <div><dt>Modèle</dt><dd>{rag ? rag.embedding_model : "BAAI/bge-m3"}</dd></div>
            <div><dt>Dimension</dt><dd>{rag ? rag.embedding_dimension : "1024"}</dd></div>
            <div className="vl-facts-wide"><dt>Collection</dt><dd>{rag ? rag.collection_name : "j6_bge_m3_content_v1"}</dd></div>
          </dl>
          <p className="vl-note">{rag ? "Lu en direct via /api/v1/rag/overview." : "Instantané de validation (overview non lu)."} Corpus AMMC approuvé · grounding lorsque applicable.</p>
        </article>
        <article>
          <h3><Globe2 size={16} aria-hidden="true" /> 4 langues métier</h3>
          <ul className="vl-lang-list">
            {LANGUAGE_VARIANTS.map(({ label, code }) => (
              <li key={code}><CheckCircle2 size={14} className="vl-icon-pass" aria-hidden="true" /><span dir="auto">{label}</span><code>{code}</code></li>
            ))}
          </ul>
          <p className="vl-note">FR · EN · AR · Darija : 5 variantes langue/écriture, Darija en arabe et en latin.</p>
        </article>
        <article>
          <h3><Link2 size={16} aria-hidden="true" /> MCP & n8n</h3>
          <dl className="vl-facts">
            <div><dt>Serveur MCP</dt><dd>{MCP_EVIDENCE.servers}</dd></div>
            <div><dt>Tools</dt><dd>{MCP_EVIDENCE.tools.length}</dd></div>
            <div><dt>Resources</dt><dd>{MCP_EVIDENCE.resources.length}</dd></div>
            <div><dt>Workflows n8n</dt><dd>{MCP_EVIDENCE.workflows.length}</dd></div>
          </dl>
          <p className="vl-tags">{MCP_EVIDENCE.tools.map((tool) => <code key={tool}>{tool}</code>)}</p>
          <p className="vl-note">{MCP_EVIDENCE.workflows.join(" · ")}. MCP et n8n utilisent le backend canonique, sans logique métier dupliquée.</p>
        </article>
      </div>
      <h3 className="vl-subtitle">Technologies utilisées <small>(information statique, non sondée)</small></h3>
      <p className="vl-tags vl-tags-muted">{TECHNOLOGIES.map((tech) => <span key={tech}>{tech}</span>)}</p>
    </section>
  );
}

/* ---------------- information ---------------- */

export function InformationCard() {
  return (
    <section className="vl-panel">
      <Head icon={Info} title="Informations importantes" subtitle="Cadre d’utilisation d’EduBourse" />
      <ul className="vl-check-list vl-check-compact">
        {IMPORTANT_INFORMATION.map((item) => (
          <li key={item}><CheckCircle2 size={15} className="vl-icon-pass" aria-hidden="true" />{item}</li>
        ))}
      </ul>
    </section>
  );
}
