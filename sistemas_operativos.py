from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class IOEvent:
    """Representa un evento de E/S: cuando (en unidades de CPU consumidas desde inicio)
    ocurre la petición de E/S y cuánto dura la E/S."""
    at: int          # unidad de CPU desde inicio del proceso en la que pide E/S
    duration: int    # duración de la E/S en unidades de tiempo


@dataclass
class Process:
    pid: str
    arrival: int           # tiempo de llegada al sistema
    burst: int             # tiempo total de CPU requerido (ráfaga total)
    io_events: List[IOEvent] = field(default_factory=list)  # lista de eventos de E/S ordenada por 'at'
    # Campos de simulación (mutarán durante la ejecución)
    remaining: int = field(init=False)
    executed: int = field(init=False, default=0)  # CPU consumida hasta ahora
    start_time: Optional[int] = field(init=False, default=None)  # primer vez que recibió CPU
    finish_time: Optional[int] = field(init=False, default=None)
    waiting_time: int = field(init=False, default=0)  # total acumulado en ready
    last_ready_enter: Optional[int] = field(init=False, default=None)  # para cálculo de espera incremental

    def __post_init__(self):
        self.remaining = self.burst
        # asegurar orden de io_events por 'at'
        self.io_events.sort(key=lambda e: e.at)

    def next_io(self) -> Optional[IOEvent]:
        """Devuelve el siguiente evento de E/S que aún no ocurrió (según executed)."""
        for ev in self.io_events:
            if ev.at > self.executed:
                return ev
            # if ev.at == self.executed: it means occurs immediately after executing this unit
        return None

    def consumes_to_next_io(self) -> int:
        """Cuántas unidades puede consumir hasta que ocurra la próxima petición de E/S.
        Retorna al menos 1 (si no hay IO devuelve remaining)."""
        ev = self.next_io()
        if ev is None:
            return self.remaining
        # si next io.at > executed, podemos consumir hasta that - executed (pero no más que remaining)
        return max(0, min(self.remaining, ev.at - self.executed))


@dataclass
class GanttEntry:
    pid: str
    start: int
    end: int


class SchedulerResult:
    def __init__(self, gantt: List[GanttEntry], processes: List[Process], total_time: int):
        self.gantt = gantt
        self.processes = processes
        self.total_time = total_time

    def metrics(self) -> Tuple[dict, dict, dict]:
        """Calcula métricas: turnaround, waiting, response por pid."""
        tat = {}
        wt = {}
        rt = {}
        for p in self.processes:
            TAT = (p.finish_time - p.arrival) if p.finish_time is not None else None
            WT = p.waiting_time
            RT = (p.start_time - p.arrival) if p.start_time is not None else None
            tat[p.pid] = TAT
            wt[p.pid] = WT
            rt[p.pid] = RT
        return tat, wt, rt

    def print_summary(self):
        tat, wt, rt = self.metrics()
        print("Gantt (pid: start-end):")
        for entry in self.gantt:
            print(f"  {entry.pid}: {entry.start} - {entry.end}")
        print(f"\nTiempo total de simulación: {self.total_time}")
        print("\nMétricas por proceso (Turnaround, Waiting, Response):")
        print("{:<6} {:>10} {:>10} {:>10}".format("PID", "Turnaround", "Waiting", "Response"))
        for p in sorted(self.processes, key=lambda x: x.pid):
            print("{:<6} {:>10} {:>10} {:>10}".format(
                p.pid,
                tat[p.pid],
                wt[p.pid],
                rt[p.pid]
            ))
        avg_tat = sum(v for v in tat.values()) / len(tat)
        avg_wt = sum(v for v in wt.values()) / len(wt)
        avg_rt = sum(v for v in rt.values()) / len(rt)
        print("\nPromedios: Turnaround = {:.2f}, Waiting = {:.2f}, Response = {:.2f}".format(
            avg_tat, avg_wt, avg_rt
        ))


class BaseScheduler:
    """Clase base con utilidades comunes."""
    def __init__(self, processes: List[Process]):
        # recibimos procesos iniciales; trabajamos con copias para no modificar originales
        self.init_processes = deepcopy(processes)

    def run(self) -> SchedulerResult:
        raise NotImplementedError


