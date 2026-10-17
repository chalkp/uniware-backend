# Backend provider API: read-only request browsing

This version of UniWare retains provider request visibility, but deliberately
**does not implement request approval or rejection**.

- `config/urls.py`: includes `api/provider/` routes.
- `apps/requests/urls_provider.py`: provider list and detail GET URLs only.
- `apps/requests/views_provider.py`: read-only provider views, scoped to
  equipment owned by the authenticated provider.
- `apps/requests/serializers.py`: read-only provider-specific serializer,
  including borrower details.
- `apps/requests/tests/test_provider_api.py`: tests access boundaries and
  checks that POST approve/reject URLs return 404.

No approval/rejection mutation routes exist. No database migration was added.
The existing borrower request create, edit, cancellation and history endpoints
remain available.

Copy your private backend `.env` from the original backend before running.
