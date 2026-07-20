"""
OptiPrice SaaS - v3.0
Clase CalculadoraPrecios: procesa internamente la derivada del modelo.
El usuario solo ingresa costos fijos, variables y metas de venta.
"""
from flask import Flask, request, render_template_string
import sympy as sp
import mpmath as mp
import math

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Clase principal: CalculadoraPrecios
# ---------------------------------------------------------------------------

class CalculadoraPrecios:
    def __init__(self):
        self.x = sp.Symbol('x', positive=True, real=True)
        self.costo_fijo = 0
        self.costo_variable = 0
        self.metas_venta = []
        self.C = None
        self.P = None
        self.I = None
        self.U = None
        self.U_prima = None
        self.U_biprima = None
        self.puntos_criticos = []
        self.maximo_valido = None
        self.valor_U_biprima_en_maximo = None

    def registrar(self, costo_fijo, costo_variable, metas_venta):
        self.costo_fijo = float(costo_fijo)
        self.costo_variable = float(costo_variable)
        self.metas_venta = [(float(p), float(q)) for p, q in metas_venta]
        if len(self.metas_venta) < 2:
            raise ValueError("Ingrese al menos 2 metas de venta (precio vs cantidad).")
        self.C = self.costo_variable * self.x + self.costo_fijo
        pts_q = [q for _, q in self.metas_venta]
        pts_p = [p for p, _ in self.metas_venta]
        self.P = self._ajustar_recta(pts_q, pts_p)
        self._reconstruir()

    def _ajustar_recta(self, xs, ys):
        n = len(xs)
        sx = sum(xs); sy = sum(ys)
        sxx = sum(x * x for x in xs)
        sxy = sum(x * y for x, y in zip(xs, ys))
        m = (n * sxy - sx * sy) / (n * sxx - sx * sx)
        b = (sy - m * sx) / n
        return m * self.x + b

    def _reconstruir(self):
        if self.C is not None and self.P is not None:
            self.I = sp.expand(self.x * self.P)
            self.U = sp.expand(self.I - self.C)
            self.U_prima = sp.expand(sp.diff(self.U, self.x))
            self.U_biprima = sp.expand(sp.diff(self.U_prima, self.x))
            self.puntos_criticos = []
            self.maximo_valido = None
            self.valor_U_biprima_en_maximo = None

    def _extraer_reales_positivos(self, soluciones):
        res = []
        for sol in soluciones:
            sn = sp.N(sol)
            if sn.is_real and sn.is_positive and sn.is_finite:
                res.append(float(sn.evalf(10)))
        return res

    def _puntos_para_grafico(self, x_opt, num_puntos=100):
        """Genera puntos (x, U(x)) para el grafico. x desde 0 hasta 2*x_opt."""
        if x_opt <= 0:
            return [], []
        max_x = max(x_opt * 2.5, 50)
        xs = [i * max_x / num_puntos for i in range(num_puntos + 1)]
        us = []
        for xv in xs:
            if xv == 0:
                xv = 0.001
            try:
                val = float(self.U.subs(self.x, xv).evalf(10))
            except Exception:
                val = 0
            us.append(round(val, 4))
        return [round(x, 4) for x in xs], us

    def optimizar(self):
        if self.C is None or self.P is None:
            raise RuntimeError("Registre los datos primero.")

        soluciones = []
        try:
            sr = sp.solve(self.U_prima, self.x)
            soluciones = sr if isinstance(sr, list) else [sr]
        except Exception:
            soluciones = []

        if not soluciones:
            def f_num(xv):
                return float(self.U_prima.subs(self.x, xv).evalf(10))
            raices = set()
            pts = [0.001, 0.01, 0.1, 1, 5, 10, 50, 100, 500, 1000, 5000, 10000, 50000, 1e5]
            for i in range(len(pts) - 1):
                a, b = pts[i], pts[i+1]
                fa, fb = f_num(a), f_num(b)
                if fa == 0: raices.add(float(a)); continue
                if fb == 0: raices.add(float(b)); continue
                if fa * fb < 0:
                    try:
                        raices.add(float(mp.findroot(f_num, (a, b))))
                    except Exception:
                        pass
            soluciones = list(raices)

        candidatos = self._extraer_reales_positivos(soluciones)
        self.puntos_criticos = candidatos

        if not candidatos:
            return self._diagnosticar()

        max_cand = None
        val_seg = None
        for p in candidatos:
            sd = float(self.U_biprima.subs(self.x, p).evalf(10))
            if sd < 0:
                if max_cand is None or self.U.subs(self.x, p).evalf(10) > self.U.subs(self.x, max_cand).evalf(10):
                    max_cand = p
                    val_seg = sd

        if max_cand is None:
            return self._diagnosticar(candidatos)

        self.maximo_valido = max_cand
        self.valor_U_biprima_en_maximo = val_seg

        precio = float(self.P.subs(self.x, max_cand).evalf(10))
        utilidad = float(self.U.subs(self.x, max_cand).evalf(10))
        ingreso = float(self.I.subs(self.x, max_cand).evalf(10))
        costo_t = float(self.C.subs(self.x, max_cand).evalf(10))
        cm = float(sp.diff(self.C, self.x).evalf(10))

        info_criticos = []
        for p in candidatos:
            sd = float(self.U_biprima.subs(self.x, p).evalf(10))
            info_criticos.append({
                'valor': round(p, 4),
                'segunda_derivada': round(sd, 6),
                'tipo': 'MAXIMO' if sd < 0 else 'minimo'
            })

        # Datos para el grafico Chart.js
        gx, gy = self._puntos_para_grafico(max_cand)

        return {
            'exito': True,
            'cantidad_optima': round(max_cand, 4),
            'precio_optimo': round(precio, 4),
            'utilidad_maxima': round(utilidad, 4),
            'ingreso_total': round(ingreso, 4),
            'costo_total': round(costo_t, 4),
            'costo_marginal': round(cm, 4),
            'margen_unitario': round(precio - cm, 4),
            'segunda_derivada': round(val_seg, 6),
            'C': sp.pretty(self.C, use_unicode=False),
            'P': sp.pretty(self.P, use_unicode=False),
            'I': sp.pretty(self.I, use_unicode=False),
            'U': sp.pretty(self.U, use_unicode=False),
            'U_prima': sp.pretty(self.U_prima, use_unicode=False),
            'U_biprima': sp.pretty(self.U_biprima, use_unicode=False),
            'puntos_criticos': info_criticos,
            'chart_x': gx,
            'chart_y': gy,
            'chart_max_x': round(max_cand, 4),
            'chart_max_y': round(utilidad, 4),
        }

    def _diagnosticar(self, candidatos=None):
        info = {
            'C': sp.pretty(self.C, use_unicode=False),
            'P': sp.pretty(self.P, use_unicode=False),
            'I': sp.pretty(self.I, use_unicode=False),
            'U': sp.pretty(self.U, use_unicode=False),
            'U_prima': sp.pretty(self.U_prima, use_unicode=False),
            'U_biprima': sp.pretty(self.U_biprima, use_unicode=False),
            'exito': False,
        }
        if candidatos:
            info['mensaje'] = "Hay puntos criticos pero todos son minimos (U''(x) > 0). Revise sus metas de venta."
            info['puntos'] = [round(p, 4) for p in candidatos]
        else:
            p0 = float(self.P.subs(self.x, 1).evalf(5))
            cv = self.costo_variable
            if p0 > cv:
                info['mensaje'] = (
                    f"El precio estimado (${p0:.2f}) supera el costo variable (${cv:.2f}), "
                    "pero la demanda no decrece lo suficiente para generar un maximo. "
                    "La utilidad crece continuamente: a mayor cantidad, mayor ganancia."
                )
            else:
                info['mensaje'] = (
                    f"El precio inicial estimado (${p0:.2f}) no cubre el costo variable (${cv:.2f}). "
                    "No es rentable producir. Ajuste sus metas de venta."
                )
        return info


