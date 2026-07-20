"""
╔══════════════════════════════════════════════════════════════╗
║  OptiPrice SaaS  v1.0                                       ║
║  Modulo Universal de Optimizacion de Precios y Margen       ║
║  para PyMEs Comerciales                                     ║
║  Motor analitico: Calculo infinitesimal simbolico (SymPy)   ║
║  Paradigma: POO                                             ║
║  Autor: Ingeniero de Software Senior & Economista Matematico║
╚══════════════════════════════════════════════════════════════╝
"""

import sympy as sp
import sys
import re


class CalculadoraPreciosUniversal:
    """
    Clase principal generica y abstracta para optimizacion de
    precios y utilidades mediante calculo infinitesimal analitico.

    Flujo matematico:
      1) I(x) = x * P(x)                     -> Ingreso Total
      2) U(x) = I(x) - C(x)                   -> Utilidad Neta
      3) U'(x)                                -> Utilidad Marginal
      4) Resolver U'(x) = 0                   -> Puntos criticos
      5) Evaluar U''(x) en cada punto critico -> Criterio de 2da derivada
      6) Seleccionar maximo (U''(x) < 0)      -> Optimo economico
    """

    def __init__(self):
        """Inicializa la variable simbolica central 'x' (cantidad de unidades)."""
        self.x = sp.Symbol('x', positive=True, real=True)
        self._costo_str = ""
        self._demanda_str = ""
        self.C = None       # Funcion de Costo Total   C(x)
        self.P = None       # Funcion de Demanda/Precio P(x)
        self.I = None       # Ingreso Total            I(x) = x * P(x)
        self.U = None       # Utilidad Neta            U(x) = I(x) - C(x)
        self.U_prima = None # Primera derivada          U'(x)
        self.U_biprima = None # Segunda derivada        U''(x)
        self.puntos_criticos = []
        self.maximo_valido = None
        self.valor_U_biprima_en_maximo = None

    # ------------------------------------------------------------------
    # Metodos de parseo y registro de funciones
    # ------------------------------------------------------------------

    def _parsear_expresion(self, expr_str: str) -> sp.Expr:
        """
        Convierte una cadena de texto en una expresion simbolica de SymPy.
        Incluye saneamiento basico y reemplazo de tokens matematicos
        comunes escritos por humanos ('^' -> '**', 'e' -> 'E', etc.).
        """
        expr_limpia = expr_str.strip()

        # Reemplazar notacion de potencia humana '^' por '**'
        expr_limpia = expr_limpia.replace('^', '**')

        # Reemplazar 'e' suelto como constante de Euler si aparece
        expr_limpia = re.sub(r'\be\b', 'E', expr_limpia)

        # Reemplazar 'ln' por 'log' (SymPy usa 'log' para ln)
        expr_limpia = expr_limpia.replace('ln(', 'log(')

        try:
            expr = sp.sympify(expr_limpia, locals={'x': self.x})
        except (sp.SympifyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"Error al parsear la expresion: '{expr_str}'. "
                f"Verifique la sintaxis matematica. Detalle: {exc}"
            )
        return expr

    def registrar_costo(self, expr_str: str):
        """
        Registra la funcion de Costo Total C(x) desde un string.
        Ejemplos: "0.5*x**2 + 200", "1000 + 15*x", "x**2 + 30*x + 5000"
        """
        self._costo_str = expr_str
        self.C = self._parsear_expresion(expr_str)
        print(f"  [OK] C(x) = {sp.pretty(self.C, use_unicode=False)}")
        self._reconstruir()

    def registrar_demanda(self, expr_str: str):
        """
        Registra la funcion de Demanda o Precio Unitario P(x) desde un string.
        Ejemplos: "-0.25*x + 40", "100 - 2*x", "5000/x + 10"
        """
        self._demanda_str = expr_str
        self.P = self._parsear_expresion(expr_str)
        print(f"  [OK] P(x) = {sp.pretty(self.P, use_unicode=False)}")
        self._reconstruir()

    def _reconstruir(self):
        """Reconstruye I(x), U(x), U'(x), U''(x) cuando se actualiza C o P."""
        if self.C is not None and self.P is not None:
            self.I = self.x * self.P
            self.U = self.I - self.C
            self.U_prima = sp.diff(self.U, self.x)
            self.U_biprima = sp.diff(self.U_prima, self.x)
            # Limpiar resultados previos
            self.puntos_criticos = []
            self.maximo_valido = None
            self.valor_U_biprima_en_maximo = None

    # ------------------------------------------------------------------
    # Metodos de analisis y optimizacion
    # ------------------------------------------------------------------

    def _extraer_soluciones_reales_positivas(self, soluciones):
        """
        Filtra y extrae unicamente las soluciones que sean:
          - Reales (no complejas)
          - Positivas (x > 0)
          - Finitas (no infinitas)
        """
        resultado = []
        for sol in soluciones:
            sol_n = sp.N(sol)
            if sol_n.is_real and sol_n.is_positive and sol_n.is_finite:
                resultado.append(float(sol_n.evalf(10)))
        return resultado

    def _segunda_derivada_en(self, valor):
        """Evalua U''(x) en un valor numerico dado."""
        return float(self.U_biprima.subs(self.x, valor).evalf(10))

    def optimizar(self):
        """
        Ejecuta el pipeline completo de optimizacion:

          1. Calcula U'(x) y U''(x) (ya construidas en _reconstruir).
          2. Resuelve U'(x) = 0.
          3. Filtra raices reales positivas finitas.
          4. Aplica criterio de la segunda derivada a cada punto critico.
          5. Selecciona el maximo absoluto (U''(x) < 0).
          6. Si no hay maximo valido, lanza excepcion.

        Retorna dict con:
            - 'cantidad_optima': float
            - 'precio_optimo': float
            - 'utilidad_maxima': float
            - 'segunda_derivada': float
            - 'U_prima': expresion
            - 'U_biprima': expresion
            - 'todos_puntos_criticos': list[float]
        """
        if self.C is None or self.P is None:
            raise RuntimeError(
                "Debe registrar ambas funciones (costo y demanda) antes de optimizar."
            )

        # Resolver U'(x) = 0 (intento analitico, con fallback numerico)
        soluciones = []
        try:
            sol_raw = sp.solve(self.U_prima, self.x)
            if not isinstance(sol_raw, list):
                sol_raw = [sol_raw]
            soluciones = sol_raw
        except (NotImplementedError, sp.polys.polyerrors.PolynomialError,
                TypeError, AttributeError):
            # Fallback: resolver numericamente
            soluciones = []

        # Si solve analitico no dio resultados, usar busqueda numerica
        if not soluciones:
            import mpmath as mp

            def f_num(xv):
                return float(self.U_prima.subs(self.x, xv).evalf(10))

            # Buscar cambio de signo barriendo dominio economico
            raices_numericas = set()
            puntos_muestreo = [0.001, 0.01, 0.1, 1, 5, 10, 50, 100, 500, 1000, 5000, 10000, 50000, 1e5]
            for i in range(len(puntos_muestreo) - 1):
                a, b = puntos_muestreo[i], puntos_muestreo[i + 1]
                fa, fb = f_num(a), f_num(b)
                if fa == 0:
                    raices_numericas.add(float(a))
                    continue
                if fb == 0:
                    raices_numericas.add(float(b))
                    continue
                if fa * fb < 0:
                    try:
                        root = mp.findroot(f_num, (a, b))
                        raices_numericas.add(float(root))
                    except Exception:
                        pass
            soluciones = list(raices_numericas)

        # Extraer soluciones reales positivas
        candidatos = self._extraer_soluciones_reales_positivas(soluciones)
        self.puntos_criticos = candidatos

        if not candidatos:
            raise RuntimeError(
                "No se encontraron puntos criticos reales y positivos en el dominio "
                "economico (x > 0). Esto puede ocurrir si:\n"
                "  1) La funcion de Utilidad U(x) es monotona (creciente o "
                "decreciente) sin maximos locales.\n"
                "  2) El mercado simulado no presenta un punto de equilibrio "
                "marginal optimo.\n"
                "  3) Revise que las funciones C(x) y P(x) esten bien definidas."
            )

        # Aplicar criterio de la segunda derivada
        maximo_candidato = None
        valor_segunda_derivada = None

        for punto in candidatos:
            segunda_der = self._segunda_derivada_en(punto)
            if segunda_der < 0:
                # Maximo local -> concavidad negativa
                if (maximo_candidato is None or
                        self.U.subs(self.x, punto).evalf(10) >
                        self.U.subs(self.x, maximo_candidato).evalf(10)):
                    maximo_candidato = punto
                    valor_segunda_derivada = segunda_der

        if maximo_candidato is None:
            raise RuntimeError(
                "Ningun punto critico satisface el criterio de maximo "
                f"(U''(x) < 0). Puntos evaluados: {candidatos}. "
                "La funcion de Utilidad es concava hacia arriba en todos "
                "sus puntos criticos (minimos locales), lo que indica que "
                "no existe un precio optimo que maximice la utilidad bajo "
                "las condiciones dadas."
            )

        self.maximo_valido = maximo_candidato
        self.valor_U_biprima_en_maximo = valor_segunda_derivada

        # Calcular precio optimo P(x_opt) y utilidad maxima U(x_opt)
        precio_optimo = float(self.P.subs(self.x, maximo_candidato).evalf(10))
        utilidad_maxima = float(self.U.subs(self.x, maximo_candidato).evalf(10))

        return {
            'cantidad_optima': maximo_candidato,
            'precio_optimo': precio_optimo,
            'utilidad_maxima': utilidad_maxima,
            'segunda_derivada': valor_segunda_derivada,
            'U_prima': self.U_prima,
            'U_biprima': self.U_biprima,
            'todos_puntos_criticos': candidatos,
        }

    # ------------------------------------------------------------------
    # Reporte detallado en consola
    # ------------------------------------------------------------------

    def reporte_completo(self):
        """
        Genera e imprime un reporte formateado con todos los resultados
        del analisis de optimizacion.
        """
        if self.maximo_valido is None:
            raise RuntimeError("Ejecute 'optimizar()' antes de generar el reporte.")

        resultado = {
            'cantidad_optima': self.maximo_valido,
            'precio_optimo': float(self.P.subs(self.x, self.maximo_valido).evalf(10)),
            'utilidad_maxima': float(self.U.subs(self.x, self.maximo_valido).evalf(10)),
            'segunda_derivada': self.valor_U_biprima_en_maximo,
            'U_prima': self.U_prima,
            'U_biprima': self.U_biprima,
            'todos_puntos_criticos': self.puntos_criticos,
        }

        print("\n" + "=" * 68)
        print("  O P T I P R I C E   S a a S   -   R E P O R T E")
        print("  Optimizacion de Precio y Utilidad (Calculo Analitico)")
        print("=" * 68)

        # Funciones registradas
        print("\n  Funciones ingresadas:")
        print("    C(x) = " + sp.pretty(self.C, use_unicode=False).replace('\n', '\n' + ' ' * 11))
        print("    P(x) = " + sp.pretty(self.P, use_unicode=False).replace('\n', '\n' + ' ' * 11))
        print("  Funciones derivadas:")
        print("    I(x) = " + sp.pretty(self.I, use_unicode=False).replace('\n', '\n' + ' ' * 11))
        print("    U(x) = " + sp.pretty(self.U, use_unicode=False).replace('\n', '\n' + ' ' * 11))

        # Funciones marginales
        print("\n  --- FUNCIONES MARGINALES ------------------------------")
        print("  | U'(x)  = " + sp.pretty(self.U_prima, use_unicode=False).replace('\n', '\n' + '  |' + ' ' * 10))
        print("  | U''(x) = " + sp.pretty(self.U_biprima, use_unicode=False).replace('\n', '\n' + '  |' + ' ' * 10))
        print("  ------------------------------------------------------")

        # Puntos criticos
        print("\n  Puntos criticos (U'(x) = 0, x > 0):")
        if self.puntos_criticos:
            for i, p in enumerate(self.puntos_criticos, 1):
                segunda_der = self._segunda_derivada_en(p)
                tipo = "MAXIMO (valido)" if segunda_der < 0 else "minimo (descartado)"
                print(f"    {i}) x = {p:,.4f}   |   U''({p:,.4f}) = {segunda_der:,.6f}   ->   {tipo}")
        else:
            print("    (ninguno)")

        # Resultado final
        print("\n  --- RESULTADO OPTIMO ----------------------------------")
        print(f"  |  Cantidad optima de produccion:  {resultado['cantidad_optima']:>10,.4f}  unidades")
        print(f"  |  Precio de venta sugerido:      ${resultado['precio_optimo']:>10,.4f}  c/u")
        print(f"  |  Utilidad maxima proyectada:    ${resultado['utilidad_maxima']:>10,.4f}")
        print(f"  |  Segunda derivada U''(x0):       {resultado['segunda_derivada']:>10,.6f}  (< 0 -> maximo)")
        print("  ------------------------------------------------------")
        print("=" * 68 + "\n")

        return resultado


