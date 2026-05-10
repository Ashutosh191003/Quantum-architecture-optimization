"""
run_visualization.py  —  Revised 7-Scene Edition
=================================================
Animated visualization for the Quantum Processor Architecture Optimization
project.  Based on Yang et al., Results in Physics 53 (2023) 106944.

Scenes
------
  0  Intro                 (4 s)
  1  IBM Architecture      (8 s)
  2  What We Measure       (9 s)
  3  GA Optimization       (13 s)
  4  PCB Analogy           (10 s)
  5  Molecular Energy QPE  (12 s)
  6  Summary               (5 s)

Dependencies:
    pip install PyQt5
"""

import sys
import math
import random

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSizePolicy,
)
from PyQt5.QtCore import (
    Qt, QTimer, QPointF, QRectF, pyqtSignal,
)
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont,
    QLinearGradient, QRadialGradient, QPainterPath,
)

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL PALETTE
# ─────────────────────────────────────────────────────────────────────────────
C_BG          = QColor("#F0F6FF")
C_PANEL       = QColor("#FFFFFF")
C_NAVY        = QColor("#0D2B5E")
C_BLUE        = QColor("#1565C0")
C_BLUE_MID    = QColor("#1E88E5")
C_BLUE_LIGHT  = QColor("#64B5F6")
C_BLUE_PALE   = QColor("#BBDEFB")
C_ACCENT      = QColor("#0288D1")
C_WHITE       = QColor("#FFFFFF")
C_TEXT        = QColor("#0D2B5E")
C_TEXT_LIGHT  = QColor("#546E8A")
C_GOOD        = QColor("#1565C0")
C_GOLD        = QColor("#FFB300")
C_GREEN       = QColor("#2E7D32")
C_GREEN_LIGHT = QColor("#66BB6A")
C_RED         = QColor("#C62828")
C_RED_LIGHT   = QColor("#EF9A9A")
C_EDGE_IBM    = QColor("#90A4AE")
C_EDGE_OUR    = QColor("#1E88E5")
C_NODE_IBM    = QColor("#B0BEC5")
C_NODE_OUR    = QColor("#1565C0")

# ─────────────────────────────────────────────────────────────────────────────
# DATA  — from results.json / paper Fig. 12 (qpe_n9)
# ─────────────────────────────────────────────────────────────────────────────
# qpe_n9 values (actual from results.json)
QPE_IBM_GATES = 139
QPE_IBM_YIELD = 0.0
QPE_EFF_GATES = 160
QPE_EFF_YIELD = 0.04756
QPE_OUR_GATES = 136
QPE_OUR_YIELD = 0.09128

# Paper aggregate numbers
AGG_PERF_GAIN     = 15.61   # % avg perf improvement over IBM
AGG_COLL_REDUCE   = 21.33   # % min freq-collision reduction
AGG_EFF_PERF_GAIN = 6.58    # % over eff-5-freq
AGG_EFF_YIELD_GAIN = 6.45   # % yield gain over eff-5-freq

# IBM 20-qubit edges (5×4 heavy-hex style subset)
IBM_EDGES_20 = [
    (0,1),(1,2),(2,3),(3,4),
    (5,6),(6,7),(7,8),(8,9),
    (10,11),(11,12),(12,13),(13,14),
    (15,16),(16,17),(17,18),(18,19),
    (0,5),(1,6),(2,7),(3,8),(4,9),
    (5,10),(6,11),(7,12),(8,13),(9,14),
    (10,15),(11,16),(12,17),(13,18),(14,19),
]

# QPE 9-qubit topology
QPE_TOPO_EDGES = [
    (0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8),(8,0),
    (0,4),(1,5),(2,6),
]

# ─────────────────────────────────────────────────────────────────────────────
# MATH HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def lerp(a, b, t):
    return a + (b - a) * t

def lerp_pt(p0, p1, t):
    return (lerp(p0[0], p1[0], t), lerp(p0[1], p1[1], t))

def ease_in_out(t):
    return t * t * (3.0 - 2.0 * t)

def ease_out(t):
    return 1.0 - (1.0 - t) ** 3

def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))

def phase(t, start, end):
    """Normalise t within a sub-phase [start,end] → [0,1], clamped."""
    return clamp((t - start) / max(1e-6, end - start))

# ─────────────────────────────────────────────────────────────────────────────
# DRAW PRIMITIVES
# ─────────────────────────────────────────────────────────────────────────────
def draw_rect(painter, x, y, w, h, r, fill, border=None, bw=1.5):
    painter.save()
    painter.setBrush(QBrush(fill))
    painter.setPen(QPen(border, bw) if border else Qt.NoPen)
    painter.drawRoundedRect(int(x), int(y), int(w), int(h), r, r)
    painter.restore()

def draw_node(painter, x, y, radius, fill, label="",
              label_color=None, border=None, bw=2, glow=False, glow_color=None):
    painter.save()
    if glow:
        gc = QColor(glow_color or fill)
        gc.setAlpha(50)
        painter.setBrush(QBrush(gc))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(x, y), radius + 9, radius + 9)
    painter.setBrush(QBrush(fill))
    painter.setPen(QPen(border or C_WHITE, bw))
    painter.drawEllipse(QPointF(x, y), radius, radius)
    if label:
        lc = label_color or C_WHITE
        painter.setPen(QPen(lc))
        painter.setFont(QFont("Courier New", 8, QFont.Bold))
        painter.drawText(
            QRectF(x - radius, y - radius, radius * 2, radius * 2),
            Qt.AlignCenter, label)
    painter.restore()

def draw_edge(painter, p0, p1, color, width=1.5, alpha=180):
    c = QColor(color); c.setAlpha(alpha)
    painter.save()
    painter.setPen(QPen(c, width, Qt.SolidLine, Qt.RoundCap))
    painter.drawLine(QPointF(p0[0], p0[1]), QPointF(p1[0], p1[1]))
    painter.restore()

def draw_text(painter, rect, text, font, color, align=Qt.AlignCenter, wrap=False):
    painter.save()
    painter.setPen(QPen(color))
    painter.setFont(font)
    flags = align | (Qt.TextWordWrap if wrap else 0)
    painter.drawText(rect, flags, text)
    painter.restore()

def draw_header_bar(painter, w, h, title, subtitle, alpha):
    bar = QColor(C_NAVY); bar.setAlpha(int(240 * alpha))
    draw_rect(painter, w*0.03, h*0.03, w*0.94, 52, 8, bar)
    draw_text(painter, QRectF(w*0.03, h*0.03, w*0.94, 52), title,
              QFont("Georgia", 14, QFont.Bold),
              QColor(255, 255, 255, int(240*alpha)))
    sc = QColor(C_TEXT_LIGHT); sc.setAlpha(int(190*alpha))
    draw_text(painter, QRectF(0, h*0.03+56, w, 24), subtitle,
              QFont("Georgia", 10), sc)

def ibm_positions(w, h):
    ox, oy = w*0.09, h*0.18
    pos = {}
    for i in range(20):
        row, col = i // 5, i % 5
        pos[i] = (ox + col*(w*0.52/4), oy + row*(h*0.54/3))
    return pos

def ring_layout_9(cx, cy, r):
    pos = {}
    for i in range(9):
        angle = 2*math.pi*i/9 - math.pi/2
        pos[i] = (cx + r*math.cos(angle), cy + r*math.sin(angle))
    return pos

def random_layout_9(seed=99):
    rng = random.Random(seed)
    return {i: (rng.uniform(0.05, 0.95), rng.uniform(0.05, 0.95))
            for i in range(9)}

# ─────────────────────────────────────────────────────────────────────────────
# SCENE BASE
# ─────────────────────────────────────────────────────────────────────────────
class Scene:
    def __init__(self, duration_ms):
        self.duration = duration_ms
        self.elapsed  = 0

    @property
    def t(self):
        return clamp(self.elapsed / max(1, self.duration))

    def paint(self, painter, w, h):
        raise NotImplementedError


