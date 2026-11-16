# Equipment and return photos

US2-6 and US7-6 extend the checkout/return workflow from `origin/US6/7/8`.

Send multipart form data with optional `photo` to POST `/api/equipment`, PATCH
`/api/equipment/{id}`, or POST `/api/provider/requests/{id}/return`. The return
endpoint still requires `return_condition`. JSON requests without photos remain
supported. To remove an attachment before retrying a return, omit `photo`.

Equipment responses and provider request responses include nullable
`photo_preview_url` and `photo_original_url`. These are root-relative authenticated
API URLs. Use the preview normally and fetch the full-size image on click. A null
URL or failed download should show a frontend placeholder. Existing photos are
unchanged when an equipment update omits `photo`.

JPEG (.jpg/.jpeg), PNG and WebP are accepted after inspecting their decoded content.
Animated files, corrupt files and extension/content mismatches are rejected.
Incoming files are limited to 20 MiB and 40 million pixels. Preview images are WebP,
strictly smaller than 1 MiB, with a maximum 1920-pixel long edge and no upscaling.
Quality starts at 80 with encoding effort 3; additional resizing/compression is
bounded. Full-size images preserve their extension, format and pixel dimensions
(dimensions swap when orientation is corrected). Filenames are randomized.

Metadata is removed from both files. Unrotated JPEG compressed image data is
preserved without re-encoding. JPEGs requiring orientation correction are encoded
at quality 100 without chroma subsampling, so those are not pixel-exact originals.
PNG and WebP full-size copies are encoded losslessly. EXIF, GPS, XMP, textual
metadata and embedded color profiles are not retained.

Both files must save successfully before a return completes. Database failures or
upload failures roll back state and remove newly written files. Equipment photo
replacement deletes old files after commit. Cleanup errors are logged for operators;
storage and database are separate systems, so crash recovery/orphan reconciliation
is an operational concern. A repeat return receives a state-conflict response.

Equipment photos use catalog visibility rules, with additional owner access for
inventory items. Return photos are accessible only to the equipment's managing
provider. Downloads require session authentication and use `private, no-store`.
Do not configure a public media directory route. Docker stores files in the
`uniware_media` volume; include it in backups alongside the database.

Deploy with `docker compose up --build` and apply migrations using the project's
normal migration command. New dependencies are pinned in `uv.lock`. The photo
fields require no backfill; existing records have no photo.

Run photo integration tests with `uv run pytest apps/common/tests/test_photos.py`.
Frontend preview/selection, upload progress, placeholders and click-to-open UI
are separate implementation work.

## Verification notes

All 15 photo tests passed. A local synthetic 4000x3000 noisy JPEG (12,023,490
bytes) took 0.679 seconds to process and produced a 446,902-byte WebP preview.
This is a single local measurement, not a production latency guarantee.

The branch now includes master through `13ad05d`, including its archive workflow,
consent implementation and corrections to the six previously failing base tests.
The equipment migration merge joins the independent photo and notice migrations.
Archived equipment cannot have its photos replaced; the existing archive guard
and transactional photo cleanup are both retained.

## Up to three equipment photos

Equipment create/update accepts multipart `photo`, `photo_2`, and `photo_3` for slots 1–3. Each supplied slot replaces only that slot; omitted slots remain unchanged. Supplying a numbered slot above 3 returns 400. Equipment responses include `photos`, an ordered list of `{slot, preview_url, original_url}` for occupied slots; the existing `photo_preview_url` and `photo_original_url` still refer to slot 1. Each URL uses the same visibility and authentication rules and each upload has the same processing limits. Return records continue to support one photo.

To delete equipment photos, send `remove_photos` with slot numbers 1–3 in a provider-owned equipment PATCH. In multipart requests, repeat `remove_photos` for each slot; JSON arrays are also supported. A slot cannot be replaced and removed in the same request. File deletion is scheduled after the database transaction commits.
