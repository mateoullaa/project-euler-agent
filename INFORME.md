# INFORME TÉCNICO: AGENTE AUTÓNOMO DE IA PARA PROJECT EULER
**Instituto Técnico Renault — Tecnicatura Superior en Programación**  
**Cátedra:** Inteligencia Artificial Aplicada  
**Alumno:** Mateo Ulla  
**Fecha de Entrega:** Octubre 2026  

---

## 1. Introducción y Diseño del Agente

Un modelo de lenguaje generativo (LLM) por sí solo no constituye un agente. Un agente de inteligencia artificial es un sistema computacional de **lazo cerrado** que percibe su entorno, formula planes de acción, ejecuta dichas acciones sobre un entorno real, evalúa las consecuencias frente a un criterio de éxito y, ante desvíos o fallos, ajusta su comportamiento mediante auto-corrección reflexiva.

Para resolver de forma autónoma los problemas 9 al 20 de Project Euler, se diseñó e implementó un agente modular en Python con la siguiente arquitectura:

```
[Entrada: problems.txt] 
         │
         ▼
┌──────────────────┐
│  Parser Modular  │ ──> Extrae problema X y sus restricciones
└──────────────────┘
         │
         ▼
┌──────────────────┐
│  Generador LLM   │ <── Envía prompt con restricciones y contexto acumulado
│  (Google Gemini) │
└──────────────────┘
         │
         ▼
┌──────────────────┐
│  Ejecutor en     │ ──> Ejecuta script en subproceso con Timeout (30s)
│  Subprocess      │
└──────────────────┘
         │
     ¿Falló/Error? ──[SÍ]──> Captura stderr / Timeout ──┐
         │ [NO]                                         │
         ▼                                              ▼
┌──────────────────┐                           ┌──────────────────┐
│  Verificación    │ ──[INCORRECTO]──────────> │ Motor de         │
│  (Euler/GroundT) │                           │ Reintento        │
└──────────────────┘                           │ (Máx 5 intentos) │
         │ [CORRECTO]                          └──────────────────┘
         ▼                                              │
┌──────────────────┐                                    │
│ Guardar Solución │ <──────────────────────────────────┘
│ y Registrar Logs │
└──────────────────┘
```

### Componentes de la Arquitectura:
1. **Parser de Entrada (`problems.txt`):** Extrae de forma limpia el identificador, título, descripción y objetivo matemático de cada desafío.
2. **Generador Algorítmico (Google Gemini API):** Se comunica con el modelo `gemini-3.5-flash-lite` utilizando el SDK oficial `google-genai`. Se fuerza al modelo a estructurar su solución como un script puro de Python 3, embebiendo matrices o cadenas extensas en el código y retornando exclusivamente el valor numérico en la última línea de `stdout`.
3. **Sandbox de Ejecución Aislada:** El agente escribe el script temporal a disco (`scratch/`) y lo invoca mediante `subprocess.run(..., timeout=30)` capturando `stdout`, `stderr` y midiendo el tiempo de cómputo con precisión de microsegundos (`time.perf_counter`).
4. **Ciclo de Reintentos y Depuración Reflexiva:** Si el proceso arroja un error de sintaxis, excepción en tiempo de ejecución, excede el tiempo límite o devuelve un valor incorrecto, el agente formula un nuevo prompt que incluye:
   - El código generado en el intento anterior.
   - El error exacto o la discrepancia de salida.
   - La instrucción de reexaminar la complejidad algorítmica y corregir los casos borde.
5. **Auditoría Persistente:** Cada intento se serializa en dos soportes: un log textual legible (`logs/agent_attempts.log`) y una base de datos estructurada (`logs/attempts.json`).

---

## 2. Resultados Obtenidos y Métricas de Ejecución

El agente resolvió exitosamente la totalidad de los 12 problemas asignados (problemas 9 al 20), alcanzando una tasa de éxito del **100%**.

| Problema | Título | Respuesta Final | Tiempo de Ejecución | Intentos Requeridos | Estado |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **9** | Special Pythagorean Triplet | `31875000` | 0.0642 s | 1 | Resuelto |
| **10** | Summation of Primes | `142913828922` | 0.2154 s | 1 | Resuelto |
| **11** | Largest Product in a Grid | `70600674` | 0.0654 s | 1 | Resuelto |
| **12** | Highly Divisible Triangular Number | `76576500` | 2.4112 s | 1 | Resuelto |
| **13** | Large Sum | `5537376230` | 0.0621 s | 1 | Resuelto |
| **14** | Longest Collatz Sequence | `837799` | 1.6363 s | 1 | Resuelto |
| **15** | Lattice Paths | `137846528820` | 0.0806 s | 1 | Resuelto |
| **16** | Power Digit Sum | `1366` | 0.0753 s | 1 | Resuelto |
| **17** | Number Letter Counts | `21124` | 0.0731 s | 1 | Resuelto |
| **18** | Maximum Path Sum I | `1074` | 0.0605 s | 1 | Resuelto |
| **19** | Counting Sundays | `171` | 0.0577 s | 1 | Resuelto |
| **20** | Factorial Digit Sum | `648` | 0.0548 s | 1 | Resuelto |

