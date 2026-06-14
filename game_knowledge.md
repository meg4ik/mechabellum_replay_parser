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

## 6. Economy reference: unit prices, unlock costs, specialist cost effects, and unit technologies

This section is intended for machine reasoning. Treat all exact numeric values as `PATCH-SENSITIVE` and prefer live game config/replay mappings when available.


### 6.1 Supply income and round-by-round budget model

This is the missing economy block the LLM must use before recommending purchases, unlocks, techs, buildings, cards, devices, or sell/rebuy lines.

#### 6.1.1 Base income rule

For standard 1v1 reasoning, assume base income during the deployment phase of UI round `R` is:

```text
base_income(R) = 200 * R
```

Round-by-round base income:

| UI round | Base income this round | Cumulative base income if nothing is spent |
|---:|---:|---:|
| 1 | 200 | 200 |
| 2 | 400 | 600 |
| 3 | 600 | 1,200 |
| 4 | 800 | 2,000 |
| 5 | 1,000 | 3,000 |
| 6 | 1,200 | 4,200 |
| 7 | 1,400 | 5,600 |
| 8 | 1,600 | 7,200 |
| 9 | 1,800 | 9,000 |
| 10 | 2,000 | 11,000 |
| 11 | 2,200 | 13,200 |
| 12 | 2,400 | 15,600 |
| 13 | 2,600 | 18,200 |
| 14 | 2,800 | 21,000 |
| 15 | 3,000 | 24,000 |

Cumulative base income through round `R` is:

```text
cumulative_base_income(R) = 100 * R * (R + 1)
```

Important: base income is symmetrical. Winning a round, losing a round, or destroying a tower does not directly change the base supply income. Those events matter through HP damage, tower debuffs, tempo, XP, board position, and unit survival — not through automatic win/loss income.

#### 6.1.2 Carryover rule

Unspent supply carries over to later rounds. The LLM must never assume the player starts each round with only the base income for that round.

Use this budget equation:

```text
available_supply_at_start_of_deployment(R)
  = carried_supply_from_previous_round
  + base_income(R)
  + persistent_income_modifiers(R)
  + one_time_income_this_round(R)
  + refunds_or_sells_this_round(R)
  - debt_or_delayed_penalties_this_round(R)
  - mandatory/preselected costs already paid this round
```

Then subtract proposed actions:

```text
remaining_supply_after_plan
  = available_supply
  - unlock_costs
  - unit_purchase_costs
  - tech_costs
  - building/device/card costs
  - rank recruitment premiums
  - other state-specific costs
```

LLM rule: a recommendation is invalid if `remaining_supply_after_plan < 0`, unless it explicitly says the plan requires Rapid Resupply/loan, a refund/sell, or another legal source of immediate supply.

#### 6.1.4 Regular card economy

Cards/reinforcement choices start appearing from round 2. Skipping a normal card grants supply, commonly treated as +50 supply. Therefore, every chosen card has an opportunity cost: even a `FREE` card can effectively cost the skipped-card supply.

LLM card-economy rules:

- If a card is skipped, add skip supply to the current round's budget.
- If a card is chosen, subtract its visible cost and also consider the lost skip value as opportunity cost when evaluating long-term efficiency.
- Do not evaluate economy cards only by their visible price. Compare against the skip value and the expected number of remaining rounds.
- In early rounds, 50 supply is strategically large because it can decide whether a player can buy a chaff unit, unlock, tech, or defend a flank.

Common economy cards / card-like effects to model:

| Card/effect | Budget effect | Timing | LLM note |
|---|---:|---|---|
| Skip normal card | +50 supply | Current round | Often correct early if offered cards do not solve the board. |
| Supply Specialist card | +50 supply per round | Persistent after purchase | Different from starting Supply Specialist, but same income shape. Include card cost and skip opportunity cost. |
| Top/Super Supply-type card | +150 supply per round | Usually starts next round | Long-term scaling. Bad if the game is likely to end before it pays back. |
| Tech Specialist / Efficient Tech Research | Reduces tech upgrade costs | Persistent or card-defined | Not income, but improves affordability of tech-heavy plans. Apply before tech-cost checks. |
| Junior Recruitment / Efficient Light Manufacturing | Reduces non-giant/light unit recruitment costs | Persistent or card-defined | Not income, but can make mass low-cost units economically correct. Apply to affected unit purchases only. |
| Senior Manufacturing / Efficient Giant Manufacturing | Reduces giant unit recruitment costs | Persistent or stack-based/card-defined | Not income, but changes giant timing. Apply to Fortress/Melting Point/Raiden/Sandworm/Vulcan/Overlord and titans only if current card text says so. |
| Subsidized unit cards | Reduces one unit's recruitment or upgrade cost | Persistent or card-defined | Track exact affected unit and whether it affects recruitment, unlock, tech, or upgrade EXP. Do not generalize. |
| Additional Deployment Slot / Deployment Specialist card | More units can be bought this round or every round | Capacity, not income | Prevents floating money when deploy slots are the bottleneck. |

PATCH-SENSITIVE: card names and exact values can change. If replay parser can extract card ID/text, use that over these generic descriptions.

