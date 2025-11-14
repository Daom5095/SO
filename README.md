# 🚀 Simulador de Planificación de CPU

Este es un proyecto en Python que simula y compara dos algoritmos fundamentales de planificación de procesos del sistema operativo: **FIFO (First-In, First-Out)** y **Round Robin (RR)**.

El simulador ejecuta un conjunto de procesos de ejemplo a través de ambos algoritmos y genera métricas de rendimiento clave, así como una visualización en forma de diagrama de Gantt para cada uno.

---

## 📋 Características

* **Modelado de Procesos:** Simula procesos con tiempos de llegada (`arrival`), ráfagas de CPU (`burst`) y eventos de Entrada/Salida (`io_events`).
* **Cálculo de Métricas:** Calcula y reporta las siguientes métricas para cada proceso y el promedio del sistema:
    * **Tiempo de Turnaround (TAT):** Tiempo total desde que un proceso llega hasta que termina.
    * **Tiempo de Espera (WT):** Tiempo total que un proceso pasa en la cola de listos (`ready`).
    * **Tiempo de Respuesta (RT):** Tiempo desde que un proceso llega hasta que obtiene la CPU por *primera vez*.
* **Resumen en Consola:** Imprime una tabla de resumen clara en la terminal.
* **Visualización Gráfica:** Genera y muestra automáticamente un **Diagrama de Gantt** para cada algoritmo usando `matplotlib`, permitiendo una fácil comparación visual de la ejecución.

---

## 🧠 Algoritmos Implementados

1.  **FIFO (First-In, First-Out):**
    * Un algoritmo **No Apropiativo**.
    * Los procesos se atienden en el estricto orden en que llegan a la cola de listos.
    * Un proceso no suelta la CPU hasta que termina su ráfaga actual o solicita una E/S.

2.  **Round Robin (RR):**
    * Un algoritmo **Apropiativo**.
    * Cada proceso recibe un pequeño "turno" de tiempo llamado `quantum`.
    * Si el proceso no termina o pide E/S antes de que se acabe su `quantum`, es interrumpido y movido al final de la cola de listos.

---

## 🛠️ Tecnologías Utilizadas

* **Python 3**
* **Matplotlib** (para la generación de los diagramas de Gantt)

---

## ⚙️ Instalación

1.  Clona este repositorio (o simplemente descarga el archivo `sistemas_operativos.py`).
2.  Necesitarás instalar la biblioteca `matplotlib` para que los gráficos funcionen. Puedes instalarla usando `pip`:

    ```bash
    pip install matplotlib
    ```

---

## ▶️ Uso

Una vez instaladas las dependencias, simplemente ejecuta el script de Python desde tu terminal:

```bash
python sistemas_operativos.py
