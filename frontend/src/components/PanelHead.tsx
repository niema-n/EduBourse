import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

/** Shared accent palette of the EduBourse design system (see styles.css .tone-*). */
export type Tone = "blue" | "green" | "cyan" | "purple" | "orange" | "red";

/**
 * Panel header used by the Dashboard and the Assistant page so both keep the
 * exact same card grammar. Markup must stay identical to avoid a Dashboard
 * visual regression.
 */
export function PanelHead({
  icon: Icon,
  tone = "blue",
  title,
  subtitle,
  action,
}: {
  icon: LucideIcon;
  tone?: Tone;
  title: string;
  subtitle: string;
  action?: ReactNode;
}) {
  return (
    <div className="panel-head">
      <span className={`panel-icon tone-${tone}`}>
        <Icon size={20} />
      </span>
      <div className="panel-title">
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {action}
    </div>
  );
}
