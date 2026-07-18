import { useEffect, useState } from "react";

export function currentPath() {
  return `${window.location.pathname}${window.location.search}`;
}

export function navigate(path, { replace = false } = {}) {
  if (replace) {
    window.history.replaceState({}, "", path);
  } else {
    window.history.pushState({}, "", path);
  }
  window.dispatchEvent(new PopStateEvent("popstate"));
}

export function useLocation() {
  const [path, setPath] = useState(currentPath);

  useEffect(() => {
    const updateLocation = () => setPath(currentPath());
    window.addEventListener("popstate", updateLocation);
    return () => window.removeEventListener("popstate", updateLocation);
  }, []);

  return path;
}

export function loginPath(nextPath = currentPath()) {
  return `/login?next=${encodeURIComponent(nextPath)}`;
}

export function requestedDestination(search) {
  const next = new URLSearchParams(search).get("next");
  return next && next.startsWith("/app") ? next : "/app";
}