# ═════════════════════════════════════════════════════════════════════════════
# SCENE 0 — INTRO
# ═════════════════════════════════════════════════════════════════════════════
class SceneIntro(Scene):
    def __init__(self):
        super().__init__(4000)
        self._rng = random.Random(7)
        self._dots = [(self._rng.randint(0, 1000), self._rng.randint(0, 700),
                       self._rng.randint(2, 5)) for _ in range(40)]

    def paint(self, painter, w, h):
        t = self.t
        fade = clamp(t*3) * clamp((1-t)*8 + 0.3)

        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, QColor("#0A1F45"))
        grad.setColorAt(1, QColor("#1565C0"))
        painter.fillRect(0, 0, w, h, QBrush(grad))

        # Particle field
        painter.save()
        for dx, dy, r in self._dots:
            x, y = dx * w/1000, dy * h/700
            c = QColor(255, 255, 255, int(35*fade))
            painter.setBrush(QBrush(c)); painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(x, y), r, r)
        painter.restore()

        # Connecting lines (circuit feel)
        painter.save()
        painter.setPen(QPen(QColor(100, 160, 255, int(18*fade)), 1))
        pts = [(dx*w/1000, dy*h/700) for dx, dy, _ in self._dots[:15]]
        for i in range(len(pts)-1):
            painter.drawLine(QPointF(*pts[i]), QPointF(*pts[i+1]))
        painter.restore()

        alpha = int(255*fade)
        draw_text(painter, QRectF(0, h*0.20, w, 60),
                  "Quantum Processor Architecture Optimization",
                  QFont("Georgia", 28, QFont.Bold),
                  QColor(255, 255, 255, alpha))
        draw_text(painter, QRectF(0, h*0.34, w, 40),
                  "Improving Performance & Reducing Frequency Collisions",
                  QFont("Georgia", 14),
                  QColor(180, 215, 255, alpha))

        tag_a = int(255 * clamp(phase(t,0.25,0.55)*3) * clamp((1-t)*8+0.3))
        draw_text(painter, QRectF(0, h*0.49, w, 34),
                  "Demo: qpe_n9  —  9-Qubit Quantum Phase Estimation",
                  QFont("Courier New", 13),
                  QColor(100, 181, 246, tag_a))

        # Divider line
        painter.save()
        painter.setPen(QPen(QColor(100, 181, 246, int(160*fade)), 1))
        painter.drawLine(int(w*0.2), int(h*0.61), int(w*0.8), int(h*0.61))
        painter.restore()

        draw_text(painter, QRectF(0, h*0.65, w, 28),
                  "Based on Yang et al., Results in Physics 53 (2023) 106944",
                  QFont("Georgia", 10),
                  QColor(144, 202, 249, int(200*fade)))


# ═════════════════════════════════════════════════════════════════════════════
# SCENE 1 — IBM ARCHITECTURE
# ═════════════════════════════════════════════════════════════════════════════
class SceneIBM(Scene):
    ACTIVE = {0, 2, 4, 6, 8, 10, 12, 14, 16}   # 9 qubits mapped to device

    def __init__(self):
        super().__init__(8000)

    def paint(self, painter, w, h):
        t = self.t
        fade = clamp(t*4)
        painter.fillRect(0, 0, w, h, QBrush(C_BG))
        draw_header_bar(painter, w, h,
                        "Step 1 — IBM General-Purpose Architecture",
                        "20-qubit square lattice  •  Fixed stripe frequency pattern",
                        fade)

        pos = ibm_positions(w, h)
        # Edges
        for a, b in IBM_EDGES_20:
            draw_edge(painter, pos[a], pos[b], C_EDGE_IBM, 1.3, int(90*fade))

        # Nodes
        for i in range(20):
            active = i in self.ACTIVE
            nc = QColor(C_NODE_OUR if active else C_NODE_IBM)
            nc.setAlpha(int((220 if active else 130)*fade))
            draw_node(painter, pos[i][0], pos[i][1],
                      13 if active else 9, nc,
                      f"Q{i}" if active else "",
                      C_WHITE, C_WHITE, 1.5 if active else 1,
                      glow=(active and t > 0.4))

        # Explanation card (appears at t>0.45)
        if t > 0.42:
            ca = clamp(phase(t, 0.42, 0.65)*3)
            self._draw_explanation(painter, w, h, ca)

        # Legend
        if t > 0.65:
            la = clamp(phase(t, 0.65, 0.80)*4)
            self._draw_legend(painter, w, h, la, pos)

    def _draw_explanation(self, painter, w, h, alpha):
        ex = w*0.67; ey = h*0.18
        ew = w*0.29; eh = h*0.62
        bg = QColor(C_NAVY); bg.setAlpha(int(230*alpha))
        draw_rect(painter, ex, ey, ew, eh, 10, bg)

        lines = [
            ("How it works", True,  QColor(255,255,255,int(240*alpha)), 11),
            ("", False, QColor(0,0,0,0), 6),
            ("Each dot is a qubit —", False, QColor(C_BLUE_LIGHT.red(), C_BLUE_LIGHT.green(), C_BLUE_LIGHT.blue(), int(220*alpha)), 9),
            ("a tiny quantum memory.", False, QColor(C_BLUE_LIGHT.red(), C_BLUE_LIGHT.green(), C_BLUE_LIGHT.blue(), int(220*alpha)), 9),
            ("", False, QColor(0,0,0,0), 5),
            ("Lines are connections —", False, QColor(200,225,255,int(210*alpha)), 9),
            ("only connected qubits", False, QColor(200,225,255,int(210*alpha)), 9),
            ("can share information.", False, QColor(200,225,255,int(210*alpha)), 9),
            ("", False, QColor(0,0,0,0), 5),
            ("To run a program,", False, QColor(C_GOLD.red(), C_GOLD.green(), C_GOLD.blue(), int(220*alpha)), 9),
            ("quantum states must hop", False, QColor(C_GOLD.red(), C_GOLD.green(), C_GOLD.blue(), int(220*alpha)), 9),
            ("along these connections.", False, QColor(C_GOLD.red(), C_GOLD.green(), C_GOLD.blue(), int(220*alpha)), 9),
            ("", False, QColor(0,0,0,0), 5),
            ("Extra hops = extra gates", False, QColor(C_RED_LIGHT.red(), C_RED_LIGHT.green(), C_RED_LIGHT.blue(), int(215*alpha)), 9),
            ("= more errors & noise.", False, QColor(C_RED_LIGHT.red(), C_RED_LIGHT.green(), C_RED_LIGHT.blue(), int(215*alpha)), 9),
            ("", False, QColor(0,0,0,0), 5),
            ("The blue dots show 9", False, QColor(180,220,255,int(200*alpha)), 8),
            ("qubits from this 20-qubit", False, QColor(180,220,255,int(200*alpha)), 8),
            ("device used for QPE.", False, QColor(180,220,255,int(200*alpha)), 8),
        ]
        y = ey + 14
        for text, bold, color, size in lines:
            if not text:
                y += size; continue
            draw_text(painter,
                      QRectF(ex+12, y, ew-24, size+8),
                      text,
                      QFont("Georgia", size, QFont.Bold if bold else QFont.Normal),
                      color, Qt.AlignLeft)
            y += size + 5

    def _draw_legend(self, painter, w, h, alpha, pos):
        lx, ly = w*0.03, h*0.84
        nc = QColor(C_NODE_OUR); nc.setAlpha(int(200*alpha))
        draw_node(painter, lx+12, ly+10, 10, nc)
        tc = QColor(C_TEXT); tc.setAlpha(int(200*alpha))
        draw_text(painter, QRectF(lx+28, ly+4, 200, 16),
                  "Active qubits  (qpe_n9 benchmark)",
                  QFont("Georgia", 9), tc, Qt.AlignLeft)
        gc = QColor(C_NODE_IBM); gc.setAlpha(int(150*alpha))
        draw_node(painter, lx+12, ly+32, 7, gc)
        draw_text(painter, QRectF(lx+28, ly+26, 200, 16),
                  "Inactive qubits",
                  QFont("Georgia", 9), tc, Qt.AlignLeft)


