import { useCallback, useEffect, useRef, useState } from "react";

import { IntegrationRequestError, testIntegrationAsk, testMcpHealth } from "../../services/integrations";
import type { IntegrationAskResponse, McpHealthResponse, TesterTab } from "../../types/integrations";

export type IntegrationTestResult =
  | { kind: "mcp_health"; response: McpHealthResponse; question: null; at: Date }
  | { kind: "mcp_ask" | "n8n_mcp_ask"; response: IntegrationAskResponse; question: string; at: Date };

export type IntegrationHistoryItem = {
  id: string;
  at: string;
  kind: TesterTab;
  status: "ok" | "error";
  route: string | null;
  preview: string | null;
};

const HISTORY_KEY = "edubourse.integrations.history.v1";
const HISTORY_LIMIT = 8;
const PREVIEW_LENGTH = 80;

function loadHistory(): IntegrationHistoryItem[] {
  try {
    const parsed: unknown = JSON.parse(window.sessionStorage.getItem(HISTORY_KEY) ?? "[]");
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter(
        (item): item is IntegrationHistoryItem =>
          !!item &&
          typeof item.id === "string" &&
          typeof item.at === "string" &&
          ["mcp_health", "mcp_ask", "n8n_mcp_ask", "voice"].includes(item.kind) &&
          (item.status === "ok" || item.status === "error"),
      )
      .slice(0, HISTORY_LIMIT);
  } catch {
    return [];
  }
}

function preview(text: string): string {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length > PREVIEW_LENGTH ? `${flat.slice(0, PREVIEW_LENGTH - 1)}…` : flat;
}

/** Tests launched from this page only; every call goes through the backend bridge. */
export function useIntegrationTests() {
  const [kind, setKind] = useState<TesterTab>("mcp_ask");
  const [message, setMessage] = useState("C'est quoi une action ?");
  const [sameThread, setSameThread] = useState(false);
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<IntegrationTestResult | null>(null);
  const [failure, setFailure] = useState<IntegrationRequestError["kind"] | null>(null);
  const [validation, setValidation] = useState(false);
  const [history, setHistory] = useState<IntegrationHistoryItem[]>(loadHistory);
  const threadsRef = useRef<{ mcp_ask: string | null; n8n_mcp_ask: string | null }>({ mcp_ask: null, n8n_mcp_ask: null });
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);
  useEffect(() => {
    try {
      if (history.length === 0) window.sessionStorage.removeItem(HISTORY_KEY);
      else window.sessionStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    } catch {
      /* storage unavailable: memory only */
    }
  }, [history]);

  const record = useCallback((item: Omit<IntegrationHistoryItem, "id" | "at">) => {
    const at = new Date();
    setHistory((items) =>
      [{ id: `${at.getTime()}-${Math.random().toString(36).slice(2, 7)}`, at: at.toISOString(), ...item }, ...items].slice(0, HISTORY_LIMIT),
    );
  }, []);

  const run = useCallback(
    async (overrideMessage?: string) => {
      // Voice runs on the canonical WebSocket session, handled by the voice hook.
      if (abortRef.current || kind === "voice") return;
      const question = (overrideMessage ?? message).trim();
      if (kind !== "mcp_health" && !question) {
        setValidation(true);
        return;
      }
      setValidation(false);
      setFailure(null);
      setResult(null);
      setPending(true);
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        if (kind === "mcp_health") {
          const response = await testMcpHealth(controller.signal);
          if (controller.signal.aborted) return;
          setResult({ kind, response, question: null, at: new Date() });
          record({ kind, status: response.status, route: null, preview: null });
        } else {
          const previous = sameThread ? threadsRef.current[kind] : null;
          const response = await testIntegrationAsk(kind === "mcp_ask" ? "mcp" : "n8n", question, previous, controller.signal);
          if (controller.signal.aborted) return;
          threadsRef.current[kind] = response.thread_id;
          setResult({ kind, response, question, at: new Date() });
          record({ kind, status: response.status, route: response.result?.route ?? null, preview: preview(question) });
        }
      } catch (caught) {
        if (controller.signal.aborted && abortRef.current !== controller) return;
        const code = caught instanceof IntegrationRequestError ? caught.kind : "unavailable";
        setFailure(code);
        record({ kind, status: "error", route: null, preview: kind === "mcp_health" ? null : preview(question) });
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
          setPending(false);
        }
      }
    },
    [kind, message, sameThread, record],
  );

  const reset = useCallback(() => {
    const controller = abortRef.current;
    abortRef.current = null;
    controller?.abort();
    threadsRef.current = { mcp_ask: null, n8n_mcp_ask: null };
    setPending(false);
    setResult(null);
    setFailure(null);
    setValidation(false);
    setSameThread(false);
    setMessage("");
  }, []);

  return {
    kind,
    setKind: (next: TesterTab) => {
      if (!abortRef.current) setKind(next);
    },
    message,
    setMessage: (value: string) => {
      setMessage(value);
      if (validation) setValidation(false);
    },
    sameThread,
    setSameThread,
    currentThread: kind === "mcp_health" || kind === "voice" ? null : threadsRef.current[kind],
    pending,
    result,
    failure,
    validation,
    history,
    run,
    reset,
    clearHistory: () => setHistory([]),
    record,
  };
}

export type IntegrationTestsApi = ReturnType<typeof useIntegrationTests>;
