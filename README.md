# Agente Autónomo de IA para Project Euler (Problemas 9 al 20)
**Instituto Técnico Renault — 2026**

Este repositorio contiene la implementación completa de un agente de inteligencia artificial diseñado para resolver problemas algorítmicos y matemáticos de [Project Euler](https://projecteuler.net) de forma autónoma, implementando un ciclo cerrado de ejecución, verificación y reintentos (auto-corrección).

---

## 1. Arquitectura y Ciclo del Agente

Un agente no es simplemente una llamada a un LLM: es un sistema de control de lazo cerrado que interactúa con un entorno de ejecución.

```
       +---------------------------------------------+
       |           Enunciado del Problema            |
       +---------------------------------------------+
                              |
                              v
       +---------------------------------------------+
       |   1. Generación de Código (Gemini API)      |<---------+
       +---------------------------------------------+          |
                              |                                 |
                              v                                 |
       +---------------------------------------------+          |
       |   2. Ejecución Aislada (Subprocess)         |          |
       |      - Límite de tiempo (Timeout 30s)       |          |
       +---------------------------------------------+          |
                              |                                 |
              [¿Error de ejecución / Timeout?]                  |
                     /                 \                        |
                   SÍ                   NO                      |
                   /                     \                      |
                  v                       v                     |
       [Registrar Error]       +---------------------+          |
                  \            |   3. Verificación   |          |
                   \           |   del Resultado     |          |
                    \          +---------------------+          |
                     \                    |                     |
                      \           [¿Respuesta Correcta?]        |
                       \                 /         \            |
                        \              NO           SÍ          |
                         \             /             \          |
                          v           v               v         |
                     +---------------------+    +---------------+
                     |  Retroalimentación  |    | Fin: Guardar  |
                     |  y Reintento (<= 5) |    | Solución y Log|
                     +---------------------+    +---------------+
                                |
                                +-------------------------------+
```

### Componentes Clave:
1. **Parser de Enunciados (`problems.txt`):** Extrae automáticamente número, título y cuerpo completo de los problemas 9 al 20.
2. **Motor LLM (Google Gemini):** Utiliza la API de Gemini (`gemini-3.5-flash-lite` / `gemini-3.5-flash`) mediante el SDK oficial `google-genai`.
3. **Sandbox de Ejecución (`subprocess`):** Ejecuta cada solución en un proceso independiente con captura de `stdout`, `stderr` y límite estricto de tiempo (`timeout=30s`).
4. **Módulo de Verificación Dual:**
   - **Modo Interactivo:** Solicita al usuario ingresar el resultado en Project Euler y confirmar o reportar feedback.
   - **Modo Automatizado (`--auto-verify`):** Compara contra la verdad de terreno para validación masiva.
5. **Ciclo de Auto-Corrección:** Si el script falla (excepción, timeout o salida incorrecta), el agente captura el error exacto, lo adjunta al código previo y genera un nuevo prompt para que el modelo depure su lógica.
6. **Sistema de Auditoría y Logs:** Registra cada intento en `logs/agent_attempts.log` (formato legible) y `logs/attempts.json` (estructurado).

---

## 2. Estructura del Proyecto

```
project-euler-agent/
│
├── agent.py                 # Código principal del agente autónomo
├── problems.txt             # Especificaciones matemáticas de los problemas 9 al 20
├── requirements.txt         # Dependencias Python
├── README.md                # Documentación del proyecto
│
├── solutions/               # Scripts finales de cada problema resuelto
│   ├── problem_09.py
│   ├── problem_10.py
│   ├── ...
│   └── problem_20.py
│
└── logs/                    # Registro exhaustivo de intentos
    ├── agent_attempts.log   # Log humano detallado
    └── attempts.json        # Log estructurado en JSON
```

---

## 3. Instalación y Uso

### Requisitos previos:
- Python 3.10+ (probado en Python 3.14)
- Conexión a Internet
- Clave de API de Gemini (gratuita en [Google AI Studio](https://aistudio.google.com))

### Instalación:
```bash
pip install -r requirements.txt
```

### Configuración de la API Key:
Puede definirse como variable de entorno o guardarse en `gemini_api_key.txt`:
```bash
# PowerShell
$env:GEMINI_API_KEY = "tu_api_key_aqui"
```

### Modos de Ejecución:

**1. Modo Automatizado Masivo (Todos los problemas 9 al 20):**
```bash
python agent.py --problems 9-20 --auto-verify
```

**2. Modo Interactivo (Verificación manual en el sitio de Project Euler):**
```bash
python agent.py --problems 9-20
```
El agente pausará tras calcular la respuesta para que la verifiques en la web de Project Euler. Si ingresas `ok`, guardará la solución; si escribes cualquier otra cosa, reintentará automáticamente.

**3. Ejecutar un problema específico:**
```bash
python agent.py --problems 12 --auto-verify
```

---

## 4. Tabla de Respuestas Verificadas (Problemas 9 al 20)

| Problema | Título | Respuesta Calculada | Tiempo de Ejecución | Intentos | Estado |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **9** | Special Pythagorean Triplet | `31875000` | 0.064 s | 1 | Verificado |
| **10** | Summation of Primes | `142913828922` | 0.215 s | 1 | Verificado |
| **11** | Largest Product in a Grid | `70600674` | 0.065 s | 1 | Verificado |
| **12** | Highly Divisible Triangular Number | `76576500` | 2.411 s | 1 | Verificado |
| **13** | Large Sum | `5537376230` | 0.062 s | 1 | Verificado |
| **14** | Longest Collatz Sequence | `837799` | 1.636 s | 1 | Verificado |
| **15** | Lattice Paths | `137846528820` | 0.081 s | 1 | Verificado |
| **16** | Power Digit Sum | `1366` | 0.075 s | 1 | Verificado |
| **17** | Number Letter Counts | `21124` | 0.073 s | 1 | Verificado |
| **18** | Maximum Path Sum I | `1074` | 0.061 s | 1 | Verificado |
| **19** | Counting Sundays | `171` | 0.058 s | 1 | Verificado |
| **20** | Factorial Digit Sum | `648` | 0.055 s | 1 | Verificado |
