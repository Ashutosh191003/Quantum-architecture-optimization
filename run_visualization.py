"""
run_visualization.py
====================
Animated visualization for the Quantum Processor Architecture Optimization project.
Based on: "A superconducting quantum processor architecture design method for
improving performance and reducing frequency collisions" (Yang et al., 2023)

Demonstrates the optimization on qpe_n9 (9-qubit Quantum Phase Estimation).

Usage:
    python run_visualization.py

Dependencies:
    pip install PyQt5
"""

import sys
import math
import random
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QGraphicsOpacityEffect, QSizePolicy, QFrame
)
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QPointF, QRectF,
    pyqtSignal, QObject, QThread
)
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QFontMetrics,
    QLinearGradient, QRadialGradient, QPainterPath, QPolygonF
)

# ─────────────────────────────────────────────────────────────────────────────
# PALETTE  (white + blue theme)
# ─────────────────────────────────────────────────────────────────────────────
C_BG          = QColor("#F0F6FF")       # very light blue-white
C_PANEL       = QColor("#FFFFFF")       # pure white panels
C_NAVY        = QColor("#0D2B5E")       # deep navy
C_BLUE        = QColor("#1565C0")       # primary blue
C_BLUE_MID    = QColor("#1E88E5")       # mid blue
C_BLUE_LIGHT  = QColor("#64B5F6")       # light blue
C_BLUE_PALE   = QColor("#BBDEFB")       # very pale blue
C_ACCENT      = QColor("#0288D1")       # cyan-blue accent
C_WHITE       = QColor("#FFFFFF")
C_TEXT        = QColor("#0D2B5E")
C_TEXT_LIGHT  = QColor("#546E8A")
C_GOOD        = QColor("#1565C0")
C_GOLD        = QColor("#FFB300")       # highlight / winner
C_EDGE_IBM    = QColor("#90A4AE")
C_EDGE_OUR    = QColor("#1E88E5")
C_NODE_IBM    = QColor("#B0BEC5")
C_NODE_OUR    = QColor("#1565C0")
C_NODE_ACTIVE = QColor("#0288D1")

# ─────────────────────────────────────────────────────────────────────────────
# REAL DATA  (qpe_n9, from Fig.12 of paper)
# ─────────────────────────────────────────────────────────────────────────────
QPE_IBM_GATES  = 248
QPE_IBM_YIELD  = 0.023
QPE_EFF_GATES  = 215
QPE_EFF_YIELD  = 0.19
QPE_OUR_GATES  = 192
QPE_OUR_YIELD  = 0.41

# IBM 20-qubit square-lattice edges (Penguin V3 style, subset shown)
IBM_EDGES_20 = [
    (0,1),(1,2),(2,3),(3,4),
    (5,6),(6,7),(7,8),(8,9),
    (10,11),(11,12),(12,13),(13,14),
    (15,16),(16,17),(17,18),(18,19),
    (0,5),(1,6),(2,7),(3,8),(4,9),
    (5,10),(6,11),(7,12),(8,13),(9,14),
    (10,15),(11,16),(12,17),(13,18),(14,19),
]

# 9-qubit QPE topology (ring + star-like connections)
QPE_TOPO_EDGES = [
    (0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,8),(8,0),
    (0,4),(1,5),(2,6)
]

# IBM layout positions (5×4 grid for 20 qubits)
def ibm_positions():
    pos = {}
    for i in range(20):
        row = i // 5
        col = i % 5
        pos[i] = (col * 80 + 40, row * 70 + 40)
    return pos

# Random initial layout for 9 qubits
def random_layout_9(w, h, seed=42):
    rng = random.Random(seed)
    pos = {}
    margin = 60
    for i in range(9):
        pos[i] = (rng.randint(margin, w - margin),
                  rng.randint(margin, h - margin))
    return pos

# Optimised layout for 9 qubits (ring layout = best for qpe)
def optimal_layout_9(cx, cy, r=110):
    pos = {}
    for i in range(9):
        angle = 2 * math.pi * i / 9 - math.pi / 2
        pos[i] = (cx + r * math.cos(angle), cy + r * math.sin(angle))
    return pos

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def lerp(a, b, t):
    return a + (b - a) * t

def lerp_pt(p0, p1, t):
    return (lerp(p0[0], p1[0], t), lerp(p0[1], p1[1], t))

def ease_in_out(t):
    return t * t * (3 - 2 * t)

def draw_rounded_rect(painter, x, y, w, h, r, color, border=None):
    painter.save()
    painter.setBrush(QBrush(color))
    if border:
        painter.setPen(QPen(border, 1.5))
    else:
        painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(int(x), int(y), int(w), int(h), r, r)
    painter.restore()

