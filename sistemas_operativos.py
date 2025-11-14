from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import matplotlib.pyplot as plt  # <-- IMPORTANTE: Añadido para graficar

@dataclass
class IOEvent:
    """Representa un evento de E/S: cuando (en unidades de CPU consumidas desde inicio)
    ocurre la petición de E/S y cuánto dura la E/S."""
    at: int          # unidad de CPU desde inicio del proceso en la que pide E/S
    duration: int    # duración de la E/S en unidades de tiempo


@dataclass
class Process:
    """Modela un proceso con sus tiempos y estado de simulación."""
    pid: str
    arrival: int           # tiempo de llegada al sistema
    burst: int             # tiempo total de CPU requerido (ráfaga total)
    io_events: List[IOEvent] = field(default_factory=list)  # lista de eventos de E/S ordenada por 'at'
    
    # --- Campos de simulación (mutarán durante la ejecución) ---
    remaining: int = field(init=False)  # cuánto tiempo de CPU le queda
    executed: int = field(init=False, default=0)  # CPU consumida hasta ahora
    start_time: Optional[int] = field(init=False, default=None)  # primer vez que recibió CPU (para Response Time)
    finish_time: Optional[int] = field(init=False, default=None) # cuándo terminó (para Turnaround Time)
    waiting_time: int = field(init=False, default=0)  # total acumulado en 'ready' (para Waiting Time)
    last_ready_enter: Optional[int] = field(init=False, default=None)  # para cálculo de espera incremental

    def __post_init__(self):
        """Se ejecuta después de crear la instancia."""
        self.remaining = self.burst
        # Aseguramos que los eventos de E/S estén ordenados por 'at'
        self.io_events.sort(key=lambda e: e.at)

    def next_io(self) -> Optional[IOEvent]:
        """Devuelve el siguiente evento de E/S que aún no ocurrió (según 'executed')."""
        for ev in self.io_events:
            if ev.at > self.executed:
                return ev
        return None

    def consumes_to_next_io(self) -> int:
        """Cuántas unidades puede consumir hasta que ocurra la próxima petición de E/S.
        Retorna al menos 1 (si no hay IO devuelve 'remaining')."""
        ev = self.next_io()
        if ev is None:
            # Si no hay más E/S, puede consumir todo lo que le queda
            return self.remaining
        
        # Cuánto falta para la siguiente E/S
        time_to_next_event = ev.at - self.executed
        # Puede consumir lo que le falte para la E/S, pero sin pasarse de lo que le queda en total
        return max(0, min(self.remaining, time_to_next_event))


@dataclass
class GanttEntry:
    """Una entrada simple para el diagrama de Gantt."""
    pid: str
    start: int
    end: int


