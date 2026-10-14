"""UNO - Human vs. Smart AI, built with Pygame.

Single-file, asset-free implementation. All cards are drawn with Pygame
primitives. Requires only ``pygame`` plus the standard ``random``/``sys``.

Run with:  python main.py

Controls
--------
* Click a highlighted card in your hand to play it.
* If you have no playable card, click the draw pile.
* If the drawn card is playable you may play it or press "Pass".
* When you play a Wild card, pick a colour in the pop-up.
* R restarts after a game ends, Esc quits.
"""

from __future__ import annotations

import random
import sys
from typing import Dict, List, Optional, Tuple

import pygame

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
WIDTH, HEIGHT = 1000, 700
FPS = 60
AI_DELAY_MS = 1100

CARD_W, CARD_H = 80, 120
SMALL_W, SMALL_H = 56, 84

# Card colours
RED, BLUE, GREEN, YELLOW, WILD = "RED", "BLUE", "GREEN", "YELLOW", "WILD"
COLORS: List[str] = [RED, BLUE, GREEN, YELLOW]

RGB: Dict[str, Tuple[int, int, int]] = {
    RED: (204, 38, 45),
    BLUE: (30, 100, 200),
    GREEN: (40, 160, 80),
    YELLOW: (240, 200, 30),
    WILD: (30, 30, 36),
}
TEXT_RGB: Dict[str, Tuple[int, int, int]] = {
    RED: (204, 38, 45),
    BLUE: (30, 100, 200),
    GREEN: (40, 160, 80),
    YELLOW: (210, 160, 0),
    WILD: (30, 30, 36),
}

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SHADOW = (8, 28, 20)
CARD_BACK = (28, 28, 40)
GOLD = (255, 224, 90)

# Card types
CT_NUMBER = "number"
CT_SKIP = "skip"
CT_REVERSE = "reverse"
CT_DRAW_TWO = "draw_two"
CT_WILD = "wild"
CT_WILD_DRAW_FOUR = "wild_draw_four"

# Game states
HUMAN_TURN = "HUMAN_TURN"
AI_TURN = "AI_TURN"
COLOR_SELECTION_MODAL = "COLOR_SELECTION_MODAL"
GAME_OVER = "GAME_OVER"

