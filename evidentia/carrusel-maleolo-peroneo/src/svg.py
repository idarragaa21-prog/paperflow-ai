# -*- coding: utf-8 -*-
"""Reusable editorial medical SVG line-art motifs for EVIDENTIA carousel."""

# All motifs use stroke="currentColor" so slide CSS controls the color.

def mortise(op=1.0, sw=2.2):
    """AP ankle mortise: tibia + medial malleolus, fibula + lateral malleolus, talar dome."""
    return f'''<svg viewBox="0 0 260 360" fill="none" stroke="currentColor" stroke-width="{sw}"
      stroke-linecap="round" stroke-linejoin="round" opacity="{op}">
      <!-- tibia shaft + medial malleolus -->
      <path d="M96 8 C90 70 92 150 96 210 C99 250 96 268 84 286 C74 300 70 314 78 326"/>
      <path d="M150 8 C156 70 156 150 152 208"/>
      <!-- distal tibia plafond -->
      <path d="M96 258 C112 268 138 268 152 258"/>
      <!-- fibula shaft + lateral malleolus -->
      <path d="M182 22 C190 90 190 170 186 226 C184 258 180 286 170 304 C164 316 168 330 178 338"/>
      <path d="M214 22 C210 96 210 176 206 236 C205 270 202 300 196 316"/>
      <!-- talar dome -->
      <path d="M96 300 C112 286 150 286 170 300 C184 310 188 328 182 344 C150 356 120 356 90 344 C82 330 84 312 96 300"/>
      <!-- syndesmosis hatch -->
      <path d="M156 214 L182 210 M156 226 L182 222 M158 238 L184 234" stroke-width="{sw*0.7}"/>
    </svg>'''

def ring(op=1.0, sw=2.2):
    """Ankle 'ring' concept: circle broken at points, labelled quadrants."""
    return f'''<svg viewBox="0 0 300 300" fill="none" stroke="currentColor" stroke-width="{sw}"
      stroke-linecap="round" opacity="{op}">
      <circle cx="150" cy="150" r="120" stroke-dasharray="6 10" opacity="0.45"/>
      <path d="M150 30 A120 120 0 0 1 270 150"/>
      <path d="M270 150 A120 120 0 0 1 150 270" opacity="0.4"/>
      <path d="M150 270 A120 120 0 0 1 30 150"/>
      <path d="M30 150 A120 120 0 0 1 150 30" opacity="0.4"/>
      <circle cx="150" cy="30" r="6" fill="currentColor" stroke="none"/>
      <circle cx="270" cy="150" r="6" fill="currentColor" stroke="none"/>
      <circle cx="150" cy="270" r="6" fill="currentColor" stroke="none"/>
      <circle cx="30" cy="150" r="6" fill="currentColor" stroke="none"/>
    </svg>'''

def deltoid(op=1.0, sw=2.2):
    """Medial deltoid ligament fan under the medial malleolus."""
    return f'''<svg viewBox="0 0 260 320" fill="none" stroke="currentColor" stroke-width="{sw}"
      stroke-linecap="round" stroke-linejoin="round" opacity="{op}">
      <path d="M120 20 C114 80 116 150 122 196 C126 224 120 240 108 252"/>
      <path d="M170 20 C176 80 176 150 172 200"/>
      <path d="M122 196 C138 206 160 206 172 196"/>
      <!-- deltoid fan fascicles -->
      <path d="M118 208 C96 236 84 268 92 300" stroke-width="{sw*0.85}"/>
      <path d="M128 210 C118 244 116 276 128 302" stroke-width="{sw*0.85}"/>
      <path d="M140 210 C142 246 150 278 168 300" stroke-width="{sw*0.85}"/>
      <path d="M150 206 C164 236 184 262 204 280" stroke-width="{sw*0.85}"/>
      <!-- talus/calc base -->
      <path d="M78 300 C120 316 176 314 214 296" opacity="0.5"/>
    </svg>'''

