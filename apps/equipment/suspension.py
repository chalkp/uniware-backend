"""Effective suspension and in-app notices for owners and affected borrowers."""
from apps.accounts.models import AccountStatus
from apps.requests.models import BorrowRequest
from .models import Equipment, EquipmentSuspensionNotice


def owner_suspended(owner):
    return owner.account_status == AccountStatus.SUSPENDED or not owner.is_active


def notify_equipment_change(equipment, suspended, *, reason=""):
    """Call only when effective suspension actually changed, in the same DB transaction."""
    action = "suspended" if suspended else "reactivated"
    detail = f" Reason: {reason}" if suspended and reason else ""
    message = f"Equipment {equipment.name} ({equipment.asset_id}) was {action}.{detail}"[:500]
    recipient_ids = {equipment.provider_id}
    recipient_ids.update(
        BorrowRequest.objects.filter(
            equipment=equipment,
            status__in=(BorrowRequest.StatusChoices.PENDING, BorrowRequest.StatusChoices.APPROVED),
        ).values_list("borrower_id", flat=True)
    )
    EquipmentSuspensionNotice.objects.bulk_create([
        EquipmentSuspensionNotice(recipient_id=pk, equipment=equipment, message=message)
        for pk in recipient_ids
    ])