#### 6.1.5 Unit reinforcement / unit drop economy

Unit reinforcement offers happen in scheduled windows and can create hidden economic value because the offered unit is free and also unlocks that unit type. In recent Season 8 notes, Unit Reinforcement gained a skip button whose supply reward increases with later rounds; exact skip values should be read from live game data or replay if available.

LLM rules:

- A free unit is not the same as cash, but it can be converted into tempo, unlock value, board value, or sometimes refund value if selling is legal.
- If a reinforcement unit is taken, model it as: `+free_unit_body + unit_unlocked`, not as immediate supply.
- If a reinforcement is skipped, add the exact skip reward if known. If unknown, mark as `unknown_unit_drop_skip_supply` instead of guessing.
- A unit already deployed or already unlocked may be blocked from future offers depending on the current reinforcement rules; use the parsed state.
- Cost-altering cards can block or modify offers; do not assume every unit is eligible for a future drop.

#### 6.1.6 Command Center and Research Center economy effects

Core building powers can directly change the budget or enable refunds:

| Source | Cost / effect | Timing | LLM note |
|---|---|---|---|
| Command Center: Rapid Resupply | Cost 0; immediately gain +200 supply; get -300 supply next round | Current round loan, next round penalty | This is a tempo loan, not free income. Recommend only if the immediate swing is worth being down 300 next round. |
| Command Center: Mass Recruitment | Cost 50; +1 purchasable unit this round | Current round | Capacity increase. Useful when money is high but deploy slots are limiting. |
| Command Center: Elite Recruitment | Cost 100; units bought this round have +1 rank | Current round | Rank premium/tempo tool. Check actual affordability of higher-rank units. |
| Research Center: Field Recovery | Cost 100 to unlock; then can destroy a friendly squad and refund invested supply | Current/future deployment phases | This is the legal sell/refund mechanism. It can convert misplaced or obsolete units/items into supply, but costs an unlock and deletes board value. |
| Research Center: Attack/Defense Enhancement | Costs supply for permanent stat buffs | Permanent | Not income, but common sink for excess cash. Compare to units/tech. |

LLM Rapid Resupply rule: if using Rapid Resupply this round, the next-round budget must include `-300 delayed_penalty`. Never describe it as “free 200”.

#### 6.1.7 Starting specialist economy modifiers

Apply starting specialist effects before normal purchases. Some are direct income; others are cost reduction or free assets.

| Starting specialist | Economy effect to apply | Timing | Direct cash? |
|---|---|---|---|
| Supply Specialist | +50 supply every round | Every round | Yes |
| Cost Control Specialist | +100 supply every round | Every round | Yes, with -11% ATK/HP penalty to all units |
| Quick Supply Specialist | +200 supply in round 1 | Round 1 only | Yes |
| Elite Specialist | +100 supply in round 1; can immediately recruit Rank 2 units | Round 1 and ongoing rank access | Partly; rank access changes costs |
| Training Specialist | +50 supply in round 1; free Intensive Training | Round 1 | Partly |
| Giant Specialist | Giant/Titan unlock cost -200 | When unlocking eligible units | Cost reduction, not income |
| Aerial Specialist | Aerial unit unlock cost -200; aerial units gain stats | When unlocking eligible air units | Cost reduction, not income |
| Sabertooth Specialist | Sabertooth tech costs -50; free Rank 1 Sabertooth on round 3 | Round 3 and tech purchases | Free unit / discount |
| Fire Badger Specialist | Fire Badger tech costs -50; free Rank 1 Fire Badger on round 3 | Round 3 and tech purchases | Free unit / discount |
| Marksman Specialist | Free Rank 3 Marksman on round 2 | Round 2 | Free unit |
| Rhino Specialist | Free Rank 2 Rhino on round 4 | Round 4 | Free unit |
| Typhoon Specialist | Free Rank 1 Typhoon on round 4 | Round 4 | Free unit |
| Amplify Specialist | Free Small Amplifying Cores on round 1 | Round 1 | Free items, not cash |
| Missile Specialist | Free Missile Strikes on round 2 | Round 2 | Free powers, not cash |

LLM rule: direct income and discounts are different. A discount can make a purchase affordable only if the player is buying that affected thing. A free unit creates board value but does not help pay for an unrelated tech unless it is legally sold/refunded.

#### 6.1.8 Economic break-even heuristics

When evaluating an economy choice, compute the payback round.

```text
net_cost = visible_cost + skipped_card_opportunity_cost
payback_rounds = ceil(net_cost / income_gain_per_round)
```

Examples:

- A +50/round card with visible cost 50 has effective early opportunity cost around 100 if skipping would give +50. It pays back slowly unless taken early.
- A +150/round card with visible cost 200 has effective opportunity cost around 250 if skipping would give +50. It needs roughly 2 rounds to recover nominal cost, but usually 3 rounds to feel clearly profitable after tempo loss.
- A -50/unit manufacturing card pays back after enough affected units are purchased. If it affects 4 future units, it is worth about 200 supply minus its cost/opportunity cost.
- A tech discount card pays back only if the player will buy enough techs. If it reduces tech by 50 and costs 50 plus a 50 skip opportunity, it needs about two relevant tech purchases to break even.

