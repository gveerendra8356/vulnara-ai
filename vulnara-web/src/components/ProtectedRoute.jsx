import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { LoadingRow } from "./Primitives";

export function ProtectedRoute({ children, requireAdmin = false }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <LoadingRow label="Checking session..." />
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace />;
  if (requireAdmin && user.role !== "admin") return <Navigate to="/" replace />;

  return children;
}
