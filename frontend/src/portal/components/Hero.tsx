import { type PointerEvent, useEffect, useState } from "react";
import { motion, useMotionTemplate, useMotionValue, useSpring } from "framer-motion";
import { ArrowDownRight } from "lucide-react";
import type { Language } from "../data/content";
import { content } from "../data/content";

interface HeroProps {
  language: Language;
}

interface HeroCopyProps {
  language: Language;
  masked?: boolean;
}

function formatHeroTitle(title: string) {
  return title.split(" ").map((part, index, parts) => (
    <span key={`${part}-${index}`}>
      {part}
      {index < parts.length - 1 ? " " : ""}
      {index === 0 && parts.length > 2 ? <br className="sm:hidden" /> : null}
    </span>
  ));
}

function HeroCopy({ language, masked = false }: HeroCopyProps) {
  const title = masked ? content.hero.maskedTitle[language] : content.hero.title[language];

  return (
    <div className="relative z-20 mx-auto flex min-h-[calc(100vh-3.5rem)] w-full max-w-7xl flex-col justify-center">
      <motion.p
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.65, delay: 0.15 }}
        className={`absolute inset-x-0 top-[29%] mx-auto w-full max-w-xl px-4 text-center text-[11px] font-semibold uppercase tracking-normal ${
          masked ? "text-white/55" : "text-black/[0.45]"
        }`}
      >
        {content.hero.role[language]}
      </motion.p>

      <div className="mx-auto w-full max-w-5xl py-24 text-center sm:py-28">
        <motion.h1
          initial={{ opacity: 0, y: 36, rotate: -4 }}
          animate={{ opacity: 1, y: 0, rotate: -2 }}
          transition={{ duration: 0.95, ease: [0.22, 1, 0.36, 1] }}
          className={`select-none text-balance text-[clamp(3rem,12vw,9.8rem)] font-black uppercase leading-[0.88] tracking-normal ${
            masked ? "text-white" : "text-black"
          }`}
        >
          {masked ? (
            <span className="inline-block max-w-[9em] text-[clamp(2.9rem,12vw,9.5rem)] normal-case leading-[0.98] sm:max-w-none">
              {title}
            </span>
          ) : (
            formatHeroTitle(title)
          )}
        </motion.h1>
      </div>

      <motion.p
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.65, delay: 0.75 }}
        className={`absolute inset-x-0 top-[72%] mx-auto w-full max-w-xl px-4 text-center text-sm leading-6 ${
          masked ? "text-white/58" : "text-black/50"
        }`}
      >
        {content.hero.tinyNote[language]}
      </motion.p>

      <motion.a
        href="#skills"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.65, delay: 1 }}
        className={`absolute bottom-8 left-1/2 hidden -translate-x-1/2 items-center gap-2 text-[10px] font-bold uppercase tracking-normal transition md:flex ${
          masked ? "text-white/45" : "text-black/[0.35] hover:text-black"
        }`}
      >
        Scroll
        <ArrowDownRight size={15} />
      </motion.a>
    </div>
  );
}

export function Hero({ language }: HeroProps) {
  const [isHovering, setIsHovering] = useState(false);
  const mouseX = useMotionValue(-320);
  const mouseY = useMotionValue(260);
  const maskOpacity = useMotionValue(0);
  const smoothX = useSpring(mouseX, { stiffness: 150, damping: 24, mass: 0.45 });
  const smoothY = useSpring(mouseY, { stiffness: 150, damping: 24, mass: 0.45 });
  const smoothOpacity = useSpring(maskOpacity, { stiffness: 210, damping: 28, mass: 0.35 });
  const circleMask = useMotionTemplate`circle(154px at ${smoothX}px ${smoothY}px)`;

  useEffect(() => {
    maskOpacity.set(isHovering ? 1 : 0);
  }, [isHovering, maskOpacity]);

  const handlePointerMove = (event: PointerEvent<HTMLElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    mouseX.set(event.clientX - bounds.left);
    mouseY.set(event.clientY - bounds.top);
    setIsHovering(true);
  };

  return (
    <section
      id="about"
      onPointerEnter={() => setIsHovering(true)}
      onPointerMove={handlePointerMove}
      onPointerLeave={() => setIsHovering(false)}
      className="relative flex min-h-screen overflow-hidden border-b border-black/5 bg-white px-4 pt-14 sm:px-6 lg:px-8"
    >
      <div className="noise-layer" />
      <div className="grid-layer" />

      <HeroCopy language={language} />

      <motion.div
        aria-hidden="true"
        style={{
          opacity: smoothOpacity,
          clipPath: circleMask,
          WebkitClipPath: circleMask
        }}
        className="pointer-events-none absolute inset-0 z-30 flex overflow-hidden bg-black px-4 pt-14 text-white sm:px-6 lg:px-8"
      >
        <div className="noise-layer opacity-20" />
        <div className="grid-layer opacity-20" />
        <HeroCopy language={language} masked />
      </motion.div>
    </section>
  );
}
