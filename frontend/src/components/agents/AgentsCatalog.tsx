import { useMemo } from "react";
import { ChevronDown, Search, SearchX, UsersRound } from "lucide-react";

import { AGENTS, AGENT_CATEGORIES, categoryLabel } from "../../data/agents";
import type { AgentCategory, AgentDefinition } from "../../data/agents";
import { AgentCard } from "./AgentCard";

/** Accent- and case-insensitive text, so "securite" finds "Sécurité". */
function fold(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

export function AgentsCatalog({
  query,
  onQueryChange,
  category,
  onCategoryChange,
  onOpen,
}: {
  query: string;
  onQueryChange: (value: string) => void;
  category: AgentCategory | "all";
  onCategoryChange: (value: AgentCategory | "all") => void;
  onOpen: (agent: AgentDefinition, trigger: HTMLButtonElement) => void;
}) {
  const visible = useMemo(() => {
    const needle = fold(query.trim());
    return AGENTS.filter((agent) => {
      if (category !== "all" && agent.category !== category) return false;
      if (!needle) return true;
      const haystack = fold(
        [agent.name, agent.route, agent.summary, agent.description, categoryLabel(agent.category)].join(" "),
      );
      return haystack.includes(needle);
    });
  }, [query, category]);

  return (
    <section className="ag-panel ag-catalog" id="catalogue-agents" aria-labelledby="ag-catalog-title">
      <div className="ag-catalog-head">
        <span className="ag-head-glyph" aria-hidden="true">
          <UsersRound size={30} strokeWidth={2.2} />
        </span>
        <div className="ag-head-copy">
          <h2 id="ag-catalog-title">Catalogue des agents</h2>
          <p>10 routes spécialisées couvrant les principaux cas d’usage de l’éducation financière</p>
        </div>
        <div className="ag-catalog-tools">
          <label className="ag-search">
            <span className="visually-hidden">Rechercher un agent</span>
            <Search size={16} aria-hidden="true" />
            <input
              type="search"
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder="Rechercher un agent..."
            />
          </label>
          <label className="ag-select">
            <span className="visually-hidden">Filtrer par catégorie</span>
            <select
              value={category}
              onChange={(event) => onCategoryChange(event.target.value as AgentCategory | "all")}
            >
              <option value="all">Toutes les catégories</option>
              {AGENT_CATEGORIES.map(({ id, label }) => (
                <option key={id} value={id}>
                  {label}
                </option>
              ))}
            </select>
            <ChevronDown size={15} aria-hidden="true" />
          </label>
        </div>
      </div>

      <p className="visually-hidden" aria-live="polite">
        {visible.length} agent{visible.length > 1 ? "s" : ""} affiché{visible.length > 1 ? "s" : ""}
      </p>

      {visible.length === 0 ? (
        <div className="ag-empty">
          <SearchX size={28} aria-hidden="true" />
          <strong>Aucun agent ne correspond à votre recherche</strong>
          <button
            type="button"
            onClick={() => {
              onQueryChange("");
              onCategoryChange("all");
            }}
          >
            Réinitialiser les filtres
          </button>
        </div>
      ) : (
        <div className="ag-grid">
          {visible.map((agent) => (
            <AgentCard key={agent.route} agent={agent} onOpen={onOpen} />
          ))}
        </div>
      )}
    </section>
  );
}
