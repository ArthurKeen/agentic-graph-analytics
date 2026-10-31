"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import type { ContextMenuState } from "./contextMenus/types";

interface ContextMenuProps {
  menu: ContextMenuState | null;
  onClose: () => void;
}

/** Keep the menu on screen.
 *
 * It is positioned at the pointer, and the canvas menu can run to twelve
 * items. Right-clicking in the lower half of the window used to render the
 * last items below the fold with no way to scroll to them. */
function clampToViewport(
  x: number,
  y: number,
  width: number,
  height: number
): { left: number; top: number } {
  const margin = 8;
  const maxLeft = window.innerWidth - width - margin;
  const maxTop = window.innerHeight - height - margin;
  return {
    left: Math.max(margin, Math.min(x, maxLeft)),
    top: Math.max(margin, Math.min(y, maxTop))
  };
}

export function ContextMenu({ menu, onClose }: ContextMenuProps) {
  const menuRef = useRef<HTMLDivElement | null>(null);
  const [position, setPosition] = useState<{ left: number; top: number } | null>(
    null
  );

  // Measure after paint, before the browser shows it at the raw coordinates.
  useLayoutEffect(() => {
    if (!menu || !menuRef.current) {
      setPosition(null);
      return;
    }
    const rect = menuRef.current.getBoundingClientRect();
    setPosition(clampToViewport(menu.x, menu.y, rect.width, rect.height));
  }, [menu]);

  // role="menu" promises arrow-key navigation to a screen reader. Without
  // this the element announced itself as a menu and then ignored every key.
  useEffect(() => {
    if (!menu) {
      return;
    }
    const first = menuRef.current?.querySelector<HTMLButtonElement>(
      "[role='menuitem']"
    );
    first?.focus();
  }, [menu]);

  if (!menu) {
    return null;
  }

  const moveFocus = (from: HTMLElement, delta: number) => {
    const items = Array.from(
      menuRef.current?.querySelectorAll<HTMLButtonElement>("[role='menuitem']") ??
        []
    );
    if (items.length === 0) {
      return;
    }
    const index = items.indexOf(from as HTMLButtonElement);
    const next = (index + delta + items.length) % items.length;
    items[next]?.focus();
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const target = event.target as HTMLElement;
    const items = Array.from(
      menuRef.current?.querySelectorAll<HTMLButtonElement>("[role='menuitem']") ??
        []
    );
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        moveFocus(target, 1);
        break;
      case "ArrowUp":
        event.preventDefault();
        moveFocus(target, -1);
        break;
      case "Home":
        event.preventDefault();
        items[0]?.focus();
        break;
      case "End":
        event.preventDefault();
        items[items.length - 1]?.focus();
        break;
      case "Escape":
        event.preventDefault();
        onClose();
        break;
      default:
        break;
    }
  };

  return (
    <div
      ref={menuRef}
      className="context-menu"
      style={{
        left: position?.left ?? menu.x,
        top: position?.top ?? menu.y,
        // Hidden for the single frame between mount and measurement, so the
        // menu never flashes at the unclamped position.
        visibility: position ? "visible" : "hidden"
      }}
      role="menu"
      onKeyDown={onKeyDown}
      onContextMenu={(event) => event.preventDefault()}
    >
      {menu.items.map((item, index) => (
        <button
          key={item.id}
          type="button"
          role="menuitem"
          data-danger={item.danger ? "true" : undefined}
          // A rule above the first item of each group. The canvas menu mixed
          // creation, workspace lifecycle, view controls and help as equals.
          data-group-start={
            index > 0 &&
            item.group !== undefined &&
            item.group !== menu.items[index - 1]?.group
              ? "true"
              : undefined
          }
          onClick={() => {
            item.onSelect();
            onClose();
          }}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
