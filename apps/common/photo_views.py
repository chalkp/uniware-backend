import mimetypes

from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.equipment.models import Equipment
from apps.requests.models import BorrowRequest


class PhotoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, resource, pk, variant):
        allowed = ("preview", "original", "preview-2", "original-2", "preview-3", "original-3")
        if variant not in allowed or (resource != "equipment" and "-" in variant):
            raise Http404
        if resource == "equipment":
            queryset = Equipment.objects.visible_to_borrowers()
            if request.user.is_provider:
                queryset = queryset | Equipment.objects.filter(provider=request.user)
        elif resource == "returns" and request.user.is_provider:
            queryset = BorrowRequest.objects.filter(equipment__provider=request.user)
        else:
            raise Http404
        obj = get_object_or_404(queryset, pk=pk)
        kind, _, slot = variant.partition("-")
        prefix = f"photo_{slot}" if slot else "photo"
        name = getattr(obj, f"{prefix}_{kind}")
        if not name:
            raise Http404
        try:
            file = default_storage.open(name, "rb")
        except FileNotFoundError as exc:
            raise Http404 from exc
        response = FileResponse(file, content_type=mimetypes.guess_type(name)[0])
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
