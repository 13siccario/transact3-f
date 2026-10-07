export function Star({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">
      <path d="M12 0l2.2 7.3L21 4l-3.3 6.8L24 12l-6.3 1.2L21 20l-6.8-3.3L12 24l-2.2-7.3L3 20l3.3-6.8L0 12l6.3-1.2L3 4l6.8 3.3z" />
    </svg>
  );
}

export function Curl({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 120 56" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round">
      <path d="M2 52C18 40 30 20 44 12c10-6 20-2 16 8-4 10-20 10-18-2 2-12 24-14 40-8 20 8 34 4 52-12" />
    </svg>
  );
}
