"use client";

import type { ContextMenuItem } from "./contextMenus/types";

interface ObjectActionBarProps {
  items: ContextMenuItem[];
  /** Ids to drop here but keep on the context menu. "Open in canvas" is the
   * usual one: the object is already open. */
  omitIds?: string[];
}

/** The selected object's actions, as buttons.
 *
 * NFR-23: a capability a user cannot find is not delivered. The header used
 * to carry the line "Right-click steps or canvas for actions", which is the
 * product telling the user to go looking. These are the same items the
 * context menu builds, so the menu stays as the accelerator it is allowed
 * to be.
 */
export function ObjectActionBar({ items, omitIds = [] }: ObjectActionBarProps) {
  const omitted = new Set(omitIds);
  const actions = items.filter((item) => !omitted.has(item.id));

  if (actions.length === 0) {
    return null;
  }

  return (
    <div className="object-action-bar" role="group" aria-label="Actions">
      {actions.map((item) => (
        <button
          key={item.id}
          type="button"
          className="object-action"
          data-danger={item.danger ? "true" : undefined}
          onClick={(event) => {
            event.stopPropagation();
            item.onSelect();
          }}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
