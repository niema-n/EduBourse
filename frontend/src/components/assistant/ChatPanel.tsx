import { useEffect, useRef } from "react";
import { FaCirclePlus, FaClockRotateLeft, FaComments, FaRobot, FaWandMagicSparkles } from "react-icons/fa6";

import type { ChatMessage } from "../../types/chat";
import { AssistantPanelHead } from "./AssistantPanelHead";
import { ChatComposer } from "./ChatComposer";
import { ChatMessageRow } from "./ChatMessage";

/** Starter questions; clicking one sends that exact text to the real backend. */
const suggestions = [
  "C’est quoi une action ?",
  "Qu’est-ce que le MASI ?",
  "Comment fonctionne le Championnat de la Bourse ?",
  "Fais-moi un quiz",
];

export function ChatPanel({
  messages,
  pending,
  draft,
  onDraftChange,
  onSend,
  onSuggestion,
  onNewChat,
  onRetry,
  inputRef,
  historyOpen,
  onToggleHistory,
  restoring = false,
}: {
  historyOpen: boolean;
  onToggleHistory: () => void;
  /** True while an old conversation is being fetched from the backend. */
  restoring?: boolean;
  messages: ChatMessage[];
  pending: boolean;
  draft: string;
  onDraftChange: (value: string) => void;
  onSend: () => void;
  onSuggestion: (text: string) => void;
  onNewChat: () => void;
  onRetry: (text: string) => void;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Keep the newest turn in view as the conversation grows.
  useEffect(() => {
    const node = scrollRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages, pending]);

  const lastAssistantId = [...messages].reverse().find((item) => item.author === "assistant")?.id;

  return (
    <section className="ap-panel ap-chat">
      <AssistantPanelHead
        bare
        icon={FaComments}
        title="Discussion avec l’Assistant IA"
        subtitle="Posez vos questions sur la bourse, l’investissement et la finance"
        action={
          <div className="ap-chat-actions">
            <button
              type="button"
              className="ap-history-toggle"
              onClick={onToggleHistory}
              aria-expanded={historyOpen}
              aria-controls="assistant-history"
            >
              <FaClockRotateLeft aria-hidden="true" /> {historyOpen ? "Masquer l’historique" : "Historique"}
            </button>
            <button
              type="button"
              className="ap-new-chat"
              onClick={onNewChat}
              aria-label="Démarrer un nouveau chat"
            >
              <FaCirclePlus aria-hidden="true" /> Nouveau chat
            </button>
          </div>
        }
      />

      <div className="ap-thread" ref={scrollRef} aria-live="polite" aria-busy={pending}>
        {restoring ? (
          <p className="ap-restoring">Chargement de la conversation...</p>
        ) : messages.length === 0 && !pending ? (
          <div className="ap-welcome">
            <span className="ap-bot-avatar ap-welcome-avatar" aria-hidden="true">
              <FaRobot />
            </span>
            <strong>Posez votre première question</strong>
            <small>
              L’assistant répond en français, anglais, arabe et darija, à partir des sources
              officielles indexées.
            </small>
            <div className="ap-suggestions">
              {suggestions.map((text) => (
                <button
                  type="button"
                  className="ap-suggestion"
                  key={text}
                  onClick={() => onSuggestion(text)}
                >
                  <FaWandMagicSparkles aria-hidden="true" /> {text}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <ChatMessageRow
              key={message.id}
              message={message}
              showDetails={message.id === lastAssistantId}
              onRetry={onRetry}
            />
          ))
        )}

        {pending && (
          <div className="ap-row ap-row-bot">
            <span className="ap-bot-avatar" aria-hidden="true">
              <FaRobot />
            </span>
            <div className="ap-bubble ap-bubble-bot ap-typing">
              <span className="ap-dots" aria-hidden="true">
                <i />
                <i />
                <i />
              </span>
              <span>EduBourse réfléchit...</span>
            </div>
          </div>
        )}
      </div>

      <ChatComposer
        value={draft}
        onChange={onDraftChange}
        onSubmit={onSend}
        pending={pending || restoring}
        inputRef={inputRef}
      />
    </section>
  );
}
