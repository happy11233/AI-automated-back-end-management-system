import { useState } from "react";
import { motion } from "framer-motion";
import { SendHorizontal } from "lucide-react";
import type { Language } from "../data/content";
import { content } from "../data/content";

interface ContactProps {
  language: Language;
}

export function Contact({ language }: ContactProps) {
  const [sent, setSent] = useState(false);

  return (
    <section id="contact" className="relative overflow-hidden bg-white px-4 py-24 sm:px-6 lg:px-8">
      <div className="grid-layer" />
      <motion.div
        aria-hidden="true"
        animate={{ y: [0, -20, 10, 0], x: [0, 18, -8, 0], scale: [1, 1.05, 0.96, 1] }}
        transition={{ duration: 9, repeat: Infinity, ease: "easeInOut" }}
        className="absolute bottom-24 right-[9%] h-48 w-48 rounded-full border border-black/[0.08]"
      />
      <div className="absolute bottom-20 left-[7%] h-0 w-0 border-b-[88px] border-l-[50px] border-r-[50px] border-b-black/[0.05] border-l-transparent border-r-transparent" />

      <div className="relative mx-auto max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
          className="mb-12 grid gap-8 md:grid-cols-[0.95fr_1fr]"
        >
          <div>
            <p className="mb-3 text-[11px] font-bold uppercase tracking-normal text-black/[0.38]">Collab</p>
            <h2 className="text-4xl font-black tracking-normal text-black sm:text-5xl">{content.contact.title[language]}</h2>
          </div>
          <div>
            <p className="text-lg leading-8 text-black/[0.70]">{content.contact.subtitle[language]}</p>
            <dl className="mt-8 space-y-3 text-sm">
              {content.contact.meta.map((item) => (
                <div key={item.label.zh} className="grid grid-cols-[92px_1fr] gap-4">
                  <dt className="font-bold text-black/[0.42]">{item.label[language]}</dt>
                  <dd className="text-black/[0.76]">{item.value[language]}</dd>
                </div>
              ))}
            </dl>
          </div>
        </motion.div>

        <div className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
          <motion.form
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
            onSubmit={(event) => {
              event.preventDefault();
              setSent(true);
            }}
            className="rounded-[6px] border border-black/[0.07] bg-white/[0.84] p-5 shadow-soft sm:p-8"
          >
            <h3 className="mb-7 text-sm font-black uppercase tracking-normal text-black">{content.contact.form.title[language]}</h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-[11px] font-bold uppercase tracking-normal text-black/[0.42]">
                {content.contact.form.name[language]}
                <input className="mt-2 h-12 w-full rounded-none border border-black/10 bg-white px-4 text-sm text-black outline-none transition placeholder:text-black/25 focus:border-black" />
              </label>
              <label className="block text-[11px] font-bold uppercase tracking-normal text-black/[0.42]">
                {content.contact.form.email[language]}
                <input
                  type="email"
                  className="mt-2 h-12 w-full rounded-none border border-black/10 bg-white px-4 text-sm text-black outline-none transition placeholder:text-black/25 focus:border-black"
                />
              </label>
            </div>
            <label className="mt-4 block text-[11px] font-bold uppercase tracking-normal text-black/[0.42]">
              {content.contact.form.message[language]}
              <textarea className="mt-2 min-h-36 w-full resize-none rounded-none border border-black/10 bg-white px-4 py-3 text-sm text-black outline-none transition placeholder:text-black/25 focus:border-black" />
            </label>
            <button
              type="submit"
              className="mt-5 inline-flex h-12 w-full items-center justify-center gap-2 rounded-full bg-black px-6 text-sm font-bold text-white transition hover:bg-black/[0.82]"
            >
              {content.contact.form.submit[language]}
              <SendHorizontal size={16} strokeWidth={2.2} />
            </button>
            {sent && (
              <motion.p
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-4 rounded-full border border-black/[0.08] bg-black/[0.03] px-4 py-3 text-center text-xs font-semibold text-black/[0.64]"
              >
                {content.contact.form.success[language]}
              </motion.p>
            )}
          </motion.form>

          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.65, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
            className="rounded-[6px] border border-black/[0.07] bg-white/[0.74] p-5 shadow-soft sm:p-8"
          >
            <h3 className="mb-7 text-sm font-black uppercase tracking-normal text-black">{content.contact.methodsTitle[language]}</h3>
            <div className="grid gap-4">
              {content.contact.methods.map((method) => {
                const Icon = method.icon;

                return (
                  <a
                    key={method.title.zh}
                    href={method.href}
                    className="group flex items-center gap-4 rounded-[6px] border border-black/[0.07] bg-white p-4 transition hover:-translate-y-1 hover:border-black/[0.24]"
                  >
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-black text-white">
                      <Icon size={18} strokeWidth={2.1} />
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-black text-black">{method.title[language]}</span>
                      <span className="mt-1 block truncate text-xs text-black/[0.48]">{method.value}</span>
                    </span>
                  </a>
                );
              })}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
