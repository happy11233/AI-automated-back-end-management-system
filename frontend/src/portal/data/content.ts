import type { LucideIcon } from "lucide-react";
import {
  BrainCircuit,
  Code2,
  Github,
  Languages,
  Mail,
  MessageCircle,
  ServerCog,
  Workflow
} from "lucide-react";

export type Language = "zh" | "en";

export interface LocalizedText {
  zh: string;
  en: string;
}

export interface NavItem {
  label: LocalizedText;
  href: string;
}

export interface Skill {
  icon: LucideIcon;
  name: LocalizedText;
  description: LocalizedText;
  stats: Array<{
    value: string;
    label: LocalizedText;
  }>;
}

export interface SkillBubble {
  label: LocalizedText;
  weight: "sm" | "md" | "lg";
}

export interface Project {
  number: string;
  title: LocalizedText;
  year: string;
  description: LocalizedText;
  tags: string[];
}

export interface ContactMethod {
  icon: LucideIcon;
  title: LocalizedText;
  value: string;
  href: string;
}

export interface LanguageContent {
  nav: NavItem[];
  location: LocalizedText;
  hero: {
    title: LocalizedText;
    maskedTitle: LocalizedText;
    role: LocalizedText;
    tinyNote: LocalizedText;
  };
  skills: {
    title: LocalizedText;
    subtitle: LocalizedText;
    items: Skill[];
    bubbles: SkillBubble[];
  };
  projects: {
    title: LocalizedText;
    subtitle: LocalizedText;
    items: Project[];
  };
  contact: {
    title: LocalizedText;
    subtitle: LocalizedText;
    meta: Array<{
      label: LocalizedText;
      value: LocalizedText;
    }>;
    form: {
      title: LocalizedText;
      name: LocalizedText;
      email: LocalizedText;
      message: LocalizedText;
      submit: LocalizedText;
      success: LocalizedText;
    };
    methodsTitle: LocalizedText;
    methods: ContactMethod[];
  };
}

