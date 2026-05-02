"use client";

import { useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";

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
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const dragStartRef = useRef<{
    pointerX: number;
    pointerY: number;
    panelX: number;
    panelY: number;
  } | null>(null);

  const startDrag = (event: ReactPointerEvent<HTMLElement>) => {
    if (event.button !== 0) {
      return;
    }

    dragStartRef.current = {
      pointerX: event.clientX,
      pointerY: event.clientY,
      panelX: dragOffset.x,
      panelY: dragOffset.y
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const drag = (event: ReactPointerEvent<HTMLElement>) => {
    if (!dragStartRef.current) {
      return;
    }

    setDragOffset({
      x: dragStartRef.current.panelX + event.clientX - dragStartRef.current.pointerX,
      y: dragStartRef.current.panelY + event.clientY - dragStartRef.current.pointerY
    });
  };

  const stopDrag = (event: ReactPointerEvent<HTMLElement>) => {
    dragStartRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  return (
    <aside
      className="floating-panel"
      data-placement={placement}
      aria-label={title}
      style={{
        transform: `translate(${translateX + dragOffset.x}px, ${offset + dragOffset.y}px)`
      }}
    >
      <header
        className="floating-panel-header"
        onPointerDown={startDrag}
        onPointerMove={drag}
        onPointerUp={stopDrag}
        onPointerCancel={stopDrag}
      >
        <strong>{title}</strong>
        <button
          className="floating-panel-close"
          type="button"
          onPointerDown={(event) => event.stopPropagation()}
          onClick={onClose}
          aria-label="Close detail panel"
        >
          ×
        </button>
      </header>
      <section>{children}</section>
    </aside>
  );
}
