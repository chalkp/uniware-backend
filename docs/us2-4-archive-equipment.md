# US2-4: Archive equipment

`POST /api/equipment/{id}/archive` archives equipment owned by the authenticated
provider. No request body is required. Session authentication and the existing
CSRF header are required, as for other write endpoints.

Success returns **200** with the existing equipment representation, including
`status: "ARCHIVED"` and an ISO 8601 `archived_at`. Retrying returns 200 without
changing the original timestamp. The endpoint does not delete the equipment,
release its unique `asset_id`, or modify any associated request or decision.
No database migration is needed: these fields already exist.

## Rules and errors

- Anonymous callers receive 401; callers without provider capability receive 403.
- Missing equipment and equipment owned by another provider both return 404.
- Equipment in RESERVED or CHECKED_OUT status, or with any APPROVED or
  CHECKED_OUT request, returns 409 with error code `BOOKING_CONFLICT`.
  Approved requests block archiving regardless of their dates until resolved.
- Other equipment statuses can be archived. PENDING, REJECTED, CANCELLED, and
  COMPLETED requests remain unchanged. Pending requests cannot subsequently be
  approved because approval requires AVAILABLE equipment.
- Archive is terminal in this API. Editing archived equipment, including trying
  to set it back to AVAILABLE, returns 409 `INVALID_STATE_TRANSITION`.

Errors follow the existing `{"error": {"code": "...", "message": "...",
"details": null}}` structure. Equipment locking serializes archive with provider
approval and equipment edits on PostgreSQL.

## Retention and visibility

Archived equipment remains in `GET /api/provider/equipment` for its owner.
It is excluded from `GET /api/equipment`, including search, category, location,
and availability filters. `GET /api/equipment/{id}` returns 404 for archived
equipment. New borrow requests for it are rejected by existing availability
validation. Historical borrower/provider request endpoints retain their nested
equipment details and identifiers. Category and location lookup lists remain
available because they are shared reference data.

There is no automatic purge or restore endpoint. Frontend confirmation and
success/error display are outside this backend change. After confirmation,
the frontend should POST to this endpoint, use the returned equipment to
refresh inventory, and display `error.message` on failure.

## Verification

`apps/equipment/tests/test_us2_4_archive_equipment.py` exercises successful and
repeated archive, permissions and ownership, active reservations/loans,
preserved history, inventory visibility, catalog filters/detail, blocked new
requests, blocked restoration, and blocked approval after archive.
