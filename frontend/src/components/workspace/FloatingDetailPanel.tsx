"use client";

interface FloatingDetailPanelProps {
  title: string;
  children: React.ReactNode;
  placement?: "viewportTopRight" | "mainColumnTopLeft";
  stackIndex?: number;
  onClose: () => void;
}

export function FloatingDetailPanel({
  title,
  children,
  placement = "viewportTopRight",
  stackIndex = 0,
  onClose
}: FloatingDetailPanelProps) {
  const offset = stackIndex * 14;
  const translateX = placement === "viewportTopRight" ? -offset : offset;

  return (
    <aside
      className="floating-panel"
      data-placement={placement}
      aria-label={title}
      style={{
        transform: `translate(${translateX}px, ${offset}px)`
      }}
    >
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