export const content: LanguageContent = {
  nav: [
    { label: { zh: "关于", en: "About" }, href: "#about" },
    { label: { zh: "技能", en: "Skills" }, href: "#skills" },
    { label: { zh: "项目", en: "Projects" }, href: "#projects" },
    { label: { zh: "联系", en: "Contact" }, href: "#contact" }
  ],
  location: {
    zh: "广东深圳",
    en: "Shenzhen, Guangdong"
  },
  hero: {
    title: {
      zh: "HELLO, I'M XIANG",
      en: "HELLO, I'M XIANG"
    },
    maskedTitle: {
      zh: "你好，我是向",
      en: "你好，我是向"
    },
    role: {
      zh: "个人简历",
      en: "personal resume"
    },
    tinyNote: {
      zh: "本网页用来展示个人简历。",
      en: "This webpage is used to display the personal resume."
    }
  },
  skills: {
    title: {
      zh: "专业技能",
      en: "Professional Skills"
    },
    subtitle: {
      zh: "目前所掌握的技能",
      en: "The skills currently at one's disposal."
    },
    items: [

    ],
    bubbles: [
      { label: { zh: "Python", en: "Python" }, weight: "lg" },
      { label: { zh: "AI Agent", en: "AI Agent" }, weight: "lg" },
      { label: { zh: "LLM", en: "LLM" }, weight: "md" },
      { label: { zh: "RAG", en: "RAG" }, weight: "lg" },
      { label: { zh: "Tool Calling", en: "Tool Calling" }, weight: "md" },
      { label: { zh: "MCP", en: "MCP" }, weight: "md" },
      { label: { zh: "FastAPI", en: "FastAPI" }, weight: "md" },
      { label: { zh: "LangChain", en: "LangChain" }, weight: "sm" },
      { label: { zh: "向量检索", en: "Vector DB" }, weight: "md" },
      { label: { zh: "工具调用", en: "Tool Calling" }, weight: "sm" },
      { label: { zh: "Prompt", en: "Prompt" }, weight: "sm" },
      { label: { zh: "MYSQL", en: "MYSQL" }, weight: "sm" },
      { label: { zh: "Docker", en: "Docker" }, weight: "sm" },
      { label: { zh: "Redis", en: "Redis" }, weight: "md" },
      { label: { zh: "LangGraph", en: "LangGraph" }, weight: "sm" },
      { label: { zh: "Nginx", en: "Nginx" }, weight: "sm" },
      { label: { zh: "Embedding", en: "Embedding" }, weight: "sm" },
      { label: { zh: "向量数据库", en: "Vector Store" }, weight: "md" },
      { label: { zh: "lora微调", en: "lora" }, weight: "sm" },
      { label: { zh: "API 设计", en: "API Design" }, weight: "sm" },
      { label: { zh: "权限系统", en: "Auth" }, weight: "sm" },
      { label: { zh: "LINUX", en: "LINUX" }, weight: "md" },
      { label: { zh: "Function Calling", en: "Function Calling" }, weight: "sm" },
      { label: { zh: "JAVA", en: "JAVA" }, weight: "sm" },
      { label: { zh: "部署", en: "Deployment" }, weight: "sm" }
    ]
  },
  projects: {
    title: {
      zh: "项目经历",
      en: "Projects"
    },
    subtitle: {
      zh: "围绕 AI 应用、知识管理和个人表达的可运行项目。",
      en: "Runnable work across AI products, knowledge management and personal expression."
    },
    items: [
      {
        number: "01",
        title: { zh: "音乐共享管理系统", en: "Music Sharing Management System" },
        year: "2025",
        description: {
          zh: "面向音乐资源上传、共享、检索和用户管理的管理系统，使用的前后端技术，强调清晰权限与稳定接口。",
          en: "A full-stack system for uploading, sharing, searching and managing music resources with clear permissions and stable APIs."
        },
        tags: ["VUE", "Bootstrap", "SQL", "JAVA"]
      },
      {
        number: "02",
        title: { zh: "个人介绍网站", en: "Personal Introduction Website" },
        year: "2026",
        description: {
          zh: "以极简视觉和响应式布局呈现个人经历、项目与联系方式，已通过腾讯云服务器部署到公网。",
          en: "A minimalist responsive website for personal story, projects and contact details, ready for public or private deployment."
        },
        tags: ["React", "TypeScript", "Motion", "Tailwind"]
      },
      {
        number: "03",
        title: { zh: "RAG 知识库系统", en: "RAG Knowledge Base System" },
        year: "2026",
        description: {
          zh: "构建可检索、可溯源、可迭代的私域知识问答链路，整合 LLM、Embedding 与文档处理。",
          en: "A retrieval-augmented private knowledge QA flow integrating LLMs, embeddings and document processing."
        },
        tags: ["Python", "LLM", "RAG", "AI Agent"]
      }
    ]
  },
  contact: {
    title: {
      zh: "与我联系",
      en: "Contact Me"
    },
    subtitle: {
      zh: "Looking forward to creating meaningful AI products with like-minded partners.",
      en: "Looking forward to creating meaningful AI products with like-minded partners."
    },
    meta: [
      {
        label: { zh: "位置", en: "Location" },
        value: { zh: "广东深圳", en: "Shenzhen, Guangdong" }
      },
      {
        label: { zh: "期望职位", en: "Expected Position" },
        value: { zh: "AI/前端/后端开发,部署运维", en: "AI/ Front-end/Back-end development, deployment and operation maintenance" }
      },
      {
        label: { zh: "技能", en: "Skills" },
        value: { zh: "Python / AI Agent / LLM / RAG / Linux", en: "Python / AI Agent / LLM / RAG / Linux" }
      }
    ],
    form: {
      title: { zh: "快速联系", en: "Quick Contact" },
      name: { zh: "你的姓名", en: "Your Name" },
      email: { zh: "邮箱地址", en: "Email Address" },
      message: { zh: "留言内容", en: "Message" },
      submit: { zh: "发送消息", en: "Send Message" },
      success: {
        zh: "已收到你的消息，我会尽快回复。",
        en: "Message received. I will get back to you soon."
      }
    },
    methodsTitle: {
      zh: "联系方式",
      en: "Contact Methods"
    },
    methods: [
      {
        icon: Mail,
        title: { zh: "邮箱联系", en: "Email" },
        value: "xxxxxxxxx@qq.com",
        href: "#contact"
      },
      {
        icon: Github,
        title: { zh: "GitHub", en: "GitHub" },
        value: "https://github.com/happy11233",
        href: "https://github.com/happy11233"
      },
      {
        icon: MessageCircle,
        title: { zh: "微信 / WeChat", en: "WeChat" },
        value: "xxxxxxxxx",
        href: "#contact"
      }
    ]
  }
};
