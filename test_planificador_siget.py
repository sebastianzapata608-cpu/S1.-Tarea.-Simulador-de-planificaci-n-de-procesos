"""Pruebas automaticas del planificador de procesos del SIGET."""

import unittest

from planificador_siget import Estado, Proceso, procesos_demo, simular


class PruebasPlanificadorSIGET(unittest.TestCase):
    def test_rechaza_quantum_invalido(self) -> None:
        with self.assertRaises(ValueError):
            simular(procesos_demo(), "rr", quantum=0)

    def test_rechaza_pid_duplicado(self) -> None:
        proceso = Proceso("P1", "Dato", 0, 2, 1, 10)
        with self.assertRaises(ValueError):
            simular((proceso, proceso), "rr")

    def test_round_robin_respeta_quantum(self) -> None:
        procesos = (
            Proceso("P1", "Uno", 0, 4, 1, 10),
            Proceso("P2", "Dos", 0, 4, 1, 10),
        )
        resultado = simular(procesos, "rr", quantum=2)
        self.assertEqual(
            resultado.secuencia_cpu,
            ("P1", "P1", "P2", "P2", "P1", "P1", "P2", "P2"),
        )

    def test_prioridad_desaloja_por_alerta_urgente(self) -> None:
        procesos = (
            Proceso("RUT", "Rutina", 0, 5, 4, 50),
            Proceso("EMG", "Emergencia", 1, 2, 1, 10),
        )
        resultado = simular(procesos, "prioridad")
        self.assertEqual(resultado.secuencia_cpu[:3], ("RUT", "EMG", "EMG"))
        metrica_emg = next(m for m in resultado.metricas if m.pid == "EMG")
        self.assertEqual(metrica_emg.respuesta, 0)

    def test_se_observan_cinco_estados(self) -> None:
        resultado = simular(procesos_demo(), "prioridad")
        observados = {Estado.NUEVO}
        for paso in resultado.pasos:
            observados.update(vista.estado for vista in paso.procesos)
        self.assertEqual(observados, set(Estado))

    def test_todos_terminan_y_consumen_su_rafaga(self) -> None:
        definiciones = procesos_demo()
        for algoritmo in ("rr", "prioridad"):
            with self.subTest(algoritmo=algoritmo):
                resultado = simular(definiciones, algoritmo)
                self.assertEqual(
                    len([pid for pid in resultado.secuencia_cpu if pid != "IDLE"]),
                    sum(p.tiempo_irrupcion for p in definiciones),
                )
                self.assertTrue(
                    all(
                        vista.estado is Estado.TERMINADO
                        for vista in resultado.pasos[-1].procesos
                    )
                )

    def test_prioridad_mejora_respuesta_critica_del_caso_demo(self) -> None:
        rr = simular(procesos_demo(), "rr")
        prioridad = simular(procesos_demo(), "prioridad")
        self.assertLess(prioridad.respuesta_critica, rr.respuesta_critica)


if __name__ == "__main__":
    unittest.main()