class SchedulerResult:
    """Clase contenedora para los resultados de la simulación."""
    def __init__(self, gantt: List[GanttEntry], processes: List[Process], total_time: int):
        self.gantt = gantt
        self.processes = processes
        self.total_time = total_time

    def metrics(self) -> Tuple[dict, dict, dict]:
        """Calcula métricas clave: turnaround, waiting, response por pid."""
        tat = {}
        wt = {}
        rt = {}
        for p in self.processes:
            # Turnaround Time: (Finalización - Llegada)
            TAT = (p.finish_time - p.arrival) if p.finish_time is not None else None
            # Waiting Time: Ya lo fuimos acumulando en p.waiting_time
            WT = p.waiting_time
            # Response Time: (Primera Ejecución - Llegada)
            RT = (p.start_time - p.arrival) if p.start_time is not None else None
            
            tat[p.pid] = TAT
            wt[p.pid] = WT
            rt[p.pid] = RT
        return tat, wt, rt

    def print_summary(self):
        """Imprime un resumen legible de los resultados y métricas."""
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
                tat[p.pid] or "N/A",
                wt[p.pid] or "N/A",
                rt[p.pid] or "N/A"
            ))
        
        # Calcular promedios (ignorando N/A)
        valid_tats = [v for v in tat.values() if v is not None]
        valid_wts = [v for v in wt.values() if v is not None]
        valid_rts = [v for v in rt.values() if v is not None]

        avg_tat = sum(valid_tats) / len(valid_tats) if valid_tats else 0
        avg_wt = sum(valid_wts) / len(valid_wts) if valid_wts else 0
        avg_rt = sum(valid_rts) / len(valid_rts) if valid_rts else 0
        
        print("\nPromedios: Turnaround = {:.2f}, Waiting = {:.2f}, Response = {:.2f}".format(
            avg_tat, avg_wt, avg_rt
        ))

    # --- ¡NUEVA FUNCIÓN! ---
    def plot_gantt(self, title: str):
        """Usa Matplotlib para dibujar el diagrama de Gantt."""
        
        fig, ax = plt.subplots(figsize=(10, 5))
        
        # Mapear PIDs a posiciones en el eje Y
        pids = sorted(list(set(p.pid for p in self.processes)))
        y_pos = {pid: i * 10 for i, pid in enumerate(pids)}
        
        # Colores para los procesos
        colors = plt.cm.get_cmap('Set3', len(pids))
        pid_colors = {pid: colors(i) for i, pid in enumerate(pids)}

        for entry in self.gantt:
            pid = entry.pid
            start = entry.start
            duration = entry.end - entry.start
            
            # Dibujamos la barra horizontal
            # broken_barh([(inicio, duración)], (y_min, y_height))
            ax.broken_barh(
                [(start, duration)], 
                (y_pos[pid], 8), 
                facecolors=(pid_colors[pid]),
                edgecolor='black'
            )
            
            # Añadimos texto (PID) dentro de la barra si hay espacio
            if duration > 0:
                ax.text(start + duration / 2, y_pos[pid] + 4, pid, 
                        ha='center', va='center', color='black', fontsize=8)

        # Configuración del gráfico
        ax.set_xlabel('Tiempo')
        ax.set_ylabel('Procesos')
        ax.set_title(f'Diagrama de Gantt - {title}')
        
        # Ponemos los nombres de los procesos en el eje Y
        ax.set_yticks([pos + 4 for pos in y_pos.values()])
        ax.set_yticklabels(pids)
        
        # Invertimos el eje Y para que P1 esté arriba (opcional)
        ax.invert_yaxis()
        
        ax.grid(True, linestyle='--', alpha=0.6)
        
        # Aseguramos que el eje X empiece en 0
        ax.set_xlim(left=0)
        
        # Mostramos el gráfico
        plt.show()


class BaseScheduler:
    """Clase base con utilidades comunes."""
    def __init__(self, processes: List[Process]):
        # Recibimos procesos iniciales; trabajamos con copias (deepcopy)
        # para no modificar la lista original y poder comparar algoritmos
        self.init_processes = deepcopy(processes)

    def run(self) -> SchedulerResult:
        raise NotImplementedError


