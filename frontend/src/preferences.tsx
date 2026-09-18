import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type Language = "en" | "zh-CN";
export type Theme = "dark" | "light";

const english = {
  "app.home": "WanderMind home",
  "app.tagline": "cognitive field notes",
  "nav.aria": "Primary navigation",
  "nav.inbox": "Inbox",
  "nav.wander": "Wander",
  "nav.wonders": "Wonders",
  "workspace.title": "Local-first workspace",
  "workspace.body": "Your knowledge stays inside your configured environment.",
  "preferences.aria": "Appearance and language",
  "preferences.chinese": "Switch to Chinese",
  "preferences.english": "Switch to English",
  "preferences.light": "Switch to light theme",
  "preferences.dark": "Switch to dark theme",
  "loading.default": "Thinking across the edges",
  "score.novelty": "Novelty",
  "score.coherence": "Coherence",
  "score.usefulness": "Usefulness",
  "score.surprise": "Surprise",
  "score.evidence": "Evidence",
  "trace.aria": "Wander trace",
  "trace.novelty": "novelty",
  "trace.collision": "collision",
  "trace.relevance": "relevance",
  "wonder.signal": "signal",
  "wonder.why": "Why?",
  "wonder.continue": "Continue",
  "wonder.save": "Save",
  "wonder.notInteresting": "Not interesting",
  "inbox.loadError": "Could not load the knowledge field.",
  "inbox.captureError": "Could not capture the thought.",
  "inbox.saveError": "Could not save the note.",
  "inbox.uploadError": "Could not upload the document.",
  "inbox.saved": "Knowledge added to the field.",
  "inbox.uploaded": "{file} entered the knowledge field.",
  "inbox.eyebrow": "Unfinished thoughts belong here",
  "inbox.heading": "Drop a thought.",
  "inbox.headingAccent": "Let it wander.",
  "inbox.intro": "Capture a question, half-formed idea, or stubborn tension. WanderMind will connect it to the knowledge already in your field.",
  "inbox.fragments": "knowledge fragments",
  "inbox.thoughtAria": "Drop a thought",
  "inbox.thoughtPlaceholder": "What keeps returning to your mind?",
  "inbox.seedHint": "Seed a directed wander",
  "inbox.begin": "Begin wandering",
  "inbox.captureLabel": "Knowledge capture",
  "inbox.captureTitle": "Add context to your mind",
  "inbox.uploadAria": "Upload text document",
  "inbox.optionalTitle": "Optional title",
  "inbox.notePlaceholder": "Paste a note, observation, excerpt, or concept...",
  "inbox.saveFragment": "Save fragment",
  "inbox.recentLabel": "Recent material",
  "inbox.recentTitle": "Your active knowledge field",
  "inbox.empty": "No fragments yet. Add two or more to unlock wandering.",
  "wander.error": "The wander could not be completed.",
  "wander.knowledgeLoadError": "Could not verify the knowledge field. Try refreshing the page.",
  "wander.knowledgeChanged": "The knowledge field changed. Add at least two fragments before trying again.",
  "wander.knowledgeRequired": "Wandering needs at least two knowledge fragments. Add {count} more to continue.",
  "wander.addKnowledge": "Add knowledge",
  "wander.eyebrow": "Structured wandering, not hidden reasoning",
  "wander.heading": "Follow the",
  "wander.headingAccent": "connection path.",
  "wander.intro": "Watch the engine retrieve, collide, transform, score, and surface ideas.",
  "wander.seedAria": "Wander seed",
  "wander.seedReady": "Captured seed is ready",
  "wander.seedPlaceholder": "Give the mind a question or tension...",
  "wander.running": "Wandering…",
  "wander.run": "Run wander",
  "wander.retrieval": "Local + remote retrieval",
  "wander.operators": "Six cognitive operators",
  "wander.candidate": "{count} candidate",
  "wander.candidates": "{count} candidates",
  "wander.scoring": "Independent scoring",
  "wander.trace": "Trace",
  "wander.traceTitle": "How the mind moved",
  "wander.steps": "{count} steps",
  "wander.outcome": "Surface result",
  "wander.open": "Open wonder",
  "wander.noSignal": "No signal crossed the threshold.",
  "wander.silence": "The engine kept the trace but chose silence over a weak or arbitrary idea.",
  "wander.agentRunning": "Agent synthesis and independent validation are running",
  "wander.runtimeVerified": "Agent Runtime verified",
  "wander.runtimeUnavailable": "No Agent Runtime call completed",
  "wander.runtimeCalls": "{count} calls · {seconds}s",
  "wander.runtimeTokens": "{count} tokens",
  "wander.bestCandidate": "Best retained candidate",
  "wander.stopReason": "Completion reason: {reason}",
  "wonders.loadError": "Could not load wonders.",
  "wonders.surfaced": "A cross-time connection surfaced.",
  "wonders.quiet": "No idea was strong enough to interrupt you.",
  "wonders.incubationError": "Incubation failed.",
  "wonders.eyebrow": "Curated, not continuous",
  "wonders.heading": "Today your mind",
  "wonders.headingAccent": "wandered to…",
  "wonders.intro": "Only connections that clear the quality threshold arrive here.",
  "wonders.incubating": "Incubating…",
  "wonders.runIncubation": "Run incubation",
  "wonders.loading": "Gathering surfaced wonders",
  "wonders.emptyTitle": "The field is quiet",
  "wonders.emptyBody": "Add knowledge, run a wander, and strong connections will collect here.",
  "detail.loadError": "Could not load the wonder.",
  "detail.exploreDone": "Explorer, evidence, and critic passes completed.",
  "detail.exploreError": "Deep exploration failed.",
  "detail.noNewKnowledge": "No sufficiently new knowledge is available yet.",
  "detail.rewonderError": "Re-wonder failed.",
  "detail.feedbackSaved": "Feedback saved.",
  "detail.feedbackError": "Feedback could not be saved.",
  "detail.opening": "Opening the connection",
  "detail.notFound": "Wonder not found",
  "detail.unavailable": "This connection is no longer available.",
  "detail.back": "← Back to wonders",
  "detail.confidence": "confidence",
  "detail.coreIdea": "Core idea",
  "detail.connectionPath": "Connection path",
  "detail.evidence": "Evidence",
  "detail.noEvidence": "No sourced evidence has been established.",
  "detail.counterEvidence": "Counter evidence",
  "detail.noCounterEvidence": "No counter evidence has been recorded.",
  "detail.questions": "Open questions",
  "detail.noQuestions": "Explore the wonder to generate follow-up questions.",
  "detail.critic": "Independent critic",
  "detail.noWeakness": "No material weakness reported.",
  "detail.factualRisk": "Factual risk {value}",
  "detail.obviousness": "Obviousness {value}",
  "detail.signalProfile": "Signal profile",
  "detail.nextMove": "Next move",
  "detail.working": "Working…",
  "detail.continue": "Continue exploring",
  "detail.rewonder": "Re-wonder with new knowledge",
  "detail.save": "Save this wonder",
} as const;

