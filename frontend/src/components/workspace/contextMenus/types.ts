export interface ContextMenuItem {
  id: string;
  label: string;
  icon: string;
  danger?: boolean;
  onSelect: () => void;
}

export interface ContextMenuState {
  x: number;
  y: number;
  items: ContextMenuItem[];
}