LLM rule: economy cards are strongest when:

1. taken early;
2. the game is likely to last multiple more rounds;
3. the current board can survive the tempo loss;
4. the player has enough deployment slots and tech/unit sinks to actually spend the extra supply.

#### 6.1.9 Budget validation checklist for every LLM recommendation

Before giving an action plan, the LLM must answer internally:

1. What is the current UI round?
2. What is the player’s actual available supply from replay, if present?
3. If not present, what is the reconstructed budget using carryover + income?
4. Which specialist/card modifiers apply this round?
5. Are any delayed penalties active next round, especially Rapid Resupply?
6. Are proposed units already unlocked? If not, include unlock cost.
7. Do proposed units have modified recruitment cost from cards/specialists?
8. Do proposed techs have modified tech cost from specialist/cards?
9. Is the player limited by deployment slots rather than supply?
10. After all costs, is the plan affordable?

### 6.2 Default unit purchase costs

The public wiki groups the current roster by supply purchase cost as follows:

| Purchase cost | Units |
|---:|---|
| 100 | Arclight, Crawler, Fang, Hound, Marksman, Void Eye, Vortex |
| 200 | Fire Badger, Hacker, Mustang, Phantom Ray, Phoenix, Rhino, Sabertooth, Sledgehammer, Steel Ball, Stormcaller, Tarantula, Wasp |
| 300 | Farseer, Scorpion, Typhoon, Wraith |
| 400 | Fortress, Melting Point, Raiden, Sandworm, Vulcan |
| 500 | Overlord |
| 800 | Abyss, Death Knell, Mountain, War Factory |

### 6.3 Unit unlock costs and upgrade EXP

| Unit | Buy cost | Unlock cost | Upgrade EXP | Notes |
|---|---:|---:|---:|---|
| Arclight | 100 | 0 | 750 | Ground chaff clear. |
| Crawler | 100 | 0 | 450 | Fast melee chaff. |
| Fang | 100 | 0 | 600 | Cheap ranged chaff / light AA. |
| Hound | 100 | 0 | 750 | Fast bruiser/chaff-clear hybrid. |
| Marksman | 100 | 0 | 650 | Long-range single-target DPS. |
| Void Eye | 100 | 0 | 650 | 100-cost specialist ranged unit; patch-sensitive. |
| Vortex | 100 | 0 | 700 | 100-cost support/DPS unit; patch-sensitive. |
| Fire Badger | 200 | 0 | 1400 | Fire-based chaff clear. |
| Hacker | 200 | 100 | 560 | Ground-unit control / shields. |
| Mustang | 200 | 0 | 1200 | Anti-air and light clear. |
| Phantom Ray | 200 | 50 | 1000 | Flying missile/burst unit. |
| Phoenix | 200 | 50 | 1300 | Flying sniper. |
| Rhino | 200 | 50 | 1150 | Fast melee bruiser. |
| Sabertooth | 200 | 0 | 1300 | Medium ranged tank / anti-medium. |
| Sledgehammer | 200 | 0 | 1300 | Medium tank line. |
| Steel Ball | 200 | 0 | 1000 | Scaling anti-heavy beam/laser unit. |
| Stormcaller | 200 | 50 | 1100 | Long-range artillery. |
| Tarantula | 200 | 0 | 1500 | Ground anti-swarm bruiser. |
| Wasp | 200 | 50 | 900 | Flying light swarm. |
| Farseer | 300 | 50 | 1800 | Missile support / AA / range utility. |
| Scorpion | 300 | 50 | 1500 | Heavy ranged artillery/anti-medium. |
| Typhoon | 300 | 50 | 1950 | 300-cost ranged unit; current version is patch-sensitive. |
| Wraith | 300 | 50 | 2250 | Flying AoE/support cruiser. |
| Fortress | 400 | 200 | 1600 | Ground giant anchor. |
| Melting Point | 400 | 200 | 1400 | Anti-giant beam DPS. |
| Raiden | 400 | 200 | 2400 | Flying giant multi-target lightning. |
| Sandworm | 400 | 200 | 2000 | Burrowing melee giant. |
| Vulcan | 400 | 200 | 2200 | Giant anti-swarm flame unit. |
| Overlord | 500 | 200 | 1750 | Long-range flying giant. |
| Abyss | 800 | 350 | 4800 | Flying titan laser sweeper. |
| Death Knell | 800 | 350 | 3200 | Ranged titan with multi-direction ramping beams. |
| Mountain | 800 | 350 | 3200 | Ground titan with huge HP/DPS. |
| War Factory | 800 | 350 | 3200 | Titan mobile factory. |

### 6.4 Specialist economy and cost modifiers

The LLM must apply these before evaluating affordability. These are not always direct unit-price changes; many specialists give free units, supply, unlock discounts, or tech discounts.