# ======================================================================
#  BLOQUE DE EJECUCION PRINCIPAL - INTERFAZ DE CONSOLA (MODO DEMO)
# ======================================================================

def _validar_no_vacio(texto, nombre_campo):
    """Valida que el texto ingresado no este vacio."""
    if not texto or not texto.strip():
        raise ValueError(f"'{nombre_campo}' no puede estar vacio.")
    return texto.strip()


def _ingresar_funcion(mensaje, ejemplo):
    """
    Solicita al usuario que ingrese una funcion por consola,
    con reintento en caso de error de sintaxis.
    """
    while True:
        try:
            texto = input(f"  {mensaje}\n" + "    -> ")
            texto = _validar_no_vacio(texto, mensaje)
            # Prueba de parseo (usamos Symbol placeholder para validar sintaxis)
            sp.sympify(texto.replace('^', '**'), locals={'x': sp.Symbol('x')})
            return texto
        except (sp.SympifyError, TypeError, ValueError) as e:
            print(f"  Error de sintaxis: {e}")
            print(f"  Ejemplo: {ejemplo}\n")


def demo_interactiva():
    """
    Modo interactivo de consola. Guia al usuario paso a paso para
    registrar funciones, ejecutar la optimizacion y ver el reporte.
    """
    print("\n")
    print("+" + "=" * 66 + "+")
    print("|         OptiPrice SaaS  -  MODO DEMO INTERACTIVO         |")
    print("|   Optimizacion Universal de Precios y Utilidad (SymPy)   |")
    print("+" + "=" * 66 + "+")
    print("\n  Este asistente le guiara para ingresar las funciones")
    print("  de Costo Total C(x) y Demanda P(x) de su negocio.")
    print("  x representa la cantidad de unidades producidas/vendidas.\n")

    # Operadores validos
    print("  Notacion permitida:")
    print("    - Potencia: x**2  o  x^2")
    print("    - Logaritmo natural: ln(x)  o  log(x)")
    print("    - Constante de Euler: E")
    print("    - Constante pi: pi\n")

    calculadora = CalculadoraPreciosUniversal()

    # Ingreso de funcion de costo
    print("  --- FUNCION DE COSTO TOTAL C(x) ---")
    costo_str = _ingresar_funcion(
        "  Ingrese C(x):",
        "0.5*x**2 + 30*x + 2000"
    )
    try:
        calculadora.registrar_costo(costo_str)
    except ValueError as e:
        print(f"\n  Error: {e}")
        print("  Reinicie el asistente e intente de nuevo.")
        return

    print()

    # Ingreso de funcion de demanda
    print("  --- FUNCION DE DEMANDA / PRECIO UNITARIO P(x) ---")
    demanda_str = _ingresar_funcion(
        "  Ingrese P(x):",
        "-0.25*x + 40"
    )
    try:
        calculadora.registrar_demanda(demanda_str)
    except ValueError as e:
        print(f"\n  Error: {e}")
        print("  Reinicie el asistente e intente de nuevo.")
        return

    # Ejecutar optimizacion
    print("\n  Analizando...")
    try:
        calculadora.optimizar()
    except RuntimeError as e:
        print(f"\n  Error de optimizacion: {e}")
        print("  Sugerencia: ajuste las funciones e intente nuevamente.")
        return

    # Reporte final
    calculadora.reporte_completo()


# ======================================================================
#  Punto de entrada
# ======================================================================

if __name__ == "__main__":
    """
    Dos modos de ejecucion:

      1) Sin argumentos -> demo interactiva guiada paso a paso.
      2) Con argumentos (C(x) y P(x)) -> ejecucion directa y reporte.
    """
    if len(sys.argv) == 3:
        # Modo argumentos directos
        costo_arg = sys.argv[1]
        demanda_arg = sys.argv[2]
        print("\n  OptiPrice SaaS - Modo argumentos directos\n")
        calc = CalculadoraPreciosUniversal()
        try:
            calc.registrar_costo(costo_arg)
            calc.registrar_demanda(demanda_arg)
            calc.optimizar()
            calc.reporte_completo()
        except (ValueError, RuntimeError) as e:
            print(f"\n  Error: {e}")
            sys.exit(1)
    elif len(sys.argv) == 2:
        print("  Uso: python optiprice_saas.py \"C(x)\" \"P(x)\"")
        print('  Ejemplo: python optiprice_saas.py "0.5*x^2+30*x+2000" "-0.25*x+40"')
        sys.exit(1)
    else:
        # Modo interactivo (por defecto)
        demo_interactiva()