class FIFOScheduler(BaseScheduler):
    """FIFO / FCFS: atiende en orden de llegada. Un proceso corre hasta terminar o hasta pedir E/S."""
    def run(self) -> SchedulerResult:
        procs = deepcopy(self.init_processes)
        time = 0
        ready = deque()
        blocked: List[Tuple[Process, int]] = []  # (process, remaining_io_time)
        finished: List[Process] = []
        gantt: List[GanttEntry] = []

        # ordenar arrivals
        arrivals = sorted(procs, key=lambda p: p.arrival)
        arrival_idx = 0
        n = len(procs)

        while len(finished) < n:
            # traer procesos que llegan en 'time'
            while arrival_idx < len(arrivals) and arrivals[arrival_idx].arrival <= time:
                p = arrivals[arrival_idx]
                p.last_ready_enter = time
                ready.append(p)
                arrival_idx += 1

            # si no hay ocupación de CPU y no hay listos, avanzar tiempo hasta la siguiente llegada o hasta que un bloqueado termine
            if not ready:
                # avanzar al menor evento (next arrival o next io completion)
                next_times = []
                if arrival_idx < len(arrivals):
                    next_times.append(arrivals[arrival_idx].arrival)
                if blocked:
                    next_times.append(time + min(bt for (_, bt) in blocked))
                if not next_times:
                    break
                next_time = min(next_times)
                # reducir tiempos de E/S durante el salto
                leap = next_time - time
                # actualizar bloqueados
                new_blocked = []
                for pb, rem in blocked:
                    rem -= leap
                    if rem <= 0:
                        # E/S terminada, entrar a ready
                        pb.last_ready_enter = next_time
                        ready.append(pb)
                    else:
                        new_blocked.append((pb, rem))
                blocked = new_blocked
                time = next_time
                continue

            # tomar primer proceso listo
            p = ready.popleft()
            # contabilizar espera desde que entró al ready hasta ahora
            if p.last_ready_enter is not None:
                p.waiting_time += time - p.last_ready_enter
                p.last_ready_enter = None
            if p.start_time is None:
                p.start_time = time

            # cuánto puede consumir hasta la próxima E/S (o remaining)
            consume = p.consumes_to_next_io()
            # consumir todo ese bloque (o lo que reste)
            start = time
            end = time + consume
            # registrar en Gantt
            gantt.append(GanttEntry(p.pid, start, end))

            # avanzar el tiempo y actualizar ejecutado/remaining
            time = end
            p.executed += consume
            p.remaining -= consume

            # comprobar si ocurrió E/S justo tras esto (es decir, next_io.at == executed)
            next_io = None
            # find IO whose at == executed (it should be the next one if any and at == executed)
            for ev in p.io_events:
                if ev.at == p.executed:
                    next_io = ev
                    break

            if next_io and p.remaining > 0:
                # pasar a bloqueado por la duración indicada
                blocked.append((p, next_io.duration))
            elif p.remaining == 0:
                # terminó
                p.finish_time = time
                finished.append(p)
            else:
                # no IO y no terminado? debería indicar que remaining==0 handled above; but if not, volver a ready
                p.last_ready_enter = time
                ready.append(p)

            # durante el avance, también disminuir tiempo de E/S de bloqueados que se solapan con el salto
            # (ya fueron descontados porque avanzamos tiempo en bloque).
            # Necesitamos revisar bloqueados y mover a ready si rem <= 0 (ya hecho en 'if not ready' salto),
            # pero aquí sólo reducimos en función de 'consume' (si no hubo salto previo)
            if blocked:
                new_blocked = []
                for pb, rem in blocked:
                    rem -= 0  # ya no hay desplazamiento necesario; el main time advanced accounted for process
                    # However: if multiple processes were blocked during time advance above, we've already updated then.
                    if rem <= 0:
                        pb.last_ready_enter = time
                        ready.append(pb)
                    else:
                        new_blocked.append((pb, rem))
                blocked = new_blocked

        # any remaining blocked processes should finish IO and then be scheduled - but loop runs until finished==n
        # finalize: collect final process states (finished + possibly those finished earlier)
        all_finished = finished + [p for p in procs if p.finish_time is not None and p not in finished]
        # ensure we return all processes in the result (use original pids order)
        return SchedulerResult(gantt, procs, time)


