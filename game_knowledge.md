# Mechabellum Game Knowledge Base for LLM Strategy Analysis

Prepared: 2026-06-14  
Purpose: use this document as a compact but detailed prompt-context block for an LLM that must understand Mechabellum board states, reason about unit roles/counters/positioning, and propose high-quality strategic decisions.

> IMPORTANT VERSION NOTE
>
> Mechabellum changes frequently. This file is based on the publicly visible state around Update 1.11 / Season 8, where the official news says Typhoon was remade, Season 8 launched, Vortex entered starter packs, and new Anomalies were introduced. Some wiki/unit-guide pages may lag behind the latest patch. Treat numeric costs/stats/tech values as patch-sensitive. Treat the conceptual roles and counter logic as more stable than exact numbers.

---

## 1. What Mechabellum is

Mechabellum is a tactical auto-battler. Players do not micro-control units during combat. They draft, unlock, buy, position, level, and modify units during deployment phases. When the round begins, armies fight automatically. Victory comes from predicting the enemy board, forcing bad targeting, building efficient counter-compositions, and spending supply better than the opponent.

Core mental model:

- Deployment decisions are the real gameplay.
- The battle phase is a test of the deployment plan.
- A “counter” is rarely just a unit name. It is a combination of unit, tech, level, item, range, side of board, chaff timing, tower pressure, and enemy targeting.
- The correct move is often not “buy the hard counter”; it is “buy the cheapest thing that fixes the current failure while preserving long-term scaling.”

---

## 2. Vocabulary and strategic concepts

### 2.1 Basic terms

- **Board**: deployable battlefield area.
- **Round**: deployment phase plus automated battle phase.
- **Supply**: main resource used for units, unlocks, techs, buildings/devices, and some powers.
- **Unit unlock**: paying to make a unit available for purchase.
- **Tech / technology**: upgrade applied to a unit type. Tech choice can completely change a unit’s role.
- **Rank / level**: unit progression from experience. In replay data this may be zero-based; display level may be `stored_level + 1`.
- **Chaff**: cheap expendable units that distract enemy DPS and manipulate targeting. Crawlers, Fangs, and Wasps are the main examples.
- **Chaff clear**: units that kill many small bodies quickly. Arclight, Vulcan, Fire Badger, Mustang, Typhoon, Wraith, Tarantula, Sledgehammer, and Stormcaller can serve this role depending on context.
- **Carry**: a core damage unit that the rest of the army protects.
- **Frontline**: units placed to absorb damage or pull targeting.
- **Backline**: long-range DPS/support that should be protected from chaff, flanks, and artillery.
- **Aggro**: pushing near the line, applying tower pressure, forcing the opponent to defend early.
- **Standard**: balanced, slower composition that protects DPS, adds chaff, and scales through tech/levels.
- **Asym / crossfire**: both players are set up on opposite sides, causing armies to cross or attack at angles.
- **Tower debuff**: destroying a tower temporarily weakens the opponent’s army; many “cheese” and flank plays exist to force this.
- **EMP**: electromagnetic disable effect; temporarily disables tech and slows movement.
- **AA**: anti-air.
- **AM**: anti-missile / missile interception.

### 2.2 The most important strategic roles

Every unit should be evaluated by what job it performs on the current board:

1. **Cheap chaff**: buys time and wastes enemy shots.
2. **Chaff clear**: removes enemy chaff so your DPS can connect.
3. **Single-target DPS**: kills tanks, giants, high-level units, and carries.
4. **Area damage / artillery**: punishes clumped units and backline formations.
5. **Anti-air**: prevents Wasp/Phoenix/Overlord/Wraith/Raiden/Phantom Ray/Abyss punishment.
6. **Tank / frontline**: absorbs damage and shapes targeting.
7. **Support**: shields, range buffs, missile interception, status immunity, fire/acid/smoke cleanup, beacon/pathing manipulation.
8. **Tower pressure / flank threat**: creates immediate loss pressure even if not best in a straight fight.
9. **Tech denial**: EMP, hacking, acid, fire, smoke/range reduction, degeneration.

A strong army usually has at least:

- enough chaff to prevent your expensive DPS from wasting shots or getting hacked/melted;
- enough chaff clear to let your DPS reach valuable targets;
- a plan for air units;
- a plan for giants/tanks;
- a plan for enemy artillery/backline;
- a plan for flanks.

---

## 3. Core mechanics that matter for reasoning

### 3.1 Targeting

Units generally target or move toward the closest valid target. Facing direction and unit orientation can matter. Certain techs change targeting priorities. Aerial Specialization treats air units as effectively closer unless only ground units are inside base range.

Implications:

- Chaff placement matters more than chaff count alone.
- A cheap unit in the right spot can waste multiple volleys from an expensive carry.
- Flanks can change which side of the army turns and shoots.
- If enemy Marksmen/Melting Points/Phoenixes are shooting chaff, your board may already be winning even if your unit choices look weaker.

### 3.2 Chaff waves

Good chaff is not only “front row.” Chaff should arrive in waves:

- front chaff absorbs opening shots;
- middle chaff protects DPS as lines meet;
- back chaff can distract enemy units after their chaff clear moves forward;
- side/flank chaff can pull targeting away from towers or carries.

Crawlers are fast and can chain into waves. Fangs are slow and can be placed behind to become delayed chaff. Wasps can distract ground-only units and punish lack of AA.

### 3.3 Experience and leveling

Experience is powerful but dangerous:

- High-level units gain stronger stats and can become carries.
- Killing high-level units feeds large experience to the enemy.
- Leveling chaff can accidentally feed enemy chaff clear very quickly.
- Do not level units just because the button is available; level when the unit will survive and its role scales.
- Be careful with high-level single squads that can be hacked, EMPed, acid-bursted, or isolated.

### 3.4 Buffs, debuffs, and stacking

- Stat buffs are additive; adding a small buff on top of a huge buff may have weak marginal value.
- Debuffs are multiplicative; stacking multiple debuffs has diminishing returns.
- Some unit techs and items with the same effect do not stack; item may be prioritized.
- Range buffs from different sources can behave differently for unit techs.

LLM rule: before recommending a buff or item, check whether it stacks with existing techs and whether the buff targets the unit’s real bottleneck. Do not add attack to a unit that cannot connect; fix range/targeting/chaff first.

### 3.5 Flanks

Flanks become available from round 2. Units placed on a flank have a spawn delay the first round they are deployed there. Flanks are powerful but risky:

- Use flanks to pull enemy units away from center.
- Use flanks to expose towers and trigger tower debuffs.
- Air flanks are especially punishing when enemy AA is weak.
- Do not overinvest in flanks if they are easily defended.
- Defending a flank often costs less than attacking with it if the defender has correct units.

### 3.6 Missile interception

Many attacks/techs are missiles and can be intercepted. Missile interception is relevant against Stormcaller, Phantom Ray, Farseer, Overlord, Hound Incendiary Bomb, Phantom Ray Sticky Oil Bomb, Typhoon Homing Missile, Vulcan bombs, Melting Point EM Barrage, Fortress Anti-Air Barrage/Rocket Punch, Abyss Swarm Missiles, and Mountain Smoke Bomb.

