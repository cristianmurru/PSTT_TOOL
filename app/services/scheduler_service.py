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
from app.core.config import get_settings
import smtplib
from email.message import EmailMessage
import traceback


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
            with open(history_path, "r", encoding="utf-8") as f:
                all_history = json.load(f)
            cutoff = datetime.now() - timedelta(days=30)
            self.execution_history = [h for h in all_history if datetime.fromisoformat(h["timestamp"]) >= cutoff]
        else:
            self.execution_history = []

    def save_history(self):
        history_path = self.export_dir / "scheduler_history.json"
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(self.execution_history, f, indent=2)

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
            # Schedule cleanup job at 7:00 AM
            self.scheduler.add_job(
                lambda: asyncio.create_task(self.cleanup_old_exports()),
                CronTrigger(hour=7, minute=0),
                name="Cleanup old exports"
            )
            logger.info("✅ SchedulerService avviato con job da configurazione")
        except Exception as e:
            logger.error(f"Errore nell'avvio del scheduler: {e}")
            raise
    
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

            logger.info(f"[SCHEDULER] Avvio export automatico per {query_filename} su {connection_name}")
            start_time = datetime.now()
            request = {
                "query_filename": query_filename,
                "connection_name": connection_name,
                "parameters": {},
                "limit": 10000
            }
            req_obj = QueryExecutionRequest(**request)
            result = self.query_service.execute_query(req_obj)
            duration = (datetime.now() - start_time).total_seconds()
            status = "success" if result and getattr(result, 'success', True) else "fail"
            # registra esecuzione parziale
            self.execution_history.append({
                "query": query_filename,
                "connection": connection_name,
                "timestamp": start_time.isoformat(),
                "status": status,
                "duration_sec": duration if status == 'success' else None,
                "row_count": getattr(result, "row_count", 0) if result else 0,
                "error": getattr(result, "error_message", None) if result else None
            })
            self.save_history()

            if end_date:
                try:
                    if date.today() > date.fromisoformat(end_date):
                        logger.info(f"[SCHEDULER] Job {query_filename} non eseguito: oltre la data di fine {end_date}")
                        return
                except Exception:
                    logger.warning(f"Formato end_date non valido: {end_date}")

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
            df.to_excel(filepath, index=False)
            logger.info(f"[SCHEDULER] Export completato: {filepath}")

            if sharing == 'email':
                # prova a inviare via email, se non configurato logga e mantiene il file
                try:
                    self._send_email_with_attachment(sched.get('email_recipients'), filepath)
                except Exception:
                    logger.exception("Invio email fallito, file salvato su filesystem")

        except Exception as e:
            logger.error(f"[SCHEDULER] Errore durante export {args}: {e}\n{traceback.format_exc()}")
            self.execution_history.append({
                "query": args[0] if args else 'unknown',
                "connection": args[1] if len(args) > 1 else 'unknown',
                "timestamp": datetime.now().isoformat(),
                "status": "fail",
                "duration_sec": None,
                "row_count": 0,
                "error": str(e)
            })
            self.save_history()

    def _send_email_with_attachment(self, recipients: Optional[str], filepath: Path):
        """Invia il file come attachment se le impostazioni SMTP sono configurate;
        i destinatari possono essere separati da pipe '|'. Se SMTP non presente, logga e ritorna.
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
        msg['Subject'] = f"Export scheduler: {filepath.name}"
        msg['From'] = smtp_from
        # destinatari separati da pipe
        tos = [r.strip() for r in recipients.split('|') if r.strip()]
        msg['To'] = ', '.join(tos)
        msg.set_content(f"In allegato il file generato dal scheduler: {filepath.name}")

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
            s.send_message(msg)
            logger.info(f"Email inviata a: {tos}")
    
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
