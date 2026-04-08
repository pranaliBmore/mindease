import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import FloatingOrbs from "@/components/FloatingOrbs";
import { Star, MessageSquare, ArrowRight } from "lucide-react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { api } from "@/lib/api";
import { getContentTypeForFeedback, getJourneyFlow } from "@/lib/authFlow";

const Feedback = () => {
  useRequireAuth();
  const navigate = useNavigate();
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [feedback, setFeedback] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    setError("");
    if (rating < 1) {
      setError("Please choose a star rating (1–5).");
      return;
    }
    const message = feedback.trim() || "No additional comments.";
    if (message.length < 2) {
      setError("Please enter at least a short comment or use the default by leaving the box empty.");
      return;
    }
    setLoading(true);
    try {
      const contentType = getContentTypeForFeedback();
      await api.submitFeedback({
        flow_type: getJourneyFlow(),
        content_type: contentType ?? null,
        message,
        rating,
      });
      navigate("/thank-you");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit feedback");
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
        className="w-full max-w-md relative z-10"
      >
        <div className="glass-card-strong p-10 text-center">
          <div className="w-14 h-14 rounded-2xl gradient-warm flex items-center justify-center mx-auto mb-4">
            <MessageSquare className="w-7 h-7 text-primary-foreground" />
          </div>
          <h1 className="text-3xl font-display font-bold text-foreground mb-2">Your Feedback</h1>
          <p className="text-muted-foreground mb-8">How was your experience today?</p>

          <div className="flex justify-center gap-2 mb-8">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                onMouseEnter={() => setHover(star)}
                onMouseLeave={() => setHover(0)}
                onClick={() => setRating(star)}
                className="transition-transform duration-200 hover:scale-125"
              >
                <Star
                  className={`w-10 h-10 ${
                    star <= (hover || rating) ? "text-peach fill-peach" : "text-border"
                  } transition-colors`}
                />
              </button>
            ))}
          </div>

          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Share your thoughts... (optional if you rated above)"
            rows={4}
            className="mindease-input resize-none mb-6 text-left"
          />

          {error ? <p className="text-sm text-destructive mb-4">{error}</p> : null}

          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="btn-warm w-full text-center disabled:opacity-50"
          >
            {loading ? "Submitting..." : "Submit Feedback"}{" "}
            <ArrowRight className="w-4 h-4 inline ml-2" />
          </button>
        </div>
      </motion.div>
    </div>
  );
};

export default Feedback;
