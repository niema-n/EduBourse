import type { ComponentType } from "react";
import { FaGlobe, FaRegLightbulb } from "react-icons/fa6";

import { AssistantPanelHead } from "./AssistantPanelHead";
import { FlagAR, FlagEN, FlagFR, FlagMA } from "./LanguageFlag";

/**
 * Project capability statement. Detection and translation happen entirely in
 * the backend; the frontend never translates a question or an answer.
 */
const languages: {
  code: string;
  name: string;
  flag: ComponentType<{ title: string }>;
  flagTitle: string;
}[] = [
  { code: "FR", name: "Français", flag: FlagFR, flagTitle: "Drapeau de la France" },
  { code: "EN", name: "Anglais", flag: FlagEN, flagTitle: "Drapeau du Royaume-Uni" },
  { code: "AR", name: "Arabe", flag: FlagAR, flagTitle: "Langue arabe" },
  { code: "Darija", name: "Darija", flag: FlagMA, flagTitle: "Drapeau du Maroc" },
];

export function MultilingualCard() {
  return (
    <section className="ap-panel">
      <AssistantPanelHead
        icon={FaGlobe}
        title="Aperçu multilingue"
        subtitle="Répond dans la langue de l’utilisateur"
      />
      <ul className="ap-langs">
        {languages.map(({ code, name, flag: Flag, flagTitle }) => (
          <li className="ap-lang" key={code}>
            <Flag title={flagTitle} />
            <span className="ap-lang-copy">
              <strong>{code}</strong>
              <small>{name}</small>
            </span>
          </li>
        ))}
      </ul>
      <p className="ap-lang-note">
        <FaRegLightbulb aria-hidden="true" />
        <span>
          L’assistant détecte automatiquement la langue de votre question et y répond
          naturellement.
        </span>
      </p>
    </section>
  );
}
