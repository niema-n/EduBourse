import type { IconType } from "react-icons";
import {
  FaCode,
  FaCrosshairs,
  FaDatabase,
  FaFileLines,
  FaGlobe,
  FaQuoteLeft,
} from "react-icons/fa6";

import type { ChatResponseBody } from "../../types/chat";
import { routePill } from "./labels";

/**
 * Metadata strip under the latest assistant answer. Every tile reads a field
 * the backend actually returned; nothing is derived or invented. `grounded` is
 * nullable in the contract and is reported as such instead of defaulting to Oui.
 */
export function ResponseMetadata({ response }: { response: ChatResponseBody }) {
  const grounded =
    response.grounded === null
      ? { text: "N/A", tone: "muted" }
      : response.grounded
        ? { text: "Oui", tone: "green" }
        : { text: "Non", tone: "orange" };

  const tiles: { icon: IconType; label: string; value: string; tone: string; code?: boolean }[] = [
    { icon: FaCrosshairs, label: "Route", value: routePill(response.route), tone: "blue" },
    { icon: FaDatabase, label: "Grounded", value: grounded.text, tone: grounded.tone },
    { icon: FaGlobe, label: "Langue", value: response.language, tone: "blue" },
    { icon: FaFileLines, label: "Script", value: response.script, tone: "blue" },
    { icon: FaQuoteLeft, label: "Citations", value: String(response.citations.length), tone: "blue" },
    { icon: FaCode, label: "Thread ID", value: response.thread_id, tone: "plain", code: true },
  ];

  return (
    <dl className="ap-meta" aria-label="Informations sur la réponse">
      {tiles.map(({ icon: Icon, label, value, tone, code }) => (
        <div className={`ap-meta-tile ${code ? "ap-meta-tile-thread" : ""}`} key={label}>
          <Icon className="ap-meta-icon" aria-hidden="true" />
          <div className="ap-meta-copy">
            <dt>{label}</dt>
            <dd>
              {code ? (
                <code title={value}>{value}</code>
              ) : (
                <span className={`ap-meta-pill ap-pill-tone-${tone}`}>{value}</span>
              )}
            </dd>
          </div>
        </div>
      ))}
    </dl>
  );
}
