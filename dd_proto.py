from dataclasses import dataclass
import random

@dataclass
class Card:
    id: str
    name: str
    cost: int
    tags: list[str]
    text: str

@dataclass
class Intent:
    id: str
    name: str
    bark: str
    caption: str
    action: str
    value: int = 0

class Game:
    def __init__(self) -> None:
        self.all_cards = self.build_card_library()
        
    def build_card_library(self) -> dict[str, Card]:
        return {
            'press_witness': Card('press_witness', 'Press the Witness', 1, ['Testimony'], 'Deal 6 pressure. If TESTIMONY is live, deal +2 more.'),
            'foundation': Card('foundation', 'Foundation', 1, ['Procedure'], 'Your next EXHIBIT this turn costs 0 and gains +1 Record.'),
            'admit_exhibit': Card('admit_exhibit', 'Admit Exhibit', 2, ['Exhibit'], 'Deal 7 pressure and gain 1 Record. If Foundation was played, gain +1 Record.'),
            'prior_statement': Card('prior_statement', 'Prior Statement', 1, ['Contradiction'], 'If TESTIMONY is live, apply EXPOSED.'),
            'impeach': Card('impeach', 'Impeach', 2, ['Contradiction'], 'Deal 10 pressure. If EXPOSED, deal +5 more and remove EXPOSED.'),
            'objection': Card('objection', 'Objection', 1, ['Objection'], 'Reduce opposing counsel\'s next move by 50%. If Judge Patience >= 5, draw 1.'),
            'sidebar': Card('sidebar', 'Sidebar', 0, ['Procedure'], 'Your next PROCEDURE or CONTRADICTION card this turn is boosted.'),
            'regain_room': Card('regain_room', 'Regain the Room', 1, ['Utility'], 'Gain 6 shield and restore 1 Judge Patience.'),
            'redirect': Card('redirect', 'Redirect', 1, ['Procedure'], 'Draw 1. If TESTIMONY is not live, gain 1 Focus.'),
        }
    
    def starter_deck(self):
        return [
            'press_witness', 'press_witness', 'foundation', 'admit_exhibit', 'prior_statement',
            'impeach', 'objection', 'sidebar', 'regain_room', 'redirect'
        ]

    def restart(self):
        self.player_cred = 28
        self.player_shield = 0
        self.enemy_cred = 30
        self.enemy_shield = 0
        self.focus = 3
        self.max_focus = 3
        self.record = 0
        self.judge_patience = 8
        self.enemy_sympathy = 0
        self.testimony_live = False
        self.exposed = False
        self.objection_reduction = 0.0
        self.sidebar_boost = False
        self.foundation_active = False
        self.played_this_turn = []
        self.last_card_played = None
        self.reroll_count = 0
        self.turn = 1
        self.deck = self.starter_deck()
        random.shuffle(self.deck)
        self.discard = []
        self.hand = []
        self.log = []
        self.floating_damages = []  # {damage, x, y, age}
        self.dialogue = ('BAILIFF', 'Act I — The Story Gets Built', 'Opposing counsel wants to build a clean story. Watch for TESTIMONY, create EXPOSED, then IMPEACH.')
        self.enemy_name = 'THE SHOWBOAT'
        self.enemy_intent = self.roll_intent()
        self.next_intent = self.roll_intent()
        self.draw(5)
        self.started = False
