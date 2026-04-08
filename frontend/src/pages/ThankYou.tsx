import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import FloatingOrbs from "@/components/FloatingOrbs";
import { Heart, Sparkles } from "lucide-react";
import { useRequireAuth } from "@/hooks/useRequireAuth";
import { api } from "@/lib/api";

const ThankYou = () => {
  useRequireAuth();
  const navigate = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);

  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await api.logout();
    } catch {
      /* still clear local session */
    } finally {
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      navigate("/");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden gradient-bg px-4">
      <FloatingOrbs />
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.7, ease: "easeOut" }}
        className="text-center relative z-10 max-w-md"
      >
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.3, type: "spring", stiffness: 200 }}
          className="w-24 h-24 rounded-3xl gradient-primary flex items-center justify-center mx-auto mb-8 relative"
        >
          <Heart className="w-12 h-12 text-primary-foreground" />
          <motion.div
            className="absolute -top-2 -right-2"
            animate={{ rotate: [0, 15, -15, 0] }}
            transition={{ repeat: Infinity, duration: 3 }}
          >
            <Sparkles className="w-6 h-6 text-peach" />
          </motion.div>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="text-4xl md:text-5xl font-display font-bold text-foreground mb-4"
        >
          Thank You
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="text-lg text-muted-foreground mb-10 leading-relaxed"
        >
          Remember, every step you take toward understanding yourself is a step toward growth. 
          You are braver than you believe. 💚
        </motion.p>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="flex flex-col sm:flex-row gap-4 justify-center"
        >
          <button onClick={() => navigate("/home")} className="btn-ghost">
            Back to Home
          </button>
          <button type="button" onClick={handleLogout} disabled={loggingOut} className="btn-primary">
            {loggingOut ? "Signing out…" : "Log Out"}
          </button>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default ThankYou;
