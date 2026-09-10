"""Simulador de planificacion de CPU para procesos del SIGET.

Implementa Round Robin y Prioridad Preventiva mediante una simulacion discreta.
Cada unidad del reloj representa una unidad de CPU; no se usan pausas para
calcular los resultados, por lo que todas las ejecuciones son reproducibles.

Ejemplos:
    python planificador_siget.py
    python planificador_siget.py --algoritmo prioridad --traza --rapido
    python planificador_siget.py --algoritmo rr --quantum 2 --traza --paso
"""

from __future__ import annotations

import argparse
import copy
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from statistics import mean
from typing import Iterable, Sequence


class Estado(str, Enum):
    NUEVO = "Nuevo"
    LISTO = "Listo"
    EJECUCION = "En ejecucion"
    BLOQUEADO = "Bloqueado"
    TERMINADO = "Terminado"


@dataclass(frozen=True, slots=True)
class Proceso:
    """Definicion inmutable de una tarea de procesamiento del SIGET."""

    pid: str
    nombre: str
    llegada: int
    tiempo_irrupcion: int
    prioridad_alerta: int
    tamano_datos_mb: int
    bloqueos: tuple[tuple[int, int], ...] = ()

    def __post_init__(self) -> None:
        if not self.pid.strip() or not self.nombre.strip():
            raise ValueError("El PID y el nombre no pueden estar vacios")
        if self.llegada < 0:
            raise ValueError("El tiempo de llegada no puede ser negativo")
        if self.tiempo_irrupcion <= 0:
            raise ValueError("El tiempo de irrupcion debe ser mayor que cero")
        if self.prioridad_alerta <= 0:
            raise ValueError("La prioridad debe ser positiva (1 es la mas alta)")
        if self.tamano_datos_mb <= 0:
            raise ValueError("El tamano de datos debe ser mayor que cero")
        puntos = [punto for punto, _ in self.bloqueos]
        if puntos != sorted(set(puntos)):
            raise ValueError("Los puntos de bloqueo deben ser unicos y crecientes")
        if any(
            punto <= 0
            or punto >= self.tiempo_irrupcion
            or duracion <= 0
            for punto, duracion in self.bloqueos
        ):
            raise ValueError("Cada bloqueo debe ocurrir durante la rafaga y durar > 0")


@dataclass(slots=True)
class ProcesoEnEjecucion:
    proceso: Proceso
    restante: int = field(init=False)
    estado: Estado = Estado.NUEVO
    cpu_consumida: int = 0
    espera: int = 0
    primera_cpu: int | None = None
    finalizacion: int | None = None
    desbloqueo: int | None = None
    siguiente_bloqueo: int = 0

    def __post_init__(self) -> None:
        self.restante = self.proceso.tiempo_irrupcion


@dataclass(frozen=True, slots=True)
class VistaProceso:
    pid: str
    estado: Estado
    restante: int
    prioridad: int
    espera: int


@dataclass(frozen=True, slots=True)
class Paso:
    instante: int
    cpu: str
    eventos: tuple[str, ...]
    procesos: tuple[VistaProceso, ...]


@dataclass(frozen=True, slots=True)
class MetricaProceso:
    pid: str
    prioridad: int
    espera: int
    respuesta: int
    retorno: int


@dataclass(frozen=True, slots=True)
class Resultado:
    algoritmo: str
    pasos: tuple[Paso, ...]
    metricas: tuple[MetricaProceso, ...]
    secuencia_cpu: tuple[str, ...]
    cambios_contexto: int
    tiempo_total: int

    @property
    def espera_promedio(self) -> float:
        return mean(m.espera for m in self.metricas)

    @property
    def respuesta_promedio(self) -> float:
        return mean(m.respuesta for m in self.metricas)

    @property
    def retorno_promedio(self) -> float:
        return mean(m.retorno for m in self.metricas)

    @property
    def respuesta_critica(self) -> float:
        criticos = [m.respuesta for m in self.metricas if m.prioridad <= 2]
        return mean(criticos) if criticos else 0.0

    @property
    def rendimiento(self) -> float:
        return len(self.metricas) / self.tiempo_total if self.tiempo_total else 0.0


def procesos_demo() -> tuple[Proceso, ...]:
    """Caso de prueba que contrasta datos rutinarios y alertas criticas."""

    return (
        Proceso(
            "CAM-01",
            "Analisis de camaras",
            llegada=0,
            tiempo_irrupcion=7,
            prioridad_alerta=3,
            tamano_datos_mb=120,
            bloqueos=((3, 2),),
        ),
        Proceso(
            "HIST-30",
            "Consolidacion historica",
            llegada=0,
            tiempo_irrupcion=6,
            prioridad_alerta=4,
            tamano_datos_mb=250,
            bloqueos=((2, 2),),
        ),
        Proceso(
            "SEN-08",
            "Alerta de congestion",
            llegada=1,
            tiempo_irrupcion=5,
            prioridad_alerta=2,
            tamano_datos_mb=60,
        ),
        Proceso(
            "EMG-911",
            "Deteccion de accidente",
            llegada=2,
            tiempo_irrupcion=4,
            prioridad_alerta=1,
            tamano_datos_mb=15,
            bloqueos=((1, 1),),
        ),
    )


