# law-in-action.tape — the civil code in ~14 seconds: a conformance
# fixture declares its intent in the header, the lethal-trifecta law
# refuses the ungated flow, and the human-gated twin passes. Every
# verdict is the released engine's own; scripts/media/render.sh stages
# the corpus copy. House theme = the engine's nika-hero palette.
Output law-in-action.gif

Set Shell zsh
Set FontFamily "JetBrains Mono"
Set FontSize 21
Set Width 1420
Set Height 780
Set Padding 24
Set Margin 22
Set MarginFill "#4f86ff"
Set BorderRadius 14
Set WindowBar Colorful
Set WindowBarSize 42
Set Theme { "name": "nika", "background": "#08090b", "foreground": "#dbe3ee", "cursor": "#4f86ff", "black": "#10131a", "red": "#ff6b6b", "green": "#34d399", "yellow": "#f0b45b", "blue": "#4f86ff", "magenta": "#b07bff", "cyan": "#22d3ee", "white": "#dbe3ee", "brightBlack": "#5b6472", "brightRed": "#ff8f8f", "brightGreen": "#5ee6b0", "brightYellow": "#ffd08a", "brightBlue": "#8db4ff", "brightMagenta": "#c9a2ff", "brightCyan": "#67e3f5", "brightWhite": "#ffffff" }
Set TypingSpeed 30ms
Set PlaybackSpeed 1.0

Hide
Type "cd /tmp/spec-demo && export TMPDIR=/tmp && unset -m '*API_KEY*' '*_TOKEN*' '*SECRET*' 2>/dev/null; setopt interactive_comments && clear"
Enter
Show

Type "# every law is machine-checkable · a fixture declares its intent up front"
Enter
Sleep 700ms
Type "head -3 envelope/trifecta-realized-flow-ungated.nika.yaml"
Enter
Sleep 2000ms

Type "# the exam: the lethal trifecta, ungated — the engine must REFUSE"
Enter
Sleep 700ms
Type "nika check envelope/trifecta-realized-flow-ungated.nika.yaml"
Enter
Sleep 4200ms

Type "clear"
Enter
Type "# the twin: same three permits, a blocking human gate dominates — must PASS"
Enter
Sleep 700ms
Type "nika check envelope/trifecta-human-gate-dominates.nika.yaml"
Enter
Sleep 4200ms
Sleep 1400ms