class FIFOScheduler(BaseScheduler):
    """FIFO / FCFS: Atiende en orden de llegada. 
    Un proceso corre hasta terminar o hasta pedir E/S (no apropiativo)."""
    
    def run(self) -> SchedulerResult:
        procs = deepcopy(self.init_processes)
        time = 0  # Reloj global de la simulación
        
        # Colas de estado
        ready = deque()  # Cola de procesos listos (usamos deque por eficiencia al sacar del inicio)
        blocked: List[Tuple[Process, int]] = []  # Lista de (proceso, tiempo_restante_E/S)
        finished: List[Process] = []
        
        gantt: List[GanttEntry] = []

        # Lista de procesos ordenada por llegada para saber cuándo meterlos
        arrivals = sorted(procs, key=lambda p: p.arrival)
        arrival_idx = 0
        n = len(procs)

        # Bucle principal: corre hasta que todos los procesos hayan terminado
        while len(finished) < n:
            
            # 1. Ingresar nuevos procesos
            # Traer a 'ready' todos los procesos que hayan llegado en el 'time' actual
            while arrival_idx < len(arrivals) and arrivals[arrival_idx].arrival <= time:
                p = arrivals[arrival_idx]
                p.last_ready_enter = time  # Marcamos cuándo entró a 'ready'
                ready.append(p)
                arrival_idx += 1

            # 2. Manejar tiempo ocioso (CPU vacía)
            # Si no hay procesos listos ('ready' está vacía)
            if not ready:
                # Si no hay listos Y no hay más por llegar Y no hay nada bloqueado, terminamos
                if arrival_idx == len(arrivals) and not blocked:
                    break 
                
                # Avanzar 'time' al próximo evento (la próxima llegada o el fin de una E/S)
                next_times = []
                if arrival_idx < len(arrivals):
                    next_times.append(arrivals[arrival_idx].arrival)
                if blocked:
                    # El próximo fin de E/S es 'time' + el mínimo 'rem' de los bloqueados
                    next_times.append(time + min(rem for (_, rem) in blocked))
                
                if not next_times:
                    break # Seguridad, no debería pasar si el bucle while está bien
                
                next_time = min(next_times)
                leap = next_time - time # El tiempo que saltamos
                
                # Actualizar bloqueados durante el salto de tiempo ocioso
                new_blocked = []
                for pb, rem in blocked:
                    rem -= leap
                    if rem <= 0:
                        # E/S terminada, entrar a 'ready' en 'next_time'
                        pb.last_ready_enter = next_time
                        ready.append(pb)
                    else:
                        new_blocked.append((pb, rem))
                blocked = new_blocked
                
                time = next_time # Avanzamos el reloj global
                continue # Volvemos al inicio del bucle para re-evaluar (pueden llegar nuevos)

            # 3. Tomar proceso de 'ready'
            # Si llegamos aquí, hay procesos en 'ready'. Tomamos el primero (FIFO)
            p = ready.popleft()
            
            # Contabilizar espera: (tiempo actual - última vez que entró a ready)
            if p.last_ready_enter is not None:
                p.waiting_time += time - p.last_ready_enter
                p.last_ready_enter = None
            
            # Marcar tiempo de inicio (si es la primera vez)
            if p.start_time is None:
                p.start_time = time

            # 4. Calcular cuánto va a correr
            # En FIFO, corre hasta la próxima E/S o hasta que termine
            consume = p.consumes_to_next_io()
            
            start = time
            end = time + consume
            if consume > 0: # Solo registrar si hubo ejecución real
                gantt.append(GanttEntry(p.pid, start, end))

            # Avanzar el tiempo y actualizar estado del proceso
            time = end
            p.executed += consume
            p.remaining -= consume

            # 5. Decidir qué pasó al final de la ráfaga
            next_io = None
            for ev in p.io_events:
                if ev.at == p.executed:
                    next_io = ev
                    break

            if next_io and p.remaining > 0:
                # A. Pidió E/S: Pasa a bloqueado
                # Se añade con su duración total. El bucle (6) la reducirá.
                blocked.append((p, next_io.duration))
            elif p.remaining == 0:
                # B. Terminó
                p.finish_time = time
                finished.append(p)
            else:
                # C. No debería pasar en FIFO (si no hay E/S y no terminó, 'consume' sería 0?)
                # Por si acaso, lo devolvemos a 'ready'
                p.last_ready_enter = time
                ready.append(p)

            # 6. Actualizar E/S de procesos bloqueados MIENTRAS 'p' corría
            if blocked and consume > 0:
                new_blocked = []
                for pb, rem in blocked:
                    rem -= consume  
                    if rem <= 0:
                        # E/S terminada. Entra a 'ready' en 'time'
                        pb.last_ready_enter = time
                        ready.append(pb)
                    else:
                        new_blocked.append((pb, rem))
                blocked = new_blocked

        return SchedulerResult(gantt, procs, time)