class RRScheduler(BaseScheduler):
    """Round Robin: quantum preemptivo. Un proceso puede ser interrumpido por E/S, por quantum agotado o por finalización."""
    def __init__(self, processes: List[Process], quantum: int):
        super().__init__(processes)
        self.quantum = quantum

    def run(self) -> SchedulerResult:
        procs = deepcopy(self.init_processes)
        time = 0
        ready = deque()
        blocked: List[Tuple[Process, int]] = []  # (process, remaining io time)
        finished: List[Process] = []
        gantt: List[GanttEntry] = []

        arrivals = sorted(procs, key=lambda p: p.arrival)
        arrival_idx = 0
        n = len(procs)

        while len(finished) < n:
            # traer llegadas
            while arrival_idx < len(arrivals) and arrivals[arrival_idx].arrival <= time:
                p = arrivals[arrival_idx]
                p.last_ready_enter = time
                ready.append(p)
                arrival_idx += 1

            if not ready:
                # avanzar al siguiente evento (llegada o terminación de E/S)
                next_times = []
                if arrival_idx < len(arrivals):
                    next_times.append(arrivals[arrival_idx].arrival)
                if blocked:
                    next_times.append(time + min(bt for (_, bt) in blocked))
                if not next_times:
                    break
                next_time = min(next_times)
                leap = next_time - time
                # actualizar bloqueados durante el salto
                new_blocked = []
                for pb, rem in blocked:
                    rem -= leap
                    if rem <= 0:
                        pb.last_ready_enter = next_time
                        ready.append(pb)
                    else:
                        new_blocked.append((pb, rem))
                blocked = new_blocked
                time = next_time
                continue

            # sacar el siguiente listo (RR)
            p = ready.popleft()
            # contabilizar espera
            if p.last_ready_enter is not None:
                p.waiting_time += time - p.last_ready_enter
                p.last_ready_enter = None
            if p.start_time is None:
                p.start_time = time

            # determinar cuánto consumir: min(quantum, until next IO, remaining)
            to_io = p.consumes_to_next_io()
            run_time = min(self.quantum, to_io, p.remaining)
            start = time
            end = time + run_time
            gantt.append(GanttEntry(p.pid, start, end))

            # avanzar
            time = end
            p.executed += run_time
            p.remaining -= run_time

            # comprobar si IO ocurre ahora
            next_io = None
            for ev in p.io_events:
                if ev.at == p.executed:
                    next_io = ev
                    break

            if next_io and p.remaining > 0:
                # pasa a bloqueado
                blocked.append((p, next_io.duration))
            elif p.remaining == 0:
                p.finish_time = time
                finished.append(p)
            else:
                # fue preempted por quantum (o to_io > quantum)
                p.last_ready_enter = time
                ready.append(p)

            # reducir tiempos de E/S de bloqueados (ya avanzado por 'run_time' en el clock)
            if blocked:
                new_blocked = []
                for pb, rem in blocked:
                    rem -= 0  # rem already accounted by time variable advancement earlier when no ready
                    rem -= run_time
                    if rem <= 0:
                        pb.last_ready_enter = time
                        ready.append(pb)
                    else:
                        new_blocked.append((pb, rem))
                blocked = new_blocked

        return SchedulerResult(gantt, procs, time)


# ---------------------------
# Ejemplo de uso y prueba
# ---------------------------

def example_processes() -> List[Process]:
    return [
        Process(pid="P1", arrival=0, burst=10, io_events=[IOEvent(at=4, duration=3)]),
        Process(pid="P2", arrival=2, burst=6, io_events=[IOEvent(at=3, duration=2)]),
        Process(pid="P3", arrival=4, burst=4, io_events=[]),
        Process(pid="P4", arrival=6, burst=8, io_events=[IOEvent(at=2, duration=4)]),
    ]


def run_comparison(process_list: List[Process], quantum: int):
    print("Procesos iniciales:")
    for p in process_list:
        ios = ", ".join(f"(at={ev.at},dur={ev.duration})" for ev in p.io_events) or "sin IO"
        print(f"  {p.pid}: llegada={p.arrival}, burst={p.burst}, IOs={ios}")
    print("\n--- FIFO ---")
    fifo = FIFOScheduler(process_list)
    res_fifo = fifo.run()
    res_fifo.print_summary()

    print("\n--- RR (quantum = {}) ---".format(quantum))
    rr = RRScheduler(process_list, quantum)
    res_rr = rr.run()
    res_rr.print_summary()


if __name__ == "__main__":
    procs = example_processes()
    run_comparison(procs, quantum=3)
