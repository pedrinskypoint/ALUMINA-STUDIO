"""Offline workshop calculations and element reference; no writes to workshop data."""
from __future__ import annotations
import html
import math
import re

# Rounded central values from CIAAW Abridged Standard Atomic Weights 2024.
ATOMIC = {'H':1.008,'Li':6.94,'B':10.81,'C':12.011,'O':15.999,'Na':22.990,'Mg':24.305,'Al':26.982,'Si':28.085,'P':30.974,'K':39.098,'Ca':40.078,'Ti':47.867,'Cr':51.996,'Mn':54.938,'Fe':55.845,'Co':58.933,'Ni':58.693,'Cu':63.546,'Zn':65.38,'Sr':87.62,'Zr':91.222,'Sn':118.71,'Ba':137.33,'Pb':207.2}
OXIDES = 'Li2O Na2O K2O MgO CaO SrO BaO ZnO PbO Al2O3 B2O3 SiO2 TiO2 ZrO2 SnO2 Fe2O3 FeO MnO MnO2 CoO NiO CuO Cr2O3 P2O5'.split()
FLUXES = set('Li2O Na2O K2O MgO CaO SrO BaO ZnO PbO'.split())
ELEMENT_SYMBOLS = 'H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og'.split()
ELEMENT_NAMES = 'Hidrógeno Helio Litio Berilio Boro Carbono Nitrógeno Oxígeno Flúor Neón Sodio Magnesio Aluminio Silicio Fósforo Azufre Cloro Argón Potasio Calcio Escandio Titanio Vanadio Cromo Manganeso Hierro Cobalto Níquel Cobre Zinc Galio Germanio Arsénico Selenio Bromo Kriptón Rubidio Estroncio Itrio Circonio Niobio Molibdeno Tecnecio Rutenio Rodio Paladio Plata Cadmio Indio Estaño Antimonio Telurio Yodo Xenón Cesio Bario Lantano Cerio Praseodimio Neodimio Prometio Samario Europio Gadolinio Terbio Disprosio Holmio Erbio Tulio Iterbio Lutecio Hafnio Tantalio Wolframio Renio Osmio Iridio Platino Oro Mercurio Talio Plomo Bismuto Polonio Astato Radón Francio Radio Actinio Torio Protactinio Uranio Neptunio Plutonio Americio Curio Berkelio Californio Einstenio Fermio Mendelevio Nobelio Lawrencio Rutherfordio Dubnio Seaborgio Bohrio Hassio Meitnerio Darmstadtio Roentgenio Copernicio Nihonio Flerovio Moscovio Livermorio Teneso Oganesón'.split()
ELEMENT_NOTES = {
    'Si': 'SiO₂ es un formador de red del vidrio; el cuarzo es una materia prima habitual.',
    'Al': 'Al₂O₃ interviene en la estructura y viscosidad del esmalte; lo aportan, entre otros, arcillas y feldespatos.',
    'B': 'B₂O₃ participa en vidrios y esmaltes borácicos. Su papel no equivale al de un fundente RO en la normalización Seger.',
}


def positive(value, label, zero=False):
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'Completá {label}.')
    if not math.isfinite(v) or v < 0 or (not zero and v == 0):
        raise ValueError(f'{label}: debe ser un número {"no negativo" if zero else "mayor que cero"}.')
    return v


def molecular_mass(formula):
    parts = re.findall(r'([A-Z][a-z]?)(\d*)', formula)
    if ''.join(a+n for a,n in parts) != formula or not parts:
        raise ValueError('Fórmula química no admitida.')
    try:
        return sum(ATOMIC[a] * int(n or 1) for a,n in parts)
    except KeyError:
        raise ValueError('Masa atómica no cargada para este elemento.')


def named_amounts(text):
    rows = []
    for i, line in enumerate((text or '').splitlines(), 1):
        if not line.strip():
            continue
        match = re.fullmatch(r'\s*(.+?)\s+([+-]?\d+(?:[.,]\d+)?)\s*', line)
        if not match:
            raise ValueError(f'Línea {i}: usá nombre y cantidad; por ejemplo Sílice 30.')
        rows.append((match[1].strip(), positive(match[2].replace(',', '.'), f'cantidad en línea {i}', zero=True)))
    if not rows or sum(v for _,v in rows) <= 0:
        raise ValueError('Ingresá una composición con total mayor que cero.')
    return rows