def _validar_procesos(procesos: Sequence[Proceso]) -> None:
    if not procesos:
        raise ValueError("Debe existir al menos un proceso")
    pids = [proceso.pid for proceso in procesos]
    if len(pids) != len(set(pids)):
        raise ValueError("Los PID deben ser unicos")


def simular(
    procesos: Sequence[Proceso], algoritmo: str, quantum: int = 2
) -> Resultado:
    """Ejecuta RR o prioridad preventiva y devuelve la traza completa."""

    _validar_procesos(procesos)
    algoritmo = algoritmo.lower()
    if algoritmo not in {"rr", "prioridad"}:
        raise ValueError("El algoritmo debe ser 'rr' o 'prioridad'")
    if quantum <= 0:
        raise ValueError("El quantum debe ser mayor que cero")

    activos = {p.pid: ProcesoEnEjecucion(copy.deepcopy(p)) for p in procesos}
    orden = {p.pid: indice for indice, p in enumerate(procesos)}
    listos: list[str] = []
    actual: str | None = None
    usado_quantum = 0
    ultimo_cpu: str | None = None
    cambios_contexto = 0
    reloj = 0
    pasos: list[Paso] = []
    secuencia_cpu: list[str] = []
    limite = (
        max(p.llegada for p in procesos)
        + sum(p.tiempo_irrupcion for p in procesos)
        + sum(duracion for p in procesos for _, duracion in p.bloqueos)
        + 100
    )

    def agregar_listo(pid: str) -> None:
        if pid not in listos:
            listos.append(pid)

    while any(p.estado is not Estado.TERMINADO for p in activos.values()):
        if reloj > limite:
            raise RuntimeError("La simulacion excedio el limite de seguridad")
        eventos: list[str] = []

        for definicion in procesos:
            runtime = activos[definicion.pid]
            if runtime.estado is Estado.NUEVO and definicion.llegada == reloj:
                runtime.estado = Estado.LISTO
                agregar_listo(definicion.pid)
                eventos.append(f"{definicion.pid} pasa de Nuevo a Listo")

        for definicion in procesos:
            runtime = activos[definicion.pid]
            if (
                runtime.estado is Estado.BLOQUEADO
                and runtime.desbloqueo == reloj
            ):
                runtime.estado = Estado.LISTO
                runtime.desbloqueo = None
                agregar_listo(definicion.pid)
                eventos.append(f"{definicion.pid} termina E/S: Bloqueado a Listo")

        if algoritmo == "prioridad" and actual is not None and listos:
            candidato = min(
                listos,
                key=lambda pid: (
                    activos[pid].proceso.prioridad_alerta,
                    activos[pid].proceso.llegada,
                    orden[pid],
                ),
            )
            if (
                activos[candidato].proceso.prioridad_alerta
                < activos[actual].proceso.prioridad_alerta
            ):
                anterior = actual
                activos[anterior].estado = Estado.LISTO
                agregar_listo(anterior)
                actual = None
                usado_quantum = 0
                eventos.append(
                    f"{anterior} es desalojado por la prioridad de {candidato}"
                )

        if actual is None and listos:
            if algoritmo == "rr":
                actual = listos.pop(0)
            else:
                actual = min(
                    listos,
                    key=lambda pid: (
                        activos[pid].proceso.prioridad_alerta,
                        activos[pid].proceso.llegada,
                        orden[pid],
                    ),
                )
                listos.remove(actual)
            runtime = activos[actual]
            runtime.estado = Estado.EJECUCION
            if runtime.primera_cpu is None:
                runtime.primera_cpu = reloj
            eventos.append(f"{actual} pasa de Listo a En ejecucion")

        for pid in listos:
            activos[pid].espera += 1

        cpu = actual or "IDLE"
        if actual is not None:
            if ultimo_cpu is not None and ultimo_cpu != actual:
                cambios_contexto += 1
            ultimo_cpu = actual
            runtime = activos[actual]
            runtime.restante -= 1
            runtime.cpu_consumida += 1
            secuencia_cpu.append(actual)
            usado_quantum += 1

            if runtime.restante == 0:
                runtime.estado = Estado.TERMINADO
                runtime.finalizacion = reloj + 1
                eventos.append(f"{actual} pasa de En ejecucion a Terminado")
                actual = None
                usado_quantum = 0
            elif (
                runtime.siguiente_bloqueo < len(runtime.proceso.bloqueos)
                and runtime.cpu_consumida
                == runtime.proceso.bloqueos[runtime.siguiente_bloqueo][0]
            ):
                _, duracion = runtime.proceso.bloqueos[runtime.siguiente_bloqueo]
                runtime.siguiente_bloqueo += 1
                runtime.estado = Estado.BLOQUEADO
                runtime.desbloqueo = reloj + 1 + duracion
                eventos.append(
                    f"{actual} solicita E/S: En ejecucion a Bloqueado "
                    f"por {duracion} u.t."
                )
                actual = None
                usado_quantum = 0
            elif algoritmo == "rr" and usado_quantum >= quantum:
                runtime.estado = Estado.LISTO
                agregar_listo(actual)
                eventos.append(
                    f"{actual} agota quantum={quantum}: En ejecucion a Listo"
                )
                actual = None
                usado_quantum = 0
        else:
            secuencia_cpu.append("IDLE")
            eventos.append("CPU ociosa: no hay procesos listos")

        vistas = tuple(
            VistaProceso(
                pid=p.pid,
                estado=activos[p.pid].estado,
                restante=activos[p.pid].restante,
                prioridad=p.prioridad_alerta,
                espera=activos[p.pid].espera,
            )
            for p in procesos
        )
        pasos.append(Paso(reloj, cpu, tuple(eventos), vistas))
        reloj += 1

    metricas = tuple(
        MetricaProceso(
            pid=p.pid,
            prioridad=p.prioridad_alerta,
            espera=activos[p.pid].espera,
            respuesta=(activos[p.pid].primera_cpu or 0) - p.llegada,
            retorno=(activos[p.pid].finalizacion or reloj) - p.llegada,
        )
        for p in procesos
    )
    nombre = "Round Robin" if algoritmo == "rr" else "Prioridad preventiva"
    return Resultado(
        algoritmo=nombre,
        pasos=tuple(pasos),
        metricas=metricas,
        secuencia_cpu=tuple(secuencia_cpu),
        cambios_contexto=cambios_contexto,
        tiempo_total=reloj,
    )