Important heuristics:

- Mustang is very efficient AM per cost but stops attacking enemies while intercepting.
- War Factory is very efficient AM per deployment.
- Interception efficiency decreases over time.
- Do not overbuy AM if the enemy can pivot away from missiles.
- Protect AM units, because losing AM can suddenly make Stormcallers/Overlords decisive.

### 3.7 Unit orientation

Units can be placed horizontally or vertically.

- Vertical formation often staggers shots and improves sustained chaff clear.
- Horizontal formation spreads units out, covers more area, and may create burst or wider target coverage.
- Vertical units move more predictably and concentrate in a column.
- Vertical units can be more vulnerable to Stormcaller/Siege Scorpion-type area punishment.
- Vertical Fangs and Sledgehammers can stall aggressive pushes.

### 3.8 Mobile Beacon

Mobile Beacon lets a small group follow a path. It is used for tower pressure, flanking, pulling, or avoiding bad targeting.

Rules of thumb:

- Beaconed units move relative to their starting position inside the beacon circle.
- A beaconed unit may stop when an enemy is on the path and within attack range.
- Only units already on the board can be beaconed; spawned units from spells/techs cannot.
- Beacon is especially dangerous with fast units or air when it creates a tower debuff.

### 3.9 Unit reinforcements / free unit drops

Unit reinforcement offers happen in windows: once between rounds 2-4, 5-7, 8-10, and 11-13. Each time, four units are offered; picking one unlocks that unit for the rest of the game. Reinforcements cannot happen back to back. A unit already deployed on the battlefield is blocked from being offered as a reinforcement. Cost-altering cards can also block units from offers.

LLM rule: when planning unlocks, consider whether waiting for a drop is better than paying unlock cost now. Conversely, deploying a unit can intentionally block it from future offers.

---

## 4. High-level game plan by phase

### 4.1 Early game: rounds 1-4

Objectives:

- Establish enough chaff and enough chaff clear.
- Avoid expensive tech commitments unless they solve an immediate problem or scale across many squads.
- Do not ignore air. One Wasp/Phoenix/Phantom Ray line can punish no-AA boards.
- Watch enemy unlocks and reinforcement/card choices.
- Fight for tower safety; early tower debuffs can snowball.

Common mistakes:

- Unlocking expensive tech before having enough units to benefit from it.
- Buying only DPS and losing to cheap chaff.
- Overreacting to one threat with too much supply.
- Placing all chaff in one predictable line.

### 4.2 Mid game: rounds 5-8

Objectives:

- Identify enemy carry and build a counter-chain.
- Decide whether you are standard, aggro, air, giant, artillery, or swarm-based.
- Add techs that solve real bottlenecks: range, EMP, AA, AM, shield, acid/fire, mobility.
- Start using flanks and beacon when they force expensive defense.
- Protect your own scaling units from being hacked, melted, or fed.

### 4.3 Late game: rounds 9+

Objectives:

- Preserve carries and deny enemy carries.
- Use layered chaff; simple front chaff is often insufficient.
- Manage shields, EMP, missile interception, and range wars.
- Consider tower damage and HP totals: sometimes the correct move is not to win cleanly, but to deal lethal damage.
- Watch for hidden conversion points: one Hacker, one Stormcaller EMP volley, one shield, one mobile beacon can flip the round.

---

## 5. Counter logic: how to think, not memorize

A counter must be chosen based on the enemy unit’s actual role on board.

### 5.1 If enemy has many small bodies

Threat examples: Crawlers, Fangs, Wasps, spawned Fangs, crawler replicate, War Factory production.

Answers:

- Arclight: efficient medium-range ground chaff clear.
- Vulcan: premium sustained ground chaff clear.
- Fire Badger: short/medium-range fire-based chaff clear.
- Mustang: anti-light and anti-air; also AM tech option.
- Typhoon: frontline chaff clear and anti-air after Season 8 remake.
- Wraith: air chaff clear, can punish ground swarms and Wasps.
- Tarantula: durable anti-light ground control.
- Stormcaller: punishes dense formations, but can overkill and be intercepted.

### 5.2 If enemy has one/few high-HP ground units

Threat examples: Fortress, Vulcan, Mountain, Death Knell, War Factory, Rhino, high-level Sledgehammer, high-level Steel Ball.

Answers:

- Melting Point / Death Knell: ramping beam damage.
- Steel Ball: excellent against isolated tanks if protected from chaff.
- Scorpion: high-impact anti-heavy artillery/direct fire depending on tech and position.
- Hacker: turns expensive ground units if chaff clear is solved.
- Marksman/Phoenix: long-range single-target DPS, especially if enemy lacks chaff.
- Acid/fire/EMP: reduce survivability and disable tech-based defense.
- Chaff: needed so anti-heavy units do not get distracted or killed.

### 5.3 If enemy has strong long-range backline

Threat examples: Marksman, Phoenix, Stormcaller, Farseer, Overlord artillery, Mountain extended range.

Answers:

- Chaff waves to waste shots.
- Flanks to pull or kill backline.
- Mobile Beacon to create tower pressure and force repositioning.
- Stormcaller or Scorpion to punish clumped backline.
- Range tech on your own backline.
- EMP to disable defensive techs or missile-based units.
- Air if they lack AA.

### 5.4 If enemy has air

Threat examples: Wasps, Phoenix, Overlord, Wraith, Phantom Ray, Raiden, Abyss.

Answers:

- Mustang: core anti-air/chaff clear.
- Marksman with Aerial Specialization: long-range anti-air single-target.
- Fangs: cheap AA/chaff, especially with range/shield depending on role.
- Typhoon: frontline anti-air/chaff-clear after Season 8 remake.
- Farseer: support/anti-air, especially with Aerial Specialization.
- Fortress Anti-Air Barrage: tech-based anti-air from a ground giant.
- Arclight Anti-Aircraft Ammunition: niche AA when already using Arclights.
- Phoenix/Overlord/Wraith mirror answers depending on range and protection.

### 5.5 If enemy has artillery/missiles

Threat examples: Stormcaller, Overlord, Farseer, Phantom Ray, Typhoon Homing Missile, Fortress barrages, Mountain bombs, Abyss missiles.

Answers:

- Missile Interceptor device.
- Mustang AM tech if it does not ruin your DPS plan.
- War Factory AM role.
- Spread formation and avoid vertical clumps.
- Flanks / fast units to force missile units to retarget.
- Air or underground/melee threats to bypass front line.
- Shields if timing and coverage are correct.

### 5.6 If enemy has shields/barriers

Threat examples: Fortress Barrier, Hacker Barrier, Typhoon Barrier, shield devices, Fangs with Portable Shield.

Answers:

- High sustained DPS, not only burst.
- EMP to disable shield-generating tech if applicable.
- Stormcaller or AoE if shield covers a static cluster.
- Melting Point/Death Knell if shield protects giants and you can clear chaff.
- Avoid wasting all damage into the shield while enemy carry shoots freely; sometimes flank/tower pressure is better.

### 5.7 If enemy has Hacker

Answers:

- Chaff in front of valuable units.
- Air, because Hacker targets ground only.
- Long-range snipe if Hacker is exposed.
- Stormcaller/Scorpion area punishment if Hacker hides behind slow front.
- EMP can interrupt/slow important tech interactions.
- Do not feed Hacker a single high-level ground unit without chaff protection.

---

## 6. Unit roster by cost bracket

The wiki unit overview groups units by supply cost:

- **100 supply**: Arclight, Crawler, Fang, Hound, Marksman.
- **200 supply**: Fire Badger, Hacker, Mustang, Phantom Ray, Phoenix, Rhino, Sabertooth, Sledgehammer, Steel Ball, Stormcaller, Tarantula, Wasp.
- **300 supply**: Farseer, Scorpion, Typhoon, Wraith.
- **400 supply**: Fortress, Melting Point, Raiden, Sandworm, Vulcan.
- **500 supply**: Overlord.
- **800 supply**: Abyss, Death Knell, Mountain, War Factory.

Note: unlock costs and availability differ. Some units may appear in starter packs, reinforcements, specialist effects, or special modes. Update 1.11 says Vortex is in starter packs and Typhoon was moved/remade into the core roster; check live game data for exact availability.

---

## 7. Unit knowledge cards

Each card below is written for strategic reasoning, not as an exact stat sheet.

### 7.1 Arclight

Role: cheap/medium-range ground chaff clear. Excellent into Crawlers, Fangs, Mustangs and other light ground swarms.

How to use:

- Buy when enemy ground chaff is blocking your DPS.
- Range Enhancement makes multiple Arclights a stable chaff-clear package.
- EMP tech gives late-game utility against tech-dependent units.
- Charged Shot helps into medium bodies but can hurt against pure chaff if attack interval becomes too slow.
- Anti-Aircraft Ammunition is niche but can patch weak AA if you already have Arclights.

Counters / weak against:

- Long-range single-target DPS like Marksman/Phoenix if Arclights are exposed.
- Air if no AA tech.
- Hackers/Fortress/giants if the fight becomes about durable targets instead of chaff.
- Stormcaller/Scorpion if clumped.

LLM heuristic: Arclight is a solution to “my DPS cannot reach because of ground chaff,” not a universal frontline.

### 7.2 Crawler

Role: cheapest high-speed melee chaff; one of the most important units in the game.

How to use:

- Use as layered chaff, not only front line.
- Place at different depths to create waves.
- Use flanks to pull fire or threaten towers.
- Subterranean Blitz and Loose Formation can make late-game Crawlers difficult to clear.
- Acidic Explosion can punish aggressive giants and high-HP frontlines.
- Impact Drill/Replicate can help Crawler mirror fights or create snowball.

Good into:

- Marksman, Phoenix, Melting Point, Overlord, Sabertooth, Scorpion, Stormcaller when they lack adequate chaff clear.

Countered by:

- Arclight, Vulcan, Fire Badger, Tarantula, Wraith, Typhoon, Sledgehammer, Rhino, Stormcaller if clumped.

LLM heuristic: if enemy DPS is too effective, add Crawlers before adding more expensive tanks. If enemy has too much chaff clear, delay/spread/tech Crawlers rather than only adding more.

### 7.3 Death Knell

Role: 800-cost ranged titan with multiple ramping beams, similar anti-heavy logic to multiple Melting Points.

How to use:

- Pair with reliable chaff clear; the beam wants high-value targets, not Crawlers.
- Barrier can protect a large army section and scales heavily with rank.
- Energy Absorption turns damage into sustain.
- Energy Diffraction increases multi-target beam coverage but lowers range.
- EM Bomb provides large tech-disabling utility.
- Steel Ball Production gives extra bodies and frontline distraction.

Good into:

- Sledgehammer, Fortress, Vulcan, Overlord and other expensive durable units if it can connect.

Countered by:

- Melting Point mirror/anti-titan logic.
- EMP, chaff, heavy air pressure, Hacker-style conversion threats, and positioning that denies beam contact.

LLM heuristic: Death Knell is a late-game centerpiece. Do not recommend it if the player cannot already solve chaff, AA, and flanks.

### 7.4 Fang

Role: cheap ranged light unit. Can be chaff, delayed chaff, anti-air filler, or scaled ranged DPS depending on tech.

How to use:

- Place behind main army to become delayed chaff after front chaff dies.
- Place in front to absorb missiles/opening lock-ons.
- Portable Shield makes them strong defensive chaff.
- Range Enhancement helps them contribute against air and stay relevant.
- Ignite punishes high-HP targets by blocking healing and burning HP.
- Grenade Launcher turns them into ground-only splash; be careful losing air targeting.
- Mechanical Rage + Armor-Piercing can make high-level Fangs real DPS.

Good into:

- Air chip, late distraction, protection against single-target DPS, and some giant setups with Ignite.

Countered by:

- Crawlers, Mustangs, Stormcallers, Vulcans, Typhoon, Tarantula and other efficient light clear.

LLM heuristic: Fangs are slower than Crawlers; use them when delayed ranged chaff or cheap AA matters.

### 7.5 Farseer

Role: 300-cost long-range support and anti-air missile unit.

How to use:

- Early all-rounder: long range, moderate AoE, hits air and ground.
- Photon Emission grants ground allies temporary damage reduction and status immunity.
- Scanning Radar gives nearby allies range.
- Missile Interceptor provides local AM.
- Aerial Specialization improves anti-air role.
- Burst Mode increases missile burst but makes interception and overkill concerns more important.

Good into:

- Mixed early boards, air threats, and compositions needing range/support/status protection.

Countered by:

- Missile interception, long-range snipers, Stormcaller/Scorpion pressure, chaff pull, and units that outscale its mixed role.

LLM heuristic: Farseer is a support glue unit. Do not treat it as a pure carry unless the board specifically lets missiles connect.

### 7.6 Fire Badger

Role: 200-cost short/medium-range ground chaff clear with fire utility.

How to use:

- Strong early into ground swarms.
- Napalm spreads ground fire and can continue killing Crawlers after the Badger dies.
- Scorching Fire increases killing speed.
- Field Maintenance / Counter-Fire / Scorching Charge improve survivability or tempo.
- Ignite can punish high-HP enemies but is more niche.
- Fire Badger can ignite oil effects, creating large battlefield swings.

Good into:

- Crawlers, Fangs, light ground swarms, and early medium boards.

Countered by:

- Long-range single-target DPS, air, Scorpion/Sabertooth/Fortress if it cannot close, and boards with sufficient range control.

LLM heuristic: Fire Badger is good when the fight happens inside its range. If enemy has long range, solve delivery or choose another chaff clear.

### 7.7 Fortress

Role: 400-cost ranged giant guard robot; protects team while dealing high ground damage.

How to use:

- Use as frontline/anchor when enemy lacks dedicated anti-giant.
- Barrier protects allies; very important in late game shield wars.
- Range Enhancement/Solid Shot lets Fortress play from safer ranges.
- Anti-Air Barrage patches air weakness but is missile-based and interceptable.
- Fang Production adds bodies/chaff.
- Rocket Punch can burst backline or clumped threats.
- Launcher Overload increases DPS but lowers range.

Good into:

- Ground pushes, medium units, and compositions that cannot melt a giant quickly.

Countered by:

- Melting Point, Hacker, Steel Ball, Scorpion, air pressure, EMP, acid/fire, and chaff that wastes Fortress shots.

LLM heuristic: Fortress is not just a tank; it is a shield platform. If recommending Fortress, specify whether it is for damage, barrier, AA barrage, or frontline anchoring.

### 7.8 Hacker

Role: 200-cost long-range control unit that converts ground units instead of dealing normal damage.

How to use:

- Only good if enemy high-value ground units can be reached through chaff.
- Needs heavy chaff clear and protection.
- Range Enhancement keeps it safe.
- Barrier adds team utility.
- Enhanced Control makes successful hacks higher value.
- Multi Control can handle multiple targets but lowers efficiency/range.
- EMP interaction can help disable defensive tech during control attempts.

Good into:

- Steel Ball, Sledgehammer, Rhino, Scorpion, Melting Point, Fire Badger, Arclight, Fortress if chaff is solved.

Countered by:

- Chaff, air units, Stormcaller, Phoenix, Wraith, Overlord, War Factory, long-range snipe, and any board that denies clean target access.

LLM heuristic: do not recommend Hacker without also recommending chaff clear and target isolation.

### 7.9 Hound

Role: 100-cost short-range light anti-swarm mech and utility chaff-clear.

How to use:

- Early light clear; needs levels/techs to stay relevant.
- Range Enhancement improves survivability and experience farming.
- Mechanical Rage improves clear speed and DPS.
- Fire Extinguisher clears fire, acid, and smoke in an area.
- Incendiary Bomb gives cheap remote fire utility.
- Armor Enhancement helps versus low-ATK chaff clear.
- Chamber Compression turns it into a ramping shot unit.

Good into:

- Crawlers/Fangs and ground-effect-heavy boards when Fire Extinguisher is relevant.

Countered by:

- Heavy armor, long range, air, high burst, and late-game boards if not leveled/teched.

LLM heuristic: Hound is a flexible early/utility piece, not a guaranteed late carry.

### 7.10 Marksman

Role: 100-cost long-range single-target DPS that hits air and ground.

How to use:

- Early anti-air and anti-tank DPS.
- Range Enhancement wins range wars and contests Stormcaller/other snipers.
- Doubleshot/Elite Marksman/Aerial Specialization improve kill power.
- EMP shot is excellent against tech-reliant carries/tanks.
- Quick Reload reduces overkill into smaller targets but lowers damage.
- Assault Mode radically changes role into shorter-range tanky AoE marksman.

Good into:

- Exposed high-value targets, Phoenix, Overlord, Wraith, Scorpion, Fortress/Rhino/Vulcan when protected.

Countered by:

- Crawlers/Fangs/Wasps, Stormcaller, Steel Ball/Rhino/flank pressure, Hackers, and chaff waves that waste shots.

LLM heuristic: Marksmen need chaff clear in front. If they keep shooting Crawlers, add chaff clear or reposition before adding more Marksmen.

### 7.11 Melting Point

Role: 400-cost ramping beam anti-giant / anti-high-HP unit.

How to use:

- Standard response to Fortress, Vulcan, War Factory, Rhino, Wraith, Overlord, Scorpion, high-level armored units.
- Needs chaff clear; otherwise it wastes time on small units.
- Range and EMP barrage can turn it into late-game control.
- Energy Absorption/sustain builds can carry if protected.
- Crawler/Steel Ball production techs can add bodies depending on patch/loadout.

Good into:

- Giants, tanks, high-level durable units.

Countered by:

- Crawlers/Fangs/Wasps, Marksman/Phoenix, Stormcaller, Hacker, Steel Ball, EMP, and any board that denies beam uptime.

LLM heuristic: Melting Point solves “big thing not dying,” not “enemy has many units.” Always pair with chaff clear.

### 7.12 Mountain

Role: 800-cost ranged titan with huge HP and strong ground damage.

How to use:

- Use as a late-game titan anchor when you can protect from anti-giant tools.
- Gun-launched Missile adds long-range burst/AoE.
- Mountain Plating blocks damage and improves tanking.
- Saturation Bombardment increases area pressure.
- Extended Range Ammo creates extreme range but lowers attack.
- Smoke Bomb reduces enemy range and can break enemy backline efficiency.
- Photon Loop gives damage reduction and status immunity.
- Anti-Aircraft Ammunition allows air targeting at damage cost.

Good into:

- Ground-heavy boards lacking Melting Point/Hacker/Scorpion/air punishment.

Countered by:

- Melting Point/Death Knell, Hacker, EMP, air if no AA, chaff disruption, and focused anti-titan tech.

LLM heuristic: Mountain is a huge commitment. Recommend it only when the opponent’s anti-giant path is delayed or already countered.

### 7.13 Mustang

Role: 200-cost anti-light, anti-air, and missile-interception platform.

How to use:

- Core answer to Wasps and light air swarms.
- Can clear Fangs and some Crawlers, especially with splash/culling-type techs.
- AM tech can counter missile-heavy boards, but Mustangs stop attacking while intercepting.
- Needs protection from heavy AoE and tanks.
- Works well behind frontline/chaff.

Good into:

- Wasps, Fangs, light units, missile pressure, some air compositions.

Countered by:

- Stormcaller, Vulcan, Sledgehammer, Arclight, Typhoon, Tarantula, Fortress, Rhino and other units that punish light clustered bodies.

LLM heuristic: Mustang can be AA, chaff clear, or AM. Do not overload it with all roles if one role conflicts with another.

### 7.14 Rhino

Role: 200-cost fast melee ground threat; tower pressure and frontline disruption.

How to use:

- Aggressive pressure unit that forces response.
- Good for flanks, mobile beacon plays, and punishing exposed backline.
- Can absorb shots and disrupt target priorities.
- Final Blitz / explosion-style builds can create suicide value.
- Needs support against chaff and high single-target DPS.

Good into:

- Exposed Marksmen/Stormcallers/weak backline, boards without enough chaff or anti-melee.

Countered by:

- Crawlers/Fangs as distraction, Melting Point/Steel Ball/Marksman/Phoenix, Hacker, Fortress, Scorpion, and slowing/EMP effects.

LLM heuristic: Rhino is strongest when it creates immediate position/tower pressure, not when walking through layered chaff into anti-tank fire.

### 7.15 Sabertooth

Role: 200-cost medium/heavy ranged single-target tank/damage unit.

How to use:

- Solid against medium/high-value targets when protected.
- Can be used as a stable ranged tank in standard boards.
- Needs chaff and anti-chaff support.
- Vulnerable to cheap distractions and dedicated anti-heavy.

Good into:

- Medium units, some frontline units, and boards lacking chaff.

Countered by:

- Crawlers/Fangs, Melting Point, Steel Ball, Hacker, Phoenix/Marksman, Scorpion, and heavy artillery if clumped.

LLM heuristic: Sabertooth is a value bruiser. It needs target access and should not be used as the only solution to swarms.

### 7.16 Sandworm

Role: 400-cost giant/rare ground unit with tunneling/disruption identity.

