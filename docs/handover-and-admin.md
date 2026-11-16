# Handover and administration contract

Deploy the matching frontend and backend integration branches together. Apply migrations with `python manage.py migrate` before serving requests.

## Checkout and loan lifecycle

Pending -> Approved -> Checked Out -> Returned. Rejection and cancellation retain their existing paths. A checked-out BorrowRequest is the loan; its equipment and borrower relations, pickup/due dates, and return history remain authoritative. A new one-to-one Checkout record stores the immutable pickup timestamp and authenticated provider actor. There is no second mutable loan status to drift out of sync. Existing checked-out/returned requests remain valid legacy loans with no invented audit record.

- `GET /api/provider/requests/ready-for-pickup?page=1`: provider-scoped paginated approved requests, active borrower, eligible inventory, no suspension/disable, no existing checkout, pickup date today or later (preserves the existing early-pickup policy).
- `POST /api/provider/requests/{id}/checkout` with `{}`: owner and active provider only; locks request, borrower and equipment, creates Checkout and updates request/equipment atomically. Wrong owner 404, wrong role 403, ineligible or duplicate 409. Nonempty input 400; the client cannot assign timestamp/actor.
- Borrower checkout now returns 403; the provider confirms physical handover.
- Request serializers include `checkout_record: {checkout_at, handover_person: {id, first_name, last_name, email, department, account_status}}` or null. No API supports modifying this record.
- `GET /api/loans/mine?status=active&page=1`: authenticated borrower's CHECKED_OUT requests, earliest due date first; excludes merely approved and returned requests, includes legacy active loans.
- Return still requires `return_condition` and keeps the handover record.

## Administration

- `GET /api/auth/users?search=full%20name&page=1`: now returns a pagination envelope, not an array. Case-insensitive email/name token matching, default 20 per page and maximum 100. No credentials or session data are returned.
- Role updates accept only boolean `is_admin`, `is_provider`, `is_borrower`; current sessions read role changes on subsequent requests. Existing suspension/reactivation revokes sessions.
- `POST /api/admin/equipment/{id}/disable` with `{reason: "..."}`: admin-only, nonblank reason up to 1000 characters. Sets existing disabled_at and disabled_reason once; repeated calls retain the first audit data. Physical availability and all requests/loans remain unchanged, so returns continue normally. It is separate from a reversible manual suspension.
- Catalog/search/filter/detail exclude disabled and suspended equipment before pagination/counting. Admin inventory and provider inventory retain these items; authorized request history remains accessible.
