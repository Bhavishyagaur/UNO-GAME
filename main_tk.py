"""UNO - Human vs. Smart AI (tkinter edition).

Needs NOTHING to install: tkinter ships with Python.
Run with:  python main_tk.py

Controls
--------
* Click a glowing card in your hand to play it.
* No playable card? Click the draw pile.
* If the drawn card is playable you may play it or press "Pass".
* Wild card -> pick a colour in the pop-up.
* R restarts after a game, Esc quits.
"""

from __future__ import annotations

import random
import tkinter as tk
from tkinter import font as tkfont
from typing import Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
WIDTH, HEIGHT = 1000, 700
AI_DELAY_MS = 1100
CARD_W, CARD_H = 80, 120
SMALL_W, SMALL_H = 56, 84

RED, BLUE, GREEN, YELLOW, WILD = "RED", "BLUE", "GREEN", "YELLOW", "WILD"
COLORS: List[str] = [RED, BLUE, GREEN, YELLOW]
HEX: Dict[str, str] = {
    RED: "#cc262d", BLUE: "#1e64c8", GREEN: "#28a050", YELLOW: "#f0c81e", WILD: "#1e1e24",
}
TEXT_HEX: Dict[str, str] = {
    RED: "#cc262d", BLUE: "#1e64c8", GREEN: "#28a050", YELLOW: "#d2a000", WILD: "#1e1e24",
}
GOLD = "#ffe05a"
CARD_BACK = "#1c1c28"

CT_NUMBER, CT_SKIP, CT_REVERSE = "number", "skip", "reverse"
CT_DRAW_TWO, CT_WILD, CT_WILD_DRAW_FOUR = "draw_two", "wild", "wild_draw_four"

HUMAN_TURN, AI_TURN = "HUMAN_TURN", "AI_TURN"
COLOR_SELECTION_MODAL, GAME_OVER = "COLOR_SELECTION_MODAL", "GAME_OVER"

