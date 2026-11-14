"""Synergies, archetypes, swap rules and 2025-2026 patch flags for build_counters.py."""

# Partner heroes whose kits combine. Comment = where it comes from.
SYN = {
    'domina': ['sojourn', 'ashe', 'baptiste', 'emre', 'freja'],           # Mobalytics Domina guide (+Emre/Freja guides)
    'emre': ['domina', 'sigma'],                                          # Mobalytics Emre guide
    'freja': ['sigma', 'domina', 'mercy'],                                # Mobalytics Freja guide
    'vendetta': ['zarya', 'ana', 'zenyatta'],                             # Mobalytics: Projected Barrier, Biotic Rifle, Orb of Harmony
    'anran': ['zarya', 'dva', 'soldier76', 'cassidy', 'juno'],            # Mobalytics Anran + Juno guides
    'juno': ['reinhardt', 'reaper', 'dva', 'anran'],                      # Mobalytics Juno guide (Hyper Ring)
    'mizuki': ['junkerqueen', 'ana'],                                     # Mobalytics Mizuki guide
    'doctrine': ['reinhardt', 'junkerqueen', 'reaper'],                   # Mobalytics: brawl/rush comps inside drone range
    'jetpackcat': ['dva', 'echo', 'tracer', 'soldier76'],                 # Mobalytics: flying/fast allies, Tactical Visor on Lifeline
    'sierra': ['sigma'],                                                  # Mobalytics Sierra guide
    'roadhog': ['zenyatta', 'kiriko'],                                    # Mobalytics: Discord on hook targets, Suzu vs anti-heal
    'wuyang': ['winston', 'dva', 'sigma'],                                # Mobalytics: stream on the diving ally, or poke
    'shion': ['winston', 'dva', 'reinhardt'],                             # Mobalytics: allies who draw attention (hero picks ours)
    'reinhardt': ['lucio', 'zarya', 'kiriko', 'brigitte', 'juno'],        # brawl; Juno per Mobalytics
    'junkerqueen': ['lucio', 'mizuki', 'kiriko', 'brigitte'],             # brawl/rush; Mizuki per Mobalytics
    'winston': ['tracer', 'genji', 'dva', 'lucio', 'kiriko'],             # dive
    'dva': ['winston', 'genji', 'tracer', 'anran', 'kiriko'],             # dive; Anran per Mobalytics
    'wreckingball': ['tracer', 'sombra', 'echo', 'lucio'],                # dive/disruption
    'doomfist': ['tracer', 'genji', 'lucio', 'kiriko'],                   # dive
    'zarya': ['reinhardt', 'genji', 'anran', 'vendetta'],                 # bubbles enable divers (Mobalytics Anran/Vendetta)
    'sigma': ['ashe', 'sojourn', 'baptiste', 'emre', 'freja', 'sierra'],  # poke (Mobalytics Emre/Freja/Sierra)
    'orisa': ['baptiste', 'kiriko', 'ashe', 'sojourn'],
    'ramattra': ['lucio', 'brigitte', 'kiriko'],
    'mauga': ['kiriko', 'lucio', 'reaper'],
    'hazard': ['tracer', 'genji', 'lucio'],
    'dmon': ['lucio', 'kiriko', 'brigitte'],
    'genji': ['ana', 'zarya', 'winston', 'kiriko'],                       # Nano Blade
    'tracer': ['winston', 'dva', 'jetpackcat', 'kiriko'],
    'pharah': ['mercy', 'juno'],                                          # Mercy pocket
    'echo': ['mercy', 'jetpackcat', 'winston'],
    'ashe': ['sigma', 'domina', 'baptiste', 'mercy'],
    'sojourn': ['domina', 'sigma', 'mercy'],
    'widowmaker': ['sigma', 'mercy', 'lucio'],
    'cassidy': ['orisa', 'baptiste', 'anran'],
    'hanzo': ['sigma', 'zenyatta'],
    'soldier76': ['jetpackcat', 'mercy', 'orisa'],
    'reaper': ['juno', 'lucio', 'reinhardt', 'mauga'],
    'bastion': ['orisa', 'mercy', 'baptiste'],
    'torbjorn': ['reinhardt', 'brigitte'],
    'symmetra': ['reinhardt', 'lucio'],
    'junkrat': ['sigma', 'orisa', 'mercy'],
    'mei': ['reinhardt', 'junkerqueen', 'lucio'],
    'venture': ['reinhardt', 'juno', 'lucio'],
    'ana': ['genji', 'reinhardt', 'junkerqueen', 'mizuki'],
    'baptiste': ['domina', 'sigma', 'orisa', 'ashe'],
    'brigitte': ['reinhardt', 'junkerqueen', 'lucio'],
    'illari': ['sigma', 'ashe', 'sojourn'],
    'kiriko': ['winston', 'genji', 'reinhardt', 'roadhog'],
    'lifeweaver': ['sigma', 'ashe', 'domina'],
    'lucio': ['reinhardt', 'junkerqueen', 'winston', 'mauga'],
    'mercy': ['pharah', 'echo', 'freja', 'ashe', 'sojourn'],
    'moira': ['reaper', 'junkerqueen', 'mauga'],
    'sombra': ['wreckingball', 'tracer', 'winston'],                      # EMP / Cyberspace Weaken into dive
    'zenyatta': ['roadhog', 'genji', 'reinhardt'],                        # Discord on targets
}

