import { motion } from "framer-motion";
import type { Language } from "../data/content";
import { content } from "../data/content";

interface ProjectsProps {
  language: Language;
}

export function Projects({ language }: ProjectsProps) {
  return (
    <section id="projects" className="relative overflow-hidden border-b border-black/5 bg-[#fbfbfb] px-4 py-24 sm:px-6 lg:px-8">
      <div className="noise-layer opacity-60" />
      <div className="mx-auto max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.45 }}
          transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
          className="mb-12 grid gap-5 md:grid-cols-[1fr_0.9fr]"
        >
          <div>
            <p className="mb-3 text-[11px] font-bold uppercase tracking-normal text-black/[0.38]">Projects</p>
            <h2 className="text-4xl font-black tracking-normal text-black sm:text-5xl">{content.projects.title[language]}</h2>
          </div>
          <p className="max-w-xl text-sm leading-7 text-black/[0.52] md:pt-12">{content.projects.subtitle[language]}</p>
        </motion.div>

        <div className="space-y-5">
          {content.projects.items.map((project, index) => (
            <motion.article
              key={project.number}
              initial={{ opacity: 0, y: 42 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.28 }}
              transition={{ duration: 0.66, delay: index * 0.08, ease: [0.22, 1, 0.36, 1] }}
              whileHover={{ y: -6 }}
              className="group relative overflow-hidden rounded-[6px] border border-black/[0.07] bg-white/[0.72] p-5 shadow-soft transition hover:border-black/[0.28] hover:bg-white sm:p-8"
            >
              <div className="grid gap-8 lg:grid-cols-[1fr_210px]">
                <div className="relative z-10">
                  <p className="mb-5 text-[11px] font-bold uppercase tracking-normal text-black/[0.36]">{project.year}</p>
                  <h3 className="text-2xl font-black tracking-normal text-black sm:text-3xl">{project.title[language]}</h3>
                  <p className="mt-4 max-w-3xl text-sm leading-7 text-black/[0.56]">{project.description[language]}</p>
                  <div className="mt-7 flex flex-wrap gap-2">
                    {project.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full border border-black/[0.08] bg-black/[0.03] px-3 py-1.5 text-[10px] font-bold uppercase tracking-normal text-black/[0.62]"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="pointer-events-none flex items-start justify-end">
                  <span className="font-black leading-none tracking-normal text-black/[0.07] transition group-hover:text-black/[0.12] text-[clamp(4.8rem,13vw,9rem)]">
                    {project.number}
                  </span>
                </div>
              </div>
            </motion.article>
          ))}
        </div>
      </div>
    </section>
  );
}
