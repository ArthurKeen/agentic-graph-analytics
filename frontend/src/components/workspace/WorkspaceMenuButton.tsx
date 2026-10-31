"use client";

import { useEffect, useRef, useState } from "react";
import type { ContextMenuItem } from "./contextMenus/types";

interface WorkspaceMenuButtonProps {
  label: string;
  items: ContextMenuItem[];
}

/** A labelled dropdown for workspace-level actions.
 *
 * FR-1 and FR-13: creating a workspace, uploading a document, editing,
 * archiving and exporting were reachable only by right-clicking empty
 * canvas. These are the same items the canvas menu builds, so the menu
 * stays as the accelerator NFR-23 allows it to be.
 */
export function WorkspaceMenuButton({ label, items }: WorkspaceMenuButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const closeOnOutside = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", closeOnOutside);
    return () => document.removeEventListener("mousedown", closeOnOutside);
  }, [isOpen]);

  if (items.length === 0) {
    return null;
  }

  const moveFocus = (from: HTMLElement, delta: number) => {
    const buttons = Array.from(
      containerRef.current?.querySelectorAll<HTMLButtonElement>(
        "[role='menuitem']"
      ) ?? []
    );
    if (buttons.length === 0) {
      return;
    }
    const index = buttons.indexOf(from as HTMLButtonElement);
    buttons[(index + delta + buttons.length) % buttons.length]?.focus();
  };

  return (
    <div className="workspace-menu" ref={containerRef}>
      <button
        type="button"
        className="workspace-menu-trigger"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" && !isOpen) {
            event.preventDefault();
            setIsOpen(true);
          }
        }}
      >
        {label}
      </button>
      {isOpen ? (
        <div
          className="workspace-menu-items"
          role="menu"
          aria-label={label}
          onKeyDown={(event) => {
            const target = event.target as HTMLElement;
            if (event.key === "ArrowDown") {
              event.preventDefault();
              moveFocus(target, 1);
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              moveFocus(target, -1);
            } else if (event.key === "Escape") {
              event.preventDefault();
              setIsOpen(false);
            }
          }}
        >
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              role="menuitem"
              data-danger={item.danger ? "true" : undefined}
              onClick={() => {
                setIsOpen(false);
                item.onSelect();
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
