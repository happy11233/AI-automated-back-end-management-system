import { Contact } from "./components/Contact";
import { Hero } from "./components/Hero";
import { Navbar } from "./components/Navbar";
import { Projects } from "./components/Projects";
import { Skills } from "./components/Skills";
import type { Language } from "./data/content";
import { type ProjectTarget } from "../workspace/types";

export function PublicPortal(props: {
  language: Language;
  onLanguageChange: () => void;
  onLLMClick: () => void;
  isAuthenticated: boolean;
  onProjectClick: (target: ProjectTarget) => void;
}) {
  return (
    <main className="portfolioShell">
      <Navbar
        language={props.language}
        onLanguageChange={props.onLanguageChange}
        onLLMClick={props.onLLMClick}
      />
      <Hero language={props.language} />
      <Skills language={props.language} />
      <Projects language={props.language} isAuthenticated={props.isAuthenticated} onProjectClick={props.onProjectClick} />
      <Contact language={props.language} />
    </main>
  );
}
