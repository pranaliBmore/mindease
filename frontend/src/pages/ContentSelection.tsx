import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import FloatingOrbs from "@/components/FloatingOrbs";
import { Quote, Play, Dumbbell, BookOpen, Music, Sunrise, ArrowRight, Check } from "lucide-react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { setContentSelectionIds } from "@/lib/authFlow";

type Option = {
  id: string;
  icon: typeof Quote;
  label: string;
  desc: string;
  color: string;
  detail: string;
  whenToUse: string;
  howItWorks: string;
};

const options: Option[] = [
  {
    id: "quotes",
    icon: Quote,
    label: "Motivational Quotes",
    desc: "Short lines meant to lift perspective, not replace professional care.",
    color: "bg-sage/10 text-sage",
    detail:
      "Each quote is a bite-sized reframe: a reminder that feelings shift, effort counts, and you do not have to be perfect to move forward.",
    whenToUse:
      "Best when you have only a minute or two—before work, after a difficult message, or when you want something hopeful to anchor to.",
    howItWorks: "Select it here; later you can pair it with feedback so we know what resonated.",
  },
  {
    id: "videos",
    icon: Play,
    label: "Guided Videos",
    desc: "Calming or empowering visuals with voice-over guidance.",
    color: "bg-teal/10 text-teal",
    detail:
      "Videos combine movement, breath cues, or gentle coaching so you are not only reading—you are following along with your eyes and body.",
    whenToUse:
      "Use when sitting still with text feels hard, or when you want a structured session with a clear beginning and end.",
    howItWorks: "Choose this card if you learn well by watching and listening; you can select multiple types together.",
  },
  {
    id: "exercise",
    icon: Dumbbell,
    label: "Exercises",
    desc: "Light movement and grounding practices tied to mood.",
    color: "bg-peach/10 text-peach",
    detail:
      "These are simple physical or breath-based exercises (stretching, pacing, grounding steps)—not a workout plan and not medical treatment.",
    whenToUse:
      "Helpful when anxiety sits in the body, or when you want to change state quickly without needing special equipment.",
    howItWorks: "If selected, your feedback step can record that exercises mattered to you on this journey.",
  },
  {
    id: "reading",
    icon: BookOpen,
    label: "Mindful Reading",
    desc: "Slightly longer reads for reflection and self-compassion.",
    color: "bg-lavender/10 text-lavender",
    detail:
      "Articles or narrative pieces invite you to slow down, notice patterns in your thinking, and practice kinder self-talk.",
    whenToUse:
      "When you have a quiet window—commute reading, evening wind-down—and want depth instead of a single punchy line.",
    howItWorks: "Selecting this tells the app you value reflective content; combine with quotes or videos if you like variety.",
  },
  {
    id: "music",
    icon: Music,
    label: "Soothing Music",
    desc: "Soundscapes and playlists aimed at regulation and focus.",
    color: "bg-teal/10 text-teal",
    detail:
      "Music options lean toward steady tempos and minimal lyrics so your nervous system gets predictable auditory input.",
    whenToUse:
      "Ideal for background support while working, studying, or trying to sleep; also useful after overstimulation.",
    howItWorks: "Pick alongside meditation or videos if you want both auditory and visual anchors.",
  },
  {
    id: "meditation",
    icon: Sunrise,
    label: "Meditation",
    desc: "Guided attention practices (breath, body scan, gentle imagery).",
    color: "bg-sage/10 text-sage",
    detail:
      "Meditation here means short guided sessions: noticing breath, relaxing muscle groups, or visualizing a safe place—not religious instruction.",
    whenToUse:
      "When you want to practice sitting with discomfort in small doses, or build a repeatable ritual at the same time each day.",
    howItWorks: "You can select meditation alone or stack it with music; your choices only affect what we highlight in feedback.",
  },
];

const ContentSelection = () => {
  useRequireAuth();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<string[]>([]);

  const toggle = (id: string) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]));
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden gradient-bg px-4 py-12">
      <FloatingOrbs />
      <div className="container mx-auto max-w-5xl relative z-10">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-8">
          <h1 className="text-4xl font-display font-bold text-foreground mb-3">What Speaks to You?</h1>
          <p className="text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            This step shapes what we emphasize in your next screen (feedback). Each card explains what the option is, when it helps, and how it fits
            the journey. Select anything that feels useful—nothing here is required for “success,” and you can change preferences later by running the
            flow again.
          </p>
        </motion.div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
          {options.map((opt, i) => (
            <motion.div
              key={opt.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 + i * 0.06 }}
              onClick={() => toggle(opt.id)}
              className={`glass-card p-5 cursor-pointer transition-all duration-300 relative text-left ${
                selected.includes(opt.id) ? "ring-2 ring-primary shadow-elevated" : "hover:shadow-elevated"
              }`}
            >
              {selected.includes(opt.id) && (
                <div className="absolute top-3 right-3 w-6 h-6 rounded-full gradient-primary flex items-center justify-center">
                  <Check className="w-3 h-3 text-primary-foreground" />
                </div>
              )}
              <div className={`w-12 h-12 rounded-xl ${opt.color} flex items-center justify-center mb-3`}>
                <opt.icon className="w-6 h-6" />
              </div>
              <h3 className="font-semibold text-foreground mb-1">{opt.label}</h3>
              <p className="text-sm text-muted-foreground mb-3">{opt.desc}</p>
              <div className="space-y-2 text-xs text-muted-foreground border-t border-border/40 pt-3">
                <p>
                  <span className="font-medium text-foreground/90">What it is: </span>
                  {opt.detail}
                </p>
                <p>
                  <span className="font-medium text-foreground/90">When to use: </span>
                  {opt.whenToUse}
                </p>
                <p>
                  <span className="font-medium text-foreground/90">How it fits: </span>
                  {opt.howItWorks}
                </p>
              </div>
            </motion.div>
          ))}
        </div>

        <div className="text-center">
          <button
            onClick={() => {
              setContentSelectionIds(selected);
              navigate("/feedback");
            }}
            className="btn-warm"
          >
            Continue to Feedback <ArrowRight className="w-4 h-4 inline ml-2" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ContentSelection;
