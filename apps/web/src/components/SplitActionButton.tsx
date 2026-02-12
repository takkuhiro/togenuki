import { useEffect, useRef, useState } from 'react';

interface SplitAction {
  key: string;
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
}

interface SplitActionButtonProps {
  actions: SplitAction[];
  disabled?: boolean;
  loading?: boolean;
}

export function SplitActionButton({
  actions,
  disabled = false,
  loading = false,
}: SplitActionButtonProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selected = actions[selectedIndex];
  const isDisabled = disabled || loading;

  useEffect(() => {
    if (!menuOpen) return;

    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [menuOpen]);

  return (
    <div className="split-action-button" ref={containerRef}>
      <button
        type="button"
        className="split-action-button-main audio-player-button"
        disabled={isDisabled}
        onClick={() => selected.onClick()}
      >
        {loading ? <span className="processing-spinner" aria-hidden="true" /> : selected.icon}
        {selected.label}
      </button>
      <button
        type="button"
        className="split-action-button-toggle audio-player-button"
        disabled={isDisabled}
        aria-label="選択肢を開く"
        onClick={() => setMenuOpen((prev) => !prev)}
      >
        <ChevronIcon />
      </button>
      {menuOpen && (
        <div className="split-action-button-menu" role="menu">
          {actions.map((action, index) => (
            <div
              key={action.key}
              role="menuitem"
              tabIndex={0}
              aria-label={action.label}
              className={`split-action-button-menu-item${index === selectedIndex ? ' split-action-button-menu-item--selected' : ''}`}
              onClick={() => {
                setSelectedIndex(index);
                setMenuOpen(false);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  setSelectedIndex(index);
                  setMenuOpen(false);
                }
              }}
            >
              {action.icon}
              {action.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ChevronIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M7 10l5 5 5-5z" />
    </svg>
  );
}
