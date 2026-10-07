import { useCallback, useEffect, useState } from "react";

/** Measures an element's width. Uses a callback ref so it also works when the element mounts late. */
export function useWidth<T extends HTMLElement>(initial = 720) {
  const [el, setEl] = useState<T | null>(null);
  const [width, setWidth] = useState(initial);
  const ref = useCallback((node: T | null) => setEl(node), []);
  useEffect(() => {
    if (!el) return;
    setWidth(Math.max(280, Math.floor(el.getBoundingClientRect().width)));
    const ro = new ResizeObserver(([e]) => setWidth(Math.max(280, Math.floor(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, [el]);
  return [ref, width] as const;
}
