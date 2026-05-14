export function apiBaseUrl(): string {
  const fromEnv = import.meta.env.VITE_API_BASE_URL as string | undefined;
  if (fromEnv) {
    return fromEnv.replace(/\/$/, "");
  }
  return "";
}

export function apiPath(path: string): string {
  const base = apiBaseUrl();
  if (!path.startsWith("/")) {
    path = `/${path}`;
  }
  return `${base}${path}`;
}

export function wsLiveUrl(): string {
  const fromEnv = import.meta.env.VITE_WS_LIVE_URL as string | undefined;
  if (fromEnv) {
    return fromEnv;
  }

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${window.location.host}/ws/live`;
}
