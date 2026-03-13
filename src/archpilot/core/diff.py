"""Legacy vs Modern 시스템 비교 엔진."""

from __future__ import annotations

from archpilot.core.models import (
    Component,
    ComponentChange,
    Connection,
    ConnectionChange,
    DiffResult,
    SystemModel,
)


class SystemDiff:
    def compare(self, legacy: SystemModel, modern: SystemModel) -> DiffResult:
        legacy_map = {c.id: c for c in legacy.components}
        modern_map = {c.id: c for c in modern.components}

        added: list[Component] = []
        removed: list[Component] = []
        modified: list[ComponentChange] = []
        unchanged: list[Component] = []

        for cid, comp in modern_map.items():
            if cid not in legacy_map:
                added.append(comp)
            else:
                changes = self._changed_fields(legacy_map[cid], comp)
                if changes:
                    modified.append(ComponentChange(
                        before=legacy_map[cid],
                        after=comp,
                        changed_fields=changes,
                    ))
                else:
                    unchanged.append(comp)

        for cid, comp in legacy_map.items():
            if cid not in modern_map:
                removed.append(comp)

        connection_changes = self._diff_connections(legacy.connections, modern.connections)

        return DiffResult(
            added=added,
            removed=removed,
            modified=modified,
            unchanged=unchanged,
            connection_changes=connection_changes,
        )

    def _changed_fields(self, before: Component, after: Component) -> list[str]:
        fields = ["type", "label", "tech", "host"]
        changed = []
        for f in fields:
            if getattr(before, f) != getattr(after, f):
                changed.append(f)
        return changed

    def _diff_connections(
        self,
        legacy: list[Connection],
        modern: list[Connection],
    ) -> list[ConnectionChange]:
        def key(c: Connection) -> tuple:
            return (c.from_id, c.to_id, c.protocol)

        legacy_set = {key(c): c for c in legacy}
        modern_set = {key(c): c for c in modern}

        changes: list[ConnectionChange] = []
        for k, conn in modern_set.items():
            if k not in legacy_set:
                changes.append(ConnectionChange(change_type="added", connection=conn))
        for k, conn in legacy_set.items():
            if k not in modern_set:
                changes.append(ConnectionChange(change_type="removed", connection=conn))

        return changes
