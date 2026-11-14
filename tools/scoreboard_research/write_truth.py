"""Write truth.json for each web test image. Hero ids follow data/heroes.json.
Role = the role icon shown in that scoreboard row (what the game says the slot is)."""
import json, os
from PIL import Image
B = r'D:\counterwatch\testdata\web'
R = {'T': 'tank', 'D': 'damage', 'S': 'support'}

def team(s):
    out = []
    for tok in s.split():
        h, r = tok.split(':')
        e = {'hero': h, 'role': R[r] if r in R else None}
        if h == 'empty':
            e = {'hero': 'empty', 'role': None}
        out.append(e)
    return out

STD = 'Standard 5v5 role-queue Tab scoreboard (2026 layout). Rows top-to-bottom: tank, damage, damage, support, support for each team.'
T = {
 1: ('orisa:T ana:S hazard:T widowmaker:D moira:S', 'ana:S sigma:T dva:T ashe:D moira:S',
     'July 2025 build, mode "Push - Random Heroes" (Arcade): rows are NOT in role order and a team can have 2 tanks. Green role strip = players in your group. Older layout: row pitch ~62 px, ally top ~200, enemy top ~592.'),
 2: ('dva:T widowmaker:D symmetra:D zenyatta:S mercy:S', 'zarya:T ashe:D bastion:D mercy:S moira:S',
     'August 2025 build, end of match (VICTORY behind board). Older layout without perk icons: row pitch ~62 px, ally rows y 206-514, enemy y 599-907, portraits x 312-372. Green strip on rows 4-5 = group members.'),
 3: ('mauga:T junkrat:D sierra:D moira:S kiriko:S', 'zarya:T sierra:D torbjorn:D lifeweaver:S kiriko:S', STD + ' Whole ally role strip green = full group (5-stack).'),
 4: ('winston:T bastion:D pharah:D mercy:S kiriko:S', 'reinhardt:T genji:D sojourn:D moira:S mizuki:S', STD + ' Custom team colours: ally pink, enemy yellow (colour-blind/team colour options).'),
 5: ('junkerqueen:T soldier76:D sierra:D moira:S mercy:S', 'mauga:T mei:D cassidy:D kiriko:S moira:S', STD + ' 1440x900 (16:10) source; custom colours ally pink, enemy gold. UI scales with width, board sits at the same place once scaled to 1920 wide and centre-cropped to 1080.'),
 6: ('ramattra:T mei:D anran:D moira:S mizuki:S', 'sigma:T soldier76:D sierra:D juno:S lifeweaver:S', STD),
 7: ('reinhardt:T bastion:D reaper:D wuyang:S moira:S', 'ramattra:T torbjorn:D pharah:D mercy:S kiriko:S', STD + ' 2434x1369 source.'),
 8: ('ramattra:T cassidy:D shion:D mercy:S mizuki:S', 'wreckingball:T shion:D bastion:D moira:S kiriko:S',
     STD + ' Interact mode (button reads CLOSE): board shifts left (left edge x=230) and gains chat/mute/report button columns. Competitive hero bans shown as 4 red-framed portraits top-left. Same hero (shion) can appear on both teams.'),
 9: ('sigma:T sojourn:D soldier76:D ana:S kiriko:S', 'dmon:T bastion:D venture:D kiriko:S ana:S', STD),
 10: ('winston:T ashe:D cassidy:D mercy:S moira:S', 'doomfist:T vendetta:D genji:D mercy:S jetpackcat:S', STD + ' Enemy colour customised to pink.'),
 11: ('doomfist:T soldier76:D cassidy:D mercy:S illari:S', 'roadhog:T hanzo:D reaper:D brigitte:S moira:S', STD + ' 2434x1369 source; ally strip green = group.'),
 12: ('roadhog:T ashe:D shion:D mercy:S kiriko:S', 'roadhog:T junkrat:D ashe:D moira:S mercy:S', STD + ' 2560x1440 source.'),
 13: ('orisa:T echo:D unknown:D mercy:S doctrine:S', 'dva:T sombra:D tracer:D moira:S doctrine:S',
     'Tabbed variant ("HERO INFO | SCOREBOARD" tabs top-left), 2560x1440, 13 Sep 2026. Ally rows show ultimate-charge % rings instead of perks. Rows 3 and 4 are dead: portrait greyed with a red respawn-timer ring ("4") drawn over it. Row 3 hero not identifiable under the timer. Row 4 is the local player (highlighted) and the hero panel says MERCY. Sombra still in the damage role (before the 2026-10-06 move to support). Burning (fire) icons left of some enemy rows.'),
 14: ('junkerqueen:T anran:D reaper:D moira:S mercy:S', 'domina:T soldier76:D sojourn:D moira:S mercy:S', STD),
 15: ('dva:T torbjorn:D mei:D moira:S juno:S', 'orisa:T genji:D sierra:D kiriko:S ana:S', STD + ' 3440x1440 ultrawide source: the UI stays in a centred 16:9 area (scale by height, crop the middle 1920).'),
 16: ('hazard:T vendetta:D hanzo:D moira:S juno:S', 'dmon:T shion:D genji:D ana:S kiriko:S', STD + ' Local player is row 4 (highlighted).'),
 17: ('hazard:T bastion:D hanzo:D ana:S baptiste:S', 'tracer:D empty:- empty:- empty:- empty:-',
     'Tabbed variant (Portuguese UI). Four enemy players have left: their rows read "AGUARDANDO JOGADOR" (waiting for player) with a three-dot placeholder instead of a portrait, and the one remaining enemy (Tracer, damage icon) is moved to the TOP enemy row, so enemy rows are not always tank-first. Ally rows show ult-charge % rings. Competitive bans (5 portraits) top-left.'),
 18: ('domina:T sierra:D cassidy:D mercy:S jetpackcat:S', 'reinhardt:T sojourn:D sierra:D mercy:S ana:S', STD + ' 2560x1440. Rows 2 and 4 green strip = group members.'),
 19: ('reinhardt:T anran:D mei:D moira:S baptiste:S', 'domina:T cassidy:D bastion:D kiriko:S moira:S', STD + ' 3269x1401 ultrawide, blurry upload.'),
 20: ('doomfist:T anran:D tracer:D wuyang:S doctrine:S', 'orisa:T echo:D junkrat:D doctrine:S sombra:S', STD + ' Sombra shown with the support icon (after the 2026-10-06 role change).'),
 21: ('winston:T soldier76:D hanzo:D zenyatta:S mercy:S', 'mauga:T bastion:D reaper:D mercy:S moira:S', STD + ' 2560x1440; full ally group (green strip).'),
 22: ('', '', 'NEGATIVE CASE. 1600x900, STADIUM round 1 (TEAM BUILDS tab and round score header visible), Control Samoa. Scoreboard bug: header (E A D DMG H MIT), VS and hero panel (Wuyang) are drawn but no player rows at all. Uploader titled it "They got rid of the scoreboard". The 2026-11-05 patch notes list a fix for "the Scoreboard and related screens would not display properly". Reader should return no heroes / low confidence, not guess.'),
 23: ('zarya:T reaper:D tracer:D zenyatta:S unknown:S', 'dva:T sojourn:D sierra:D moira:S mercy:S',
     'Tabbed variant (Spanish UI, HERO INFO | SCOREBOARD tabs, competitive bans top-left). Ally rows show ult-charge % rings plus one perk slot. Ally rows 1 and 5 are dead: dark portrait with red respawn ring "8". Row 1 is zarya: pink hair visible around the ring, and the chat line "[MAT2014 (ZARYA)]" names that row player. Row 5 not identifiable. Chat also confirms enemy D.Va (KORPSEBUNNY) and Moira (HINITE). Escort map (Dorado, competitive, Spanish UI).'),
 24: ('domina:T sierra:D pharah:D wuyang:S juno:S', 'orisa:T sierra:D cassidy:D lifeweaver:S ana:S', STD + ' 3840x2160 (4K) source.'),
 25: ('winston:T shion:D hanzo:D juno:S jetpackcat:S', 'unknown:T unknown:D unknown:D unknown:S unknown:S',
     '2560x1494 (windowed). Tabbed variant, mid-match (TIME 2:59, enemy stats non-zero) yet ALL enemy portraits are grey "?" silhouettes. Same uploader as #26 and #32; cause not confirmed (not explained in patch notes found). Role icons still shown, so enemy roles are known but heroes are not.'),
 26: ('sigma:T ashe:D genji:D unknown:S lifeweaver:S', 'unknown:T unknown:D unknown:D unknown:S unknown:S',
     'Tabbed variant, TIME 0:00 (setup). Local player (row 4) has not picked: "?" silhouette. All enemy portraits "?". No hero panel, so the board is centred alone (left edge x~551 in 1080p space). All stats 0.'),
 27: ('reinhardt:T tracer:D mei:D ana:S juno:S', 'wreckingball:T genji:D junkrat:D sombra:S ana:S', STD + ' Ally colour customised to yellow. Sombra with support icon.'),
 28: ('roadhog:T vendetta:D anran:D juno:S jetpackcat:S', 'hazard:T reaper:D cassidy:D ana:S mercy:S', STD + ' 2560x1494 (windowed).'),
 29: ('doomfist:T tracer:D vendetta:D moira:S lifeweaver:S', 'hazard:T anran:D junkrat:D doctrine:S kiriko:S', STD + ' Italian UI. Custom colours: ally cyan, enemy orange. Local player row 4 (Moira).'),
 30: ('zarya:T freja:D ashe:D mercy:S mizuki:S', 'dva:T genji:D sojourn:D kiriko:S juno:S', STD + ' Italian UI, ally cyan / enemy orange.'),
 31: ('doomfist:T hanzo:D soldier76:D zenyatta:S lifeweaver:S', 'doomfist:T genji:D vendetta:D ana:S illari:S', STD + ' Italian UI, ally cyan / enemy orange. Mirror tank (doomfist on both teams).'),
 32: ('wreckingball:T pharah:D shion:D juno:S zenyatta:S', 'unknown:T unknown:D unknown:D unknown:S unknown:S', STD + ' 2560x1494. Tabbed variant, mid-match (TIME 4:52, enemy stats non-zero) yet all enemy portraits are "?" silhouettes; cause not confirmed. Chat line shows an ally swap: "SleepyBear switched to Shion (was Genji)" and row 3 already shows Shion.'),
 33: ('domina:T sojourn:D cassidy:D juno:S kiriko:S', 'winston:T soldier76:D anran:D ana:S doctrine:S', STD + ' 2560x1494.'),
 34: ('reaper:D genji:D dva:T kiriko:S moira:S', 'lucio:S empty:- empty:- empty:- empty:-',
     'STADIUM (Payload Race), Nov 2026. Tabs "TEAM BUILDS | SCOREBOARD | ENEMY BUILDS"; round score boxes at top centre (0 - ROUND 3 - 3); extra columns (cash, BTY = bounty). Bigger rows: pitch ~71.5 px, ally rows y 211-569, enemy y 654-1012, portraits ~70 px at x 170-240, board left edge x=140. Rows NOT in role order. Four enemies left ("WAITING FOR PLAYER"), remaining enemy moved to top row. Interact mode (CLOSE, report buttons).'),
 35: ('reinhardt:T genji:D tracer:D moira:S kiriko:S', 'dva:T reaper:D ashe:D moira:S empty:-',
     'STADIUM, 2025 build. "TOTAL STATS" view, cash and BTY columns, Stadium rank badges (roman numerals) beside names. Ally rows y 216-524, enemy y 609-917 (pitch ~62), board left edge x=182. Enemy custom colour magenta. One enemy left: bottom row "WAITING FOR PLAYER".'),
}
for n, (a, e, notes) in T.items():
    d = os.path.join(B, str(n))
    w, h = Image.open(os.path.join(d, 'image.png')).size
    doc = {'width': w, 'height': h, 'my_team': team(a) if a else [], 'enemy_team': team(e) if e else [], 'notes': notes}
    with open(os.path.join(d, 'truth.json'), 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=1)
print('ok', len(T))
