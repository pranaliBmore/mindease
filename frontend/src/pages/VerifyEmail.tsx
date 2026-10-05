import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import FloatingOrbs from "@/components/FloatingOrbs";
import { MailCheck, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

const RESEND_COOLDOWN_SECONDS = 30;

const VerifyEmail = () => {
  const navigate = useNavigate();

  const [otp, setOtp] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState("");
  const [banner, setBanner] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const cooldownRef = useRef<number | null>(null);

  const { data: me, refetch } = useQuery({ queryKey: ["me"], queryFn: () => api.getMe() });

  useEffect(() => {
    if (me?.email_verified) {
      navigate("/home", { replace: true });
    }
  }, [me, navigate]);

  useEffect(() => {
    return () => {
      if (cooldownRef.current) window.clearInterval(cooldownRef.current);
    };
  }, []);

  const startCooldown = () => {
    setCooldown(RESEND_COOLDOWN_SECONDS);
    cooldownRef.current = window.setInterval(() => {
      setCooldown((prev) => {
        if (prev <= 1) {
          if (cooldownRef.current) window.clearInterval(cooldownRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const verify = async () => {
    const clean = otp.trim();
    if (clean.length < 4) {
      setError("Enter the code from your email.");
      return;
    }
    setError("");
    setBanner("");
    setVerifying(true);
    try {
      await api.verifyEmail(clean);
      await refetch();
      navigate("/home", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not verify email");
    } finally {
      setVerifying(false);
    }
  };

  const resend = async () => {
    setError("");
    setBanner("");
    setResending(true);
    try {
      const res = await api.resendOtp();
      setBanner(res.message);
      startCooldown();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not resend code");
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden gradient-bg px-4">
      <FloatingOrbs />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="glass-card-strong p-8 md:p-12 w-full max-w-md relative z-10 text-center"
      >
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl gradient-primary mb-4">
          <MailCheck className="w-8 h-8 text-primary-foreground" />
        </div>
        <h1 className="text-2xl font-display font-bold text-foreground mb-2">Verify your email</h1>
        <p className="text-muted-foreground text-sm mb-8">
          We sent a 6-digit code to <span className="text-foreground font-medium">{me?.email}</span>. Enter it
          below to finish setting up your account.
        </p>

        <input
          value={otp}
          onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 8))}
          onKeyDown={(e) => e.key === "Enter" && void verify()}
          placeholder="------"
          inputMode="numeric"
          className="mindease-input text-center text-2xl tracking-[0.5em] font-semibold mb-4"
        />

        {banner ? <p className="text-sm text-primary font-medium mb-3">{banner}</p> : null}
        {error ? <p className="text-sm text-destructive mb-3">{error}</p> : null}

        <button
          type="button"
          onClick={() => void verify()}
          disabled={verifying}
          className="btn-primary w-full mb-4 disabled:opacity-60"
        >
          {verifying ? <Loader2 className="w-4 h-4 animate-spin inline mr-2" /> : null}
          Verify email
        </button>

        <button
          type="button"
          onClick={() => void resend()}
          disabled={resending || cooldown > 0}
          className="text-sm text-primary font-semibold hover:underline disabled:opacity-50 disabled:no-underline"
        >
          {cooldown > 0 ? `Resend code in ${cooldown}s` : resending ? "Sending..." : "Resend code"}
        </button>
      </motion.div>
    </div>
  );
};

export default VerifyEmail;
