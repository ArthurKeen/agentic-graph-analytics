"use client";

import type { ContextMenuState } from "./contextMenus/types";

interface ContextMenuProps {
  menu: ContextMenuState | null;
  onClose: () => void;
}

export function ContextMenu({ menu, onClose }: ContextMenuProps) {
  if (!menu) {
    return null;
  }

  return (
    <div
      className="context-menu"
      style={{ left: menu.x, top: menu.y }}
      role="menu"
      onContextMenu={(event) => event.preventDefault()}
    >
      {menu.items.map((item) => (
        <button
          key={item.id}
          type="button"
          role="menuitem"
          data-danger={item.danger ? "true" : undefined}
          onClick={() => {
            item.onSelect();
            onClose();
          }}
        >
          <span aria-hidden="true">{item.icon}</span> {item.label}
        </button>
      ))}
    </div>
  );
}