def _tabla_procesos(procesos: Iterable[VistaProceso]) -> list[str]:
    lineas = [
        "PID       Estado          Restante  Prioridad  Espera",
        "---------  --------------  --------  ---------  ------",
    ]
    for p in procesos:
        lineas.append(
            f"{p.pid:<9}  {p.estado.value:<14}  {p.restante:>8}  "
            f"{p.prioridad:>9}  {p.espera:>6}"
        )
    return lineas


def formatear_traza(resultado: Resultado) -> str:
    lineas = [
        f"\n=== TRAZA: {resultado.algoritmo} ===",
        "Estado inicial: todos los procesos estan en Nuevo y conservan su rafaga completa.",
    ]
    for paso in resultado.pasos:
        lineas.append(f"\nFin del intervalo [{paso.instante}, {paso.instante + 1}) | CPU: {paso.cpu}")
        lineas.extend(f"  - {evento}" for evento in paso.eventos)
        lineas.extend(_tabla_procesos(paso.procesos))
    return "\n".join(lineas)


def formatear_resumen(resultado: Resultado) -> str:
    lineas = [
        f"\n=== RESULTADOS: {resultado.algoritmo} ===",
        "PID       Pri.  Espera  Respuesta  Retorno",
        "---------  ----  ------  ---------  -------",
    ]
    for metrica in resultado.metricas:
        lineas.append(
            f"{metrica.pid:<9}  {metrica.prioridad:>4}  {metrica.espera:>6}  "
            f"{metrica.respuesta:>9}  {metrica.retorno:>7}"
        )
    lineas.extend(
        [
            f"Espera promedio: {resultado.espera_promedio:.2f} u.t.",
            f"Respuesta promedio: {resultado.respuesta_promedio:.2f} u.t.",
            f"Respuesta critica (prioridad 1-2): {resultado.respuesta_critica:.2f} u.t.",
            f"Retorno promedio: {resultado.retorno_promedio:.2f} u.t.",
            f"Cambios de contexto: {resultado.cambios_contexto}",
            f"Rendimiento: {resultado.rendimiento:.3f} procesos/u.t.",
            "Gantt: " + " | ".join(resultado.secuencia_cpu),
        ]
    )
    return "\n".join(lineas)