type MessageKey = keyof typeof english;

const chinese: Record<MessageKey, string> = {
  "app.home": "WanderMind 首页",
  "app.tagline": "认知漫游札记",
  "nav.aria": "主导航",
  "nav.inbox": "灵感收集",
  "nav.wander": "思维漫游",
  "nav.wonders": "洞见成果",
  "workspace.title": "本地优先工作区",
  "workspace.body": "你的知识始终保存在所配置的环境中。",
  "preferences.aria": "外观和语言",
  "preferences.chinese": "切换为中文",
  "preferences.english": "切换为英文",
  "preferences.light": "切换为亮色主题",
  "preferences.dark": "切换为深色主题",
  "loading.default": "正在探索知识边界",
  "score.novelty": "新颖度",
  "score.coherence": "连贯性",
  "score.usefulness": "实用性",
  "score.surprise": "惊喜度",
  "score.evidence": "证据潜力",
  "trace.aria": "漫游轨迹",
  "trace.novelty": "新颖度",
  "trace.collision": "碰撞度",
  "trace.relevance": "相关度",
  "wonder.signal": "洞见信号",
  "wonder.why": "查看缘由",
  "wonder.continue": "继续探索",
  "wonder.save": "稍后查看",
  "wonder.notInteresting": "不感兴趣",
  "inbox.loadError": "无法加载知识场。",
  "inbox.captureError": "无法记录这条想法。",
  "inbox.saveError": "无法保存笔记。",
  "inbox.uploadError": "无法上传文档。",
  "inbox.saved": "知识已加入知识场。",
  "inbox.uploaded": "{file} 已进入知识场。",
  "inbox.eyebrow": "未完成的想法值得被看见",
  "inbox.heading": "放下一条思绪。",
  "inbox.headingAccent": "让它自由漫游。",
  "inbox.intro": "记录一个问题、尚未成形的点子或挥之不去的矛盾。WanderMind 会将它与你知识场中的内容建立连接。",
  "inbox.fragments": "条知识片段",
  "inbox.thoughtAria": "记录一条想法",
  "inbox.thoughtPlaceholder": "最近什么问题总在你脑海中出现？",
  "inbox.seedHint": "以此开启定向漫游",
  "inbox.begin": "开始漫游",
  "inbox.captureLabel": "知识采集",
  "inbox.captureTitle": "为思维补充背景",
  "inbox.uploadAria": "上传文本文档",
  "inbox.optionalTitle": "标题（可选）",
  "inbox.notePlaceholder": "粘贴笔记、观察、摘录或概念……",
  "inbox.saveFragment": "保存片段",
  "inbox.recentLabel": "近期素材",
  "inbox.recentTitle": "活跃知识场",
  "inbox.empty": "还没有知识片段。添加两条以上即可开始漫游。",
  "wander.error": "本次思维漫游未能完成。",
  "wander.knowledgeLoadError": "无法确认知识场状态，请刷新页面后重试。",
  "wander.knowledgeChanged": "知识场已发生变化，请补足至少两条知识后重试。",
  "wander.knowledgeRequired": "思维漫游至少需要两条知识片段，请再添加 {count} 条。",
  "wander.addKnowledge": "前往添加知识",
  "wander.eyebrow": "结构化漫游，而非隐藏推理",
  "wander.heading": "沿着",
  "wander.headingAccent": "连接路径前进。",
  "wander.intro": "观察引擎如何检索、碰撞、变换、评分并呈现想法。",
  "wander.seedAria": "漫游种子",
  "wander.seedReady": "已捕获的种子可以开始漫游",
  "wander.seedPlaceholder": "给思维一个问题或矛盾……",
  "wander.running": "漫游中……",
  "wander.run": "运行漫游",
  "wander.retrieval": "局部与远距检索",
  "wander.operators": "六类认知算子",
  "wander.candidate": "{count} 个候选",
  "wander.candidates": "{count} 个候选",
  "wander.scoring": "独立质量评分",
  "wander.trace": "轨迹",
  "wander.traceTitle": "思维如何移动",
  "wander.steps": "{count} 步",
  "wander.outcome": "呈现结果",
  "wander.open": "打开洞见",
  "wander.noSignal": "没有信号越过呈现阈值。",
  "wander.silence": "引擎保留了完整轨迹，但选择对薄弱或任意的想法保持安静。",
  "wander.agentRunning": "Agent 正在综合候选并执行独立校验",
  "wander.runtimeVerified": "Agent Runtime 已验证",
  "wander.runtimeUnavailable": "没有 Agent Runtime 调用成功完成",
  "wander.runtimeCalls": "{count} 次调用 · {seconds} 秒",
  "wander.runtimeTokens": "{count} tokens",
  "wander.bestCandidate": "本轮最佳候选",
  "wander.stopReason": "完成原因：{reason}",
  "wonders.loadError": "无法加载洞见。",
  "wonders.surfaced": "一条跨时间连接浮现了。",
  "wonders.quiet": "没有足够强的想法值得打扰你。",
  "wonders.incubationError": "静默孵化失败。",
  "wonders.eyebrow": "只呈现精选结果",
  "wonders.heading": "今天，你的思维",
  "wonders.headingAccent": "漫游到了……",
  "wonders.intro": "只有越过质量阈值的连接才会来到这里。",
  "wonders.incubating": "孵化中……",
  "wonders.runIncubation": "运行静默孵化",
  "wonders.loading": "正在收集浮现的洞见",
  "wonders.emptyTitle": "知识场暂时安静",
  "wonders.emptyBody": "添加知识并运行漫游，足够强的连接会汇聚到这里。",
  "detail.loadError": "无法加载这条洞见。",
  "detail.exploreDone": "探索、证据与独立批评流程已完成。",
  "detail.exploreError": "深度探索失败。",
  "detail.noNewKnowledge": "暂时没有足够新颖的知识可用于再次漫游。",
  "detail.rewonderError": "再次漫游失败。",
  "detail.feedbackSaved": "反馈已保存。",
  "detail.feedbackError": "无法保存反馈。",
  "detail.opening": "正在打开这条连接",
  "detail.notFound": "未找到洞见",
  "detail.unavailable": "这条连接已不可用。",
  "detail.back": "← 返回洞见列表",
  "detail.confidence": "置信度",
  "detail.coreIdea": "核心想法",
  "detail.connectionPath": "连接路径",
  "detail.evidence": "支持证据",
  "detail.noEvidence": "尚未建立有来源的支持证据。",
  "detail.counterEvidence": "反向证据",
  "detail.noCounterEvidence": "尚未记录反向证据。",
  "detail.questions": "开放问题",
  "detail.noQuestions": "继续探索以生成后续问题。",
  "detail.critic": "独立批评者",
  "detail.noWeakness": "未报告实质性弱点。",
  "detail.factualRisk": "事实风险 {value}",
  "detail.obviousness": "显然度 {value}",
  "detail.signalProfile": "信号画像",
  "detail.nextMove": "下一步",
  "detail.working": "处理中……",
  "detail.continue": "继续深度探索",
  "detail.rewonder": "结合新知识再次漫游",
  "detail.save": "保存这条洞见",
};