# ═════════════════════════════════════════════════════════════════════════════
# SCENE 2 — WHAT WE MEASURE
# ═════════════════════════════════════════════════════════════════════════════
class SceneWhatWeMeasure(Scene):
    def __init__(self):
        super().__init__(9000)

    def paint(self, painter, w, h):
        t = self.t
        fade = clamp(t*4)
        painter.fillRect(0, 0, w, h, QBrush(C_BG))
        draw_header_bar(painter, w, h,
                        "Step 2 — What We Measure",
                        "Two metrics determine architecture quality",
                        fade)

        # Phase 1: explanation cards (0 → 0.38)
        cards_a = clamp(phase(t, 0.00, 0.25)*4)
        self._draw_metric_cards(painter, w, h, cards_a)

        # Phase 2: "Simulating…" loading bar (0.30 → 0.65)
        if t > 0.30:
            sim_a = clamp(phase(t, 0.30, 0.50)*4)
            sim_p = clamp(phase(t, 0.36, 0.68))
            self._draw_loading(painter, w, h, sim_a, sim_p)

        # Phase 3: results appear (0.68 → 1.0)
        if t > 0.66:
            res_a = clamp(phase(t, 0.66, 0.85)*4)
            self._draw_results(painter, w, h, res_a)

    def _draw_metric_cards(self, painter, w, h, alpha):
        # Left card — Gate Count
        lx = w*0.04; ly = h*0.17; lw = w*0.44; lh = h*0.46
        bg1 = QColor(C_PANEL); bg1.setAlpha(int(240*alpha))
        bc1 = QColor(C_BLUE);  bc1.setAlpha(int(160*alpha))
        draw_rect(painter, lx, ly, lw, lh, 10, bg1, bc1)

        # Icon area — mini circuit
        self._draw_circuit_icon(painter, lx+lw*0.5, ly+lh*0.28, lw*0.35, alpha)

        tc = QColor(C_NAVY); tc.setAlpha(int(230*alpha))
        draw_text(painter, QRectF(lx, ly+8, lw, 26),
                  "SWAP Gate Count",
                  QFont("Georgia", 13, QFont.Bold), tc)
        sc = QColor(C_TEXT_LIGHT); sc.setAlpha(int(200*alpha))
        lines_g = [
            "When qubits are not directly",
            "connected, the computer inserts",
            "SWAP gates to move data.",
            "",
            "More SWAP gates = more time",
            "= more chances for errors.",
            "",
            "Lower is better.  ↓",
        ]
        y = ly + lh*0.55
        for line in lines_g:
            draw_text(painter, QRectF(lx+14, y, lw-28, 15),
                      line, QFont("Georgia", 9),
                      QColor(C_GOLD if line.endswith("↓") else
                             (C_TEXT_LIGHT.red(), C_TEXT_LIGHT.green(), C_TEXT_LIGHT.blue()),
                             int((230 if "↓" in line else 200)*alpha)),
                      Qt.AlignLeft)
            y += 15 if line else 6

        # Right card — Yield Rate
        rx = w*0.52; ry = h*0.17; rw = w*0.44; rh = h*0.46
        bg2 = QColor(C_PANEL); bg2.setAlpha(int(240*alpha))
        bc2 = QColor(C_GREEN);  bc2.setAlpha(int(160*alpha))
        draw_rect(painter, rx, ry, rw, rh, 10, bg2, bc2)

        self._draw_frequency_icon(painter, rx+rw*0.5, ry+rh*0.28, rw*0.35, alpha)

        tc2 = QColor(C_NAVY); tc2.setAlpha(int(230*alpha))
        draw_text(painter, QRectF(rx, ry+8, rw, 26),
                  "Yield Rate",
                  QFont("Georgia", 13, QFont.Bold), tc2)
        lines_y = [
            "Each qubit vibrates at its own",
            "frequency.  If two qubits share",
            "a similar frequency, they",
            "accidentally interfere — a",
            "\"frequency collision\".",
            "",
            "Yield = probability no collision",
            "occurs.  Higher is better.  ↑",
        ]
        y2 = ry + rh*0.55
        for line in lines_y:
            c = (QColor(C_GREEN_LIGHT.red(),C_GREEN_LIGHT.green(),C_GREEN_LIGHT.blue(),int(230*alpha))
                 if "↑" in line
                 else QColor(C_TEXT_LIGHT.red(),C_TEXT_LIGHT.green(),C_TEXT_LIGHT.blue(),int(200*alpha)))
            draw_text(painter, QRectF(rx+14, y2, rw-28, 15),
                      line, QFont("Georgia", 9), c, Qt.AlignLeft)
            y2 += 15 if line else 6

    def _draw_circuit_icon(self, painter, cx, cy, size, alpha):
        """Mini horizontal circuit diagram."""
        painter.save()
        painter.setPen(QPen(QColor(C_BLUE.red(),C_BLUE.green(),C_BLUE.blue(),int(160*alpha)), 1.5))
        for dy in [-size*0.25, 0, size*0.25]:
            painter.drawLine(QPointF(cx-size*0.5, cy+dy), QPointF(cx+size*0.5, cy+dy))
        # Gate boxes
        for gx, gy in [(cx-size*0.2, cy-size*0.25), (cx+size*0.1, cy),
                       (cx-size*0.05, cy+size*0.25)]:
            draw_rect(painter, gx-8, cy+gy-cy-9, 16, 18, 3,
                      QColor(C_BLUE.red(),C_BLUE.green(),C_BLUE.blue(),int(120*alpha)))
        painter.restore()

    def _draw_frequency_icon(self, painter, cx, cy, size, alpha):
        """Mini sine-wave collision diagram."""
        painter.save()
        path1 = QPainterPath()
        path2 = QPainterPath()
        steps = 60
        for i in range(steps+1):
            x = cx - size*0.5 + size*i/steps
            y1 = cy - size*0.15 + math.sin(i/steps*4*math.pi)*size*0.12
            y2 = cy + size*0.15 + math.sin(i/steps*4*math.pi + 0.3)*size*0.12
            if i == 0:
                path1.moveTo(x, y1); path2.moveTo(x, y2)
            else:
                path1.lineTo(x, y1); path2.lineTo(x, y2)
        painter.setPen(QPen(QColor(C_BLUE.red(),C_BLUE.green(),C_BLUE.blue(),int(170*alpha)), 1.8))
        painter.drawPath(path1)
        painter.setPen(QPen(QColor(C_RED.red(),C_RED.green(),C_RED.blue(),int(170*alpha)), 1.8))
        painter.drawPath(path2)
        # "Collision" highlight
        painter.setPen(QPen(QColor(C_GOLD.red(),C_GOLD.green(),C_GOLD.blue(),int(180*alpha)), 2))
        painter.drawEllipse(QPointF(cx, cy), 8, 8)
        painter.restore()

    def _draw_loading(self, painter, w, h, alpha, progress):
        bx = w*0.04; by = h*0.67; bw = w*0.92; bh = 28
        bg = QColor(C_BLUE_PALE); bg.setAlpha(int(200*alpha))
        draw_rect(painter, bx, by, bw, bh, 14, bg)
        if progress > 0.01:
            grad = QLinearGradient(bx, 0, bx+bw*progress, 0)
            grad.setColorAt(0, QColor("#1565C0"))
            grad.setColorAt(1, QColor("#0288D1"))
            painter.save()
            painter.setBrush(QBrush(grad)); painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(bx), int(by), int(bw*progress), int(bh), 14, 14)
            painter.restore()

        tc = QColor(C_NAVY); tc.setAlpha(int(220*alpha))
        draw_text(painter, QRectF(bx, by-22, bw, 20),
                  f"Simulating QPE on IBM device…   {int(progress*100)}% complete",
                  QFont("Courier New", 9, QFont.Bold), tc, Qt.AlignLeft)

    def _draw_results(self, painter, w, h, alpha):
        cards = [
            ("IBM Baseline", QPE_IBM_GATES, QPE_IBM_YIELD, C_NODE_IBM, False),
            ("eff-5-freq",   QPE_EFF_GATES, QPE_EFF_YIELD, C_BLUE_LIGHT, False),
            ("Ours  ★",      QPE_OUR_GATES, QPE_OUR_YIELD, C_NODE_OUR,  True),
        ]
        cw = w*0.28; gap = w*0.03
        sx = (w - (cw*3 + gap*2))/2; cy = h*0.70

        for idx, (name, gates, yld, col, winner) in enumerate(cards):
            cx = sx + idx*(cw+gap)
            bg = QColor("#E3F2FD" if winner else "#FFFFFF")
            bg.setAlpha(int(235*alpha))
            bc = QColor(col); bc.setAlpha(int(180*alpha))
            draw_rect(painter, cx, cy, cw, h*0.22, 8, bg, bc)

            nc = QColor(col); nc.setAlpha(int(220*alpha))
            draw_text(painter, QRectF(cx, cy+6, cw, 22),
                      name, QFont("Georgia", 10, QFont.Bold if winner else QFont.Normal), nc)
            tc = QColor(C_NAVY); tc.setAlpha(int(210*alpha))
            draw_text(painter, QRectF(cx, cy+28, cw, 22),
                      f"{gates} gates",
                      QFont("Courier New", 13, QFont.Bold), tc)
            draw_text(painter, QRectF(cx, cy+50, cw, 22),
                      f"yield = {yld:.4f}",
                      QFont("Courier New", 11, QFont.Bold), tc)
            if winner:
                gc = QColor(C_GOLD); gc.setAlpha(int(230*alpha))
                draw_text(painter, QRectF(cx, cy+72, cw, 18),
                          "Fewer gates · Higher yield",
                          QFont("Georgia", 8, QFont.Bold), gc)


