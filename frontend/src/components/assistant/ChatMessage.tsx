import { FaRobot, FaRotateRight, FaTriangleExclamation, FaUser } from "react-icons/fa6";

import type { ChatMessage as ChatMessageModel } from "../../types/chat";
import { directionFor, guessScript } from "../../services/chat";
import { ProvenancePanel, knowledgeSourceLabel } from "./ProvenancePanel";
import { ResponseMetadata } from "./ResponseMetadata";
import { SourcesPanel } from "./SourcesPanel";
import { errorMessage, formatTime, routePill } from "./labels";

/**
 * One conversation row. Assistant text is rendered exactly as the backend
 * returned it: no rewriting, no translation, no appended content.
 */
export function ChatMessageRow({
  message,
  showDetails,
  onRetry,
}: {
  message: ChatMessageModel;
  /** Metadata and sources are attached to the latest assistant answer only. */
  showDetails: boolean;
  onRetry: (text: string) => void;
}) {
  if (message.author === "user") {
    // Direction here is presentation only; the backend classifies the language.
    const dir = directionFor(guessScript(message.text));
    return (
      <div className="ap-turn ap-turn-user">
        <div className="ap-row ap-row-user">
          <div className="ap-bubble ap-bubble-user" dir={dir}>
            {message.text}
          </div>
          <span className="ap-user-avatar" aria-hidden="true">
            <FaUser />
          </span>
        </div>
        <time className="ap-time ap-time-user">{formatTime(message.at)}</time>
      </div>
    );
  }

  if (message.author === "restored") {
    const source = knowledgeSourceLabel(message.knowledgeSource);
    return (
      <div className="ap-turn">
        <div className="ap-row ap-row-bot">
          <span className="ap-bot-avatar" aria-hidden="true">
            <FaRobot />
          </span>
          <div
            className={`ap-bubble ap-bubble-bot ${message.route === "securite" ? "ap-bubble-guarded" : ""}`}
            dir={message.script ? directionFor(message.script) : "auto"}
          >
            {message.text}
          </div>
        </div>
        <p className="ap-time ap-time-bot ap-restored-meta">
          {formatTime(message.at)} · Restauré de l’historique
          {message.route ? ` · route ${routePill(message.route)}` : ""}
          {source ? ` · ${source}` : ""}
        </p>
      </div>
    );
  }

  if (message.author === "error") {
    return (
      <div className="ap-turn">
        <div className="ap-row ap-row-bot">
          <span className="ap-bot-avatar ap-bot-avatar-error" aria-hidden="true">
            <FaTriangleExclamation />
          </span>
          <div className="ap-bubble ap-bubble-error" role="alert">
            <strong>{errorMessage(message.kind)}</strong>
            <button
              type="button"
              className="ap-retry"
              onClick={() => onRetry(message.retryMessage)}
            >
              <FaRotateRight aria-hidden="true" /> Réessayer
            </button>
          </div>
        </div>
        <time className="ap-time ap-time-bot">{formatTime(message.at)}</time>
      </div>
    );
  }

  // The backend tells us the script, so RTL is driven by real response data.
  const dir = directionFor(message.response.script);
  return (
    <div className="ap-turn">
      <div className="ap-row ap-row-bot">
        <span className="ap-bot-avatar" aria-hidden="true">
          <FaRobot />
        </span>
        <div
          className={`ap-bubble ap-bubble-bot ${message.response.blocked ? "ap-bubble-guarded" : ""}`}
          dir={dir}
        >
          {message.text}
        </div>
      </div>
      <time className="ap-time ap-time-bot">{formatTime(message.at)}</time>
      {showDetails && (
        <div className="ap-details">
          <ResponseMetadata response={message.response} />
          <ProvenancePanel response={message.response} />
          <SourcesPanel
            citations={message.response.citations}
            internalSource={message.response.route === "formation_elearning"
              ? message.response.internal_pedagogical_source : null}
          />
        </div>
      )}
    </div>
  );
}