const codeLabels: Record<Language, Record<string, string>> = {
  en: {},
  "zh-CN": {
    active: "活跃",
    analogy: "类比",
    candidate: "候选",
    closed: "已关闭",
    collision: "知识碰撞",
    completed: "已完成",
    connection: "连接",
    counterfactual: "反事实",
    dismissed: "已忽略",
    explore: "探索",
    explored: "已探索",
    failed: "失败",
    hypothesis: "假设",
    incubating: "孵化中",
    inversion: "反转",
    note: "笔记",
    pass: "通过",
    question: "问题",
    reject: "拒绝",
    revise: "需修订",
    running: "运行中",
    saved: "已保存",
    seed: "种子",
    stopped: "已停止",
  },
};

interface PreferencesContextValue {
  language: Language;
  theme: Theme;
  setLanguage: (language: Language) => void;
  setTheme: (theme: Theme) => void;
  t: (key: MessageKey, variables?: Record<string, string | number>) => string;
  labelCode: (value: string) => string;
  formatDate: (value: string | Date, options?: Intl.DateTimeFormatOptions) => string;
}

const defaultValue: PreferencesContextValue = {
  language: "en",
  theme: "dark",
  setLanguage: () => undefined,
  setTheme: () => undefined,
  t: (key, variables) => interpolate(english[key], variables),
  labelCode: humanize,
  formatDate: (value, options) => new Intl.DateTimeFormat("en", options).format(new Date(value)),
};