| Specialist | Economy / cost effect | Combat/stat effect | HP modifier | Strategic implication |
|---|---|---|---:|---|
| Giant Specialist | Giant and Titan unlock costs reduced by 200. | None listed. | +100 | Earlier giants/titans; can use unlocks to block giant unit reinforcements. |
| Aerial Specialist | Aerial unit unlock costs reduced by 200. | Aerial units gain +13% ATK and +13% HP. | +400 | Enables early air unlocks and stronger air-based scaling. |
| Speed Specialist | No direct supply/cost change. | All units gain +3 movement speed. | +300 | Tempo/aggression specialist; speed can be good or harmful depending on targeting. |
| Marksman Specialist | Free Rank 3 Marksman on round 2. | None listed. | -200 | Strong round-2 tempo but can feed XP if exposed. |
| Elite Specialist | +100 supplies in round 1; can immediately recruit Rank 2 units. | Rank-2 access can create early tempo. | +500 | Do not assume Rank 2 purchases have base cost; live game cost formula should be read from game state/config. |
| Rhino Specialist | Free Rank 2 Rhino on round 4. | None listed. | -300 | Round-4 power spike; can also be sold for a supply injection if not useful. |
| Cost Control Specialist | +100 supplies every round. | All units suffer -11% ATK and -11% HP. | +100 | Economic scaling at permanent stat penalty; favors stat-agnostic tech/powers. |
| Fortified Specialist | No direct supply/cost change. | All units gain +17% HP. | +300 | More value on HP breakpoints and durable starts. |
| Sabertooth Specialist | Sabertooth tech upgrade costs reduced by 50; free Rank 1 Sabertooth on round 3. | None listed. | 0 | Build around Sabertooth only if it will actually affect tempo or scaling. |
| Fire Badger Specialist | Fire Badger tech upgrade costs reduced by 50; free Rank 1 Fire Badger on round 3. | None listed. | 0 | Best if the board can exploit another Badger and cheaper Badger tech. |
| Typhoon Specialist | Free Rank 1 Typhoon on round 4. | None listed. | -300 | Delayed 300-supply tempo spike; weak before round 4. |
| Supply Specialist | +50 supplies every round. | None listed. | -600 | Flexible economy, but lower starting HP makes early damage dangerous. |
| Quick Supply Specialist | +200 supplies in round 1. | None listed. | -500 | Round-1 tempo spike; little persistent economy afterward. |
| Missile Specialist | Two free Missile Strikes on round 2. | None listed. | +100 | Temporary tempo/punish tool; not a permanent economy engine. |
| Amplify Specialist | Three free Small Amplifying Cores on round 1. | Equipment stats depend on the item. | +500 | Best on early durable units that use both HP and damage. |
| Training Specialist | +50 supplies in round 1 and one free Intensive Training. | Enables early level/EXP pressure. | +300 | Valuable with aggressive units that convert early levels into tempo. |

LLM affordability rule: when specialist is known, compute economy in this order: starting/round supply modifiers -> free units/items/powers -> unlock discounts -> tech discounts -> rank recruitment rules -> normal unit/tech costs. If the exact rank-recruit cost is not present in the parsed state, say it is unknown instead of guessing.

### 6.5 Legal movement / repositioning constraint

Critical rule for recommendations: existing deployed units are normally fixed after placement. Do **not** recommend moving/repositioning existing units unless the current state includes a legal movement mechanism such as Jump Drive, Mobile Beacon/pathing, a reposition card, a unit-specific movement ability, or another explicit mechanic.

Legal positioning advice may apply to:

- newly purchased units;
- flanking deployments;
- orientation/facing if still allowed;
- Mobile Beacon or other legal pathing tools;
- units with techs that explicitly allow redeployment, such as Phoenix Jump Drive, Wasp Jump Drive, or Overlord Jump Drive;
- selling/rebuying only when legal and economically justified.

### 6.6 Full unit technology catalog

Use this catalog to understand what each unit can become after tech. Costs are supply costs for researching that technology on that unit type. Descriptions are paraphrased for LLM reasoning, not copied as UI text.

#### 100-cost units

**Arclight**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Range Enhancement | 300 | +40 range; makes Arclight safer and more consistent as chaff clear. |
| Electromagnetic Shot | 400 | Hits apply EMP: disables tech and slows movement. |
| Charged Shot | 200 | Much higher attack damage, slower attack cycle; better into medium units, worse if overkill/chaff is the issue. |
| Armor Enhancement | 100 | More HP plus flat damage block that scales with rank. |
| Anti-Aircraft Ammunition | 300 | Allows Arclight to attack air. |
| Elite Marksman | 400 | Per-rank range and ATK scaling. |
| Shockwave | 200 | Shorter range but attacks create a small shockwave AoE near the target. |

**Crawler**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Mechanical Rage | 150 | Faster movement and shorter attack interval. |
| Replicate | 250 | Enemy kills can create more Crawlers, increasing swarm snowball. |
| Subterranean Blitz | 350 | Faster movement; burrows when not near enemies, reducing incoming damage while closing distance. |
| Acidic Explosion | 150 | On death leaves acid, punishing high-HP units and increasing damage taken by affected units. |
| Impact Drill | 150 | Large attack increase; improves Crawler damage when they actually connect. |
| Loose Formation | 250 | Less HP but wider spread, making AoE/chaff clear less efficient. |

