import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import FloatingOrbs from "@/components/FloatingOrbs";
import {
  ArrowLeft,
  Sparkles,
  TrendingUp,
  TrendingDown,
  Minus,
  Loader2,
  MessageCircle,
  ScanFace,
} from "lucide-react";
import { api, type InsightsResponse } from "@/lib/api";

const MOOD_META: Record<string, { label: string; cls: string }> = {
  happiness: { label: "Happy", cls: "bg-sage" },
  neutrality: { label: "Neutral", cls: "bg-teal/70" },
  stress: { label: "Stressed", cls: "bg-peach" },
  anxiety: { label: "Anxious", cls: "bg-lavender" },
  sadness: { label: "Sad", cls: "bg-teal" },
  anger: { label: "Angry", cls: "bg-destructive/70" },
  fear: { label: "Fearful", cls: "bg-lavender/70" },
};
const moodLabel = (m: string) => MOOD_META[m]?.label ?? m;

function TrendBadge({ trend }: { trend: InsightsResponse["trend"] }) {
  const map = {
    improving: { icon: TrendingUp, text: "Trending lighter", cls: "text-sage bg-sage/10" },
    dipping: { icon: TrendingDown, text: "A bit heavier lately", cls: "text-peach bg-peach/10" },
    steady: { icon: Minus, text: "Fairly steady", cls: "text-teal bg-teal/10" },
    "not enough data": { icon: Minus, text: "Not enough data yet", cls: "text-muted-foreground bg-muted" },
  } as const;
  const { icon: Icon, text, cls } = map[trend];
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium ${cls}`}>
      <Icon className="w-3.5 h-3.5" /> {text}
    </span>
  );
}

const Insights = () => {
  const navigate = useNavigate();
  const [range, setRange] = useState<"week" | "month">("month");
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async (r: "week" | "month") => {
    setLoading(true);
    setError("");
    try {
      setData(await api.getInsights(r));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load insights.");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(range);
  }, [range, load]);

  const maxCount = data ? Math.max(1, ...data.mood_breakdown.map((b) => b.count)) : 1;

  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden gradient-bg">
      <FloatingOrbs />

      <div className="glass-card-strong border-b border-border/50 px-4 md:px-6 py-3 flex items-center gap-2 relative z-10">
        <button
          onClick={() => navigate("/home")}
          aria-label="Back to home"
          className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="w-9 h-9 rounded-xl gradient-primary flex items-center justify-center shrink-0">
          <Sparkles className="w-5 h-5 text-primary-foreground" />
        </div>
        <div className="flex-1">
          <h1 className="font-semibold text-foreground leading-tight">Your Insights</h1>
          <p className="text-xs text-muted-foreground">A gentle look at your check-ins</p>
        </div>
        <button
          onClick={() => navigate("/chat-ai")}
          aria-label="Open chat"
          className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-colors"
          title="Chat"
        >
          <MessageCircle className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6 relative z-10">
        <div className="max-w-2xl mx-auto space-y-5">
          <div className="flex gap-1 p-1 bg-muted rounded-lg w-fit">
            {(["week", "month"] as const).map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium capitalize transition-colors ${
                  range === r ? "bg-card shadow-sm text-foreground" : "text-muted-foreground"
                }`}
              >
                {r === "week" ? "7 days" : "30 days"}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="glass-card p-10 flex items-center justify-center">
              <Loader2 className="w-6 h-6 text-primary animate-spin" />
            </div>
          ) : error ? (
            <div className="glass-card p-6 text-center text-sm text-destructive">{error}</div>
          ) : data && data.check_ins === 0 ? (
            <div className="glass-card-strong p-8 text-center">
              <Sparkles className="w-8 h-8 text-primary mx-auto mb-3" />
              <h2 className="font-semibold text-foreground mb-1">Nothing to show yet</h2>
              <p className="text-sm text-muted-foreground mb-5">
                Do a quick emotion scan or a written check-in and your patterns will appear here.
              </p>
              <div className="flex flex-wrap gap-3 justify-center">
                <button onClick={() => navigate("/emotion-analysis")} className="btn-primary inline-flex items-center gap-2">
                  <ScanFace className="w-4 h-4" /> Emotion scan
                </button>
                <button onClick={() => navigate("/expression")} className="btn-ghost">
                  Write a check-in
                </button>
              </div>
            </div>
          ) : data ? (
            <>
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-card-strong p-6"
              >
                <div className="flex flex-wrap items-center gap-x-6 gap-y-2 mb-4">
                  <div>
                    <div className="text-2xl font-display font-bold text-foreground">{data.check_ins}</div>
                    <div className="text-xs text-muted-foreground">check-ins</div>
                  </div>
                  <div>
                    <div className="text-2xl font-display font-bold text-foreground">{data.active_days}</div>
                    <div className="text-xs text-muted-foreground">active days</div>
                  </div>
                  <div>
                    <div className="text-lg font-display font-semibold text-foreground capitalize">
                      {data.top_mood ? moodLabel(data.top_mood) : "-"}
                    </div>
                    <div className="text-xs text-muted-foreground">most frequent</div>
                  </div>
                  <div className="ml-auto">
                    <TrendBadge trend={data.trend} />
                  </div>
                </div>

                {data.mood_breakdown.length > 0 && (
                  <div className="space-y-1.5">
                    {data.mood_breakdown.map((b) => (
                      <div key={b.mood} className="flex items-center gap-3">
                        <span className="w-20 shrink-0 text-xs text-muted-foreground capitalize">
                          {moodLabel(b.mood)}
                        </span>
                        <div className="flex-1 h-2.5 rounded-full bg-muted overflow-hidden">
                          <div
                            className={`h-full rounded-full ${MOOD_META[b.mood]?.cls ?? "bg-primary"}`}
                            style={{ width: `${(b.count / maxCount) * 100}%` }}
                          />
                        </div>
                        <span className="w-6 text-right text-xs text-muted-foreground">{b.count}</span>
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 }}
                className="glass-card-strong p-6"
              >
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="w-4 h-4 text-primary" />
                  <h2 className="font-semibold text-foreground">What MindEase notices</h2>
                </div>
                <ul className="space-y-2.5">
                  {data.observations.map((o, i) => (
                    <li key={i} className="flex gap-2.5 text-sm text-foreground/90 leading-relaxed">
                      <span className="text-primary mt-0.5">-</span>
                      <span>{o}</span>
                    </li>
                  ))}
                </ul>
                <p className="text-[11px] text-muted-foreground mt-4">
                  Based only on your own check-in history. MindEase offers support, not professional care.
                </p>
              </motion.div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default Insights;
