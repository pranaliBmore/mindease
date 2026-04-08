import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import FloatingOrbs from "@/components/FloatingOrbs";
import { Send, Bot, User, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { useRequireAuth } from "@/hooks/useRequireAuth";

interface Message {
  id: number;
  role: "user" | "ai";
  text: string;
}

function buildWelcomeFromSession(): Message[] {
  const reason = localStorage.getItem("emotionReason")?.trim() || null;
  const emotion = localStorage.getItem("detectedEmotion")?.trim() || null;
  let text: string;
  if (reason && emotion) {
    text = `I hear you. Your latest check-in suggested **${emotion}**, and you chose to share: "${reason}". How can I support you right now?`;
  } else if (emotion) {
    text = `Hello! Your latest check-in suggested **${emotion}**. If you’d like to say more about what’s behind that, I’m listening. How can I support you today?`;
  } else {
    text = "Hello! I'm here to support you. How are you feeling right now?";
  }
  return [{ id: 0, role: "ai", text }];
}

const ChatAI = () => {
  useRequireAuth();
  const navigate = useNavigate();
  const emotionContext = localStorage.getItem("detectedEmotion")?.trim() || undefined;
  const [messages, setMessages] = useState<Message[]>(() => buildWelcomeFromSession());
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);
  const [chatError, setChatError] = useState("");
  const messagesEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;
    setChatError("");
    const userMsg: Message = { id: Date.now(), role: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setTyping(true);

    try {
      const response = await api.sendChat({
        message: userMsg.text,
        emotion_context: emotionContext,
      });
      setMessages((prev) => [...prev, { id: Date.now() + 1, role: "ai", text: response.reply }]);
      setTyping(false);
    } catch (err) {
      setTyping(false);
      setChatError(err instanceof Error ? err.message : "AI chat unavailable");
    }
  };

  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden gradient-bg">
      <FloatingOrbs />
      {/* Header */}
      <div className="glass-card-strong border-b border-border/50 px-6 py-4 flex items-center justify-between relative z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center">
            <Bot className="w-5 h-5 text-primary-foreground" />
          </div>
          <div>
            <h1 className="font-semibold text-foreground">MindEase AI</h1>
            <p className="text-xs text-muted-foreground">{typing ? "Typing..." : "Online"}</p>
          </div>
        </div>
        <button onClick={() => navigate("/community")} className="btn-ghost text-sm py-2 px-4">
          Join Community <ArrowRight className="w-3 h-3 inline ml-1" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6 space-y-4 relative z-10">
        <div className="max-w-2xl mx-auto space-y-4">
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
            >
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                msg.role === "ai" ? "gradient-primary" : "bg-peach/20"
              }`}>
                {msg.role === "ai" ? (
                  <Bot className="w-4 h-4 text-primary-foreground" />
                ) : (
                  <User className="w-4 h-4 text-peach" />
                )}
              </div>
              <div className={`max-w-[75%] p-4 rounded-2xl ${
                msg.role === "ai"
                  ? "glass-card text-foreground"
                  : "gradient-primary text-primary-foreground"
              }`}>
                <p className="text-sm leading-relaxed">{msg.text}</p>
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
          <div ref={messagesEnd} />
        </div>
      </div>

      {/* Input */}
      <div className="glass-card-strong border-t border-border/50 px-4 md:px-6 py-4 relative z-10">
        <div className="max-w-2xl mx-auto flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Share what's on your mind..."
            className="mindease-input flex-1"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim()}
            className="btn-primary px-4 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
        {chatError ? <p className="max-w-2xl mx-auto text-destructive text-sm mt-2">{chatError}</p> : null}
      </div>
    </div>
  );
};

export default ChatAI;
