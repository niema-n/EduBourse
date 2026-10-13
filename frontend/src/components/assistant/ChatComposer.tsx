import { useEffect } from "react";
import type { KeyboardEvent as ReactKeyboardEvent } from "react";
import { FaMicrophone, FaPaperclip, FaPaperPlane } from "react-icons/fa6";
import { useNavigate } from "react-router-dom";

import { MESSAGE_MAX_LENGTH } from "../../services/chat";

/**
 * Message composer. Enter sends, Shift+Enter inserts a newline, and the send
 * button is disabled while a request is in flight so a question cannot be
 * submitted twice.
 */
export function ChatComposer({
  value,
  onChange,
  onSubmit,
  pending,
  inputRef,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  pending: boolean;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
}) {
  const navigate = useNavigate();
  const canSend = value.trim().length > 0 && !pending;

  // Grow the textarea with its content, up to the CSS max-height.
  useEffect(() => {
    const node = inputRef.current;
    if (!node) return;
    node.style.height = "auto";
    node.style.height = `${Math.min(node.scrollHeight, 132)}px`;
  }, [value, inputRef]);

  const onKeyDown = (event: ReactKeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (canSend) onSubmit();
    }
  };

  return (
    <form
      className="ap-composer"
      onSubmit={(event) => {
        event.preventDefault();
        if (canSend) onSubmit();
      }}
    >
      <div className="ap-input">
        <button
          type="button"
          className="ap-input-tool"
          disabled
          aria-label="Pièces jointes non disponibles"
          title="Pièces jointes non disponibles"
        >
          <FaPaperclip aria-hidden="true" />
        </button>

        <label className="visually-hidden" htmlFor="assistant-question">
          Votre question
        </label>
        <textarea
          id="assistant-question"
          ref={inputRef}
          rows={1}
          value={value}
          maxLength={MESSAGE_MAX_LENGTH}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Posez votre question..."
        />

        {/* Voice is delivered on its own page (F4). This is a deliberate shortcut
            there, not a recorder: it never requests microphone access. */}
        <span className="mic-wrap">
          <button
            type="button"
            className="ap-input-tool mic-button"
            onClick={() => navigate("/voice")}
            aria-label="Voice-to-Voice — disponible dans la section dédiée"
            aria-describedby="mic-tooltip"
          >
            <FaMicrophone aria-hidden="true" />
          </button>
          <span id="mic-tooltip" role="tooltip" className="mic-tooltip">
            Voice-to-Voice — disponible dans la section dédiée
          </span>
        </span>
      </div>

      <button type="submit" className="ap-send" disabled={!canSend} aria-label="Envoyer la question">
        <FaPaperPlane aria-hidden="true" />
      </button>
    </form>
  );
}
