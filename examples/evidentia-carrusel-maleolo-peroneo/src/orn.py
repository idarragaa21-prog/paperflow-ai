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

def ankle_anatomy(navy=NAVY, gold=GOLD, ink="#2B3A57"):
    """Stylized labeled AP ankle mortise: tibia, fibula, talus, syndesmosis, deltoid."""
    boneF="#E9E6DD"; taloF="#DCE2EC"
    return f'''<svg viewBox="0 0 620 560" fill="none" font-family="Montserrat, sans-serif">
      <!-- TIBIA -->
      <path d="M250 20 C244 90 246 180 252 250 L252 300 C252 320 246 336 232 348
               L214 360 C205 366 205 380 214 388 L250 392 C280 396 320 396 350 392
               L360 388 C372 382 372 366 360 358 L352 300 L352 250
               C356 180 356 90 350 20 Z" fill="{boneF}" stroke="{navy}" stroke-width="3"/>
      <path d="M252 296 C280 308 322 308 352 296" stroke="{navy}" stroke-width="2.4" fill="none"/>
      <!-- FIBULA (lateral malleolus, lower) -->
      <path d="M392 46 C400 130 400 220 396 280 C394 316 388 350 378 372
               C372 386 376 402 388 410 L404 404 C416 396 420 372 420 348
               C424 300 424 210 420 130 C418 96 414 66 408 46 Z"
            fill="{boneF}" stroke="{navy}" stroke-width="3"/>
      <!-- TALUS dome -->
      <path d="M214 396 C240 384 330 384 360 396 C384 406 392 428 384 448
               C350 470 260 470 224 448 C210 430 200 410 214 396 Z"
            fill="{taloF}" stroke="{navy}" stroke-width="3"/>
      <!-- syndesmosis hatch (gold) -->
      <g stroke="{gold}" stroke-width="2.6" stroke-linecap="round">
        <path d="M356 250 L392 244 M356 264 L392 258 M357 278 L393 272 M359 292 L392 286"/>
      </g>
      <!-- deltoid fan (gold) medial -->
      <g stroke="{gold}" stroke-width="2.6" fill="none" stroke-linecap="round">
        <path d="M226 356 C206 384 200 414 210 440"/>
        <path d="M232 360 C222 390 222 418 236 442"/>
        <path d="M242 362 C244 392 254 418 272 438"/>
      </g>
      <!-- labels + gold leaders -->
      <g stroke="{gold}" stroke-width="1.6"><line x1="470" y1="150" x2="410" y2="150"/></g>
      <circle cx="470" cy="150" r="3.5" fill="{gold}"/>
      <text x="482" y="145" font-size="19" font-weight="800" fill="{navy}" letter-spacing="1">PERONÉ</text>
      <text x="482" y="169" font-size="14" font-weight="600" fill="{ink}" letter-spacing="1">Columna lateral</text>

      <g stroke="{gold}" stroke-width="1.6"><line x1="150" y1="120" x2="248" y2="120"/></g>
      <circle cx="150" cy="120" r="3.5" fill="{gold}"/>
      <text x="30" y="115" font-size="19" font-weight="800" fill="{navy}" letter-spacing="1">TIBIA</text>
      <text x="30" y="139" font-size="14" font-weight="600" fill="{ink}" letter-spacing="1">Maléolo medial</text>

      <g stroke="{gold}" stroke-width="1.6"><line x1="486" y1="270" x2="378" y2="268"/></g>
      <circle cx="486" cy="270" r="3.5" fill="{gold}"/>
      <text x="498" y="266" font-size="16" font-weight="800" fill="{gold}" letter-spacing="1">SINDESMOSIS</text>
      <text x="498" y="288" font-size="13" font-weight="600" fill="{ink}">tibia–peroné</text>

      <g stroke="{gold}" stroke-width="1.6"><line x1="126" y1="420" x2="214" y2="424"/></g>
      <circle cx="126" cy="420" r="3.5" fill="{gold}"/>
      <text x="16" y="416" font-size="16" font-weight="800" fill="{gold}" letter-spacing="1">DELTOIDEO</text>
      <text x="16" y="438" font-size="13" font-weight="600" fill="{ink}">profundo · LTTPP</text>

      <g stroke="{gold}" stroke-width="1.6"><line x1="470" y1="440" x2="360" y2="432"/></g>
      <circle cx="470" cy="440" r="3.5" fill="{gold}"/>
      <text x="482" y="436" font-size="19" font-weight="800" fill="{navy}" letter-spacing="1">ASTRÁGALO</text>
      <text x="482" y="460" font-size="14" font-weight="600" fill="{ink}">en la mortaja</text>
    </svg>'''
