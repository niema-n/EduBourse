import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { test } from "node:test";
import { build } from "esbuild";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

// Render the actual components, using the project's installed build tool.
const result = await build({
  stdin: {
    contents: `export { SourcesPanel } from './src/components/assistant/SourcesPanel';
      export { ResponseMetadata } from './src/components/assistant/ResponseMetadata';`,
    resolveDir: process.cwd(), loader: "tsx",
  },
  bundle: true, write: false, format: "cjs", platform: "node", packages: "external",
});
const mod = { exports: {} };
new Function("require", "module", "exports", result.outputFiles[0].text)(
  createRequire(import.meta.url), mod, mod.exports,
);
const { SourcesPanel, ResponseMetadata } = mod.exports;

for (const level of ["beginner", "intermediate", "advanced"]) {
  test(`${level}: internal source is separate from grounding and citations`, () => {
    const source = {
      label: "Contenu pédagogique interne EduBourse",
      description: `Parcours ${level}, module 2/8: Titre du module`,
      level, path_id: `${level}_financial_learning`, module_id: `${level}_module_2`,
      module_title: "Titre du module", module_number: 2, module_count: 8,
    };
    const html = renderToStaticMarkup(createElement(SourcesPanel, {
      citations: [], internalSource: source,
    }));
    assert.ok(html.includes(source.label));
    assert.ok(html.includes(source.description));
    assert.ok(!html.includes("Aucune source affichée"));
    assert.ok(!html.includes("ap-chip"));
    const response = {
      answer: "Module", blocked: false, status: "ok",
      route: "formation_elearning", grounded: null, citations: [],
      language: "fr", script: "latin", thread_id: "source",
      internal_pedagogical_source: source,
    };
    const metadata = renderToStaticMarkup(createElement(ResponseMetadata, { response }));
    assert.ok(metadata.includes("N/A"));
    assert.match(metadata, /Citations<\/dt>[\s\S]*?>0<\/span>/);
  });
}

test("empty-source message is unchanged without internal metadata", () => {
  const html = renderToStaticMarkup(createElement(SourcesPanel, { citations: [] }));
  assert.ok(html.includes("Aucune source affichée pour cette réponse."));
});

test("real RAG citations are unchanged", () => {
  const html = renderToStaticMarkup(createElement(SourcesPanel, { citations: [{
    evidence_id: "E1", chunk_id: "chunk", source_id: "doc", title: "Document RAG",
    page: 3, page_start: 3, page_end: 3, heading: null,
  }] }));
  assert.ok(html.includes("Document RAG"));
  assert.ok(html.includes("p. 3"));
  assert.ok(!html.includes("Contenu pédagogique interne"));
});