**Fang**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Ignite | 150 | Attacks can burn targets for percentage HP damage and block healing. |
| Range Enhancement | 300 | +40 range; improves delayed chaff/AA contribution. |
| Mechanical Rage | 300 | Faster movement and much faster attack cycle. |
| Portable Shield | 500 | Each Fang gains a personal shield; strong defensive chaff tech. |
| Armor-Piercing Bullets | 100 | Higher ATK; makes high-level Fangs real DPS. |
| Grenade Launcher | 150 | Adds ground splash and range, but removes air targeting. |

**Hound**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Mechanical Rage | 300 | Faster movement and shorter attack interval. |
| Range Enhancement | 300 | +40 range. |
| Fire Extinguisher | 200 | Clears fire, acid and smoke zones near Hounds; useful support into ground effects. |
| Incendiary Bomb | 200 | Periodically launches ground-fire bombs at long range. |
| Armor Enhancement | 250 | More HP plus flat damage block scaling with rank. |
| Chamber Compression | 200 | Attack charges up over time, then resets after attacking; rewards timing and target access. |

**Marksman**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Doubleshot | 250 | Fires two shots per attack with reload penalty; improves burst. |
| Range Enhancement | 300 | +40 range; key backline scaling tech. |
| Quick Reload | 250 | Faster attacks but lower damage; better into medium/light targets than pure giants. |
| Electromagnetic Shot | 250 | Applies EMP on hit. |
| Elite Marksman | 400 | Per-rank range and ATK scaling. |
| Shooting Squad | 300 | Summons Fangs at the start of combat. |
| Assault Mode | 150 | Converts Marksman into short-range durable AoE assault unit; extremely role-changing. |
| Aerial Specialization | 250 | Stronger and longer-ranged versus air targets. |

**Void Eye**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Range Enhancement | 300 | +40 range. |
| Energy Shield | 250 | Personal shield equal to HP; blocks at least one damage instance. |
| Charged Shot | 100 | Higher ATK with slower attack interval. |
| Aerial Mode | 200 | Converts to flying, enables air targeting, increases speed, lowers range. |
| Energy Absorption | 50 | More HP and lifesteal from damage dealt. |
| Suppression Shots | 100 | Longer range and reduces target range temporarily. |
| Electromagnetic Armor | 300 | Enemies attacking it receive EMP-like interference. |

**Vortex**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Range Enhancement | 300 | +40 range. |
| Mobile Power Station | 250 | Adds range and buffs nearby ground allies' ATK; non-stacking aura. |
| Electromagnetic Cloud | 400 | Attacks apply EMP in an area around the target. |
| Electromagnetic Twin | 400 | Spawns a fragile Vortex Mirage behind itself at battle start. |
| Accumulator Shield | 200 | Periodically deploys an AoE shield after enough attacks; shield scales with Vortex level. |
| Grid Integration | 200 | Linked nearby Vortex units gain ATK per additional link, up to a cap. |
| Emergency Armor | 100 | First time HP drops below half, becomes untargetable/damage-resistant for a short time. |
| Field Maintenance | 100 | More HP and self-regeneration after taking damage. |

#### 200-cost units

**Fire Badger**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Range Enhancement | 300 | +40 range. |
| Napalm | 300 | Less HP, but attacks create burning ground zones. |
| Ignite | 100 | Burns targets for percentage HP damage and prevents healing. |
| Field Maintenance | 150 | More HP and self-regeneration after damage. |
| Scorching Fire | 300 | Much higher ATK. |
| Scorching Charge | 200 | More HP; at low HP charges and detonates, igniting an area. |
| Counter-Fire | 200 | More HP; taking damage temporarily gives a large range boost. |

**Hacker**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Multi Control | 250 | Lower range, but splits control into multiple weaker beams. |
| Barrier | 400 | Deploys a shield dome; shield HP scales with rank. |
| Range Enhancement | 300 | +40 range. |
| Enhanced Control | 300 | Hacked units recover to full HP immediately. |
| Electromagnetic Interference | 100 | Control/hit applies EMP-style tech disable and movement slow. |

**Mustang**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Missile Interceptor | 200 | Intercepts missiles in a radius; efficiency decays under continuous load. |
| Range Enhancement | 300 | +40 range. |
| High-Explosive Ammo | 50 | Adds splash at the cost of lower ATK; improves chaff clear. |
| Aerial Specialization | 300 | Stronger and longer-ranged against air. |
| Armor-Piercing Bullets | 300 | Higher ATK. |
| Culling Rounds | 200 | Executes low-current-HP targets but lowers ATK; strong into swarms/finishers. |

**Phantom Ray**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Burst Mode | 200 | Fires a large missile burst with a much longer reload. |
| Range Enhancement | 300 | +40 range. |
| Armor Enhancement | 250 | More HP plus flat damage block scaling with rank. |
| Sticky Oil Bomb | 100 | Periodically launches slowing oil; fire can ignite oil. |
| Stealth Cloak | 100 | More ATK/HP and begins cloaked; revealed when attacking. |
| High-Explosive Ammo | 150 | Adds splash, lowers ATK. |
| Energy Shield | 400 | Personal HP-sized shield. |
| Ground Targeting | 150 | Longer ground range but lower ATK. |