def formatear_comparacion(rr: Resultado, prioridad: Resultado) -> str:
    mejor_critico = (
        prioridad.algoritmo
        if prioridad.respuesta_critica < rr.respuesta_critica
        else rr.algoritmo
    )
    menor_espera = (
        prioridad.algoritmo
        if prioridad.espera_promedio < rr.espera_promedio
        else rr.algoritmo
    )
    return "\n".join(
        [
            "\n=== COMPARACION DE ALGORITMOS ===",
            "Metrica                         Round Robin  Prioridad preventiva",
            "------------------------------  -----------  --------------------",
            f"Espera promedio (u.t.)          {rr.espera_promedio:>11.2f}  {prioridad.espera_promedio:>20.2f}",
            f"Respuesta promedio (u.t.)       {rr.respuesta_promedio:>11.2f}  {prioridad.respuesta_promedio:>20.2f}",
            f"Respuesta critica (u.t.)        {rr.respuesta_critica:>11.2f}  {prioridad.respuesta_critica:>20.2f}",
            f"Retorno promedio (u.t.)         {rr.retorno_promedio:>11.2f}  {prioridad.retorno_promedio:>20.2f}",
            f"Cambios de contexto             {rr.cambios_contexto:>11}  {prioridad.cambios_contexto:>20}",
            f"Rendimiento (procesos/u.t.)     {rr.rendimiento:>11.3f}  {prioridad.rendimiento:>20.3f}",
            "",
            f"Menor latencia critica: {mejor_critico}.",
            f"Menor espera promedio en este escenario: {menor_espera}.",
            "Interpretacion: Round Robin reparte la CPU de forma equitativa; "
            "Prioridad preventiva favorece las alertas urgentes y puede retrasar "
            "el trabajo rutinario.",
        ]
    )


def _mostrar_animado(texto: str, pausa: float, paso_a_paso: bool) -> None:
    bloques = texto.split("\nFin del intervalo")
    print(bloques[0])
    for bloque in bloques[1:]:
        print("\nFin del intervalo" + bloque)
        if paso_a_paso:
            input("Presione Enter para avanzar...")
        elif pausa > 0:
            time.sleep(pausa)


def construir_salida(
    resultados: Sequence[Resultado], incluir_traza: bool, comparar: bool
) -> str:
    partes: list[str] = []
    for resultado in resultados:
        if incluir_traza:
            partes.append(formatear_traza(resultado))
        partes.append(formatear_resumen(resultado))
    if comparar and len(resultados) == 2:
        partes.append(formatear_comparacion(resultados[0], resultados[1]))
    return "\n".join(partes).strip() + "\n"


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulador de planificacion de procesos para el SIGET"
    )
    parser.add_argument(
        "--algoritmo",
        choices=("rr", "prioridad", "comparar"),
        default="comparar",
        help="algoritmo que se ejecutara (predeterminado: comparar)",
    )
    parser.add_argument(
        "--quantum", type=int, default=2, help="quantum de Round Robin"
    )
    parser.add_argument(
        "--traza", action="store_true", help="muestra los estados en cada intervalo"
    )
    parser.add_argument(
        "--paso", action="store_true", help="avanza la traza al presionar Enter"
    )
    parser.add_argument(
        "--rapido", action="store_true", help="elimina la pausa de la animacion"
    )
    parser.add_argument(
        "--velocidad",
        type=float,
        default=0.15,
        help="segundos de pausa entre intervalos (predeterminado: 0.15)",
    )
    parser.add_argument(
        "--evidencia",
        type=Path,
        help="guarda traza y resultados en un archivo de texto",
    )
    return parser.parse_args()


def main() -> int:
    opciones = argumentos()
    if opciones.quantum <= 0:
        print("Error: el quantum debe ser mayor que cero.")
        return 2
    if opciones.velocidad < 0:
        print("Error: la velocidad no puede ser negativa.")
        return 2

    definiciones = procesos_demo()
    algoritmos = (
        ("rr", "prioridad")
        if opciones.algoritmo == "comparar"
        else (opciones.algoritmo,)
    )
    resultados = tuple(
        simular(definiciones, algoritmo, opciones.quantum)
        for algoritmo in algoritmos
    )
    comparar = opciones.algoritmo == "comparar"

    if opciones.traza and not opciones.evidencia:
        for resultado in resultados:
            _mostrar_animado(
                formatear_traza(resultado),
                0.0 if opciones.rapido else opciones.velocidad,
                opciones.paso,
            )
            print(formatear_resumen(resultado))
        if comparar:
            print(formatear_comparacion(resultados[0], resultados[1]))
    else:
        print(construir_salida(resultados, opciones.traza, comparar), end="")

    if opciones.evidencia:
        opciones.evidencia.parent.mkdir(parents=True, exist_ok=True)
        contenido = construir_salida(resultados, incluir_traza=True, comparar=comparar)
        opciones.evidencia.write_text(contenido, encoding="utf-8")
        print(f"Evidencia guardada en: {opciones.evidencia}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
