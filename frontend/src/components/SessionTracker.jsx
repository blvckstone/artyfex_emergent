import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { api } from "@/lib/api";

const getSessionId = () => {
  try {
    let sid = localStorage.getItem("artyfex_sid");
    if (!sid) {
      sid = `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
      localStorage.setItem("artyfex_sid", sid);
    }
    return sid;
  } catch {
    return `s_${Date.now()}`;
  }
};

/**
 * Mounts once at App level. Sends a heartbeat every 20s and a pageview on route change.
 * Silently ignores failures.
 */
export default function SessionTracker() {
  const location = useLocation();
  const lastPathRef = useRef(null);

  // Heartbeat interval
  useEffect(() => {
    const sid = getSessionId();
    const send = () => {
      try {
        api.post("/analytics/heartbeat", { session_id: sid, path: window.location.pathname, user_agent: navigator.userAgent })
          .catch(() => {});
      } catch {}
    };
    send();
    const id = setInterval(send, 20000);
    return () => clearInterval(id);
  }, []);

  // Pageview on route change
  useEffect(() => {
    const path = location.pathname;
    if (lastPathRef.current === path) return;
    lastPathRef.current = path;
    // Skip admin pages from pageview counts (still counted in heartbeat)
    if (path.startsWith("/admin")) return;
    try {
      api.post("/analytics/pageview", { path, session_id: getSessionId(), referrer: document.referrer || null }).catch(() => {});
    } catch {}
  }, [location.pathname]);

  return null;
}
