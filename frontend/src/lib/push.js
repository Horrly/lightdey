import { api } from "./api";
import { pushAreas } from "./local";

let configPromise;
function pushConfig() {
  configPromise ??= api("/push/config/").catch(() => ({ enabled: false }));
  return configPromise;
}

export function pushSupported() {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

// iPhones only allow web push for apps added to the home screen.
export function needsInstallForPush() {
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const standalone = window.matchMedia?.("(display-mode: standalone)").matches || navigator.standalone;
  return ios && !standalone;
}

function urlBase64ToUint8Array(base64) {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const raw = atob((base64 + padding).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

async function subscription(publicKey) {
  const registration = await navigator.serviceWorker.ready;
  const existing = await registration.pushManager.getSubscription();
  if (existing) return existing;
  return registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  });
}

export async function enableLightAlerts(slug) {
  const config = await pushConfig();
  if (!config.enabled) throw new Error("Notifications aren't available yet.");
  if (!pushSupported()) throw new Error("This browser doesn't support notifications.");

  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("Allow notifications in your browser settings to get alerts.");

  const sub = await subscription(config.public_key);
  await api(`/areas/${slug}/push/`, { method: "POST", body: sub.toJSON() });
  pushAreas.set(slug, true);
}

export async function disableLightAlerts(slug) {
  const registration = await navigator.serviceWorker.ready;
  const sub = await registration.pushManager.getSubscription();
  if (sub) await api(`/areas/${slug}/push/`, { method: "DELETE", body: { endpoint: sub.endpoint } });
  pushAreas.set(slug, false);
}
