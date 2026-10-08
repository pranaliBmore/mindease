import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import FloatingOrbs from "@/components/FloatingOrbs";
import {
  Send,
  Bot,
  User,
  ArrowLeft,
  ScanFace,
  Users,
  HeartHandshake,
  Trash2,
  Wind,
  Leaf,
  PenLine,
  Sparkles,
  RefreshCw,
  Copy,
  Check,
  ShieldAlert,
  X,
} from "lucide-react";
import { api, type ChatMode } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "ai";
  text: string;
  safety?: string;
}

const uid = () => Math.random().toString(36).slice(2) + Date.now().toString(36);

function welcomeText(): string {
  const reason = localStorage.getItem("emotionReason")?.trim() || null;
  const emotion = localStorage.getItem("detectedEmotion")?.trim() || null;
  if (reason && emotion) {
    return `I hear you. Your last check-in looked like **${emotion}**, and you shared: "${reason}". How can I help right now?`;
  }
  if (emotion) {
    return `Hi. Your last check-in looked like **${emotion}**. Want to say a bit more about it? I'm listening.`;
  }
  return "Hi, I'm here with you. How are you feeling right now?";
}

const SUGGESTIONS: { label: string; text: string; mode?: ChatMode }[] = [
  { label: "I feel anxious", text: "I'm feeling anxious and I'm not sure why." },
  { label: "My mind won't switch off", text: "My thoughts keep racing and I can't switch off." },
  { label: "I'm feeling low", text: "I'm feeling low today." },
  { label: "Help me feel calmer", text: "Can you help me feel a bit calmer right now?" },
  { label: "See this differently", text: "Something is worrying me. Can you help me see it differently?", mode: "reframe" },
];

const TOOLS: { key: string; label: string; icon: typeof Wind; text: string; mode: ChatMode }[] = [
  { key: "grounding", label: "Grounding", icon: Leaf, text: "Can you guide me through a grounding exercise?", mode: "grounding" },
  { key: "journal", label: "Journal prompt", icon: PenLine, text: "Give me a journaling prompt for how I feel right now.", mode: "journal_prompt" },
  { key: "pep", label: "Pep talk", icon: Sparkles, text: "I could use a little encouragement.", mode: "pep_talk" },
];

/** Very small markdown: **bold**, line breaks, and "- " / "• " bullets. */
function RichText({ text }: { text: string }) {
  const lines = text.split(/\r?\n/);
  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        const bullet = /^\s*([-*•])\s+/.test(line);
        const content = line.replace(/^\s*([-*•])\s+/, "");
        const parts = content.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
        const rendered = parts.map((p, j) =>
          /^\*\*[^*]+\*\*$/.test(p) ? <strong key={j}>{p.slice(2, -2)}</strong> : <span key={j}>{p}</span>,
        );
        if (!line.trim()) return <div key={i} className="h-1" />;
        return bullet ? (
          <div key={i} className="flex gap-2">
            <span className="text-primary">•</span>
            <p className="text-sm leading-relaxed">{rendered}</p>
          </div>
        ) : (
          <p key={i} className="text-sm leading-relaxed">
            {rendered}
          </p>
        );
      })}
    </div>
  );
}

/** Client-side 4-4-4-4 box breathing. No AI needed. */
function BreathingBox({ onClose }: { onClose: () => void }) {
  const phases = [
    { label: "Breathe in", secs: 4, scale: 1.35 },
    { label: "Hold", secs: 4, scale: 1.35 },
    { label: "Breathe out", secs: 4, scale: 1 },
    { label: "Hold", secs: 4, scale: 1 },
  ];
  const [running, setRunning] = useState(true);
  const [phase, setPhase] = useState(0);
  const [cycles, setCycles] = useState(0);

  useEffect(() => {
    if (!running) return;
    const t = setTimeout(() => {
      setPhase((p) => {
        const next = (p + 1) % phases.length;
        if (next === 0) setCycles((c) => c + 1);
        return next;
      });
    }, phases[phase].secs * 1000);
    return () => clearTimeout(t);
  }, [running, phase]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="glass-card p-5 mb-3 overflow-hidden"
    >
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-semibold text-foreground">Box breathing · {cycles} cycle{cycles === 1 ? "" : "s"}</p>
        <button onClick={onClose} aria-label="Close breathing exercise" className="text-muted-foreground hover:text-foreground">
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="flex flex-col items-center py-4">
        <div className="relative w-28 h-28 flex items-center justify-center">
          <motion.div
            className="absolute inset-0 rounded-full gradient-primary opacity-20"
            animate={{ scale: phases[phase].scale }}
            transition={{ duration: phases[phase].secs, ease: "easeInOut" }}
          />
          <motion.div
            className="w-16 h-16 rounded-full gradient-primary"
            animate={{ scale: phases[phase].scale }}
            transition={{ duration: phases[phase].secs, ease: "easeInOut" }}
          />
        </div>
        <p className="mt-4 text-base font-medium text-foreground">{phases[phase].label}</p>
        <p className="text-xs text-muted-foreground">4 seconds</p>
      </div>
      <div className="flex gap-2 justify-center">
        <button onClick={() => setRunning((r) => !r)} className="btn-ghost text-sm py-1.5 px-4">
          {running ? "Pause" : "Resume"}
        </button>
        <button onClick={onClose} className="btn-primary text-sm py-1.5 px-4">
          I'm done
        </button>
      </div>
    </motion.div>
  );
}