# ═════════════════════════════════════════════════════════════════════════════
# SCENE 3 — GA OPTIMIZATION
# ═════════════════════════════════════════════════════════════════════════════
class SceneGA(Scene):
    def __init__(self):
        super().__init__(13000)
        self._rpos_norm = random_layout_9(seed=99)  # unit-square coords
        self._right_cache = {}

    def _place(self, norm, ox, oy, pw, ph):
        """Map unit-square coords into panel."""
        margin = 0.12
        return {i: (ox + (norm[i][0]*(1-2*margin)+margin)*pw,
                    oy + (norm[i][1]*(1-2*margin)+margin)*ph)
                for i in norm}

    def paint(self, painter, w, h):
        t = self.t
        fade = clamp(t*4)
        painter.fillRect(0, 0, w, h, QBrush(C_BG))
        draw_header_bar(painter, w, h,
                        "Step 3 — Genetic Algorithm Optimization  (λ sweep 1→6)",
                        "Minimising: Σ SWAP gates + λ · frequency collision risk",
                        fade)

        # Panel split line
        painter.save()
        lc = QColor(C_BLUE_PALE); lc.setAlpha(int(160*fade))
        painter.setPen(QPen(lc, 1, Qt.DashLine))
        painter.drawLine(int(w*0.5), int(h*0.14), int(w*0.5), int(h*0.88))
        painter.restore()

        # Side labels
        tc = QColor(C_NAVY); tc.setAlpha(int(200*fade))
        draw_text(painter, QRectF(w*0.02, h*0.14, w*0.46, 26),
                  "Random Initial Layout", QFont("Georgia", 11, QFont.Bold), tc)
        draw_text(painter, QRectF(w*0.52, h*0.14, w*0.46, 26),
                  "GA-Optimised Ring Architecture", QFont("Georgia", 11, QFont.Bold), tc)

        # Node morph progress (phase 0.22 → 0.62)
        raw_morph = phase(t, 0.22, 0.62)
        morph = ease_in_out(raw_morph)

        # Left panel positions
        pw, ph = w*0.44, h*0.56
        lpos = self._place(self._rpos_norm, w*0.03, h*0.18, pw, ph)

        # Right panel: morph from random to ring
        cx_r = w*0.76; cy_r = h*0.47
        r_ring = min(w, h)*0.17
        opt = ring_layout_9(cx_r, cy_r, r_ring)
        rnd_r = self._place(self._rpos_norm, w*0.53, h*0.18, pw, ph)
        for i in range(9):
            self._right_cache[i] = lerp_pt(rnd_r[i], opt[i], morph)

        # Draw left graph (dims as morph progresses)
        la = int(200*fade*(1 - morph*0.55))
        for a, b in QPE_TOPO_EDGES:
            draw_edge(painter, lpos[a], lpos[b], C_BLUE_LIGHT, 1.4, int(la*0.7))
        for i in lpos:
            nc = QColor(C_NODE_IBM); nc.setAlpha(la)
            draw_node(painter, lpos[i][0], lpos[i][1], 12, nc,
                      f"Q{i}", QColor(255,255,255,la), C_WHITE, 1.2)

        # Draw right graph
        ra = int(210*fade)
        for a, b in QPE_TOPO_EDGES:
            if a in self._right_cache and b in self._right_cache:
                draw_edge(painter, self._right_cache[a], self._right_cache[b],
                          C_EDGE_OUR, 2.0, int(ra*0.7*(0.3+morph*0.7)))
        for i in self._right_cache:
            nc = QColor(C_NODE_OUR); nc.setAlpha(ra)
            draw_node(painter, self._right_cache[i][0], self._right_cache[i][1],
                      14, nc, f"Q{i}", C_WHITE, C_WHITE, 2,
                      glow=(morph > 0.75))

        # GA progress bar
        ga_p = clamp(phase(t, 0.10, 0.55))
        self._draw_ga_bar(painter, w, h, ga_p, fade)

        # Lambda explanation popup
        if t > 0.55:
            pa = clamp(phase(t, 0.55, 0.72)*4)
            self._draw_lambda_card(painter, w, h, pa)

        # Side-by-side improvement after morph
        if t > 0.68:
            ra2 = clamp(phase(t, 0.68, 0.88)*4)
            self._draw_comparison_cards(painter, w, h, ra2)

    def _draw_ga_bar(self, painter, w, h, p, alpha):
        bx = w*0.04; by = h*0.77; bw = w*0.92; bh = 20
        bg = QColor(C_BLUE_PALE); bg.setAlpha(int(190*alpha))
        draw_rect(painter, bx, by, bw, bh, 10, bg)
        if p > 0.01:
            grad = QLinearGradient(bx, 0, bx+bw*p, 0)
            grad.setColorAt(0, QColor("#1565C0")); grad.setColorAt(1, QColor("#0288D1"))
            painter.save()
            painter.setBrush(QBrush(grad)); painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(bx), int(by), int(bw*p), int(bh), 10, 10)
            painter.restore()
        lam = max(1, int(p*6)); itr = int(p*300)
        fit = -4.5 + p*3.1
        tc = QColor(C_NAVY); tc.setAlpha(int(210*alpha))
        draw_text(painter, QRectF(bx, by-22, bw*0.7, 20),
                  f"  GA Running — λ={lam}  |  Generation: {itr}/300  |  Best fitness: {fit:.2f}",
                  QFont("Courier New", 9, QFont.Bold), tc, Qt.AlignLeft)

    def _draw_lambda_card(self, painter, w, h, alpha):
        px = w*0.54; py = h*0.58; pw = 220; ph = 100
        bg = QColor(C_NAVY); bg.setAlpha(int(215*alpha))
        draw_rect(painter, px, py, pw, ph, 8, bg)
        lines = [
            ("λ controls the trade-off:", True,  QColor(255,255,255,int(240*alpha)), 9),
            ("Low λ  → fewer SWAP gates", False, QColor(C_GOLD.red(),C_GOLD.green(),C_GOLD.blue(),int(220*alpha)), 8),
            ("        (better performance)", False, QColor(200,225,255,int(190*alpha)), 8),
            ("High λ → lower max-degree", False, QColor(C_GREEN_LIGHT.red(),C_GREEN_LIGHT.green(),C_GREEN_LIGHT.blue(),int(220*alpha)), 8),
            ("        (better yield rate)", False, QColor(200,225,255,int(190*alpha)), 8),
            ("We sweep λ=1…6 and pick best.", True, QColor(C_BLUE_LIGHT.red(),C_BLUE_LIGHT.green(),C_BLUE_LIGHT.blue(),int(220*alpha)), 8),
        ]
        y = py+10
        for text, bold, color, size in lines:
            draw_text(painter, QRectF(px+10, y, pw-20, size+7), text,
                      QFont("Georgia", size, QFont.Bold if bold else QFont.Normal),
                      color, Qt.AlignLeft)
            y += size+8

    def _draw_comparison_cards(self, painter, w, h, alpha):
        data = [
            ("IBM Baseline", QPE_IBM_GATES, QPE_IBM_YIELD, C_NODE_IBM, False),
            ("eff-5-freq",   QPE_EFF_GATES, QPE_EFF_YIELD, C_BLUE_LIGHT, False),
            ("Ours  ★",      QPE_OUR_GATES, QPE_OUR_YIELD, C_NODE_OUR,  True),
        ]
        cw = w*0.28; gap = w*0.02
        sx = (w - (cw*3+gap*2))/2; cy = h*0.84

        for idx, (name, gates, yld, col, winner) in enumerate(data):
            cx = sx + idx*(cw+gap)
            bg = QColor("#E3F2FD" if winner else C_PANEL.name())
            bg.setAlpha(int(230*alpha))
            bc = QColor(col); bc.setAlpha(int(170*alpha))
            draw_rect(painter, cx, cy, cw, h*0.13, 7, bg, bc)
            nc = QColor(col); nc.setAlpha(int(220*alpha))
            draw_text(painter, QRectF(cx, cy+4, cw, 18),
                      name, QFont("Georgia", 9, QFont.Bold if winner else QFont.Normal), nc)
            tc = QColor(C_NAVY); tc.setAlpha(int(210*alpha))
            draw_text(painter, QRectF(cx, cy+22, cw, 17),
                      f"{gates} gates", QFont("Courier New", 11, QFont.Bold), tc)
            draw_text(painter, QRectF(cx, cy+40, cw, 17),
                      f"yield {yld:.4f}", QFont("Courier New", 10, QFont.Bold), tc)


