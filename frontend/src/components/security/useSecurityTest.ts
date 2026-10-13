import { useCallback, useEffect, useRef, useState } from "react";

import { ChatError, sendChatMessage } from "../../services/chat";
import {
  HISTORY_LIMIT,
  createSecurityThreadId,
  loadSecurityHistory,
  outcomeOf,
  previewOf,
  saveSecurityHistory,
} from "../../services/security";
import type { SecurityChannel, SecurityHistoryItem } from "../../services/security";
import type { ChatErrorKind, ChatResponseBody } from "../../types/chat";

export type SecurityTestResult = {
  question: string;
  response: ChatResponseBody;
  durationMs: number;
  at: Date;
};

/**
 * Sends questions to the real POST /api/v1/chat. The browser applies no
 * security rule: it only displays route / blocked / status as returned.
 */
export function useSecurityTest() {
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const [result, setResult] = useState<SecurityTestResult | null>(null);
  const [error, setError] = useState<ChatErrorKind | null>(null);
  const [validation, setValidation] = useState(false);
  const [history, setHistory] = useState<SecurityHistoryItem[]>(loadSecurityHistory);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);
  useEffect(() => saveSecurityHistory(history), [history]);

  /** Adds one backend decision (text or voice) to this page's session history. */
  const record = useCallback((question: string, response: ChatResponseBody, channel: SecurityChannel) => {
    const at = new Date();
    setHistory((items) =>
      [
        {
          id: `${at.getTime()}-${Math.random().toString(36).slice(2, 7)}`,
          at: at.toISOString(),
          channel,
          preview: previewOf(question),
          language: response.language,
          route: response.route,
          status: response.status,
          outcome: outcomeOf(response),
        },
        ...items,
      ].slice(0, HISTORY_LIMIT),
    );
  }, []);

  const run = useCallback(
    async (text: string) => {
      const question = text.trim();
      if (!question) {
        setValidation(true);
        return;
      }
      if (abortRef.current) return;
      setValidation(false);
      setError(null);
      setResult(null);
      setPending(true);
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const { response, requestDurationMs } = await sendChatMessage(
          { message: question, thread_id: createSecurityThreadId() },
          controller.signal,
        );
        if (controller.signal.aborted) return;
        setResult({ question, response, durationMs: requestDurationMs, at: new Date() });
        record(question, response, "texte");
      } catch (caught) {
        if (controller.signal.aborted) return;
        setError(caught instanceof ChatError ? caught.kind : "network");
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
          setPending(false);
        }
      }
    },
    [record],
  );

  const reset = useCallback(() => {
    const controller = abortRef.current;
    abortRef.current = null;
    controller?.abort();
    setPending(false);
    setMessage("");
    setResult(null);
    setError(null);
    setValidation(false);
  }, []);

  const clearHistory = useCallback(() => setHistory([]), []);

  const pick = useCallback(
    (text: string) => {
      if (abortRef.current) return;
      setMessage(text);
      void run(text);
    },
    [run],
  );

  return {
    message,
    setMessage: (value: string) => {
      setMessage(value);
      if (validation) setValidation(false);
    },
    pending,
    result,
    error,
    validation,
    history,
    run,
    reset,
    pick,
    clearHistory,
    record,
  };
}

export type SecurityTestApi = ReturnType<typeof useSecurityTest>;