def table_result(headers, rows, note=''):
    head = ''.join(f'<th>{html.escape(str(x))}</th>' for x in headers)
    body = ''.join('<tr>'+''.join(f'<td>{html.escape(str(v))}</td>' for v in row)+'</tr>' for row in rows)
    return f'<div class="panel"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table><p>{html.escape(note)}</p></div>'


def scale_recipe(text, target):
    rows = named_amounts(text)
    target = positive(target, 'peso final')
    total = sum(v for _,v in rows)
    return table_result(['Material', 'Original (partes)', 'A pesar (g)'], [(name, f'{v:g}', f'{v/total*target:.3f}') for name,v in rows], f'Total: {target:g} g. No modifica la fórmula ni descuenta stock. Usá cantidades de una misma base; no mezcles gramos y porcentajes.')


def umf_calculation(text):
    weights = {}
    for name, v in named_amounts(text):
        name = name.translate(str.maketrans('₀₁₂₃₄₅₆₇₈₉', '0123456789'))
        if name not in OXIDES:
            raise ValueError(f'Óxido no admitido: {name}. Ingresá análisis de óxidos, no nombres de materias primas.')
        weights[name] = weights.get(name, 0) + v
    moles = {name: grams/molecular_mass(name) for name,grams in weights.items()}
    flux = sum(v for name,v in moles.items() if name in FLUXES)
    if flux <= 0:
        raise ValueError('Falta al menos un fundente de la base RO/R₂O para normalizar a unidad.')
    return table_result(['Óxido','Gramos / partes','Moles','UMF','Grupo'], [(name, f'{weights[name]:g}', f'{v:.5f}', f'{v/flux:.5f}', 'RO / R₂O' if name in FLUXES else 'Fuera de la base') for name,v in moles.items()], 'Base unitaria: Li₂O, Na₂O, K₂O, MgO, CaO, SrO, BaO, ZnO y PbO. B₂O₃ y colorantes se muestran fuera de esa base. Convención declarada, no predicción de maduración, color ni seguridad. No altera los datos originales.')


def shrinkage(initial, final):
    a, b = positive(initial, 'medida inicial'), positive(final, 'medida final', zero=True)
    return (a-b)/a*100


def absorption(dry, saturated):
    a, b = positive(dry, 'peso seco'), positive(saturated, 'peso saturado')
    if b < a:
        raise ValueError('El peso saturado no puede ser menor que el seco. Revisá las mediciones.')
    return (b-a)/a*100


def plaster_batch(plaster, ratio):
    plaster, ratio = positive(plaster, 'peso de yeso'), positive(ratio, 'agua por 100 de yeso')
    water = plaster*ratio/100
    return table_result(['Yeso (g)','Agua (g)','Mezcla (g)'], [(f'{plaster:g}', f'{water:g}', f'{plaster+water:g}')], 'Relación por peso del producto elegido. No calcula volumen de molde ni reemplaza la ficha de su fabricante.')


def periodic_html(query=''):
    query = (query or '').casefold().strip()
    cells = []
    for z, (symbol, name) in enumerate(zip(ELEMENT_SYMBOLS, ELEMENT_NAMES), 1):
        if query and query not in f'{z} {symbol} {name}'.casefold():
            continue
        related = [o for o in OXIDES if symbol in [a for a,_ in re.findall(r'([A-Z][a-z]?)(\d*)', o)] and symbol != 'O']
        refs = ' · '.join(f'<a href="https://digitalfire.com/oxide/{o.lower()}" target="_blank" rel="noopener">{o}</a>' for o in related)
        mass = f'Masa atómica de cálculo ≈ {ATOMIC[symbol]:g} (valor redondeado).' if symbol in ATOMIC else 'Masa atómica: consultar la referencia CIAAW.'
        note = ELEMENT_NOTES.get(symbol, 'Consultá las referencias de sus compuestos; el elemento puro y sus óxidos no tienen las mismas propiedades.')
        cells.append(f'<details class="element-card"><summary><small>{z}</small> <b>{symbol}</b><br>{name}</summary><p>{mass}</p><p>{note}</p><p>{refs or "Ficha cerámica específica pendiente."}</p></details>')
    return '<p>Tocá un elemento para desplegar su ficha. Listado de los 118 elementos por número atómico; buscá por nombre, símbolo o número.</p><div class="element-grid">'+''.join(cells)+'</div><p>Referencias: <a href="https://iupac.org/iptei/" target="_blank" rel="noopener">IUPAC</a> · <a href="https://ciaaw.org/abridged-atomic-weights.htm" target="_blank" rel="noopener">CIAAW: pesos atómicos abreviados</a>. Las fichas ampliadas se incorporan progresivamente.</p>'
