"""Virtual configurable residual devices; node remains the sole electrical meter."""
from models.flow import Datapoints


def has_meter(node):
    return node.kind == "node" and any(node.datapoints.get(key) for key in ("power_total", "power_l1", "power_l2", "power_l3"))


def residual_device(node):
    settings = node.residual
    return node.model_copy(update={
        "id": node.id + ":rest_consumption", "kind": "residual", "parent_id": node.id,
        "name": settings.name or node.name + " · Restverbrauch", "direction": "out", "category": "consumer",
        "group_id": settings.group_id, "color": settings.color or node.color, "icon": settings.icon or node.icon,
        "sort_order": node.sort_order if settings.sort_order is None else settings.sort_order,
        "datapoints": Datapoints(), "run_power_w": None, "storage_ids": [], "mppt_ids": [], "dc_load_ids": [],
    })


def with_residuals(flows):
    return [*flows, *(residual_device(node) for node in flows if has_meter(node))]


def apply_residual_display(item, node):
    settings = node.residual
    item.name = settings.name or node.name + " · Restverbrauch"
    item.color = settings.color or node.color
    item.icon = settings.icon or node.icon
    if hasattr(item, "name_is_generated"):
        item.name_is_generated = not bool(settings.name)
