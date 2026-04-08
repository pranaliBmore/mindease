import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import FloatingOrbs from "@/components/FloatingOrbs";
import heroBg from "@/assets/hero-bg.jpg";
import { Heart, Sparkles, Shield, Users } from "lucide-react";
import { useRequireAuth } from "@/hooks/useRequireAuth";

const features = [
  { icon: Sparkles, title: "AI-Powered Support", desc: "Get personalized guidance through intelligent conversations" },
  { icon: Shield, title: "Safe Space", desc: "Express yourself freely in a judgment-free environment" },
  { icon: Users, title: "Community", desc: "Connect with others on similar journeys" },
];

const Home = () => {
  useRequireAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen relative overflow-hidden">
      <FloatingOrbs />

      {/* Hero */}
      <div className="relative min-h-[85vh] flex items-center">
        <div
          className="absolute inset-0 bg-cover bg-center opacity-30"
          style={{ backgroundImage: `url(${heroBg})` }}
        />
        <div className="absolute inset-0 gradient-bg" />

        <div className="container mx-auto px-6 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="max-w-2xl"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 mb-6">
              <Heart className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium text-primary">Welcome to MindEase</span>
            </div>
            <h1 className="text-5xl md:text-6xl lg:text-7xl font-display font-bold text-foreground leading-tight mb-6">
              Find Your
              <span className="text-gradient block">Inner Calm</span>
            </h1>
            <p className="text-lg text-muted-foreground max-w-lg mb-8 leading-relaxed">
              A supportive companion for managing anxiety and building confidence. 
              Choose your path to emotional well-being.
            </p>
            <div className="flex flex-wrap gap-4">
              <button onClick={() => navigate("/path-selection")} className="btn-primary">
                Begin Your Journey
              </button>
              <button onClick={() => navigate("/community")} className="btn-ghost">
                Explore Community
              </button>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Features */}
      <div className="container mx-auto px-6 py-20 relative z-10">
        <div className="grid md:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 + i * 0.15 }}
              className="glass-card p-8 hover:shadow-elevated transition-all duration-500 group"
            >
              <div className="w-12 h-12 rounded-xl gradient-primary flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <f.icon className="w-6 h-6 text-primary-foreground" />
              </div>
              <h3 className="text-xl font-display font-semibold text-foreground mb-2">{f.title}</h3>
              <p className="text-muted-foreground leading-relaxed">{f.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Home;
