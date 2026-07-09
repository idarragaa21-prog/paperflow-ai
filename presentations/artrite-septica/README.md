# Artrite Séptica — do básico ao avançado

Apresentação profissional (pt-BR, 16:9, fundo branco) sobre artrite séptica,
do básico ao avançado, com base em literatura indexada recente e diretrizes.

- **Autor:** Diego Alejandro Idárraga — R2 Ortopedia e Traumatologia,
  Hospital Municipal Barata Ribeiro, Rio de Janeiro.
- **Arquivo final:** `Artrite_Septica_Diego_Idarraga.pptx` (30 slides).

## Conteúdo (30 slides)

Fundamentos (definição, epidemiologia, classificação) · microbiologia e
fisiopatologia · quadro clínico e fatores de risco · diagnóstico (marcadores
séricos, líquido sinovial com razões de verossimilhança, imagem) · algoritmo
diagnóstico do adulto · artrite séptica pediátrica (critérios de Kocher/Caird)
e algoritmo · diagnóstico diferencial · tratamento (princípios,
antibioticoterapia empírica e dirigida, drenagem) e algoritmo cirúrgico ·
cenários avançados (artrite gonocócica, infecção de prótese — PJI) ·
complicações, prognóstico e mensagens-chave · referências.

## Sobre as figuras

Todas as gráficas e algoritmos foram **redesenhados** a partir de dados
publicados (valores, percentuais e limiares diagnósticos), não sendo
reproduções de figuras protegidas por direitos autorais. As faixas de
percentual (agentes, articulações, incidência) são apresentadas como
intervalos canônicos das fontes citadas (Mathews *Lancet* 2010; BSR 2006).
As referências verificadas constam no último slide.

## Como reconstruir

```bash
pip install python-pptx matplotlib Pillow
python3 charts.py       # gera as figuras em assets/
python3 build_deck.py   # gera o .pptx
```

## Estrutura

| Arquivo | Função |
|---|---|
| `build_deck.py` | Monta a apresentação (30 slides) |
| `deck_helpers.py` | Paleta, layout e helpers de forma/fluxograma |
| `charts.py` | Gera as gráficas baseadas em evidência (`assets/`) |
| `assets/` | Figuras PNG usadas nos slides |
| `Artrite_Septica_Diego_Idarraga.pptx` | Apresentação final |