**Phoenix**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Quantum Reassembly | 150 | Once destroyed, can rebuild near allied Phoenix after a delay. |
| Range Enhancement | 300 | +40 range. |
| Launcher Overload | 200 | Much faster attacks, shorter range. |
| Energy Shield | 200 | Personal HP-sized shield. |
| Jump Drive | 100 | Faster and can be freely redeployed during deployment. |
| Electromagnetic Shot | 200 | Applies EMP on hit. |
| Elite Marksman | 400 | Per-rank range and ATK scaling. |
| Charged Shot | 200 | Much higher ATK, shorter range. |

**Rhino**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Whirlwind | 250 | When surrounded, spins for sustained AoE melee damage. |
| Photon Coating | 300 | Temporary damage reduction and immunity to EMP, fire, acid and degeneration. |
| Field Maintenance | 200 | Self-regeneration after damage. |
| Final Blitz | 250 | Explodes on death, dealing max-HP-based area damage. |
| Mechanical Rage | 150 | Faster movement and shorter attack interval. |
| Wreckage Recycling | 100 | More ATK and heals on kill. |
| Power Armor | 300 | More HP and slow immunity. |
| Armor Enhancement | 200 | More HP plus flat block scaling with rank. |
| Combat Evolvement | 200 | Gains HP and ATK over time during battle. |

**Sabertooth**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Range Enhancement | 300 | +40 range. |
| Field Maintenance | 300 | More HP and self-regeneration. |
| Missile Interceptor | 150 | Local missile interception. |
| Doubleshot | 150 | Fires two shells with reload penalty. |
| Secondary Armament | 200 | Adds side guns with rank-scaling damage. |
| Field Entrenchment | 200 | Starts entrenched: cannot move, but gains HP/range/attack speed until it leaves. |

**Sledgehammer**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Field Maintenance | 200 | More HP and self-regeneration. |
| Damage Sharing | 200 | Nearby Sledgehammers chain, gain HP, and share damage. |
| Mechanical Rage | 250 | Faster movement and shorter attack interval. |
| Range Enhancement | 300 | +40 range. |
| Electromagnetic Shot | 350 | Applies EMP on hit. |
| Armor-Piercing Bullets | 200 | Much higher ATK with slower attack interval. |
| Armor Enhancement | 250 | More HP plus flat block scaling with rank. |

**Steel Ball**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Energy Absorption | 200 | More HP and lifesteal from damage. |
| Damage Sharing | 250 | Nearby Steel Balls chain, gain HP, and share damage. |
| Range Enhancement | 300 | +40 range. |
| Mechanical Division | 300 | On death, spawns Crawlers. |
| Armor Enhancement | 300 | More HP plus flat block scaling with rank. |
| Fortified Target Lock | 200 | On target switch, prioritizes the highest-HP enemy in range. |
| Kinetic Charge | 150 | Gains range based on distance traveled, up to a cap. |

**Stormcaller**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Incendiary Bomb | 350 | Shorter range, but missiles ignite ground zones. |
| Range Enhancement | 300 | +40 range. |
| Launcher Overload | 250 | Faster firing, shorter range, faster movement. |
| High-Explosive Ammo | 150 | Larger splash, lower ATK. |
| Electromagnetic Explosion | 300 | Missiles apply EMP on hit. |
| High Explosive Anti-tank Shells | 150 | Much higher ATK, slower attack cycle. |

**Tarantula**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Spider Mine | 300 | Periodically fires mines that explode for area damage; mine stats scale with rank. |
| Range Enhancement | 300 | +40 range. |
| Mechanical Rage | 400 | Faster movement and shorter attack interval. |
| Armor-Piercing Bullets | 150 | Higher ATK. |
| Field Maintenance | 150 | More HP and self-regeneration. |
| Armor Enhancement | 200 | More HP plus flat block scaling with rank. |
| Anti-Aircraft Ammunition | 150 | Allows Tarantula to attack air. |
| High-Explosive Ammo | 300 | Adds splash, lowers ATK. |

**Wasp**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Energy Shield | 300 | Personal HP-sized shield. |
| Range Enhancement | 300 | +40 range. |
| Jump Drive | 100 | Faster and can be freely redeployed during deployment. |
| Ground Specialization | 200 | Greatly higher ATK against ground. |
| Elite Marksman | 400 | Per-rank range and ATK scaling. |
| Ignite | 100 | Burns targets and blocks healing. |
| Electromagnetic Shot | 100 | Applies EMP on hit. |
| High-Explosive Ammo | 100 | Adds splash, lowers ATK. |
| Armor-Piercing Bullets | 100 | Higher ATK. |
| Aerial Specialization | 200 | Stronger and longer-ranged against air. |

#### 300-cost units