def plate(op=1.0, sw=2.2):
    """Lateral fibular plate with screws."""
    return f'''<svg viewBox="0 0 200 340" fill="none" stroke="currentColor" stroke-width="{sw}"
      stroke-linecap="round" stroke-linejoin="round" opacity="{op}">
      <!-- fibula -->
      <path d="M70 12 C82 90 82 190 76 250 C72 286 66 312 74 330"/>
      <path d="M104 12 C98 92 98 192 102 252 C104 286 108 308 104 326"/>
      <!-- fracture line -->
      <path d="M74 170 L104 150" stroke-dasharray="3 6"/>
      <!-- plate -->
      <rect x="112" y="70" width="26" height="210" rx="13"/>
      <!-- screws -->
      <line x1="112" y1="96" x2="70" y2="96"/>
      <line x1="112" y1="132" x2="66" y2="132"/>
      <line x1="112" y1="200" x2="70" y2="200"/>
      <line x1="112" y1="236" x2="70" y2="236"/>
      <line x1="112" y1="262" x2="72" y2="262"/>
      <circle cx="125" cy="96" r="5" fill="currentColor" stroke="none"/>
      <circle cx="125" cy="132" r="5" fill="currentColor" stroke="none"/>
      <circle cx="125" cy="200" r="5" fill="currentColor" stroke="none"/>
      <circle cx="125" cy="236" r="5" fill="currentColor" stroke="none"/>
      <circle cx="125" cy="262" r="5" fill="currentColor" stroke="none"/>
    </svg>'''

def pyramid(op=1.0, sw=2.2):
    """Evidence pyramid with the narrative-review tier highlighted."""
    return f'''<svg viewBox="0 0 300 260" fill="none" stroke="currentColor" stroke-width="{sw}"
      stroke-linecap="round" stroke-linejoin="round" opacity="{op}">
      <path d="M150 14 L214 74 L86 74 Z"/>
      <path d="M86 74 L214 74 L246 104 L54 104 Z"/>
      <path d="M54 104 L246 104 L278 134 L22 134 Z"/>
      <path d="M22 134 L278 134 L300 164 L0 164 Z" fill="currentColor" fill-opacity="0.10"/>
      <path d="M0 164 L300 164 L300 210 L0 210 Z"/>
      <line x1="150" y1="188" x2="150" y2="188"/>
    </svg>'''

def stress(op=1.0, sw=2.2):
    """Two mini mortise frames: stable vs unstable (medial clear space)."""
    def frame(x, gap):
        return f'''
        <rect x="{x}" y="20" width="120" height="150" rx="8" opacity="0.5"/>
        <path d="M{x+38} 34 C{x+34} 80 {x+36} 120 {x+40} 150" />
        <path d="M{x+62} 34 C{x+66} 80 {x+66} 120 {x+62} 150" opacity="0.5"/>
        <path d="M{x+80+gap} 40 C{x+84+gap} 90 {x+82+gap} 130 {x+78+gap} 158"/>
        <path d="M{x+40} 150 C{x+58} 162 {x+80+gap} 162 {x+96+gap} 150"/>
        '''
    return f'''<svg viewBox="0 0 300 200" fill="none" stroke="currentColor" stroke-width="{sw}"
      stroke-linecap="round" stroke-linejoin="round" opacity="{op}">
      {frame(10,2)}
      {frame(168,16)}
    </svg>'''

def checklist(op=1.0, sw=2.2):
    return f'''<svg viewBox="0 0 260 240" fill="none" stroke="currentColor" stroke-width="{sw}"
      stroke-linecap="round" stroke-linejoin="round" opacity="{op}">
      <rect x="14" y="24" width="26" height="26" rx="5"/>
      <path d="M20 37 l6 7 l10 -13"/>
      <line x1="58" y1="37" x2="240" y2="37" opacity="0.5"/>
      <rect x="14" y="84" width="26" height="26" rx="5"/>
      <path d="M20 97 l6 7 l10 -13"/>
      <line x1="58" y1="97" x2="240" y2="97" opacity="0.5"/>
      <rect x="14" y="144" width="26" height="26" rx="5"/>
      <path d="M20 157 l6 7 l10 -13"/>
      <line x1="58" y1="157" x2="240" y2="157" opacity="0.5"/>
      <rect x="14" y="204" width="26" height="26" rx="5"/>
      <path d="M20 217 l6 7 l10 -13"/>
      <line x1="58" y1="217" x2="240" y2="217" opacity="0.5"/>
    </svg>'''

MOTIFS = {
    "mortise": mortise, "ring": ring, "deltoid": deltoid, "plate": plate,
    "pyramid": pyramid, "stress": stress, "checklist": checklist,
}
