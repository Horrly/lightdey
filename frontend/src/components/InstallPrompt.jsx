import { useEffect, useState } from "react";

// Chrome/Android fire `beforeinstallprompt`; iPhones need a manual "Add to Home Screen".
export default function InstallPrompt() {
  const [promptEvent, setPromptEvent] = useState(null);
  const [dismissed, setDismissed] = useState(() => {
    try {
      return localStorage.getItem("ld.installDismissed") === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    const onPrompt = (e) => {
      e.preventDefault();
      setPromptEvent(e);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  if (!promptEvent || dismissed) return null;

  function dismiss() {
    setDismissed(true);
    try {
      localStorage.setItem("ld.installDismissed", "1");
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="fixed inset-x-3 bottom-3 z-30 mx-auto flex max-w-md items-center gap-3 rounded-2xl border border-night-600 bg-night-800 p-3 shadow-2xl">
      <img src="/icons/icon-192.png" alt="" className="h-10 w-10 rounded-xl" />
      <p className="flex-1 text-sm">
        <span className="font-semibold text-white">Install LightDey</span>
        <span className="block text-xs text-slate-400">One tap to report, alerts when light returns.</span>
      </p>
      <button className="text-xs text-slate-400" onClick={dismiss}>
        Not now
      </button>
      <button
        className="btn bg-glow-400 text-night-950 hover:bg-glow-300"
        onClick={async () => {
          promptEvent.prompt();
          await promptEvent.userChoice;
          setPromptEvent(null);
        }}
      >
        Install
      </button>
    </div>
  );
}
