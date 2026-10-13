import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import type { ReactNode } from "react";
import type { IconType } from "react-icons";
import {
  FaBrain,
  FaChartSimple,
  FaCode,
  FaDatabase,
  FaGlobe,
  FaLink,
  FaRegFileLines,
  FaUsers,
} from "react-icons/fa6";

import { BackendResponseCard } from "../components/assistant/BackendResponseCard";
import { ChatPanel } from "../components/assistant/ChatPanel";
import { HistoryPanel } from "../components/assistant/HistoryPanel";
import type { HistoryState } from "../components/assistant/HistoryPanel";
import { MultilingualCard } from "../components/assistant/MultilingualCard";
import { PipelineCard } from "../components/assistant/PipelineCard";
import type { ChatMessage, LastExchange } from "../types/chat";
import { ChatError, createThreadId, sendChatMessage } from "../services/chat";
import { deleteConversation, fetchConversation, fetchConversations } from "../services/conversations";

import "../assistant.css";

/**
 * Validated project capabilities, not live runtime health. They describe what
 * the system supports; they never claim a service is currently up.
 */
const capabilityPills: { icon: IconType; label: ReactNode; variant: string }[] = [
  {
    icon: FaGlobe,
    label: (
      <>
        FR / EN / AR / <b>Darija</b>
      </>
    ),
    variant: "plain",
  },
  { icon: FaDatabase, label: "RAG grounded", variant: "plain" },
  { icon: FaLink, label: "Thread continuity", variant: "green" },
  { icon: FaCode, label: "10 routes", variant: "blue" },
];

/** Verified project values (see the RAG manifest), presented as static facts. */
function OverviewCards() {
  return (
    <section className="ap-overview" aria-label="Aperçu du service">
      <article className="ap-card">
        <span className="ap-card-tile ap-tile-blue" aria-hidden="true">
          <FaGlobe />
        </span>
        <div className="ap-card-copy">
          <span className="ap-card-label">Langues prises en charge</span>
          <strong className="ap-card-value">4</strong>
          <small>FR&nbsp; • &nbsp;EN&nbsp; • &nbsp;AR&nbsp; • &nbsp;Darija</small>
        </div>
        <span className="ap-card-marks" aria-hidden="true">
          <FaChartSimple className="ap-mark-chart" />
          <FaUsers className="ap-mark-users" />
        </span>
      </article>

      <article className="ap-card ap-card-badged">
        <span className="ap-card-tile ap-tile-blue" aria-hidden="true">
          <FaCode />
        </span>
        <div className="ap-card-copy">
          <span className="ap-card-label">Routes backend</span>
          <strong className="ap-card-value">10</strong>
          <small>Toutes les routes opérationnelles</small>
        </div>
        <span className="ap-card-badge">
          <FaBrain aria-hidden="true" /> LangGraph
        </span>
      </article>

      <article className="ap-card">
        <span className="ap-card-tile ap-tile-green" aria-hidden="true">
          <FaDatabase />
        </span>
        <div className="ap-card-copy">
          <span className="ap-card-label">Base RAG</span>
          <strong className="ap-card-value">353 embeddings</strong>
          <small className="ap-card-detail-strong">1024 dimensions</small>
        </div>
        <span className="ap-card-marks" aria-hidden="true">
          <FaRegFileLines className="ap-mark-doc" />
        </span>
      </article>
    </section>
  );
}

const THREAD_STORAGE_KEY = "edubourse.assistant.thread_id";

/** Keep the thread for the browser session so a reload does not fork it. */
function loadThreadId(): string {
  try {
    const stored = window.sessionStorage.getItem(THREAD_STORAGE_KEY);
    if (stored && stored.trim()) return stored;
  } catch {
    // Private mode or blocked storage: fall back to an in-memory thread.
  }
  const created = createThreadId();
  try {
    window.sessionStorage.setItem(THREAD_STORAGE_KEY, created);
  } catch {
    // Non-fatal: React state still holds the thread for this page view.
  }
  return created;
}

/** History is an inline column on wide screens and a drawer below this width. */
const HISTORY_INLINE_MIN_WIDTH = 1101;

function isWideViewport(): boolean {
  return typeof window === "undefined" || window.innerWidth >= HISTORY_INLINE_MIN_WIDTH;
}

let messageCounter = 0;
const nextId = (prefix: string) => `${prefix}-${(messageCounter += 1)}`;

