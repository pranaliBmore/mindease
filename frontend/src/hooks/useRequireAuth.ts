import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

export function useRequireAuth() {
  const navigate = useNavigate();

  useEffect(() => {
    if (!localStorage.getItem("accessToken")) {
      navigate("/", { replace: true });
    }
  }, [navigate]);
}
