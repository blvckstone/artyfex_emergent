import React, { useEffect, useState } from "react";
import { X, Download } from "lucide-react";

export default function PWAInstallPrompt() {
  const [deferred, setDeferred] = useState(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const key = "pwa_install_dismissed_v1";
    if (localStorage.getItem(key)) return;
    const handler = (e) => {
      e.preventDefault();
      setDeferred(e);
      setVisible(true);
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  if (!visible || !deferred) return null;
  const dismiss = () => {
    localStorage.setItem("pwa_install_dismissed_v1", "1");
    setVisible(false);
  };
  const install = async () => {
    deferred.prompt();
    const choice = await deferred.userChoice;
    if (choice && choice.outcome) {
      localStorage.setItem("pwa_install_dismissed_v1", "1");
    }
    setVisible(false);
    setDeferred(null);
  };

  return (
    <div
      data-testid="pwa-install-prompt"
      className="fixed z-[60] bottom-20 lg:bottom-6 left-4 right-4 lg:left-auto lg:right-6 lg:max-w-sm bg-ink-900 border border-gold/30 shadow-xl p-4 flex items-start gap-3"
      style={{ paddingBottom: "calc(1rem + env(safe-area-inset-bottom))" }}
    >
      <div className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-gold/15 text-gold shrink-0"><Download className="w-4 h-4" /></div>
      <div className="flex-1">
        <div className="font-serif text-cream text-base">Install ArtyFex</div>
        <div className="text-cream/60 text-xs mt-1">Add to home screen for a native-app experience — faster, offline-ready.</div>
        <div className="mt-3 flex gap-2">
          <button onClick={install} data-testid="pwa-install-yes" className="px-3 py-2 text-[10px] uppercase tracking-luxury bg-gold text-ink-950 hover:bg-cream transition-colors">Install</button>
          <button onClick={dismiss} data-testid="pwa-install-no" className="px-3 py-2 text-[10px] uppercase tracking-luxury text-cream/60 hover:text-cream">Not now</button>
        </div>
      </div>
      <button onClick={dismiss} aria-label="Dismiss install prompt" className="text-cream/50 hover:text-cream"><X className="w-4 h-4" /></button>
    </div>
  );
}