DRAW_RECT = (WIDTH // 2 - 110, 235, CARD_W, CARD_H)
DISCARD_RECT = (WIDTH // 2 + 30, 235, CARD_W, CARD_H)
PASS_RECT = (WIDTH // 2 - 60, 368, 120, 36)
BANNER_RECT = (120, 160, 760, 46)
INDICATOR_CENTER = (720, 295)
HUMAN_HAND_Y, AI_HAND_Y, HAND_MAX_WIDTH = 520, 40, 860
MODAL_RECT = (WIDTH // 2 - 230, HEIGHT // 2 - 140, 460, 280)
PLAY_AGAIN_RECT = (WIDTH // 2 - 110, HEIGHT // 2 + 43, 220, 54)

Rect = Tuple[int, int, int, int]  # x, y, w, h


def inside(rect: Rect, pos: Tuple[int, int]) -> bool:
    x, y, w, h = rect
    return x <= pos[0] <= x + w and y <= pos[1] <= y + h


# --------------------------------------------------------------------------- #
# Drawing helpers
# --------------------------------------------------------------------------- #
class Painter:
    """Small helpers around a tkinter Canvas."""

    _fonts: Dict[int, tkfont.Font] = {}

    def __init__(self, canvas: tk.Canvas) -> None:
        self.canvas = canvas

    def font(self, size: int) -> tkfont.Font:
        size = max(7, int(size))
        if size not in self._fonts:
            self._fonts[size] = tkfont.Font(family="Arial", size=-size, weight="bold")
        return self._fonts[size]

    def text(self, x: float, y: float, text: str, size: int, fill: str = "white",
             max_w: Optional[int] = None, anchor: str = "center") -> None:
        size = int(size)
        while max_w is not None and size > 8 and self.font(size).measure(text) > max_w:
            size -= 1
        self.canvas.create_text(x, y, text=text, fill=fill, font=self.font(size), anchor=anchor)

    def rrect(self, x1: float, y1: float, x2: float, y2: float, r: float = 10, **kw) -> int:
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
               x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return self.canvas.create_polygon(pts, smooth=True, **kw)

    def button(self, rect: Rect, label: str, fill: str, hovered: bool,
               text_fill: str = "white") -> None:
        x, y, w, h = rect
        self.rrect(x + 2, y + 3, x + w + 2, y + h + 3, 10, fill="#081c14")
        self.rrect(x, y, x + w, y + h, 10, fill=fill if not hovered else self._lighter(fill),
                   outline="white", width=3)
        self.text(x + w / 2, y + h / 2, label, 20, text_fill, max_w=w - 16)

    @staticmethod
    def _lighter(color: str) -> str:
        r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
        return "#%02x%02x%02x" % tuple(min(255, c + 35) for c in (r, g, b))


# --------------------------------------------------------------------------- #
# Card
# --------------------------------------------------------------------------- #
class Card:
    """A UNO card that can draw itself on a canvas."""

    CENTER_LABELS = {"Skip": "SKIP", "Reverse": "REV", "+2": "+2", "Wild": "WILD", "+4": "+4"}
    CORNER_LABELS = {"Skip": "SK", "Reverse": "RV", "+2": "+2", "Wild": "W", "+4": "+4"}

    def __init__(self, color: str, value: str, card_type: str) -> None:
        self.color = color
        self.value = value
        self.card_type = card_type

    @property
    def is_wild(self) -> bool:
        return self.card_type in (CT_WILD, CT_WILD_DRAW_FOUR)

    def describe(self) -> str:
        if self.card_type == CT_WILD:
            return "Wild"
        if self.card_type == CT_WILD_DRAW_FOUR:
            return "Wild +4"
        return f"{self.color.title()} {self.value}"

    def draw(self, p: Painter, x: int, y: int, w: int, h: int,
             face_up: bool = True, highlight: bool = False) -> None:
        p.rrect(x + 3, y + 4, x + w + 3, y + h + 4, 10, fill="#081c14")
        p.rrect(x, y, x + w, y + h, 10, fill="white")
        ix1, iy1, ix2, iy2 = x + 6, y + 6, x + w - 6, y + h - 6
        cx, cy = x + w / 2, y + h / 2
        ow, oh = (ix2 - ix1) * 0.82, (iy2 - iy1) * 0.56

        if not face_up:
            p.rrect(ix1, iy1, ix2, iy2, 8, fill=CARD_BACK)
            p.canvas.create_oval(cx - ow / 2, cy - oh / 2, cx + ow / 2, cy + oh / 2,
                                 fill="#c81e28", outline=GOLD, width=2)
            p.text(cx, cy, "UNO", int(h * 0.2), GOLD, max_w=int(ow) - 8)
        else:
            if self.is_wild:
                mx, my = (ix1 + ix2) / 2, (iy1 + iy2) / 2
                for col, box in ((RED, (ix1 + 1, iy1 + 1, mx, my)), (BLUE, (mx, iy1 + 1, ix2 - 1, my)),
                                 (YELLOW, (ix1 + 1, my, mx, iy2 - 1)), (GREEN, (mx, my, ix2 - 1, iy2 - 1))):
                    p.canvas.create_rectangle(*box, fill=HEX[col], outline=HEX[col])
            else:
                p.rrect(ix1, iy1, ix2, iy2, 8, fill=HEX[self.color])
            p.canvas.create_oval(cx - ow / 2, cy - oh / 2, cx + ow / 2, cy + oh / 2,
                                 fill="white", outline="white")
            label = self.CENTER_LABELS.get(self.value, self.value)
            start = int(h * (0.40 if len(label) <= 2 else 0.2))
            p.text(cx, cy, label, start, TEXT_HEX[self.color], max_w=int(ow) - 8)
            corner = self.CORNER_LABELS.get(self.value, self.value)
            fill = "black" if self.color == YELLOW else "white"
            p.text(ix1 + 4, iy1 + 3, corner, int(h * 0.13), fill, anchor="nw")
            p.text(ix2 - 4, iy2 - 3, corner, int(h * 0.13), fill, anchor="se")

        if highlight:
            p.rrect(x - 3, y - 3, x + w + 3, y + h + 3, 12, fill="", outline=GOLD, width=4)


# --------------------------------------------------------------------------- #
# Deck
# --------------------------------------------------------------------------- #
class Deck:
    """Standard 108-card UNO deck with draw and discard piles."""

    def __init__(self) -> None:
        self.draw_pile: List[Card] = self._build()
        self.discard_pile: List[Card] = []
        random.shuffle(self.draw_pile)

    @staticmethod
    def _build() -> List[Card]:
        cards: List[Card] = []
        for color in COLORS:
            cards.append(Card(color, "0", CT_NUMBER))
            for number in range(1, 10):
                for _ in range(2):
                    cards.append(Card(color, str(number), CT_NUMBER))
            for ctype, value in ((CT_SKIP, "Skip"), (CT_REVERSE, "Reverse"), (CT_DRAW_TWO, "+2")):
                for _ in range(2):
                    cards.append(Card(color, value, ctype))
        for _ in range(4):
            cards.append(Card(WILD, "Wild", CT_WILD))
            cards.append(Card(WILD, "+4", CT_WILD_DRAW_FOUR))
        return cards

    def draw(self) -> Optional[Card]:
        if not self.draw_pile:
            self._reshuffle()
        return self.draw_pile.pop() if self.draw_pile else None

    def _reshuffle(self) -> None:
        if len(self.discard_pile) <= 1:
            return
        top = self.discard_pile.pop()
        self.draw_pile = self.discard_pile
        self.discard_pile = [top]
        random.shuffle(self.draw_pile)

    def deal(self, players: List["Player"], count: int = 7) -> None:
        for _ in range(count):
            for player in players:
                card = self.draw()
                if card is not None:
                    player.hand.append(card)
        for player in players:
            player.sort_hand()

    def start_card(self) -> Card:
        while True:
            card = self.draw_pile.pop()
            if card.card_type == CT_NUMBER:
                self.discard_pile.append(card)
                return card
            self.draw_pile.insert(0, card)


# --------------------------------------------------------------------------- #
# Players
# --------------------------------------------------------------------------- #
class Player:
    """Holds a hand and knows the play-validation rules."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.hand: List[Card] = []

    @staticmethod
    def is_valid_play(card: Card, top: Card, active_color: str) -> bool:
        if card.is_wild or card.color == active_color:
            return True
        return (not top.is_wild) and card.value == top.value

    def playable_cards(self, top: Card, active_color: str) -> List[Card]:
        return [c for c in self.hand if self.is_valid_play(c, top, active_color)]

    def has_playable(self, top: Card, active_color: str) -> bool:
        return bool(self.playable_cards(top, active_color))

    def sort_hand(self) -> None:
        self.hand.sort(key=lambda c: (COLORS.index(c.color) if c.color in COLORS else 4, c.value))

    def add_card(self, card: Card) -> None:
        self.hand.append(card)
        self.sort_hand()

    def draw_cards(self, deck: Deck, count: int) -> int:
        drawn = 0
        for _ in range(count):
            card = deck.draw()
            if card is None:
                break
            self.hand.append(card)
            drawn += 1
        self.sort_hand()
        return drawn


class AIPlayer(Player):
    """Computer opponent: matches first, uses actions wisely, saves Wilds."""

    ACTION_PRIORITY = {CT_DRAW_TWO: 3, CT_SKIP: 2, CT_REVERSE: 1}

    def best_color(self) -> str:
        counts = {color: 0 for color in COLORS}
        for card in self.hand:
            if card.color in counts:
                counts[card.color] += 1
        highest = max(counts.values())
        if highest == 0:
            return random.choice(COLORS)
        return random.choice([c for c in COLORS if counts[c] == highest])

    def choose_color(self) -> str:
        return self.best_color()

    def choose_card(self, top: Card, active_color: str, opponent_count: int) -> Optional[Card]:
        playable = self.playable_cards(top, active_color)
        if not playable:
            return None
        numbers = [c for c in playable if c.card_type == CT_NUMBER]
        actions = [c for c in playable if c.card_type in self.ACTION_PRIORITY]
        wilds = [c for c in playable if c.is_wild]
        dominant = self.best_color()

        if actions and (opponent_count <= 3 or not numbers):
            return max(actions, key=lambda c: (self.ACTION_PRIORITY[c.card_type], c.color == dominant))
        if opponent_count <= 2:
            for card in wilds:
                if card.card_type == CT_WILD_DRAW_FOUR:
                    return card
        if numbers:
            return max(numbers, key=lambda c: (c.color == dominant, int(c.value)))
        plain = [c for c in wilds if c.card_type == CT_WILD]
        return plain[0] if plain else wilds[0]


# --------------------------------------------------------------------------- #
# Game
# --------------------------------------------------------------------------- #
class UnoGame:
    """Game state machine, input handling and rendering."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("UNO - Human vs. AI")
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, highlightthickness=0, bg="#091a13")
        self.canvas.pack()
        self.p = Painter(self.canvas)
        self.mouse: Tuple[int, int] = (0, 0)
        self.ai_job: Optional[str] = None

        self.deck = Deck()
        self.human = Player("You")
        self.ai = AIPlayer("AI")
        self.state = HUMAN_TURN
        self.active_color = RED
        self.status = ""
        self.drawn_card: Optional[Card] = None
        self.pending_wild: Optional[Card] = None
        self.winner: Optional[Player] = None

        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Motion>", self._on_motion)
        root.bind("<Escape>", lambda _e: root.destroy())
        root.bind("<r>", self._on_restart_key)
        root.bind("<R>", self._on_restart_key)
        self.new_game()

    # ----------------------------------------------------------- setup ---- #
    def new_game(self) -> None:
        if self.ai_job is not None:
            self.root.after_cancel(self.ai_job)
            self.ai_job = None
        self.deck = Deck()
        self.human = Player("You")
        self.ai = AIPlayer("AI")
        self.deck.deal([self.human, self.ai], 7)
        start = self.deck.start_card()
        self.active_color = start.color
        self.drawn_card = None
        self.pending_wild = None
        self.winner = None
        self.state = HUMAN_TURN
        self.status = "Your turn! Play a matching card or draw."
        self.redraw()

    @property
    def top_card(self) -> Card:
        return self.deck.discard_pile[-1]

    def _set_turn(self, human_turn: bool) -> None:
        if human_turn:
            self.state = HUMAN_TURN
        else:
            self.state = AI_TURN
            self.ai_job = self.root.after(AI_DELAY_MS, self._ai_turn)
        self.redraw()

    def _is_playable(self, card: Card) -> bool:
        return Player.is_valid_play(card, self.top_card, self.active_color)

    # ------------------------------------------------------- game logic ---- #
    def _play_card(self, card: Card, by_human: bool) -> None:
        player = self.human if by_human else self.ai
        player.hand.remove(card)
        self.deck.discard_pile.append(card)
        self.drawn_card = None

        if not player.hand:
            self.winner = player
            self.state = GAME_OVER
            self.status = "You played your last card!" if by_human else "The AI played its last card!"
            self.redraw()
            return
        if card.is_wild:
            if by_human:
                self.pending_wild = card
                self.state = COLOR_SELECTION_MODAL
                self.status = "Choose a colour for your Wild card."
                self.redraw()
                return
            color = self.ai.choose_color()
        else:
            color = card.color
        self._resolve_card(card, by_human, color)

    def _resolve_card(self, card: Card, by_human: bool, color: str) -> None:
        self.active_color = color
        name = "You" if by_human else "AI"
        opponent = self.ai if by_human else self.human
        opp_name = "AI" if by_human else "You"
        s = "s" if opp_name == "AI" else ""
        keep_turn = False
        desc = card.describe()

        if card.card_type in (CT_SKIP, CT_REVERSE):
            keep_turn = True
            miss = "misses" if by_human else "miss"
            extra = " (Reverse acts as Skip)" if card.card_type == CT_REVERSE else ""
            msg = f"{name} played {desc}!{extra} {opp_name} {miss} a turn."
        elif card.card_type == CT_DRAW_TWO:
            keep_turn = True
            opponent.draw_cards(self.deck, 2)
            msg = f"{name} played {desc}! {opp_name} draw{s} 2 cards."
        elif card.card_type == CT_WILD_DRAW_FOUR:
            keep_turn = True
            opponent.draw_cards(self.deck, 4)
            msg = f"{name} played Wild +4 - colour is {color}! {opp_name} draw{s} 4 cards."
        elif card.card_type == CT_WILD:
            msg = f"{name} played Wild - colour is {color}."
        else:
            msg = f"{name} played {desc}."

        mover = self.human if by_human else self.ai
        if len(mover.hand) == 1:
            msg += " UNO!"
        if keep_turn:
            msg += " Your turn again!" if by_human else " AI plays again."
        else:
            msg += " AI is thinking..." if by_human else " Your turn!"
        self.status = msg
        self._set_turn(human_turn=(by_human == keep_turn))

    def _human_draw(self) -> None:
        if self.drawn_card is not None:
            self.status = "Play the card you drew, or press Pass."
            self.redraw()
            return
        if self.human.has_playable(self.top_card, self.active_color):
            self.status = "You already have a playable card!"
            self.redraw()
            return
        card = self.deck.draw()
        if card is None:
            self.status = "The draw pile is empty - your turn is skipped."
            self._set_turn(human_turn=False)
            return
        self.human.add_card(card)
        if self._is_playable(card):
            self.drawn_card = card
            self.status = f"You drew {card.describe()} - play it or press Pass."
            self.redraw()
        else:
            self.status = f"You drew {card.describe()} - no play. AI's turn."
            self._set_turn(human_turn=False)

    def _ai_turn(self) -> None:
        self.ai_job = None
        if self.state != AI_TURN:
            return
        card = self.ai.choose_card(self.top_card, self.active_color, len(self.human.hand))
        if card is not None:
            self._play_card(card, by_human=False)
            return
        drawn = self.deck.draw()
        if drawn is None:
            self.status = "AI cannot draw. Your turn!"
            self._set_turn(human_turn=True)
            return
        self.ai.add_card(drawn)
        if self._is_playable(drawn):
            self._play_card(drawn, by_human=False)
            if self.state != GAME_OVER:
                self.status = self.status.replace("AI played", "AI drew and played", 1)
                self.redraw()
        else:
            self.status = "AI drew a card. Your turn!"
            self._set_turn(human_turn=True)

    # ----------------------------------------------------------- layout ---- #
    @staticmethod
    def _hand_rects(count: int, card_w: int, card_h: int, y: int) -> List[Rect]:
        if count == 0:
            return []
        step = card_w + 10
        if count * step - 10 > HAND_MAX_WIDTH:
            step = (HAND_MAX_WIDTH - card_w) / max(1, count - 1)
        total = (count - 1) * step + card_w
        start_x = (WIDTH - total) / 2
        return [(int(start_x + i * step), y, card_w, card_h) for i in range(count)]

    def _human_rects(self) -> List[Rect]:
        return self._hand_rects(len(self.human.hand), CARD_W, CARD_H, HUMAN_HAND_Y)

    def _card_index_at(self, pos: Tuple[int, int]) -> Optional[int]:
        rects = self._human_rects()
        for index in range(len(rects) - 1, -1, -1):
            if inside(rects[index], pos):
                return index
        return None

    @staticmethod
    def _color_button_rects() -> Dict[str, Rect]:
        mx, my = MODAL_RECT[0], MODAL_RECT[1]
        return {color: (mx + 30 + (i % 2) * 210, my + 80 + (i // 2) * 74, 190, 60)
                for i, color in enumerate(COLORS)}

    # ------------------------------------------------------------ input ---- #
    def _on_motion(self, event: tk.Event) -> None:
        self.mouse = (event.x, event.y)
        self.redraw()

    def _on_restart_key(self, _event: tk.Event) -> None:
        if self.state == GAME_OVER:
            self.new_game()

    def _on_click(self, event: tk.Event) -> None:
        pos = (event.x, event.y)
        if self.state == COLOR_SELECTION_MODAL:
            for color, rect in self._color_button_rects().items():
                if inside(rect, pos) and self.pending_wild is not None:
                    card, self.pending_wild = self.pending_wild, None
                    self._resolve_card(card, True, color)
                    return
        elif self.state == GAME_OVER:
            if inside(PLAY_AGAIN_RECT, pos):
                self.new_game()
        elif self.state == HUMAN_TURN:
            self._handle_human_click(pos)

    def _handle_human_click(self, pos: Tuple[int, int]) -> None:
        if self.drawn_card is not None and inside(PASS_RECT, pos):
            self.status = "You passed. AI's turn."
            self.drawn_card = None
            self._set_turn(human_turn=False)
            return
        if inside(DRAW_RECT, pos):
            self._human_draw()
            return
        index = self._card_index_at(pos)
        if index is None:
            return
        card = self.human.hand[index]
        if self.drawn_card is not None and card is not self.drawn_card:
            self.status = "You must play the card you just drew, or press Pass."
            self.redraw()
        elif not self._is_playable(card):
            self.status = "That card can't be played on the current card."
            self.redraw()
        else:
            self._play_card(card, by_human=True)

    # -------------------------------------------------------- rendering ---- #
    def redraw(self) -> None:
        c, p = self.canvas, self.p
        c.delete("all")
        self._draw_table()
        self._draw_ai_hand()
        self._draw_banner()
        self._draw_center()
        self._draw_human_hand()
        if self.state == COLOR_SELECTION_MODAL:
            self._draw_color_modal()
        elif self.state == GAME_OVER:
            self._draw_game_over()

    def _draw_table(self) -> None:
        p = self.p
        p.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#091a13", outline="")
        p.rrect(20, 14, WIDTH - 20, HEIGHT - 14, 120, fill="#482c18")
        p.rrect(33, 27, WIDTH - 33, HEIGHT - 27, 108, fill="#145436", outline="#0e3e28", width=4)
        p.canvas.create_oval(190, 150, 810, 470, fill="#18603e", outline="#10462e", width=3)

    def _draw_ai_hand(self) -> None:
        count = len(self.ai.hand)
        for x, y, w, h in self._hand_rects(count, SMALL_W, SMALL_H, AI_HAND_Y):
            self.top_card.draw(self.p, x, y, w, h, face_up=False)
        text = f"AI - {count} card{'s' if count != 1 else ''}" + ("  (UNO!)" if count == 1 else "")
        self.p.text(WIDTH // 2, AI_HAND_Y + SMALL_H + 22, text, 20)

    def _draw_banner(self) -> None:
        x, y, w, h = BANNER_RECT
        self.p.rrect(x, y, x + w, y + h, 12, fill="#0a1812", outline=HEX[self.active_color], width=3)
        self.p.text(x + w / 2, y + h / 2, self.status, 22, max_w=w - 30)

    def _human_needs_draw(self) -> bool:
        return (self.state == HUMAN_TURN and self.drawn_card is None
                and not self.human.has_playable(self.top_card, self.active_color))

    def _draw_center(self) -> None:
        p = self.p
        dx, dy, dw, dh = DRAW_RECT
        pile = len(self.deck.draw_pile)
        if pile > 0:
            for off in (-4, -2):
                self.top_card.draw(p, dx + off, dy + off, dw, dh, face_up=False)
            self.top_card.draw(p, dx, dy, dw, dh, face_up=False, highlight=self._human_needs_draw())
        else:
            p.rrect(dx, dy, dx + dw, dy + dh, 10, fill="", outline="#0e3e28", width=3)
        p.text(dx + dw / 2, dy + dh + 18, f"Draw ({pile})", 16)

        sx, sy, sw, sh = DISCARD_RECT
        self.top_card.draw(p, sx, sy, sw, sh, face_up=True)
        p.text(sx + sw / 2, sy + sh + 18, "Discard", 16)

        ix, iy = INDICATOR_CENTER
        p.text(ix, iy - 56, "Active colour", 16)
        p.canvas.create_oval(ix - 34 + 2, iy - 34 + 3, ix + 34 + 2, iy + 34 + 3, fill="#081c14", outline="")
        p.canvas.create_oval(ix - 34, iy - 34, ix + 34, iy + 34, fill=HEX[self.active_color],
                             outline="white", width=4)
        p.text(ix, iy + 56, self.active_color.title(), 16)

        if self.state == HUMAN_TURN and self.drawn_card is not None:
            p.button(PASS_RECT, "Pass", "#783c3c", inside(PASS_RECT, self.mouse))

    def _draw_human_hand(self) -> None:
        rects = self._human_rects()
        hovered = self._card_index_at(self.mouse) if self.state == HUMAN_TURN else None
        order = [i for i in range(len(rects)) if i != hovered]
        if hovered is not None:
            order.append(hovered)
        for i in order:
            card = self.human.hand[i]
            x, y, w, h = rects[i]
            playable = (card is self.drawn_card) if self.drawn_card is not None else self._is_playable(card)
            if i == hovered:
                y -= 16
            card.draw(self.p, x, y, w, h, face_up=True,
                      highlight=(self.state == HUMAN_TURN and playable))
        count = len(self.human.hand)
        text = f"Your hand - {count} card{'s' if count != 1 else ''}" + ("  (UNO!)" if count == 1 else "")
        self.p.text(WIDTH // 2, HUMAN_HAND_Y - 40, text, 20)
        self.p.text(WIDTH // 2, HEIGHT - 42,
                    "Click a glowing card to play  |  No move? Click the draw pile  |  Esc to quit",
                    14, "#aad2b9")

    def _dim(self) -> None:
        # tkinter has no alpha fill; a stipple pattern gives a dimmed look.
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="black", stipple="gray50", outline="")

    def _draw_color_modal(self) -> None:
        p = self.p
        self._dim()
        x, y, w, h = MODAL_RECT
        p.rrect(x, y, x + w, y + h, 18, fill="#10281e", outline="white", width=4)
        p.text(x + w / 2, y + 42, "Choose a colour", 28)
        for color, rect in self._color_button_rects().items():
            p.button(rect, color.title(), HEX[color], inside(rect, self.mouse),
                     "black" if color == YELLOW else "white")

    def _draw_game_over(self) -> None:
        p = self.p
        self._dim()
        human_won = self.winner is self.human
        p.text(WIDTH // 2, HEIGHT // 2 - 70, "YOU WIN!" if human_won else "AI WINS!", 84,
               GOLD if human_won else "#e65a5a")
        sub = ("You emptied your hand. Congratulations!" if human_won
               else "The AI emptied its hand. Better luck next time!")
        p.text(WIDTH // 2, HEIGHT // 2 - 10, sub, 22)
        p.button(PLAY_AGAIN_RECT, "Play Again", "#28825a", inside(PLAY_AGAIN_RECT, self.mouse))
        p.text(WIDTH // 2, PLAY_AGAIN_RECT[1] + PLAY_AGAIN_RECT[3] + 22, "or press R", 15, "#c8dccd")


def main() -> None:
    root = tk.Tk()
    UnoGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()
