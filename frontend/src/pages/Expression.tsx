import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import FloatingOrbs from "@/components/FloatingOrbs";
import { Pen, ArrowRight, Loader2, Sparkles, Play } from "lucide-react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { api, type SoloAnalyzeResponse } from "@/lib/api";

const prompts = [
  "What made you smile today?",
  "What's one thing you're grateful for right now?",
  "Describe a moment where you felt at peace recently.",
  "What would you tell your younger self?",
  "What's one small step you can take today toward feeling better?",
];

function formatPercent(p: number) {
  const v = Math.max(0, Math.min(1, p));
  return `${(v * 100).toFixed(1)}%`;
}

const Expression = () => {
  useRequireAuth();
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const currentPrompt = useMemo(() => prompts[Math.floor(Math.random() * prompts.length)], []);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<SoloAnalyzeResponse | null>(null);

  const handleAnalyze = async () => {
    setError("");
    const cleaned = text.trim();
    if (cleaned.length < 2) {
      setError("Please write a little more (at least 2 characters).");
      return;
    }
    setLoading(true);
    try {
      const sessionId = sessionStorage.getItem("soloSessionId");
      const res = await api.soloAnalyze({ text: cleaned, session_id: sessionId });
      sessionStorage.setItem("soloSessionId", res.session_id);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Solo analysis failed");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden gradient-bg px-4 py-12">
      <FloatingOrbs />
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-4xl relative z-10"
      >
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="glass-card-strong p-10">
          <div className="text-center mb-8">
            <div className="w-14 h-14 rounded-2xl gradient-warm flex items-center justify-center mx-auto mb-4">
              <Pen className="w-7 h-7 text-primary-foreground" />
            </div>
            <h1 className="text-3xl font-display font-bold text-foreground mb-2">Page of Expression</h1>
            <p className="text-muted-foreground">
              Write freely. When you click Analyze, we’ll run a real NLP emotion model and then tailor suggestions for you.
            </p>
          </div>

          <div className="glass-card p-4 mb-6">
            <p className="text-sm text-primary font-medium italic">Prompt: {currentPrompt}</p>
          </div>

          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Start writing... There are no wrong answers here."
            rows={8}
            className="mindease-input resize-none mb-6"
          />

          <div className="flex gap-3">
            <button onClick={() => navigate("/content-selection")} className="btn-ghost flex-1 text-center">
              Skip
            </button>
            <button
              type="button"
              onClick={() => void handleAnalyze()}
              disabled={loading}
              className="btn-warm flex-1 text-center disabled:opacity-60"
            >
              {loading ? <Loader2 className="w-4 h-4 inline mr-2 animate-spin" /> : <Sparkles className="w-4 h-4 inline mr-2" />}
              Analyze
            </button>
          </div>
          {error ? <p className="text-sm text-destructive text-center mt-4">{error}</p> : null}
          </div>

          <div className="glass-card-strong p-10">
            <div className="text-center mb-6">
              <h2 className="text-2xl font-display font-bold text-foreground">Your Results</h2>
              <p className="text-muted-foreground text-sm mt-1">
                Each submission is analyzed fresh. We won’t reuse an earlier emotion unless your text supports it again.
              </p>
            </div>

            {!result ? (
              <div className="text-center text-muted-foreground">
                <p className="mb-2">Write something and click Analyze.</p>
                <p className="text-sm">You’ll see detected emotion, confidence, and tailored suggestions here.</p>
              </div>
            ) : (
              <div className="space-y-5">
                <div className="glass-card p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-xs text-muted-foreground">Detected emotion</div>
                      <div className="text-xl font-semibold text-foreground capitalize">{result.emotion}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-muted-foreground">Confidence</div>
                      <div className="text-lg font-semibold text-foreground">{formatPercent(result.confidence)}</div>
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground mt-3">
                    Model: <span className="font-medium text-foreground/80">{result.model_used}</span>
                  </div>
                </div>

                <div className="glass-card p-5">
                  <h3 className="font-semibold text-foreground mb-2">Exercises</h3>
                  <ul className="space-y-2 text-sm text-muted-foreground list-disc pl-5">
                    {result.suggestions.exercises.map((x) => (
                      <li key={x}>{x}</li>
                    ))}
                  </ul>
                </div>

                <div className="glass-card p-5">
                  <h3 className="font-semibold text-foreground mb-2">Tips</h3>
                  <ul className="space-y-2 text-sm text-muted-foreground list-disc pl-5">
                    {result.suggestions.tips.map((x) => (
                      <li key={x}>{x}</li>
                    ))}
                  </ul>
                </div>

                <div className="glass-card p-5">
                  <h3 className="font-semibold text-foreground mb-2">Motivational quotes</h3>
                  <div className="space-y-2">
                    {result.suggestions.quotes.map((q) => (
                      <p key={q} className="text-sm text-muted-foreground italic">
                        “{q}”
                      </p>
                    ))}
                  </div>
                </div>

                <div className="glass-card p-5">
                  <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2">
                    <Play className="w-4 h-4 text-primary" /> Videos
                  </h3>
                  <div className="space-y-2">
                    {result.suggestions.videos.map((v) => (
                      <a
                        key={`${v.title}-${v.url}`}
                        href={v.url}
                        target="_blank"
                        rel="noreferrer"
                        className="block text-sm text-primary hover:underline"
                      >
                        {v.title}
                      </a>
                    ))}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => navigate("/content-selection")}
                  className="btn-primary w-full text-center"
                >
                  Continue <ArrowRight className="w-4 h-4 inline ml-2" />
                </button>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default Expression;
