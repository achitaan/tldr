import os
import threading
import time
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections, OperationalError
from django.utils import timezone
from study.models import Job, RuntimeState
from study.jobs import claim, run_job

def heartbeat():
    """Contention must not terminate the process that owns active jobs."""
    try:
        RuntimeState.objects.update_or_create(key='worker', defaults={'value': {'heartbeat': timezone.now().isoformat(), 'pid': os.getpid()}})
        return True
    except OperationalError:
        close_old_connections()
        return False

class Command(BaseCommand):
    help = 'Run one generation/ingestion worker and one render worker; jobs persist in SQLite.'
    def add_arguments(self, parser):
        parser.add_argument('--once',action='store_true',help='Drain currently queued jobs and exit (for local verification).')
    def handle(self,*args,**options):
        handle = open(settings.DATA_ROOT/'worker.lock','a+b')
        handle.seek(0)
        if handle.read(1)==b'':
            handle.write(b'0'); handle.flush()
        handle.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except (OSError,IOError):
            handle.close()
            raise CommandError('A study worker already owns this data directory.')
        Job.objects.filter(status='running').update(status='queued',progress=0,error='Recovered after worker restart.')
        Job.objects.filter(worker_active=True).update(worker_active=False)
        stop = threading.Event()
        def work(lane):
            while not stop.is_set():
                close_old_connections()
                try:
                    job=claim(lane)
                    if job:
                        run_job(job)
                    elif options['once']:
                        return
                    else:
                        stop.wait(0.8)
                except OperationalError:
                    stop.wait(0.3)
                finally:
                    close_old_connections()
        self.stdout.write('TLDR local workers started (one generation, one renderer).')
        threads=[threading.Thread(target=work,args=(lane,),daemon=True) for lane in ('generation','render')]
        try:
            for thread in threads: thread.start()
            while any(t.is_alive() for t in threads):
                heartbeat()
                for thread in threads: thread.join(timeout=0.5)
            # --once generation may enqueue rendering after render lane initially drained.
            if options['once']:
                while (job:=claim('render')) is not None: run_job(job)
        except KeyboardInterrupt:
            stop.set()
            self.stdout.write('Worker stopping; active jobs recover on next startup.')
        finally:
            handle.close()
