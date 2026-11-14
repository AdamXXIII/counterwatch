import json, sys, os
D = sys.argv[1]
cards = json.load(open(os.path.join(D, 'cards.json'), encoding='utf8'))
ab = json.load(open(os.path.join(D, 'abilities.json'), encoding='utf8'))

KIT = {
 'doctrine': 'Mid-range hybrid heal/damage scepter; Infuse empowers next ability (piercing blast, self-drones, free-flight on Shrouded Momentum dash with damage reduction); ult cuts enemy max health and gives allies overhealth.',
 'ana': 'Long-range hitscan healer, no mobility; Sleep Dart (hard CC) and Biotic Grenade (anti-heal); Nano Boost.',
 'anran': 'Fire-projectile flanker with burn DoT; Inferno Rush gap-close, Dancing Blaze dodges all damage and self-heals; ult charge-explode; passive self-revive on death. High mobility close/mid range.',
 'ashe': 'Long-range hitscan sharpshooter; Coach Gun self-knockback escape; Dynamite burn; B.O.B. ult knock-up.',
 'baptiste': 'Mid-range burst hitscan + healing grenades; Regenerative Burst self/AoE heal; Immortality Field prevents deaths; Exo Boots high jump; Amp Matrix ult.',
 'bastion': 'Specialist with huge sustained DPS in Assault form (slow, no mobility); Recon form accurate; bouncing grenade; immobile Artillery ult.',
 'brigitte': 'Short-range melee support; Whip Shot knockback, Barrier Shield + Shield Bash, Repair Pack, Inspire AoE heal; Rally ult armor.',
 'cassidy': 'Mid-range hitscan revolver, Combat Roll with damage reduction; Deadeye ult.',
 'dmon': 'Stalwart mech tank with melee Plasma Saber and Portable Fusion Repeater gun; frontal Power Barrier with Surging Strike push; Propulsors horizontal fuel dash; ejects when mech dies; Limit Break ult self-overhealth + damage amp on enemies.',
 'dva': 'Dive tank: Boosters flight, Defense Matrix blocks projectiles in front, Micro Missiles; short-range spread guns; Self-Destruct ult, ejects on mech death.',
 'domina': 'Stalwart barrier tank: mid-range beam ending in high-impact shot; segmented Barrier Array; Sonic Repulsors push + wall stun; Crystal Charge remote explosive; Panopticon ult imprisons enemies.',
 'doomfist': 'Brawl/dive tank: Rocket Punch knockback (wall impact), Seismic Slam leap, Power Block frontal block empowers punch; Meteor Strike ult. Very mobile, short-range spread gun.',
 'echo': 'Flying recon: Tri-Shot projectiles, Sticky Bombs burst, Flight + Glide; Focusing Beam executes low-health targets; Duplicate ult copies an enemy.',
 'emre': 'Specialist with three-round burst rifle (zoom tightens accuracy/range); Cyber Frag bouncing grenade; Override Protocol ult transforms into a living weapon; Altered Vitals faster passive regen. Mid-long range, low mobility.',
 'freja': 'Recon crossbow: Take Aim high-speed explosive bolt; Quick Dash vault refreshes Take Aim; Updraft vertical launch; Bola Shot ult wraps and pulls enemies. Highly mobile poke/aerial pick hero.',
 'genji': 'Melee-range diving flanker: wall climb/double jump, Swift Strike dash (resets on kill), Deflect returns projectiles; Dragonblade ult.',
 'hanzo': 'Long-range projectile bow with one-shot potential; Storm Arrows, Sonic Arrow reveal, Lunge double jump, wall climb; Dragonstrike ult. Shield-breaking burst.',
 'hazard': 'Initiator brawl tank: Bonespur burst, Spike Guard frontal block with homing spikes, Violent Leap lunge + knockback slash, Jagged Wall knockback; Downpour ult immobilizes; Vault climbs walls.',
 'illari': 'Long-range auto-charging rifle + mid-range heal beam; Healing Pylon; Outburst knockback/mobility; Captive Sun ult slows and detonates.',
 'jetpackcat': 'Tactician flying healer: mid-range healing/damaging projectile spread; Frenetic Flight; Lifeline tows an ally (movement + healing); Purr AoE heal + knockback; Catnapper ult dives, knocks down and tethers an enemy. Can carry allies off-angle.',
 'junkerqueen': 'Stalwart brawl tank: short-range Scattergun, Commanding Shout (team temp health + speed), Carnage/Rampage wounds (anti-heal on Rampage); heals from wound DoT.',
 'junkrat': 'Specialist spam: bouncing frag grenades, Concussion Mine mobility/knockback, Steel Trap immobilize; RIP-Tire ult.',
 'juno': 'Mobile hybrid support: burst Mediblaster heals/damages, Pulsar Torpedoes lock-on heal/damage, Glide Boost, double jump/hover; Hyper Ring speed; Orbital Ray ult heals + damage amp.',
 'kiriko': 'Mobile medic: healing Ofuda, Kunai headshots, Swift Step teleport to ally, Protection Suzu invulnerability + cleanse; Kitsune Rush ult.',
 'lifeweaver': 'Medic: charged Healing Blossom, Thorn Volley, Petal Platform, Rejuvenating Dash; Life Grip pulls an ally to safety (saves from CC/ults); Tree of Life ult.',
 'lucio': 'Tactician speed/heal aura, Wall Ride mobility, Soundwave knockback (boops off map), Sound Barrier ult temp health. Enables brawl/rush, low single-target healing.',
 'mauga': 'Bruiser chaingun tank with high sustained damage, Overrun unstoppable charge and launch, Cardiac Overdrive damage reduction + team lifesteal, Berserker crit overhealth; Cage Fight ult.',
 'mei': 'Specialist short-range slowing spray + long-range icicle; Cryo-Freeze invulnerable self-heal; Ice Wall splits fights/blocks; Blizzard ult freezes.',
 'mercy': 'Medic beam healer/damage booster; Guardian Angel mobility to allies; Resurrect; Valkyrie flight ult.',
 'mizuki': 'Survivor support: bouncing Spirit Glaive damage, Healing Kasa bounces between allies, Binding Chain hinders an enemy (anti-mobility), Katashiro Return leap with recall teleport; Kekkai Sanctuary ult heals and absorbs projectiles; Remedy Aura passive heal.',
 'moira': 'Medic short-range healing spray + lock-on drain beam, Biotic Orb, Fade invulnerable escape; Coalescence ult.',
 'orisa': 'Bruiser sustain tank: heat-based mid-range gun, Energy Javelin stun/knockback, Fortify (unstoppable, damage reduction), Javelin Spin destroys projectiles; Terra Surge ult.',
 'pharah': 'Recon flyer: long-range rockets, Jump Jet/Jet Dash/Hover; Concussive Blast knockback; Barrage ult.',
 'ramattra': 'Stalwart form-shifting tank: Omnic Form projectile stream + placeable Void Barrier; Nemesis Form piercing punches with block; Ravenous Vortex slows/pulls down (anti-air/anti-mobility); Annihilation ult.',
 'reaper': 'Flanker close-range shotguns with lifesteal; Shadow Step teleport, Wraith Form invulnerable escape; Death Blossom ult.',
 'reinhardt': 'Stalwart melee tank: large frontal Barrier Field, Charge pin, Fire Strike; Earthshatter ult knockdown.',
 'roadhog': 'Bruiser (reworked 2026): two-burst Scrap Gun, Chain Hook pulls an enemy, Trash Compactor absorbs projectiles into an explosive scrap ball, Take a Breather self-heal + damage reduction; Whole Hog knockback ult.',
 'shion': 'Flanker bike rider: rapid-fire Kira Pistols, Execution X-shaped volley, Joyride bike that launches forward on dismount, Evade dash with overhealth; Satsuriku Spree ult triple rush. Highly mobile close/mid range.',
 'sierra': 'Recon automatic Helix Rifle (spiral pattern, gains accuracy), Tracking Shot mark makes shots home on target, Tremor Charge shockwave, Anchor Drone grapple; Trailblazer ult bombing drone.',
 'sigma': 'Stalwart poke tank: Hyperspheres, Kinetic Grasp absorbs projectiles into overhealth, Accretion knockdown, movable Experimental Barrier; Gravitic Flux ult.',
 'sojourn': 'Sharpshooter: rapid railgun + charged high-impact shot, Power Slide/jump mobility, Disruptor Shot zone; Overclock ult. Long-range burst pick hero.',
 'soldier76': 'Specialist all-rounder hitscan rifle, Sprint, Biotic Field self/team heal, Helix Rockets; Tactical Visor aimbot ult.',
 'sombra': 'Support (Tactician; moved from Damage in the 2026-10-06 Season 5 patch): short-range Machine Pistol, Hotfix heal-over-time that also hacks health packs and most enemy deployables, Cyberspace zone weakens enemies and heals allies, Translocator teleport + stealth; EMP ult damages by % current health, hacks and destroys barriers. No standalone Hack ability any more.',
 'symmetra': 'Specialist short-range charging beam + charged orbs, Sentry Turrets slow/damage, Teleporter; Photon Barrier ult.',
 'torbjorn': 'Specialist area denial: Rivet Gun long-range/short-range alt, auto-building turret, Overload temp health + speed; Molten Core ult (extra damage to armor).',
 'tracer': 'Flanker: Blink teleports, Recall restores health/position, short-range pulse pistols; Pulse Bomb ult.',
 'vendetta': 'Flanker melee greatsword: combo swings, Warding Stance frontal block (deflects melee) + Projected Edge ranged projectile, Whirlwind Dash, Soaring Slice throw-and-fly; Sundering Blade ult cleaves through defenses. Close range, high mobility.',
 'venture': 'Flanker short-range explosive excavator; Drill Dash push, Burrow invulnerable underground then emerge damage; Tectonic Shock ult.',
 'widowmaker': 'Sharpshooter long-range one-shot sniper, Grappling Hook, Venom Mine flank detection; Infra-Sight ult wallhack.',
 'winston': 'Initiator dive tank: Jump Pack leap, Barrier Projector dome, short-range chaining Tesla Cannon; Primal Rage ult.',
 'wreckingball': 'Initiator: Grappling Claw high-speed swing/collisions, Roll, Piledriver launch, Adaptive Shield scales with nearby enemies; Minefield ult.',
 'wuyang': 'Survivor support: water-orb projectile with controllable trajectory, Restorative Stream passive/active heal on one ally, Rushing Torrent mobility, Tidal Blast protect-then-knockdown; Guardian Wave ult knocks back and boosts healing received.',
 'zarya': 'Bruiser: short-range beam that scales with Energy, Particle Barrier self-bubble + Projected Barrier on ally; Graviton Surge ult.',
 'zenyatta': 'Tactician long-range orbs, Orb of Discord damage amp, Orb of Harmony heal; Snap Kick knockback; Transcendence ult invulnerable heal.',
}