# Static layout rectangles
DRAW_RECT = pygame.Rect(WIDTH // 2 - 110, 235, CARD_W, CARD_H)
DISCARD_RECT = pygame.Rect(WIDTH // 2 + 30, 235, CARD_W, CARD_H)
PASS_RECT = pygame.Rect(WIDTH // 2 - 60, 368, 120, 36)
BANNER_RECT = pygame.Rect(120, 160, 760, 46)
INDICATOR_CENTER = (720, 295)
HUMAN_HAND_Y = 520
AI_HAND_Y = 40
HAND_MAX_WIDTH = 860

MODAL_RECT = pygame.Rect(0, 0, 460, 280)
MODAL_RECT.center = (WIDTH // 2, HEIGHT // 2)
PLAY_AGAIN_RECT = pygame.Rect(0, 0, 220, 54)
PLAY_AGAIN_RECT.center = (WIDTH // 2, HEIGHT // 2 + 70)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
class Fonts:
    """Lazy font cache (fonts can only be created after pygame.init())."""

    _cache: Dict[int, pygame.font.Font] = {}

    @classmethod
    def get(cls, size: int) -> pygame.font.Font:
        size = max(8, int(size))
        if size not in cls._cache:
            cls._cache[size] = pygame.font.SysFont(
                "arial,helvetica,dejavusans,liberationsans", size, bold=True
            )
        return cls._cache[size]

    @classmethod
    def fit(
        cls,
        text: str,
        color: Tuple[int, int, int],
        max_width: int,
        start_size: int,
    ) -> pygame.Surface:
        """Render ``text`` shrinking the font until it fits ``max_width``."""
        size = int(start_size)
        surf = cls.get(size).render(text, True, color)
        while surf.get_width() > max_width and size > 8:
            size -= 1
            surf = cls.get(size).render(text, True, color)
        return surf


def draw_button(
    surface: pygame.Surface,
    rect: pygame.Rect,
    text: str,
    base: Tuple[int, int, int],
    hovered: bool,
    text_color: Tuple[int, int, int] = WHITE,
) -> None:
    """Draw a simple rounded button with hover feedback."""
    color = tuple(min(255, c + 30) for c in base) if hovered else base
    pygame.draw.rect(surface, SHADOW, rect.move(2, 3), border_radius=10)
    pygame.draw.rect(surface, color, rect, border_radius=10)
    pygame.draw.rect(surface, WHITE, rect, 3, border_radius=10)
    label = Fonts.fit(text, text_color, rect.w - 16, 24)
    surface.blit(label, label.get_rect(center=rect.center))


def draw_background() -> pygame.Surface:
    """Pre-render the dark felt poker table."""
    bg = pygame.Surface((WIDTH, HEIGHT))
    bg.fill((9, 26, 19))
    table = pygame.Rect(20, 14, WIDTH - 40, HEIGHT - 28)
    pygame.draw.rect(bg, (72, 44, 24), table, border_radius=130)
    felt = table.inflate(-26, -26)
    pygame.draw.rect(bg, (20, 84, 54), felt, border_radius=118)
    pygame.draw.rect(bg, (14, 62, 40), felt, 4, border_radius=118)
    oval = pygame.Rect(190, 150, 620, 320)
    pygame.draw.ellipse(bg, (24, 96, 62), oval)
    pygame.draw.ellipse(bg, (16, 70, 46), oval, 3)
    return bg


# --------------------------------------------------------------------------- #
# Card
# --------------------------------------------------------------------------- #
class Card:
    """A single UNO card that knows how to draw itself."""

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
        """Human-readable name used in status messages."""
        if self.card_type == CT_WILD:
            return "Wild"
        if self.card_type == CT_WILD_DRAW_FOUR:
            return "Wild +4"
        return f"{self.color.title()} {self.value}"

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Card({self.color}, {self.value})"

    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        face_up: bool = True,
        highlight: bool = False,
    ) -> None:
        """Render the card inside ``rect`` using only Pygame primitives."""
        pygame.draw.rect(surface, SHADOW, rect.move(3, 4), border_radius=10)
        pygame.draw.rect(surface, WHITE, rect, border_radius=10)
        inner = rect.inflate(-10, -10)

        if not face_up:
            self._draw_back(surface, rect, inner)
        else:
            self._draw_front(surface, rect, inner)

        if highlight:
            pygame.draw.rect(surface, GOLD, rect.inflate(6, 6), 4, border_radius=12)

    def _draw_back(self, surface: pygame.Surface, rect: pygame.Rect, inner: pygame.Rect) -> None:
        pygame.draw.rect(surface, CARD_BACK, inner, border_radius=8)
        oval = pygame.Rect(0, 0, int(inner.w * 0.82), int(inner.h * 0.5))
        oval.center = inner.center
        pygame.draw.ellipse(surface, (200, 30, 40), oval)
        pygame.draw.ellipse(surface, GOLD, oval, 2)
        text = Fonts.fit("UNO", GOLD, oval.w - 6, int(rect.h * 0.2))
        surface.blit(text, text.get_rect(center=oval.center))

    def _draw_front(self, surface: pygame.Surface, rect: pygame.Rect, inner: pygame.Rect) -> None:
        if self.is_wild:
            half_w, half_h = inner.w // 2, inner.h // 2
            r = 8
            quads = (
                (RED, pygame.Rect(inner.x, inner.y, half_w, half_h), {"border_top_left_radius": r}),
                (BLUE, pygame.Rect(inner.x + half_w, inner.y, inner.w - half_w, half_h),
                 {"border_top_right_radius": r}),
                (YELLOW, pygame.Rect(inner.x, inner.y + half_h, half_w, inner.h - half_h),
                 {"border_bottom_left_radius": r}),
                (GREEN, pygame.Rect(inner.x + half_w, inner.y + half_h, inner.w - half_w,
                                    inner.h - half_h), {"border_bottom_right_radius": r}),
            )
            for color, quad, radii in quads:
                pygame.draw.rect(surface, RGB[color], quad, **radii)
        else:
            pygame.draw.rect(surface, RGB[self.color], inner, border_radius=8)

        # Centre oval with the main label
        oval = pygame.Rect(0, 0, int(inner.w * 0.80), int(inner.h * 0.56))
        oval.center = inner.center
        pygame.draw.ellipse(surface, WHITE, oval)
        center_text = self.CENTER_LABELS.get(self.value, self.value)
        start = int(rect.h * (0.40 if len(center_text) <= 2 else 0.24))
        label = Fonts.fit(center_text, TEXT_RGB[self.color], oval.w - 10, start)
        surface.blit(label, label.get_rect(center=oval.center))

        # Corner labels
        corner_color = BLACK if self.color == YELLOW else WHITE
        corner_text = self.CORNER_LABELS.get(self.value, self.value)
        corner = Fonts.get(int(rect.h * 0.13)).render(corner_text, True, corner_color)
        surface.blit(corner, (inner.x + 4, inner.y + 2))
        corner_rot = pygame.transform.rotate(corner, 180)
        surface.blit(corner_rot, (inner.right - corner_rot.get_width() - 4,
                                  inner.bottom - corner_rot.get_height() - 2))


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
            for card_type, value in ((CT_SKIP, "Skip"), (CT_REVERSE, "Reverse"), (CT_DRAW_TWO, "+2")):
                for _ in range(2):
                    cards.append(Card(color, value, card_type))
        for _ in range(4):
            cards.append(Card(WILD, "Wild", CT_WILD))
            cards.append(Card(WILD, "+4", CT_WILD_DRAW_FOUR))
        return cards

    def draw(self) -> Optional[Card]:
        """Draw one card, reshuffling the discard pile if needed."""
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
        """Flip the first discard; it is always a plain number card."""
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
    """Base class: holds a hand and knows the play-validation rules."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.hand: List[Card] = []

    @staticmethod
    def is_valid_play(card: Card, top: Card, active_color: str) -> bool:
        if card.is_wild:
            return True
        if card.color == active_color:
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
        """Draw up to ``count`` cards; returns how many were actually drawn."""
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
    """Computer opponent with a simple but sensible strategy."""

    ACTION_PRIORITY = {CT_DRAW_TWO: 3, CT_SKIP: 2, CT_REVERSE: 1}

    def best_color(self) -> str:
        """Colour the AI holds the most of (random tie-break / empty hand)."""
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
        """Pick a card to play, or ``None`` if the AI must draw."""
        playable = self.playable_cards(top, active_color)
        if not playable:
            return None

        numbers = [c for c in playable if c.card_type == CT_NUMBER]
        actions = [c for c in playable if c.card_type in self.ACTION_PRIORITY]
        wilds = [c for c in playable if c.is_wild]
        dominant = self.best_color()
        opponent_close = opponent_count <= 3

        # 1. Action cards: when the opponent is close to winning (or when
        #    nothing else matches) use them to keep control of the game.
        if actions and (opponent_close or not numbers):
            return max(actions, key=lambda c: (self.ACTION_PRIORITY[c.card_type], c.color == dominant))

        # 2. Emergency: opponent nearly out of cards -> Wild +4.
        if opponent_count <= 2:
            for card in wilds:
                if card.card_type == CT_WILD_DRAW_FOUR:
                    return card

        # 3. Matching colour / number cards first; prefer switching to (or
        #    staying in) the colour we hold most, then dump high values.
        if numbers:
            return max(numbers, key=lambda c: (c.color == dominant, int(c.value)))

        # 4. Only wilds left: keep them as a last resort, plain Wild first.
        plain = [c for c in wilds if c.card_type == CT_WILD]
        return plain[0] if plain else wilds[0]


# --------------------------------------------------------------------------- #
# Game
# --------------------------------------------------------------------------- #
class UnoGame:
    """Owns the game state, rules, input handling and rendering."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.background = draw_background()
        self.mouse_pos: Tuple[int, int] = (0, 0)

        self.deck = Deck()
        self.human = Player("You")
        self.ai = AIPlayer("AI")
        self.state = HUMAN_TURN
        self.active_color = RED
        self.status = ""
        self.drawn_card: Optional[Card] = None
        self.pending_wild: Optional[Card] = None
        self.winner: Optional[Player] = None
        self.ai_timer = 0
        self.new_game()

    # ----------------------------------------------------------- setup ---- #
    def new_game(self) -> None:
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

    @property
    def top_card(self) -> Card:
        return self.deck.discard_pile[-1]

    def _set_turn(self, human_turn: bool) -> None:
        if human_turn:
            self.state = HUMAN_TURN
        else:
            self.state = AI_TURN
            self.ai_timer = pygame.time.get_ticks()

    def _is_playable(self, card: Card) -> bool:
        return Player.is_valid_play(card, self.top_card, self.active_color)

    # ------------------------------------------------------- game logic ---- #
    def _play_card(self, card: Card, by_human: bool) -> None:
        """Move a card from a hand to the discard pile and apply its effect."""
        player = self.human if by_human else self.ai
        player.hand.remove(card)
        self.deck.discard_pile.append(card)
        self.drawn_card = None

        if not player.hand:
            self.winner = player
            self.state = GAME_OVER
            self.status = "You played your last card!" if by_human else "The AI played its last card!"
            return

        if card.is_wild:
            if by_human:
                self.pending_wild = card
                self.state = COLOR_SELECTION_MODAL
                self.status = "Choose a colour for your Wild card."
                return
            color = self.ai.choose_color()
        else:
            color = card.color
        self._resolve_card(card, by_human, color)

    def _resolve_card(self, card: Card, by_human: bool, color: str) -> None:
        """Apply colour changes, draw penalties and decide whose turn is next."""
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
            return
        if self.human.has_playable(self.top_card, self.active_color):
            self.status = "You already have a playable card!"
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
        else:
            self.status = f"You drew {card.describe()} - no play. AI's turn."
            self._set_turn(human_turn=False)

    def _ai_turn(self) -> None:
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
        else:
            self.status = "AI drew a card. Your turn!"
            self._set_turn(human_turn=True)

    # ----------------------------------------------------------- layout ---- #
    @staticmethod
    def _hand_rects(count: int, card_w: int, card_h: int, y: int) -> List[pygame.Rect]:
        if count == 0:
            return []
        gap = 10
        step = card_w + gap
        if count * step - gap > HAND_MAX_WIDTH:
            step = (HAND_MAX_WIDTH - card_w) / max(1, count - 1)
        total = (count - 1) * step + card_w
        start_x = (WIDTH - total) / 2
        return [pygame.Rect(int(start_x + i * step), y, card_w, card_h) for i in range(count)]

    def _human_rects(self) -> List[pygame.Rect]:
        return self._hand_rects(len(self.human.hand), CARD_W, CARD_H, HUMAN_HAND_Y)

    def _card_index_at(self, pos: Tuple[int, int]) -> Optional[int]:
        rects = self._human_rects()
        for index in range(len(rects) - 1, -1, -1):
            if rects[index].collidepoint(pos):
                return index
        return None

    @staticmethod
    def _color_button_rects() -> Dict[str, pygame.Rect]:
        rects: Dict[str, pygame.Rect] = {}
        for i, color in enumerate(COLORS):
            col, row = i % 2, i // 2
            x = MODAL_RECT.x + 30 + col * (190 + 20)
            y = MODAL_RECT.y + 80 + row * (60 + 14)
            rects[color] = pygame.Rect(x, y, 190, 60)
        return rects

    # ------------------------------------------------------------ input ---- #
    def handle_click(self, pos: Tuple[int, int]) -> None:
        if self.state == COLOR_SELECTION_MODAL:
            for color, rect in self._color_button_rects().items():
                if rect.collidepoint(pos) and self.pending_wild is not None:
                    card, self.pending_wild = self.pending_wild, None
                    self._resolve_card(card, True, color)
                    return
        elif self.state == GAME_OVER:
            if PLAY_AGAIN_RECT.collidepoint(pos):
                self.new_game()
        elif self.state == HUMAN_TURN:
            self._handle_human_click(pos)

    def _handle_human_click(self, pos: Tuple[int, int]) -> None:
        if self.drawn_card is not None and PASS_RECT.collidepoint(pos):
            self.status = "You passed. AI's turn."
            self.drawn_card = None
            self._set_turn(human_turn=False)
            return
        if DRAW_RECT.collidepoint(pos):
            self._human_draw()
            return
        index = self._card_index_at(pos)
        if index is None:
            return
        card = self.human.hand[index]
        if self.drawn_card is not None and card is not self.drawn_card:
            self.status = "You must play the card you just drew, or press Pass."
        elif not self._is_playable(card):
            self.status = "That card can't be played on the current card."
        else:
            self._play_card(card, by_human=True)

    def update(self) -> None:
        if self.state == AI_TURN and pygame.time.get_ticks() - self.ai_timer >= AI_DELAY_MS:
            self._ai_turn()

    # -------------------------------------------------------- rendering ---- #
    def draw(self) -> None:
        surface = self.screen
        surface.blit(self.background, (0, 0))
        self._draw_ai_hand()
        self._draw_banner()
        self._draw_center()
        self._draw_human_hand()
        if self.state == COLOR_SELECTION_MODAL:
            self._draw_color_modal()
        elif self.state == GAME_OVER:
            self._draw_game_over()

    def _draw_ai_hand(self) -> None:
        count = len(self.ai.hand)
        for rect in self._hand_rects(count, SMALL_W, SMALL_H, AI_HAND_Y):
            self.top_card.draw(self.screen, rect, face_up=False)
        text = f"AI - {count} card{'s' if count != 1 else ''}"
        if count == 1:
            text += "  (UNO!)"
        label = Fonts.get(22).render(text, True, WHITE)
        self.screen.blit(label, label.get_rect(center=(WIDTH // 2, AI_HAND_Y + SMALL_H + 22)))

    def _draw_banner(self) -> None:
        pygame.draw.rect(self.screen, (10, 24, 18), BANNER_RECT, border_radius=12)
        border = RGB[self.active_color] if self.active_color in RGB else WHITE
        pygame.draw.rect(self.screen, border, BANNER_RECT, 3, border_radius=12)
        text = Fonts.fit(self.status, WHITE, BANNER_RECT.w - 30, 24)
        self.screen.blit(text, text.get_rect(center=BANNER_RECT.center))

    def _human_needs_draw(self) -> bool:
        return (
            self.state == HUMAN_TURN
            and self.drawn_card is None
            and not self.human.has_playable(self.top_card, self.active_color)
        )

    def _draw_center(self) -> None:
        # Draw pile (stacked look)
        pile = len(self.deck.draw_pile)
        if pile > 0:
            self.top_card.draw(self.screen, DRAW_RECT.move(-4, -4), face_up=False)
            self.top_card.draw(self.screen, DRAW_RECT.move(-2, -2), face_up=False)
            self.top_card.draw(self.screen, DRAW_RECT, face_up=False,
                               highlight=self._human_needs_draw())
        else:
            pygame.draw.rect(self.screen, (14, 62, 40), DRAW_RECT, 3, border_radius=10)
        draw_label = Fonts.get(18).render(f"Draw ({pile})", True, WHITE)
        self.screen.blit(draw_label, draw_label.get_rect(center=(DRAW_RECT.centerx, DRAW_RECT.bottom + 18)))

        # Discard pile
        self.top_card.draw(self.screen, DISCARD_RECT, face_up=True)
        disc_label = Fonts.get(18).render("Discard", True, WHITE)
        self.screen.blit(disc_label, disc_label.get_rect(center=(DISCARD_RECT.centerx, DISCARD_RECT.bottom + 18)))

        # Active colour indicator
        title = Fonts.get(18).render("Active colour", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(INDICATOR_CENTER[0], INDICATOR_CENTER[1] - 56)))
        color = RGB.get(self.active_color, WHITE)
        pygame.draw.circle(self.screen, SHADOW, (INDICATOR_CENTER[0] + 2, INDICATOR_CENTER[1] + 3), 34)
        pygame.draw.circle(self.screen, color, INDICATOR_CENTER, 34)
        pygame.draw.circle(self.screen, WHITE, INDICATOR_CENTER, 34, 4)
        name = Fonts.get(18).render(self.active_color.title(), True, WHITE)
        self.screen.blit(name, name.get_rect(center=(INDICATOR_CENTER[0], INDICATOR_CENTER[1] + 56)))

        # Pass button (only after drawing a playable card)
        if self.state == HUMAN_TURN and self.drawn_card is not None:
            hovered = PASS_RECT.collidepoint(self.mouse_pos)
            draw_button(self.screen, PASS_RECT, "Pass", (120, 60, 60), hovered)

    def _draw_human_hand(self) -> None:
        rects = self._human_rects()
        hovered = self._card_index_at(self.mouse_pos) if self.state == HUMAN_TURN else None
        order = [i for i in range(len(rects)) if i != hovered]
        if hovered is not None:
            order.append(hovered)

        for i in order:
            card = self.human.hand[i]
            rect = rects[i].copy()
            if self.drawn_card is not None:
                playable = card is self.drawn_card
            else:
                playable = self._is_playable(card)
            glow = self.state == HUMAN_TURN and playable
            if i == hovered:
                rect.y -= 16
            card.draw(self.screen, rect, face_up=True, highlight=glow)

        count = len(self.human.hand)
        text = f"Your hand - {count} card{'s' if count != 1 else ''}"
        if count == 1:
            text += "  (UNO!)"
        label = Fonts.get(22).render(text, True, WHITE)
        self.screen.blit(label, label.get_rect(center=(WIDTH // 2, HUMAN_HAND_Y - 40)))

        hint = Fonts.get(15).render(
            "Click a glowing card to play  |  No move? Click the draw pile  |  Esc to quit",
            True, (170, 210, 185))
        self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 42)))

    def _dim(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 175))
        self.screen.blit(overlay, (0, 0))

    def _draw_color_modal(self) -> None:
        self._dim()
        pygame.draw.rect(self.screen, (16, 40, 30), MODAL_RECT, border_radius=18)
        pygame.draw.rect(self.screen, WHITE, MODAL_RECT, 4, border_radius=18)
        title = Fonts.get(30).render("Choose a colour", True, WHITE)
        self.screen.blit(title, title.get_rect(center=(MODAL_RECT.centerx, MODAL_RECT.y + 42)))
        for color, rect in self._color_button_rects().items():
            hovered = rect.collidepoint(self.mouse_pos)
            text_color = BLACK if color == YELLOW else WHITE
            draw_button(self.screen, rect, color.title(), RGB[color], hovered, text_color)

    def _draw_game_over(self) -> None:
        self._dim()
        human_won = self.winner is self.human
        headline = "YOU WIN!" if human_won else "AI WINS!"
        color = GOLD if human_won else (230, 90, 90)
        title = Fonts.get(84).render(headline, True, color)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 70)))
        sub_text = "You emptied your hand. Congratulations!" if human_won else \
            "The AI emptied its hand. Better luck next time!"
        sub = Fonts.get(24).render(sub_text, True, WHITE)
        self.screen.blit(sub, sub.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 10)))
        hovered = PLAY_AGAIN_RECT.collidepoint(self.mouse_pos)
        draw_button(self.screen, PLAY_AGAIN_RECT, "Play Again", (40, 130, 80), hovered)
        hint = Fonts.get(16).render("or press R", True, (200, 220, 205))
        self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, PLAY_AGAIN_RECT.bottom + 22)))


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main() -> None:
    pygame.init()
    pygame.display.set_caption("UNO - Human vs. AI")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    game = UnoGame(screen)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r and game.state == GAME_OVER:
                    game.new_game()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                game.handle_click(event.pos)

        game.mouse_pos = pygame.mouse.get_pos()
        game.update()
        game.draw()
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
