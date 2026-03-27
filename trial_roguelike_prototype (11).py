import random
import tkinter as tk
from dataclasses import dataclass
from typing import List, Dict

BG = '#16111f'
PANEL = '#2a1d33'
PANEL2 = '#3a2847'
ACCENT = '#f3b563'
TEXT = '#f6ead7'
MUTED = '#c8b8a6'
DANGER = '#ff6b6b'
GOOD = '#6bffb0'
INFO = '#78d7ff'
WARN = '#ffd56b'
CARD_BG = '#24192c'

# font parameters
FONT_SCALE = 1.3
TITLE_FONT = ('Courier', int(18 * FONT_SCALE), 'bold')
HEADING_FONT = ('Courier', int(14 * FONT_SCALE), 'bold')
BODY_FONT = ('Courier', int(10 * FONT_SCALE))

@dataclass
class Card:
    id: str
    name: str
    cost: int
    tags: List[str]
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
    def __init__(self):
        self.all_cards = self.build_card_library()
        self.restart()

    def build_card_library(self) -> Dict[str, Card]:
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
        self.dialogue = ('', '', 'Opposing counsel wants to build a clean story. Watch for TESTIMONY, create EXPOSED, then IMPEACH.')
        self.enemy_name = 'THE SHOWBOAT'
        self.enemy_intent = self.roll_intent()
        self.next_intent = self.roll_intent()
        self.draw(5)
        self.started = False

    def get_intent_weights(self):
        """Return weighted probabilities for each intent based on current state."""
        w = {
            'direct_exam': 25,
            'polish_story': 20,
            'grandstanding': 20,
            'overprepare': 20,
            'cheap_shot': 15,
        }
        # Testimony not live — priority is establishing the story
        if not self.testimony_live:
            w['direct_exam'] += 15
            w['overprepare'] += 10
            w['grandstanding'] -= 8
            w['cheap_shot'] -= 5
        else:
            # Story already live — shift to defense and aggression
            w['direct_exam'] -= 10
            w['overprepare'] -= 10
            w['polish_story'] += 10
            w['grandstanding'] += 5
        # Player has EXPOSED the story — go aggressive before they can Impeach
        if self.exposed:
            w['cheap_shot'] += 12
            w['grandstanding'] += 8
            w['direct_exam'] -= 8
            w['overprepare'] -= 8
        # Enemy is losing badly — all in on aggression
        if self.enemy_cred < 15:
            w['grandstanding'] += 10
            w['cheap_shot'] += 10
            w['polish_story'] -= 8
        # Player is on the ropes — press the advantage
        if self.player_cred < 15:
            w['cheap_shot'] += 12
            w['grandstanding'] += 8
        # High sympathy stack — can afford to grandstand more
        if self.enemy_sympathy >= 3:
            w['grandstanding'] += 8
            w['polish_story'] -= 8
        # Clamp: no weight below 5
        for k in w:
            w[k] = max(5, w[k])
        return w
    
    def roll_intent(self):
        """Roll a random intent weighted by probabilities."""
        intents_map = {
            'direct_exam': Intent('direct_exam', 'Direct Examination', 'Tell the jury what happened.', 'Creates TESTIMONY LIVE. This enables your contradiction cards.', 'testimony'),
            'polish_story': Intent('polish_story', 'Polish the Story', 'Let\'s keep this simple.', 'Gains SYMPATHY, which softens your pressure.', 'sympathy', 1),
            'grandstanding': Intent('grandstanding', 'Grandstanding', 'Counsel can posture all they like.', 'Deals 7 pressure and annoys the judge.', 'attack', 7),
            'overprepare': Intent('overprepare', 'Overprepare the Witness', 'We reviewed this very carefully.', 'Creates TESTIMONY; Gains 1 SYMPATHY.', 'testimony_plus', 1),
            'cheap_shot': Intent('cheap_shot', 'Cheap Shot', 'Try to keep up.', 'Deals 9 pressure.', 'attack', 9),
        }
        weights = self.get_intent_weights()
        choice = random.choices(list(intents_map.keys()), weights=list(weights.values()), k=1)[0]
        return intents_map[choice]
    
    def get_intent_probabilities(self):
        """Return probabilities as percentages for display."""
        weights = self.get_intent_weights()
        total = sum(weights.values())
        return {k: round((v / total) * 100) for k, v in weights.items()}
    
    def reroll_next_intent(self):
        """Spend Judge Patience to reroll the next intent."""
        cost = 3
        if self.judge_patience < cost:
            self.add_log(f'Not enough Judge Patience! Need {cost}, have {self.judge_patience}.')
            return False
        self.judge_patience -= cost
        self.next_intent = self.roll_intent()
        self.add_log(f'Rerolled next intent! Judge Patience −{cost}.')
        return True

    def draw(self, n):
        for _ in range(n):
            if not self.deck:
                self.deck = self.discard
                self.discard = []
                random.shuffle(self.deck)
            if not self.deck:
                return
            cid = self.deck.pop()
            self.hand.append(self.all_cards[cid])

    def add_log(self, msg):
        self.log.append(msg)
        self.log = self.log[-12:]

    def set_dialogue(self, speaker, bark, caption):
        self.dialogue = (speaker, bark, caption)

    def effective_enemy_damage(self, amount):
        reduced = int(round(amount * (1 - self.objection_reduction)))
        return max(0, reduced)

    def deal_to_enemy(self, amount):
        original = amount
        sympathy_block = min(self.enemy_sympathy, amount)
        amount = max(0, amount - self.enemy_sympathy)
        shield_block = 0
        if self.enemy_shield:
            shield_block = min(self.enemy_shield, amount)
            self.enemy_shield -= shield_block
            amount -= shield_block
        self.enemy_cred = max(0, self.enemy_cred - amount)
        # Create floating damage indicator
        if amount > 0:
            self.floating_damages.append({'damage': amount, 'age': 0})
        return (amount, sympathy_block, shield_block, original)

    def deal_to_player(self, amount):
        original = amount
        shield_block = 0
        if self.player_shield:
            shield_block = min(self.player_shield, amount)
            self.player_shield -= shield_block
            amount -= shield_block
        self.player_cred = max(0, self.player_cred - amount)
        return (amount, shield_block, original)

    def play_card(self, idx):
        if not self.started or idx >= len(self.hand):
            return
        card = self.hand[idx]
        if card.cost > self.focus:
            self.add_log(f'Not enough Focus for {card.name}.')
            return
        self.focus -= card.cost
        self.hand.pop(idx)
        self.discard.append(card.id)
        self.played_this_turn.append(card.id)
        
        # Play sound effect
        try:
            self.root.bell() if hasattr(self, 'root') else None
        except:
            pass

        if card.id == 'press_witness':
            dmg = 6 + (2 if self.testimony_live else 0)
            actual, sympathy_block, shield_block, original = self.deal_to_enemy(dmg)
            log_msg = f'Press the Witness: {original} damage.'
            if sympathy_block > 0:
                log_msg += f' {sympathy_block} blocked by SYMPATHY.'
            if shield_block > 0:
                log_msg += f' {shield_block} blocked by SHIELD.'
            if actual > 0:
                log_msg += f' {actual} actual credibility loss.'
            else:
                log_msg += ' NO DAMAGE DEALT.'
            self.add_log(log_msg)
            self.set_dialogue('YOU', 'Answer the question.', 'Pressure is your basic way to cut into opposing counsel\'s credibility.')

        elif card.id == 'foundation':
            self.foundation_active = True
            self.add_log('Foundation set: next Exhibit is boosted.')
            self.set_dialogue('YOU', 'Let\'s lay a proper foundation.', 'Foundation makes your next Exhibit stronger and helps build Record.')

        elif card.id == 'admit_exhibit':
            bonus_record = 1 if self.foundation_active else 0
            if self.foundation_active:
                self.focus += card.cost  # Foundation makes Exhibit free
            actual, sympathy_block, shield_block, original = self.deal_to_enemy(7)
            self.record += 1 + bonus_record
            self.foundation_active = False
            log_msg = f'Admit Exhibit: {original} damage.'
            if sympathy_block > 0:
                log_msg += f' {sympathy_block} blocked by SYMPATHY.'
            if shield_block > 0:
                log_msg += f' {shield_block} blocked by SHIELD.'
            if actual > 0:
                log_msg += f' {actual} actual credibility loss.'
            else:
                log_msg += ' NO DAMAGE DEALT.'
            log_msg += f' Record +{1 + bonus_record}.'
            self.add_log(log_msg)
            self.set_dialogue('YOU', 'Move to admit Exhibit 12.', 'Record is the usable proof you have locked into the case.')

        elif card.id == 'prior_statement':
            if self.testimony_live:
                self.exposed = True
                self.last_card_played = 'prior_statement'
                self.add_log('TESTIMONY is now EXPOSED. ‖ Impeach next for COMBO BONUS!')
                self.set_dialogue('YOU', 'That is not what was said before.', 'EXPOSED means the story has cracked. Impeach next for +3 COMBO!')
            else:
                self.add_log('No live testimony to challenge.')
                self.last_card_played = None

        elif card.id == 'impeach':
            dmg = 10
            combo_bonus = 0
            # Combo: Prior Statement → Impeach gives +3 damage
            if self.last_card_played == 'prior_statement' and self.exposed:
                dmg += 3
                combo_bonus = 3
            if self.exposed:
                dmg += 5
                self.exposed = False
            if self.sidebar_boost:
                dmg += 2
                self.sidebar_boost = False
            actual, sympathy_block, shield_block, original = self.deal_to_enemy(dmg)
            log_msg = f'Impeach: {original} damage.'
            if combo_bonus > 0:
                log_msg += f' (+{combo_bonus} COMBO BONUS!)'
            if sympathy_block > 0:
                log_msg += f' {sympathy_block} blocked by SYMPATHY.'
            if shield_block > 0:
                log_msg += f' {shield_block} blocked by SHIELD.'
            if actual > 0:
                log_msg += f' {actual} actual credibility loss.'
            else:
                log_msg += ' NO DAMAGE DEALT.'
            self.add_log(log_msg)
            self.set_dialogue('YOU', 'No further dancing around it.', 'Impeach is your main payoff against EXPOSED.')

        elif card.id == 'objection':
            self.objection_reduction += 0.5
            if self.judge_patience >= 5:
                self.draw(1)
                self.add_log('Objection sustained enough to draw 1.')
            else:
                self.judge_patience = max(0, self.judge_patience - 1)
                self.add_log('Objection overruled. Judge Patience −1.')
            self.set_dialogue('YOU', 'Objection.', 'Objection weakens the next enemy move. Higher Judge Patience makes it stronger.')

        elif card.id == 'sidebar':
            self.sidebar_boost = True
            self.add_log('Sidebar: next Procedure/Contradiction is boosted.')
            self.set_dialogue('YOU', 'May we approach?', 'Sidebar sets up a cleaner contradiction or procedure play.')

        elif card.id == 'regain_room':
            self.player_shield += 6
            self.judge_patience = min(10, self.judge_patience + 1)
            self.add_log('You gain 6 shield and restore 1 Judge Patience.')
            self.set_dialogue('YOU', 'Let\'s reset the room.', 'Shield protects your credibility. Judge Patience supports your control tools.')

        elif card.id == 'redirect':
            self.draw(1)
            if not self.testimony_live:
                self.focus += 1
            self.add_log('Redirect draws 1; if no testimony is live, gain 1 Focus.')
            self.set_dialogue('YOU', 'Let\'s clarify that.', 'Redirect is a tempo card that helps when the room is not in crisis yet.')

        if self.enemy_cred <= 0:
            self.set_dialogue('THE SHOWBOAT', 'No further questions.', 'You won by breaking opposing counsel\'s credibility before your own collapsed.')

    def end_turn(self):
        if not self.started or self.enemy_cred <= 0 or self.player_cred <= 0:
            return
        self.last_card_played = None  # Reset combo tracker
        intent = self.enemy_intent
        self.set_dialogue(self.enemy_name, intent.bark, intent.caption)
        self.add_log(f'{self.enemy_name} uses {intent.name}.')

        if intent.action == 'testimony':
            self.testimony_live = True
            self.add_log('TESTIMONY LIVE.')
        elif intent.action == 'sympathy':
            self.enemy_sympathy += intent.value
            self.add_log(f'SYMPATHY +{intent.value}.')
        elif intent.action == 'attack':
            dmg = self.effective_enemy_damage(intent.value)
            actual, shield_block, original = self.deal_to_player(dmg)
            self.judge_patience = max(0, self.judge_patience - (1 if intent.id == 'grandstanding' else 0))
            log_msg = f'{self.enemy_name} deals {original} pressure.'
            if shield_block > 0:
                log_msg += f' {shield_block} blocked by your SHIELD.'
            if actual > 0:
                log_msg += f' You lose {actual} credibility.'
            else:
                log_msg += ' FULLY PROTECTED BY SHIELD.'
            self.add_log(log_msg)
        elif intent.action == 'testimony_plus':
            self.testimony_live = True
            self.enemy_sympathy += intent.value
            self.add_log('TESTIMONY LIVE and SYMPATHY +1.')

        self.objection_reduction = 0.0
        self.sidebar_boost = False
        self.played_this_turn = []
        self.last_card_played = None
        self.reroll_count = 0
        self.focus = self.max_focus
        self.turn += 1
        self.enemy_intent = self.next_intent
        self.next_intent = self.roll_intent()
        self.draw(5 - len(self.hand))

        if self.player_cred <= 0:
            self.set_dialogue(self.enemy_name, 'A clean story beats a messy theory.', 'You lost when your credibility hit zero first.')
        elif self.enemy_cred <= 0:
            self.set_dialogue(self.enemy_name, 'The room has turned.', 'You won the duel by collapsing the opposing story.')

