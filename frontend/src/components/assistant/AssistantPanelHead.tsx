import type { ReactNode } from "react";
import type { IconType } from "react-icons";

/**
 * Panel header of the Assistant page, matching its reference design: a solid
 * blue icon tile (or a bare glyph for the chat card), a title and a subtitle.
 */
export function AssistantPanelHead({
  icon: Icon,
  title,
  subtitle,
  action,
  bare = false,
}: {
  icon: IconType;
  title: string;
  subtitle: string;
  action?: ReactNode;
  /** Bare glyph without a tile, as used by the discussion card. */
  bare?: boolean;
}) {
  return (
    <div className="ap-head">
      <span className={bare ? "ap-head-glyph" : "ap-head-tile"} aria-hidden="true">
        <Icon />
      </span>
      <div className="ap-head-copy">
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {action}
    </div>
  );
}