**Farseer**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Photon Emission | 400 | Temporarily protects nearby ground allies with damage reduction and status immunity. |
| Scanning Radar | 300 | Nearby allies gain range; aura does not stack. |
| Missile Interceptor | 200 | Local missile interception. |
| Electromagnetic Explosion | 150 | Applies EMP on missile hits. |
| Range Enhancement | 300 | +40 range. |
| Burst Mode | 200 | Fires a larger missile burst with much longer reload. |
| Aerial Specialization | 200 | Stronger and longer-ranged against air. |

**Scorpion**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Acid Attack | 300 | Attacks create acid zones that deal percentage HP damage and amplify incoming damage. |
| Siege Mode | 300 | Much longer range, lower ATK, longer attack interval, and minimum range limitation. |
| Range Enhancement | 300 | +40 range. |
| Doubleshot | 100 | Fires two shells with reload penalty. |
| Field Maintenance | 150 | More HP and self-regeneration. |
| Armor Enhancement | 100 | More HP plus flat block scaling with rank. |

**Typhoon**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Mechanical Rage | 300 | Faster movement and higher ATK. |
| Aerial Specialization | 250 | Stronger and longer-ranged against air. |
| Barrier | 400 | Deploys a shield dome; shield scales with rank. |
| Homing Missile | 300 | Periodically launches homing missiles at distant enemies; damage scales with level/rank. |

**Wraith**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Floating Artillery Array | 400 | Doubles the number of floating cannons. |
| Range Enhancement | 300 | +40 range. |
| Armor Enhancement | 200 | More HP plus flat block scaling with rank. |
| Degeneration Beam | 200 | Debuffs nearby enemies: movement, attack, and damage taken. |
| Field Maintenance | 200 | More HP and self-regeneration. |
| High-Explosive Ammo | 150 | Cannon splash increases, ATK decreases. |
| Land Cruiser | 300 | Converts to ground-only, with longer range but slower attacks and no air targeting. |

#### 400/500-cost giant units

**Fortress**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Barrier | 500 | Large shield dome; shield HP scales heavily with rank. |
| Range Enhancement | 300 | +40 range. |
| Anti-Air Barrage | 200 | Periodic anti-air missiles; useful but interceptable. |
| Fang Production | 300 | Periodically produces Fangs during battle. |
| Launcher Overload | 150 | Faster attacks, shorter range. |
| Elite Marksman | 150 | Per-rank range and ATK scaling. |
| Doubleshot | 100 | Fires two shells with reload penalty. |
| Armor Enhancement | 150 | More HP plus flat block scaling with rank. |
| Rocket Punch | 300 | Fires powerful fists at HP thresholds for high area burst. |
| Solid Shot | 200 | Longer range and slower attacks with smaller splash. |

**Melting Point**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Energy Absorption | 200 | More HP and lifesteal from damage dealt. |
| Range Enhancement | 300 | +40 range. |
| Energy Diffraction | 150 | Shorter range, but splits beam into multiple weaker rays. |
| Electromagnetic Barrage | 300 | Periodically launches EMP projectiles with heavy shield damage. |
| Crawler Production | 300 | Periodically produces Crawlers during battle. |
| Armor Enhancement | 100 | More HP plus flat block scaling with rank. |

**Raiden**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Fork | 250 | Shorter range, more lightning bolts per attack. |
| Chain | 200 | Shorter range, bolts can jump to nearby enemies for reduced damage. |
| Ionization | 100 | Greatly lowers ATK but adds percentage-current-HP damage. |
| Range Enhancement | 300 | +40 range. |
| Electromagnetic Shot | 300 | Applies EMP on hit. |

**Sandworm**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Mechanical Rage | 150 | Faster movement and shorter attack interval. |
| Armor Enhancement | 250 | More HP plus flat block scaling with rank. |
| Mechanical Division | 200 | On death, creates Larvas. |
| Anti-Aerial | 100 | Allows Sandworm to attack air with extra range. |
| Burrow Maintenance | 150 | More HP and rapid healing while burrowed. |
| Replicate | 250 | Creates Larvas whenever it emerges from the ground. |
| Sandstorm | 200 | Emerging creates a sandstorm that reduces range and ranged damage taken inside. |
| Strike | 150 | Emerges faster and empowers first attack after emergence. |

**Vulcan**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Ignite | 250 | Attacks ignite targets for percentage HP burn and healing prevention. |
| Range Enhancement | 300 | +40 range. |
| Incendiary Bomb | 300 | Periodically launches long-range fire bombs. |
| Scorching Fire | 300 | Higher ATK. |
| Best Partner | 250 | Summons a same-rank Marksman at battle start. |
| Sticky Oil Bomb | 200 | Periodically launches slowing oil bombs that can be ignited. |
| Armor Enhancement | 150 | More HP plus flat block scaling with rank. |

**Overlord**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Overlord Artillery | 300 | Adds ground-only cannons with rank-scaling damage. |
| Launcher Overload | 300 | Faster missile attacks, shorter range. |
| Mothership | 250 | Periodically produces Wasps. |
| Jump Drive | 300 | Faster and can be freely redeployed during deployment. |
| Photon Emission | 300 | Temporarily protects nearby allies with damage reduction and status immunity. |
| Range Enhancement | 300 | +40 range. |
| Armor Enhancement | 150 | More HP plus flat block scaling with rank. |
| Field Maintenance | 150 | More HP and self-regeneration. |
| High-Explosive Ammo | 200 | Larger missile splash, lower ATK. |

