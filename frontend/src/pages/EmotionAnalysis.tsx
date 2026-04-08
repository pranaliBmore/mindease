import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import FloatingOrbs from "@/components/FloatingOrbs";
import { ScanFace, ArrowRight, Loader2, Camera } from "lucide-react";
import { api, type EmotionResponse } from "@/lib/api";
import { getCameraStream, isCameraSupportedEnvironment, stopMediaStream } from "@/lib/camera";
import { useRequireAuth } from "@/hooks/useRequireAuth";

const EmotionAnalysis = () => {
  useRequireAuth();
  const navigate = useNavigate();
  const [stage, setStage] = useState<"scan" | "result" | "reason">("scan");
  const [detected, setDetected] = useState<EmotionResponse | null>(null);
  const [reason, setReason] = useState("");
  const [scanning, setScanning] = useState(false);
  const [cameraError, setCameraError] = useState("");
  const [reasonStepError, setReasonStepError] = useState("");
  const [cameraOn, setCameraOn] = useState(false);
  const [videoReady, setVideoReady] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    return () => {
      stopMediaStream(streamRef.current);
      streamRef.current = null;
    };
  }, []);

  useEffect(() => {
    const attachStreamToVideo = async () => {
      if (!cameraOn || !videoRef.current || !streamRef.current) return;
      try {
        videoRef.current.srcObject = streamRef.current;
        await videoRef.current.play();
      } catch (err) {
        setCameraError(err instanceof Error ? err.message : "Unable to start camera preview");
      }
    };
    attachStreamToVideo();
  }, [cameraOn]);

  const startCamera = async () => {
    setCameraError("");
    setVideoReady(false);
    try {
      const stream = await getCameraStream({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      setCameraOn(true);
    } catch (err) {
      setCameraError(
        err instanceof Error ? err.message : "Camera permission denied. Please allow camera access.",
      );
    }
  };

  const stopCamera = () => {
    stopMediaStream(streamRef.current);
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setVideoReady(false);
    setCameraOn(false);
  };

  const handleCaptureAndAnalyze = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    if (!videoReady) {
      setCameraError("Camera is starting. Please wait a moment and capture again.");
      return;
    }
    setScanning(true);
    setCameraError("");
    try {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new Error("Camera context unavailable");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const imageBase64 = canvas.toDataURL("image/jpeg", 0.9);
      const result = await api.detectEmotion({ image_base64: imageBase64 });
      handleAnalysisResult(result);
    } catch (err) {
      setScanning(false);
      setCameraError(err instanceof Error ? err.message : "Emotion analysis failed");
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setScanning(true);
    setCameraError("");
    const reader = new FileReader();
    reader.onload = async (ev) => {
      try {
        const imageBase64 = ev.target?.result as string;
        const result = await api.detectEmotion({ image_base64: imageBase64 });
        handleAnalysisResult(result);
      } catch (err) {
        setScanning(false);
        setCameraError(err instanceof Error ? err.message : "Emotion analysis failed");
      }
    };
    reader.onerror = () => {
      setScanning(false);
      setCameraError("Failed to read image file");
    };
    reader.readAsDataURL(file);
  };

  const handleAnalysisResult = (result: EmotionResponse) => {
    setDetected(result);
    localStorage.removeItem("emotionReason");
    sessionStorage.setItem("emotionSessionId", result.id);
    localStorage.setItem("detectedEmotion", result.emotion);
    localStorage.setItem("detectedEmotionConfidence", String(result.confidence));
    stopCamera();
    setScanning(false);
    setStage("result");
  };

  const syncSessionAndGoToChat = async (reasonText: string | null) => {
    setReasonStepError("");
    const sid = sessionStorage.getItem("emotionSessionId");
    if (sid) {
      try {
        await api.attachEmotionReason({ emotion_id: sid, text: reasonText?.trim() ?? "" });
      } catch (err) {
        setReasonStepError(err instanceof Error ? err.message : "Could not save your note");
        return;
      }
    }
    const trimmed = reasonText?.trim();
    if (trimmed) {
      localStorage.setItem("emotionReason", trimmed);
    } else {
      localStorage.removeItem("emotionReason");
    }
    navigate("/chat-ai");
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden gradient-bg px-4 py-12">
      <FloatingOrbs />
      <div className="w-full max-w-lg relative z-10">
        <AnimatePresence mode="wait">
          {stage === "scan" && (
            <motion.div
              key="scan"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="glass-card-strong p-10 text-center"
            >
              <div className="w-32 h-32 mx-auto rounded-full bg-primary/10 flex items-center justify-center mb-6 relative">
                {scanning ? (
                  <Loader2 className="w-16 h-16 text-primary animate-spin" />
                ) : (
                  <ScanFace className="w-16 h-16 text-primary" />
                )}
                {scanning && (
                  <motion.div
                    className="absolute inset-0 rounded-full border-2 border-primary/30"
                    animate={{ scale: [1, 1.3, 1], opacity: [0.5, 0, 0.5] }}
                    transition={{ repeat: Infinity, duration: 1.5 }}
                  />
                )}
              </div>
              <h1 className="text-3xl font-display font-bold text-foreground mb-3">Emotion Analysis</h1>
              <p className="text-muted-foreground mb-8">
                Let us understand how you're feeling right now
              </p>
              {!isCameraSupportedEnvironment() ? (
                <p className="text-sm text-muted-foreground mb-4 rounded-xl border border-border/60 bg-muted/40 px-4 py-3">
                  This browser does not expose camera APIs. Use a current Chrome, Firefox, Safari, or Edge — not an
                  in-app browser preview if it blocks <code className="text-xs">getUserMedia</code>.
                </p>
              ) : null}
              <div className="space-y-3">
                {!cameraOn ? (
                  <>
                    <button
                      onClick={startCamera}
                      disabled={scanning || !isCameraSupportedEnvironment()}
                      className="btn-primary w-full text-center"
                    >
                      <Camera className="w-4 h-4 inline mr-2" />
                      Analyse using Camera
                    </button>
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      disabled={scanning}
                      className="btn-ghost w-full text-center border border-primary/30"
                    >
                      Upload an Image
                    </button>
                  </>
                ) : (
                  <>
                    <div className="overflow-hidden rounded-xl border border-border/60 bg-black/20 min-h-[256px]">
                      <video
                        ref={videoRef}
                        autoPlay
                        playsInline
                        muted
                        onLoadedData={() => setVideoReady(true)}
                        onCanPlay={() => setVideoReady(true)}
                        onPlaying={() => setVideoReady(true)}
                        className="w-full h-64 object-cover"
                      />
                    </div>
                    <button
                      onClick={handleCaptureAndAnalyze}
                      disabled={scanning || !videoReady}
                      className="btn-primary w-full text-center"
                    >
                      {scanning ? "Analyzing..." : "Capture & Analyze"}
                    </button>
                  </>
                )}
                {cameraError ? <p className="text-sm text-destructive">{cameraError}</p> : null}
              </div>
              <input 
                type="file" 
                accept="image/*" 
                ref={fileInputRef} 
                className="hidden" 
                onChange={handleFileUpload} 
              />
              <canvas ref={canvasRef} className="hidden" />
            </motion.div>
          )}

          {stage === "result" && detected && (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="glass-card-strong p-10 text-center"
            >
              <h2 className="text-2xl font-display font-bold text-foreground mb-2">
                Detected: {detected.emotion}
              </h2>
              <p className="text-muted-foreground mb-2 leading-relaxed">{detected.description}</p>
              <p className="text-sm text-muted-foreground mb-8">
                Confidence: {(detected.confidence * 100).toFixed(1)}%
              </p>
              <button
                type="button"
                onClick={() => {
                  setReason("");
                  setReasonStepError("");
                  setStage("reason");
                }}
                className="btn-primary w-full text-center"
              >
                Continue <ArrowRight className="w-4 h-4 inline ml-2" />
              </button>
            </motion.div>
          )}

          {stage === "reason" && (
            <motion.div
              key="reason"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="glass-card-strong p-10"
            >
              <h2 className="text-2xl font-display font-bold text-foreground mb-2 text-center">
                What's on your mind?
              </h2>
              <p className="text-muted-foreground text-center mb-6">
                Share what brought you here today—only if you want to. Anything you type applies to{" "}
                <span className="font-medium text-foreground">this check-in only</span>. Leaving it blank is fine; we
                will not reuse an older note.
              </p>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Optional — e.g. work stress, a conversation, or nothing specific…"
                rows={5}
                className="mindease-input resize-none mb-6"
              />
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => void syncSessionAndGoToChat(null)}
                  className="btn-ghost flex-1 text-center"
                >
                  Skip
                </button>
                <button
                  type="button"
                  onClick={() => void syncSessionAndGoToChat(reason)}
                  className="btn-primary flex-1 text-center"
                >
                  Continue to Chat
                </button>
              </div>
              {reasonStepError ? <p className="text-sm text-destructive text-center mt-3">{reasonStepError}</p> : null}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default EmotionAnalysis;