How to use:

- Punishes static backlines and creates formation chaos.
- Strong when the opponent has weak control and poor anti-giant.
- Often benefits from protection against EMP/status and from complementary chaff clear.
- Can threaten towers or backline depending on positioning and tech.

Good into:

- Static long-range boards, weakly protected backline, and formations that cannot retarget quickly.

Countered by:

- Melting Point, Scorpion, Hacker, EMP, strong chaff/tank layers, and air if your comp overinvests in ground-only pressure.

LLM heuristic: Sandworm is a disruption pick. Recommend it when pathing chaos solves the enemy board, not simply because enemy has backline.

### 7.17 Scorpion

Role: 300-cost heavy anti-armor / artillery-like ground unit.

How to use:

- Punishes expensive ground units and clumped medium/heavy boards.
- Acid/anti-armor techs can make it strong versus high HP and Titans.
- Needs protection from chaff and air.
- Position carefully; it can overkill or be distracted.

Good into:

- Fortress, Rhino, Vulcan, War Factory, Steel Ball, Typhoon, Sledgehammer and other ground value units.

Countered by:

- Crawlers/Fangs/Wasps, Phoenix/Overlord/Marksman, Stormcaller, Hacker, and flanks that force bad target selection.

LLM heuristic: Scorpion is a precision answer to durable ground value. Always ask: “Will it shoot the right target?”

### 7.18 Sledgehammer

Role: 200-cost medium tank line; generalist ground frontline/DPS.

How to use:

- Good early stabilizer.
- Can protect backline and absorb light fire.
- Scales with levels and certain armor/range/damage techs.
- Vertical placement can stall pushes.

Good into:

- Arclight, Mustang, Fangs, Crawlers, light ground, weak medium boards.

Countered by:

- Hacker, Fortress, Phoenix, Overlord, Scorpion, War Factory, Marksman, Rhino, Melting Point if high-level, and chaff if unsupported.

LLM heuristic: Sledgehammer is a stabilizer, not a late-game answer to everything. If it is dying to anti-armor, pivot or protect.

### 7.19 Steel Ball

Role: 200-cost anti-heavy rolling/melee-ish unit with strong single-target pressure.

How to use:

- Excellent into isolated high-HP targets if it connects.
- Needs chaff clear and protection from being distracted.
- Can snowball levels if it gets good targets.
- Vulnerable to chaff and control.

Good into:

- Fortress, Rhino, Melting Point, Vulcan, War Factory, Fire Badger, Typhoon.

Countered by:

- Crawlers/Fangs, Hacker, Phoenix, Overlord, Stormcaller, Scorpion, EMP, and bad pathing.

LLM heuristic: Steel Ball is only as good as its target access. If it spends the fight on Crawlers, it is not a counter.

### 7.20 Stormcaller

Role: 200-cost long-range missile artillery.

How to use:

- Punishes clumped ground units and static backlines.
- EMP missiles can disable tech/shields/armor and swing fights.
- Incendiary or high-impact techs can create persistent area denial.
- Strong when enemy lacks AM, spread, or pressure.
- Vulnerable to missile interception and fast/flank threats.

Good into:

- Arclight, Fang, Melting Point, Vulcan, Mustang, Marksman, Fortress, Scorpion, Typhoon, dense Sledge lines.

Countered by:

- Overlord/Phoenix pressure, Stormcaller mirror, Crawlers/flanks, Sledgehammer/Rhino rush, War Factory/Mustang AM, Sabertooth depending on positioning.

LLM heuristic: Before recommending Stormcaller, check if enemy already has AM or if the target is too spread/fast.

### 7.21 Tarantula

Role: 200-cost durable anti-light/medium ground unit with strong local control.

How to use:

- Strong into Crawlers/Fangs and some medium units.
- Durable enough to frontline better than pure chaff clear.
- Techs can push it toward armor, range, or damage depending on matchup.
- Can be a good answer to swarm when Arclight/Vulcan lines are vulnerable.

Good into:

- Crawlers, Fangs, Mustangs, light ground, some early/mid boards.

Countered by:

- Melting Point/Steel Ball/Scorpion, Phoenix/Marksman, Stormcaller, Hacker, air if no support.

LLM heuristic: Tarantula is a robust anti-swarm bruiser. Use when you need chaff clear that does not instantly die.

### 7.22 Typhoon

Role: after Update 1.11 / Season 8, Typhoon is a frontline chaff-clearing and anti-air unit, moved into a more core role. Official notes say the remake removed old techs and added new techs including Range Enhancement, Anti-Air Marker, Reactive Armor, Maintenance Array, Field Reassembly, Wreckage Detonation, and Field Entrenchment.

How to use:

- Use as tanky frontline anti-light and anti-air.
- Range Enhancement improves reach.
- Anti-Air Marker punishes air by lowering range and increasing damage taken.
- Reactive Armor helps survive burst.
- Maintenance Array adds healing to self/allies.
- Field Reassembly gives one revive-like return.
- Wreckage Detonation adds chain clear when Typhoon kills units.
- Field Entrenchment turns it into a static fortified defender.

Good into:

- Crawlers, Fangs, Wasps, light swarms, some air pressure, and frontline stabilization.

Countered by:

- Dedicated anti-heavy like Scorpion/Melting Point, long-range artillery, Fortress/Sandworm/Mountain type heavy pressure, EMP/status, and being outranged if it cannot connect.

LLM heuristic: Because Typhoon was recently remade, prefer live patch data over older wiki descriptions.

### 7.23 Void Eye

Role: ranged support/DPS unit with electromagnetic/status identity.

How to use:

- Use when EMP/control and ranged support matter.
- Strong in comps that need to disable tech-dependent enemies.
- Can pair with Fire Badger, Arclight, Sandworm, or standard frontlines depending on board.
- Needs chaff and protection.

Good into:

- Tech-dependent ground boards, shield/armor-reliant units, medium/high-value units if protected.

Countered by:

- Chaff floods, Stormcaller/Scorpion, fast melee/flanks, long-range snipers, air pressure if unsupported.

LLM heuristic: Void Eye is valuable for disabling, not just raw damage. Recommend it when disabling enemy tech changes the fight.

### 7.24 Vortex

Role: ground unit introduced/expanded in later updates; Update 1.11 notes say Vortex is now in starter packs. It has grid/link-style tech identity and can scale through linked units/positioning.

How to use:

- Treat as a synergy/scaling unit, not just raw stat stick.
- Its value depends heavily on placement and whether linked/supported units survive.
- Watch patch notes for exact tech values; Update 1.11 adjusted Grid Integration, Emergency Armor, Field Maintenance, and Electromagnetic Twin costs/effects.

Good into:

- Boards where its link/scaling mechanic can stay alive and generate value.

Countered by:

- Focus fire, EMP/control, artillery/AoE against linked clusters, and flanks that break formation.

LLM heuristic: Only recommend Vortex if you can explain the formation/synergy being built around it.

### 7.25 Vulcan

Role: 400-cost giant ground chaff-clear/flame platform.

How to use:

- Premium answer to ground swarm and low-HP masses.
- Strong stabilizer when enemy overuses Crawlers/Fangs.
- Can scale with range/fire/utility tech.
- Needs protection from anti-giant and air.

