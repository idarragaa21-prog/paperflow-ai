# -*- coding: utf-8 -*-
"""
Geração de gráficas baseadas em evidência para a apresentação de Artrite Séptica.
Todas as figuras são REDESENHADAS a partir de dados publicados (não reproduções
de figuras protegidas por direitos autorais). Fundo branco, estilo clínico limpo.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import os

ASSETS = os.path.join(os.path.dirname(__file__), "assets")
os.makedirs(ASSETS, exist_ok=True)

# ---- Paleta clínica ----
INK     = "#12324F"   # navy escuro
PRIMARY = "#1F6FB2"   # azul clínico
TEAL    = "#0E9AA7"   # verde-azulado
ALERT   = "#D64541"   # vermelho alerta
AMBER   = "#E1A140"   # âmbar
GREEN   = "#2E9E6B"   # verde
GRID    = "#E3E9EF"
TXT     = "#455A6B"
MUTE    = "#8A9BA8"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 15,
    "text.color": TXT,
    "axes.edgecolor": "#C9D4DC",
    "axes.labelcolor": TXT,
    "xtick.color": TXT,
    "ytick.color": TXT,
    "axes.linewidth": 1.0,
    "figure.dpi": 200,
})

DPI = 220


def _save(fig, name):
    path = os.path.join(ASSETS, name)
    fig.savefig(path, dpi=DPI, bbox_inches="tight", transparent=True, pad_inches=0.08)
    plt.close(fig)
    print("saved", name)


def _clean(ax, keep_left=False, keep_bottom=True):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if not keep_left:
        ax.spines["left"].set_visible(False)
    if not keep_bottom:
        ax.spines["bottom"].set_visible(False)
    ax.tick_params(length=0)


# 1) EPIDEMIOLOGIA — incidência por grupo de risco (por 100.000/ano)
def chart_epidemiologia():
    grupos = ["População\ngeral", "Idosos\n(>80 anos)", "Artrite\nreumatoide", "AR + prótese\narticular"]
    valores = [6, 18, 30, 70]  # por 100.000/ano (aprox., Mathews 2010)
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    colors = [PRIMARY, PRIMARY, AMBER, ALERT]
    bars = ax.bar(grupos, valores, color=colors, width=0.62, zorder=3)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=GRID, zorder=0)
    _clean(ax, keep_left=False)
    ax.set_yticks([])
    ax.set_ylim(0, 82)
    for b, v in zip(bars, valores):
        ax.text(b.get_x()+b.get_width()/2, v+2.2, f"{v}", ha="center", va="bottom",
                fontsize=17, fontweight="bold", color=INK)
    ax.set_ylabel("Casos por 100.000 pessoas-ano", fontsize=13, color=MUTE)
    _save(fig, "epi_incidencia.png")


# 2) MICROBIOLOGIA — distribuição de agentes (artrite séptica nativa não gonocócica)
def chart_microbiologia():
    labels = ["S. aureus", "Estreptococos", "Bacilos Gram-\nnegativos",
              "Estafilococos coag.\nnegativos", "Cultura\nnegativa", "Outros"]
    vals = [44, 20, 12, 8, 11, 5]
    colors = [ALERT, PRIMARY, TEAL, AMBER, MUTE, "#C4CED6"]
    fig, ax = plt.subplots(figsize=(8.8, 4.7))
    y = np.arange(len(labels))[::-1]
    bars = ax.barh(y, vals, color=colors, height=0.62, zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=13.5)
    ax.set_xlim(0, 52)
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=GRID, zorder=0)
    _clean(ax)
    ax.set_xticks([])
    for b, v in zip(bars, vals):
        ax.text(v+1, b.get_y()+b.get_height()/2, f"{v}%", va="center", ha="left",
                fontsize=15, fontweight="bold", color=INK)
    _save(fig, "microbiologia.png")


# 3) ARTICULAÇÕES ACOMETIDAS — distribuição (%)
def chart_articulacoes():
    labels = ["Joelho", "Quadril", "Tornozelo", "Ombro", "Punho", "Cotovelo", "Outras"]
    vals = [45, 15, 9, 8, 7, 6, 10]
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    colors = [PRIMARY]*len(labels)
    colors[0] = ALERT
    bars = ax.bar(labels, vals, color=colors, width=0.66, zorder=3)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=GRID, zorder=0)
    _clean(ax)
    ax.set_yticks([])
    ax.set_ylim(0, 52)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v+1.4, f"{v}%", ha="center", va="bottom",
                fontsize=14.5, fontweight="bold", color=INK)
    _save(fig, "articulacoes.png")


# 4) LÍQUIDO SINOVIAL — leucócitos por categoria (escala log)
def chart_liquido_sinovial():
    cats = ["Normal", "Não\ninflamatório", "Inflamatório", "Séptico"]
    lo = [0.06, 0.2, 2, 50]      # x1000 cel/mm3
    hi = [0.2, 2, 50, 150]
    colors = [GREEN, TEAL, AMBER, ALERT]
    fig, ax = plt.subplots(figsize=(9.0, 4.4))
    y = np.arange(len(cats))[::-1]
    for yi, l, h, c in zip(y, lo, hi, colors):
        ax.plot([l, h], [yi, yi], color=c, lw=13, solid_capstyle="round", zorder=3)
    ax.set_yticks(y)
    ax.set_yticklabels(cats, fontsize=14)
    ax.set_xscale("log")
    ax.set_xlim(0.05, 200)
    ax.set_xticks([0.1, 1, 10, 100])
    ax.set_xticklabels(["100", "1.000", "10.000", "100.000"], fontsize=12)
    ax.set_xlabel("Leucócitos no líquido sinovial (cel/mm³)", fontsize=13, color=MUTE)
    ax.axvline(50, color=ALERT, ls="--", lw=1.4, zorder=2)
    ax.text(52, 3.35, "≥ 50.000\nalta suspeita", color=ALERT, fontsize=11.5, va="top", fontweight="bold")
    ax.set_axisbelow(True)
    ax.xaxis.grid(True, color=GRID, zorder=0)
    _clean(ax)
    _save(fig, "liquido_sinovial.png")


# 5) CRITÉRIOS DE KOCHER — probabilidade de artrite séptica por nº de critérios
def chart_kocher():
    n = ["0", "1", "2", "3", "4"]
    prob = [0.2, 3, 40, 93, 99]
    colors = [GREEN, GREEN, AMBER, ALERT, ALERT]
    fig, ax = plt.subplots(figsize=(8.8, 4.7))
    bars = ax.bar(n, prob, color=colors, width=0.64, zorder=3)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=GRID, zorder=0)
    _clean(ax)
    ax.set_yticks([])
    ax.set_ylim(0, 112)
    for b, v in zip(bars, prob):
        t = f"{v}%" if v >= 1 else "<1%"
        ax.text(b.get_x()+b.get_width()/2, v+2.5, t, ha="center", va="bottom",
                fontsize=16, fontweight="bold", color=INK)
    ax.set_xlabel("Número de critérios preditores presentes", fontsize=13, color=MUTE)
    ax.set_ylabel("Probabilidade de artrite séptica", fontsize=12.5, color=MUTE)
    _save(fig, "kocher.png")


# 6) PROGNÓSTICO — desfechos
def chart_prognostico():
    labels = ["Mortalidade", "Sequela\nfuncional", "Osteomielite\nsecundária"]
    vals = [10, 40, 8]
    colors = [ALERT, AMBER, PRIMARY]
    fig, ax = plt.subplots(figsize=(7.8, 4.4))
    bars = ax.bar(labels, vals, color=colors, width=0.6, zorder=3)
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=GRID, zorder=0)
    _clean(ax)
    ax.set_yticks([])
    ax.set_ylim(0, 52)
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v+1.4, f"~{v}%", ha="center", va="bottom",
                fontsize=16, fontweight="bold", color=INK)
    _save(fig, "prognostico.png")


if __name__ == "__main__":
    chart_epidemiologia()
    chart_microbiologia()
    chart_articulacoes()
    chart_liquido_sinovial()
    chart_kocher()
    chart_prognostico()
    print("OK")
