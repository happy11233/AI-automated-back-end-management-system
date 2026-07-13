import { Bot, ExternalLink, Languages, LogIn, MapPin } from "lucide-react";
import { motion } from "framer-motion";
import type { Language } from "../data/content";
import { content } from "../data/content";

interface NavbarProps {
  language: Language;
  onLanguageChange: () => void;
  onLoginClick: () => void;
  onLLMClick: () => void;
}

export function Navbar({ language, onLanguageChange, onLoginClick, onLLMClick }: NavbarProps) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className="fixed left-0 right-0 top-0 z-50 border-b border-black/5 bg-white/[0.78] backdrop-blur-xl"
    >
      <nav className="mx-auto flex h-14 w-full max-w-7xl items-center justify-between px-4 text-[11px] font-semibold uppercase tracking-normal text-black sm:px-6 lg:px-8">
        <a href="#about" className="font-black tracking-[0.16em]">
          XIANG
        </a>

        <div className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-1 rounded-full border border-black/5 bg-black/[0.025] p-1 md:flex">
          {content.nav.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="rounded-full px-4 py-2 text-black/[0.72] transition hover:bg-black/[0.07] hover:text-black"
            >
              {item.label[language]}
            </a>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="hidden items-center gap-1.5 text-black/[0.62] sm:flex">
            <MapPin size={13} strokeWidth={2.2}/>
            {content.location[language]}
          </span>
          <button
              type="button"
              onClick={onLoginClick}
              className="inline-flex h-9 items-center gap-1.5 rounded-full border border-black/[0.08] bg-white px-3 text-black/[0.78] shadow-sm transition hover:bg-black/[0.07] hover:text-black"
          >
            <LogIn size={14} strokeWidth={2.2}/>
            {language === "zh" ? "登录" : "Login"}
          </button>
          <button
              type="button"
              onClick={onLLMClick}
              className="inline-flex h-9 items-center gap-1.5 rounded-full border border-black/[0.08] bg-white px-3 text-black/[0.78] shadow-sm transition hover:bg-black/[0.07] hover:text-black"
          >
            <Bot size={14} strokeWidth={2.2}/>
            {language === "zh" ? "大模型" : "AI"}
          </button>
          <button
              type="button"
              onClick={() => window.open("https://github.com/happy11233", "_blank")}
              className="inline-flex h-9 items-center gap-1.5 rounded-full border border-black/[0.08] bg-white px-3 text-black/[0.78] shadow-sm transition hover:bg-black/[0.07] hover:text-black"
          >
            <ExternalLink size={14} strokeWidth={2.2}/>
            {language === "zh" ? "Github" : "Github"}
          </button>
          <button
              type="button"
              onClick={onLanguageChange}
              className="inline-flex h-9 items-center gap-1.5 rounded-full border border-black/[0.08] bg-white px-3 text-black/[0.78] shadow-sm transition hover:bg-black/[0.07] hover:text-black"
              aria-label="Switch language"
          >
            <Languages size={14} strokeWidth={2.2}/>
            {language === "zh" ? "EN" : "中"}
          </button>
        </div>
      </nav>
    </motion.header>
  );
}
