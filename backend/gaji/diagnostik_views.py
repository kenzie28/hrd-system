"""Admin API for downloading the step-by-step Gaji diagnostic workbook."""
from django.http import HttpResponse
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from karyawan.permissions import IsAdminAllowed

from .access import HasGajiPassword
from .diagnostik import export_gaji_diagnostik_xlsx
from .services import gaji_for_month, parse_bulan

XLSX_CONTENT_TYPE = (
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
)


class AdminGajiDiagnostikExportView(APIView):
    """Download one month's payroll recalculated with Excel formulas."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminAllowed, HasGajiPassword]

    def get(self, request):
        try:
            periode = parse_bulan(request.query_params.get('bulan'))
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if not gaji_for_month(periode).exists():
            return Response(
                {'detail': 'Belum ada gaji untuk bulan ini.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        content = export_gaji_diagnostik_xlsx(periode)
        filename = f'gaji-diagnostik-{periode:%Y-%m}.xlsx'
        response = HttpResponse(content, content_type=XLSX_CONTENT_TYPE)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
