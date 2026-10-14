# UNO - Human vs. AI

Two versions of the same game. Both follow the same rules and AI strategy.

## Files
| File | Purpose |
|------|---------|
| `main_tk.py` | Desktop game using tkinter - NOTHING to install (use this if pip is blocked) |
| `main.py` | Desktop game (Python + Pygame), single file, no image assets |
| `requirements.txt` | Python dependency (`pygame`) |
| `index.html` | Browser version (HTML + CSS + JS), single file, no install needed |

## Run the no-install version (PyCharm or terminal)
Right-click `main_tk.py` > *Run*, or `python main_tk.py`. tkinter is built into Python.

## Run the Pygame version (PyCharm)
1. Open the folder in PyCharm (Python 3.8+).
2. Install the dependency: `pip install -r requirements.txt`
   (or PyCharm: *File > Settings > Project > Python Interpreter > +  > pygame*).
3. Right-click `main.py` > *Run 'main'*.

## Run the browser version
Double-click `index.html` - it opens in any modern browser.

## Rules
- Play a card matching the top card's colour or value, or any Wild.
- Skip, Reverse (acts as Skip in 2-player), +2 and Wild +4 make the opponent miss a turn.
- No playable card? Click the draw pile. If the drawn card is playable you may play it or Pass.
- Empty your hand to win. Press R after a game to restart; Esc quits (Pygame version).
