import React, { createContext, useContext, useState, useEffect } from "react";
import api from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("access_token"));
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("user") || "null");
    } catch {
      return null;
    }
  });
  const [loading] = useState(false);

  useEffect(() => {
    // Listen for custom logout events dispatched from API client interceptor
    const handleLogoutEvent = () => {
      setToken(null);
      setUser(null);
    };

    window.addEventListener("auth-logout", handleLogoutEvent);
    return () => {
      window.removeEventListener("auth-logout", handleLogoutEvent);
    };
  }, []);

  const login = async (username, password) => {
    const response = await api.post("/auth/login", { username, password });
    const { access_token, refresh_token } = response.data;

    // Decode basic user info from JWT or build user object
    let parsedUser = { username, role: username === "admin" ? "admin" : "evaluator" };
    try {
      const parts = access_token.split(".");
      if (parts.length === 3) {
        const payload = JSON.parse(atob(parts[1]));
        parsedUser = {
          username: payload.username || username,
          role: payload.role || "evaluator",
        };
      }
    } catch (e) {
      console.warn("Could not decode payload", e);
    }

    localStorage.setItem("access_token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
    localStorage.setItem("user", JSON.stringify(parsedUser));

    setToken(access_token);
    setUser(parsedUser);
    return parsedUser;
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (refreshToken) {
      try {
        await api.post("/auth/logout", { refresh_token: refreshToken });
      } catch (err) {
        console.error("Logout request error:", err);
      }
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        isAuthenticated: !!token,
        loading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
