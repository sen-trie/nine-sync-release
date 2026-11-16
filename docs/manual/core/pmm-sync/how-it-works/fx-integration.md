# Accessories and Effects in a PMM Sync

Your PMM contains a list of accessories and their animation. If you use MME, an `.emm` file beside the PMM can also tell NineSync which effects were assigned to them.

During a sync, Core reads the PMM and passes the accessory information to FX. FX then imports the `.x` files, applies their animation and builds their effects. If FX is not installed, Core shows a notice when the project contains accessories. You can also use FX on its own to import `.x` files directly.

## Which effect is used?

FX checks these in order and uses the first one that applies:

1. The **Effect File** you selected for the accessory.
2. An assignment in the `.emm` file beside the PMM.
3. A `.fx` file with the same name as the `.x`, in the same folder.

The `.emm` can assign effects to individual material subsets, hide an accessory, or specify that it has no effect. If the `.emm` names an effect that cannot be found, NineSync reports it instead of choosing another file. If the accessory is not listed in the `.emm`, FX looks for a matching `.fx` beside it.

## Matching accessories

MME and the PMM can list accessories in different orders, so FX matches them by path. It also accounts for repeated accessories and can fall back to the file name when there is only one possible match.

## Cleaning up

Core's **Clean** button also asks FX to remove the accessories and effects it created. If an FX error occurs during a sync, it is logged and the rest of the sync can continue.

See [FX Import](../../../fx/import.md#which-fx-file-is-used) for more about choosing effects.
