import tkinter as tk

orig = tk.Tk.mainloop
def fake_mainloop(self, *a, **kw):
    def run():
        try:
            app.begin_cross()
            app.refresh()
            print('begin_cross: OK')
            # play every affordable card
            for _ in range(10):
                if not app.game.hand:
                    break
                card = app.game.hand[0]
                if card.cost <= app.game.focus:
                    app.game.play_card(0)
                    app.refresh()
                    print(f'played {card.id}: OK')
                else:
                    break
            app.end_turn()
            app.refresh()
            print('end_turn: OK')
            if app.game.judge_patience >= 3:
                app.reroll_next()
                app.refresh()
                print('reroll: OK')
            print('ALL OK')
        except Exception as e:
            import traceback
            traceback.print_exc()
        finally:
            self.destroy()
    self.after(300, run)
    orig(self, *a, **kw)
tk.Tk.mainloop = fake_mainloop

exec(open('trial_roguelike_prototype (11).py', encoding='utf-8').read())
