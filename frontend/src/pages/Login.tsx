import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import FloatingOrbs from "@/components/FloatingOrbs";
import { Heart, Eye, EyeOff, Mail, Lock, User } from "lucide-react";
import { api } from "@/lib/api";

const Login = () => {
  const [isSignUp, setIsSignUp] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (isSignUp && name.trim().length < 2) {
      setError("Name must be at least 2 characters.");
      return;
    }
    setLoading(true);
    try {
      const tokens = isSignUp
        ? await api.signup({ name: name.trim(), email: email.trim(), password })
        : await api.login({ email: email.trim(), password });
      localStorage.setItem("accessToken", tokens.access_token);
      localStorage.setItem("refreshToken", tokens.refresh_token);
      navigate("/home");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden gradient-bg px-4">
      <FloatingOrbs />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="glass-card-strong p-8 md:p-12 w-full max-w-md relative z-10"
      >
        <div className="text-center mb-8">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
            className="inline-flex items-center justify-center w-16 h-16 rounded-2xl gradient-primary mb-4"
          >
            <Heart className="w-8 h-8 text-primary-foreground" />
          </motion.div>
          <h1 className="text-3xl font-display font-bold text-foreground">MindEase</h1>
          <p className="text-muted-foreground mt-2">Your journey to inner peace starts here</p>
        </div>

        <div className="flex gap-2 p-1 bg-muted rounded-xl mb-8">
          <button
            onClick={() => setIsSignUp(false)}
            className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all duration-300 ${
              !isSignUp ? "bg-card shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Sign In
          </button>
          <button
            onClick={() => setIsSignUp(true)}
            className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all duration-300 ${
              isSignUp ? "bg-card shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Sign Up
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <AnimatePresence mode="wait">
            {isSignUp && (
              <motion.div
                key="name"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Full Name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="mindease-input pl-11"
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type="email"
              placeholder="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mindease-input pl-11"
            />
          </div>

          <div className="relative">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mindease-input pl-11 pr-11"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
            >
              {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>
          <p className="text-xs text-muted-foreground text-left">Use at least 8 characters (required by the server).</p>

          <button type="submit" className="btn-primary w-full text-center">
            {loading ? "Please wait..." : isSignUp ? "Create Account" : "Sign In"}
          </button>
          {error ? <p className="text-sm text-destructive text-center">{error}</p> : null}
        </form>

        <p className="text-center text-sm text-muted-foreground mt-6">
          {isSignUp ? "Already have an account? " : "Don't have an account? "}
          <button
            onClick={() => setIsSignUp(!isSignUp)}
            className="text-primary font-semibold hover:underline"
          >
            {isSignUp ? "Sign In" : "Sign Up"}
          </button>
        </p>
      </motion.div>
    </div>
  );
};

export default Login;