class App:
    def __init__(self, root):
        self.root = root
        self.root.title('STRIKE FROM THE RECORD // ACT I PROTOTYPE')
        self.root.configure(bg=BG)
        self.game = Game()
        self.game.root = self.root  # Pass root for sound effects
        self.build_ui()
        self.refresh()

    def panel(self, parent, **kwargs):
        return tk.Frame(parent, bg=PANEL, highlightbackground=ACCENT, highlightthickness=1, **kwargs)

    def create_rounded_panel(self, parent, **pack_kwargs):
        """Create a properly functioning rounded panel that doesn't have text overflow issues.
        Returns just the inner frame where content should be added."""
        # Outer container for border effect (accent-colored)
        outer = tk.Frame(parent, bg=ACCENT, relief='flat', borderwidth=0)
        outer.pack(**pack_kwargs)
        
        # Inner panel (actual content area)
        inner = tk.Frame(outer, bg=PANEL)
        inner.pack(fill='both', expand=True, padx=2, pady=2)
        
        return inner

    def build_ui(self):
        self.root.geometry('1400x900')
        self.root.minsize(1100, 700)
        self.root.config(bg=BG)

        self.top = tk.Frame(self.root, bg=BG)
        self.top.pack(fill='x', padx=10, pady=8)

        self.banner = tk.Label(
            self.top,
            text='STRIKE FROM THE RECORD // SIMPLE BUILD',
            bg=BG,
            fg=ACCENT,
            font=TITLE_FONT
        )
        self.banner.pack(anchor='w')

        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(fill='both', expand=True, padx=10, pady=(0, 8))
        self.main.columnconfigure(0, weight=1)
        self.main.columnconfigure(1, weight=2)
        self.main.columnconfigure(2, weight=1)
        self.main.rowconfigure(0, weight=1)
        self.main.rowconfigure(1, weight=0)

        self.left_panel = self.panel(self.main)
        self.left_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 8))

        self.guidance_text = tk.Label(
            self.left_panel,
            text='',
            bg=PANEL,
            fg=TEXT,
            font=BODY_FONT,
            justify='left',
            wraplength=260,
            anchor='nw'
        )
        self.guidance_text.pack(fill='x', padx=10, pady=(10, 8))

        self.top_left_status = tk.Label(
            self.main,
            text='',
            bg='#1a1410',
            fg=ACCENT,
            font=BODY_FONT,
            justify='left',
            padx=8,
            pady=4
        )
        self.top_left_status.place(relx=0.02, rely=0.135, anchor='nw', width=220, height=42)

        # =========================================================
        # PAPER STATS PANEL (placed over notebook area on desk)
        # =========================================================
        text_x0, text_y0, text_x1, text_y1 = CLIPBOARD_TEXT_BOUNDS
        text_relx, text_rely = self.scene_to_rel(text_x0, text_y0)

        self.paper_stats = tk.Canvas(
            self.main,
            bg='#efe2c2',
            highlightthickness=0,
            bd=0,
            relief='flat'
        )
        self.paper_stats.place(
            relx=text_relx,
            rely=text_rely,
            anchor='nw',
            width=(text_x1 - text_x0),
            height=(text_y1 - text_y0)
        )

        # =========================================================
        # DIALOGUE BOX (floating above desk, centered)
        # =========================================================
        self.transcript = tk.Frame(self.main, bg='#241a22', highlightbackground=ACCENT, highlightthickness=2)
        self.transcript.place_forget()

        self.speaker = tk.Label(
            self.transcript,
            text='',
            bg=PANEL,
            fg=ACCENT,
            font=BODY_FONT
        )
        self.top_left_status.pack(fill='x', padx=10, pady=(0, 8))

        self.paper_stats = tk.Label(
            self.left_panel,
            text='',
            bg=PANEL,
            fg=TEXT,
            font=BODY_FONT,
            wraplength=480,
        )
        self.bark.pack(anchor='w', padx=10, pady=4)

        self.caption = tk.Label(
            self.transcript,
            text='',
            bg=PANEL,
            fg=MUTED,
            font=BODY_FONT,
            wraplength=480,
            justify='left'
        )
        self.caption.pack(anchor='w', padx=10, pady=(0, 8))

        # =========================================================
        # NEXT TURN ODDS / ALERT BOX
        # =========================================================
        self.prob_text = tk.Label(
            self.main,
            text='',
            bg='#241a22',
            fg=GOOD,
            font=BODY_FONT,
            justify='left',
            anchor='nw'
        )
        self.prob_text.place(relx=0.02, rely=0.98, anchor='sw', width=195, height=110)

        # =========================================================
        # ENCOUNTER START / ONBOARDING BOX
        # =========================================================
        overlay_outer = tk.Frame(self.main, bg=ACCENT, relief='flat', borderwidth=0)
        overlay_outer.place(relx=0.92, rely=0.12, anchor='ne', width=250, height=132)

        self.overlay = tk.Frame(overlay_outer, bg=PANEL)
        self.overlay.pack(fill='both', expand=True, padx=2, pady=2)

        tk.Label(
            self.overlay,
            text='THE SHOWBOAT',
            bg=PANEL,
            fg=ACCENT,
            font=HEADING_FONT,
            wraplength=250,
            justify='left'
        ).pack(anchor='w', padx=10, pady=(10, 4))

        tk.Label(
            self.overlay,
            text='Wait for TESTIMONY.\nThen PRIOR STATEMENT → IMPEACH.',
            bg=PANEL,
            fg=INFO,
            font=BODY_FONT,
            wraplength=250,
            justify='left'
        ).pack(anchor='w', padx=10, pady=(0, 6))

        self.start_btn = tk.Button(
            self.overlay,
            text='BEGIN CROSS',
            command=self.begin_cross,
            bg=ACCENT,
            fg=BG,
            font=HEADING_FONT,
            relief='flat'
        )
        self.start_btn.pack(anchor='w', padx=10, pady=(0, 10), fill='x')

        # =========================================================
        # COMBAT LOG (compact, right side)
        # =========================================================
        self.combat_log_text = tk.Label(
            self.main,
            text='',
            bg='#20161d',
            fg=TEXT,
            font=BODY_FONT,
            justify='left',
            anchor='nw',
            padx=8,
            pady=8,
            highlightbackground=ACCENT,
            highlightthickness=2
        )
        self.combat_log_text.place(relx=0.78, rely=0.50, anchor='nw', width=210, height=118)

        # =========================================================
        # HAND / CARDS ON TABLE
        # =========================================================
        self.hand_title = tk.Label(
            self.main,
            text='YOUR HAND',
            bg='#1a1410',
            fg='#f6d7a7',
            font=BODY_FONT
        )
        self.hand_title.place(relx=0.73, rely=0.69, anchor='w')

        self.deck_info = tk.Label(
            self.left_panel,
            text='',
            bg=PANEL,
            fg=MUTED,
            font=BODY_FONT
        )
        self.deck_info.pack(fill='x', padx=10, pady=(0, 4))

        self.center_panel = self.panel(self.main)
        self.center_panel.grid(row=0, column=1, sticky='nsew', padx=(0, 8))
        self.center_panel.columnconfigure(0, weight=1)
        self.center_panel.rowconfigure(1, weight=1)

        self.transcript = tk.Frame(self.center_panel, bg=PANEL)
        self.transcript.grid(row=0, column=0, sticky='ew', padx=10, pady=10)

        self.speaker = tk.Label(self.transcript, text='', bg=PANEL, fg=ACCENT, font=('Courier', 11, 'bold'))
        self.speaker.pack(anchor='w')
        self.bark = tk.Label(self.transcript, text='', bg=PANEL, fg=TEXT, font=('Courier', 11, 'bold'), justify='left', wraplength=520)
        self.bark.pack(anchor='w', pady=(4, 2))
        self.caption = tk.Label(self.transcript, text='', bg=PANEL, fg=MUTED, font=('Courier', 9), justify='left', wraplength=520)
        self.caption.pack(anchor='w')

        self.hand_title = tk.Label(self.center_panel, text='HAND', bg=PANEL, fg=ACCENT, font=('Courier', 12, 'bold'))
        self.hand_title.grid(row=2, column=0, sticky='w', padx=10, pady=(6, 4))

        self.hand_frame = tk.Frame(self.center_panel, bg=PANEL)
        self.hand_frame.grid(row=3, column=0, sticky='ew', padx=10, pady=(0, 10))

        self.right_panel = self.panel(self.main)
        self.right_panel.grid(row=0, column=2, sticky='nsew')

        self.overlay = tk.Frame(self.right_panel, bg=PANEL)
        self.overlay.pack(fill='x', padx=10, pady=(10, 6))
        tk.Label(self.overlay, text='THE SHOWBOAT', bg=PANEL, fg=ACCENT, font=('Courier', 12, 'bold')).pack(anchor='w')
        self.enemy_cred_lbl = tk.Label(self.overlay, text='Credibility: 30', bg=PANEL, fg=DANGER, font=('Courier', 9, 'bold'))
        self.enemy_cred_lbl.pack(anchor='w', pady=(2, 6))
        self.start_btn = tk.Button(self.overlay, text='BEGIN CROSS', command=self.begin_cross, bg=ACCENT, fg=BG, font=('Courier', 11, 'bold'), relief='raised')
        self.start_btn.pack(fill='x')

        # THIS TURN intent card
        self.intent_frame = tk.Frame(self.right_panel, bg=PANEL2, relief='flat')
        self.intent_frame.pack(fill='x', padx=10, pady=(6, 3))
        tk.Label(self.intent_frame, text='THIS TURN', bg=PANEL2, fg=MUTED, font=('Courier', 7, 'bold')).pack(anchor='w', padx=8, pady=(6, 1))
        self.intent_name_lbl = tk.Label(self.intent_frame, text='—', bg=PANEL2, fg=ACCENT, font=('Courier', 10, 'bold'), wraplength=230, justify='left')
        self.intent_name_lbl.pack(anchor='w', padx=8, pady=(0, 1))
        self.intent_action_lbl = tk.Label(self.intent_frame, text='', bg=PANEL2, fg=WARN, font=('Courier', 9, 'bold'), wraplength=230, justify='left')
        self.intent_action_lbl.pack(anchor='w', padx=8, pady=(0, 1))
        self.intent_desc_lbl = tk.Label(self.intent_frame, text='', bg=PANEL2, fg=MUTED, font=('Courier', 8), wraplength=230, justify='left')
        self.intent_desc_lbl.pack(anchor='w', padx=8, pady=(0, 6))

        # NEXT TURN intent card
        self.next_intent_frame = tk.Frame(self.right_panel, bg=CARD_BG, relief='flat')
        self.next_intent_frame.pack(fill='x', padx=10, pady=(0, 3))
        tk.Label(self.next_intent_frame, text='NEXT TURN', bg=CARD_BG, fg=MUTED, font=('Courier', 7, 'bold')).pack(anchor='w', padx=8, pady=(6, 1))
        self.next_intent_name_lbl = tk.Label(self.next_intent_frame, text='—', bg=CARD_BG, fg=INFO, font=('Courier', 10, 'bold'), wraplength=230, justify='left')
        self.next_intent_name_lbl.pack(anchor='w', padx=8, pady=(0, 1))
        self.next_intent_action_lbl = tk.Label(self.next_intent_frame, text='', bg=CARD_BG, fg=MUTED, font=('Courier', 8, 'bold'), wraplength=230, justify='left')
        self.next_intent_action_lbl.pack(anchor='w', padx=8, pady=(0, 6))

        # Future odds display
        self.prob_text = tk.Label(
            self.right_panel,
            text='',
            bg=PANEL,
            fg=GOOD,
            font=('Courier', 8),
            justify='left',
            anchor='nw'
        )
        self.prob_text.pack(fill='x', padx=10, pady=(0, 4))

        # Combat log
        self.combat_log_text = tk.Label(
            self.right_panel,
            text='',
            bg=PANEL,
            fg=TEXT,
            font=('Courier', 8),
            justify='left',
            anchor='nw',
            wraplength=240
        )
        self.combat_log_text.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        self.bottom = tk.Frame(self.root, bg=BG)
        self.bottom.pack(fill='x', padx=10, pady=(0, 10))

        self.reroll_btn = tk.Button(self.bottom, text='REROLL NEXT TURN', command=self.reroll_next, bg=WARN, fg='#000000', font=('Courier', 10, 'bold'), relief='raised')
        self.reroll_btn.pack(side='left', padx=(0, 8))
        tk.Button(self.bottom, text='END TURN', command=self.end_turn, bg=ACCENT, fg=BG, font=('Courier', 12, 'bold'), relief='raised').pack(side='left', padx=(0, 8))
        tk.Button(self.bottom, text='RESTART', command=self.restart, bg=PANEL2, fg=TEXT, font=('Courier', 12, 'bold'), relief='raised').pack(side='left')

        self.hand_cards = []

        # =========================================================
        # BOTTOM CONTROLS
        # =========================================================
        self.bottom = tk.Frame(self.root, bg='#1a1410')
        self.bottom.place(relx=0.86, rely=0.97, anchor='se', width=310, height=54)

        self.controls = tk.Frame(self.bottom, bg='#1a1410')
        self.controls.pack(fill='both', expand=True, padx=8, pady=8)

        self.reroll_btn = tk.Button(
            self.controls,
            text='REROLL NEXT TURN',
            command=self.reroll_next,
            bg=WARN,
            fg='#000000',
            font=BODY_FONT,
            relief='flat',
            borderwidth=0,
            width=16
        )
        self.reroll_btn.pack(side='left', padx=6)

        tk.Button(
            self.controls,
            text='END TURN',
            command=self.end_turn,
            bg=ACCENT,
            fg=BG,
            font=HEADING_FONT,
            relief='flat',
            width=12
        ).pack(side='left', padx=6)

        tk.Button(
            self.controls,
            text='RESTART',
            command=self.restart,
            bg=PANEL2,
            fg=TEXT,
            font=HEADING_FONT,
            relief='flat',
            width=12
        ).pack(side='left', padx=6)


    def load_scene(self):
        """Load and scale the courtroom image to fullscreen background."""
        img_path = os.path.join(os.path.dirname(__file__), 'courtroom_scene.png')
        if not os.path.exists(img_path):
            self.scene_label.config(text='[ courtroom_scene.png not found ]', fg=MUTED, font=TITLE_FONT )
            return
            
        try:
            # Get actual window size
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            
            # If window not yet sized, use sensible defaults
            if w < 100 or h < 100:
                w, h = 1600, 1000
            
            # Load and resize image
            img = Image.open(img_path).convert('RGB')
            img_resized = img.resize((w, h), Image.Resampling.LANCZOS)
            
            # Store reference and display
            self.scene_img = ImageTk.PhotoImage(img_resized)
            self.scene_label.config(image=self.scene_img, text='')
            self.scene_label.lower()
            
        except Exception as e:
            self.scene_label.config(text=f'[ background error: {str(e)} ]', fg=MUTED, font=TITLE_FONT )

    def begin_cross(self):
        self.game.started = True
        self.start_btn.configure(state='disabled')
        self.game.set_dialogue('THE SHOWBOAT', 'Ladies and gentlemen, this case is simpler than my learned friend wants you to believe.', 'The Showboat wants to build a clean story. Watch his TESTIMONY and break his credibility.')
        self.refresh()

    def restart(self):
        self.game.restart()
        self.start_btn.configure(state='normal')
        self.refresh()

    def end_turn(self):
        self.game.end_turn()
        self.refresh()

    def play(self, idx):
        self.game.play_card(idx)
        self.refresh()

    def reroll_next(self):
        """Spend Judge Patience to reroll the next intent."""
        if self.game.reroll_next_intent():
            self.refresh()

    def _draw_rounded_rect(self, canvas, x1, y1, x2, y2, radius=15, **kwargs):
        """Draw a rounded rectangle on a Canvas widget."""
        points = [
            x1+radius, y1,
            x1+radius, y1,
            x2-radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1+radius,
            x1, y1
        ]
        return canvas.create_polygon(points, **kwargs, smooth=True)

    def card_status(self, card):
        if card.id == 'prior_statement' and not self.game.testimony_live:
            return ('NEEDS TESTIMONY', WARN)
        if card.id == 'impeach' and not self.game.exposed:
            return ('NEEDS EXPOSED', WARN)
        if card.id == 'impeach' and self.game.exposed and self.game.last_card_played == 'prior_statement':
            return ('★ COMBO READY ★', GOOD)
        if card.id == 'admit_exhibit' and self.game.foundation_active:
            return ('BOOSTED', GOOD)
        if card.id == 'objection':
            return ('LIVE', INFO)
        if card.id == 'press_witness' and self.game.testimony_live:
            return ('LIVE', GOOD)
        return ('READY', TEXT)

    def refresh(self):
        g = self.game
        
        # Age and remove floating damages
        g.floating_damages = [d for d in g.floating_damages if d['age'] < 30]
        for d in g.floating_damages:
            d['age'] += 1
        
        self.speaker.config(text=g.dialogue[0])
        self.bark.config(text=g.dialogue[1])
        self.caption.config(text=g.dialogue[2])
        self.guidance_text.config(text=g.dialogue[2])
        self.top_left_status.config(
            text=(
                f'Opp. Health: {g.enemy_cred}\n'
                f'Testimony: {"ON" if g.testimony_live else "OFF"}'
            )
        )
        self.enemy_cred_lbl.config(
            text=f'Credibility: {g.enemy_cred}' + (f'  Shield: {g.enemy_shield}' if g.enemy_shield else ''),
            fg=DANGER if g.enemy_cred <= 10 else WARN if g.enemy_cred <= 20 else TEXT
        )

        deck_count = len(g.deck)
        discard_count = len(g.discard)

        clipboard_lines = [
            'CASE NOTES',
            '',
            f'Turn: {g.turn}',
            f'Credibility: {g.player_cred}',
            f'Shield: {g.player_shield}',
            f'Focus: {g.focus}/{g.max_focus}',
            f'Record: {g.record}',
            f'Judge Patience: {g.judge_patience}',
            f'Deck: {deck_count}',
            f'Discard: {discard_count}',
            '',
            'OPPOSITION',
            f'Sympathy: {g.enemy_sympathy}',
            f'Exposed: {"YES" if g.exposed else "NO"}',
        ]
        self.paper_stats.delete('all')
        paper_width = int(self.paper_stats.winfo_width() or 265)
        y = 18
        for index, line in enumerate(clipboard_lines):
            is_header = line in ('CASE NOTES', 'OPPOSITION')
            font = HEADING_FONT if is_header else BODY_FONT
            fill = '#5d4226' if is_header else '#4a3320'
            self.paper_stats.create_text(
                28,
                y,
                text=line,
                anchor='nw',
                font=font,
                fill=fill,
                angle=7,
                width=paper_width - 40
            )
            y += 28 if is_header else 22

        # Combat log
        combat_display = '\n'.join(g.log[-8:]) if g.started and g.log else ''
        self.combat_log_text.config(text=combat_display)

        # Intent display helpers
        INTENT_ICONS = {
            'direct_exam': '📖', 'polish_story': '✨',
            'grandstanding': '🎭', 'overprepare': '📚', 'cheap_shot': '⚡',
        }
        def action_label(intent):
            if intent.action == 'attack':
                return (f'ATTACK  {intent.value} pressure', DANGER)
            if intent.action == 'testimony':
                return ('TESTIMONY: Creates LIVE', WARN)
            if intent.action == 'sympathy':
                return (f'SYMPATHY +{intent.value}: Softens pressure', INFO)
            if intent.action == 'testimony_plus':
                return ('TESTIMONY + SYMPATHY +1', WARN)
            return (intent.action, MUTED)

        if g.started:
            ei = g.enemy_intent
            ei_label, ei_color = action_label(ei)
            self.intent_name_lbl.config(text=f'{INTENT_ICONS.get(ei.id, "?")}  {ei.name}')
            self.intent_action_lbl.config(text=ei_label, fg=ei_color)
            self.intent_desc_lbl.config(text=ei.caption)

            ni = g.next_intent
            ni_label, _ = action_label(ni)
            self.next_intent_name_lbl.config(text=f'{INTENT_ICONS.get(ni.id, "?")}  {ni.name}')
            self.next_intent_action_lbl.config(text=ni_label)

            # Future odds
            probs = g.get_intent_probabilities()
            intent_display_names = {
                'direct_exam': ('📖', 'Direct Exam'),
                'polish_story': ('✨', 'Polish Story'),
                'grandstanding': ('🎭', 'Grandstand'),
                'overprepare': ('📚', 'Overprepare'),
                'cheap_shot': ('⚡', 'Cheap Shot'),
            }
            odds_lines = ['FUTURE ODDS']
            for key in ['direct_exam', 'polish_story', 'grandstanding', 'overprepare', 'cheap_shot']:
                icon, name = intent_display_names[key]
                odds_lines.append(f'{icon} {name:<14} {probs[key]}%')
            self.prob_text.config(text='\n'.join(odds_lines))
        else:
            self.intent_name_lbl.config(text='—')
            self.intent_action_lbl.config(text='Waiting for cross to begin', fg=MUTED)
            self.intent_desc_lbl.config(text='')
            self.next_intent_name_lbl.config(text='—')
            self.next_intent_action_lbl.config(text='')
            self.prob_text.config(text='')

        # Update reroll button state and styling
        reroll_enabled = g.started and g.judge_patience >= 3 and g.enemy_cred > 0 and g.player_cred > 0
        self.reroll_btn.config(state='normal' if reroll_enabled else 'disabled')

        for canvas in getattr(self, 'hand_cards', []):
            canvas.destroy()
        self.hand_cards = []

        if not g.started:
            self.deck_info.config(text='')
            if g.enemy_cred <= 0:
                self.banner.config(text='COURT FEED // VICTORY — THE SHOWBOAT LOST CREDIBILITY')
            elif g.player_cred <= 0:
                self.banner.config(text='COURT FEED // DEFEAT — YOUR CREDIBILITY COLLAPSED')
            else:
                self.banner.config(text='COURT FEED // ACT I')
            return

        card_width = 148
        card_height = 240

        card_row = tk.Frame(self.hand_frame, bg=PANEL)
        card_row.pack(anchor='center', pady=4)
        self.hand_cards.append(card_row)

        for i, card in enumerate(g.hand):
            status, color = self.card_status(card)
            card_x = start_x + i * horizontal_step
            card_y = row_y
            
            card_canvas = tk.Canvas(self.main, width=card_width, height=card_height, bg='#6f3816', highlightthickness=0, relief='flat', borderwidth=0)
            card_canvas.place(x=card_x, y=card_y)
            self.hand_cards.append(card_canvas)
            
            # Draw rounded rectangle for card background
            self._draw_rounded_rect(card_canvas, 1, 1, card_width-1, card_height-1, radius=15, fill='#cdb89c', outline='#201610', width=2)
            
            # Create a frame to hold card content
            content_frame = tk.Frame(card_canvas, bg='#cdb89c', relief='flat', borderwidth=0)
            card_canvas.create_window(card_width // 2, card_height // 2, window=content_frame, width=card_width - 10, height=card_height - 10)
            
            # Top section with cost
            top_row = tk.Frame(content_frame, bg='#cdb89c')
            top_row.pack(fill='x', padx=8, pady=(7, 3))
            cost_label = tk.Label(top_row, text=str(card.cost), bg='#cdb89c', fg='#201610', font=HEADING_FONT)
            cost_label.pack(side='left')
            
            # Card name
            tk.Label(content_frame, text=card.name, bg='#cdb89c', fg='#201610', font=BODY_FONT, wraplength=132, justify='center').pack(padx=9, pady=(0, 3))
            
            # Card tags - smaller and muted
            tk.Label(content_frame, text=' • '.join(card.tags), bg='#cdb89c', fg='#6d5743', font=BODY_FONT, wraplength=132, justify='center').pack(padx=9, pady=(0, 3))
            
            # Card description - cleaner layout
            tk.Label(content_frame, text=card.text, bg='#cdb89c', fg='#2d221d', font=BODY_FONT, wraplength=130, justify='left').pack(padx=10, pady=(3, 6), anchor='n')
            
            # Status indicator - compact
            if status and status != '':
                tk.Label(content_frame, text=status, bg='#cdb89c', fg=color, font=BODY_FONT).pack(pady=(0, 5))
            
            # Play button - full width at bottom
            state = 'normal' if g.started and card.cost <= g.focus and g.enemy_cred > 0 and g.player_cred > 0 else 'disabled'
            tk.Button(content_frame, text='PLAY', state=state, command=lambda idx=i: self.play(idx), bg='#f3b563', fg='#16111f', relief='flat', font=BODY_FONT).pack(fill='x', padx=8, pady=(4, 7))

        self.deck_info.config(text='')

        if g.enemy_cred <= 0:
            self.banner.config(text='COURT FEED // VICTORY — THE SHOWBOAT LOST CREDIBILITY')
        elif g.player_cred <= 0:
            self.banner.config(text='COURT FEED // DEFEAT — YOUR CREDIBILITY COLLAPSED')
        else:
            self.banner.config(text='COURT FEED // ACT I')

if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()