SRC_HEROES = 'https://overwatch.blizzard.com/en-us/heroes/'
heroes = []
for c in cards:
    hid = c['slug'].replace('-', '')
    assert hid in KIT, hid
    abil = [{'name': n.strip(), 'desc': ' '.join(d.split())} for n, d in ab[c['slug']]]
    heroes.append({
        'id': hid,
        'name': c['name'],
        'role': c['role'],
        'subrole': c['sub'].capitalize(),
        'kit': KIT[hid],
        'abilities': abil,
        'official_page': SRC_HEROES + c['slug'] + '/',
        'portrait': 'assets/heroes/%s.png' % hid,
        'portrait_source': c['src'],
    })
assert len(heroes) == len(KIT)

out = {
 'as_of': '2026-11-14 (Overwatch Season 5 of 2026 "Reign of Talon"; midseason patch 2026-11-03, hotfix 2026-11-05)',
 'hero_count': len(heroes),
 'sources': [
  {'url': SRC_HEROES, 'used_for': 'Roster (54 heroes), role and sub-role of each hero (data-role/data-subrole on each hero card), sub-role passive text, portrait image URLs'},
  {'url': SRC_HEROES + '<slug>/', 'used_for': 'Ability names and descriptions per hero (official hero pages, fetched 2026-11-14)'},
  {'url': 'https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/11/', 'used_for': 'Latest live patch: 2026-11-03 midseason balance patch and 2026-11-05 hotfix; perks still live; no new hero in November'},
  {'url': 'https://kami-labs.fr/en/gaming/overwatch-saison-5-doctrine-roadhog-sombra/', 'used_for': 'Secondary (third-party) preview of Season 5; facts confirmed by the official 2026-10 patch notes.'},
  {'url': 'https://overwatch.blizzard.com/news/24316733/55-66', 'used_for': 'Queue formats: 5v5 standard Competitive, 6v6 Open Queue running, 2-2-2 6v6 Role Queue only as a 4-week Season 6 test'},
  {'url': 'https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/10/', 'used_for': '2026-10-06 "Reign of Talon - Season 5: A Grim Doctrine": Doctrine added, Sombra "Moved from Damage to Support role", Roadhog rework'},
  {'url': 'https://overwatch.blizzard.com/en-us/news/patch-notes/live/2026/06/', 'used_for': '2026-06-16 Hero Bans changes: Preferred Hero 3 negative votes, 5th Lobby Ban slot that can break the 2-per-role limit; Shion added'},
  {'url': 'https://overwatch.blizzard.com/en-us/news/24197272/', 'used_for': 'Original hero ban rules: 4 total (2 per team), weighted 7/5/3 vote, max 2 per role (Season 16, April 2025). Superseded in part by the 2026-06-16 patch.'},
 ],
 'game_rules': {
  'team_size': '5v5 role queue is the standard mode: 1 tank, 2 damage, 2 support. 6v6 Open Queue also exists; 6v6 2-2-2 Role Queue is planned only as a 4-week test at the start of Season 6. The scoreboard reader must handle 5 (and possibly 6) rows per team.',
  'subroles': {
   'tank': {'Bruiser': 'Gain resistance to critical hits. Move faster while below half health.', 'Initiator': 'Gain a heal over time after using a specified movement ability.', 'Stalwart': 'Gain knockback and slow resistance.'},
   'damage': {'Flanker': 'Health packs restore more health.', 'Recon': 'Damaging enemies below half health reveals them.', 'Sharpshooter': 'Critical hits reduce your movement ability cooldowns.', 'Specialist': 'Eliminating an enemy briefly increases reload speed.'},
   'support': {'Medic': 'Healing allies with your weapon also heals you.', 'Survivor': 'Movement abilities start passive health regeneration.', 'Tactician': 'Store excess ultimate charge.'},
  },
  'perks': 'Perks are live: each hero picks a Minor Perk and a Major Perk (Level 3) during a match (shown on official hero pages; adjusted in the 2026-11-03 patch). Perk choices can change a matchup mid-game (e.g. Winston Revitalizing Barrier, D.Mon Overstrike) but are not visible on the Tab scoreboard portrait.',
  'hero_bans': 'Competitive only. Base rule (Director\'s Take, Season 16, 2025): 4 bans per match (2 per team), weighted vote (7/5/3), at most 2 bans per role. Changed 2026-06-16 (Season 3 patch): a player\'s Preferred Hero contributes 3 negative votes, and a 5th "Lobby Ban" slot can break the 2-per-role limit (votes from both teams added; triggers if both teams voted for the hero and it got 10 total votes). So 4 or 5 heroes can be banned. Banned heroes cannot be picked, so the counter engine must exclude them; bans are not shown on the Tab scoreboard and must be entered another way.',
  'role_changes_2026': 'Sombra is now Support (Tactician). Roadhog was reworked (Trash Compactor, Take a Breather, Whole Hog). Do not rely on pre-2026 counter data for these two.',
  'stadium': 'Stadium is a separate mode with Powers bought in the Armory (official hero pages: 12 Powers per hero). Out of scope for counter-picking.',
 },
 'kit_note': 'kit = factual summary of official ability text only. Counter judgements (weak to / strong vs) were removed because no source was opened for them; counter data must come from sourced coach material.',
 'heroes': heroes,
}
json.dump(out, open(sys.argv[2], 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print(len(heroes))