export function AssistantPage() {
  const [threadId, setThreadId] = useState(loadThreadId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [lastExchange, setLastExchange] = useState<LastExchange | null>(null);

  const [history, setHistory] = useState<HistoryState>({ status: "loading" });
  const [historyOpen, setHistoryOpen] = useState(isWideViewport);
  const [restoring, setRestoring] = useState<string | null>(null);
  const [historyNotice, setHistoryNotice] = useState<string | null>(null);
  const [deletingThreadId, setDeletingThreadId] = useState<string | null>(null);
  const deletingRef = useRef(false);

  // Guards against a second submission slipping through before the state flush.
  const pendingRef = useRef(false);
  const threadRef = useRef(threadId);
  const messagesRef = useRef(messages);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const restoreAbortRef = useRef<AbortController | null>(null);
  const historyAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    threadRef.current = threadId;
  }, [threadId]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  /** Reloads the backend history. A failure never blocks the active chat. */
  const refreshHistory = useCallback((silent = false) => {
    historyAbortRef.current?.abort();
    const controller = new AbortController();
    historyAbortRef.current = controller;
    if (!silent) setHistory({ status: "loading" });
    fetchConversations(controller.signal)
      .then((items) => {
        if (!controller.signal.aborted) setHistory({ status: "ready", items });
      })
      .catch(() => {
        if (!controller.signal.aborted) setHistory((current) => (silent && current.status === "ready" ? current : { status: "error" }));
      });
  }, []);

  useEffect(() => {
    refreshHistory();
    return () => {
      historyAbortRef.current?.abort();
      restoreAbortRef.current?.abort();
    };
  }, [refreshHistory]);

  useEffect(() => {
    if (!historyNotice) return undefined;
    const timer = window.setTimeout(() => setHistoryNotice(null), 5000);
    return () => window.clearTimeout(timer);
  }, [historyNotice]);

  // A page such as RAG & Sources may hand over a question to prefill. It is
  // only placed in the composer: the user still decides to send it.
  const location = useLocation();
  const navigate = useNavigate();
  useEffect(() => {
    const prefill = (location.state as { prefill?: unknown } | null)?.prefill;
    if (typeof prefill === "string" && prefill.trim()) {
      setDraft(prefill.slice(0, 4000));
      navigate(location.pathname, { replace: true, state: null });
      window.setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [location.state, location.pathname, navigate]);

  // Abort an in-flight request if the user leaves the page.
  const abortRef = useRef<AbortController | null>(null);
  useEffect(() => () => abortRef.current?.abort(), []);

  const send = useCallback(async (text: string) => {
    const message = text.trim();
    if (!message || pendingRef.current || deletingRef.current) return;

    pendingRef.current = true;
    setPending(true);
    setDraft("");
    setMessages((current) => [
      ...current,
      { id: nextId("user"), author: "user", text: message, at: new Date() },
    ]);

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      // The same thread_id is reused for every turn of this conversation, which
      // is what lets the backend keep the conversational context.
      const { response, requestDurationMs } = await sendChatMessage(
        { message, thread_id: threadRef.current },
        controller.signal,
      );
      const at = new Date();
      setMessages((current) => [
        ...current,
        { id: nextId("bot"), author: "assistant", text: response.answer, at, response },
      ]);
      setLastExchange({ response, requestDurationMs, at });
      // The backend stores ok/blocked turns: show the conversation in the history.
      if (response.status === "ok" || response.status === "blocked") refreshHistory(true);
    } catch (error) {
      const kind = error instanceof ChatError ? error.kind : "network";
      setMessages((current) => [
        ...current,
        { id: nextId("err"), author: "error", at: new Date(), kind, retryMessage: message },
      ]);
      // A client timeout does not mean the backend dropped the turn: resync the history.
      refreshHistory(true);
    } finally {
      abortRef.current = null;
      pendingRef.current = false;
      setPending(false);
      inputRef.current?.focus();
    }
  }, [refreshHistory]);

  const activateThread = useCallback((next: string) => {
    try {
      window.sessionStorage.setItem(THREAD_STORAGE_KEY, next);
    } catch {
      // Non-fatal: the thread still applies to this page view.
    }
    threadRef.current = next;
    setThreadId(next);
  }, []);

  const closeHistoryOnSmallScreens = useCallback(() => {
    if (!isWideViewport()) setHistoryOpen(false);
  }, []);

  const startNewChat = useCallback(() => {
    abortRef.current?.abort();
    restoreAbortRef.current?.abort();
    // The previous thread stays in the backend history; only the view is reset.
    activateThread(createThreadId());
    setMessages([]);
    setLastExchange(null);
    setDraft("");
    setRestoring(null);
    pendingRef.current = false;
    setPending(false);
    closeHistoryOnSmallScreens();
    inputRef.current?.focus();
  }, [activateThread, closeHistoryOnSmallScreens]);

  const selectConversation = useCallback(
    async (selected: string) => {
      if (pendingRef.current || deletingRef.current) return;
      closeHistoryOnSmallScreens();
      if (selected === threadRef.current && messagesRef.current.length > 0) return;
      restoreAbortRef.current?.abort();
      const controller = new AbortController();
      restoreAbortRef.current = controller;
      setRestoring(selected);
      try {
        const detail = await fetchConversation(selected, controller.signal);
        if (controller.signal.aborted) return;
        activateThread(detail.thread_id);
        setMessages(
          detail.messages.map((stored) => {
            const at = new Date(stored.created_at);
            const id = nextId(stored.role === "user" ? "hist-user" : "hist-bot");
            return stored.role === "user"
              ? { id, author: "user" as const, text: stored.content, at }
              : {
                  id,
                  author: "restored" as const,
                  text: stored.content,
                  at,
                  route: stored.route,
                  script: stored.script === "arabic" || stored.script === "latin" ? stored.script : null,
                  knowledgeSource: stored.knowledge_source,
                };
          }),
        );
        setLastExchange(null);
        setDraft("");
      } catch {
        if (!controller.signal.aborted) {
          setHistoryNotice("Impossible de charger cette conversation.");
        }
      } finally {
        if (restoreAbortRef.current === controller) {
          restoreAbortRef.current = null;
          setRestoring(null);
        }
        inputRef.current?.focus();
      }
    },
    [activateThread, closeHistoryOnSmallScreens],
  );

  const removeConversation = async (selected: string) => {
    if (pendingRef.current || deletingRef.current || restoring) return;
    deletingRef.current = true;
    setDeletingThreadId(selected);
    historyAbortRef.current?.abort();
    try {
      await deleteConversation(selected);
      setHistory((current) => current.status === "ready"
        ? { ...current, items: current.items.filter((item) => item.thread_id !== selected) }
        : current);
      if (threadRef.current === selected) startNewChat();
      refreshHistory(true);
    } catch {
      setHistoryNotice("Impossible de supprimer cette conversation. Réessayez.");
    } finally {
      deletingRef.current = false;
      setDeletingThreadId(null);
    }
  };

  return (
    <div className="assistant-page" data-thread-id={threadId}>
      <section className="ap-pills" aria-label="Capacités de l'assistant">
        {capabilityPills.map(({ icon: Icon, label, variant }, index) => (
          <span className={`ap-pill ap-pill-${variant}`} key={index}>
            <i aria-hidden="true">
              <Icon />
            </i>
            <span>{label}</span>
          </span>
        ))}
      </section>

      <OverviewCards />

      <div className={`ap-grid ap-grid-history ${historyOpen ? "" : "is-history-collapsed"}`}>
        {historyOpen && (
          <button
            type="button"
            className="ap-history-scrim"
            aria-label="Fermer l’historique"
            onClick={() => setHistoryOpen(false)}
          />
        )}
        <HistoryPanel
          state={history}
          activeThreadId={threadId}
          loadingThreadId={restoring}
          disabled={pending || restoring !== null || deletingThreadId !== null}
          deletingThreadId={deletingThreadId}
          onDelete={(selected) => void removeConversation(selected)}
          open={historyOpen}
          onSelect={(selected) => void selectConversation(selected)}
          onNewChat={startNewChat}
          onRetry={() => refreshHistory()}
          onClose={() => setHistoryOpen(false)}
        />
        <div className="ap-chat-column">
          {historyNotice && (
            <p className="ap-history-notice" role="alert">
              {historyNotice}
            </p>
          )}
          <ChatPanel
            messages={messages}
            pending={pending}
            draft={draft}
            onDraftChange={setDraft}
            onSend={() => void send(draft)}
            onSuggestion={(text) => void send(text)}
            onRetry={(text) => void send(text)}
            onNewChat={startNewChat}
            inputRef={inputRef}
            historyOpen={historyOpen}
            onToggleHistory={() => setHistoryOpen((value) => !value)}
            restoring={restoring !== null}
          />
        </div>
        <div className="ap-side">
          <PipelineCard />
          <MultilingualCard />
          <BackendResponseCard exchange={lastExchange} />
        </div>
      </div>
    </div>
  );
}
