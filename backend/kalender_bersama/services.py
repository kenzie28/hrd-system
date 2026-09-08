from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone

from cuti.models import Cuti, PermohonanCuti, StatusPermohonanCuti
from karyawan.models import Karyawan

from .models import Langganan, NotifikasiDismiss

VISIBLE_CUTI_STATUSES = (
    StatusPermohonanCuti.APPROVED,
    StatusPermohonanCuti.MENUNGGU_PEMBATALAN_SUPERVISOR,
    StatusPermohonanCuti.MENUNGGU_PEMBATALAN_HRD,
)

SEARCH_MIN_CHARS = 2
SEARCH_LIMIT = 20
NOTIFICATION_DAYS = 14
CALENDAR_MAX_SPAN_DAYS = 93


class ServiceError(Exception):
    def __init__(self, detail, status_code=400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def subscribed_ids(subscriber):
    return Langganan.objects.filter(subscriber=subscriber).values_list(
        'target_id', flat=True
    )


def list_langganan(subscriber):
    return (
        Langganan.objects.filter(subscriber=subscriber)
        .select_related('target')
        .order_by('target__nama', 'target_id')
    )


def search_karyawan(subscriber, q):
    query = (q or '').strip()
    if len(query) < SEARCH_MIN_CHARS:
        return Karyawan.objects.none()
    return (
        Karyawan.objects.filter(
            Q(nama__icontains=query) | Q(karyawan_id__icontains=query)
        )
        .exclude(pk=subscriber.pk)
        .order_by('nama', 'karyawan_id')[:SEARCH_LIMIT]
    )


def subscribe(subscriber, karyawan_id):
    target_id = str(karyawan_id or '').strip()
    if not target_id:
        raise ServiceError('karyawan_id wajib diisi.')
    if target_id == subscriber.karyawan_id:
        raise ServiceError('Tidak dapat menambahkan diri sendiri ke grup.')
    target = Karyawan.objects.filter(pk=target_id).first()
    if target is None:
        raise ServiceError('Karyawan tidak ditemukan.', 404)
    if Langganan.objects.filter(subscriber=subscriber, target=target).exists():
        raise ServiceError('Rekan sudah ada di grup.')
    return Langganan.objects.create(subscriber=subscriber, target=target)


def unsubscribe(subscriber, karyawan_id):
    target_id = str(karyawan_id or '').strip()
    deleted, _ = Langganan.objects.filter(
        subscriber=subscriber, target_id=target_id
    ).delete()
    if not deleted:
        raise ServiceError('Rekan tidak ada di grup.', 404)


def upcoming_cuti(subscriber, today=None, days=NOTIFICATION_DAYS):
    today = today or timezone.localdate()
    window_end = today + timedelta(days=days)
    dismissed_ids = NotifikasiDismiss.objects.filter(
        subscriber=subscriber
    ).values_list('permohonan_id', flat=True)
    return (
        PermohonanCuti.objects.filter(
            karyawan_id__in=subscribed_ids(subscriber),
            status__in=VISIBLE_CUTI_STATUSES,
            tanggal_mulai__lte=window_end,
            tanggal_selesai__gte=today,
        )
        .exclude(pk__in=dismissed_ids)
        .select_related('karyawan')
        .order_by('tanggal_mulai', 'karyawan__nama', 'id')
    )


def dismiss_notification(subscriber, permohonan_id):
    permohonan = PermohonanCuti.objects.filter(pk=permohonan_id).first()
    if permohonan is None:
        raise ServiceError('Notifikasi tidak ditemukan.', 404)
    if not Langganan.objects.filter(
        subscriber=subscriber, target=permohonan.karyawan
    ).exists():
        raise ServiceError('Notifikasi tidak ditemukan.', 404)
    NotifikasiDismiss.objects.get_or_create(
        subscriber=subscriber, permohonan=permohonan
    )


def parse_date_range(dari, sampai):
    start = _parse_iso_date(dari, 'dari')
    end = _parse_iso_date(sampai, 'sampai')
    if start > end:
        raise ServiceError('Tanggal dari tidak boleh setelah sampai.')
    if (end - start).days > CALENDAR_MAX_SPAN_DAYS:
        raise ServiceError('Rentang kalender terlalu panjang.')
    return start, end


def calendar_days(subscriber, dari, sampai):
    return (
        Cuti.objects.filter(
            permohonan__karyawan_id__in=subscribed_ids(subscriber),
            permohonan__status__in=VISIBLE_CUTI_STATUSES,
            tanggal__gte=dari,
            tanggal__lte=sampai,
        )
        .select_related('permohonan', 'permohonan__karyawan')
        .order_by('tanggal', 'permohonan__karyawan__nama', 'id')
    )


def _parse_iso_date(value, field):
    raw = str(value or '').strip()
    if not raw:
        raise ServiceError(f'Parameter {field} wajib diisi.')
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except ValueError:
        raise ServiceError(f'Parameter {field} harus berformat YYYY-MM-DD.')
