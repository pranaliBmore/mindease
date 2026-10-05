import type { ReactElement } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { hasValidSession } from "@/lib/api";

interface ProtectedRouteProps {
  children: ReactElement;
}

/**
 * Checked synchronously during render, not in a useEffect - an invalid session renders
 * the redirect directly instead of mounting `children` first and redirecting a tick
 * later. That gap let protected pages flash their full UI before the old per-page
 * useRequireAuth() effect fired, and the lazy-loaded page chunk never even needs to
 * load here since it's not in the render tree.
 */
const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
  const location = useLocation();

  if (!hasValidSession()) {
    return <Navigate to="/" replace state={{ from: location.pathname }} />;
  }

  return children;
};

export default ProtectedRoute;
