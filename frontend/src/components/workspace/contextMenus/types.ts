export interface ContextMenuItem {
  id: string;
  label: string;
  icon: string;
  danger?: boolean;
  /** Which menu an item belongs to. The canvas menu was a flat list of
   * twelve mixing object creation, workspace lifecycle, view controls and
   * help as equals. Grouping lets the menu separate them and lets the
   * sidebar render the create and workspace groups as visible menus. */
  group?: "create" | "workspace" | "view" | "help";
  onSelect: () => void;
}

export interface ContextMenuState {
  x: number;
  y: number;
  items: ContextMenuItem[];
}
