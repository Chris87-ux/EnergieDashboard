# Consumer groups

[Documentation](README.md) · [Devices and nodes](DEVICES-AND-NODES.md) · [CSV](CSV.md)

## Purpose

A consumer group is an additional view across the electrical node hierarchy. Pumps in the house, yard and workshop can share one group while remaining connected to different meters. Group totals do not create a new flow, alter node residuals or add consumption again to the site balance.

## Configure

1. Under **Configuration → Consumer groups**, create the group with name, colour and display order.
2. Edit a consumer and choose **Additional consumer group (optional)**.
3. Repeat for the other consumers. A device belongs to at most one additional group; No group is valid.
4. Check group live power and Today energy in the overview. The energy balance shows group energy for its selected period.

Ordinary consumption devices (`kind=device`, `direction=out`) are eligible, including RUN and optional DC consumers. Grid, nodes, batteries, producers, MPPTs and hybrid inverters are not normal group consumers. Automatic node residuals are not assignable, avoiding aggregation of another measurement boundary into the same device sum.

## Calculation

Live power sums the magnitudes of active member powers. RUN devices contribute their fixed watts while running. Group energy sums each member's energy in the chosen period; it does not sum current lifetime counter readings.

Disabled devices and descendants of disabled nodes are excluded. A missing member power makes group power unknown. Incomplete history is marked. An empty group is zero. DC consumers can be included in their group without adding them again to the AC site balance.

Membership follows the **current configuration** for the selected historic period. Moving a device later applies its available history to its new group; time-dependent historic memberships are not recorded. Groups cannot reconstruct missing or incorrect device history.

## Maintenance

Lower display-order values appear first and do not affect calculations. Groups have stable IDs, survive updates/full backup/restore, and appear as `record_type=consumer_group` in full CSV. Device rows reference `group_id` independently of `parent_id`.

A group still referenced by any device, including disabled ones, cannot be deleted. Remove/reassign those devices first. Keep IDs unchanged when renaming groups or editing CSV.
