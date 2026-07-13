import { motion, type Variants } from "framer-motion";
import type { Language } from "../data/content";
import { content } from "../data/content";

interface SkillsProps {
  language: Language;
}

const smoothEase = [0.22, 1, 0.36, 1] as const;

const containerVariants: Variants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.045
    }
  }
};

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 24, scale: 0.98 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.52, ease: smoothEase }
  }
};

export function Skills({ language }: SkillsProps) {
  const skillCards = content.skills.bubbles.slice(0, 16);

  return (
    <section id="skills" className="relative overflow-hidden border-b border-black/5 bg-white px-4 py-24 sm:px-6 lg:px-8">
      <div className="grid-layer" />
      <div className="noise-layer opacity-50" />

      <div className="relative mx-auto max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.45 }}
          transition={{ duration: 0.65, ease: smoothEase }}
          className="mb-12 max-w-2xl"
        >
          <p className="mb-3 text-[11px] font-bold uppercase tracking-normal text-black/[0.38]">Skills</p>
          <h2 className="text-4xl font-black tracking-normal text-black sm:text-5xl">{content.skills.title[language]}</h2>
          <p className="mt-5 text-sm leading-7 text-black/[0.54]">{content.skills.subtitle[language]}</p>
        </motion.div>

        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, amount: 0.2 }}
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          {skillCards.map((skill, index) => (
            <motion.article
              key={skill.label.zh}
              variants={cardVariants}
              whileHover={{ y: -5 }}
              className="group relative min-h-28 overflow-hidden rounded-[6px] border border-black/[0.07] bg-white/78 p-5 shadow-soft backdrop-blur-sm transition hover:border-black/[0.26] hover:bg-white"
            >
              <span className="absolute right-4 top-4 text-3xl font-black leading-none tracking-normal text-black/[0.06] transition group-hover:text-black/[0.1]">
                {String(index + 1).padStart(2, "0")}
              </span>
              <div className="relative z-10 flex h-full flex-col justify-between gap-6">
                <p className="text-[10px] font-bold uppercase tracking-normal text-black/[0.34]">
                  {skill.weight === "lg" ? "Core" : skill.weight === "md" ? "Stack" : "Tool"}
                </p>
                <h3 className="max-w-[9rem] text-lg font-black uppercase leading-tight tracking-normal text-black">
                  {skill.label[language]}
                </h3>
              </div>
            </motion.article>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
