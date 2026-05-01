"use client";

interface FloatingDetailPanelProps {
  title: string;
  children: React.ReactNode;
  placement?: "viewportTopRight" | "mainColumnTopLeft";
  onClose: () => void;
}

export function FloatingDetailPanel({
  title,
  children,
  placement = "viewportTopRight",
  onClose
}: FloatingDetailPanelProps) {
  return (
    <aside className="floating-panel" data-placement={placement} aria-label={title}>
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