class RRScheduler(BaseScheduler):
    """Round Robin: Apropiativo por 'quantum'.
    Un proceso puede ser interrumpido por E/S, por finalización o por quantum agotado."""
    
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
            
            # 1. Ingresar nuevos procesos (igual que FIFO)
            while arrival_idx < len(arrivals) and arrivals[arrival_idx].arrival <= time:
                p = arrivals[arrival_idx]
                p.last_ready_enter = time
                ready.append(p)
                arrival_idx += 1

            # 2. Manejar tiempo ocioso (igual que FIFO)
            if not ready:
                if arrival_idx == len(arrivals) and not blocked:
                    break
                    
                next_times = []
                if arrival_idx < len(arrivals):
                    next_times.append(arrivals[arrival_idx].arrival)
                if blocked:
                    next_times.append(time + min(bt for (_, bt) in blocked))
                
                if not next_times:
                    break
                
                next_time = min(next_times)
                leap = next_time - time
                
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

            # 3. Tomar proceso de 'ready' (igual que FIFO, saca del inicio)
            p = ready.popleft()
            
            if p.last_ready_enter is not None:
                p.waiting_time += time - p.last_ready_enter
                p.last_ready_enter = None
            if p.start_time is None:
                p.start_time = time

            # 4. Calcular cuánto va a correr (¡Aquí cambia!)
            to_io = p.consumes_to_next_io()
            run_time = min(self.quantum, to_io, p.remaining)
            
            start = time
            end = time + run_time
            if run_time > 0: # Solo registrar si hubo ejecución real
                gantt.append(GanttEntry(p.pid, start, end))

            # Avanzar
            time = end
            p.executed += run_time
            p.remaining -= run_time

            # 5. Decidir qué pasó al final de la ráfaga
            next_io = None
            for ev in p.io_events:
                if ev.at == p.executed:
                    next_io = ev
                    break
            
            # Re-ingresar nuevos procesos que pudieron llegar *justo* ahora
            while arrival_idx < len(arrivals) and arrivals[arrival_idx].arrival <= time:
                p_new = arrivals[arrival_idx]
                p_new.last_ready_enter = time
                ready.append(p_new)
                arrival_idx += 1

            if next_io and p.remaining > 0 and run_time == to_io:
                # A. Pidió E/S (se cumple to_io <= quantum)
                blocked.append((p, next_io.duration))
            elif p.remaining == 0:
                # B. Terminó (se cumple p.remaining <= quantum y <= to_io)
                p.finish_time = time
                finished.append(p)
            else:
                # C. Se acabó el quantum (o justo coincidió quantum y E/S/Fin)
                # Si no terminó y no pidió E/S, fue apropiado por quantum
                # Vuelve al final de la cola 'ready'
                p.last_ready_enter = time
                ready.append(p)

            # 6. Actualizar E/S de procesos bloqueados MIENTRAS 'p' corría
            if blocked and run_time > 0:
                new_blocked = []
                for pb, rem in blocked:
                    rem -= run_time # Restamos lo que 'p' usó de CPU
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
    """Define los procesos de prueba."""
    return [
        Process(pid="P1", arrival=0, burst=10, io_events=[IOEvent(at=4, duration=3)]),
        Process(pid="P2", arrival=2, burst=6, io_events=[IOEvent(at=3, duration=2)]),
        Process(pid="P3", arrival=4, burst=4, io_events=[]),
        Process(pid="P4", arrival=6, burst=8, io_events=[IOEvent(at=2, duration=4)]),
    ]


def run_comparison(process_list: List[Process], quantum: int):
    """Ejecuta ambos simuladores e imprime la comparación."""
    print("Procesos iniciales:")
    for p in process_list:
        ios = ", ".join(f"(at={ev.at},dur={ev.duration})" for ev in p.io_events) or "sin IO"
        print(f"  {p.pid}: llegada={p.arrival}, burst={p.burst}, IOs={ios}")
    
    print("\n--- FIFO ---")
    # Usamos deepcopy para asegurar que FIFO no afecte la lista para RR
    fifo = FIFOScheduler(deepcopy(process_list))
    res_fifo = fifo.run()
    res_fifo.print_summary()
    res_fifo.plot_gantt("FIFO")  # <-- AÑADIDO: Muestra el gráfico FIFO

    print("\n--- RR (quantum = {}) ---".format(quantum))
    rr = RRScheduler(deepcopy(process_list), quantum)
    res_rr = rr.run()
    res_rr.print_summary()
    res_rr.plot_gantt(f"Round Robin (Q={quantum})") # <-- AÑADIDO: Muestra el gráfico RR


# Punto de entrada principal
if __name__ == "__main__":
    procs = example_processes()
    run_comparison(procs, quantum=3)