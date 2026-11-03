import type { ContextMenuItem } from "./types";

interface BuildAssetContextMenuArgs {
  onViewInfo: () => void;
  onCopyId: () => void;
}

export function buildAssetContextMenu({
  onViewInfo,
  onCopyId
}: BuildAssetContextMenuArgs): ContextMenuItem[] {
  return [
    {
      id: "view-info",
      label: "View Info",
      onSelect: onViewInfo
    },
    {
      id: "copy-id",
      label: "Copy ID",
      onSelect: onCopyId
    }
  ];
}
