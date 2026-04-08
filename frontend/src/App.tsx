import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Suspense, lazy } from "react";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";

// Lazy load components
const Login = lazy(() => import("./pages/Login"));
const Home = lazy(() => import("./pages/Home"));
const PathSelection = lazy(() => import("./pages/PathSelection"));
const EmotionAnalysis = lazy(() => import("./pages/EmotionAnalysis"));
const ChatAI = lazy(() => import("./pages/ChatAI"));
const Community = lazy(() => import("./pages/Community"));
const Expression = lazy(() => import("./pages/Expression"));
const ContentSelection = lazy(() => import("./pages/ContentSelection"));
const Feedback = lazy(() => import("./pages/Feedback"));
const ThankYou = lazy(() => import("./pages/ThankYou"));
const NotFound = lazy(() => import("./pages/NotFound"));

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Suspense fallback={<div>Loading...</div>}>
          <Routes>
            <Route path="/" element={<Login />} />
            <Route path="/home" element={<Home />} />
            <Route path="/path-selection" element={<PathSelection />} />
            <Route path="/emotion-analysis" element={<EmotionAnalysis />} />
            <Route path="/chat-ai" element={<ChatAI />} />
            <Route path="/community" element={<Community />} />
            <Route path="/expression" element={<Expression />} />
            <Route path="/content-selection" element={<ContentSelection />} />
            <Route path="/feedback" element={<Feedback />} />
            <Route path="/thank-you" element={<ThankYou />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
