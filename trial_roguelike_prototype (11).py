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
            'press_witness': Card('press_witness', 'Press the Witness', 1, ['Testimony'], 'Deal 4 pressure. If TESTIMONY is live, deal +2.'),
            'foundation': Card('foundation', 'Foundation', 1, ['Procedure'], 'Your next EXHIBIT this turn costs 0 and gains +1 Record.'),
            'admit_exhibit': Card('admit_exhibit', 'Admit Exhibit', 2, ['Exhibit'], 'Deal 5 pressure and gain 1 Record. If Foundation was played, gain +1 Record.'),
            'prior_statement': Card('prior_statement', 'Prior Statement', 1, ['Contradiction'], 'If TESTIMONY is live, apply EXPOSED.'),
            'impeach': Card('impeach', 'Impeach', 2, ['Contradiction'], 'Deal 8. If EXPOSED, deal +5 and remove EXPOSED.'),
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
        self.player_cred = 40
        self.player_shield = 0
        self.enemy_cred = 42
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
            Intent('polish_story', 'Polish the Story', 'Let\'s keep this simple.', 'Gains SYMPATHY, which softens your pressure.', 'sympathy', 2),
            Intent('grandstanding', 'Grandstanding', 'Counsel can posture all they like.', 'Deals 6 pressure and annoys the judge.', 'attack', 6),
            Intent('overprepare', 'Overprepare the Witness', 'We reviewed this very carefully.', 'Creates TESTIMONY and 1 SYMPATHY.', 'testimony_plus', 1),
            Intent('cheap_shot', 'Cheap Shot', 'Try to keep up.', 'Deals 8 pressure.', 'attack', 8),
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
        amount = max(0, amount - self.enemy_sympathy)
        if self.enemy_shield:
            blocked = min(self.enemy_shield, amount)
            self.enemy_shield -= blocked
            amount -= blocked
        self.enemy_cred -= amount
        return amount

    def deal_to_player(self, amount):
        if self.player_shield:
            blocked = min(self.player_shield, amount)
            self.player_shield -= blocked
            amount -= blocked
        self.player_cred -= amount
        return amount

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
            dmg = 4 + (2 if self.testimony_live else 0)
            dealt = self.deal_to_enemy(dmg)
            self.add_log(f'Press the Witness deals {dealt}.')
            self.set_dialogue('YOU', 'Answer the question.', 'Pressure is your basic way to cut into opposing counsel\'s credibility.')

        elif card.id == 'foundation':
            self.foundation_active = True
            self.add_log('Foundation set: next Exhibit is boosted.')
            self.set_dialogue('YOU', 'Let\'s lay a proper foundation.', 'Foundation makes your next Exhibit stronger and helps build Record.')

        elif card.id == 'admit_exhibit':
            bonus_record = 1 if self.foundation_active else 0
            dealt = self.deal_to_enemy(5)
            self.record += 1 + bonus_record
            self.foundation_active = False
            self.add_log(f'Admit Exhibit deals {dealt}; Record +{1 + bonus_record}.')
            self.set_dialogue('YOU', 'Move to admit Exhibit 12.', 'Record is the usable proof you have locked into the case.')

        elif card.id == 'prior_statement':
            if self.testimony_live:
                self.exposed = True
                self.add_log('TESTIMONY is now EXPOSED.')
                self.set_dialogue('YOU', 'That is not what was said before.', 'EXPOSED means the story has cracked. Now cash it out with Impeach.')
            else:
                self.add_log('No live testimony to challenge.')

        elif card.id == 'impeach':
            dmg = 8
            if self.exposed:
                dmg += 5
                self.exposed = False
            if self.sidebar_boost:
                dmg += 2
                self.sidebar_boost = False
            dealt = self.deal_to_enemy(dmg)
            self.add_log(f'Impeach deals {dealt}.')
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
            dealt = self.deal_to_player(dmg)
            self.judge_patience = max(0, self.judge_patience - (1 if intent.id == 'grandstanding' else 0))
            self.add_log(f'You lose {dealt} credibility.')
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
        self.root.geometry('1500x980')
        self.root.minsize(1300, 880)

        self.top = tk.Frame(self.root, bg=BG)
        self.top.pack(fill='x', padx=10, pady=8)

        self.banner = tk.Label(self.top, text='COURT FEED // ACT I — THE STORY GETS BUILT', bg=BG, fg=ACCENT, font=('Courier', 22, 'bold'))
        self.banner.pack(anchor='w')

        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(fill='both', expand=True, padx=10, pady=8)
        self.main.columnconfigure(0, weight=3)
        self.main.columnconfigure(1, weight=2)
        self.main.rowconfigure(0, weight=1)
        self.main.rowconfigure(1, weight=1)

        # Left top: image + transcript
        self.left_top = self.panel(self.main)
        self.left_top.grid(row=0, column=0, sticky='nsew', padx=(0, 8), pady=(0, 8))
        self.left_top.rowconfigure(1, weight=1)
        self.left_top.columnconfigure(0, weight=1)

        self.scene_label = tk.Label(self.left_top, bg=PANEL)
        self.scene_label.grid(row=0, column=0, sticky='nsew', padx=8, pady=8)
        self.load_scene()

        self.transcript = tk.Frame(self.left_top, bg=PANEL2)
        self.transcript.grid(row=1, column=0, sticky='ew', padx=8, pady=(0, 8))
        self.speaker = tk.Label(self.transcript, text='', bg=PANEL2, fg=ACCENT, font=('Courier', 16, 'bold'))
        self.speaker.pack(anchor='w', padx=10, pady=(8, 0))
        self.bark = tk.Label(self.transcript, text='', bg=PANEL2, fg=TEXT, font=('Courier', 18, 'bold'), wraplength=780, justify='left')
        self.bark.pack(anchor='w', padx=10)
        self.caption = tk.Label(self.transcript, text='', bg=PANEL2, fg=MUTED, font=('Courier', 12), wraplength=780, justify='left')
        self.caption.pack(anchor='w', padx=10, pady=(0, 8))

        # Left bottom: hand and log
        self.left_bottom = self.panel(self.main)
        self.left_bottom.grid(row=1, column=0, sticky='nsew', padx=(0, 8))
        self.left_bottom.columnconfigure(0, weight=1)
        self.left_bottom.rowconfigure(1, weight=1)

        self.hand_title = tk.Label(self.left_bottom, text='YOUR HAND // BUILD PATTERNS, BREAK CREDIBILITY', bg=PANEL, fg=ACCENT, font=('Courier', 16, 'bold'))
        self.hand_title.grid(row=0, column=0, sticky='w', padx=8, pady=(8, 4))
        self.hand_frame = tk.Frame(self.left_bottom, bg=PANEL)
        self.hand_frame.grid(row=1, column=0, sticky='nsew', padx=8)
        self.log_box = tk.Label(self.left_bottom, text='', bg=PANEL2, fg=MUTED, font=('Courier', 11), justify='left', anchor='nw')
        self.log_box.grid(row=2, column=0, sticky='ew', padx=8, pady=8)

        # Right column HUD
        self.right = tk.Frame(self.main, bg=BG)
        self.right.grid(row=0, column=1, rowspan=2, sticky='nsew')
        self.right.columnconfigure(0, weight=1)

        self.overlay = self.panel(self.right)
        self.overlay.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        tk.Label(self.overlay, text='ENCOUNTER START // THE SHOWBOAT', bg=PANEL, fg=ACCENT, font=('Courier', 18, 'bold')).pack(anchor='w', padx=10, pady=(10, 4))
        tk.Label(self.overlay, text='WIN CONDITION: Reduce opposing counsel\'s CREDIBILITY to 0 before yours hits 0.', bg=PANEL, fg=TEXT, font=('Courier', 12), wraplength=500, justify='left').pack(anchor='w', padx=10)
        tk.Label(self.overlay, text='FIRST PATTERN: Wait for TESTIMONY LIVE → play PRIOR STATEMENT → then IMPEACH.', bg=PANEL, fg=INFO, font=('Courier', 12, 'bold'), wraplength=500, justify='left').pack(anchor='w', padx=10, pady=(4, 4))
        self.start_btn = tk.Button(self.overlay, text='BEGIN CROSS', command=self.begin_cross, bg=ACCENT, fg=BG, font=('Courier', 16, 'bold'), relief='flat')
        self.start_btn.pack(anchor='w', padx=10, pady=(4, 10))

        self.player_panel = self.panel(self.right)
        self.player_panel.grid(row=1, column=0, sticky='ew', pady=(0, 8))
        self.enemy_panel = self.panel(self.right)
        self.enemy_panel.grid(row=2, column=0, sticky='ew', pady=(0, 8))
        self.state_panel = self.panel(self.right)
        self.state_panel.grid(row=3, column=0, sticky='ew', pady=(0, 8))
        self.hint_panel = self.panel(self.right)
        self.hint_panel.grid(row=4, column=0, sticky='ew', pady=(0, 8))
        self.controls = self.panel(self.right)
        self.controls.grid(row=5, column=0, sticky='ew')

        self.player_stats = tk.Label(self.player_panel, bg=PANEL, fg=TEXT, justify='left', font=('Courier', 14, 'bold'))
        self.player_stats.pack(anchor='w', padx=10, pady=10)
        self.enemy_stats = tk.Label(self.enemy_panel, bg=PANEL, fg=TEXT, justify='left', font=('Courier', 14, 'bold'))
        self.enemy_stats.pack(anchor='w', padx=10, pady=10)
        self.state_stats = tk.Label(self.state_panel, bg=PANEL, fg=TEXT, justify='left', font=('Courier', 13, 'bold'))
        self.state_stats.pack(anchor='w', padx=10, pady=10)
        self.hint_text = tk.Label(self.hint_panel, bg=PANEL, fg=MUTED, justify='left', font=('Courier', 12), wraplength=500)
        self.hint_text.pack(anchor='w', padx=10, pady=10)

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
        self.enemy_stats.config(text=(
            f'OPPOSING COUNSEL // {g.enemy_name}\n'
            f'CREDIBILITY: {g.enemy_cred}\n'
            f'SHIELD: {g.enemy_shield}\n'
            f'INTENT: {g.enemy_intent.name}'
        ))
        self.state_stats.config(text=(
            'COMBAT STATE\n'
            f'TESTIMONY: {"LIVE" if g.testimony_live else "OFF"}\n'
            f'EXPOSED: {"YES" if g.exposed else "NO"}\n'
            f'SYMPATHY: {g.enemy_sympathy}\n'
            f'RECORD: {g.record}\n'
            f'JUDGE PATIENCE: {g.judge_patience}\n'
            f'DECK: {len(g.deck)}  DISCARD: {len(g.discard)}'
        ))
        hint = 'WHAT MATTERS NOW\n'
        if not g.started:
            hint += 'Hit BEGIN CROSS. Your first job is to watch for TESTIMONY LIVE.'
        elif g.testimony_live and not g.exposed:
            hint += 'TESTIMONY is live. PRIOR STATEMENT can create EXPOSED.'
        elif g.exposed:
            hint += 'The story is cracked. IMPEACH is your best cash-out right now.'
        elif g.foundation_active:
            hint += 'FOUNDATION is set. ADMIT EXHIBIT will build extra RECORD.'
        else:
            hint += 'Protect your credibility, watch enemy intent, and build toward your next pattern.'
        self.hint_text.config(text=hint)

        self.log_box.config(text='COURT LOG\n' + '\n'.join(g.log[-8:]))

        for w in self.hand_frame.winfo_children():
            w.destroy()
        for i, card in enumerate(g.hand):
            status, color = self.card_status(card)
            fr = tk.Frame(self.hand_frame, bg=CARD_BG, highlightbackground=color, highlightthickness=3)
            fr.grid(row=0, column=i, padx=5, pady=5, sticky='n')
            tk.Label(fr, text=f'{card.name} [{card.cost}]', bg=CARD_BG, fg=ACCENT, font=('Courier', 12, 'bold'), wraplength=150, justify='left').pack(anchor='w', padx=6, pady=(6, 0))
            tk.Label(fr, text=' / '.join(card.tags), bg=CARD_BG, fg=INFO, font=('Courier', 10, 'bold'), wraplength=150, justify='left').pack(anchor='w', padx=6)
            tk.Label(fr, text=card.text, bg=CARD_BG, fg=TEXT, font=('Courier', 10), wraplength=150, justify='left').pack(anchor='w', padx=6, pady=4)
            tk.Label(fr, text=status, bg=CARD_BG, fg=color, font=('Courier', 10, 'bold')).pack(anchor='w', padx=6)
            state = 'normal' if g.started and card.cost <= g.focus and g.enemy_cred > 0 and g.player_cred > 0 else 'disabled'
            tk.Button(fr, text='PLAY', state=state, command=lambda idx=i: self.play(idx), bg=ACCENT, fg=BG, relief='flat', font=('Courier', 11, 'bold')).pack(fill='x', padx=6, pady=(4, 6))

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
