import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Dict
import smtplib
from email.message import EmailMessage
from loguru import logger

from app.core.config import get_settings


class DailyReportService:
    """Genera e invia il report giornaliero delle schedulazioni.
    - Legge `scheduler_history.json` da `export_dir`
    - Filtra per la data richiesta
    - Costruisce un corpo email HTML con riepilogo e dettagli
    - Invia via SMTP ai destinatari configurati (pipe-separated)
    """

    def __init__(self):
        self.settings = get_settings()
        self.history_path = Path(self.settings.export_dir) / "scheduler_history.json"

    def _load_history(self) -> List[Dict]:
        try:
            if self.history_path.exists():
                with open(self.history_path, "r", encoding="utf-8") as f:
                    return json.load(f) or []
        except Exception as e:
            logger.error(f"[DAILY_REPORT] Errore lettura history: {e}")
        return []

    def _filter_by_date(self, all_history: List[Dict], day: date) -> List[Dict]:
        out = []
        for h in all_history:
            try:
                ts_raw = h.get("timestamp")
                ts = None
                if ts_raw:
                    try:
                        ts = datetime.fromisoformat(ts_raw)
                    except Exception:
                        ts = None
                if ts is None:
                    # Fallback: prova da campo start_date se presente
                    sd = h.get("start_date")
                    if sd:
                        try:
                            ts = datetime.fromisoformat(sd)
                        except Exception:
                            try:
                                ts = datetime.strptime(sd, "%Y-%m-%d %H:%M:%S")
                            except Exception:
                                ts = None
                if ts and ts.date() == day:
                    out.append(h)
            except Exception:
                continue
        return out

    def _filter_by_last_hours(self, all_history: List[Dict], end_dt: datetime, hours: int = 24) -> List[Dict]:
        start_dt = end_dt - timedelta(hours=hours)
        out: List[Dict] = []
        for h in all_history:
            ts = None
            try:
                ts_raw = h.get("timestamp")
                if ts_raw:
                    try:
                        ts = datetime.fromisoformat(ts_raw)
                    except Exception:
                        ts = None
                if ts is None:
                    sd = h.get("start_date")
                    if sd:
                        try:
                            ts = datetime.fromisoformat(sd)
                        except Exception:
                            try:
                                ts = datetime.strptime(sd, "%Y-%m-%d %H:%M:%S")
                            except Exception:
                                ts = None
                if ts and (start_dt <= ts <= end_dt):
                    out.append(h)
            except Exception:
                continue
        return out

    def _build_html(self, day: date, items: List[Dict]) -> str:
        total = len(items)
        success = sum(1 for h in items if h.get("status") == "success")
        fail = sum(1 for h in items if h.get("status") in ("fail", "retry_scheduled"))
        avg = 0.0
        durations = [h.get("duration_sec") for h in items if h.get("duration_sec") is not None]
        if durations:
            avg = sum(durations) / len(durations)
        rows_total = sum(int(h.get("row_count", 0) or 0) for h in items)

        def esc(s: Optional[str]) -> str:
            if not s:
                return ""
            return str(s).replace("<", "&lt;").replace(">", "&gt;")

        html_rows = []
        for h in items:
            # Partenza: preferisci timestamp ISO completo; fallback al token start_date
            partenza = ''
            try:
                ts_raw = h.get('timestamp')
                if ts_raw:
                    ts_dt = datetime.fromisoformat(ts_raw)
                    partenza = ts_dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                partenza = ''
            if not partenza:
                partenza = h.get('start_date') or ''

            html_rows.append(
                f"""
                <tr>
                    <td>{esc(h.get('query'))}</td>
                    <td>{esc(h.get('connection'))}</td>
                    <td>{esc(partenza)}</td>
                    <td>{esc(h.get('status'))}</td>
                    <td style='text-align:right'>{(h.get('duration_sec') or 0):.2f}</td>
                    <td style='text-align:right'>{int(h.get('row_count') or 0)}</td>
                    <td style='width:40%'><pre style='white-space:pre-wrap;margin:0'>{esc(h.get('error') or '')}</pre></td>
                </tr>
                """
            )

        # HTML email ben formato (head + style una sola volta; nessun testo spurio)
        html = f"""
        <html>
        <head>
            <meta charset='utf-8'>
            <style>
                body {{ font-family: system-ui, Arial, sans-serif; }}
                table {{ width: 100%; border-collapse: collapse; table-layout: auto; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
                th {{ background: #f3f4f6; text-align: left; }}
            </style>
        </head>
        <body>
            <h3>Report schedulazioni - {day.isoformat()}</h3>
            <p>
                Totale: <b>{total}</b> &nbsp;|
                Successi: <b style='color:#059669'>{success}</b> &nbsp;|
                Fallimenti: <b style='color:#dc2626'>{fail}</b> &nbsp;|
                Tempo medio (s): <b>{avg:.2f}</b> &nbsp;|
                Righe totali: <b>{rows_total}</b>
            </p>
            <table>
                <thead>
                    <tr>
                        <th>Query</th>
                        <th>Connessione</th>
                        <th>Partenza</th>
                        <th>Stato</th>
                        <th>Durata (s)</th>
                        <th>Rows</th>
                        <th style='width:40%'>Errore</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(html_rows) if html_rows else '<tr><td colspan=7>Nessuna esecuzione</td></tr>'}
                </tbody>
            </table>
        </body>
        </html>
        """
        return html

    def generate(self, day: Optional[date] = None) -> Dict[str, str]:
        # Se viene fornita una data esplicita, mantiene il comportamento "giornaliero".
        # Se day è None, estrae le esecuzioni delle ultime 24 ore rispetto all'istante corrente.
        hist = self._load_history()
        if day is not None:
            d = day
            items = self._filter_by_date(hist, d)
            body_html = self._build_html(d, items)
            return {
                "date": d.isoformat(),
                "items_count": str(len(items)),
                "body_html": body_html
            }
        else:
            now = datetime.now()
            items = self._filter_by_last_hours(hist, now, hours=24)
            # Manteniamo il titolo con la data odierna per compatibilità visuale
            d = now.date()
            body_html = self._build_html(d, items)
            return {
                "date": d.isoformat(),
                "items_count": str(len(items)),
                "body_html": body_html
            }

    def send_email(self, to_pipe: Optional[str], cc_pipe: Optional[str], subject: str, body_html: str) -> None:
        settings = get_settings()
        smtp_host = getattr(settings, 'smtp_host', None)
        smtp_port = getattr(settings, 'smtp_port', 25)
        smtp_user = getattr(settings, 'smtp_user', None)
        smtp_password = getattr(settings, 'smtp_password', None)
        smtp_from = getattr(settings, 'smtp_from', None)

        if not smtp_host or not smtp_from:
            logger.warning("[DAILY_REPORT] SMTP non configurato (smtp_host/smtp_from mancanti)")
            return
        if not to_pipe:
            logger.warning("[DAILY_REPORT] Nessun destinatario configurato")
            return

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = smtp_from
        tos = [r.strip() for r in to_pipe.split('|') if r.strip()]
        msg['To'] = ', '.join(tos)
        ccs: List[str] = []
        if cc_pipe:
            ccs = [c.strip() for c in cc_pipe.split('|') if c.strip()]
            if ccs:
                msg['Cc'] = ', '.join(ccs)

        msg.set_content("Questo client richiede HTML.")
        msg.add_alternative(body_html, subtype='html')

        with smtplib.SMTP(smtp_host, smtp_port) as s:
            s.ehlo()
            try:
                s.starttls()
            except Exception:
                pass
            if smtp_user and smtp_password:
                s.login(smtp_user, smtp_password)
            all_rcpts = tos + ccs
            try:
                s.send_message(msg, to_addrs=all_rcpts)
            except Exception:
                s.sendmail(smtp_from, all_rcpts, msg.as_string())
        logger.info(f"[DAILY_REPORT] Email inviata - To: {tos} | Cc: {ccs}")

    def generate_and_send(self, day: Optional[date] = None) -> None:
        # Se day è None, usa la finestra delle ultime 24 ore
        payload = self.generate(day)
        # Subject con token semplici data
        subj = getattr(self.settings, 'daily_report_subject', 'Report schedulazioni PSTT')
        self.send_email(
            getattr(self.settings, 'daily_report_recipients', None),
            getattr(self.settings, 'daily_report_cc', None),
            subj,
            payload['body_html']
        )
