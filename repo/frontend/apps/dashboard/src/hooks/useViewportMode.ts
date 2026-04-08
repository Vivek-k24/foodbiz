import { useEffect, useState } from "react";

import type { ViewportMode } from "../lib/types";

function readViewportMode(): ViewportMode {
  if (typeof window === "undefined") {
    return "large";
  }
  if (window.innerWidth <= 760) {
    return "narrow";
  }
  if (window.innerWidth <= 1180) {
    return "medium";
  }
  return "large";
}

export function useViewportMode(): ViewportMode {
  const [mode, setMode] = useState<ViewportMode>(readViewportMode);

  useEffect(() => {
    function onResize(): void {
      setMode(readViewportMode());
    }

    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  return mode;
}
