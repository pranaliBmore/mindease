import { useNavigate } from "react-router-dom";
import { ArrowRight, HeartHandshake } from "lucide-react";

const FindMatchPrompt = () => {
  const navigate = useNavigate();

  return (
    <button
      type="button"
      onClick={() => navigate("/match")}
      className="w-full text-left glass-card p-5 cursor-pointer group hover:shadow-elevated transition-all duration-500 hover:-translate-y-1 flex items-center gap-4"
    >
      <div className="w-11 h-11 rounded-xl gradient-primary flex items-center justify-center shrink-0 group-hover:scale-110 transition-transform">
        <HeartHandshake className="w-5 h-5 text-primary-foreground" />
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="font-semibold text-foreground">Don't know anyone here yet? Find a match</h3>
        <p className="text-sm text-muted-foreground">
          Answer a few quick questions and we'll anonymously pair you with someone going through something similar.
        </p>
      </div>
      <ArrowRight className="w-4 h-4 text-primary shrink-0 group-hover:translate-x-1 transition-transform" />
    </button>
  );
};

export default FindMatchPrompt;
