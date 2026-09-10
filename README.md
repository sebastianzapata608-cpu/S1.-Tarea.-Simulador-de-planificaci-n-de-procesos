# SIGET – Simulador de Planificación de Procesos
## 🎥 Video de evidencia

En el siguiente enlace se puede visualizar la explicación y ejecución del simulador:

[Ver video de evidencia - Grupo 5](https://drive.google.com/file/d/1nBdsAAXcE3RWpHHvI6W9CClbTX1jk43T/view)

## Descripción

Este proyecto implementa un **simulador de planificación de CPU** adaptado al contexto del **Sistema Inteligente de Gestión de Tráfico (SIGET)**.

El objetivo es representar cómo un sistema operativo puede administrar diferentes procesos que compiten por el uso de la CPU, aplicando distintos algoritmos de planificación y observando el comportamiento de cada proceso durante su ciclo de vida.

El simulador permite comparar dos algoritmos:

* **Round Robin**
* **Prioridad preventiva**

Además, representa dinámicamente los estados de los procesos y calcula diferentes métricas que permiten analizar el rendimiento de cada estrategia de planificación.

---

# Objetivo del proyecto

Simular la gestión de procesos dentro del SIGET para analizar cómo diferentes algoritmos de planificación afectan aspectos como:

* Tiempo de espera.
* Tiempo de respuesta.
* Tiempo de retorno.
* Atención de procesos críticos.
* Cantidad de cambios de contexto.
* Rendimiento general del sistema.
* Equidad en la distribución de CPU.

La simulación busca representar un escenario donde algunas tareas corresponden a procesamiento rutinario y otras representan eventos de mayor urgencia.

---

# Procesos simulados

El proyecto utiliza cuatro procesos relacionados con el funcionamiento del SIGET.

| PID       | Proceso                 | Llegada | Tiempo de CPU | Prioridad |  Datos |
| --------- | ----------------------- | ------: | ------------: | --------: | -----: |
| `CAM-01`  | Análisis de cámaras     |       0 |             7 |         3 | 120 MB |
| `HIST-30` | Consolidación histórica |       0 |             6 |         4 | 250 MB |
| `SEN-08`  | Alerta de congestión    |       1 |             5 |         2 |  60 MB |
| `EMG-911` | Detección de accidente  |       2 |             4 |         1 |  15 MB |

En el algoritmo de prioridad:

**Un número menor representa una prioridad mayor.**

Por ejemplo:

`1 = máxima prioridad`

Por esta razón, `EMG-911`, correspondiente a la detección de un accidente, representa la tarea más urgente del escenario.

---

# Información almacenada por proceso

Cada proceso contiene atributos como:

* `PID`
* Nombre.
* Tiempo de llegada.
* `tiempo_irrupcion`.
* `prioridad_alerta`.
* `tamano_datos_mb`.
* Bloqueos opcionales de entrada/salida.

Estos atributos permiten representar procesos con diferentes características y necesidades dentro del sistema.

---

# Estados de los procesos

Durante la simulación cada proceso puede pasar por los cinco estados principales estudiados en Sistemas Operativos.

## Nuevo

El proceso existe, pero todavía no ha llegado al sistema.

```text
Nuevo
```

---

## Listo

El proceso ya puede ejecutarse, pero se encuentra esperando un turno para utilizar la CPU.

```text
Listo
```

---

## En ejecución

El proceso actualmente está utilizando la CPU.

```text
En ejecucion
```

---

## Bloqueado

El proceso debe esperar temporalmente por una operación simulada de entrada/salida.

```text
Bloqueado
```

Después de finalizar dicha operación, el proceso regresa al estado `Listo`.

---

## Terminado

El proceso consumió completamente el tiempo de CPU que necesitaba.

```text
Terminado
```

---

# Algoritmos implementados

## 1. Round Robin

Round Robin distribuye el tiempo de CPU de manera equitativa entre los procesos disponibles.

Cada proceso recibe una cantidad limitada de tiempo denominada:

```text
Quantum
```

En este proyecto el valor predeterminado es:

```text
Quantum = 2
```

Cuando un proceso consume su quantum y todavía no ha terminado, vuelve a la cola de procesos listos para esperar un nuevo turno.

De esta manera se evita que un único proceso monopolice la CPU.

### Características principales

* Utiliza una cola FIFO.
* Distribuye la CPU de manera equitativa.
* Permite configurar el quantum.
* Puede producir una mayor cantidad de cambios de contexto.
* Es apropiado cuando se busca repartir el procesador entre múltiples tareas.

---

# 2. Prioridad preventiva

Este algoritmo selecciona para ejecución el proceso listo con la **prioridad más alta**.

En nuestra implementación:

```text
Prioridad 1 = mayor prioridad
```

Si mientras un proceso utiliza la CPU aparece otro proceso con una prioridad superior, el proceso actual puede ser desalojado.

Por ejemplo:

Si se está ejecutando un proceso rutinario con prioridad `4` y aparece una emergencia con prioridad `1`, la CPU puede detener temporalmente el proceso rutinario y atender la emergencia.

### Características principales

* Favorece eventos críticos.
* Permite desalojar procesos en ejecución.
* Reduce la latencia de respuesta de las alertas importantes.
* Puede aumentar el tiempo de espera de procesos menos prioritarios.

---

# Bloqueos de Entrada/Salida

Algunos procesos incluyen operaciones simuladas de entrada/salida.

Durante estas operaciones el proceso cambia:

```text
En ejecucion
      ↓
Bloqueado
      ↓
Listo
```

Mientras dicho proceso está bloqueado, otro proceso puede utilizar la CPU.

Esto permite representar de manera más realista el comportamiento de los procesos administrados por un sistema operativo.

---

# Comparación de los algoritmos

El programa ejecuta ambos algoritmos utilizando el mismo conjunto de procesos para permitir una comparación justa.

Se analizan métricas como:

* Espera promedio.
* Respuesta promedio.
* Respuesta de procesos críticos.
* Retorno promedio.
* Cambios de contexto.
* Rendimiento.

La interpretación general es:

### Round Robin

Busca distribuir la CPU de manera equitativa.

### Prioridad preventiva

Busca responder rápidamente a eventos urgentes.

Por esta razón, dentro del contexto del SIGET, un algoritmo basado en prioridades puede resultar especialmente útil para situaciones como:

* Accidentes.
* Congestiones severas.
* Alertas críticas.
* Eventos que requieren respuesta inmediata.

Sin embargo, los procesos rutinarios pueden experimentar tiempos de espera mayores.

---

# Diagrama de Gantt

El simulador genera un **diagrama de Gantt textual** para visualizar el orden en el cual los procesos utilizaron la CPU.

Ejemplo:

```text
CAM-01 | CAM-01 | HIST-30 | HIST-30 | SEN-08 | EMG-911 | ...
```

Esto facilita observar las diferencias entre los algoritmos de planificación.

---

# Métricas calculadas

Para cada proceso se calculan:

### Tiempo de espera

Tiempo durante el cual el proceso permanece listo esperando utilizar la CPU.

### Tiempo de respuesta

Tiempo transcurrido desde la llegada del proceso hasta que obtiene la CPU por primera vez.

### Tiempo de retorno

Tiempo total desde la llegada del proceso hasta su finalización.

Además, el programa calcula:

* Espera promedio.
* Respuesta promedio.
* Retorno promedio.
* Respuesta crítica.
* Cambios de contexto.
* Rendimiento en procesos por unidad de tiempo.

---

# Estructura del proyecto

```text
SIGET_PLANIFICADOR/
│
├── planificador_siget.py
├── test_planificador_siget.py
├── README.md
├── evidencia_planificador.txt
├── guion_video_planificador.md
│
└── output/
    └── pdf/
        └── relatoria_planificador_SIGET.pdf
```

## Archivos

### `planificador_siget.py`

Contiene la implementación principal del simulador, los procesos, estados, algoritmos de planificación, métricas y generación de resultados.

### `test_planificador_siget.py`

Contiene las pruebas automáticas utilizadas para comprobar el funcionamiento del simulador.

### `evidencia_planificador.txt`

Archivo que puede contener una ejecución completa y reproducible de la simulación.

### `guion_video_planificador.md`

Guion utilizado como apoyo para realizar el video de evidencia.

### `relatoria_planificador_SIGET.pdf`

Documento técnico donde se explican las decisiones de diseño, algoritmos implementados, resultados y conclusiones.

---

# Requisitos

* Python 3.10 o superior.
* No requiere paquetes externos.

El programa utiliza únicamente módulos disponibles en la biblioteca estándar de Python.

---

# Ejecución

Desde una terminal ubicada en la carpeta del proyecto ejecutar:

```powershell
python .\planificador_siget.py
```

De manera predeterminada el programa ejecutará y comparará:

```text
Round Robin
vs.
Prioridad preventiva
```

---

# Visualizar los estados de los procesos

Para observar la transición de los procesos entre los diferentes estados utilizando Prioridad preventiva:

```powershell
python .\planificador_siget.py --algoritmo prioridad --traza
```

Durante la ejecución se podrá observar información como:

```text
PID       Estado          Restante  Prioridad  Espera
---------  --------------  --------  ---------  ------
CAM-01     En ejecucion           5          3       0
HIST-30    Listo                  6          4       2
SEN-08     Listo                  5          2       1
EMG-911    Nuevo                  4          1       0
```

---

# Ejecutar Round Robin

Para ejecutar solamente Round Robin:

```powershell
python .\planificador_siget.py --algoritmo rr
```

También se puede modificar el quantum.

Por ejemplo:

```powershell
python .\planificador_siget.py --algoritmo rr --quantum 3
```

---

# Ejecutar Prioridad preventiva

```powershell
python .\planificador_siget.py --algoritmo prioridad
```

Para mostrar también todas las transiciones:

```powershell
python .\planificador_siget.py --algoritmo prioridad --traza
```

---

# Ejecución paso a paso

El simulador permite avanzar manualmente una unidad de tiempo cada vez que se presiona Enter.

Ejemplo:

```powershell
python .\planificador_siget.py --algoritmo rr --quantum 2 --traza --paso
```

Esta opción es especialmente útil para observar y explicar el ciclo de vida de los procesos durante una demostración.

---

# Comparar los algoritmos

Para ejecutar ambos algoritmos y comparar sus resultados:

```powershell
python .\planificador_siget.py --algoritmo comparar
```

Al finalizar se genera una tabla similar a:

```text
=== COMPARACION DE ALGORITMOS ===

Metrica                         Round Robin  Prioridad preventiva
------------------------------  -----------  --------------------
Espera promedio
Respuesta promedio
Respuesta critica
Retorno promedio
Cambios de contexto
Rendimiento
```

Posteriormente el programa indica cuál algoritmo obtuvo:

* Menor latencia crítica.
* Menor espera promedio.

---

# Generar evidencia

El programa permite almacenar automáticamente la traza completa y los resultados de la simulación.

```powershell
python .\planificador_siget.py --algoritmo comparar --quantum 2 --traza --rapido --evidencia .\evidencia_planificador.txt
```

El archivo generado será:

```text
evidencia_planificador.txt
```

Este archivo contiene:

* Transiciones de estados.
* Uso de CPU.
* Eventos de cada proceso.
* Métricas.
* Diagramas de Gantt.
* Comparación de algoritmos.

---

# Ejecución rápida

La opción:

```powershell
--rapido
```

elimina las pausas utilizadas durante la visualización animada.

Ejemplo:

```powershell
python .\planificador_siget.py --algoritmo prioridad --traza --rapido
```

---

# Pruebas automáticas

El proyecto incluye **siete pruebas automáticas**.

Para ejecutarlas:

```powershell
python -m unittest -v test_planificador_siget.py
```

Las pruebas verifican, entre otros aspectos:

* Rechazo de valores inválidos para el quantum.
* Rechazo de PID duplicados.
* Correcto funcionamiento del quantum de Round Robin.
* Desalojo por llegada de una alerta más urgente.
* Representación de los cinco estados.
* Finalización correcta de todos los procesos.
* Mejora de la respuesta crítica mediante Prioridad preventiva.

Una ejecución correcta debe finalizar indicando:

```text
Ran 7 tests

OK
```

---

# Manejo de errores

El simulador incluye diferentes validaciones para evitar configuraciones incorrectas.

Entre ellas:

* Quantum mayor que cero.
* Tiempo de llegada válido.
* Tiempo de irrupción mayor que cero.
* Prioridad positiva.
* Tamaño de datos válido.
* PID únicos.
* Bloqueos de entrada/salida correctamente definidos.
* Velocidad de visualización válida.

Esto permite hacer el simulador más robusto frente a entradas incorrectas.

---

# Conceptos de Sistemas Operativos aplicados

Durante el desarrollo se aplican diferentes conceptos relacionados con la gestión de procesos.

## Planificación de CPU

Determina qué proceso debe utilizar el procesador en cada instante.

## Cambio de contexto

Ocurre cuando la CPU deja de ejecutar un proceso y comienza a ejecutar otro.

## Desalojo

Permite retirar temporalmente de la CPU un proceso para ejecutar otro.

## Quantum

Cantidad máxima de tiempo que un proceso puede utilizar la CPU en Round Robin antes de ceder su turno.

## Prioridad

Permite determinar qué procesos deben recibir atención primero.

## Estados del proceso

Representan las diferentes etapas por las que pasa un proceso durante su ciclo de vida.

## Entrada/Salida

Puede provocar que un proceso abandone temporalmente la CPU y permanezca bloqueado.

---

# Conclusión

La simulación demuestra cómo diferentes algoritmos de planificación pueden producir comportamientos distintos utilizando exactamente el mismo conjunto de procesos.

**Round Robin** ofrece una distribución más equitativa de la CPU mediante el uso de un quantum.

Por otro lado, **Prioridad preventiva** permite responder más rápidamente ante eventos críticos, característica especialmente importante dentro de un sistema inteligente de gestión de tráfico.

En un escenario como el SIGET, donde pueden coexistir procesos rutinarios con situaciones de emergencia, la selección del algoritmo de planificación tiene un impacto directo sobre los tiempos de respuesta y la utilización eficiente de los recursos.

La comparación de métricas permite observar estas diferencias de forma objetiva y relacionar la simulación con los conceptos estudiados sobre administración de procesos en Sistemas Operativos.

---

## Autor

Sebastián Zapata Alvarez
Emanuel Taborda Lopez
Juan Alejandro Salazar Acosta

Tecnología en Desarrollo de Software
Sistemas Operativos
2026
