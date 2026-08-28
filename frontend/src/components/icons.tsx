interface IconProps {
  className?: string;
}

export const PlayIcon = ({ className }: IconProps) => (
  <svg viewBox="0 0 24 24" className={className} fill="currentColor" aria-hidden="true">
    <path d="M8 5v14l11-7z" />
  </svg>
);

export const PauseIcon = ({ className }: IconProps) => (
  <svg viewBox="0 0 24 24" className={className} fill="currentColor" aria-hidden="true">
    <path d="M6 5h4v14H6zM14 5h4v14h-4z" />
  </svg>
);

export const RestartIcon = ({ className }: IconProps) => (
  <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
    <path d="M3 12a9 9 0 1 0 3-6.7" strokeLinecap="round" />
    <path d="M3 4v4h4" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const MicIcon = ({ className }: IconProps) => (
  <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
    <rect x="9" y="3" width="6" height="11" rx="3" fill="currentColor" stroke="none" />
    <path d="M5 11a7 7 0 0 0 14 0M12 18v3" strokeLinecap="round" />
  </svg>
);

export const SendIcon = ({ className }: IconProps) => (
  <svg viewBox="0 0 24 24" className={className} fill="currentColor" aria-hidden="true">
    <path d="M3 11l18-8-8 18-2-7-8-3z" />
  </svg>
);

export const FilmIcon = ({ className }: IconProps) => (
  <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">
    <rect x="3" y="4" width="18" height="16" rx="2" />
    <path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4" strokeLinecap="round" />
  </svg>
);