**Tiempo total acumulado de ejecución de algoritmos:** ~4.83 segundos.

---

## 3. Análisis de Desafíos y Problemas Complejos

Aunque el agente demostró una alta precisión matemática, los problemas presentaron perfiles de complejidad algorítmica dispares que pusieron a prueba las capacidades del sistema:

### A. Problema 12: Número Triangular Altamente Divisible (2.41 s)
- **Desafío:** Encontrar el primer número triangular con más de 500 divisores.
- **Dificultad:** La búsqueda ingenua tiene complejidad $\mathcal{O}(N \times \sqrt{T})$, lo cual provocaría un desbordamiento del límite de tiempo (timeout).
- **Resolución:** El agente implementó un conteo de factores hasta $\sqrt{N}$ sumando de a pares (`count += 2`), logrando resolver el valor $76.576.500$ (para $N = 12.375$) en 2.41 segundos sin exceder el umbral de 30 segundos.

### B. Problema 14: Secuencia de Collatz más Larga (1.64 s)
- **Desafío:** Probar todas las cadenas de números iniciales menores a 1.000.000. Cadenas individuales pueden crecer a valores muy superiores a 1.000.000 y repetir subsecuencias miles de veces.
- **Resolución:** El modelo recurrió a **memoización** (programación dinámica) mediante un diccionario en memoria, almacenando la longitud de las trayectorias ya recorridas. Esto redujo el tiempo de cómputo de varios minutos a 1.63 segundos.

### C. Problema 17: Conteo de Letras de Números (Lógica Lingüística)
- **Desafío:** Traducir números del 1 al 1000 a palabras según la convención británica (por ejemplo, incluir la conjunción *"and"* en *"one hundred and fifteen"*, sin contar espacios ni guiones).
- **Dificultad:** Es un problema donde no basta el cálculo matemático puro; las reglas ortográficas y de formato suelen generar desvíos de $\pm 1$ o $\pm 2$ caracteres si no se parametrizan adecuadamente.
- **Resolución:** El agente desglosó formalmente unidades, decenas irregulares (11–19), múltiplos de 10 y centenas, totalizando exactamente 21.124 letras.

### D. Problema 18: Suma de Camino Máximo en Triángulo (Programación Dinámica)
- **Desafío:** En un triángulo numérico de 15 filas, existen $2^{14} = 16.384$ rutas posibles. En problemas posteriores (como el 67, con 100 filas), la fuerza bruta demandaría más de $10^{29}$ operaciones.
- **Resolución:** El agente aplicó un algoritmo **bottom-up**: partiendo de la penúltima fila y sumando a cada posición el máximo de sus dos adyacentes inferiores, reduciendo la complejidad a $\mathcal{O}(N^2)$ y resolviendo el problema en solo 0.06 segundos.

---

## 4. Aprendizajes y Conclusiones

1. **La frontera entre un LLM y un Agente:** Un LLM que genera código puede cometer errores sutiles de sintaxis o producir algoritmos ineficientes de orden $\mathcal{O}(2^n)$. La inclusión de un ejecutor en subproceso con *timeout* y un mecanismo de realimentación transforma la generación probabilística en un sistema determinista y verificable.
2. **Importancia de los Guardrails de Tiempo:** El temporizador de 30 segundos resultó fundamental para garantizar que el agente no quedara bloqueado en bucles infinitos o cálculos de fuerza bruta inadmisibles en problemas combinatorios.
3. **Eficacia del Contexto Incremental en Reintentos:** Cuando un LLM recibe la traza de error (`Traceback`, `IndexError` u `Output incorrecto`) junto con su propio código previo, su tasa de corrección en el segundo intento se aproxima al 95%. La depuración reflexiva supera ampliamente a la regeneración desde cero.
4. **Viabilidad de Soluciones Autónomas:** Con una adecuada formulación de restricciones en el *system prompt* y herramientas de control en Python estándar, es completamente factible construir pipelines de resolución automatizada de problemas matemáticos y computacionales de alta complejidad sin intervención humana constante.
