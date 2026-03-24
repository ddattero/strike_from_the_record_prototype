import os
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
        self.turn = 1
        self.deck = self.starter_deck()
        random.shuffle(self.deck)
        self.discard = []
        self.hand = []
        self.log = []
        self.dialogue = ('BAILIFF', 'Act I — The Story Gets Built', 'Opposing counsel wants to build a clean story. Watch for TESTIMONY, create EXPOSED, then IMPEACH.')
        self.enemy_name = 'THE SHOWBOAT'
        self.enemy_intent = self.roll_intent()
        self.draw(5)
        self.started = False

    def roll_intent(self):
        intents = [
            Intent('direct_exam', 'Direct Examination', 'Tell the jury what happened.', 'Creates TESTIMONY LIVE. This enables your contradiction cards.', 'testimony'),
            Intent('polish_story', 'Polish the Story', 'Let\'s keep this simple.', 'Gains SYMPATHY, which softens your pressure.', 'sympathy', 1),
            Intent('grandstanding', 'Grandstanding', 'Counsel can posture all they like.', 'Deals 7 pressure and annoys the judge.', 'attack', 7),
            Intent('overprepare', 'Overprepare the Witness', 'We reviewed this very carefully.', 'Creates TESTIMONY; Gains 1 SYMPATHY.', 'testimony_plus', 1),
            Intent('cheap_shot', 'Cheap Shot', 'Try to keep up.', 'Deals 9 pressure.', 'attack', 9),
        ]
        return random.choice(intents)

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
                self.add_log('TESTIMONY is now EXPOSED.')
                self.set_dialogue('YOU', 'That is not what was said before.', 'EXPOSED means the story has cracked. Now cash it out with Impeach.')
            else:
                self.add_log('No live testimony to challenge.')

        elif card.id == 'impeach':
            dmg = 10
            if self.exposed:
                dmg += 5
                self.exposed = False
            if self.sidebar_boost:
                dmg += 2
                self.sidebar_boost = False
            actual, sympathy_block, shield_block, original = self.deal_to_enemy(dmg)
            log_msg = f'Impeach: {original} damage.'
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
        self.focus = self.max_focus
        self.turn += 1
        self.enemy_intent = self.roll_intent()
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
        self.scene_img = None
        self.build_ui()
        self.refresh()

    def panel(self, parent, **kwargs):
        return tk.Frame(parent, bg=PANEL, highlightbackground=ACCENT, highlightthickness=2, **kwargs)

    def build_ui(self):
        self.root.geometry('1600x1000')
        self.root.minsize(1400, 900)

        self.top = tk.Frame(self.root, bg=BG)
        self.top.pack(fill='x', padx=10, pady=8)

        self.banner = tk.Label(self.top, text='COURT FEED // ACT I — THE STORY GETS BUILT', bg=BG, fg=ACCENT, font=('Courier', 22, 'bold'))
        self.banner.pack(anchor='w')

        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(fill='both', expand=True, padx=10, pady=8)
        self.main.columnconfigure(0, weight=1)  # Left: Stats
        self.main.columnconfigure(1, weight=2)  # Middle: Scene + Action + Cards
        self.main.columnconfigure(2, weight=1)  # Right: Trial Record
        self.main.rowconfigure(0, weight=1)
        self.main.rowconfigure(1, weight=1)

        # ===== LEFT COLUMN: STATS =====
        self.left_stats = tk.Frame(self.main, bg=BG)
        self.left_stats.grid(row=0, column=0, rowspan=2, sticky='nsew', padx=(0, 8), pady=(0, 8))
        self.left_stats.columnconfigure(0, weight=1)

        # Player stats
        self.player_panel = self.panel(self.left_stats)
        self.player_panel.pack(fill='x', pady=(0, 8))
        self.player_stats = tk.Label(self.player_panel, bg=PANEL, fg=TEXT, justify='left', font=('Courier', 13, 'bold'))
        self.player_stats.pack(anchor='w', padx=10, pady=10)

        # Enemy stats
        self.enemy_panel = self.panel(self.left_stats)
        self.enemy_panel.pack(fill='x', pady=(0, 8))
        self.enemy_stats = tk.Label(self.enemy_panel, bg=PANEL, fg=TEXT, justify='left', font=('Courier', 13, 'bold'))
        self.enemy_stats.pack(anchor='w', padx=10, pady=10)

        # Combat state
        self.state_panel = self.panel(self.left_stats)
        self.state_panel.pack(fill='x', pady=(0, 8))
        self.state_stats = tk.Label(self.state_panel, bg=PANEL, fg=TEXT, justify='left', font=('Courier', 12, 'bold'))
        self.state_stats.pack(anchor='w', padx=10, pady=10)

        # Hint/guidance
        self.hint_panel = self.panel(self.left_stats)
        self.hint_panel.pack(fill='both', expand=True)
        self.hint_text = tk.Label(self.hint_panel, bg=PANEL, fg=MUTED, justify='left', font=('Courier', 11), wraplength=180)
        self.hint_text.pack(anchor='nw', padx=10, pady=10)

        # ===== MIDDLE COLUMN: SCENE + ACTION + CARDS =====
        self.middle = tk.Frame(self.main, bg=BG)
        self.middle.grid(row=0, column=1, sticky='nsew', padx=(0, 8), pady=(0, 8))
        self.middle.columnconfigure(0, weight=1)
        self.middle.rowconfigure(0, weight=1)
        self.middle.rowconfigure(1, weight=0)
        self.middle.rowconfigure(2, weight=0)

        # Scene and transcript
        self.scene_panel = self.panel(self.middle)
        self.scene_panel.grid(row=0, column=0, sticky='nsew', padx=0, pady=0)
        self.scene_panel.rowconfigure(0, weight=1)
        self.scene_panel.columnconfigure(0, weight=1)

        self.scene_label = tk.Label(self.scene_panel, bg=PANEL)
        self.scene_label.grid(row=0, column=0, sticky='nsew', padx=8, pady=8)
        self.load_scene()

        self.transcript = tk.Frame(self.scene_panel, bg=PANEL2)
        self.transcript.grid(row=1, column=0, sticky='ew', padx=8, pady=(0, 8))
        self.speaker = tk.Label(self.transcript, text='', bg=PANEL2, fg=ACCENT, font=('Courier', 14, 'bold'))
        self.speaker.pack(anchor='w', padx=10, pady=(8, 0))
        self.bark = tk.Label(self.transcript, text='', bg=PANEL2, fg=TEXT, font=('Courier', 16, 'bold'), wraplength=600, justify='left')
        self.bark.pack(anchor='w', padx=10)
        self.caption = tk.Label(self.transcript, text='', bg=PANEL2, fg=MUTED, font=('Courier', 11), wraplength=600, justify='left')
        self.caption.pack(anchor='w', padx=10, pady=(0, 8))

        # Action summary (what happened this turn)
        self.action_summary = self.panel(self.middle)
        self.action_summary.grid(row=1, column=0, sticky='ew', padx=0, pady=(8, 8))
        self.action_text = tk.Label(self.action_summary, text='', bg=PANEL, fg=GOOD, font=('Courier', 11, 'bold'), wraplength=550, justify='left')
        self.action_text.pack(anchor='nw', padx=10, pady=8)

        # Hand
        self.hand_section = tk.Frame(self.middle, bg=BG)
        self.hand_section.grid(row=2, column=0, sticky='ew', padx=0, pady=(8, 0))
        self.hand_section.columnconfigure(0, weight=1)

        self.hand_title = tk.Label(self.hand_section, text='YOUR HAND // BUILD PATTERNS, BREAK CREDIBILITY', bg=BG, fg=ACCENT, font=('Courier', 14, 'bold'))
        self.hand_title.pack(anchor='w', padx=0, pady=(0, 4))
        self.hand_frame = tk.Frame(self.hand_section, bg=BG)
        self.hand_frame.pack(fill='x', padx=0)

        # ===== RIGHT COLUMN: TRIAL RECORD =====
        self.right = tk.Frame(self.main, bg=BG)
        self.right.grid(row=0, column=2, rowspan=2, sticky='nsew')
        self.right.columnconfigure(0, weight=1)
        self.right.rowconfigure(0, weight=0)
        self.right.rowconfigure(1, weight=1)

        self.overlay = self.panel(self.right)
        self.overlay.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        tk.Label(self.overlay, text='ENCOUNTER START // THE SHOWBOAT', bg=PANEL, fg=ACCENT, font=('Courier', 16, 'bold')).pack(anchor='w', padx=10, pady=(10, 4))
        tk.Label(self.overlay, text='FIRST PATTERN: Wait for TESTIMONY LIVE → PRIOR STATEMENT → IMPEACH.', bg=PANEL, fg=INFO, font=('Courier', 10, 'bold'), wraplength=280, justify='left').pack(anchor='w', padx=10, pady=(4, 4))
        self.start_btn = tk.Button(self.overlay, text='BEGIN CROSS', command=self.begin_cross, bg=ACCENT, fg=BG, font=('Courier', 14, 'bold'), relief='flat')
        self.start_btn.pack(anchor='w', padx=10, pady=(4, 10))

        # Trial record log
        self.trial_record_title = tk.Label(self.right, text='TRIAL RECORD // FIGHT HISTORY', bg=BG, fg=ACCENT, font=('Courier', 13, 'bold'))
        self.trial_record_title.grid(row=0, column=0, sticky='w', padx=0, pady=(8, 4))

        self.trial_record_box = self.panel(self.right)
        self.trial_record_box.grid(row=1, column=0, sticky='nsew', padx=0, pady=0)
        self.trial_record_box.rowconfigure(0, weight=1)
        self.trial_record_box.columnconfigure(0, weight=1)

        self.trial_record_text = tk.Label(self.trial_record_box, text='', bg=PANEL2, fg=MUTED, font=('Courier', 9), justify='left', anchor='nw')
        self.trial_record_text.pack(fill='both', expand=True, padx=8, pady=8)

        # Bottom: controls
        self.bottom = tk.Frame(self.root, bg=BG)
        self.bottom.pack(fill='x', padx=10, pady=8)

        self.controls = self.panel(self.bottom)
        self.controls.pack(fill='x')
        tk.Button(self.controls, text='END TURN', command=self.end_turn, bg=ACCENT, fg=BG, font=('Courier', 14, 'bold'), relief='flat').pack(side='left', padx=10, pady=10)
        tk.Button(self.controls, text='RESTART', command=self.restart, bg=PANEL2, fg=TEXT, font=('Courier', 14, 'bold'), relief='flat').pack(side='left', padx=10, pady=10)

    def load_scene(self):
        img_path = os.path.join(os.path.dirname(__file__), 'courtroom_scene.png')
        if os.path.exists(img_path):
            try:
                self.scene_img = tk.PhotoImage(file=img_path)
                # Scale to fit most screens.
                self.scene_img = self.scene_img.subsample(3, 3)
                self.scene_label.configure(image=self.scene_img)
            except Exception:
                self.scene_label.configure(text='[ court scene unavailable ]', fg=MUTED, font=('Courier', 18, 'bold'))
        else:
            self.scene_label.configure(text='[ court scene missing ]', fg=MUTED, font=('Courier', 18, 'bold'))

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

    def card_status(self, card):
        if card.id == 'prior_statement' and not self.game.testimony_live:
            return ('NEEDS TESTIMONY', WARN)
        if card.id == 'impeach' and not self.game.exposed:
            return ('NEEDS EXPOSED', WARN)
        if card.id == 'admit_exhibit' and self.game.foundation_active:
            return ('BOOSTED', GOOD)
        if card.id == 'objection':
            return ('LIVE', INFO)
        if card.id == 'press_witness' and self.game.testimony_live:
            return ('LIVE', GOOD)
        return ('READY', TEXT)

    def refresh(self):
        g = self.game
        self.speaker.config(text=g.dialogue[0])
        self.bark.config(text=g.dialogue[1])
        self.caption.config(text=g.dialogue[2])

        self.player_stats.config(text=(
            'YOUR CASE\n'
            f'CREDIBILITY: {g.player_cred}\n'
            f'SHIELD: {g.player_shield}\n'
            f'FOCUS: {g.focus}/{g.max_focus}'
        ))
        
        # Highlight enemy defenses if active
        enemy_defense = ''
        if g.enemy_shield > 0:
            enemy_defense += f'\nSHIELD: {g.enemy_shield}'
        if g.enemy_sympathy > 0:
            enemy_defense += f'\nSYMPATHY: {g.enemy_sympathy}'
        
        self.enemy_stats.config(text=(
            f'OPPOSING COUNSEL\n{g.enemy_name}\n'
            f'CREDIBILITY: {g.enemy_cred}\n' +
            (enemy_defense if enemy_defense else '\nNO DEFENSES\n') +
            f'\nINTENT: {g.enemy_intent.name}'
        ))
        
        state_lines = [f'TURN: {g.turn}']
        test_marker = f'TESTIMONY: {"✓ LIVE" if g.testimony_live else "OFF"}'
        state_lines.append(test_marker)
        
        exposed_marker = f'EXPOSED: {"✓ YES" if g.exposed else "NO"}'
        state_lines.append(exposed_marker)
        state_lines.append(f'RECORD: {g.record}')
        state_lines.append(f'JUDGE PATIENCE: {g.judge_patience}')
        
        self.state_stats.config(text='\n'.join(state_lines))
        
        hint = 'WHAT MATTERS NOW\n'
        if not g.started:
            hint += 'Hit BEGIN CROSS. Watch for TESTIMONY LIVE to start your combo.'
        elif g.testimony_live and not g.exposed:
            hint += 'TESTIMONY active. Use PRIOR STATEMENT to EXPOSE.'
        elif g.exposed:
            hint += 'Story is cracked. IMPEACH for big damage.'
        elif g.foundation_active:
            hint += 'FOUNDATION ready. ADMIT EXHIBIT boosted.'
        else:
            hint += 'Build your patterns. Protect your credibility.'
        self.hint_text.config(text=hint)

        # Action summary (most recent moves)
        action_lines = []
        if g.started and len(g.log) > 0:
            # Show last 2-3 moves as action summary
            action_lines = g.log[-3:]
        
        if action_lines:
            self.action_text.config(text='LAST ACTIONS:\n' + '\n'.join(action_lines))
        else:
            self.action_text.config(text='')

        # Trial record (full combat history)
        trial_lines = []
        if g.started:
            trial_lines = g.log[-10:]  # Last 10 moves
        
        if trial_lines:
            self.trial_record_text.config(text='FULL LOG:\n' + '\n'.join(trial_lines))
        else:
            self.trial_record_text.config(text='Fighting has not begun.')

        for w in self.hand_frame.winfo_children():
            w.destroy()
        for i, card in enumerate(g.hand):
            status, color = self.card_status(card)
            
            # Main card frame with playing card styling (raised border for 3D effect)
            card_frame = tk.Frame(self.hand_frame, bg='#e8dcc8', relief='raised', borderwidth=3)
            card_frame.grid(row=0, column=i, padx=6, pady=6, sticky='n')
            
            # Inner card content frame
            inner_frame = tk.Frame(card_frame, bg=CARD_BG)
            inner_frame.pack(fill='both', expand=True, padx=2, pady=2)
            
            # Top-left cost indicator (like card pip)
            top_section = tk.Frame(inner_frame, bg=CARD_BG, height=25)
            top_section.pack(fill='x', padx=4, pady=(4, 0))
            cost_label = tk.Label(top_section, text=str(card.cost), bg=CARD_BG, fg=ACCENT, font=('Courier', 16, 'bold'), width=3)
            cost_label.pack(side='left')
            
            # Card name
            tk.Label(inner_frame, text=f'{card.name}', bg=CARD_BG, fg=ACCENT, font=('Courier', 10, 'bold'), wraplength=130, justify='center').pack(anchor='center', padx=4, pady=(2, 0))
            
            # Tags
            tk.Label(inner_frame, text=' / '.join(card.tags), bg=CARD_BG, fg=INFO, font=('Courier', 8, 'bold'), wraplength=130, justify='center').pack(anchor='center', padx=2, pady=1)
            
            # Card text description
            tk.Label(inner_frame, text=card.text, bg=CARD_BG, fg=TEXT, font=('Courier', 8), wraplength=130, justify='center').pack(anchor='center', padx=4, pady=3)
            
            # Status indicator
            status_label = tk.Label(inner_frame, text=status, bg=CARD_BG, fg=color, font=('Courier', 8, 'bold'))
            status_label.pack(anchor='center', pady=1)
            
            # Play button at bottom
            state = 'normal' if g.started and card.cost <= g.focus and g.enemy_cred > 0 and g.player_cred > 0 else 'disabled'
            tk.Button(inner_frame, text='PLAY', state=state, command=lambda idx=i: self.play(idx), bg=ACCENT, fg=BG, relief='raised', borderwidth=2, font=('Courier', 9, 'bold')).pack(fill='x', padx=4, pady=(2, 4))

        if g.enemy_cred <= 0:
            self.banner.config(text='COURT FEED // VICTORY — THE SHOWBOAT LOST CREDIBILITY')
        elif g.player_cred <= 0:
            self.banner.config(text='COURT FEED // DEFEAT — YOUR CREDIBILITY COLLAPSED')
        else:
            self.banner.config(text='COURT FEED // ACT I — THE STORY GETS BUILT')

if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()
