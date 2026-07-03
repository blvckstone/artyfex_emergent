import React, { createContext, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";

const AuthContext = createContext(null);
const TOKEN_KEY = "artyfex_user_token";

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || "");
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState("login"); // login | signup

  useEffect(() => {
    if (!token) { setReady(true); return; }
    api.get("/auth/me", { headers: { Authorization: `Bearer ${token}` } })
      .then(r => setUser(r.data))
      .catch(() => { localStorage.removeItem(TOKEN_KEY); setToken(""); })
      .finally(() => setReady(true));
  }, [token]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem(TOKEN_KEY, data.token);
    setToken(data.token); setUser(data.user); setDialogOpen(false);
  };
  const signup = async (name, email, password, phone) => {
    const { data } = await api.post("/auth/signup", { name, email, password, phone });
    localStorage.setItem(TOKEN_KEY, data.token);
    setToken(data.token); setUser(data.user); setDialogOpen(false);
  };
  const logout = () => { localStorage.removeItem(TOKEN_KEY); setToken(""); setUser(null); };
  const openAuth = (mode = "login") => { setDialogMode(mode); setDialogOpen(true); };

  const authedApi = () => {
    const inst = api.create ? api.create() : api;
    if (token) inst.defaults.headers.common["Authorization"] = `Bearer ${token}`;
    return inst;
  };

  const updateProfile = async (updates) => {
    const inst = authedApi();
    const { data } = await inst.patch("/auth/me", updates);
    setUser(data);
    return data;
  };

  return (
    <AuthContext.Provider value={{ token, user, ready, login, signup, logout, updateProfile, dialogOpen, setDialogOpen, dialogMode, openAuth, authedApi }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
