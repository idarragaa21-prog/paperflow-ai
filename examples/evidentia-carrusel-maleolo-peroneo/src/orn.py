# -*- coding: utf-8 -*-
"""EVIDENTIA brand ornaments (SVG) matching the real @evidentia_co carousels."""

NAVY="#17294D"; NAVY2="#22406E"; GOLD="#BE9B49"; GOLD2="#D8BE7A"

def dotgrid(nx, ny, gap=14, r=2.6, color=GOLD, op=0.85):
    dots=[]
    for i in range(nx):
        for j in range(ny):
            dots.append(f'<circle cx="{i*gap+r}" cy="{j*gap+r}" r="{r}"/>')
    w=(nx-1)*gap+2*r; h=(ny-1)*gap+2*r
    return f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" fill="{color}" opacity="{op}">{"".join(dots)}</svg>'

def bulb_magnifier(color=GOLD, sw=3.0):
    # lightbulb + magnifier — the EVIDENTIA "research/idea" mark
    return f'''<svg viewBox="0 0 120 120" fill="none" stroke="{color}" stroke-width="{sw}"
      stroke-linecap="round" stroke-linejoin="round">
      <path d="M60 20 C42 20 30 33 30 49 C30 60 37 67 42 73 C45 77 46 81 46 86 H74 C74 81 75 77 78 73 C83 67 90 60 90 49 C90 33 78 20 60 20 Z"/>
      <path d="M48 92 H72 M50 99 H70"/>
      <path d="M60 40 C54 40 50 44 50 50 M60 40 C66 40 70 44 70 50" opacity="0.9"/>
      <path d="M60 40 V63" opacity="0.9"/>
      <!-- rays -->
      <path d="M60 10 V4 M35 16 L31 11 M85 16 L89 11 M22 38 L16 35 M98 38 L104 35" opacity="0.85"/>
      <!-- magnifier -->
      <circle cx="82" cy="82" r="15" stroke-width="{sw}"/>
      <path d="M93 93 L104 104" stroke-width="{sw+1}"/>
    </svg>'''

def diamond_rule(color=GOLD, w=360):
    return f'''<svg viewBox="0 0 {w} 20" width="{w}" height="20" fill="none" stroke="{color}" stroke-width="1.4">
      <line x1="0" y1="10" x2="{w/2-16}" y2="10"/>
      <line x1="{w/2+16}" y1="10" x2="{w}" y2="10"/>
      <rect x="{w/2-6}" y="4" width="12" height="12" transform="rotate(45 {w/2} 10)" fill="{color}" stroke="none"/>
    </svg>'''

def laurel_crest(color=GOLD, navy=NAVY):
    # small shield + laurel + E (header emblem)
    return f'''<svg viewBox="0 0 120 120" fill="none">
      <path d="M60 14 L92 24 V56 C92 82 78 98 60 106 C42 98 28 82 28 56 V24 Z"
        fill="{navy}" stroke="{color}" stroke-width="2"/>
      <text x="60" y="74" font-family="Playfair Display, serif" font-size="46" font-weight="800"
        fill="{color}" text-anchor="middle">E</text>
      <g stroke="{color}" stroke-width="2" fill="none" stroke-linecap="round">
        <path d="M20 44 C10 52 8 66 12 80"/>
        <path d="M20 50 l-8 2 M18 60 l-8 3 M18 70 l-7 4 M20 79 l-6 4"/>
        <path d="M100 44 C110 52 112 66 108 80"/>
        <path d="M100 50 l8 2 M102 60 l8 3 M102 70 l7 4 M100 79 l6 4"/>
      </g>
    </svg>'''