Good into:

- Crawlers, Fangs, Mustangs, Arclights, ground swarms, some medium pushes.

Countered by:

- Melting Point, Steel Ball, Scorpion, Hacker, Phoenix/Marksman, Overlord, air, EMP/acid, and chaff pulling if poorly positioned.

LLM heuristic: Vulcan is great when the problem is “too many bodies.” It is bad if the real problem is enemy single-target anti-giant already online.

### 7.26 War Factory

Role: 800-cost production/support/titan unit; also one of the strongest per-deployment missile interception platforms.

How to use:

- Use as late-game production engine and anti-missile anchor.
- Can answer missile-heavy boards, especially Stormcallers and tech missiles.
- Produces units depending on tech/loadout and can overwhelm long fights.
- Needs protection from anti-giant and focused DPS.

Good into:

- Arclight, Marksman, Rhino, Sledgehammer, Steel Ball, Vulcan, Stormcaller, Overlord, Fire Badger, Typhoon, Sabertooth and missile-based boards when AM is needed.

Countered by:

- Melting Point, Scorpion, Hacker/EMP, Phoenix/Marksman pressure, and sufficient anti-giant DPS.

LLM heuristic: War Factory is often less about direct damage and more about production + AM + inevitability. Recommend it when the game will go long.

### 7.27 Abyss

Role: 800-cost air titan. High commitment, air-based late-game threat.

How to use:

- Use when enemy anti-air is weak or can be disabled/overloaded.
- Needs protection from Marksman/Phoenix/Farseer/Mustang/Typhoon/AA techs.
- Swarm Missiles or similar missile techs may require checking enemy AM.
- Strong when it forces the opponent to split between anti-ground and anti-air.

Good into:

- Ground-only or weak-AA boards, slow giant boards, clumped support if its weapons connect.

Countered by:

- Melting Point in some interactions, Marksman/Farseer/Typhoon/Mustang/Phoenix/Overlord AA, missile interception, EMP/anti-air markers, and range control.

LLM heuristic: Never recommend Abyss just because it is expensive. Recommend it only when enemy AA/AM economy is weak.

### 7.28 Overlord

Role: 500-cost air backline damage dealer, missile/artillery-like pressure.

How to use:

- Strong aggressive pressure, especially against weak AA and towers.
- Needs protection and chaff/frontline to prevent enemy long-range AA from free firing.
- Can be supported by Rhinos/Steel Balls/Sledgehammers/ground pressure to force enemy targeting.
- Vulnerable to missile interception depending on tech/attack and to long-range anti-air.

Good into:

- Arclight, Fang, Melting Point, Vulcan, Mustang, Marksman, Fortress, Scorpion, Typhoon depending on AA and range context.

Countered by:

- Marksman, Phoenix, Mustang, Farseer, Typhoon AA, Fortress AA Barrage, War Factory AM, missile interception, and enemy Overlord/Phoenix range pressure.

LLM heuristic: Overlord is best when aggressive tower pressure matters. It is risky in pure long-range standard if enemy has better AA.

### 7.29 Phantom Ray

Role: 200-cost medium aircraft with missile/bomb identity and close-range pressure.

How to use:

- Punishes weak AA and ground-only boards.
- Sticky Oil Bomb and missile attacks can be intercepted/answered.
- Can be a tempo air threat before heavy AA is online.
- Needs support against Mustangs/Marksmen/Farseers.

Good into:

- Ground-only or slow boards, exposed backline, units weak to air pressure.

Countered by:

- Mustangs, Marksmen, Farseer, Typhoon, Phoenix, missile interception, and spread positioning.

LLM heuristic: Phantom Ray is a tempo air punish. Check enemy AA before scaling it.

### 7.30 Phoenix

Role: 200-cost long-range air single-target DPS.

How to use:

- Excellent into exposed ground DPS, Melting Points, Steel Balls, Scorpions, and weak-AA boards.
- Can snipe from air while avoiding ground-only units.
- Needs chaff/ground pressure so enemy AA does not focus it freely.
- Jump/Shield/Range/EMP-type techs can make it a carry depending on patch.

Good into:

- Crawler-protected anti-ground comps, Melting Point, Steel Ball, Hacker, Sledgehammer, Scorpion, War Factory if AA is weak.

Countered by:

- Marksman, Mustang, Farseer, Typhoon, Overlord, Fortress AA, Wraith, War Factory AM/AA interactions, and enemy Phoenix mirror.

LLM heuristic: Phoenix is a strong answer to ground-only anti-heavy. It still loses if enemy AA is layered and protected.

### 7.31 Raiden

Role: 400-cost air unit with heavy damage/control identity.

How to use:

- Use as a high-value air carry/support when enemy AA is not ready.
- Energy Shield became cheaper in Season 8 notes, making defensive builds more attractive.
- Pairs with Typhoon or other frontline that forces AA to split.
- Needs protection from Marksman/Phoenix/Farseer/Mustang/Typhoon.

Good into:

- Ground-heavy boards and comps that lack high-quality AA/range.

Countered by:

- Dedicated AA, long-range anti-air, missile interception if relevant, EMP/anti-air marker, and heavy range control.

LLM heuristic: Raiden is a high-investment air option; only recommend when it changes the damage race or punishes missing AA.

### 7.32 Wasp

Role: 200-cost light air swarm/chaff/DPS unit.

How to use:

- Punishes ground-only units and weak AA.
- Excellent flank and tower-pressure threat.
- Can serve as flying chaff against ground-only DPS.
- Needs to avoid Mustangs/Typhoon/Farseer/Marksman and other AA.
- Shield/range/swarm techs can create huge pressure if opponent lacks correct response.

Good into:

- Ground-only boards, Melting Point, Fortress without AA, Steel Ball, Rhino/Sledge if unsupported, tower pressure setups.

Countered by:

- Mustangs, Typhoon, Marksman, Farseer, Arclight AA, Fortress AA, Wraith, Phoenix, Overlord, and splash AA.

LLM heuristic: Wasps are powerful when they force an unlock/tech response. If enemy already has efficient AA, do not overcommit.

### 7.33 Wraith

Role: 300-cost air chaff-clear / multi-gun unit.

How to use:

- Clears Crawlers/Fangs/Wasps and punishes light swarms from air.
- Targeting tries to use multiple guns on multiple targets when possible.
- Good in compositions that need air-based chaff clear and tower pressure.
- Vulnerable to long-range anti-air and high single-target AA.

Good into:

- Crawlers, Fangs, Sledgehammer/Steel Ball support lines, Wasps, light boards.

Countered by:

- Overlord, Phoenix, Melting Point in some contexts, Marksman, Farseer, Typhoon, Mustang, War Factory/AM/AA depending on tech.

LLM heuristic: Wraith is good when enemy light units are the bottleneck. It is not a pure anti-giant solution.

---

## 8. Common composition archetypes

### 8.1 Arclight + Marksman + Stormcaller standard

Core idea:

- Arclights clear ground chaff.
- Marksmen kill high-value units and air.
- Stormcallers punish clumps/backline.
- Crawlers/Fangs protect all of it.