const PreferencesContext = createContext<PreferencesContextValue>(defaultValue);

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(readLanguage);
  const [theme, setTheme] = useState<Theme>(readTheme);

  useEffect(() => {
    document.documentElement.lang = language;
    document.documentElement.dataset.language = language;
    writePreference("wandermind-language", language);
  }, [language]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    writePreference("wandermind-theme", theme);
    document.querySelector('meta[name="theme-color"]')?.setAttribute(
      "content",
      theme === "dark" ? "#09111b" : "#f4f1e8",
    );
  }, [theme]);

  const t = useCallback(
    (key: MessageKey, variables?: Record<string, string | number>) => {
      const dictionary = language === "zh-CN" ? chinese : english;
      return interpolate(dictionary[key], variables);
    },
    [language],
  );
  const labelCode = useCallback(
    (code: string) => codeLabels[language][code] ?? humanize(code),
    [language],
  );
  const formatDate = useCallback(
    (date: string | Date, options?: Intl.DateTimeFormatOptions) =>
      new Intl.DateTimeFormat(language, options).format(new Date(date)),
    [language],
  );

  const value = useMemo<PreferencesContextValue>(() => {
    return {
      language,
      theme,
      setLanguage,
      setTheme,
      t,
      labelCode,
      formatDate,
    };
  }, [formatDate, labelCode, language, t, theme]);

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
}

export function usePreferences(): PreferencesContextValue {
  return useContext(PreferencesContext);
}

function readLanguage(): Language {
  const stored = readPreference("wandermind-language");
  if (stored === "en" || stored === "zh-CN") return stored;
  return window.navigator.language.toLowerCase().startsWith("zh") ? "zh-CN" : "en";
}

function readTheme(): Theme {
  const stored = readPreference("wandermind-theme");
  if (stored === "dark" || stored === "light") return stored;
  return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

function interpolate(template: string, variables?: Record<string, string | number>): string {
  if (!variables) return template;
  return Object.entries(variables).reduce(
    (result, [key, value]) => result.replaceAll(`{${key}}`, String(value)),
    template,
  );
}

function humanize(value: string): string {
  return value.replaceAll("_", " ");
}

function readPreference(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writePreference(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    return;
  }
}