# ═════════════════════════════════════════════════════════════════════════════
# SCENE 4 — PCB ANALOGY  (significantly expanded)
# ═════════════════════════════════════════════════════════════════════════════
class ScenePCB(Scene):
    COMPS = [
        ("MCU",   "#1565C0", 54, 34),
        ("PWR",   "#0277BD", 40, 28),
        ("ADC",   "#0288D1", 36, 24),
        ("SEN-1", "#0288D1", 32, 22),
        ("SEN-2", "#0288D1", 32, 22),
        ("CAP",   "#546E8A", 20, 26),
        ("RES",   "#546E8A", 22, 12),
        ("CONN",  "#1B5E20", 34, 18),
    ]
    CONNS = [(0,1),(0,2),(0,3),(0,4),(1,5),(1,6),(2,3),(3,7),(4,7),(0,7)]

    def __init__(self):
        super().__init__(10000)
        self._rpos = None; self._opos = None

    def _ensure(self, w, h):
        if self._rpos: return
        rng = random.Random(21)
        pw = w*0.36; ph = h*0.54; ox = w*0.06; oy = h*0.19
        self._rpos = [(ox+rng.uniform(0.1,0.9)*pw, oy+rng.uniform(0.1,0.9)*ph)
                      for _ in self.COMPS]
        cx = ox+pw/2; cy = oy+ph/2
        self._opos = [
            (cx,           cy),
            (cx-pw*0.30,   cy),
            (cx+pw*0.30,   cy-ph*0.20),
            (cx,           cy-ph*0.28),
            (cx+pw*0.30,   cy+ph*0.22),
            (cx-pw*0.28,   cy-ph*0.25),
            (cx-pw*0.28,   cy+ph*0.25),
            (cx,           cy+ph*0.36),
        ]

    def paint(self, painter, w, h):
        t = self.t
        self._ensure(w, h)
        fade = clamp(t*4)
        painter.fillRect(0, 0, w, h, QBrush(C_BG))
        draw_header_bar(painter, w, h,
                        "Step 4 — PCB Layout Analogy",
                        "The same graph-theory principle used in electronics engineering",
                        fade)

        # Divider
        painter.save()
        lc = QColor(C_BLUE_PALE); lc.setAlpha(int(150*fade))
        painter.setPen(QPen(lc, 1, Qt.DashLine))
        painter.drawLine(int(w*0.50), int(h*0.14), int(w*0.50), int(h*0.88))
        painter.restore()

        # Panel labels
        tc = QColor(C_NAVY); tc.setAlpha(int(200*fade))
        draw_text(painter, QRectF(w*0.02, h*0.14, w*0.46, 26),
                  "Random Placement", QFont("Georgia", 11, QFont.Bold), tc)
        draw_text(painter, QRectF(w*0.52, h*0.14, w*0.46, 26),
                  "Graph-Optimised Layout", QFont("Georgia", 11, QFont.Bold), tc)

        morph = ease_in_out(clamp(phase(t, 0.28, 0.68)))

        # Left board
        self._draw_board(painter, self._rpos, int(200*fade*(1-morph*0.55)), optimised=False)

        # Right board (morphing)
        rp_shifted = [(p[0]+w*0.48, p[1]) for p in self._rpos]
        op_shifted = [(p[0]+w*0.48, p[1]) for p in self._opos]
        merged = [lerp_pt(rp_shifted[i], op_shifted[i], morph)
                  for i in range(len(self.COMPS))]
        self._draw_board(painter, merged, int(210*fade), optimised=True, morph=morph)

        # Analogy table (appears mid-scene)
        if t > 0.55:
            aa = clamp(phase(t, 0.55, 0.75)*4)
            self._draw_analogy_table(painter, w, h, aa)

        # Metrics comparison row
        if t > 0.72:
            ma = clamp(phase(t, 0.72, 0.90)*4)
            self._draw_metric_row(painter, w, h, ma, morph)

        # Insight card
        if t > 0.82:
            ia = clamp(phase(t, 0.82, 0.95)*4)
            self._draw_insight(painter, w, h, ia)

    def _draw_board(self, painter, positions, alpha, optimised=False, morph=0):
        if alpha < 5: return
        for a, b in self.CONNS:
            if a < len(positions) and b < len(positions):
                tc = QColor(21,101,192, int(145*alpha/210)) if optimised \
                     else QColor(100,120,140, int(100*alpha/200))
                painter.save()
                painter.setPen(QPen(tc, 2.0 if optimised else 1.4,
                                    Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(QPointF(*positions[a]), QPointF(*positions[b]))
                painter.restore()

        for idx, (name, col_hex, cw, ch) in enumerate(self.COMPS):
            if idx >= len(positions): break
            px, py = positions[idx]
            cx2, cy2 = px-cw/2, py-ch/2
            cc = QColor(col_hex); cc.setAlpha(alpha)
            draw_rect(painter, cx2, cy2, cw, ch, 4, cc,
                      QColor(255,255,255,int(alpha*0.7)))
            lc = QColor(255,255,255, alpha)
            draw_text(painter, QRectF(cx2, cy2, cw, ch), name,
                      QFont("Courier New", 7, QFont.Bold), lc)
            if optimised and morph > 0.82:
                painter.save()
                gc = QColor(2,136,209, int(55*morph))
                painter.setBrush(QBrush(gc)); painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(int(cx2-4), int(cy2-4), int(cw+8), int(ch+8), 5, 5)
                painter.restore()

    def _draw_analogy_table(self, painter, w, h, alpha):
        rows = [
            ("Quantum Concept",       "PCB / Electronics Equivalent"),
            ("Qubit",                 "Electronic component (MCU, sensor)"),
            ("Coupling edge",         "PCB trace / wire"),
            ("SWAP gate count",       "Total trace length"),
            ("Frequency collision",   "Signal crosstalk / interference"),
            ("Yield rate",            "Board reliability / signal integrity"),
            ("Optimised architecture","Optimal component placement"),
        ]
        tx = w*0.06; ty = h*0.68; tw = w*0.88
        rh = h*0.026
        bg = QColor(C_NAVY); bg.setAlpha(int(220*alpha))
        draw_rect(painter, tx, ty, tw, rh*len(rows)+8, 8, bg)

        for ri, (left, right) in enumerate(rows):
            y = ty+4+ri*rh
            is_hdr = ri==0
            fc = QColor(C_GOLD if is_hdr else C_BLUE_LIGHT)
            fc.setAlpha(int((240 if is_hdr else 210)*alpha))
            rc = QColor(255,255,255,int(200*alpha))
            draw_text(painter, QRectF(tx+10, y, tw*0.42, rh),
                      left, QFont("Georgia", 8, QFont.Bold if is_hdr else QFont.Normal),
                      fc, Qt.AlignLeft | Qt.AlignVCenter)
            draw_text(painter, QRectF(tx+tw*0.50, y, tw*0.46, rh),
                      right, QFont("Georgia", 8, QFont.Bold if is_hdr else QFont.Normal),
                      rc, Qt.AlignLeft | Qt.AlignVCenter)

        # Separator line
        painter.save()
        sep = QColor(C_GOLD); sep.setAlpha(int(120*alpha))
        painter.setPen(QPen(sep, 0.8, Qt.DashLine))
        painter.drawLine(int(tx+tw*0.48), int(ty+4), int(tx+tw*0.48), int(ty+4+rh*len(rows)))
        painter.restore()

    def _draw_metric_row(self, painter, w, h, alpha, morph):
        by = h*0.870; bx = w*0.06; bw = w*0.88
        items = [
            ("Trace length (≡ gate count)",
             "High — poor routing",
             f"Reduced by ~{int(18*morph)}%  ✓"),
            ("Crosstalk (≡ collision risk)",
             "Unpredictable",
             "Controlled  ✓"),
        ]
        iw = bw/2; ih = h*0.058
        for ci, (metric, before, after) in enumerate(items):
            ix = bx + ci*iw
            bg = QColor(C_PANEL); bg.setAlpha(int(220*alpha))
            bc = QColor(C_BLUE_PALE); bc.setAlpha(int(180*alpha))
            draw_rect(painter, ix, by, iw-6, ih, 6, bg, bc)
            mc = QColor(C_TEXT_LIGHT); mc.setAlpha(int(190*alpha))
            draw_text(painter, QRectF(ix+6, by+2, iw-20, ih*0.33),
                      metric, QFont("Georgia", 8, QFont.Bold), mc, Qt.AlignLeft)
            rc = QColor(C_RED); rc.setAlpha(int(180*alpha))
            draw_text(painter, QRectF(ix+6, by+ih*0.35, iw*0.42, ih*0.55),
                      before, QFont("Georgia", 8), rc, Qt.AlignLeft)
            gc = QColor(C_GREEN); gc.setAlpha(int(210*alpha))
            draw_text(painter, QRectF(ix+iw*0.44, by+ih*0.35, iw*0.50, ih*0.55),
                      after, QFont("Georgia", 8, QFont.Bold), gc, Qt.AlignLeft)

    def _draw_insight(self, painter, w, h, alpha):
        ix = w*0.52; iy = h*0.58; iw = w*0.44; ih = h*0.095
        bg = QColor("#0D3B8C"); bg.setAlpha(int(230*alpha))
        draw_rect(painter, ix, iy, iw, ih, 8, bg)
        tc = QColor(255,255,255,int(230*alpha))
        draw_text(painter, QRectF(ix+10, iy+6, iw-20, ih-12),
                  "Insight: Optimising qubit layout is exactly like\n"
                  "optimising a PCB — minimise wire length, avoid\n"
                  "interference. Same maths, different scale.",
                  QFont("Georgia", 9), tc, Qt.AlignLeft, wrap=True)


# ═════════════════════════════════════════════════════════════════════════════
# SCENE 5 — MOLECULAR ENERGY / QPE  (new)
# ═════════════════════════════════════════════════════════════════════════════
class SceneMolecular(Scene):
    """
    QPE on H₂ molecule.
    Left: IBM arch → noisy energy convergence (wobbly).
    Right: Our arch → clean convergence.
    Both show an H₂ atom diagram + energy line-plot.
    """
    def __init__(self):
        super().__init__(12000)
        self._ibm_noise  = self._gen_noisy_series(seed=1)
        self._our_series = self._gen_clean_series()

    @staticmethod
    def _gen_noisy_series(seed=1):
        rng = random.Random(seed)
        TRUE = -1.136
        pts = []
        for i in range(80):
            noise = rng.gauss(0, 0.18) * max(0.2, 1 - i/80*0.5)
            drift = rng.gauss(0, 0.09)
            pts.append(TRUE + noise + drift)
        return pts

    @staticmethod
    def _gen_clean_series():
        TRUE = -1.136
        pts = []
        for i in range(80):
            decay = math.exp(-i/22)
            pts.append(TRUE + decay*0.55 + math.sin(i*0.6)*decay*0.08)
        return pts

    def paint(self, painter, w, h):
        t = self.t
        fade = clamp(t*4)
        painter.fillRect(0, 0, w, h, QBrush(C_BG))
        draw_header_bar(painter, w, h,
                        "Step 5 — Practical Application: H₂ Molecular Energy",
                        "Quantum Phase Estimation finds the ground-state energy of hydrogen",
                        fade)

        # Two panels
        lx = w*0.03; lw = w*0.44; ry = h*0.17; ph = h*0.58
        rx = w*0.53; rw = w*0.44

        # Panel backgrounds
        lbg = QColor(C_PANEL); lbg.setAlpha(int(230*fade))
        rbg = QColor(C_PANEL); rbg.setAlpha(int(230*fade))
        lbc = QColor(C_RED);   lbc.setAlpha(int(120*fade))
        rbc = QColor(C_GREEN); rbc.setAlpha(int(120*fade))
        draw_rect(painter, lx, ry, lw, ph, 10, lbg, lbc)
        draw_rect(painter, rx, ry, rw, ph, 10, rbg, rbc)

        # Panel headers
        rc = QColor(C_RED);   rc.setAlpha(int(200*fade))
        gc = QColor(C_GREEN); gc.setAlpha(int(200*fade))
        draw_text(painter, QRectF(lx, ry+6, lw, 22),
                  "IBM Architecture — Noisy",
                  QFont("Georgia", 11, QFont.Bold), rc)
        draw_text(painter, QRectF(rx, ry+6, rw, 22),
                  "Our Architecture — Stable",
                  QFont("Georgia", 11, QFont.Bold), gc)

        # Atom diagrams
        prog = clamp(phase(t, 0.05, 0.30)*3)
        self._draw_h2(painter, lx+lw*0.5, ry+ph*0.26, lw*0.35, fade, noisy=(t>0.45), morph=prog)
        self._draw_h2(painter, rx+rw*0.5, ry+ph*0.26, rw*0.35, fade, noisy=False, morph=prog)

        # Energy values (appear early)
        if t > 0.15:
            ea = clamp(phase(t, 0.15, 0.32)*4)
            self._draw_energy_label(painter, lx, ry+ph*0.43, lw,
                                    self._ibm_noise, t, ea, noisy=True)
            self._draw_energy_label(painter, rx, ry+ph*0.43, rw,
                                    self._our_series, t, ea, noisy=False)

        # Line plots
        if t > 0.30:
            pa = clamp(phase(t, 0.30, 0.50)*4)
            plot_p = clamp(phase(t, 0.35, 0.82))
            gw = lw*0.88; gh = ph*0.35
            self._draw_plot(painter, lx+lw*0.06, ry+ph*0.53, gw, gh,
                            self._ibm_noise, plot_p, pa, noisy=True)
            self._draw_plot(painter, rx+rw*0.06, ry+ph*0.53, gw, gh,
                            self._our_series, plot_p, pa, noisy=False)

        # Explanation card
        if t > 0.72:
            xa = clamp(phase(t, 0.72, 0.90)*4)
            self._draw_explanation(painter, w, h, xa)

    def _draw_h2(self, painter, cx, cy, size, alpha, noisy=False, morph=0):
        """Draw stylised H₂ molecule: two atoms + bond + orbits."""
        painter.save()
        r_atom = size*0.16
        sep    = size*0.38

        # Bond
        bc = QColor(C_BLUE_MID if not noisy else C_RED)
        bc.setAlpha(int(160*alpha))
        painter.setPen(QPen(bc, 3))
        painter.drawLine(QPointF(cx-sep, cy), QPointF(cx+sep, cy))

        # Electron orbits
        for sign in (-1, 1):
            ax = cx + sign*sep
            orb_c = QColor(C_BLUE_LIGHT if not noisy else C_RED_LIGHT)
            orb_c.setAlpha(int(60*alpha))
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(orb_c, 1, Qt.DashLine))
            painter.drawEllipse(QPointF(ax, cy), r_atom*1.7, r_atom*1.1)

            # Atoms
            ac = QColor(C_BLUE if not noisy else C_RED)
            ac.setAlpha(int(220*alpha))
            draw_node(painter, ax, cy, r_atom, ac, "H",
                      C_WHITE, C_WHITE, 1.5, glow=(morph > 0.5))

            # Electrons (animated)
            angle = morph*6.28 * sign
            ex = ax + r_atom*1.7*math.cos(angle)
            ey = cy + r_atom*1.1*math.sin(angle)
            ec = QColor(C_GOLD if not noisy else C_RED)
            ec.setAlpha(int(200*alpha))
            painter.setBrush(QBrush(ec)); painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(ex, ey), 4, 4)

        # "Noisy" wobble indicator
        if noisy and alpha > 0.5:
            wobble_c = QColor(C_RED); wobble_c.setAlpha(int(100*alpha))
            painter.setPen(QPen(wobble_c, 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), size*0.48, size*0.48)

        painter.restore()

    def _draw_energy_label(self, painter, px, py, pw, series, t, alpha, noisy):
        idx = min(len(series)-1, int(phase(t, 0.15, 0.85)*len(series)))
        val = series[idx]
        color = QColor(C_RED if noisy else C_GREEN)
        color.setAlpha(int(230*alpha))
        draw_text(painter, QRectF(px, py, pw, 24),
                  f"Energy: {val:+.4f} Ha",
                  QFont("Courier New", 13, QFont.Bold), color)
        tc = QColor(C_TEXT_LIGHT); tc.setAlpha(int(170*alpha))
        draw_text(painter, QRectF(px, py+22, pw, 16),
                  "True value: −1.1362 Ha",
                  QFont("Courier New", 9), tc)

    def _draw_plot(self, painter, px, py, pw, ph, series, progress, alpha, noisy):
        """Draw energy convergence line plot."""
        # Frame
        bg = QColor("#F8FBFF"); bg.setAlpha(int(220*alpha))
        bc = QColor(C_RED if noisy else C_GREEN); bc.setAlpha(int(140*alpha))
        draw_rect(painter, px, py, pw, ph, 6, bg, bc, 1)

        # Axes
        painter.save()
        ac = QColor(C_TEXT_LIGHT); ac.setAlpha(int(160*alpha))
        painter.setPen(QPen(ac, 1))
        painter.drawLine(QPointF(px+2, py+2), QPointF(px+2, py+ph-2))
        painter.drawLine(QPointF(px+2, py+ph-2), QPointF(px+pw-2, py+ph-2))
        painter.restore()

        # True value line
        TRUE = -1.1362
        y_min, y_max = -1.6, -0.6
        def to_y(v): return py + ph - (v-y_min)/(y_max-y_min)*ph

        ty = to_y(TRUE)
        painter.save()
        tc = QColor(C_GOLD); tc.setAlpha(int(120*alpha))
        painter.setPen(QPen(tc, 1, Qt.DashLine))
        painter.drawLine(QPointF(px+4, ty), QPointF(px+pw-4, ty))
        painter.restore()

        draw_text(painter, QRectF(px+pw*0.5, ty-14, pw*0.45, 13),
                  "true value",
                  QFont("Courier New", 7), QColor(C_GOLD.red(),C_GOLD.green(),C_GOLD.blue(),int(160*alpha)),
                  Qt.AlignLeft)

        # Data line
        n_pts = max(2, int(progress * len(series)))
        path  = QPainterPath()
        for i in range(n_pts):
            x = px + 4 + (i/(len(series)-1))*(pw-8)
            y = clamp(to_y(series[i]), py+2, py+ph-2)
            if i == 0: path.moveTo(x, y)
            else:      path.lineTo(x, y)

        lc = QColor(C_RED if noisy else C_GREEN); lc.setAlpha(int(220*alpha))
        painter.save()
        painter.setPen(QPen(lc, 2 if noisy else 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        painter.restore()

        # Axis labels
        yc = QColor(C_TEXT_LIGHT); yc.setAlpha(int(150*alpha))
        draw_text(painter, QRectF(px+2, py, pw-4, 13), "Energy (Ha)",
                  QFont("Courier New", 7), yc, Qt.AlignLeft)
        draw_text(painter, QRectF(px+2, py+ph-12, pw-4, 12), "Iterations →",
                  QFont("Courier New", 7), yc, Qt.AlignRight)

    def _draw_explanation(self, painter, w, h, alpha):
        ex = w*0.03; ey = h*0.79; ew = w*0.94; eh = h*0.16
        bg = QColor(C_NAVY); bg.setAlpha(int(225*alpha))
        draw_rect(painter, ex, ey, ew, eh, 10, bg)
        tc = QColor(255,255,255,int(230*alpha))
        draw_text(painter, QRectF(ex, ey+6, ew, eh*0.42),
                  "Why does this matter?",
                  QFont("Georgia", 11, QFont.Bold), tc)
        sc = QColor(C_BLUE_LIGHT); sc.setAlpha(int(210*alpha))
        draw_text(painter, QRectF(ex+12, ey+eh*0.42, ew-24, eh*0.55),
                  "QPE finds the ground-state energy of molecules — essential for drug discovery & materials science.\n"
                  "More errors → wrong energy → wrong chemistry.  Better architecture = trustworthy quantum simulation.",
                  QFont("Georgia", 9), sc, Qt.AlignLeft, wrap=True)


# ═════════════════════════════════════════════════════════════════════════════
# SCENE 6 — SUMMARY
# ═════════════════════════════════════════════════════════════════════════════
class SceneSummary(Scene):
    def __init__(self):
        super().__init__(5000)

    def paint(self, painter, w, h):
        t = self.t
        fade = clamp(t*3) * clamp((1-t)*12 + 0.15)

        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, QColor("#0A1F45"))
        grad.setColorAt(1, QColor("#1565C0"))
        painter.fillRect(0, 0, w, h, QBrush(grad))

        alpha = int(255*fade)

        draw_text(painter, QRectF(0, h*0.05, w, 44),
                  "Results Summary",
                  QFont("Georgia", 26, QFont.Bold),
                  QColor(255,255,255,alpha))

        # Divider
        painter.save()
        painter.setPen(QPen(QColor(100,181,246,int(130*fade)), 1))
        painter.drawLine(int(w*0.2), int(h*0.17), int(w*0.8), int(h*0.17))
        painter.restore()

        # Key metrics
        metrics = [
            ("↑  15.61%", "average performance improvement over IBM baseline",  C_BLUE_LIGHT),
            ("↓  21.33%", "minimum reduction in frequency collision probability", C_BLUE_LIGHT),
            ("↑   6.58%", "performance gain over eff-5-freq method",             C_GOLD),
            ("↑   6.45%", "yield improvement over eff-5-freq method",            C_GOLD),
            ("  qpe_n9:", "136 gates / yield 0.0913  vs IBM 139 gates / yield 0",C_GREEN_LIGHT),
        ]
        for idx, (num, desc, col) in enumerate(metrics):
            ia = int(alpha * clamp(phase(t, 0.15+idx*0.06, 0.35+idx*0.06)*5))
            nc = QColor(col); nc.setAlpha(ia)
            draw_text(painter, QRectF(w*0.12, h*0.22+idx*h*0.095, w*0.28, 36),
                      num, QFont("Courier New", 15, QFont.Bold), nc, Qt.AlignRight)
            dc = QColor(200,230,255,ia)
            draw_text(painter, QRectF(w*0.43, h*0.22+idx*h*0.095, w*0.48, 36),
                      desc, QFont("Georgia", 10), dc, Qt.AlignLeft)

        # Hook cards
        if t > 0.55:
            ha = clamp(phase(t, 0.55, 0.78)*4)
            self._draw_hooks(painter, w, h, ha)

        # Footer
        fc = QColor(C_BLUE_LIGHT); fc.setAlpha(int(170*fade))
        draw_text(painter, QRectF(0, h*0.91, w, 24),
                  "Yang et al. (2023)  •  Graph-theory based quantum processor architecture design",
                  QFont("Georgia", 9), fc)

    def _draw_hooks(self, painter, w, h, alpha):
        hooks = [
            ("🔐 Cryptography",
             "Shor's algorithm runs on QPE.\nBetter arch → faster factoring\n→ post-quantum security matters now."),
            ("💊 Drug Discovery",
             "Molecular simulation finds new\ndrugs. Wrong energy = wrong drug.\nReliable arch = reliable results."),
            ("🔋 Materials Science",
             "Design better batteries & solar\ncells by simulating electron\nbehaviour accurately."),
        ]
        cw = w*0.28; gap = w*0.02
        sx = (w-(cw*3+gap*2))/2; cy = h*0.73

        for idx, (title, body) in enumerate(hooks):
            cx = sx + idx*(cw+gap)
            bg = QColor(255,255,255,int(18*alpha))
            bc = QColor(C_BLUE_LIGHT); bc.setAlpha(int(120*alpha))
            draw_rect(painter, cx, cy, cw, h*0.155, 8, bg, bc)
            tc = QColor(C_GOLD); tc.setAlpha(int(230*alpha))
            draw_text(painter, QRectF(cx, cy+5, cw, 20),
                      title, QFont("Georgia", 9, QFont.Bold), tc)
            sc = QColor(200,230,255,int(200*alpha))
            draw_text(painter, QRectF(cx+8, cy+24, cw-16, h*0.12),
                      body, QFont("Georgia", 8), sc, Qt.AlignLeft, wrap=True)


# ─────────────────────────────────────────────────────────────────────────────
# CANVAS  —  drives all scenes
# ─────────────────────────────────────────────────────────────────────────────
class VisualizationCanvas(QWidget):
    scene_changed = pyqtSignal(int, int)

    SCENE_DEFS = [
        ("Intro",             SceneIntro),
        ("IBM Architecture",  SceneIBM),
        ("What We Measure",   SceneWhatWeMeasure),
        ("GA Optimization",   SceneGA),
        ("PCB Analogy",       ScenePCB),
        ("Molecular Energy",  SceneMolecular),
        ("Summary",           SceneSummary),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(960, 600)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._scenes  = [cls() for _, cls in self.SCENE_DEFS]
        self._current = 0
        self._elapsed = 0
        self._paused  = False
        self._timer   = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        if self._paused:
            return
        self._elapsed += 16
        scene = self._scenes[self._current]
        scene.elapsed = self._elapsed
        if self._elapsed >= scene.duration:
            nxt = (self._current + 1) % len(self._scenes)
            self._goto(nxt)
        self.update()

    def _goto(self, idx):
        self._current = idx
        self._elapsed = 0
        self._scenes[idx].elapsed = 0
        self.scene_changed.emit(idx, len(self._scenes))

    def next_scene(self):
        if self._current < len(self._scenes)-1:
            self._goto(self._current+1)

    def prev_scene(self):
        if self._current > 0:
            self._goto(self._current-1)

    def toggle_pause(self):
        self._paused = not self._paused
        return self._paused

    def restart(self):
        for s in self._scenes:
            s.elapsed = 0
        self._paused = False
        self._goto(0)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        self._scenes[self._current].paint(p, self.width(), self.height())


# ─────────────────────────────────────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "Quantum Processor Architecture Optimization — Visualization"
        )
        self.setMinimumSize(1060, 700)
        self.resize(1260, 800)

        central = QWidget()
        self.setCentralWidget(central)
        vbox = QVBoxLayout(central)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        self.canvas = VisualizationCanvas()
        vbox.addWidget(self.canvas, 1)
        vbox.addWidget(self._build_controls())

        self.canvas.scene_changed.connect(self._on_scene_changed)
        self._update_label(0)

        self.setStyleSheet("QMainWindow { background: #F0F6FF; }")

    def _build_controls(self):
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet("""
            QWidget  { background:#0D2B5E; border-top:1px solid #1565C0; }
            QPushButton {
                background:#1565C0; color:white; border:none;
                border-radius:6px; padding:6px 20px;
                font-family:Georgia; font-size:11px; min-width:76px;
            }
            QPushButton:hover   { background:#1E88E5; }
            QPushButton:pressed { background:#0D47A1; }
            QLabel {
                color:#BBDEFB; font-family:Georgia; font-size:11px;
                background:transparent;
            }
        """)
        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 6, 16, 6)
        h.setSpacing(10)

        self.btn_prev    = QPushButton("◀  Prev")
        self.btn_pause   = QPushButton("⏸  Pause")
        self.btn_next    = QPushButton("Next  ▶")
        self.btn_restart = QPushButton("↺  Restart")
        self.scene_label = QLabel()
        self.scene_label.setAlignment(Qt.AlignCenter)

        self.btn_prev.clicked.connect(self.canvas.prev_scene)
        self.btn_next.clicked.connect(self.canvas.next_scene)
        self.btn_pause.clicked.connect(self._toggle_pause)
        self.btn_restart.clicked.connect(self.canvas.restart)

        for w in (self.btn_prev, self.btn_pause, self.btn_next):
            h.addWidget(w)
        h.addSpacing(20)
        h.addWidget(self.scene_label, 1)
        h.addWidget(self.btn_restart)
        return bar

    def _toggle_pause(self):
        paused = self.canvas.toggle_pause()
        self.btn_pause.setText("▶  Resume" if paused else "⏸  Pause")

    def _on_scene_changed(self, idx, _total):
        self._update_label(idx)

    def _update_label(self, idx):
        name = self.canvas.SCENE_DEFS[idx][0]
        total = len(self.canvas.SCENE_DEFS)
        self.scene_label.setText(f"Scene {idx+1} / {total}  —  {name}")

    def keyPressEvent(self, event):
        key = event.key()
        if   key == Qt.Key_Right: self.canvas.next_scene()
        elif key == Qt.Key_Left:  self.canvas.prev_scene()
        elif key == Qt.Key_Space: self._toggle_pause()
        elif key == Qt.Key_R:     self.canvas.restart()
        elif key == Qt.Key_Escape:self.close()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Quantum Architecture Viz")
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