Weaknesses:

- Flanks and fast melee if poorly defended.
- Missile interception if too Stormcaller-dependent.
- Air if Marksmen are distracted or insufficient.
- Strong shields/giants if no Melting Point/Hacker/Scorpion.

### 8.2 Crawler + Steel Ball + Wraith / Phoenix aggro

Core idea:

- Crawlers pull shots and create waves.
- Steel Balls/Rhinos/fast ground threaten high-value targets.
- Wraith/Phoenix adds air pressure and chaff clear.

Weaknesses:

- Strong Fire Badger/Vulcan/Typhoon/Tarantula chaff clear.
- Good AA if air portion is central.
- EMP/Stormcaller if clumped.

### 8.3 Fortress shield standard

Core idea:

- Fortress anchors frontline and provides Barrier.
- Backline DPS works behind shield.
- Chaff protects Fortress from Melting Point/Steel Ball/Hacker target access.

Weaknesses:

- Melting Point + chaff clear.
- Hacker if Fortress can be isolated.
- Scorpion/EMP/acid/Death Knell.
- Overinvestment into one shield cluster can lose to flanks.

### 8.4 Melting Point anti-giant core

Core idea:

- Melting Point kills expensive durable units.
- Needs Arclight/Vulcan/Fire Badger/Typhoon/etc. to clear chaff.
- Needs AA and flank defense.

Weaknesses:

- Crawlers/Fangs/Wasps.
- Phoenix/Marksman/Stormcaller.
- Hacker/EMP if protected poorly.

### 8.5 Air punish

Core idea:

- Use Wasps/Phoenix/Overlord/Phantom Ray/Raiden/Wraith/Abyss when enemy anti-air is late or bad.
- Combine with tower pressure and chaff to force targeting errors.

Weaknesses:

- Mustangs/Marksmen/Farseer/Typhoon/Fortress AA.
- Overcommitting into AA after enemy responds.
- Missile interception if air uses interceptable missiles.

### 8.6 Hacker control composition

Core idea:

- Heavy chaff clear plus Hacker converts enemy expensive ground units.
- Works best when enemy board is few high-value ground units and weak chaff layering.

Weaknesses:

- Air, chaff, fast flanks, artillery, long-range snipe.
- Hacker that never completes hack is wasted supply.

### 8.7 Stormcaller artillery composition

Core idea:

- Punish static, clumped, range-dependent enemies.
- EMP missile tech can disable protective tech.

Weaknesses:

- AM devices/Mustang/War Factory.
- Spread formations.
- Fast/flank pressure.
- Air if no AA.

### 8.8 War Factory late-game inevitability

Core idea:

- War Factory provides production and/or missile interception.
- Great if the game goes long and enemy relies on missiles or static DPS.

Weaknesses:

- Melting Point/Scorpion/Hacker and focused anti-giant.
- Being too slow when enemy can kill towers/HP quickly.

---

## 9. Board-state analysis algorithm for the LLM

When given a replay-derived state, analyze in this exact order:

### Step 1: Identify both players’ win conditions

For each side, list:

- main DPS/carry;
- chaff package;
- chaff clear package;
- anti-air package;
- anti-giant package;
- support/shields/EMP/AM;
- flank/tower pressure;
- current tech commitments.

### Step 2: Identify failure points

Ask:

- Which units are shooting bad targets?
- Is the carry protected by enough chaff?
- Is chaff arriving in waves or all dying at once?
- Is there enough chaff clear before single-target DPS engages?
- Is enemy air uncontested?
- Are enemy giants uncontested?
- Is artillery being intercepted or allowed to land?
- Are flanks defended cheaply?
- Is any high-level unit feeding too much XP?

### Step 3: Find cheapest sufficient fix

Prefer low-cost tactical fixes before expensive pivots:

1. Use legal positioning: place new units correctly, adjust orientation/pathing if allowed, use flanks/beacon if available. Do not assume existing units can be moved.
2. Add chaff or delayed chaff.
3. Add one efficient counter unit.
4. Add tech to existing multiple squads.
5. Unlock new unit if existing roster cannot solve issue.
6. Add giant/titan only if it creates a new win condition.

Important movement constraint:
In Mechabellum, deployed units are normally fixed after placement. The LLM must not recommend moving or repositioning existing units unless the current game state includes a valid repositioning ability, card, item, specialist effect, mobile beacon/pathing option, or another explicit mechanic that allows it.

When no such ability exists, "positioning advice" may only apply to:
- newly purchased units;
- flanking deployments;
- unit orientation if still allowed during placement;
- mobile beacon/pathing if available;
- future purchases;
- selling/rebuying only if economically justified and legally possible.

### Step 4: Check counter-counter

Before recommending a move, predict opponent’s likely response.

Examples:

- If you add Wasps, opponent may add Mustangs/Marksman/Typhoon.
- If you add Melting Point, opponent may add Crawlers/Phoenix/Stormcaller.
- If you add Stormcaller, opponent may add AM/War Factory or spread.
- If you add Fortress, opponent may add Melting Point/Hacker/Scorpion.
- If you add Hacker, opponent may add air/chaff/flanks.

### Step 5: Recommend a specific action plan

State the most important fix first. Cover: what to buy or tech, where to place it, and what it solves. Include the most likely opponent counter and how to stay ahead of it.

---

## 10. Decision heuristics for common situations

### 10.1 “I am losing because enemy has too much chaff”

Do not add more single-target DPS. Add chaff clear:

- ground chaff: Arclight, Fire Badger, Vulcan, Tarantula, Typhoon, Sledgehammer, Stormcaller if clumped;
- air chaff/Wasps: Mustang, Typhoon, Marksman AA, Farseer AA, Wraith, Fortress AA;
- late chaff waves: add delayed Fangs or spread chaff clear deeper.

### 10.2 “I am losing because my DPS shoots Crawlers”

Fix target access:

- Add/tech Arclight/Fire Badger/Vulcan/Typhoon/Tarantula.
- Add your own chaff to delay enemy chaff clear.
- Move single-target DPS further/sideways so chaff clear engages first.
- Avoid buying more Marksmen/Melting Points until the chaff issue is solved.

### 10.3 “Enemy has Fortress/Vulcan/War Factory/Mountain/Death Knell”

Possible plan:

- Add Melting Point or Death Knell.
- Add Steel Ball or Scorpion if target access is good.
- Add Hacker if chaff can be cleared.
- Add EMP/acid/fire to disable/suppress sustain/shield.
- Add chaff to protect anti-giant DPS.

### 10.4 “Enemy has too much air”

Possible plan:

- Mustangs for light air/Wasps and general AA.
- Marksmen with Aerial Specialization for long-range air single-target.
- Farseer/Typhoon for supportive AA.
- Fortress AA Barrage if already using Fortress.
- Phoenix/Overlord mirror if range/tempo is favorable.
- Do not rely on ground-only units to solve air.

### 10.5 “Enemy Stormcallers are killing everything”

Possible plan:

- Spread formation; avoid vertical clumps.
- Use Mustangs/War Factory/Missile Interceptor for AM.
- Add fast flank/Crawlers/Rhino/Phoenix to pull or kill Stormcallers.
- Use shields if timed/positioned properly.
- Use your own Stormcaller/Overlord/air pressure if they have no answer.

