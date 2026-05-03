import time
import requests
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

MINUTES_BEFORE = 15
MINUTES_AFTER = 10
CACHE_SECONDS = 300
MERGE_GAP_MINUTES = 5  # si dos bloqueos están separados por menos de esto, se fusionan

class NewsFilter:
    def __init__(self, api_key, cache_seconds=CACHE_SECONDS):
        self.api_key = api_key
        self.cache_seconds = cache_seconds
        self._cache_timestamp = 0
        self._cached_blocked_intervals = []  # lista de tuplas (inicio, fin) en UTC

    def _get_economic_calendar(self):
        today = datetime.now(timezone.utc).date()
        tomorrow = today + timedelta(days=1)
        url = "https://finnhub.io/api/v1/calendar/economic"
        params = {
            "from": today.strftime("%Y-%m-%d"),
            "to": tomorrow.strftime("%Y-%m-%d"),
            "token": self.api_key
        }
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Error obteniendo calendario: {e}")
            return []

    def _merge_intervals(self, intervals, gap=timedelta(minutes=MERGE_GAP_MINUTES)):
        """Fusiona intervalos que se solapan o están separados por menos de gap."""
        if not intervals:
            return []
        sorted_intervals = sorted(intervals, key=lambda x: x[0])
        merged = [sorted_intervals[0]]
        for current in sorted_intervals[1:]:
            last = merged[-1]
            if current[0] <= last[1] + gap:
                # Se fusionan: extiende el último intervalo hasta el máximo de los fines
                merged[-1] = (last[0], max(last[1], current[1]))
            else:
                merged.append(current)
        return merged

    def _get_all_blocked_intervals(self):
        """Obtiene y fusiona todos los bloques de alto impacto USD/EUR del día."""
        events = self._get_economic_calendar()
        now = datetime.now(timezone.utc)
        intervals = []
        # Países/regiones que afectan EUR/USD
        relevant_countries = ["United States", "Euro Zone"]
        for ev in events:
            if ev.get("country") not in relevant_countries:
                continue
            if ev.get("impact") != "high":
                continue
            event_time_str = ev.get("eventTime") or ev.get("date")
            if not event_time_str:
                continue
            try:
                event_dt = datetime.strptime(event_time_str, "%Y-%m-%d %H:%M:%S")
                event_dt = event_dt.replace(tzinfo=timezone.utc)
            except ValueError:
                try:
                    event_dt = datetime.strptime(event_time_str, "%Y-%m-%d %H:%M:%S.%f")
                    event_dt = event_dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            # Solo eventos futuros
            if event_dt <= now:
                continue
            start = event_dt - timedelta(minutes=MINUTES_BEFORE)
            end = event_dt + timedelta(minutes=MINUTES_AFTER)
            intervals.append((start, end))

        # Fusionar intervalos cercanos o solapados
        merged = self._merge_intervals(intervals)
        return merged

    def is_safe_to_trade(self):
        now = datetime.now(timezone.utc)

        # Usar caché si todavía es válida
        if self._cached_blocked_intervals and (time.time() - self._cache_timestamp) < self.cache_seconds:
            # Verificar si estamos dentro de algún intervalo bloqueado
            for start, end in self._cached_blocked_intervals:
                if start <= now < end:
                    return False
            return True

        # Actualizar caché
        self._cached_blocked_intervals = self._get_all_blocked_intervals()
        self._cache_timestamp = time.time()

        # Verificar con los intervalos nuevos
        for start, end in self._cached_blocked_intervals:
            if start <= now < end:
                remaining = end - now
                logger.info(f"Bloqueo activo. Resta {remaining}. Intervalos: {self._cached_blocked_intervals}")
                return False
        return True
