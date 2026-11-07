from apps.accounts.services import require
from apps.establishments.services import list_establishments
from apps.inspections.services import list_inspections


def coverage(actor, filters):
    require(actor, "inspections.view_inspection")
    establishments = list_establishments(
        actor,
        {
            "kind": filters.get("establishment_kind"),
            "province": filters.get("province"),
            "search": filters.get("search"),
        },
    )
    visits = list_inspections(actor, filters).filter(establishment__in=establishments)
    inspected = visits.values("establishment_id").distinct().count()
    total = establishments.count()
    return {
        "establishments": total,
        "inspected": inspected,
        "uninspected": total - inspected,
        "visits": visits.count(),
        "approved": visits.filter(approved=True).count(),
        "unapproved": visits.filter(approved=False).count(),
        "coverage_percent": round(inspected * 100 / total, 1) if total else 0,
    }
