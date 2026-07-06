export function Logo({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="trinetra-mark" x1="0" y1="0" x2="40" y2="40">
          <stop offset="0" stopColor="#2DD4BF" />
          <stop offset="1" stopColor="#00836C" />
        </linearGradient>
      </defs>
      <path
        d="M20 3 L34 8.5 V19 C34 28.5 28 34.5 20 37.5 C12 34.5 6 28.5 6 19 V8.5 Z"
        fill="rgba(0,131,108,.14)"
        stroke="url(#trinetra-mark)"
        strokeWidth="2"
      />
      <polyline
        points="10.5,21.5 15,21.5 17.5,14.5 21.5,26.5 24,19 26,21.5 29.5,21.5"
        fill="none"
        stroke="url(#trinetra-mark)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