const ChatAI = () => {
  const navigate = useNavigate();
  const emotionContext = localStorage.getItem("detectedEmotion")?.trim() || undefined;

  const [messages, setMessages] = useState<Message[]>([{ id: "welcome", role: "ai", text: welcomeText() }]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [chatError, setChatError] = useState("");
  const [showBreathing, setShowBreathing] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const messagesEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typing]);

  // Load past conversation once.
  useEffect(() => {
    let cancelled = false;
    api
      .getChatHistory()
      .then((res) => {
        if (cancelled || !res.messages.length) return;
        const restored: Message[] = [{ id: "welcome", role: "ai", text: welcomeText() }];
        res.messages.forEach((m) => {
          restored.push({ id: m.id + "-u", role: "user", text: m.user_message });
          restored.push({ id: m.id + "-a", role: "ai", text: m.ai_reply });
        });
        setMessages(restored);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const send = useCallback(
    async (text: string, mode: ChatMode = "chat") => {
      const clean = text.trim();
      if (!clean || typing) return;
      setChatError("");
      setMessages((prev) => [...prev, { id: uid(), role: "user", text: clean }]);
      setInput("");
      setTyping(true);
      try {
        const res = await api.sendChat({ message: clean, emotion_context: emotionContext, mode });
        setMessages((prev) => [...prev, { id: uid(), role: "ai", text: res.reply, safety: res.safety }]);
      } catch (err) {
        setChatError(err instanceof Error ? err.message : "MindEase AI is unavailable right now.");
      } finally {
        setTyping(false);
      }
    },
    [emotionContext, typing],
  );

  const clearChat = async () => {
    try {
      await api.clearChat();
    } catch {
      /* reset locally regardless */
    }
    setShowBreathing(false);
    setMessages([{ id: "welcome", role: "ai", text: welcomeText() }]);
  };

  const copy = (m: Message) => {
    navigator.clipboard?.writeText(m.text).then(
      () => {
        setCopiedId(m.id);
        setTimeout(() => setCopiedId((c) => (c === m.id ? null : c)), 1500);
      },
      () => undefined,
    );
  };

  const showSuggestions = messages.filter((m) => m.role === "user").length === 0 && !typing;

  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden gradient-bg">
      <FloatingOrbs />

      {/* Header */}
      <div className="glass-card-strong border-b border-border/50 px-4 md:px-6 py-3 flex items-center gap-2 relative z-10">
        <button
          onClick={() => navigate("/home")}
          aria-label="Back to home"
          className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="w-9 h-9 rounded-xl gradient-primary flex items-center justify-center shrink-0">
          <Bot className="w-5 h-5 text-primary-foreground" />
        </div>
        <div className="min-w-0 flex-1">
          <h1 className="font-semibold text-foreground leading-tight">MindEase AI</h1>
          <p className="text-xs text-muted-foreground">{typing ? "Typing…" : "Here to listen"}</p>
        </div>
        <button
          onClick={() => navigate("/insights")}
          aria-label="Your insights"
          className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
          title="Your insights"
        >
          <Sparkles className="w-4 h-4" />
        </button>
        <button
          onClick={() => navigate("/emotion-analysis")}
          aria-label="Emotion check"
          className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
          title="Emotion check"
        >
          <ScanFace className="w-4 h-4" />
        </button>
        <button
          onClick={() => navigate("/community")}
          aria-label="Community"
          className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
          title="Community"
        >
          <Users className="w-4 h-4" />
        </button>
        <button
          onClick={() => navigate("/match")}
          aria-label="Don't know anyone? Find a match"
          className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
          title="Don't know anyone? Find a match"
        >
          <HeartHandshake className="w-4 h-4" />
        </button>
        <button
          onClick={clearChat}
          aria-label="Clear conversation"
          className="p-2 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
          title="Clear conversation"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6 relative z-10">
        <div className="max-w-2xl mx-auto space-y-4">
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
            >
              <div
                className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                  msg.role === "ai" ? "gradient-primary" : "bg-peach/20"
                }`}
              >
                {msg.role === "ai" ? (
                  <Bot className="w-4 h-4 text-primary-foreground" />
                ) : (
                  <User className="w-4 h-4 text-peach" />
                )}
              </div>
              <div
                className={`group max-w-[80%] p-4 rounded-2xl ${
                  msg.safety === "crisis"
                    ? "bg-destructive/10 border border-destructive/30 text-foreground"
                    : msg.role === "ai"
                      ? "glass-card text-foreground"
                      : "gradient-primary text-primary-foreground"
                }`}
              >
                {msg.safety === "crisis" && (
                  <div className="flex items-center gap-1.5 text-destructive text-xs font-semibold mb-1.5">
                    <ShieldAlert className="w-3.5 h-3.5" /> Please reach out for support
                  </div>
                )}
                <RichText text={msg.text} />
                {msg.role === "ai" && msg.id !== "welcome" && (
                  <button
                    onClick={() => copy(msg)}
                    className="mt-2 text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity"
                    aria-label="Copy message"
                  >
                    {copiedId === msg.id ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    {copiedId === msg.id ? "Copied" : "Copy"}
                  </button>
                )}
              </div>
            </motion.div>
          ))}

          {typing && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
              <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center">
                <Bot className="w-4 h-4 text-primary-foreground" />
              </div>
              <div className="glass-card px-4 py-3 rounded-2xl">
                <div className="flex gap-1">
                  {[0, 1, 2].map((i) => (
                    <motion.div
                      key={i}
                      className="w-2 h-2 rounded-full bg-primary/40"
                      animate={{ y: [0, -5, 0] }}
                      transition={{ repeat: Infinity, duration: 0.6, delay: i * 0.15 }}
                    />
                  ))}
                </div>
              </div>
            </motion.div>
          )}

          {showSuggestions && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-wrap gap-2 pt-1"
            >
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.label}
                  onClick={() => send(s.text, s.mode)}
                  className="text-sm px-3 py-1.5 rounded-full bg-primary/5 border border-primary/20 text-primary hover:bg-primary/10 transition-colors"
                >
                  {s.label}
                </button>
              ))}
            </motion.div>
          )}

          <div ref={messagesEnd} />
        </div>
      </div>

      {/* Tools + input */}
      <div className="glass-card-strong border-t border-border/50 px-4 md:px-6 py-3 relative z-10">
        <div className="max-w-2xl mx-auto">
          <AnimatePresence>
            {showBreathing && <BreathingBox key="breath" onClose={() => setShowBreathing(false)} />}
          </AnimatePresence>

          <div className="flex flex-wrap gap-2 mb-3">
            <button
              onClick={() => setShowBreathing((v) => !v)}
              className={`text-sm px-3 py-1.5 rounded-full border inline-flex items-center gap-1.5 transition-colors ${
                showBreathing
                  ? "bg-primary/10 border-primary/30 text-primary"
                  : "bg-muted/50 border-border text-muted-foreground hover:text-foreground"
              }`}
            >
              <Wind className="w-3.5 h-3.5" /> Breathe
            </button>
            {TOOLS.map((t) => (
              <button
                key={t.key}
                onClick={() => send(t.text, t.mode)}
                disabled={typing}
                className="text-sm px-3 py-1.5 rounded-full bg-muted/50 border border-border text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1.5 disabled:opacity-50"
              >
                <t.icon className="w-3.5 h-3.5" /> {t.label}
              </button>
            ))}
          </div>

          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send(input)}
              placeholder="Share what's on your mind…"
              className="mindease-input flex-1"
            />
            <button
              onClick={() => send(input)}
              disabled={!input.trim() || typing}
              className="btn-primary px-4 disabled:opacity-40 disabled:cursor-not-allowed"
              aria-label="Send message"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>

          {chatError ? (
            <p className="text-destructive text-sm mt-2 flex items-center gap-1.5">
              <RefreshCw className="w-3.5 h-3.5" /> {chatError}
            </p>
          ) : (
            <p className="text-[11px] text-muted-foreground mt-2 text-center">
              MindEase offers support, not professional care. In an emergency, contact your local services.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatAI;