# ---------------------------------------------------------------------------
# Interfaz Web - Diseño moderno con glassmorphism y graficos
# ---------------------------------------------------------------------------

HTML = r"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OptiPrice SaaS</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{font-family:'Inter','Segoe UI',sans-serif}
body{
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e9f0 100%);
  min-height:100vh;
}
/* Header animado */
.header{
  background: linear-gradient(-45deg, #0d6efd, #6610f2, #0dcaf0, #6f42c1);
  background-size: 400% 400%;
  animation: grad 12s ease infinite;
  color:#fff; padding:2.5rem 0; text-align:center; margin-bottom:2rem;
  position:relative; overflow:hidden;
}
@keyframes grad{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.header::after{
  content:''; position:absolute; bottom:0; left:0; right:0;
  height:30px; background:linear-gradient(transparent, #f5f7fa);
}
.header h1{font-weight:800; font-size:2.5rem; margin:0; text-shadow:0 2px 20px rgba(0,0,0,.15)}
.header .sub{opacity:.92; font-size:1.1rem; margin-top:.3rem}
.header .icon-top{font-size:3rem; margin-bottom:.3rem; display:inline-block}

/* Glassmorphism cards */
.card-glass{
  background: rgba(255,255,255,.85);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border:1px solid rgba(255,255,255,.3);
  border-radius:16px; box-shadow:0 8px 32px rgba(0,0,0,.08);
  margin-bottom:1.5rem; overflow:hidden;
}
.card-glass .card-hd{
  padding:1rem 1.5rem; font-weight:600; font-size:1.1rem;
  border-bottom:1px solid rgba(0,0,0,.05);
  display:flex; align-items:center; gap:.6rem;
}

/* Inputs */
.input-premium{
  border:2px solid #e0e0e0; border-radius:10px; padding:.6rem .8rem;
  font-size:1.1rem; font-weight:600; transition:all .25s;
}
.input-premium:focus{border-color:#0d6efd; box-shadow:0 0 0 4px rgba(13,110,253,.15); outline:none}
.input-group-text{border-radius:10px 0 0 10px; font-weight:600}

/* Boton optimizar */
.btn-opt{
  background: linear-gradient(135deg,#0d6efd,#6610f2);
  border:none; border-radius:12px; padding:.9rem; font-size:1.1rem;
  font-weight:700; color:#fff; transition:all .3s; position:relative; overflow:hidden;
}
.btn-opt:hover{transform:translateY(-2px); box-shadow:0 8px 25px rgba(13,110,253,.35)}
.btn-opt:active{transform:translateY(0)}
.btn-opt i{margin-right:.5rem}

/* Tabla metas */
.tabla-meta th{
  background:rgba(13,110,253,.06); font-size:.75rem; text-transform:uppercase;
  letter-spacing:.5px; font-weight:700; padding:.6rem .5rem; border:0;
}
.tabla-meta td{border:0; padding:.3rem .2rem; vertical-align:middle}
.tabla-meta input{border:1.5px solid #e0e0e0; border-radius:8px; padding:.4rem .6rem; font-size:.9rem; transition:all .2s; width:100%}
.tabla-meta input:focus{border-color:#0d6efd; box-shadow:0 0 0 3px rgba(13,110,253,.1); outline:none}
.btn-add{font-size:.8rem; border-radius:8px; border:1.5px dashed #0d6efd; background:transparent; color:#0d6efd; padding:.3rem 1rem; transition:all .2s}
.btn-add:hover{background:rgba(13,110,253,.08)}

/* KPI Cards */
.kpi-card{
  background:#fff; border-radius:14px; padding:1rem .5rem; text-align:center;
  box-shadow:0 2px 12px rgba(0,0,0,.05); transition:all .3s; height:100%;
  border:1px solid rgba(0,0,0,.04);
}
.kpi-card:hover{transform:translateY(-3px); box-shadow:0 8px 25px rgba(0,0,0,.1)}
.kpi-icon{font-size:1.6rem; margin-bottom:.2rem}
.kpi-label{font-size:.7rem; text-transform:uppercase; letter-spacing:.5px; color:#888; font-weight:600}
.kpi-valor{font-size:1.6rem; font-weight:800; color:#0d6efd; line-height:1.2}
.kpi-unit{font-size:.75rem; color:#999}

/* Banner resultado principal */
.banner-result{
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
  border-radius:14px; padding:1.5rem; text-align:center; margin-bottom:1.5rem;
  border-left:5px solid #2e7d32;
}
.banner-result h4{font-weight:800; margin:0}
.banner-result h4 span{color:#0d6efd}
.banner-result .big-number{font-size:2rem; font-weight:800; color:#0d6efd}
.banner-result .util-val{font-size:1.8rem; font-weight:800}

/* Banner diagnostico */
.banner-diag{
  background: linear-gradient(135deg, #fff8e1, #ffecb3);
  border-radius:14px; padding:1.2rem; border-left:5px solid #f9a825;
}

/* Modelos y derivadas */
.mono-box{
  background:#f8f9fa; border-radius:8px; padding:.4rem .7rem;
  font-family:'Courier New',monospace; font-size:.85rem; border:1px solid #e9ecef;
  display:inline-block; margin-bottom:.3rem;
}

/* Steps */
.step-line{
  display:flex; flex-wrap:wrap; gap:.3rem; justify-content:center; margin:1rem 0;
}
.step-item{
  background:#fff; border:1px solid #dee2e6; border-radius:20px;
  padding:.25rem .8rem; font-size:.75rem; color:#666; transition:all .3s;
  display:inline-flex; align-items:center; gap:.3rem;
}
.step-item.active{background:#0d6efd; color:#fff; border-color:#0d6efd}
.step-item i{font-size:.8rem}

/* Critical points */
.pc{border-radius:8px; padding:.3rem .7rem; margin-bottom:.3rem; font-size:.85rem}
.pc.max{background:rgba(46,125,50,.08); border:1px solid rgba(46,125,50,.2)}
.pc.min{background:rgba(255,152,0,.1); border:1px solid rgba(255,152,0,.25)}

footer{
  text-align:center; padding:2rem; color:#999; font-size:.8rem;
  border-top:1px solid rgba(0,0,0,.05); margin-top:2rem;
}

/* Spinner */
.spinner-overlay{display:none; position:fixed; inset:0; background:rgba(255,255,255,.7); z-index:9999; align-items:center; justify-content:center}
.spinner-overlay.show{display:flex}
.spinner-box{background:#fff; padding:2rem 3rem; border-radius:16px; text-align:center; box-shadow:0 8px 40px rgba(0,0,0,.12)}
.spinner-border{width:3rem; height:3rem}

/* Animaciones */
.fade-in{animation:fadeIn .5s ease forwards}
@keyframes fadeIn{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
.fade-in-d1{animation-delay:.1s;opacity:0}
.fade-in-d2{animation-delay:.2s;opacity:0}
.fade-in-d3{animation-delay:.3s;opacity:0}
.fade-in-d4{animation-delay:.4s;opacity:0}

/* Responsive */
@media(max-width:576px){
  .header h1{font-size:1.8rem}
  .kpi-valor{font-size:1.2rem}
  .banner-result .big-number{font-size:1.5rem}
}
</style>
</head>
<body>

<!-- Spinner -->
<div class="spinner-overlay" id="spinner">
  <div class="spinner-box">
    <div class="spinner-border text-primary mb-3" role="status"></div>
    <div class="fw-bold">Optimizando...</div>
    <div class="small text-muted">Procesando derivadas y puntos criticos</div>
  </div>
</div>

<!-- Header -->
<div class="header">
  <div class="container">
    <div class="icon-top"><i class="bi bi-graph-up-arrow"></i></div>
    <h1>OptiPrice SaaS</h1>
    <p class="sub">Usted ingresa sus costos y metas &mdash; el sistema deriva y optimiza</p>
  </div>
</div>

<div class="container">
  <div class="row justify-content-center">
    <div class="col-lg-9">

      <!-- FORMULARIO -->
      <div class="card-glass fade-in">
        <div class="card-hd"><i class="bi bi-sliders2 text-primary"></i> Parametros del negocio</div>
        <div class="p-4">
          <form method="POST" id="form-opt">

            <div class="row g-3 mb-4">
              <div class="col-md-6">
                <label class="fw-semibold mb-1"><i class="bi bi-building text-danger me-1"></i> Costo Fijo</label>
                <div class="input-group">
                  <span class="input-group-text bg-white fw-bold">$</span>
                  <input type="text" class="form-control input-premium" name="costo_fijo"
                         placeholder="ej: 2000" value="{{ request.form.get('costo_fijo', '') }}" required>
                </div>
                <div class="form-text mt-1"><i class="bi bi-info-circle"></i> Rentas, sueldos administrativos, costos fijos</div>
              </div>
              <div class="col-md-6">
                <label class="fw-semibold mb-1"><i class="bi bi-box-seam text-warning me-1"></i> Costo Variable Unitario</label>
                <div class="input-group">
                  <span class="input-group-text bg-white fw-bold">$</span>
                  <input type="text" class="form-control input-premium" name="costo_variable"
                         placeholder="ej: 30" value="{{ request.form.get('costo_variable', '') }}" required>
                </div>
                <div class="form-text mt-1"><i class="bi bi-info-circle"></i> Materiales, mano de obra directa por unidad</div>
              </div>
            </div>

            <h6 class="fw-bold mb-2"><i class="bi bi-bar-chart-fill text-success me-1"></i> Metas de Venta</h6>
            <p class="text-muted small mb-2"><i class="bi bi-question-circle"></i> Estime: ¿a qué precio y cuántas unidades espera vender?</p>
            <table class="table tabla-meta mb-2">
              <thead><tr><th style="width:42%"><i class="bi bi-tags me-1"></i>Precio estimado ($)</th><th style="width:42%"><i class="bi bi-cart me-1"></i>Cantidad estimada</th><th style="width:16%"></th></tr></thead>
              <tbody id="tabla-metas">
                {% for i in range(metas|length) %}
                <tr>
                  <td><input type="text" name="mp{{i}}" value="{{ metas[i][0] }}" placeholder="ej: 50" class="text-center"></td>
                  <td><input type="text" name="mq{{i}}" value="{{ metas[i][1] }}" placeholder="ej: 100" class="text-center"></td>
                  <td class="text-center">
                    {% if loop.index > 2 %}
                    <button type="button" class="btn btn-sm btn-outline-danger border-0" onclick="this.closest('tr').remove()"><i class="bi bi-x-lg"></i></button>
                    {% endif %}
                  </td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
            <button type="button" class="btn-add mb-3" onclick="agregarFila()"><i class="bi bi-plus-lg me-1"></i>Agregar meta</button>
            <input type="hidden" name="n_metas" value="{{ metas|length }}" id="n-metas">

            <button type="submit" class="btn btn-opt w-100" onclick="document.getElementById('spinner').classList.add('show')">
              <i class="bi bi-cpu"></i> Optimizar
              <i class="bi bi-chevron-double-right"></i>
            </button>
          </form>
        </div>
      </div>

      <!-- RESULTADOS -->
      {% if resultado %}

        {% if resultado.exito %}
        <!-- Banner principal -->
        <div class="card-glass fade-in fade-in-d1">
          <div class="card-hd"><i class="bi bi-trophy text-success"></i> Reporte de optimizacion</div>
          <div class="p-4">

            <div class="banner-result">
              <div class="small text-muted text-uppercase fw-bold mb-1">Resultado optimo</div>
              <h4>Produzca <span class="big-number">{{ resultado.cantidad_optima }}</span> unidades</h4>
              <p class="mb-0 mt-1" style="font-size:1.1rem">
                a un precio de <strong>${{ resultado.precio_optimo }}</strong> c/u
                &rarr; Utilidad maxima de
                <strong class="util-val" style="color:{% if resultado.utilidad_maxima >= 0 %}#2e7d32{% else %}#c62828{% endif %}">
                  ${{ resultado.utilidad_maxima }}
                </strong>
              </p>
            </div>

            <!-- Timeline pasos -->
            <div class="step-line">
              <span class="step-item active"><i class="bi bi-currency-dollar"></i> C(x)</span>
              <span class="step-item active"><i class="bi bi-graph-up"></i> P(x)</span>
              <span class="step-item active"><i class="bi bi-plus-circle"></i> I(x)</span>
              <span class="step-item active"><i class="bi bi-dash-circle"></i> U(x)</span>
              <span class="step-item active"><i class="bi bi-diagram-2"></i> U'(x)=0</span>
              <span class="step-item active"><i class="bi bi-check-circle"></i> U''(x)&lt;0</span>
            </div>

            <!-- KPIs -->
            <div class="row g-2 mb-4">
              <div class="col-md-3 col-6"><div class="kpi-card">
                <div class="kpi-icon text-primary"><i class="bi bi-boxes"></i></div>
                <div class="kpi-label">Cantidad optima</div>
                <div class="kpi-valor">{{ resultado.cantidad_optima }}</div>
                <div class="kpi-unit">unidades</div>
              </div></div>
              <div class="col-md-3 col-6"><div class="kpi-card">
                <div class="kpi-icon text-success"><i class="bi bi-tag"></i></div>
                <div class="kpi-label">Precio optimo</div>
                <div class="kpi-valor">${{ resultado.precio_optimo }}</div>
                <div class="kpi-unit">c/u</div>
              </div></div>
              <div class="col-md-3 col-6"><div class="kpi-card">
                <div class="kpi-icon" style="color:{% if resultado.utilidad_maxima >= 0 %}#2e7d32{% else %}#c62828{% endif %}"><i class="bi bi-cash-stack"></i></div>
                <div class="kpi-label">Utilidad maxima</div>
                <div class="kpi-valor" style="color:{% if resultado.utilidad_maxima >= 0 %}#2e7d32{% else %}#c62828{% endif %}">${{ resultado.utilidad_maxima }}</div>
                <div class="kpi-unit">proyectada</div>
              </div></div>
              <div class="col-md-3 col-6"><div class="kpi-card">
                <div class="kpi-icon text-info"><i class="bi bi-arrow-left-right"></i></div>
                <div class="kpi-label">Margen unitario</div>
                <div class="kpi-valor">${{ resultado.margen_unitario }}</div>
                <div class="kpi-unit">precio - costo marginal</div>
              </div></div>
            </div>

            <!-- Chart.js grafico -->
            <div class="mb-4">
              <h6 class="fw-semibold mb-2"><i class="bi bi-graph-down text-primary"></i> Curva de Utilidad U(x)</h6>
              <div style="position:relative; height:260px">
                <canvas id="chartUtilidad"></canvas>
              </div>
              <div class="text-center small text-muted mt-1">
                <i class="bi bi-dot text-primary"></i> U(x) &nbsp;
                <i class="bi bi-dot text-success"></i> Maximo en x = {{ resultado.cantidad_optima }}, U = ${{ resultado.utilidad_maxima }}
              </div>
            </div>

            <hr>

            <!-- Detalles tecnicos colapsables -->
            <div class="accordion" id="detallesAccordion">
              <div class="accordion-item border-0">
                <h2 class="accordion-header">
                  <button class="accordion-button collapsed bg-light fw-semibold py-2" type="button" data-bs-toggle="collapse" data-bs-target="#detallesCollapse">
                    <i class="bi bi-gear me-2"></i> Detalles tecnicos del modelo
                  </button>
                </h2>
                <div id="detallesCollapse" class="accordion-collapse collapse" data-bs-parent="#detallesAccordion">
                  <div class="accordion-body px-0">
                    <div class="row">
                      <div class="col-md-6">
                        <h6 class="label-sm text-muted"><i class="bi bi-calculator me-1"></i> Modelo construido internamente</h6>
                        <div class="mono-box">C(x) = {{ resultado.C }}</div><br>
                        <div class="mono-box">P(x) = {{ resultado.P }}</div><br>
                        <div class="mono-box">I(x) = {{ resultado.I }}</div><br>
                        <div class="mono-box">U(x) = {{ resultado.U }}</div>
                      </div>
                      <div class="col-md-6">
                        <h6 class="label-sm text-muted"><i class="bi bi-diagram-2 me-1"></i> Derivadas del modelo</h6>
                        <div class="mono-box">U'(x) = {{ resultado.U_prima }}</div><br>
                        <div class="mono-box">U''(x) = {{ resultado.U_biprima }}</div><br>
                        <h6 class="label-sm text-muted mt-2"><i class="bi bi-bullseye me-1"></i> Puntos criticos (U'(x)=0)</h6>
                        {% for pc in resultado.puntos_criticos %}
                        <div class="pc {{ 'max' if pc.tipo == 'MAXIMO' else 'min' }}">
                          <strong>x = {{ pc.valor }}</strong> &nbsp;|&nbsp;
                          U'' = {{ pc.segunda_derivada }} &nbsp;|&nbsp;
                          <strong>{{ pc.tipo }}</strong>
                        </div>
                        {% endfor %}
                      </div>
                    </div>
                    <div class="row mt-2 text-center small">
                      <div class="col-4"><span class="text-muted"><i class="bi bi-cash"></i> Ingreso:</span> <strong>${{ resultado.ingreso_total }}</strong></div>
                      <div class="col-4"><span class="text-muted"><i class="bi bi-wallet2"></i> Costo:</span> <strong>${{ resultado.costo_total }}</strong></div>
                      <div class="col-4"><span class="text-muted"><i class="bi bi-graph-up"></i> Costo Marginal:</span> <strong>${{ resultado.costo_marginal }}</strong></div>
                    </div>
                    <div class="text-center small text-success fw-bold mt-2">
                      <i class="bi bi-check-circle-fill"></i>
                      U''(x) = {{ resultado.segunda_derivada }} &lt; 0 &rarr; Maximo global confirmado
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>

        {% else %}
        <!-- Diagnostico -->
        <div class="card-glass fade-in fade-in-d1">
          <div class="card-hd" style="color:#f9a825"><i class="bi bi-exclamation-triangle-fill" style="color:#f9a825"></i> Diagnostico</div>
          <div class="p-4">
            <div class="banner-diag">{{ resultado.mensaje }}</div>
            {% if resultado.puntos %}
            <div class="mt-2 small"><strong>Puntos encontrados:</strong> {{ resultado.puntos|join(', ') }}</div>
            {% endif %}
            <hr>
            <div class="mono-box">C(x) = {{ resultado.C }}</div><br>
            <div class="mono-box">P(x) = {{ resultado.P }}</div><br>
            <div class="mono-box">U'(x) = {{ resultado.U_prima }}</div><br>
            <div class="mono-box">U''(x) = {{ resultado.U_biprima }}</div>
          </div>
        </div>
        {% endif %}

      {% endif %}

      {% if error %}
      <div class="card-glass">
        <div class="p-4">
          <div class="banner-diag" style="background:linear-gradient(135deg,#ffebee,#ffcdd2);border-left-color:#c62828">
            <i class="bi bi-x-circle-fill me-1" style="color:#c62828"></i> {{ error }}
          </div>
        </div>
      </div>
      {% endif %}

    </div>
  </div>
</div>

<footer>
  <i class="bi bi-cpu me-1"></i> OptiPrice SaaS &mdash; Clase CalculadoraPrecios &mdash;
  U(x) = x&middot;P(x) &minus; C(x) &rarr; U'(x)=0 &rarr; max
</footer>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script>
function agregarFila() {
  const tb = document.getElementById('tabla-metas');
  const n = tb.querySelectorAll('tr').length;
  const tr = document.createElement('tr');
  tr.innerHTML = `<td><input type="text" name="mp${n}" placeholder="ej: 45" class="text-center"></td>
                  <td><input type="text" name="mq${n}" placeholder="ej: 150" class="text-center"></td>
                  <td class="text-center"><button type="button" class="btn btn-sm btn-outline-danger border-0" onclick="this.closest('tr').remove()"><i class="bi bi-x-lg"></i></button></td>`;
  tb.appendChild(tr);
}

// Oculta spinner al cargar
window.addEventListener('load', function(){
  setTimeout(function(){ document.getElementById('spinner').classList.remove('show'); }, 300);
});

// Grafico Chart.js
{% if resultado and resultado.exito and resultado.chart_x %}
const ctx = document.getElementById('chartUtilidad').getContext('2d');
new Chart(ctx, {
  type: 'line',
  data: {
    labels: {{ resultado.chart_x|tojson }},
    datasets: [{
      label: 'U(x)',
      data: {{ resultado.chart_y|tojson }},
      borderColor: '#0d6efd',
      backgroundColor: 'rgba(13,110,253,.08)',
      fill: true,
      tension: .3,
      pointRadius: 0,
      borderWidth: 3,
    }, {
      label: 'Maximo',
      data: [{{ resultado.chart_max_x }}, {{ resultado.chart_max_y }}],
      pointRadius: 8,
      pointBackgroundColor: '#2e7d32',
      pointBorderColor: '#fff',
      pointBorderWidth: 3,
      showLine: false,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: function(ctx) {
            if (ctx.datasetIndex === 1) return 'Maximo: x=' + {{ resultado.chart_max_x }} + ', U=$' + {{ resultado.chart_max_y }};
            return 'x=' + ctx.raw.x + ', U=$' + ctx.raw.y;
          }
        }
      }
    },
    scales: {
      x: {
        title: { display: true, text: 'Cantidad (x)', font: {size: 11} },
        grid: { color: 'rgba(0,0,0,.04)' }
      },
      y: {
        title: { display: true, text: 'Utilidad $', font: {size: 11} },
        grid: { color: 'rgba(0,0,0,.04)' }
      }
    }
  }
});
{% endif %}
</script>
</body>
</html>
"""


@app.route('/', methods=['GET', 'POST'])
def index():
    resultado = None
    error = None
    metas_default = [['', ''], ['', '']]

    if request.method == 'POST':
        try:
            cf = float(request.form.get('costo_fijo', 0))
            cv = float(request.form.get('costo_variable', 0))
            n = int(request.form.get('n_metas', 2))
            pares_metas = []
            for i in range(n + 10):
                p = request.form.get(f'mp{i}', '').strip()
                q = request.form.get(f'mq{i}', '').strip()
                if p and q:
                    pares_metas.append((float(p), float(q)))
            if not pares_metas:
                pares_metas = [(0, 0), (0, 0)]
            metas_default = [[str(p), str(q)] for p, q in pares_metas]
            calc = CalculadoraPrecios()
            calc.registrar(cf, cv, pares_metas)
            resultado = calc.optimizar()
        except (ValueError, RuntimeError, Exception) as e:
            error = str(e)

    return render_template_string(HTML, resultado=resultado, error=error, metas=metas_default)


if __name__ == '__main__':
    print("=" * 55)
    print("  OptiPrice SaaS v3.0")
    print("  http://127.0.0.1:5000")
    print("=" * 55)
    app.run(debug=True, host='127.0.0.1', port=5000)
