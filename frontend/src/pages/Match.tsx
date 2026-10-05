import { useCallback, useLayoutEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import FloatingOrbs from "@/components/FloatingOrbs";
import {
  HeartHandshake,
  Loader2,
  Send,
  Sparkles,
  Flag,
  LogOut,
  UserCheck,
  ShieldAlert,
  Bot,
} from "lucide-react";
import { useSocialWebSocket, type WsMatchMessagePayload } from "@/hooks/useSocialWebSocket";
import {
  api,
  type MatchAnswers,
  type MatchGoal,
  type MatchMessageItem,
  type MatchSession,
  type MatchSupportStyle,
  type MatchTopic,
  type SoloEmotion,
} from "@/lib/api";

const MOOD_OPTIONS: { value: SoloEmotion; label: string }[] = [
  { value: "stress", label: "Stressed" },
  { value: "anxiety", label: "Anxious" },
  { value: "sadness", label: "Sad" },
  { value: "anger", label: "Frustrated" },
  { value: "fear", label: "Scared or worried" },
  { value: "happiness", label: "Okay, just want to talk" },
  { value: "neutrality", label: "Not sure / numb" },
];

const TOPIC_OPTIONS: { value: MatchTopic; label: string }[] = [
  { value: "work_study", label: "Work or studies" },
  { value: "relationships", label: "A relationship" },
  { value: "family", label: "Family" },
  { value: "health", label: "Health" },
  { value: "loneliness", label: "Feeling alone" },
  { value: "other", label: "Something else" },
];

const SUPPORT_OPTIONS: { value: MatchSupportStyle; label: string }[] = [
  { value: "just_listen", label: "Just listen to me" },
  { value: "share_experience", label: "Share something similar they've been through" },
  { value: "give_advice", label: "Offer suggestions" },
  { value: "light_distraction", label: "Keep it light, distract me" },
];

const GOAL_OPTIONS: { value: MatchGoal; label: string }[] = [
  { value: "feel_heard", label: "Feel heard" },
  { value: "feel_less_alone", label: "Feel less alone" },
  { value: "get_practical_tips", label: "Get a useful tip" },
  { value: "laugh_a_bit", label: "Laugh a little" },
];

interface QuizOptionGridProps {
  options: { value: string; label: string }[];
  value: string | null;
  onSelect: (v: string) => void;
}

function QuizOptionGrid({ options, value, onSelect }: QuizOptionGridProps) {
  return (
    <div className="grid sm:grid-cols-2 gap-2">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onSelect(opt.value)}
          className={`text-left rounded-xl border px-4 py-3 text-sm transition-all ${
            value === opt.value
              ? "border-primary bg-primary/10 text-foreground font-medium"
              : "border-border/50 bg-background/40 text-muted-foreground hover:border-primary/40"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

type ViewState = "quiz" | "waiting" | "matched" | "ended";

const Match = () => {
  const navigate = useNavigate();
  const chatScrollRef = useRef<HTMLDivElement>(null);
  const sessionRef = useRef<MatchSession | null>(null);

  const [token] = useState(() => localStorage.getItem("accessToken"));
  const [view, setView] = useState<ViewState>("quiz");
  const [loadingStart, setLoadingStart] = useState(false);
  const [error, setError] = useState("");
  const [banner, setBanner] = useState("");

  const [mood, setMood] = useState<SoloEmotion | null>(null);
  const [topic, setTopic] = useState<MatchTopic | null>(null);
  const [supportStyle, setSupportStyle] = useState<MatchSupportStyle | null>(null);
  const [goal, setGoal] = useState<MatchGoal | null>(null);

  const [session, setSession] = useState<MatchSession | null>(null);
  const [messages, setMessages] = useState<MatchMessageItem[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [safetyNotice, setSafetyNotice] = useState("");
  const [revealSent, setRevealSent] = useState(false);
  const [showReportConfirm, setShowReportConfirm] = useState(false);

  sessionRef.current = session;

  const { data: me } = useQuery({ queryKey: ["me"], queryFn: () => api.getMe() });
  const myId = me?.id ?? "";

  const loadMessages = useCallback(async (sessionId: string) => {
    try {
      const rows = await api.getMatchMessages(sessionId);
      setMessages(rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load messages");
    }
  }, []);

  // Restore an in-progress match/wait state on mount (e.g. after a page refresh).
  useLayoutEffect(() => {
    api
      .getMatchState()
      .then((st) => {
        if (st.status === "matched" && st.session) {
          setSession(st.session);
          setView("matched");
          void loadMessages(st.session.session_id);
        } else if (st.status === "waiting") {
          setView("waiting");
        }
      })
      .catch(() => {
        /* not fatal, default quiz view stays */
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onMatchFound = useCallback(
    (s: MatchSession) => {
      setSession(s);
      setView("matched");
      setMessages([]);
      setRevealSent(false);
      void loadMessages(s.session_id);
    },
    [loadMessages],
  );

  const onMatchMessage = useCallback((msg: WsMatchMessagePayload) => {
    const current = sessionRef.current;
    if (!current || msg.session_id !== current.session_id) return;
    setMessages((prev) => (prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]));
  }, []);

  const onMatchEnded = useCallback((sessionId: string) => {
    const current = sessionRef.current;
    if (!current || current.session_id !== sessionId) return;
    setView("ended");
  }, []);

  const { sendMatchMessage } = useSocialWebSocket(token, {
    onMatchFound,
    onMatchMessage,
    onMatchEnded,
    onMatchSafety: (detail) => setSafetyNotice(detail),
    onWsError: (d) => setError(d),
  });

  useLayoutEffect(() => {
    const el = chatScrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const findMatch = async () => {
    if (!mood || !topic || !supportStyle || !goal) {
      setError("Please answer all four questions.");
      return;
    }
    setError("");
    setLoadingStart(true);
    try {
      const answers: MatchAnswers = { mood, topic, support_style: supportStyle, goal };
      const res = await api.startMatch(answers);
      if (res.status === "matched" && res.session) {
        onMatchFound(res.session);
      } else {
        setView("waiting");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start matching");
    } finally {
      setLoadingStart(false);
    }
  };

  const cancelWaiting = async () => {
    try {
      await api.cancelMatch();
    } catch {
      /* ignore */
    }
    setView("quiz");
  };

  const sendChat = () => {
    const text = chatInput.trim();
    if (!text || !session) return;
    setChatInput("");
    setError("");
    sendMatchMessage(session.session_id, text);
  };

  const reveal = async () => {
    if (!session) return;
    setError("");
    try {
      const res = await api.revealMatch(session.session_id);
      setBanner(res.message);
      setRevealSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send request");
    }
  };

  const endMatch = async () => {
    if (!session) return;
    try {
      await api.endMatch(session.session_id);
    } catch {
      /* ignore */
    }
    setView("ended");
  };

  const submitReport = async (reason: string) => {
    if (!session) return;
    setError("");
    try {
      const res = await api.reportMatch(session.session_id, reason);
      setBanner(res.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit report");
    } finally {
      setShowReportConfirm(false);
      setView("ended");
    }
  };

  const startOver = () => {
    setSession(null);
    setMessages([]);
    setSafetyNotice("");
    setRevealSent(false);
    setBanner("");
    setError("");
    setView("quiz");
  };

  return (
    <div className="min-h-screen relative overflow-hidden gradient-bg px-4 py-12">
      <FloatingOrbs />
      <div className="container mx-auto max-w-2xl relative z-10">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl gradient-primary mb-4">
            <HeartHandshake className="w-8 h-8 text-primary-foreground" />
          </div>
          <h1 className="text-4xl font-display font-bold text-foreground mb-3">Find Someone to Talk To</h1>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Answer a few quick questions and we'll pair you anonymously with someone else on MindEase who's in a
            similar place. No names shown unless you both choose to share.
          </p>
        </motion.div>

        {banner ? <p className="text-sm text-primary font-medium mb-4 text-center">{banner}</p> : null}
        {error ? <p className="text-sm text-destructive mb-4 text-center">{error}</p> : null}

        {view === "quiz" && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-card-strong p-6 space-y-6">
            <div className="space-y-3">
              <h2 className="font-semibold text-foreground">How are you feeling right now?</h2>
              <QuizOptionGrid options={MOOD_OPTIONS} value={mood} onSelect={(v) => setMood(v as SoloEmotion)} />
            </div>
            <div className="space-y-3">
              <h2 className="font-semibold text-foreground">What's mostly on your mind?</h2>
              <QuizOptionGrid options={TOPIC_OPTIONS} value={topic} onSelect={(v) => setTopic(v as MatchTopic)} />
            </div>
            <div className="space-y-3">
              <h2 className="font-semibold text-foreground">What kind of support are you looking for?</h2>
              <QuizOptionGrid
                options={SUPPORT_OPTIONS}
                value={supportStyle}
                onSelect={(v) => setSupportStyle(v as MatchSupportStyle)}
              />
            </div>
            <div className="space-y-3">
              <h2 className="font-semibold text-foreground">What would make this chat worth it?</h2>
              <QuizOptionGrid options={GOAL_OPTIONS} value={goal} onSelect={(v) => setGoal(v as MatchGoal)} />
            </div>
            <button
              type="button"
              onClick={() => void findMatch()}
              disabled={loadingStart}
              className="btn-primary w-full disabled:opacity-60"
            >
              {loadingStart ? <Loader2 className="w-4 h-4 animate-spin inline mr-2" /> : null}
              Find my match
            </button>
          </motion.div>
        )}

        {view === "waiting" && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-card-strong p-8 text-center space-y-5">
            <Loader2 className="w-10 h-10 animate-spin text-primary mx-auto" />
            <h2 className="text-xl font-semibold text-foreground">Looking for your match…</h2>
            <p className="text-sm text-muted-foreground max-w-sm mx-auto">
              We'll connect you the moment someone compatible is available — this can take a little while if few
              people are online. Keep this tab open and we'll notify you instantly.
            </p>
            <div className="flex flex-col sm:flex-row gap-2 justify-center pt-2">
              <button type="button" onClick={() => navigate("/chat-ai")} className="btn-ghost flex items-center justify-center gap-2">
                <Bot className="w-4 h-4" /> Chat with AI while you wait
              </button>
              <button type="button" onClick={() => void cancelWaiting()} className="btn-ghost">
                Cancel
              </button>
            </div>
          </motion.div>
        )}

        {view === "matched" && session && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-card-strong flex flex-col min-h-[480px] overflow-hidden">
            <div className="border-b border-border/50 px-4 py-3 shrink-0 flex items-center justify-between gap-2 flex-wrap">
              <div>
                <h2 className="font-semibold text-foreground flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary" /> You're chatting with {session.peer_alias}
                </h2>
                <p className="text-xs text-muted-foreground mt-1">
                  Anonymous for now. You appear to them as "{session.my_alias}".
                </p>
              </div>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => void reveal()}
                  disabled={revealSent}
                  title="Send a friend request with your real name"
                  className="btn-ghost text-xs py-1 px-2 flex items-center gap-1 disabled:opacity-50"
                >
                  <UserCheck className="w-3.5 h-3.5" /> {revealSent ? "Request sent" : "Reveal & add as friend"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowReportConfirm(true)}
                  title="Report this person"
                  className="btn-ghost text-xs py-1 px-2 flex items-center gap-1 text-destructive"
                >
                  <Flag className="w-3.5 h-3.5" /> Report
                </button>
                <button
                  type="button"
                  onClick={() => void endMatch()}
                  title="End this match"
                  className="btn-ghost text-xs py-1 px-2 flex items-center gap-1"
                >
                  <LogOut className="w-3.5 h-3.5" /> End
                </button>
              </div>
            </div>

            {showReportConfirm ? (
              <div className="px-4 py-3 bg-destructive/10 border-b border-destructive/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                <p className="text-xs text-foreground flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-destructive shrink-0" />
                  Report this match? It will end immediately and you won't be paired with them again.
                </p>
                <div className="flex gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => void submitReport("inappropriate")}
                    className="btn-primary text-xs py-1 px-3"
                  >
                    Confirm report
                  </button>
                  <button type="button" onClick={() => setShowReportConfirm(false)} className="btn-ghost text-xs py-1 px-3">
                    Cancel
                  </button>
                </div>
              </div>
            ) : null}

            {safetyNotice ? (
              <div className="px-4 py-3 bg-primary/10 border-b border-primary/20 text-xs text-foreground">
                {safetyNotice}
              </div>
            ) : null}

            <div
              ref={chatScrollRef}
              className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden overscroll-y-contain px-4 py-3 space-y-3"
            >
              {messages.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center mt-8">
                  Say hello — they're here to listen too.
                </p>
              ) : (
                messages.map((line) => {
                  const mine = line.from_user_id === myId;
                  return (
                    <div key={line.id} className={`flex min-w-0 ${mine ? "justify-end" : "justify-start"}`}>
                      <div
                        className={`max-w-[85%] min-w-0 rounded-2xl px-4 py-2 text-sm break-words [overflow-wrap:anywhere] ${
                          mine ? "gradient-primary text-primary-foreground" : "glass-card text-foreground"
                        }`}
                      >
                        {line.body}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
            <div className="border-t border-border/50 p-3 flex gap-2 shrink-0 min-w-0">
              <input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendChat()}
                placeholder="Type a message…"
                className="mindease-input flex-1 min-w-0"
              />
              <button type="button" onClick={sendChat} disabled={!chatInput.trim()} className="btn-primary px-3 disabled:opacity-40">
                <Send className="w-5 h-5" />
              </button>
            </div>
          </motion.div>
        )}

        {view === "ended" && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-card-strong p-8 text-center space-y-5">
            <h2 className="text-xl font-semibold text-foreground">That match has ended</h2>
            <p className="text-sm text-muted-foreground">
              Thanks for showing up for someone today. You can find a new match anytime.
            </p>
            <button type="button" onClick={startOver} className="btn-primary">
              Find a new match
            </button>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default Match;
