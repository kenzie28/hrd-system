from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from karyawan.permissions import IsAdminAllowed

from .services import (
    StateError,
    StateImportResult,
    export_state_csv,
    extract_password,
    import_state_csv,
    password_matches,
    serialize_import_result,
)


def _forbidden():
    return Response(
        {'detail': 'Kata sandi State Manager tidak valid.'},
        status=status.HTTP_403_FORBIDDEN,
    )


class AdminStateExportView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]

    def get(self, request):
        if not password_matches(extract_password(request)):
            return _forbidden()

        csv_text = export_state_csv()
        filename = timezone.localtime().strftime('hrd-state-%Y%m%d-%H%M%S.csv')
        response = HttpResponse(csv_text, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


class AdminStateImportView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if not password_matches(extract_password(request)):
            return _forbidden()

        upload = request.FILES.get('file')
        if upload is None:
            result = StateImportResult(
                errors=[StateError(0, 'File CSV wajib diunggah.')],
            )
            return Response(
                serialize_import_result(result),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            raw = upload.read()
            if isinstance(raw, bytes):
                text = raw.decode('utf-8-sig')
            else:
                text = str(raw)
        except UnicodeDecodeError:
            result = StateImportResult(
                errors=[StateError(0, 'File harus berformat UTF-8.')],
            )
            return Response(
                serialize_import_result(result),
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = import_state_csv(text)
        if not result.ok:
            return Response(
                serialize_import_result(result),
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(serialize_import_result(result), status=status.HTTP_200_OK)