ARCH = {
    'dive': ['winston', 'dva', 'doomfist', 'wreckingball', 'hazard', 'genji', 'tracer', 'anran', 'shion', 'vendetta', 'venture',
             'sierra', 'echo', 'sombra', 'jetpackcat', 'kiriko', 'lucio', 'juno', 'wuyang', 'mercy'],
    'brawl': ['reinhardt', 'junkerqueen', 'dmon', 'mauga', 'ramattra', 'zarya', 'roadhog', 'hazard', 'reaper', 'mei', 'symmetra',
              'torbjorn', 'venture', 'vendetta', 'brigitte', 'lucio', 'moira', 'doctrine', 'mizuki', 'kiriko', 'ana'],
    'poke': ['domina', 'sigma', 'orisa', 'ramattra', 'ashe', 'sojourn', 'widowmaker', 'hanzo', 'cassidy', 'soldier76', 'emre', 'freja',
             'junkrat', 'pharah', 'bastion', 'sierra', 'baptiste', 'zenyatta', 'illari', 'ana', 'lifeweaver', 'wuyang', 'mercy'],
}

SWAP_RULES = [
    {'rule': 'Default is to stay. Same-role swaps after a death win about 2.5 points fewer of the next fights than staying (score held equal); only 3.1% of swap matchups beat staying.', 'src': 'cw_swap_death'},
    {'rule': 'Swap when the swap answers the hero that is killing you: tank to Winston after a Widowmaker kill costs only -1.8 points vs -3.9 for an unrelated tank swap; DPS to Soldier: 76 after a Pharah kill costs -0.5 vs -3.9.', 'src': 'cw_swap_death'},
    {'rule': "Comfort beats paper counters: swapping to a hero with under 30 min played in 90 days costs -5.1 points, 5+ hours costs -1.8. Only suggest heroes in the player's pool.", 'src': 'cw_swap_death'},
    {'rule': 'A real counter edge is 52-53% (prefer it if equally comfortable), 53-55% is worth swapping even if less practised, above 55% is a rare hard counter. Counters are modest; do not overstate them.', 'src': 'cw_counterpick'},
    {'rule': 'Lock counters only after the enemy comp is visible; an early counter gives the enemy a free re-pick.', 'src': 'cw_counterpick'},
    {'rule': 'Check what the team loses: a tank swap changes what supports can protect; a DPS swap changes ult economy. Only swap if the team can absorb it.', 'src': 'cw_counterpick'},
    {'rule': 'Counter-swapping matters most on tank (one tank per team in 5v5), so tank pools should be wider. Coaches converge on a primary plus a same-role secondary for counter-swaps and bans.', 'src': 'cw_onetrick'},
    {'rule': 'If the enemy comp holds two hard counters to your hero, switch to your backup; a hero under 50% at your rank is a reason to lean on the secondary.', 'src': 'cw_onetrick'},
    {'rule': 'Ult charge: a swap keeps at most 25% ultimate charge. Do not swap with ult nearly ready; spend it first.', 'src': 'shack_s3'},
    {'rule': 'Do not swap in a way that breaks the comp (no frontline, no healing), and do not swap mid-fight; swap while dead or in spawn.', 'src': 'dignitas_switch'},
    {'rule': 'Tanks who swap every death hurt their team more than any counter helps; one swap per clear, repeated problem.', 'src': 'esgg_tank_swap'},
    {'rule': 'Swap after the same threat stops your team two fights in a row (free sniper, unpressured Pharah, a flanker), not after one death.', 'url': 'https://jeu.video/en/guide/overwatch-2-counters-objective'},
    {'rule': 'Map and mode matter: an edge can vanish on another map or mode (Symmetra 49.2% on Push vs 59.4% on Flashpoint). Domina wants chokes and long halls (Havana, Junkertown) and struggles on high-ground maps (Gibraltar, Numbani).', 'src': 'cw_s5_meta'},
    {'rule': 'Rank matters: below Diamond mechanics dominate and 1-2 heroes total is fine; matchups shift by rank, so weight counters less in low ranks.', 'src': 'cw_counterpick'},
    {'rule': '[2026-02] Sub-role passives change swap value: Stalwart tanks have 40% knockback and slow resistance (weakens boop and slow counters), Bruisers take 25% less crit damage, Initiators heal 75 while airborne; Tactician supports keep up to 25% excess ult charge after ulting.', 'src': 'bz_pn_2026_02'},
]

