/**
 * Mirrors backend/app/schemas/rag.py exactly. The read-only RAG API never
 * returns paths, vectors, URLs or dates, so none are modelled here.
 */

export type RagIndexStatus = "available" | "not_loaded" | "unavailable";

export type RagOverview = {
  collection_name: string;
  embedding_model: string;
  embedding_dimension: number;
  distance_metric: string;
  index_version: number;
  indexed_chunk_count: number;
  live_chunk_count: number | null;
  source_count: number;
  corpus_languages: string[];
  authorities: string[];
  index_status: RagIndexStatus;
};

export type RagSource = {
  source_id: string;
  title: string;
  authority: string;
  categories: string[];
  language: string;
  source_type: string;
  chunk_count: number;
};

export type RagSources = {
  total_sources: number;
  total_chunks: number;
  sources: RagSource[];
};

export type RagSearchHit = {
  rank: number;
  chunk_id: string;
  source_id: string;
  title: string;
  authority: string | null;
  categories: string[];
  page_start: number;
  page_end: number;
  heading: string | null;
  /** Original retrieved source text: the evidence, never translated. */
  excerpt: string;
  source_language: string | null;
  score: number;
  score_type: "cosine_distance" | "rrf";
  /** Display-only preview of `excerpt` in the user's language. */
  translated_excerpt: string | null;
  translated_language: "en" | "ar" | "ary" | null;
  translated_script: "latin" | "arabic" | null;
  translation_status: "not_needed" | "translated" | "unavailable";
};

export type RagSearchResult = {
  query: string;
  language: "fr" | "en" | "ar" | "ary";
  script: "latin" | "arabic";
  retrieval_query: string | null;
  branches: string[];
  top_k: number;
  results: RagSearchHit[];
};
