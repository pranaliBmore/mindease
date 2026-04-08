import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import FloatingOrbs from "@/components/FloatingOrbs";
import { ScanFace, Palette, Users, Bot, ArrowRight } from "lucide-react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { setJourneyFlow } from "@/lib/authFlow";

const PathSelection = () => {
  useRequireAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden gradient-bg px-4 py-12">
      <FloatingOrbs />
      <div className="container mx-auto max-w-5xl relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl md:text-5xl font-display font-bold text-foreground mb-4">
            Choose Your Path
          </h1>
          <p className="text-lg text-muted-foreground max-w-lg mx-auto">
            Select the experience that resonates with you. Both paths lead to growth.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* With Flow */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            onClick={() => {
              setJourneyFlow("with_flow");
              navigate("/emotion-analysis");
            }}
            className="glass-card-strong p-8 cursor-pointer group hover:shadow-elevated transition-all duration-500 hover:-translate-y-1"
          >
            <div className="w-14 h-14 rounded-2xl gradient-primary flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
              <ScanFace className="w-7 h-7 text-primary-foreground" />
            </div>
            <h2 className="text-2xl font-display font-bold text-foreground mb-3">With Community & AI</h2>
            <p className="text-muted-foreground mb-6 leading-relaxed">
              Get your emotions analyzed, chat with AI for guidance, and join a supportive community to build meaningful connections.
            </p>
            <div className="space-y-3 mb-6">
              {[
                { icon: ScanFace, text: "Face Emotion Analysis" },
                { icon: Bot, text: "AI Chat Support" },
                { icon: Users, text: "Community Connection" },
              ].map(({ icon: Icon, text }) => (
                <div key={text} className="flex items-center gap-3 text-sm text-foreground">
                  <Icon className="w-4 h-4 text-primary" />
                  <span>{text}</span>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-2 text-primary font-semibold group-hover:gap-3 transition-all">
              Start Journey <ArrowRight className="w-4 h-4" />
            </div>
          </motion.div>

          {/* Without Flow */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            onClick={() => {
              setJourneyFlow("without_flow");
              navigate("/expression");
            }}
            className="glass-card-strong p-8 cursor-pointer group hover:shadow-elevated transition-all duration-500 hover:-translate-y-1"
          >
            <div className="w-14 h-14 rounded-2xl gradient-warm flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
              <Palette className="w-7 h-7 text-primary-foreground" />
            </div>
            <h2 className="text-2xl font-display font-bold text-foreground mb-3">Solo Expression</h2>
            <p className="text-muted-foreground mb-6 leading-relaxed">
              Express yourself freely, explore curated motivational content, and find inspiration through quotes, videos, and exercises.
            </p>
            <div className="space-y-3 mb-6">
              {[
                { icon: Palette, text: "Page of Expression" },
                { text: "Motivational Content" },
                { text: "Personalized Feedback" },
              ].map(({ text }, i) => (
                <div key={text} className="flex items-center gap-3 text-sm text-foreground">
                  <div className="w-4 h-4 rounded-full bg-peach/30 flex items-center justify-center">
                    <div className="w-1.5 h-1.5 rounded-full bg-peach" />
                  </div>
                  <span>{text}</span>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-2 text-peach font-semibold group-hover:gap-3 transition-all">
              Begin Exploring <ArrowRight className="w-4 h-4" />
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default PathSelection;
