---
hide:
  - toc
---

# Accessories and Effects in a PMM Sync

Your PMM contains a list of accessories and their animation. If you use MME, an `.emm` file beside the PMM can also tell NineSync which effects were assigned to them.

During a sync, Core reads the PMM and passes the accessory information to FX. FX then imports the `.x` files, applies their animation and builds their effects. If FX is not installed, Core shows a notice when the project contains accessories. You can also use FX on its own to import `.x` files directly ([FX Import](../../fx/index.md)).

## Which effect is used?

FX chooses each accessory's effect by the rules in [Which `.fx` file is used](../../fx/import.md#which-fx-file-is-used). The `.emm` can also assign effects to individual material subsets.

## Matching accessories

MME and the PMM can list accessories in different orders, so FX matches them by path. It also accounts for repeated accessories and can fall back to the file name when there is only one possible match.

## Cleaning up

Core's **Clean** button also asks FX to remove the accessories and effects it created. If an FX error occurs during a sync, it is logged and the rest of the sync can continue.

How the hand-over works is in [Accessory and FX Integration](how-it-works/accessory-fx-integration.md).