PATCH = {
    'sombra': '[2026-10-06] Reworked into a Support (Tactician). Hack and Virus removed; Hotfix heals and hacks health packs/deployables; Cyberspace zone applies Weaken (cut target damage and healing by 50%, 40% after 2026-11-03). Only EMP hacks now, so "Sombra hack cancels Ball/abilities" counters need EMP.',
    'roadhog': '[2026-10-06] Reworked: two-burst Scrap Gun, Trash Compactor absorbs projectiles and fires them back, Hook stun 0.3 s and pull to 4.5 m, Breather retuned (2026-10-13). Less one-shot hook combo, more frontline mitigation.',
    'doctrine': '[2026-10-06] New support (hero 54), Season 5. Nerfed 2026-10-13 and 2026-11-03 (Scepter output, Infuse and Shrouded Momentum cooldowns).',
    'dmon': '[2026] New tank. 2026-10-13 armour 275->250; 2026-11-03 Power Barrier slower to deploy, Propulsors no impact damage, Overstrike lifesteal 150->125%.',
    'junkerqueen': '[2026-11-03] Health 375->425, Carnage cooldown 9->7 s.',
    'mauga': '[2026-11-03] Armour 125->150, Chaingun burn 15->20.',
    'ramattra': '[2026-11-03] Void Accelerator ammo 100->125.',
    'winston': '[2026-02] Barrier Toss perk removed. [2026-11-03] Revitalizing Barrier perk 35->30 hps.',
    'wreckingball': '[2026-11-05] Faster Grappling Claw retract speed limit.',
    'dva': '[2026-02] Health 375->325 (5v5). [2026-10-06] Micro Missiles fire rate 11->14.',
    'domina': '[2026] New tank (Season 1). [2026-10-06] Crystal Charge cd 8->7 s, Reconstruction lifesteal 75->100%.',
    'anran': '[2026] New damage (Season 1). [2026-02] Dancing Blaze cleanse removed. [2026-11-03] Inferno Rush knockback removed, fans 22->24.',
    'genji': '[2026-10-06] Swift Strike 50->60, Dragonblade 110->100. [2026-11-03] Deflect 2->1.5 s.',
    'vendetta': '[2026-02] Health 150->175, armour 125->100. [2026-11-03] Slower combo and leap.',
    'shion': '[2026] New damage (Season 3). [2026-11-03] Execution spread tightened, ult faster.',
    'sierra': '[2026] New damage (Season 2).',
    'emre': '[2026] New damage (Season 1). [2026-11-03] Cyber Frag detonates faster.',
    'reaper': '[2026-02] Shadow Step no longer cleanses. [2026-11-03] Health 275->300.',
    'ana': '[2026-11-03] Biotic Grenade damage 90->60 (anti-heal kept). [2026-10-06] Local Anesthetic perk.',
    'brigitte': '[2026-11-03] Inspire cooldown 1.25->1 s, instant heal 12->15.',
    'illari': '[2026-02] Solar Flare perk change. [2026-11-03] Faster charge, stronger Pylon.',
    'jetpackcat': '[2026] New support (Season 1). [2026-10-06] Cassidy Deadeye can no longer ride Lifeline. [2026-11-03] Health 225->200.',
    'mizuki': '[2026] New support (Season 1).',
    'kiriko': '[2026-10-13] Health 225->250.',
    'lucio': '[2026-10-06] Sound Barrier 5->6 s.',
    'cassidy': "[2026-02] Gun Slingin' perk removed. [2026-10-06] Deadeye cannot attach to Jetpack Cat Lifeline.",
    'tracer': '[2026-02] Flashback perk removed; Blink Packs moved to a major perk.',
    'widowmaker': '[2026-02] Escape Plan perk removed. [2026-10-06] Hitscan projectile sizes reduced globally.',
    'hanzo': "[2026-11-03] Sonic Disruption can no longer override Sombra's hacked health packs.",
    'zarya': '[2026-02] Energy Lance no longer needs 50+ energy.',
    'echo': '[2026-11-03] Aerial Munitions refills ammo.',
    'pharah': '[2026-02] Sky Spy perk removed.',
    'ashe': '[2026-02] Sidewinder perk removed.',
    'lifeweaver': '[2026-02] Several perks removed; Tree of Life converts overhealing at 100%.',
    'bastion': '[2026-10-06] Reconfigure duration 6->5 s.',
}
