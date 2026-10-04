# M9SPOOLRESET1A — one-time diagnostic backlog purge

The 26 September diagnostic bundle showed a large recovered sidecar backlog. This
overlay is intentionally non-photographic: on the first visible launch after the
update it deletes only files inside the app-private directory:

`filesDir/m9diag_spool`

It then writes `filesDir/m9diag_spool_reset1a.done`, so later launches do not
repeat the purge.

## Preserved

- JPEG and DNG files
- public DCIM diagnostic JSON files already exported
- app preferences/settings
- renderer, colour, SAT2, curve02, BT.601 and TG1
- TC20 and Auto-exposure FINISH1J
- PRIMARYEXPORT1B fresh-first export

## Purpose

Recovered private sidecars from older sessions can otherwise continue exporting
long after their capture, making a newly appearing SOURCECAL/TTL/etc. file look as
though it belongs to the newest photograph. Resetting the private queue gives the
next test a clean diagnostic generation boundary.

The next diagnostic bundle should report `M9SPOOLRESET1A_ONCE`,
`spoolResetCompleted=true`, a nonzero deletion count/bytes if backlog existed,
and recovered/pending counts near zero before new captures repopulate them.