### 10.6 “Enemy Hacker is converting my units”

Possible plan:

- Add chaff in front of hack targets.
- Add air damage or long-range snipe.
- Add artillery/Stormcaller pressure if Hacker is static.
- Reposition high-value ground units away from Hacker line.
- EMP or kill Hacker before control completes.

### 10.7 “Enemy flanks are killing towers”

Possible plan:

- Defend with minimal units: Fangs, Crawlers, Arclight, Mustang, Marksman, or relevant AA.
- Do not overdefend if the flank is bait.
- Use your own counterflank only if it forces more supply than it costs.
- Watch mobile beacon paths and air flanks.

### 10.8 “I have supply but no obvious move”

Prioritize:

1. Patch missing AA/anti-giant/anti-chaff.
2. Add chaff wave depth.
3. Add tech to unit type with multiple squads and clear role.
4. Prepare counter to opponent’s likely next pivot.
5. Avoid random expensive units that do not solve a board problem.

---

## 11. Compact counter matrix

This is a practical heuristic matrix, not a deterministic simulator.

| Enemy threat | Primary answers | Important caveat |
|---|---|---|
| Crawlers | Arclight, Fire Badger, Vulcan, Tarantula, Typhoon, Wraith, Stormcaller if clumped | Add depth; one front clear may not handle waves |
| Fangs | Arclight, Mustang, Vulcan, Typhoon, Tarantula, Stormcaller | Shield/range Fangs can survive longer |
| Wasps | Mustang, Typhoon, Marksman AA, Farseer AA, Wraith, Fortress AA | Do not overinvest if Wasps are only distraction |
| Marksman | Crawlers/Fangs, Stormcaller, flanks, Rhino, Phoenix if AA weak | Needs target denial more than raw tanking |
| Phoenix | Marksman, Mustang, Farseer, Typhoon, Overlord/Phoenix mirror | Protect AA from chaff |
| Stormcaller | AM, spread, flanks, fast units, air pressure, shields | AM can be baited; interception efficiency changes over time |
| Melting Point | Crawlers/Fangs/Wasps, Marksman, Phoenix, Stormcaller, Hacker, EMP | Do not feed it big isolated targets |
| Fortress | Melting Point, Hacker, Steel Ball, Scorpion, EMP/acid, air | Clear Fortress chaff first |
| Vulcan | Melting Point, Steel Ball, Scorpion, Hacker, Phoenix/Marksman, Overlord | Do not fight Vulcan with pure ground chaff |
| Hacker | Chaff, air, long-range snipe, Stormcaller/Scorpion, flanks | Hacker is useless if it cannot reach a valuable target |
| Steel Ball | Crawlers/Fangs, Hacker, Phoenix, Overlord, Stormcaller, Scorpion | Prevent it from connecting to giants/carries |
| Rhino | Chaff, Melting Point/Steel Ball/Marksman, Hacker, Fortress, Scorpion | Watch tower pressure and mobile beacon |
| War Factory | Melting Point, Scorpion, Hacker, focused anti-giant DPS | It may be bought mainly for AM/production, not direct DPS |
| Overlord | Marksman, Phoenix, Mustang, Farseer, Typhoon, Fortress AA, AM | Aggressive Overlords punish weak tower defense |
| Wraith | Marksman, Phoenix, Overlord, Mustang/Typhoon, Farseer | Wraith clears chaff; protect your AA from chaff |
| Death Knell/Mountain/Abyss | Melting Point/Death Knell, EMP, Hacker, strong AA/anti-titan, chaff manipulation | Titans require a full plan, not one unit |

---

## 12. Strategic dos and don’ts

### Do

- Add chaff in layers.
- Check air every round.
- Check anti-giant every round after midgame.
- Use tech when multiple units benefit or it changes a key interaction.
- Use flanks to force inefficient defense.
- Consider missile interception before committing to Stormcallers/Overlords/Farseer missile plans.
- Preserve high-level units and avoid feeding XP.
- Think in counter-counter chains.

### Don’t

- Do not buy expensive giants when the enemy already has unanswered Melting Point/Hacker/Scorpion.
- Do not add more single-target DPS if chaff is the problem.
- Do not add Stormcallers into heavy AM without another reason.
- Do not overdefend a weak flank with too much supply.
- Do not assume a unit counter works if it cannot reach the correct target.
- Do not ignore orientation/spread against artillery.
- Do not treat old unit guides as authoritative after a major patch.

---

## 13. Known patch-sensitive topics

The following should be checked against live game data before using exact values:

- Typhoon after Update 1.11 / Season 8 remake.
- Vortex starter-pack inclusion and tech values.
- Hacker preparation/control timings.
- Mustang Culling Rounds cost.
- Hound Chamber Compression value.
- Arclight Shockwave value.
- Scorpion Acid Attack / Convergent Fire values.
- Farseer / Overlord / Battlefield Power Photon Emission startup.
- Reinforcement card rules, skip button, and unit drop supply option.
- Anomalies in Dimensional Rift, especially Battlefield Power Research and Experimental Death Knell.

---

## 14. Source notes for future refresh

Recommended source hierarchy:

1. **Live game files / extracted game configs**: best source for numeric unit IDs, tech IDs, exact stats, and replay mapping.
2. **Official Steam news / patch notes**: best public source for latest changes.
3. **Mechabellum Wiki / mbxmas wiki**: good for unit pages, mechanics, costs, tech lists, glossary.
4. **MechaMonarch guides/counter list**: useful high-MMR community heuristics and counter relationships.
5. **Steam guides / Reddit / YouTube**: useful for meta and examples, but should be treated as opinion and patch-sensitive.

Key public URLs used during preparation:

- https://store.steampowered.com/app/669330/Mechabellum/
- https://steamcommunity.com/app/669330/allnews/
- https://wiki.mbxmas.com/units/
- https://wiki.mbxmas.com/glossary/
- https://wiki.mbxmas.com/mechanics/buffs-debuffs-items/
- https://wiki.mbxmas.com/mechanics/experience/
- https://wiki.mbxmas.com/mechanics/flanks/
- https://wiki.mbxmas.com/mechanics/missile-interception/
- https://wiki.mbxmas.com/mechanics/mobile-beacon/
- https://wiki.mbxmas.com/mechanics/targeting/
- https://wiki.mbxmas.com/mechanics/unit-orientation/
- https://wiki.mbxmas.com/mechanics/unit-reinforcements/
- https://mechamonarch.com/unit/
- https://mechamonarch.com/guide/mechabellum-counters/

---

## 15. Final instruction to LLM using this file

When analyzing Mechabellum, always reason from mechanics and board state first. A unit is only a counter if:

1. it targets the right layer of the enemy army;
2. it survives long enough to perform its role;
3. it is not neutralized by chaff, range, air, EMP, shields, missile interception, flanks, or tech;
4. it does not open an even easier counter for the opponent;
5. it fits the player’s existing economy and composition.

The best recommendation is usually a small set of coordinated changes: one purchase, one tech, and one positioning adjustment.