def draw_node(painter, x, y, radius, fill_color, label="", label_color=None,
              border_color=None, border_width=2, glow=False):
    painter.save()
    if glow:
        glow_color = QColor(fill_color)
        glow_color.setAlpha(40)
        painter.setBrush(QBrush(glow_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QPointF(x, y), radius + 8, radius + 8)

    painter.setBrush(QBrush(fill_color))
    bc = border_color if border_color else C_WHITE
    painter.setPen(QPen(bc, border_width))
    painter.drawEllipse(QPointF(x, y), radius, radius)

    if label:
        lc = label_color if label_color else C_WHITE
        painter.setPen(QPen(lc))
        font = QFont("Courier New", 8, QFont.Bold)
        painter.setFont(font)
        painter.drawText(
            QRectF(x - radius, y - radius, radius * 2, radius * 2),
            Qt.AlignCenter, label
        )
    painter.restore()

def draw_edge(painter, p0, p1, color, width=1.5, alpha=180):
    c = QColor(color)
    c.setAlpha(alpha)
    painter.save()
    painter.setPen(QPen(c, width))
    painter.drawLine(QPointF(p0[0], p0[1]), QPointF(p1[0], p1[1]))
    painter.restore()


# ─────────────────────────────────────────────────────────────────────────────
# SCENE BASE
# ─────────────────────────────────────────────────────────────────────────────
class Scene:
    """Base class for animation scenes."""
    def __init__(self, duration_ms):
        self.duration = duration_ms
        self.elapsed = 0   # updated externally

    @property
    def t(self):
        """Normalised time 0→1."""
        return min(1.0, self.elapsed / max(1, self.duration))

    def paint(self, painter, w, h):
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 0 — INTRO
# ─────────────────────────────────────────────────────────────────────────────
class SceneIntro(Scene):
    def __init__(self):
        super().__init__(4000)

    def paint(self, painter, w, h):
        t = self.t
        fade = min(1.0, t * 3) * min(1.0, (1 - t) * 8 + 0.3)

        # Background gradient
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, QColor("#0D2B5E"))
        grad.setColorAt(1, QColor("#1565C0"))
        painter.fillRect(0, 0, w, h, QBrush(grad))

        # Floating circuit dots
        rng = random.Random(7)
        painter.save()
        for _ in range(30):
            x = rng.randint(0, w)
            y = rng.randint(0, h)
            r = rng.randint(2, 5)
            c = QColor(255, 255, 255, int(30 * fade))
            painter.setBrush(QBrush(c))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(x, y), r, r)
        painter.restore()

        alpha = int(255 * fade)

        # Title
        painter.save()
        c = QColor(255, 255, 255, alpha)
        painter.setPen(QPen(c))
        font = QFont("Georgia", 28, QFont.Bold)
        painter.setFont(font)
        painter.drawText(
            QRectF(0, h * 0.22, w, 60), Qt.AlignCenter,
            "Quantum Processor Architecture Optimization"
        )
        painter.restore()

        # Subtitle
        painter.save()
        c2 = QColor(180, 210, 255, alpha)
        painter.setPen(QPen(c2))
        font2 = QFont("Georgia", 14)
        painter.setFont(font2)
        painter.drawText(
            QRectF(0, h * 0.35, w, 40), Qt.AlignCenter,
            "Improving Performance & Reducing Frequency Collisions"
        )
        painter.restore()

        # Program tag
        painter.save()
        tag_alpha = int(255 * min(1.0, max(0, t - 0.3) * 5) * min(1.0, (1 - t) * 8 + 0.3))
        c3 = QColor(100, 181, 246, tag_alpha)
        painter.setPen(QPen(c3))
        font3 = QFont("Courier New", 13)
        painter.setFont(font3)
        painter.drawText(
            QRectF(0, h * 0.50, w, 35), Qt.AlignCenter,
            "Demo: qpe_n9  —  9-Qubit Quantum Phase Estimation"
        )
        painter.restore()

        # Bottom line
        painter.save()
        line_alpha = int(180 * fade)
        lc = QColor(100, 181, 246, line_alpha)
        painter.setPen(QPen(lc, 1))
        painter.drawLine(int(w * 0.2), int(h * 0.62),
                         int(w * 0.8), int(h * 0.62))
        painter.restore()

        # Authors note
        painter.save()
        c4 = QColor(144, 202, 249, int(200 * fade))
        painter.setPen(QPen(c4))
        font4 = QFont("Georgia", 10)
        painter.setFont(font4)
        painter.drawText(
            QRectF(0, h * 0.66, w, 30), Qt.AlignCenter,
            "Based on Yang et al., Results in Physics 53 (2023) 106944"
        )
        painter.restore()


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 1 — IBM GENERAL PURPOSE ARCHITECTURE
# ─────────────────────────────────────────────────────────────────────────────
class SceneIBM(Scene):
    def __init__(self):
        super().__init__(7000)
        self._ibm_pos = None
        self._highlight_nodes = {0, 2, 4, 6, 8, 10, 12, 14, 16}  # 9 used qubits

    def _get_ibm_pos(self, w, h):
        if self._ibm_pos is None:
            ox = w * 0.12
            oy = h * 0.18
            self._ibm_pos = {}
            for i in range(20):
                row = i // 5
                col = i % 5
                self._ibm_pos[i] = (ox + col * (w * 0.55 / 4),
                                     oy + row * (h * 0.55 / 3))
        return self._ibm_pos

    def paint(self, painter, w, h):
        t = self.t
        fade_in = min(1.0, t * 4)

        # Background
        painter.fillRect(0, 0, w, h, QBrush(C_BG))

        pos = self._get_ibm_pos(w, h)

        # Section header
        self._draw_header(painter, w, h, "Step 1: IBM General-Purpose Architecture",
                          "20-qubit square lattice  •  Fixed frequency stripe pattern",
                          fade_in)

        # Draw edges
        painter.save()
        for (a, b) in IBM_EDGES_20:
            ea = int(100 * fade_in)
            draw_edge(painter, pos[a], pos[b], C_EDGE_IBM, 1.2, ea)
        painter.restore()

        # Draw nodes
        node_appear = min(1.0, t * 5)
        for i in range(20):
            alpha_factor = min(1.0, node_appear + (0.3 if i in self._highlight_nodes else 0))
            if i in self._highlight_nodes:
                col = QColor(C_NODE_OUR)
                col.setAlpha(int(220 * fade_in))
                draw_node(painter, pos[i][0], pos[i][1], 13,
                          col, f"Q{i}", C_WHITE, C_WHITE, 1.5,
                          glow=(t > 0.5))
            else:
                col = QColor(C_NODE_IBM)
                col.setAlpha(int(150 * fade_in))
                draw_node(painter, pos[i][0], pos[i][1], 10,
                          col, f"Q{i}", QColor(80, 80, 80), C_WHITE, 1)

        # Metrics panel (appears at t>0.5)
        if t > 0.45:
            mp_alpha = min(1.0, (t - 0.45) * 6)
            self._draw_metrics_panel(painter, w, h, mp_alpha,
                                     QPE_IBM_GATES, QPE_IBM_YIELD, "IBM Baseline")

        # Annotation bubble
        if t > 0.6:
            ann_alpha = min(1.0, (t - 0.6) * 5)
            self._draw_annotation(painter, w, h, ann_alpha,
                                  pos[6][0] + 20, pos[6][1] - 30,
                                  "9 qubits used\nfrom 20-qubit device")

        # Legend
        if t > 0.7:
            leg_alpha = min(1.0, (t - 0.7) * 5)
            self._draw_legend(painter, w, h, leg_alpha)

    def _draw_header(self, painter, w, h, title, subtitle, alpha):
        # Top bar
        bar_color = QColor(C_NAVY)
        bar_color.setAlpha(int(240 * alpha))
        painter.save()
        painter.setBrush(QBrush(bar_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(int(w * 0.03), int(h * 0.03),
                                int(w * 0.94), 52, 8, 8)

        c = QColor(255, 255, 255, int(240 * alpha))
        painter.setPen(QPen(c))
        painter.setFont(QFont("Georgia", 14, QFont.Bold))
        painter.drawText(QRectF(w * 0.03, h * 0.03, w * 0.94, 52),
                         Qt.AlignCenter, title)
        painter.restore()

        # Subtitle
        painter.save()
        c2 = QColor(C_TEXT_LIGHT)
        c2.setAlpha(int(200 * alpha))
        painter.setPen(QPen(c2))
        painter.setFont(QFont("Georgia", 10))
        painter.drawText(QRectF(0, h * 0.03 + 58, w, 24),
                         Qt.AlignCenter, subtitle)
        painter.restore()

    def _draw_metrics_panel(self, painter, w, h, alpha,
                             gates, yld, label):
        px = w * 0.70
        py = h * 0.20
        pw = w * 0.26
        ph = h * 0.55

        # Panel bg
        bg = QColor(C_PANEL)
        bg.setAlpha(int(240 * alpha))
        draw_rounded_rect(painter, px, py, pw, ph, 10, bg, C_BLUE_PALE)

        painter.save()
        # Label
        lc = QColor(C_NAVY)
        lc.setAlpha(int(230 * alpha))
        painter.setPen(QPen(lc))
        painter.setFont(QFont("Georgia", 11, QFont.Bold))
        painter.drawText(QRectF(px, py + 12, pw, 28), Qt.AlignCenter, label)

        # Divider
        dc = QColor(C_BLUE_PALE)
        dc.setAlpha(int(200 * alpha))
        painter.setPen(QPen(dc, 1))
        painter.drawLine(int(px + 15), int(py + 45),
                         int(px + pw - 15), int(py + 45))

        # Gate count
        self._metric_row(painter, px, py + 58, pw, alpha,
                         "SWAP Gate Count", f"{gates}", C_BLUE)

        # Yield
        self._metric_row(painter, px, py + 130, pw, alpha,
                         "Yield Rate", f"{yld:.3f}", C_BLUE)

        # Explanation
        painter.setPen(QPen(QColor(C_TEXT_LIGHT.red(),
                                   C_TEXT_LIGHT.green(),
                                   C_TEXT_LIGHT.blue(), int(180 * alpha))))
        painter.setFont(QFont("Georgia", 8))
        painter.drawText(
            QRectF(px + 10, py + ph - 95, pw - 20, 80),
            Qt.AlignLeft | Qt.TextWordWrap,
            "Yield Rate = probability that no\nfrequency collisions occur.\n\n"
            "Higher yield → lower collision\nprobability → more reliable chip."
        )
        painter.restore()

    def _metric_row(self, painter, x, y, pw, alpha, name, value, vcolor):
        painter.save()
        nc = QColor(C_TEXT_LIGHT)
        nc.setAlpha(int(200 * alpha))
        painter.setPen(QPen(nc))
        painter.setFont(QFont("Georgia", 9))
        painter.drawText(QRectF(x + 10, y, pw - 20, 22), Qt.AlignLeft, name)

        vc = QColor(vcolor)
        vc.setAlpha(int(230 * alpha))
        painter.setPen(QPen(vc))
        painter.setFont(QFont("Courier New", 18, QFont.Bold))
        painter.drawText(QRectF(x + 10, y + 20, pw - 20, 40),
                         Qt.AlignLeft, value)
        painter.restore()

    def _draw_annotation(self, painter, w, h, alpha, ax, ay, text):
        painter.save()
        bg = QColor(C_GOLD)
        bg.setAlpha(int(220 * alpha))
        painter.setBrush(QBrush(bg))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(int(ax), int(ay - 28), 130, 38, 6, 6)

        tc = QColor(50, 30, 0, int(230 * alpha))
        painter.setPen(QPen(tc))
        painter.setFont(QFont("Georgia", 8))
        painter.drawText(QRectF(ax + 4, ay - 28, 122, 38),
                         Qt.AlignCenter | Qt.TextWordWrap, text)
        painter.restore()

    def _draw_legend(self, painter, w, h, alpha):
        painter.save()
        lx = w * 0.03
        ly = h * 0.82
        # Blue node = used, grey = unused
        draw_node(painter, lx + 12, ly + 12, 10,
                  QColor(C_NODE_OUR.red(), C_NODE_OUR.green(),
                         C_NODE_OUR.blue(), int(200 * alpha)),
                  "", None, C_WHITE, 1.5)
        tc = QColor(C_TEXT)
        tc.setAlpha(int(200 * alpha))
        painter.setPen(QPen(tc))
        painter.setFont(QFont("Georgia", 9))
        painter.drawText(int(lx + 28), int(ly + 17), "Active qubits (qpe_n9)")

        draw_node(painter, lx + 12, ly + 35, 8,
                  QColor(C_NODE_IBM.red(), C_NODE_IBM.green(),
                         C_NODE_IBM.blue(), int(160 * alpha)),
                  "", None, C_WHITE, 1)
        painter.drawText(int(lx + 28), int(ly + 40), "Inactive qubits")
        painter.restore()


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 2 — GENETIC ALGORITHM OPTIMIZATION
# ─────────────────────────────────────────────────────────────────────────────
class SceneGA(Scene):
    def __init__(self):
        super().__init__(12000)
        self._rand_pos = None
        self._opt_pos = None

    def _ensure_positions(self, w, h):
        if self._rand_pos is None:
            cx = w * 0.25
            cy = h * 0.52
            self._rand_pos = random_layout_9(int(w * 0.42), int(h * 0.7), seed=99)
            # Shift into left panel
            for i in self._rand_pos:
                x, y = self._rand_pos[i]
                self._rand_pos[i] = (x * 0.38 + w * 0.06,
                                     y * 0.6 + h * 0.2)
        if self._opt_pos is None:
            cx = w * 0.27
            cy = h * 0.52
            self._opt_pos = optimal_layout_9(cx, cy, r=min(w, h) * 0.17)

    def paint(self, painter, w, h):
        t = self.t
        self._ensure_positions(w, h)

        painter.fillRect(0, 0, w, h, QBrush(C_BG))

        # Phases:
        # 0.00-0.15  fade in header + random layout
        # 0.15-0.55  GA progress bar animates, nodes morph
        # 0.55-0.75  optimal layout shown, metrics updated
        # 0.75-1.00  tooltip / explanation cards

        fade = min(1.0, t * 5)

        # Header
        self._draw_header(painter, w, h, fade)

        # Split line
        painter.save()
        lc = QColor(C_BLUE_PALE)
        lc.setAlpha(int(180 * fade))
        painter.setPen(QPen(lc, 1, Qt.DashLine))
        painter.drawLine(int(w * 0.51), int(h * 0.14),
                         int(w * 0.51), int(h * 0.88))
        painter.restore()

        # Left side label
        self._draw_side_label(painter, w * 0.27, h * 0.15,
                              "Random Initial Layout", fade)
        # Right side label
        self._draw_side_label(painter, w * 0.76, h * 0.15,
                              "Optimised Architecture", fade)

        # Node positions: interpolate after t>0.25
        node_t = max(0.0, min(1.0, (t - 0.25) / 0.40))
        smooth_t = ease_in_out(node_t)

        # Draw LEFT graph (random, fades to dim after optimization)
        left_alpha = int(220 * fade * (1 - smooth_t * 0.5))
        self._draw_graph(painter, self._rand_pos, QPE_TOPO_EDGES,
                         C_BLUE_LIGHT, C_NODE_IBM, left_alpha, "left", smooth_t)

        # Draw RIGHT graph (morphing from random to optimal)
        for i in range(9):
            rp = self._rand_pos[i]
            op = self._opt_pos[i]
            mx = lerp(rp[0] + w * 0.51, op[0] + w * 0.51, smooth_t)
            my = lerp(rp[1], op[1], smooth_t)
            # Shift left random to right panel
            rx = rp[0] + w * 0.51
            ry = rp[1]
            ox2 = op[0] + w * 0.50
            oy2 = op[1]
            merged = (lerp(rx, ox2, smooth_t), lerp(ry, oy2, smooth_t))
            self._right_pos_cache = getattr(self, '_right_pos_cache', {})
            self._right_pos_cache[i] = merged

        rc = getattr(self, '_right_pos_cache', {})
        if rc:
            right_alpha = int(200 * fade)
            nc = QColor(C_NODE_OUR)
            nc.setAlpha(right_alpha)
            ec = QColor(C_EDGE_OUR)
            ec.setAlpha(int(160 * fade))

            for (a, b) in QPE_TOPO_EDGES:
                if a in rc and b in rc:
                    draw_edge(painter, rc[a], rc[b], ec, 2.0, int(150 * fade * (0.3 + smooth_t * 0.7)))

            for i in rc:
                glow = smooth_t > 0.8
                draw_node(painter, rc[i][0], rc[i][1], 14,
                          nc, f"Q{i}", C_WHITE, C_WHITE, 2, glow=glow)

        # GA Progress bar
        ga_t = min(1.0, max(0.0, (t - 0.10) / 0.45))
        self._draw_ga_bar(painter, w, h, ga_t, fade)

        # Metrics comparison
        if t > 0.55:
            m_alpha = min(1.0, (t - 0.55) * 5)
            self._draw_metrics_comparison(painter, w, h, m_alpha, smooth_t)

        # Lambda info popup
        if t > 0.70:
            p_alpha = min(1.0, (t - 0.70) * 5)
            self._draw_lambda_popup(painter, w, h, p_alpha)

    def _draw_graph(self, painter, pos, edges, edge_col, node_col,
                    alpha, side, morph_t):
        for (a, b) in edges:
            if a in pos and b in pos:
                draw_edge(painter, pos[a], pos[b],
                          QColor(edge_col.red(), edge_col.green(),
                                 edge_col.blue(), int(alpha * 0.6)), 1.5)
        for i in pos:
            nc = QColor(node_col.red(), node_col.green(),
                        node_col.blue(), alpha)
            draw_node(painter, pos[i][0], pos[i][1], 12,
                      nc, f"Q{i}",
                      QColor(255, 255, 255, alpha), C_WHITE, 1.5)

    def _draw_header(self, painter, w, h, alpha):
        bar_color = QColor(C_NAVY)
        bar_color.setAlpha(int(240 * alpha))
        painter.save()
        painter.setBrush(QBrush(bar_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(int(w * 0.03), int(h * 0.03),
                                int(w * 0.94), 52, 8, 8)
        c = QColor(255, 255, 255, int(240 * alpha))
        painter.setPen(QPen(c))
        painter.setFont(QFont("Georgia", 14, QFont.Bold))
        painter.drawText(QRectF(w * 0.03, h * 0.03, w * 0.94, 52),
                         Qt.AlignCenter,
                         "Step 2: Genetic Algorithm Optimization  (λ sweep 1→6)")
        painter.restore()

        painter.save()
        c2 = QColor(C_TEXT_LIGHT)
        c2.setAlpha(int(180 * alpha))
        painter.setPen(QPen(c2))
        painter.setFont(QFont("Georgia", 10))
        painter.drawText(QRectF(0, h * 0.03 + 58, w, 24),
                         Qt.AlignCenter,
                         "Optimising: Σd(i,j) [gate count] + λ·Δ(G) [max degree / yield]")
        painter.restore()

    def _draw_side_label(self, painter, cx, y, text, alpha):
        painter.save()
        c = QColor(C_NAVY)
        c.setAlpha(int(200 * alpha))
        painter.setPen(QPen(c))
        painter.setFont(QFont("Georgia", 11, QFont.Bold))
        painter.drawText(QRectF(cx - 120, y, 240, 26), Qt.AlignCenter, text)
        painter.restore()

    def _draw_ga_bar(self, painter, w, h, ga_t, alpha):
        bx = w * 0.06
        by = h * 0.84
        bw = w * 0.88
        bh = 22

        # Background track
        bg = QColor(C_BLUE_PALE)
        bg.setAlpha(int(200 * alpha))
        draw_rounded_rect(painter, bx, by, bw, bh, 11, bg)

        # Fill
        fill_w = bw * ga_t
        if fill_w > 4:
            grad = QLinearGradient(bx, 0, bx + fill_w, 0)
            grad.setColorAt(0, QColor("#1565C0"))
            grad.setColorAt(1, QColor("#0288D1"))
            painter.save()
            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(bx), int(by), int(fill_w), int(bh), 11, 11)
            painter.restore()

        # Label
        painter.save()
        lam = max(1, int(ga_t * 6))
        iteration = int(ga_t * 300)
        lc = QColor(C_NAVY)
        lc.setAlpha(int(220 * alpha))
        painter.setPen(QPen(lc))
        painter.setFont(QFont("Courier New", 9, QFont.Bold))
        painter.drawText(
            QRectF(bx, by - 22, bw, 20), Qt.AlignLeft,
            f"  GA Running — λ={lam}  |  Iteration: {iteration}/300  |"
            f"  Best fitness: {-3.5 + ga_t * 2.8:.2f}"
        )
        painter.restore()

    def _draw_metrics_comparison(self, painter, w, h, alpha, smooth_t):
        # Small cards at bottom
        cards = [
            ("IBM Baseline", QPE_IBM_GATES, QPE_IBM_YIELD, C_NODE_IBM),
            ("eff-5-freq",   QPE_EFF_GATES, QPE_EFF_YIELD, C_BLUE_LIGHT),
            ("Ours  ✓",      QPE_OUR_GATES, QPE_OUR_YIELD, C_NODE_OUR),
        ]
        card_w = w * 0.24
        gap = w * 0.04
        start_x = (w - (card_w * 3 + gap * 2)) / 2
        cy = h * 0.87

        for idx, (name, gates, yld, col) in enumerate(cards):
            cx = start_x + idx * (card_w + gap)
            is_ours = idx == 2

            bg = QColor(C_PANEL)
            if is_ours:
                bg = QColor("#E3F2FD")
            bg.setAlpha(int(230 * alpha))
            bc = QColor(col)
            bc.setAlpha(int(180 * alpha))
            draw_rounded_rect(painter, cx, cy, card_w, h * 0.11, 8, bg, bc)

            painter.save()
            nc = QColor(col)
            nc.setAlpha(int(220 * alpha))
            painter.setPen(QPen(nc))
            painter.setFont(QFont("Georgia", 9, QFont.Bold if is_ours else QFont.Normal))
            painter.drawText(QRectF(cx, cy + 4, card_w, 20), Qt.AlignCenter, name)

            tc = QColor(C_NAVY)
            tc.setAlpha(int(200 * alpha))
            painter.setPen(QPen(tc))
            painter.setFont(QFont("Courier New", 11, QFont.Bold))
            painter.drawText(QRectF(cx, cy + 22, card_w, 24),
                             Qt.AlignCenter, f"{gates} gates")
            painter.drawText(QRectF(cx, cy + 42, card_w, 24),
                             Qt.AlignCenter, f"yield={yld:.3f}")

            if is_ours:
                gold = QColor(C_GOLD)
                gold.setAlpha(int(220 * alpha))
                painter.setPen(QPen(gold))
                painter.setFont(QFont("Georgia", 8, QFont.Bold))
                painter.drawText(QRectF(cx, cy + 62, card_w, 18),
                                 Qt.AlignCenter, "Best Result ★")
            painter.restore()

    def _draw_lambda_popup(self, painter, w, h, alpha):
        px = w * 0.59
        py = h * 0.50
        pw = 200
        ph = 90

        bg = QColor(C_NAVY)
        bg.setAlpha(int(220 * alpha))
        draw_rounded_rect(painter, px, py, pw, ph, 8, bg)

        painter.save()
        tc = QColor(255, 255, 255, int(230 * alpha))
        painter.setPen(QPen(tc))
        painter.setFont(QFont("Georgia", 9))
        painter.drawText(
            QRectF(px + 8, py + 8, pw - 16, ph - 16),
            Qt.AlignLeft | Qt.TextWordWrap,
            "λ controls trade-off:\n"
            "Low λ → prioritise fewer\nSWAP gates (performance)\n"
            "High λ → prioritise lower\nmax-degree (yield rate)"
        )
        painter.restore()


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 3 — COMPARISON CHART
# ─────────────────────────────────────────────────────────────────────────────
class SceneCompare(Scene):
    def __init__(self):
        super().__init__(8000)

    def paint(self, painter, w, h):
        t = self.t
        fade = min(1.0, t * 4)

        painter.fillRect(0, 0, w, h, QBrush(C_BG))
        self._draw_header(painter, w, h, fade)

        bar_t = min(1.0, max(0, (t - 0.15) / 0.55))
        smooth = ease_in_out(bar_t)

        self._draw_gate_chart(painter, w, h, smooth, fade)
        self._draw_yield_chart(painter, w, h, smooth, fade)

        if t > 0.75:
            self._draw_summary(painter, w, h, min(1.0, (t - 0.75) * 4))

    def _draw_header(self, painter, w, h, alpha):
        bar_color = QColor(C_NAVY)
        bar_color.setAlpha(int(240 * alpha))
        painter.save()
        painter.setBrush(QBrush(bar_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(int(w * 0.03), int(h * 0.03),
                                int(w * 0.94), 52, 8, 8)
        c = QColor(255, 255, 255, int(240 * alpha))
        painter.setPen(QPen(c))
        painter.setFont(QFont("Georgia", 14, QFont.Bold))
        painter.drawText(QRectF(w * 0.03, h * 0.03, w * 0.94, 52),
                         Qt.AlignCenter,
                         "Step 3: Performance Comparison  —  qpe_n9")
        painter.restore()

        painter.save()
        c2 = QColor(C_TEXT_LIGHT)
        c2.setAlpha(int(180 * alpha))
        painter.setPen(QPen(c2))
        painter.setFont(QFont("Georgia", 10))
        painter.drawText(QRectF(0, h * 0.03 + 58, w, 24),
                         Qt.AlignCenter,
                         "Lower gate count = better performance  •  "
                         "Higher yield = fewer frequency collisions")
        painter.restore()

    def _draw_gate_chart(self, painter, w, h, t, alpha):
        # Left bar chart — gate count (lower is better)
        data = [
            ("IBM\nPenguin V3", QPE_IBM_GATES, C_NODE_IBM),
            ("eff-5-freq",      QPE_EFF_GATES, C_BLUE_LIGHT),
            ("Ours",            QPE_OUR_GATES, C_NODE_OUR),
        ]
        chart_x = w * 0.06
        chart_y = h * 0.18
        chart_w = w * 0.40
        chart_h = h * 0.55
        max_val = 280

        self._draw_chart_frame(painter, chart_x, chart_y, chart_w, chart_h,
                               alpha, "SWAP Gate Count  (lower = better ↓)")

        bar_w = chart_w * 0.18
        gap = chart_w * 0.10
        start_x = chart_x + chart_w * 0.10
        for idx, (name, val, col) in enumerate(data):
            bx = start_x + idx * (bar_w + gap)
            bar_h = (val / max_val) * chart_h * 0.80 * t
            by = chart_y + chart_h * 0.88 - bar_h

            is_ours = idx == 2
            bc = QColor(col)
            bc.setAlpha(int(220 * alpha))

            if is_ours:
                grad = QLinearGradient(bx, by, bx, by + bar_h)
                grad.setColorAt(0, QColor("#0288D1"))
                grad.setColorAt(1, QColor("#0D47A1"))
                painter.save()
                painter.setBrush(QBrush(grad))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(int(bx), int(by),
                                        int(bar_w), int(bar_h), 4, 4)
                painter.restore()
            else:
                draw_rounded_rect(painter, bx, by, bar_w, bar_h, 4, bc)

            # Value label
            painter.save()
            vc = QColor(C_NAVY)
            vc.setAlpha(int(220 * alpha))
            painter.setPen(QPen(vc))
            painter.setFont(QFont("Courier New", 10, QFont.Bold))
            painter.drawText(QRectF(bx, by - 24, bar_w, 22),
                             Qt.AlignCenter, str(val))

            # Name label
            painter.setFont(QFont("Georgia", 8))
            painter.drawText(
                QRectF(bx - 5, chart_y + chart_h * 0.90,
                       bar_w + 10, 30),
                Qt.AlignCenter | Qt.TextWordWrap, name
            )

            # Winner star
            if is_ours and t > 0.9:
                sc = QColor(C_GOLD)
                sc.setAlpha(int(220 * alpha))
                painter.setPen(QPen(sc))
                painter.setFont(QFont("Georgia", 14, QFont.Bold))
                painter.drawText(QRectF(bx, by - 44, bar_w, 24),
                                 Qt.AlignCenter, "★")
            painter.restore()

    def _draw_yield_chart(self, painter, w, h, t, alpha):
        data = [
            ("IBM\nPenguin V3", QPE_IBM_YIELD, C_NODE_IBM),
            ("eff-5-freq",      QPE_EFF_YIELD, C_BLUE_LIGHT),
            ("Ours",            QPE_OUR_YIELD, C_NODE_OUR),
        ]
        chart_x = w * 0.54
        chart_y = h * 0.18
        chart_w = w * 0.40
        chart_h = h * 0.55
        max_val = 0.50

        self._draw_chart_frame(painter, chart_x, chart_y, chart_w, chart_h,
                               alpha, "Yield Rate  (higher = better ↑)")

        bar_w = chart_w * 0.18
        gap = chart_w * 0.10
        start_x = chart_x + chart_w * 0.10
        base_y = chart_y + chart_h * 0.88

        for idx, (name, val, col) in enumerate(data):
            bx = start_x + idx * (bar_w + gap)
            bar_h = (val / max_val) * chart_h * 0.80 * t
            by = base_y - bar_h

            is_ours = idx == 2
            bc = QColor(col)
            bc.setAlpha(int(220 * alpha))

            if is_ours:
                grad = QLinearGradient(bx, by, bx, by + bar_h)
                grad.setColorAt(0, QColor("#0288D1"))
                grad.setColorAt(1, QColor("#0D47A1"))
                painter.save()
                painter.setBrush(QBrush(grad))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(int(bx), int(by),
                                        int(bar_w), int(bar_h), 4, 4)
                painter.restore()
            else:
                draw_rounded_rect(painter, bx, by, bar_w, bar_h, 4, bc)

            painter.save()
            vc = QColor(C_NAVY)
            vc.setAlpha(int(220 * alpha))
            painter.setPen(QPen(vc))
            painter.setFont(QFont("Courier New", 10, QFont.Bold))
            painter.drawText(QRectF(bx, by - 24, bar_w, 22),
                             Qt.AlignCenter, f"{val:.3f}")

            painter.setFont(QFont("Georgia", 8))
            painter.drawText(
                QRectF(bx - 5, base_y + 5, bar_w + 10, 30),
                Qt.AlignCenter | Qt.TextWordWrap, name
            )

            if is_ours and t > 0.9:
                sc = QColor(C_GOLD)
                sc.setAlpha(int(220 * alpha))
                painter.setPen(QPen(sc))
                painter.setFont(QFont("Georgia", 14, QFont.Bold))
                painter.drawText(QRectF(bx, by - 44, bar_w, 24),
                                 Qt.AlignCenter, "★")
            painter.restore()

    def _draw_chart_frame(self, painter, cx, cy, cw, ch, alpha, title):
        bg = QColor(C_PANEL)
        bg.setAlpha(int(230 * alpha))
        draw_rounded_rect(painter, cx, cy, cw, ch, 10, bg, C_BLUE_PALE)

        painter.save()
        tc = QColor(C_NAVY)
        tc.setAlpha(int(200 * alpha))
        painter.setPen(QPen(tc))
        painter.setFont(QFont("Georgia", 10, QFont.Bold))
        painter.drawText(QRectF(cx, cy + 8, cw, 24), Qt.AlignCenter, title)

        # Baseline line
        lc = QColor(C_BLUE_PALE)
        lc.setAlpha(int(180 * alpha))
        painter.setPen(QPen(lc, 1, Qt.DashLine))
        painter.drawLine(int(cx + 15), int(cy + ch * 0.88),
                         int(cx + cw - 15), int(cy + ch * 0.88))
        painter.restore()

    def _draw_summary(self, painter, w, h, alpha):
        sx = w * 0.06
        sy = h * 0.78
        sw = w * 0.88
        sh = h * 0.15

        bg = QColor(C_NAVY)
        bg.setAlpha(int(230 * alpha))
        draw_rounded_rect(painter, sx, sy, sw, sh, 10, bg)

        painter.save()
        tc = QColor(255, 255, 255, int(230 * alpha))
        painter.setPen(QPen(tc))
        painter.setFont(QFont("Georgia", 11, QFont.Bold))
        painter.drawText(
            QRectF(sx, sy + 8, sw, sh * 0.45),
            Qt.AlignCenter,
            "Our method: 22.6% fewer SWAP gates  •  17.8× higher yield than IBM baseline"
        )
        gc = QColor(C_BLUE_LIGHT)
        gc.setAlpha(int(200 * alpha))
        painter.setPen(QPen(gc))
        painter.setFont(QFont("Georgia", 9))
        painter.drawText(
            QRectF(sx, sy + sh * 0.48, sw, sh * 0.45),
            Qt.AlignCenter,
            "Average across all 16 benchmarks: 15.61% performance improvement  "
            "•  minimum 21.33% reduction in frequency collision probability"
        )
        painter.restore()


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 4 — ECE ANALOGY (PCB Layout)
# ─────────────────────────────────────────────────────────────────────────────
class SceneECE(Scene):
    # Component types
    COMPONENTS = [
        ("MCU",    "#1565C0", 54, 36),
        ("PWR",    "#0277BD", 42, 30),
        ("ADC",    "#0288D1", 38, 26),
        ("SEN-1",  "#0288D1", 32, 24),
        ("SEN-2",  "#0288D1", 32, 24),
        ("CAP",    "#546E8A", 20, 28),
        ("RES",    "#546E8A", 24, 14),
        ("CONN",   "#1B5E20", 36, 20),
    ]

    # Connections (index pairs)
    CONNECTIONS = [
        (0, 1), (0, 2), (0, 3), (0, 4),
        (1, 5), (1, 6), (2, 3), (3, 7),
        (4, 7), (0, 7),
    ]

    def __init__(self):
        super().__init__(10000)
        self._rand_pos = None
        self._opt_pos = None

    def _ensure_positions(self, w, h):
        if self._rand_pos is None:
            rng = random.Random(21)
            self._rand_pos = []
            margin = 80
            bw = w * 0.38
            bh = h * 0.60
            ox = w * 0.06
            oy = h * 0.20
            for _ in self.COMPONENTS:
                self._rand_pos.append((
                    ox + rng.uniform(margin * 0.3, bw - margin * 0.3),
                    oy + rng.uniform(margin * 0.3, bh - margin * 0.3),
                ))

        if self._opt_pos is None:
            # Grid-optimised layout minimising trace length
            # Place MCU centre-ish, sensors near it, power near edge
            bw = w * 0.38
            bh = h * 0.60
            ox = w * 0.06
            oy = h * 0.20
            cx = ox + bw / 2
            cy = oy + bh / 2
            self._opt_pos = [
                (cx,          cy),           # MCU - centre
                (cx - bw*0.30, cy),          # PWR - left
                (cx + bw*0.30, cy - bh*0.20),# ADC - upper right
                (cx,          cy - bh*0.28), # SEN-1 - top
                (cx + bw*0.30, cy + bh*0.20),# SEN-2 - lower right
                (cx - bw*0.30, cy - bh*0.25),# CAP - upper left
                (cx - bw*0.30, cy + bh*0.25),# RES - lower left
                (cx,          cy + bh*0.35), # CONN - bottom
            ]

    def paint(self, painter, w, h):
        t = self.t
        self._ensure_positions(w, h)

        painter.fillRect(0, 0, w, h, QBrush(C_BG))

        fade = min(1.0, t * 4)
        self._draw_header(painter, w, h, fade)

        # Split
        painter.save()
        lc = QColor(C_BLUE_PALE)
        lc.setAlpha(int(160 * fade))
        painter.setPen(QPen(lc, 1, Qt.DashLine))
        painter.drawLine(int(w * 0.51), int(h * 0.15),
                         int(w * 0.51), int(h * 0.88))
        painter.restore()

        # Labels
        self._side_label(painter, w * 0.27, h * 0.15,
                         "Random Component Placement", fade)
        self._side_label(painter, w * 0.76, h * 0.15,
                         "Graph-Optimised PCB Layout", fade)

        # Morphing
        morph_t_raw = max(0.0, min(1.0, (t - 0.30) / 0.45))
        smooth = ease_in_out(morph_t_raw)

        # LEFT (random, dims after morph)
        left_alpha = int(200 * fade * (1 - smooth * 0.6))
        self._draw_pcb(painter, self._rand_pos, left_alpha, offset_x=0)

        # RIGHT (morphing)
        right_positions = []
        right_offset = w * 0.50
        for i in range(len(self.COMPONENTS)):
            rp = self._rand_pos[i]
            op = self._opt_pos[i]
            rx = rp[0] + right_offset
            ry = rp[1]
            ox2 = op[0] + right_offset
            oy2 = op[1]
            right_positions.append((lerp(rx, ox2, smooth),
                                    lerp(ry, oy2, smooth)))

        right_alpha = int(210 * fade)
        self._draw_pcb(painter, right_positions, right_alpha,
                       offset_x=0, is_optimised=True, morph=smooth)

        # Metrics
        if t > 0.60:
            self._draw_pcb_metrics(painter, w, h,
                                   min(1.0, (t - 0.60) * 4), smooth)

        # Analogy card
        if t > 0.78:
            self._draw_analogy_card(painter, w, h,
                                    min(1.0, (t - 0.78) * 5))

    def _draw_pcb(self, painter, positions, alpha, offset_x=0,
                  is_optimised=False, morph=0):
        if alpha < 5:
            return

        # Draw PCB board bg
        bx = positions[0][0] if positions else 0
        # Rough bounding from positions
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]
        if not xs:
            return

        # PCB green tint background per side
        pcb_bg = QColor(0, 40, 20, int(40 * alpha / 200))

        # Draw connections (traces)
        for (a, b) in self.CONNECTIONS:
            if a < len(positions) and b < len(positions):
                pa = positions[a]
                pb = positions[b]
                # Trace color: copper-like
                if is_optimised:
                    tc = QColor(21, 101, 192, int(140 * alpha / 210))
                else:
                    tc = QColor(100, 120, 140, int(100 * alpha / 200))
                painter.save()
                painter.setPen(QPen(tc, 2.0 if is_optimised else 1.5,
                                    Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(QPointF(pa[0], pa[1]),
                                 QPointF(pb[0], pb[1]))
                painter.restore()

        # Draw components
        for idx, (name, color_hex, cw, ch) in enumerate(self.COMPONENTS):
            if idx >= len(positions):
                break
            px, py = positions[idx]
            cx = px - cw / 2
            cy = py - ch / 2

            comp_col = QColor(color_hex)
            comp_col.setAlpha(int(alpha))
            border = QColor(255, 255, 255, int(alpha * 0.7))
            draw_rounded_rect(painter, cx, cy, cw, ch, 4, comp_col, border)

            # Label
            painter.save()
            lc = QColor(255, 255, 255, int(alpha))
            painter.setPen(QPen(lc))
            painter.setFont(QFont("Courier New", 7, QFont.Bold))
            painter.drawText(QRectF(cx, cy, cw, ch),
                             Qt.AlignCenter, name)
            painter.restore()

            # Glow on optimised
            if is_optimised and morph > 0.85:
                painter.save()
                gc = QColor(2, 136, 209, int(50 * morph))
                painter.setBrush(QBrush(gc))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(int(cx - 4), int(cy - 4),
                                        int(cw + 8), int(ch + 8), 6, 6)
                painter.restore()

    def _draw_header(self, painter, w, h, alpha):
        bar_color = QColor(C_NAVY)
        bar_color.setAlpha(int(240 * alpha))
        painter.save()
        painter.setBrush(QBrush(bar_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(int(w * 0.03), int(h * 0.03),
                                int(w * 0.94), 52, 8, 8)
        c = QColor(255, 255, 255, int(240 * alpha))
        painter.setPen(QPen(c))
        painter.setFont(QFont("Georgia", 14, QFont.Bold))
        painter.drawText(QRectF(w * 0.03, h * 0.03, w * 0.94, 52),
                         Qt.AlignCenter,
                         "Step 4: ECE Analogy  —  PCB Component Layout Optimisation")
        painter.restore()

        painter.save()
        c2 = QColor(C_TEXT_LIGHT)
        c2.setAlpha(int(180 * alpha))
        painter.setPen(QPen(c2))
        painter.setFont(QFont("Georgia", 10))
        painter.drawText(QRectF(0, h * 0.03 + 58, w, 24),
                         Qt.AlignCenter,
                         "Same graph-theory principle: minimise trace length (gates) "
                         "& signal interference (frequency collisions)")
        painter.restore()

    def _side_label(self, painter, cx, y, text, alpha):
        painter.save()
        c = QColor(C_NAVY)
        c.setAlpha(int(200 * alpha))
        painter.setPen(QPen(c))
        painter.setFont(QFont("Georgia", 11, QFont.Bold))
        painter.drawText(QRectF(cx - 130, y, 260, 26), Qt.AlignCenter, text)
        painter.restore()

    def _draw_pcb_metrics(self, painter, w, h, alpha, morph):
        rows = [
            ("Trace Length (equiv. gate count)",
             "High — unoptimised", f"Reduced by ~{int(18 * morph)}%"),
            ("Signal Interference (equiv. yield)",
             "Unpredictable",      f"Controlled  ✓"),
        ]
        sx = w * 0.06
        sy = h * 0.82
        sw = w * 0.88
        sh = h * 0.08

        bg = QColor(C_PANEL)
        bg.setAlpha(int(220 * alpha))
        draw_rounded_rect(painter, sx, sy, sw, sh, 8, bg, C_BLUE_PALE)

        painter.save()
        col_w = sw / 3
        headers = ["Metric", "Before Optimisation", "After Optimisation"]
        for ci, hdr in enumerate(headers):
            hc = QColor(C_NAVY)
            hc.setAlpha(int(200 * alpha))
            painter.setPen(QPen(hc))
            painter.setFont(QFont("Georgia", 9, QFont.Bold))
            painter.drawText(
                QRectF(sx + ci * col_w, sy + 4, col_w, sh * 0.4),
                Qt.AlignCenter, hdr
            )

        for ri, (metric, before, after) in enumerate(rows):
            painter.setFont(QFont("Georgia", 8))
            for ci, val in enumerate([metric, before, after]):
                vc = QColor(C_BLUE if ci == 2 else C_TEXT_LIGHT)
                vc.setAlpha(int(200 * alpha))
                painter.setPen(QPen(vc))
                painter.drawText(
                    QRectF(sx + ci * col_w,
                           sy + sh * 0.45 + ri * sh * 0.28, col_w, sh * 0.28),
                    Qt.AlignCenter, val
                )
        painter.restore()

    def _draw_analogy_card(self, painter, w, h, alpha):
        px = w * 0.54
        py = h * 0.55
        pw = w * 0.42
        ph = h * 0.20

        bg = QColor(C_NAVY)
        bg.setAlpha(int(230 * alpha))
        draw_rounded_rect(painter, px, py, pw, ph, 10, bg)

        painter.save()
        tc = QColor(255, 255, 255, int(230 * alpha))
        painter.setPen(QPen(tc))
        painter.setFont(QFont("Georgia", 10, QFont.Bold))
        painter.drawText(QRectF(px + 12, py + 10, pw - 24, 22),
                         Qt.AlignLeft, "Quantum → ECE Analogy")

        lc = QColor(C_BLUE_LIGHT)
        lc.setAlpha(int(210 * alpha))
        painter.setPen(QPen(lc))
        painter.setFont(QFont("Georgia", 9))
        lines = [
            "Qubit           ≡   Electronic Component (IC / Sensor)",
            "Coupling edge   ≡   PCB trace / wire",
            "SWAP gate count ≡   Total trace length",
            "Frequency coll. ≡   Signal interference / crosstalk",
            "Yield rate      ≡   Board reliability / signal integrity",
        ]
        for idx, line in enumerate(lines):
            painter.drawText(
                QRectF(px + 12, py + 36 + idx * 18, pw - 24, 18),
                Qt.AlignLeft, line
            )
        painter.restore()


# ─────────────────────────────────────────────────────────────────────────────
# SCENE 5 — OUTRO
# ─────────────────────────────────────────────────────────────────────────────
class SceneOutro(Scene):
    def __init__(self):
        super().__init__(4000)

    def paint(self, painter, w, h):
        t = self.t
        fade = min(1.0, t * 3) * min(1.0, (1 - t) * 10 + 0.2)

        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, QColor("#0D2B5E"))
        grad.setColorAt(1, QColor("#1565C0"))
        painter.fillRect(0, 0, w, h, QBrush(grad))

        alpha = int(255 * fade)

        painter.save()
        tc = QColor(255, 255, 255, alpha)
        painter.setPen(QPen(tc))
        painter.setFont(QFont("Georgia", 22, QFont.Bold))
        painter.drawText(QRectF(0, h * 0.28, w, 50),
                         Qt.AlignCenter, "Results Summary")
        painter.restore()

        items = [
            ("↑  15.61%", "Average performance improvement over IBM"),
            ("↓  21.33%", "Minimum reduction in frequency collisions"),
            ("↑   6.58%", "Performance gain over eff-5-freq"),
            ("↓   6.45%", "Yield improvement over eff-5-freq"),
        ]
        for idx, (num, desc) in enumerate(items):
            item_alpha = int(alpha * min(1.0, max(0, t * 5 - idx * 0.3)))
            painter.save()
            nc = QColor(100, 181, 246, item_alpha)
            painter.setPen(QPen(nc))
            painter.setFont(QFont("Courier New", 14, QFont.Bold))
            painter.drawText(
                QRectF(w * 0.22, h * 0.44 + idx * 40, w * 0.20, 34),
                Qt.AlignRight, num
            )
            dc = QColor(200, 225, 255, item_alpha)
            painter.setPen(QPen(dc))
            painter.setFont(QFont("Georgia", 11))
            painter.drawText(
                QRectF(w * 0.45, h * 0.44 + idx * 40, w * 0.40, 34),
                Qt.AlignLeft, desc
            )
            painter.restore()

        painter.save()
        fc = QColor(C_BLUE_LIGHT)
        fc.setAlpha(int(180 * fade))
        painter.setPen(QPen(fc))
        painter.setFont(QFont("Georgia", 10))
        painter.drawText(QRectF(0, h * 0.84, w, 28),
                         Qt.AlignCenter,
                         "Yang et al. (2023)  •  Graph-theory based quantum processor design")
        painter.restore()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CANVAS WIDGET
# ─────────────────────────────────────────────────────────────────────────────
class VisualizationCanvas(QWidget):
    scene_changed = pyqtSignal(int, int)  # current, total

    SCENE_DEFS = [
        ("Intro",        SceneIntro),
        ("IBM Arch",     SceneIBM),
        ("GA Optimize",  SceneGA),
        ("Comparison",   SceneCompare),
        ("ECE Analogy",  SceneECE),
        ("Outro",        SceneOutro),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(900, 580)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._scenes = [cls() for _, cls in self.SCENE_DEFS]
        self._current = 0
        self._elapsed = 0
        self._paused = False

        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60 fps
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        if self._paused:
            return
        self._elapsed += 16
        scene = self._scenes[self._current]
        scene.elapsed = self._elapsed

        if self._elapsed >= scene.duration:
            if self._current < len(self._scenes) - 1:
                self._current += 1
                self._elapsed = 0
                self._scenes[self._current].elapsed = 0
                self.scene_changed.emit(self._current,
                                        len(self._scenes))
            else:
                # Loop back
                self._current = 0
                self._elapsed = 0
                for s in self._scenes:
                    s.elapsed = 0
                self.scene_changed.emit(0, len(self._scenes))

        self.update()

    def next_scene(self):
        if self._current < len(self._scenes) - 1:
            self._current += 1
            self._elapsed = 0
            self._scenes[self._current].elapsed = 0
            self.scene_changed.emit(self._current, len(self._scenes))

    def prev_scene(self):
        if self._current > 0:
            self._current -= 1
            self._elapsed = 0
            self._scenes[self._current].elapsed = 0
            self.scene_changed.emit(self._current, len(self._scenes))

    def toggle_pause(self):
        self._paused = not self._paused
        return self._paused

    def restart(self):
        self._current = 0
        self._elapsed = 0
        for s in self._scenes:
            s.elapsed = 0
        self._paused = False
        self.scene_changed.emit(0, len(self._scenes))

    def current_scene_name(self):
        return self.SCENE_DEFS[self._current][0]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        w = self.width()
        h = self.height()
        scene = self._scenes[self._current]
        scene.paint(painter, w, h)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "Quantum Processor Architecture Optimization — Visualization"
        )
        self.setMinimumSize(1000, 680)
        self.resize(1200, 760)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Canvas
        self.canvas = VisualizationCanvas()
        layout.addWidget(self.canvas, 1)

        # Control bar
        ctrl = self._build_control_bar()
        layout.addWidget(ctrl)

        # Connect signals
        self.canvas.scene_changed.connect(self._on_scene_changed)
        self._update_scene_label(0, len(self.canvas.SCENE_DEFS))

        # Window style
        self.setStyleSheet("""
            QMainWindow { background: #F0F6FF; }
        """)

    def _build_control_bar(self):
        bar = QWidget()
        bar.setFixedHeight(54)
        bar.setStyleSheet("""
            QWidget {
                background: #0D2B5E;
                border-top: 1px solid #1565C0;
            }
            QPushButton {
                background: #1565C0;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 18px;
                font-family: Georgia;
                font-size: 11px;
                min-width: 70px;
            }
            QPushButton:hover { background: #1E88E5; }
            QPushButton:pressed { background: #0D47A1; }
            QLabel {
                color: #BBDEFB;
                font-family: Georgia;
                font-size: 11px;
                background: transparent;
            }
        """)

        h = QHBoxLayout(bar)
        h.setContentsMargins(16, 6, 16, 6)
        h.setSpacing(10)

        self.btn_prev = QPushButton("◀  Prev")
        self.btn_pause = QPushButton("⏸  Pause")
        self.btn_next = QPushButton("Next  ▶")
        self.btn_restart = QPushButton("↺  Restart")

        self.scene_label = QLabel("Scene 1 / 6  —  Intro")
        self.scene_label.setAlignment(Qt.AlignCenter)

        self.btn_prev.clicked.connect(self.canvas.prev_scene)
        self.btn_next.clicked.connect(self.canvas.next_scene)
        self.btn_restart.clicked.connect(self.canvas.restart)
        self.btn_pause.clicked.connect(self._toggle_pause)

        h.addWidget(self.btn_prev)
        h.addWidget(self.btn_pause)
        h.addWidget(self.btn_next)
        h.addSpacing(20)
        h.addWidget(self.scene_label, 1)
        h.addWidget(self.btn_restart)

        return bar

    def _toggle_pause(self):
        paused = self.canvas.toggle_pause()
        self.btn_pause.setText("▶  Resume" if paused else "⏸  Pause")

    def _on_scene_changed(self, current, total):
        self._update_scene_label(current, total)

    def _update_scene_label(self, current, total):
        name = self.canvas.SCENE_DEFS[current][0]
        self.scene_label.setText(
            f"Scene {current + 1} / {total}  —  {name}"
        )

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Right:
            self.canvas.next_scene()
        elif event.key() == Qt.Key_Left:
            self.canvas.prev_scene()
        elif event.key() == Qt.Key_Space:
            self._toggle_pause()
        elif event.key() == Qt.Key_R:
            self.canvas.restart()
        elif event.key() == Qt.Key_Escape:
            self.close()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Quantum Architecture Viz")

    # High-DPI support
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
