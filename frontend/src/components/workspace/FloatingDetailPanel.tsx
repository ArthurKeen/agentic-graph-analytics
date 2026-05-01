"use client";

interface FloatingDetailPanelProps {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
}

export function FloatingDetailPanel({
  title,
  children,
  onClose
}: FloatingDetailPanelProps) {
  return (
    <aside className="floating-panel" aria-label={title}>
      <header>
        <strong>{title}</strong>
        <button type="button" onClick={onClose} aria-label="Close detail panel">
          ×
        </button>
      </header>
      <section>{children}</section>
    </aside>
  );
}
