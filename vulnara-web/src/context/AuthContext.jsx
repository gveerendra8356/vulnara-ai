import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, USE_MOCK } from "../lib/api";
import { TOKEN_KEY } from "../lib/httpClient";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const hydrate = useCallback(async () => {
    const hasToken = USE_MOCK ? true : !!localStorage.getItem(TOKEN_KEY);
    if (!hasToken && !USE_MOCK) {
      setLoading(false);
      return;
    }
    try {
      // In mock mode there's no persisted session on refresh (by design —
      // Mock Mode is a demo sandbox, not real storage), so this will only
      // resolve after an explicit login() call sets state.currentUser.
      const me = await api.me();
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    hydrate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = async (email, password) => {
    const data = await api.login({ email, password });
    setUser(data.user);
    return data.user;
  };

  const register = async (payload) => {
    return api.register(payload);
  };

  const logout = async () => {
    await api.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