#### 800-cost titan units

**Abyss**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Range Enhancement | 500 | +40 range. |
| Dark Companion | 300 | Summons a same-rank Wraith at battle start. |
| Photon Coating | 300 | Temporary damage reduction and status immunity. |
| Disintegration | 350 | Periodically damages nearby ground enemies by percentage current HP and slows them. |
| Swarm Missiles | 500 | Periodically launches many missiles at nearby ground enemies; damage scales with rank. |
| Wreckage Recycling | 300 | Higher ATK and heals after kills. |
| Vertical Sweep | 350 | Higher ATK and changes beam sweep direction to vertical. |

**Death Knell**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Energy Diffraction | 500 | Shorter range, but fires many weaker rays. |
| Range Enhancement | 500 | +40 range. |
| Steel Ball Production | 450 | Periodically produces Steel Balls. |
| Barrier | 700 | Large shield dome with huge rank-scaling shield HP. |
| Energy Absorption | 400 | More HP and lifesteal from damage. |
| Electromagnetic Bomb | 500 | Periodically launches many EMP shots with heavy shield damage. |

**Mountain**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Gun-launched Missile | 400 | Periodically fires a high-damage area rocket; damage scales with rank. |
| Mountain Plating | 400 | Large flat damage block scaling with rank. |
| Saturation Bombardment | 500 | Wider splash and many shells per attack, but much slower attack interval. |
| Extended Range Ammo | 400 | Greatly longer range with much lower ATK. |
| Smoke Bomb | 250 | Periodically launches smoke that reduces unit range. |
| Photon Loop | 400 | Periodic self photon coating: damage reduction and status immunity. |
| Anti-Aircraft Ammunition | 300 | Allows Mountain to attack air with large ATK penalty. |
| Range Enhancement | 500 | +40 range. |

**War Factory**

| Tech | Cost | Effect / strategic meaning |
|---|---:|---|
| Range Enhancement | 500 | +40 range. |
| Phoenix Production | 500 | Periodically produces Phoenixes. |
| Steel Ball Production | 450 | Periodically produces Steel Balls. |
| Sledgehammer Production | 400 | Periodically produces Sledgehammers. |
| Missile Interceptor | 350 | Strong local missile interception. |
| Launcher Overload | 350 | Faster attacks, shorter range. |
| Photon Coating | 300 | Temporary damage reduction and status immunity. |
| Armor Enhancement | 400 | More HP plus flat block scaling with rank. |
| High-Explosive Ammo | 350 | Larger main-gun splash, lower ATK. |

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
- For newly bought or legally movable units, avoid feeding high-value ground units into the Hacker line.
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
- https://wiki.mbxmas.com/buildings/command-center/
- https://wiki.mbxmas.com/buildings/research-center/
- https://wiki.mbxmas.com/specialists/supply-specialist/
- https://wiki.mbxmas.com/specialists/quick-supply-specialist/
- https://wiki.mbxmas.com/specialists/cost-control-specialist/
- https://wiki.mbxmas.com/specialists/elite-specialist/
- https://mechamonarch.com/guide/mechabellum-card-guide/
- https://steamcommunity.com/app/669330/discussions/0/3833172420311906149/
- https://steamcommunity.com/app/669330/discussions/0/521962388138841184/
- https://mechamonarch.com/unit/
- https://mechamonarch.com/guide/mechabellum-counters/

Additional exact-cost / tech-catalog refresh URLs:

- https://wiki.mbxmas.com/specialists/giant-specialist/
- https://wiki.mbxmas.com/specialists/aerial-specialist/
- https://wiki.mbxmas.com/specialists/elite-specialist/
- https://wiki.mbxmas.com/specialists/cost-control-specialist/
- https://wiki.mbxmas.com/specialists/supply-specialist/
- https://wiki.mbxmas.com/units/ground/arclight/
- https://wiki.mbxmas.com/units/ground/crawler/
- https://wiki.mbxmas.com/units/ground/fang/
- https://wiki.mbxmas.com/units/ground/hound/
- https://wiki.mbxmas.com/units/ground/marksman/
- https://wiki.mbxmas.com/units/ground/void-eye/
- https://wiki.mbxmas.com/units/ground/vortex/
- https://wiki.mbxmas.com/units/air/abyss/
- https://wiki.mbxmas.com/units/ground/war-factory/

---

## 15. Final instruction to LLM using this file

When analyzing Mechabellum, always reason from mechanics and board state first. A unit is only a counter if:

1. it targets the right layer of the enemy army;
2. it survives long enough to perform its role;
3. it is not neutralized by chaff, range, air, EMP, shields, missile interception, flanks, or tech;
4. it does not open an even easier counter for the opponent;
5. it fits the player’s existing economy and composition.

The best recommendation is usually a small set of coordinated changes: one purchase, one tech, and one positioning adjustment.
