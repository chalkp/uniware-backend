# Seed equipment photos

Place photos here named `UNIWARE-NNNN-S.ext`, where `NNNN` is the four-digit asset number and `S` is the photo slot (1, 2 or 3). Supported extensions: `.jpg`, `.jpeg`, `.png`, `.webp` (case-insensitive).

Examples: `UNIWARE-0001-1.jpg`, `UNIWARE-0001-2.png`, `UNIWARE-0001-3.webp`. Slots can be omitted. Use only one file per asset and slot.

The numbered assets follow the order in `EQUIPMENT_NAMES` in `apps/common/management/commands/seed.py`. For example, `UNIWARE-0001` is Cubemars Motor AK80-9 and `UNIWARE-0009` is GoPro Hero 12.

Images are copied into the Docker image when it is built. After adding or changing files, rebuild and restart the API container (`docker compose up -d --build api`), apply migrations (`docker compose exec api python manage.py migrate`), and run `make seed`. Seed imports only empty photo slots; it never overwrites existing photos. Delete or replace photos through an appropriate management operation if you intentionally need to change existing data.

Files are processed like uploaded photos: metadata is removed, the original format is retained, and a WebP preview is created. The input limit is 20 MiB and 40 million pixels. Originals and previews are stored in the persistent `uniware_media` Docker volume, separate from these source files.
