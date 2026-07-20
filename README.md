# OptiPrice SaaS

**Optimización de precios y utilidades mediante cálculo diferencial simbólico.**

Sistema SaaS que encuentra el **precio y la cantidad óptima de producción** para maximizar la utilidad de una PyME comercial. El usuario solo ingresa datos básicos de su negocio — el motor interno procesa las derivadas y resuelve el modelo de optimización automáticamente.

---

## Cómo funciona

### 1. Entrada de datos

El usuario ingresa **3 conceptos simples**:

| Dato | Ejemplo | Significado |
|------|---------|-------------|
| **Costo Fijo** | $2,000 | Rentas, sueldos, costos que no cambian con la producción |
| **Costo Variable Unitario** | $30 | Materiales, mano de obra directa por cada unidad |
| **Metas de Venta** | A $50 vendo 100 uds, a $40 vendo 200 uds | Estimaciones de precio versus cantidad esperada |

### 2. Procesamiento interno (motor matemático)

La clase `CalculadoraPrecios` construye automáticamente:

```
C(x) = costo_variable · x + costo_fijo         ← Costo Total
P(x) = pendiente · x + intercepto              ← Demanda (ajustada desde metas)
I(x) = x · P(x)                                 ← Ingreso Total
U(x) = I(x) − C(x)                             ← Utilidad Neta
U'(x) = 0                                       ← Derivada: condición de máximo
U''(x) < 0                                      ← Segunda derivada: concavidad
```

### 3. Resultado

El sistema reporta:

- **Cantidad óptima** de unidades a producir
- **Precio de venta sugerido** por unidad
- **Utilidad máxima** proyectada
- **Margen unitario** (precio − costo marginal)
- **Gráfico** de la curva de utilidad con el punto máximo resaltado
- **Funciones y derivadas** del modelo completo

---

## Stack tecnológico

| Componente | Tecnología |
|------------|-----------|
| **Lenguaje** | Python 3.x |
| **Framework web** | Flask |
| **Cálculo simbólico** | SymPy |
| **Resolución numérica** | mpmath |
| **Frontend** | Bootstrap 5 + Chart.js + Bootstrap Icons |
| **Despliegue** | Vercel |

---

## Instalación y ejecución local

```bash
# Clonar el repositorio
git clone https://github.com/lcgavilan97/Calculo.git
cd Calculo

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python web_app.py
# Abrir http://127.0.0.1:5000
```

### Modo consola

También incluye una versión CLI:

```bash
python optiprice_saas.py "C(x)" "P(x)"
# Ejemplo:
python optiprice_saas.py "0.5*x**2+30*x+2000" "-0.25*x+40"
```

---

## Estructura del proyecto

```
Calculo/
├── web_app.py           # Interfaz web (Flask) con interfaz moderna
├── optiprice_saas.py    # Versión de consola (CLI)
├── requirements.txt     # Dependencias del proyecto
├── vercel.json          # Configuración para Vercel
└── README.md            # Este archivo
```

---

## Licencia

MIT
