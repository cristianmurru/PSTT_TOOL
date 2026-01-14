"""
Servizio per il sistema di scheduling (stub per ora)
"""
import asyncio
from datetime import datetime
from typing import Optional
from loguru import logger
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.query_service import QueryService
from app.core.config import get_settings
from pathlib import Path
from app.models.queries import QueryExecutionRequest
import json
from app.models.scheduling import SchedulingItem, SchedulingHistoryItem
from datetime import datetime, timedelta, date
def _today():
    return date.today()
from app.core.config import get_settings
import smtplib
from email.message import EmailMessage
import traceback
from app.services.daily_report_service import DailyReportService


def _to_int(val, default: int) -> int:
    try:
        if val is None:
            return default
        return int(val)
    except Exception:
        try:
            return int(float(val))
        except Exception:
            return default


def _daily_report_job():
    """Funzione modulare sicura per il reloader: genera e invia il report giornaliero."""
    try:
        svc = DailyReportService()
        svc.generate_and_send(date.today())
        logger.info("[DAILY_REPORT] Report giornaliero inviato")
    except Exception as e:
        logger.error(f"[DAILY_REPORT] Errore invio report giornaliero: {e}")


class SchedulerService:
    """Servizio per la gestione dello scheduling"""
    
    def __init__(self):
        self.is_running = False
        self.scheduler = None
        self.jobs = []
        self.query_service = QueryService()
        self.settings = get_settings()
        self.export_dir = Path(self.settings.export_dir)
        self.queries_to_schedule = [sched["query"] for sched in getattr(self.settings, 'scheduling', [])]
        self.execution_history = []  # Tracciamento esecuzioni
        logger.info("SchedulerService inizializzato")
    
    def load_history(self):
        history_path = self.export_dir / "scheduler_history.json"
        if history_path.exists():
            try:
                # Gestisci file vuoto o corrotto con backup automatico
                text = history_path.read_text(encoding="utf-8")
                if not text.strip():
                    self.execution_history = []
                    return
                all_history = json.loads(text)
                # Mantieni tutto lo storico in memoria; il filtro dei 30 giorni verrà applicato in API/UI
                # per evitare perdite di eventi al riavvio.
                try:
                    self.execution_history = list(all_history)
                except Exception:
                    self.execution_history = []
            except Exception as e:
                # Backup del file corrotto e riparti da history vuota
                try:
                    import shutil
                    ts = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                    backup = self.export_dir / f"scheduler_history_corrupt_{ts}.json"
                    shutil.copy(str(history_path), str(backup))
                    logger.warning(f"[SCHEDULER] scheduler_history.json corrotto: backup in {backup} ({e})")
                except Exception:
                    logger.warning(f"[SCHEDULER] scheduler_history.json corrotto e non backupabile: {e}")
                self.execution_history = []
        else:
            self.execution_history = []

    def save_history(self):
        history_path = self.export_dir / "scheduler_history.json"
        try:
            tmp_dir = self.export_dir / "_tmp"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tmp_file = tmp_dir / "scheduler_history.json.tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self.execution_history, f, indent=2)
            # Move atomico
            import shutil
            shutil.move(str(tmp_file), str(history_path))
        except Exception as e:
            logger.warning(f"[SCHEDULER] Impossibile salvare history: {e}")

    async def start(self):
        """Avvia il servizio scheduler"""
        try:
            self.is_running = True
            self.load_history()
            from apscheduler.executors.asyncio import AsyncIOExecutor
            executors = {
                'default': AsyncIOExecutor()
            }
            self.scheduler = AsyncIOScheduler(executors=executors)
            self.scheduler.start()
            # Schedulazione dinamica da config
            scheduling = getattr(self.settings, 'scheduling', [])
            for sched in scheduling:
                try:
                    mode = sched.get('scheduling_mode', 'classic')
                    end_date = sched.get('end_date')
                    if mode == 'cron' and sched.get('cron_expression'):
                        try:
                            trigger = CronTrigger.from_crontab(sched['cron_expression'])
                        except Exception:
                            # fallback: try to parse as CronTrigger kwargs
                            logger.warning(f"Impossibile parse cron_expression: {sched.get('cron_expression')}, skipping job")
                            continue
                    else:
                        trigger_args = {}
                        if sched.get('hour') is not None:
                            trigger_args['hour'] = sched.get('hour')
                        if sched.get('minute') is not None:
                            trigger_args['minute'] = sched.get('minute')
                        if sched.get('second') is not None:
                            trigger_args['second'] = sched.get('second')
                        days = sched.get('days_of_week')
                        if days:
                            trigger_args['day_of_week'] = ','.join(str(d) for d in days)
                        if not trigger_args:
                            logger.warning(f"Schedulazione priva di orario per job {sched.get('query')}, skipping")
                            continue
                        trigger = CronTrigger(**trigger_args)

                    # Passa l'intera dict di schedulazione al job per avere accesso ai nuovi campi
                    self.scheduler.add_job(
                        self.run_scheduled_query,
                        trigger,
                        args=[sched],
                        name=f"Export {sched.get('query')} on {sched.get('connection')}",
                        misfire_grace_time=600,  # 10 minuti di tolleranza
                        coalesce=True
                    )
                except Exception as e:
                    logger.error(f"Errore nella creazione job per sched {sched}: {e}")
            # Cleanup job (direct coroutine, avoids create_task outside loop)
            self.scheduler.add_job(
                self.cleanup_old_exports,
                CronTrigger(hour=7, minute=0),
                name="Cleanup old exports",
                misfire_grace_time=900,
            )
            # Daily report job (configurabile via env)
            try:
                if getattr(self.settings, 'daily_report_enabled', False):
                    cron = getattr(self.settings, 'daily_report_cron', None)
                    if cron:
                        try:
                            dr_trigger = CronTrigger.from_crontab(cron)
                        except Exception:
                            logger.warning(f"[DAILY_REPORT] Cron non valido '{cron}', fallback su daily_reports_hour")
                            dr_trigger = CronTrigger(hour=getattr(self.settings, 'daily_reports_hour', 6), minute=0)
                    else:
                        dr_trigger = CronTrigger(hour=getattr(self.settings, 'daily_reports_hour', 6), minute=0)

                    self.scheduler.add_job(
                        _daily_report_job,
                        dr_trigger,
                        name="Daily report schedulazioni",
                        misfire_grace_time=900,
                        coalesce=True
                    )
                    logger.info("[DAILY_REPORT] Job giornaliero configurato")
            except Exception:
                logger.exception("[DAILY_REPORT] Errore configurazione job giornaliero")
            logger.info("✅ SchedulerService avviato con job da configurazione")
        except Exception as e:
            logger.error(f"Errore nell'avvio del scheduler: {e}")
            raise

        # Metodo non più utilizzato; mantenuto per retrocompatibilità (non referenziato)
        async def _run_daily_report(self):
            _daily_report_job()
    
    async def stop(self):
        """Ferma il servizio scheduler"""
        try:
            self.is_running = False
            if self.scheduler:
                self.scheduler.shutdown()
            logger.info("🛑 SchedulerService fermato")
        except Exception as e:
            logger.error(f"Errore nell'arresto del scheduler: {e}")
    
    async def run_scheduled_query(self, *args):
        """Esegue la query schedulata. Accetta due forme di chiamata:
        - run_scheduled_query(sched_dict)
        - run_scheduled_query(query_filename, connection_name, end_date)
        """
        try:
            # Normalizza input
            if len(args) == 1 and isinstance(args[0], dict):
                sched = args[0]
            elif len(args) >= 2:
                sched = {
                    'query': args[0],
                    'connection': args[1],
                    'end_date': args[2] if len(args) > 2 else None
                }
                # try to enrich with config scheduling entry
                for s in getattr(self.settings, 'scheduling', []):
                    if s.get('query') == sched['query'] and s.get('connection') == sched['connection']:
                        sched = {**s, **sched}
                        break
            else:
                logger.error("Argomenti invalidi passati a run_scheduled_query")
                return

            query_filename = sched.get('query')
            connection_name = sched.get('connection')
            end_date = sched.get('end_date')

            export_id = f"{query_filename}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            logger.info(f"[SCHEDULER][{export_id}] START export per {query_filename} su {connection_name}")
            # Controllo data di fine: accetta stringhe ISO (YYYY-MM-DD), stringhe DD/MM/YYYY,
            # oggetti datetime/date. Se non è possibile parsare, logga il warning ma non blocca l'esecuzione.
            def _parse_end_date(ed):
                if ed is None:
                    return None
                # se è già un datetime o date
                # controlla datetime prima di date perché datetime è sottoclasse di date
                if isinstance(ed, datetime):
                    return ed.date()
                if isinstance(ed, date):
                    return ed
                if isinstance(ed, str):
                    s = ed.strip()
                    # prova ISO YYYY-MM-DD
                    try:
                        return date.fromisoformat(s)
                    except Exception:
                        pass
                    # prova DD/MM/YYYY
                    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
                        try:
                            return datetime.strptime(s, fmt).date()
                        except Exception:
                            continue
                return None

            if end_date:
                parsed_end = _parse_end_date(end_date)
                if parsed_end is None:
                    logger.warning(f"Formato end_date non valido: {end_date}")
                else:
                    if _today() > parsed_end:
                        logger.info(f"[SCHEDULER] Job {query_filename} non eseguito: oltre la data di fine {end_date}")
                        return

            # Esegui la query solo se non sopra la end_date
            start_time = datetime.now()
            # Do not force a hardcoded limit here; allow QueryExecutionRequest default (None = no limit)
            request = {
                "query_filename": query_filename,
                "connection_name": connection_name,
                "parameters": {}
            }
            req_obj = QueryExecutionRequest(**request)

            # Timeout configurabile (default 300s) per la fase query
            query_timeout = _to_int(getattr(self.settings, 'scheduler_query_timeout_sec', 300), 300)
            try:
                query_timeout = float(query_timeout)
            except Exception:
                query_timeout = 300.0
            if query_timeout <= 0:
                query_timeout = 300.0
            logger.info(f"[SCHEDULER][{export_id}] START_QUERY timeout={query_timeout}s")
            loop = asyncio.get_event_loop()
            try:
                result = await asyncio.wait_for(loop.run_in_executor(None, self.query_service.execute_query, req_obj), timeout=query_timeout)
            except asyncio.TimeoutError:
                logger.error(f"[SCHEDULER][{export_id}] TIMEOUT_QUERY superati {query_timeout}s")
                result = None
            duration_query = (datetime.now() - start_time).total_seconds()
            logger.info(f"[SCHEDULER][{export_id}] END_QUERY duration={duration_query:.2f}s rows={getattr(result,'row_count',0)}")
            duration = (datetime.now() - start_time).total_seconds()
            status = "success" if result and getattr(result, 'success', True) else "fail"
            # registra esecuzione parziale (inclusa data di partenza calcolata dai token)
            try:
                sched_item_for_date = SchedulingItem(**sched)
                start_date_token = sched_item_for_date.render_string("{date}", start_time)
            except Exception:
                start_date_token = None
            self.execution_history.append({
                "query": query_filename,
                "connection": connection_name,
                "timestamp": start_time.isoformat(),
                "status": status,
                "duration_sec": duration if status == 'success' else None,
                "row_count": getattr(result, "row_count", 0) if result else 0,
                "error": getattr(result, "error_message", None) if result else None,
                "start_date": start_date_token
            })
            self.save_history()

            if not result or not getattr(result, 'success', True):
                logger.error(f"[SCHEDULER] Errore export {query_filename}: {getattr(result, 'error_message', 'unknown')}")
                return

            # Costruisci filename dal template usando SchedulingItem
            try:
                sched_item = SchedulingItem(**sched)
                filename = sched_item.render_filename(start_time)
            except Exception:
                logger.exception("Impossibile creare SchedulingItem o generare filename, uso fallback")
                filename = f"{query_filename.replace('.sql','')}_{datetime.now().strftime('%Y-%m-%d')}.xlsx"

            # Gestione condivisione
            sharing = sched.get('sharing_mode', 'filesystem')
            output_dir = sched.get('output_dir') or str(self.export_dir)
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            filepath = Path(output_dir) / filename

            # Rimuovi file esistente
            if filepath.exists():
                try:
                    filepath.unlink()
                    logger.info(f"[SCHEDULER] File esistente eliminato: {filepath}")
                except Exception as e:
                    logger.error(f"[SCHEDULER] Impossibile eliminare file esistente: {filepath} - {e}")
                    return

            import pandas as pd
            df = pd.DataFrame(result.data)
            # Strategia temp locale: crea file temporaneo e poi move atomico
            tmp_dir = Path(output_dir) / "_tmp"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            tmp_file = tmp_dir / f"{filename}.tmp.xlsx"
            write_start = datetime.now()
            logger.info(f"[SCHEDULER][{export_id}] START_WRITE temp={tmp_file}")
            write_timeout = _to_int(getattr(self.settings, 'scheduler_write_timeout_sec', 120), 120)
            try:
                write_timeout = float(write_timeout)
            except Exception:
                write_timeout = 120.0
            if write_timeout <= 0:
                write_timeout = 120.0
            try:
                # Usa keyword index=False per chiarezza
                await asyncio.wait_for(loop.run_in_executor(None, lambda: df.to_excel(tmp_file, index=False)), timeout=write_timeout)
            except asyncio.TimeoutError:
                logger.error(f"[SCHEDULER][{export_id}] TIMEOUT_WRITE superati {write_timeout}s")
                return
            write_duration = (datetime.now() - write_start).total_seconds()
            logger.info(f"[SCHEDULER][{export_id}] END_WRITE duration={write_duration:.2f}s size={tmp_file.stat().st_size}B")

            # Move con retry
            move_attempts = 3
            for attempt in range(1, move_attempts + 1):
                try:
                    import shutil
                    shutil.move(str(tmp_file), str(filepath))
                    logger.info(f"[SCHEDULER][{export_id}] MOVE_OK {tmp_file} -> {filepath} attempt={attempt}")
                    break
                except Exception as move_err:
                    logger.warning(f"[SCHEDULER][{export_id}] MOVE_FAIL attempt={attempt} error={move_err}")
                    await asyncio.sleep(2 * attempt)
            else:
                logger.error(f"[SCHEDULER][{export_id}] MOVE_ABORT dopo {move_attempts} tentativi; file rimane in {tmp_file}")
                return

            total_duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"[SCHEDULER][{export_id}] EXPORT_COMPLETED total_duration={total_duration:.2f}s final={filepath}")
            self._append_metrics(export_id, query_filename, connection_name, duration_query, write_duration, total_duration, getattr(result,'row_count',0))

            if sharing == 'email':
                # prova a inviare via email, se non configurato logga e mantiene il file
                try:
                    to_field = sched.get('email_to') or sched.get('email_recipients')
                    cc_field = sched.get('email_cc')
                    subject_raw = sched.get('email_subject') or f"Export scheduler: {filepath.name}"
                    # default body standard richiesto
                    default_body = (
                        "Buongiorno,\n"
                        "in allegato estrazione relativa l'oggetto, generata da procedura automatica.\n"
                        "Saluti,\n"
                        "Report_PSTT\n"
                    )
                    body_raw = sched.get('email_body') or default_body
                    
                    # Sostituisci token in subject e body usando il metodo del modello (import già a livello modulo)
                    sched_item = SchedulingItem(**sched)
                    subject = sched_item.render_string(subject_raw)
                    body = sched_item.render_string(body_raw)
                    
                    self._send_email_with_attachment(to_field, filepath, cc_field, subject, body)
                except Exception:
                    logger.exception("Invio email fallito, file salvato su filesystem")

        except Exception as e:
            logger.error(f"[SCHEDULER] Errore durante export {args}: {e}\n{traceback.format_exc()}")
            # Usa i nomi già risolti se disponibili
            qn = locals().get('query_filename', 'unknown')
            cn = locals().get('connection_name', 'unknown')
            self.execution_history.append({
                "query": qn,
                "connection": cn,
                "timestamp": datetime.now().isoformat(),
                "status": "fail",
                "duration_sec": None,
                "row_count": 0,
                "error": str(e),
                "start_date": None
            })
            self.save_history()

    def _append_metrics(self, export_id: str, query: str, connection: str, duration_query: float, duration_write: float, duration_total: float, rows: int):
        try:
            metrics_path = self.export_dir / "scheduler_metrics.json"
            if metrics_path.exists():
                with open(metrics_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = []
            data.append({
                "export_id": export_id,
                "query": query,
                "connection": connection,
                "timestamp": datetime.utcnow().isoformat(),
                "duration_query_sec": duration_query,
                "duration_write_sec": duration_write,
                "duration_total_sec": duration_total,
                "rows": rows
            })
            with open(metrics_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"[SCHEDULER] Impossibile salvare metriche: {e}")

    def _send_email_with_attachment(self, recipients: Optional[str], filepath: Path, cc: Optional[str] = None, subject: Optional[str] = None, body: Optional[str] = None):
        """Invia il file come attachment se le impostazioni SMTP sono configurate.
        - `recipients`: lista To separata da pipe '|'
        - `cc`: lista CC separata da pipe '|'
        - `subject`: oggetto email
        - `body`: corpo email plain text
        """
        settings = get_settings()
        smtp_host = getattr(settings, 'smtp_host', None)
        smtp_port = getattr(settings, 'smtp_port', 25)
        smtp_user = getattr(settings, 'smtp_user', None)
        smtp_password = getattr(settings, 'smtp_password', None)
        smtp_from = getattr(settings, 'smtp_from', None)

        if not smtp_host or not smtp_from:
            logger.warning("SMTP non configurato: impossibile inviare email. Specificare smtp_host e smtp_from in settings")
            return

        if not recipients:
            logger.warning("Nessun destinatario email specificato")
            return

        # prepara messaggio
        msg = EmailMessage()
        msg['Subject'] = subject or f"Export scheduler: {filepath.name}"
        msg['From'] = smtp_from
        # destinatari separati da pipe
        tos = [r.strip() for r in recipients.split('|') if r.strip()]
        msg['To'] = ', '.join(tos)
        # CC
        ccs = []
        if cc:
            ccs = [c.strip() for c in cc.split('|') if c.strip()]
            if ccs:
                msg['Cc'] = ', '.join(ccs)
        # body
        msg.set_content(body or f"In allegato il file generato dal scheduler: {filepath.name}")

        with open(filepath, 'rb') as f:
            data = f.read()
        msg.add_attachment(data, maintype='application', subtype='octet-stream', filename=filepath.name)

        # invia
        with smtplib.SMTP(smtp_host, smtp_port) as s:
            s.ehlo()
            try:
                s.starttls()
            except Exception:
                pass
            if smtp_user and smtp_password:
                s.login(smtp_user, smtp_password)
            # Includi esplicitamente To+Cc nella envelope list per garantire consegna CC
            all_rcpts = tos + ccs
            try:
                s.send_message(msg, to_addrs=all_rcpts)
            except Exception:
                # fallback conservativo
                s.sendmail(smtp_from, all_rcpts, msg.as_string())
            logger.info(f"Email inviata - To: {tos} | Cc: {ccs}")
    
    async def cleanup_old_exports(self):
        try:
            logger.info("[SCHEDULER] Avvio pulizia file export > 30 giorni")
            now = datetime.now()
            for file in self.export_dir.glob("*.gz"):
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                if (now - mtime).days > 30:
                    file.unlink()
                    logger.info(f"[SCHEDULER] File eliminato: {file}")
            logger.info("[SCHEDULER] Pulizia completata")
        except Exception as e:
            logger.error(f"[SCHEDULER] Errore pulizia file: {e}")
    
    def get_status(self) -> dict:
        """Ottiene lo stato del scheduler"""
        history = self.execution_history[-20:]  # Ultime 20 esecuzioni
        success_count = sum(1 for h in self.execution_history if h["status"] == "success")
        fail_count = sum(1 for h in self.execution_history if h["status"] == "fail")
        avg_time = (sum(h["duration_sec"] for h in self.execution_history if h["duration_sec"] is not None) / max(1, len(self.execution_history)))
        # Filtra solo i job utente (escludi job tecnici come la pulizia)
        if self.scheduler:
            try:
                all_jobs = self.scheduler.get_jobs()
                user_jobs = [job for job in all_jobs if not job.name.lower().startswith("cleanup")]
            except Exception:
                user_jobs = []
        else:
            user_jobs = []

        return {
            "running": self.is_running,
            "active_jobs": len(user_jobs),
            "scheduled_jobs": len(user_jobs),
            "last_execution": history[-1] if history else None,
            "history": history,
            "success_count": success_count,
            "fail_count": fail_count,
            "avg_duration_sec": avg_time
        }
    
    def remove_scheduling(self, query_filename, connection_name):
        """Rimuove una schedulazione attiva e il relativo job dal scheduler."""
        # Trova il job corrispondente
        job_id = f"Export {query_filename} on {connection_name}"
        if self.scheduler:
            try:
                self.scheduler.remove_job(job_id)
                logger.info(f"Job rimosso: {job_id}")
            except Exception as e:
                logger.error(f"Impossibile rimuovere job {job_id}: {e}")
        # Rimuovi la schedulazione dalla fonte dati (es. file, config, db)
        # Esempio: se usi una lista in memoria
        self.queries_to_schedule = [q for q in self.queries_to_schedule if q != query_filename]
        # Aggiorna la dashboard/contatori
        # Se hai una funzione per aggiornare la UI, chiamala qui
        # Esempio: self.update_dashboard()
        logger.info("Schedulazione e job rimossi, dashboard aggiornata.")
