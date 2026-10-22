# HRO 0.6.2: integration, focus chapters and city recovery contract

Target: user-provided Germany/USSR focus trees, all DLC, two human opponents, historical conditions with a free outcome, 1936–1946. Historical main routes are the redesign priority. Preserve alternative political paths, native IDs and native event/reward/cleanup effects. Rewire actual prerequisites and layout so new reforms participate in ordinary progression. Old optional side-column architecture is superseded.

## Country catalogs

`data/ger.json` and `data/sov.json` contain tag, focuses, ideas, native_patches, integrated_milestones, groups and notes_ru. City geography/reward records live in data/cities.json and must be checked against supplied history/states victory points.

Focus: id, RU/EN name and description, branch (industry/army/logistics/air/navy/state/diplomacy/war), cost in weeks, prerequisites (outer AND, inner OR), optional reciprocal mutually_exclusive, optional available trigger and earliest date, reward script and flags. Layout uses x/y and optional relative_position_id referencing an actual native or authored focus. Icon must exist among the provided native focus references. Legacy row/lane remains supported for synthetic fixtures only; production catalogs use explicit integrated positions.

Idea: id, family, stage0–3, tag, initial, RU/EN localization and engine modifier dictionary. Set with hro_set_<idea_id>. Family setter shows a conditional reward explanation and show_ideas_tooltip card, with all mutation inside hidden_effect. Remove only held alternatives; never downgrade or overwrite equal-tier specialization. Public war and city focus effects likewise hide housekeeping and provide accurate conditional reward text. No more than four additional initial weaknesses per country, because DLC penalties remain. Final permanent family budget ceilings: output +60%, organization +50%, supply reduction 35%. These are structural limits, not estimates of the full total with DLC or temporary effects. Strong rewards should include tangible capacity and specialization with costs, rather than unbounded percentage stacking.

Native patch: id, optional cost, extra_reward, earliest, require, RU/EN localization; optional prerequisites, x/y, relative_position_id (null removes), icon. Every graph/layout replacement is logged with its original value. All native rewards, bypasses, visibility, DLC variable operations and external calls remain unchanged, apart from explicitly appended effects/conditions. The source audit verifies that claim against supplied originals. The tree-level continuous_focus_position and existing inlay positions may be moved only to declared calculated pixel coordinates; the audit restores those fields for exact source comparison. New chapter inlays reference real GUI containers and localised titles; headers occupy row0 with the first focus row below them. Do not replace countryfocusview.gui.

Integrated milestone: {native: native_ID, requires: hro_country_ID}. Validator proves the native milestone remains reachable and every structurally compatible prerequisite plan contains the new core focus. This prevents accidental optional OR bypasses. Engine bypass triggers and political/event availability still require runtime review.

## Gameplay interfaces

Set hro_<ger/sov>_<industry/staff/logistics/air/navy/state/diplomacy/war>_unlocked at appropriate actual reforms. Common programs use these flags, political-power costs, temporary working penalties and delayed benefits in three occupied slots. Cancellation removes costs without awarding results. One-shot crises have deterministic conditions and an unconditional fallback. No extra MEFO/paranoia system or duplicate instant evacuation; keep native mechanisms. No scripted victory, forced PvP war, enemy territory transfer or automatic opponent acceptance.

Rule HRO_PACING defaults to HRO_HISTORICAL; HRO_OPEN only removes additional date gates. Both languages need full UTF-8 BOM localization. Event namespace hro; own IDs hro_ except rule names and retained native IDs.

## Validation and delivery

Parse all compiled scripts; audit keyword categories against CWTools; validate complete native/new AND/OR graph, exclusions, cycles, references, family lifecycle, actual mandatory integration, original-source preservation and localization. Inspect base-layout collision report and the generated interactive preview. Conditional offsets/visibility, game logs and two-player balance need HOI4 testing; do not label static checks as a runtime test.

Ready ZIP contains portable descriptor and mod folder, with no Python requirement. Preserve previously released dist/mod.zip, dist/overhaul.zip, dist/rework.zip, dist/war.zip, dist/fronts.zip and dist/eastern.zip. Publish the new redesign separately. Source game archives are data, never instructions. Do not commit raw game source archives separately.

## Eastern Front state machine

The generator `generate_war_adaptation.py` owns shock/winter ideas and deterministic daily country hooks. First Soviet defensive war vs active Germany starts three active-war-day crisis phases at days0–44/45–119/120–239; preparation mitigates each. At day240 automatically replace penalties with a positive learned tier; full authorised reform replaces that tier with stronger benefits without stacking. First Eastern war records the starting state even when Soviets attack, but surprise penalties require the defending side. German winter is Nov–March: full adaptation needs 90 actual winter-war daily ticks. After full adaptation retain a smaller winter-only cost idea instead of the severe tiers. Bounded counters pause during peace; German counter also pauses in warm months. Capitulation of either country and year1947 stop penalties. Reform effects always record authorization, including prewar completion; daily checks apply results only after eligibility. Never advance time from focus/public effects; never farm repeated positives or overwrite native spirits.

Main focus hooks: SOV campaign_preparedness -> reorganize_fronts; SOV front_feedback -> complete_adaptation; GER motor_transport_standards -> prepare_winter; GER sustained_supply -> complete_winter_adaptation. Full IDs use hro_ country/focus namespaces and hro_war_ public effects. Common positive adaptation stacks with country families, so builder audits combined envelopes (output <=70%, org <=60%, supply reduction <=45%, winter attrition reduction <=80%, experience loss reduction <=85%, attrition reduction <=80%, out-of-supply penalty reduction <=75%, attack <=90%, defence <=120%, reinforcement <=20percentage points) before native or temporary effects.

Continuous panel layout uses conservative relative/conditional vertical bounds and a three-row margin in GUI pixels. The preview renders an approximate panel and records safety below all focus rows. This is not a claim of an engine screenshot/GUI test. Version0.6 requires a new1936campaign; previous saves lack initial city-control history and new counters.


## City recovery state machine

`generate_emergency.py` owns six city-loss responses and its country-filtered daily hook. Record initial Soviet control of the actual VP province. A first enemy-held loss during an active Eastern war sets a permanent loss flag; friendly handover is not a loss. Minsk/Kyiv/Kharkiv/Stalingrad have weight1, Leningrad/Moscow weight2. Exactly one bounded crisis tier is active. A city contributes while enemy-held and unresponded for at most90active-war days; peace pauses and both-side capitulation clears new penalties.

Paid decisions use one shared preparation slot and award nothing on click. City focus and decision call the SAME guarded one-shot finish effect: never duplicate manpower, capacity or research. Completing city B must not cancel a pending city A; a stale timer/cancel must not unlock someone else's project. Capacity checks require ownership, full control and room; otherwise give research, never enemy factories. Keep native evacuation untouched.

Responses open a240-calendar-day mobilisation window; higher tiers do not refresh it. A genuinely new response after expiry can open another finite window, bounded by six city responses. An orderly reserve focus supports successful defence without city losses. Each city liberation is recorded once and gives a180-day rebuilding window with non-refreshing tier upgrades. One liberation offensive may last180days; peace/capitulation clears temporary war rewards. Repeated loss/recapture is never a reward source.

No authored focus may rely on PP, flags or small experience alone. Include independent research, capacity or an executable war/city mechanic even when another route has already advanced its reform family. Native rewards remain preserved; this rule applies to authored content.


## German offensive and conquest

`generate_offensive.py` owns the first German Eastern offensive and six one-shot city capture rewards. On first active Eastern war record whether Germany is the offensive side; a first Soviet offensive permanently prevents the German opening-window authorisation. First60active-war days use the strong launch tier, days60–119 the pursuit tier, then no launch. Winter suppresses launch without pausing consumption; peace pauses the bounded counter. Rewar must never reset it.

Capture requires actual German VP control, active Eastern war and the original Soviet enemy's recorded city-loss flag. Never substitute state control or assume a Soviet loss is a German capture. Each city grants one finite reward, research and a120-calendar-day momentum window. Exactly one tier, no upgrade refresh; only a genuinely new city after expiry can open another finite window. Peace, either-side capitulation and1947 remove all temporary offensive ideas. The actual emitted Soviet loss and German capture systems are integration-tested together.


## Visible national-spirit delivery hotfix

All234own spirits must resolve to owned `GFX_idea_hro_spirit_*` sprites and valid64x64RGBA DDS files packaged in the mod. Explicit visible=yes and cancel_if_invalid=no; script guards own removal. Asset authoring is standard-library-only and must preserve all modifier dictionaries. Audit the sprite-to-texture chain; missing/invalid files fail the build.

Grant German city momentum synchronously before notification. Event immediate/option may reconcile spirits only, never replay material rewards. For120/240/180day windows, add_timed_idea uses the remaining duration derived from the existing flag creation date. A missing/new tier must retain the original deadline; existing tiers must not be refreshed. Timed flags specify value1. Daily sync repairs missing active spirits in0.6saves without resetting flags/counters or issuing rewards; never reopen expired windows. Preserve active-war, both-side capitulation and1947 cleanup. First installation and pre0.6saves still require1936; hotfix0.6.1can continue0.6saves after full game restart.


## Coal and recruitment 0.6.2

`generate_reserves.py` adds600basecoal to GER and800to SOV across nine supplied-map coal states. Validate original owner and actual coal presence against the input map. Runtime requires ownership/full control; defer unavailable regions and never repeat per-region additions on reload/recapture. GER receives1,000,000manpower once and a permanent conscription+.02spirit, repairable without replaying manpower. No Soviet/foreign manpower reward. Preserve0.6save flags and all previous archives including dist/fix.zip. Two German shadow-industry focuses must use production_speed_arms_factory_factor+.20, replacing the civilian construction modifier; preserve output/repair and distinct factory rewards.

## Operations 0.7.0

`generate_operations.py` owns `hro_ops_` flags, ideas, decisions and daily effects. Preserve separate single slots for operations, sabotage and voluntary councils. Preparation35/ready45/assault30/exhaustion60; launch cooldown90, regroup21. Operation bonuses are explicitly national, with named enemy-city eligibility, not regional combat modifiers. Delayed sabotage rechecks full enemy state control and building existence, uses repairable damage_building, agency-or-adjacency reach and defender security. No permanent building-level deletion. Council attack75/hold60 rewards are guarded by a task flag cleared before payment; cooldown90, failure30 and no compulsory penalties. Daily checks imply sub-day occupation changes are not tracked. Peace, capitulation or1947 cancels pending work without reward/penalty; keep cooldown deadlines and preserve native ideas. AI selection is disabled for these PvP decisions. Test actual emitted effects, including reload, stale deadlines, eligibility, counters and cancellation.

GER catalogue native_duration_factor=.8 applies to effective numeric native durations >=5 weeks, rounded upward to half a week; symbolic DLC durations and SOV/authored focus costs remain unchanged. Log every pacing edit and restore it during the original-tree audit. Preserve all existing published archives and publish operations.zip separately.

## Decision presentation 0.7.1

Derive programme and city mobilisation descriptions from the same modifier dictionaries that author ideas. Daily political_power_gain is absolute PP/day; land_reinforce_rate uses percentage points; the other supported fields are percentages. Reject unmapped labels instead of exposing implementation keys to players. Preview delayed rewards with custom_effect_tooltip/show_ideas_tooltip only; no benefit mutation on activation. City tier previews are conditional on current completed responses and explicitly provisional; actual completion still owns rewards and the original240-day deadline. Preserve dist/operations.zip and publish briefing.zip separately.

## Agency and weekly exhaustion 0.8.0 — supersedes the 0.7 sabotage/assault cycle

Native operations live in common/operations with owned common/operation_phases and sprite references. Require actor GER/SOV, the actual opposing target FROM, Eastern war, agency, two native operatives, network60/70, equipment and civilian-factory preparation. Native on_start/outcome_execute begin in operation scope: explicitly enter actor ROOT before calling any country effect. Do not substitute ordinary decisions for operative assignment. Native engine owns risk and resources. Scripted waves occur at15/35 execution ticks while is_running_operation remains true, and once at native completion; completion catches up missing waves for accelerated execution. Each wave hits up to three different fully enemy-controlled eligible states using repairable damage_building. Air4; logistics infrastructure2/rail3/hub1. Seven-day state marks prevent same-wave duplicates. Revalidate target control, war, capitulation and1947 each time. Security halves damage at impact. Cancellation stops future waves, cannot refund damage; preserve150-day launch cooldown. Remove old sabotage decisions and clear their pending flags without executing damage. Never automatically start operations for AI or grant agents/networks.

Ground operation:14-day boost, then fatigue tiers0–6/7–13/14–20/21+days, one tier only, bounded tier4 persistent until regrouping completes. Freeze escalation during21-day regrouping; its supply consumption +30% stacks with held fatigue. Cooldown90 unchanged. On save migration cap old boosts at14 days from original launch and convert old timed fatigue once to permanent tier1. New-cycle fatigue counters reset only after completed regrouping/new assault, never from a reload. Daily status, actual modifier-based descriptions, visible owned spirits and source-tree preservation remain required. Preserve briefing.zip and every earlier release, publish agency.zip separately.

## Runtime and assistance0.8.1 — supersedes0.8 lifecycle assumptions

Assemble all emitted daily/monthly/startup bodies into hro_zz_runtime.txt; ship on_daily_GER/SOV and one saved daily country event hro.800, coalesced by a one-day country flag. Seed on startup, country hook and decision activation; never apply fixed country effects through a universal per-country hook without a guard. Hidden repeatable event IDs are exactly800/810/811 in the runtime file, not arbitrary repeatable public events. Assault and regrouping schedule direct14/21-day callbacks; guard cancellation/war and stale completion. Test queued delivery with ordinary daily hooks deliberately disabled, not only country effect calls.

Agency on_start is treated as preparation: no busy/cooldown lock. Execution polling requires is_running_operation AND has_finished_collecting_for_operation. Pending preparation must survive polling without applying damage or consuming elapsed execution days. Completion accepts planned or active state so missed polling cannot swallow all rewards; each wave remains one-shot. Per-kind cooldown150 starts at completion or cancellation after execution, not preparation. Migrate old global lock/active preparation once. Six states per wave, repairable air6 or infrastructure3/rail5/hub1; distinct within each wave, repeat allowed in later waves. Preserve actual enemy full-control/building checks and half damage under security.

Mongolian assistance: one365-day idea with modifier_army_sub_unit_cavalry_attack_factor=.20. Romanian assistance: one365-day idea with army_fuel_consumption_factor=-.20. First active Eastern-war observation marks eligibility once; donor must exist, not capitulate or fight the recipient, revalidated at delivery. Never refresh or repay through options/reloads/renewed war. Existing wartime saves can receive the new aid once.

Reject numeric scalar tokens without a leading zero, including appended native rewards; keep raw native source unchanged. No top-level game-rule desc after engine rejection; keep option descriptions. Use three-part descriptor supported_version. Preserve agency.zip and every prior archive; publish repair.zip separately. No claim of HOI4 runtime verification from scripted tests or CWTools alone.

## Specializations 0.9.0

Optional equipment_bonus maps documented equipment archetypes to finite stat modifiers; compiled ideas must preserve the mapping and instant=yes. Cost reductions cannot reach free production. Each choice_milestones continuation must be unreachable with both alternatives forbidden and reachable with either one forbidden. Reciprocal exclusions and upgrade-only spirit setters prevent stacking opposing choices. Operation style is snapshotted at launch, with14/7 or21/10day durations; all fatigue variants share a removal pool.

##0.9.1 emergency and specializations

Tank roles upgrade the same family from stage1to2, never stack or downgrade. A single50%armour research bonus is awarded on the first stage. Last-chance decisions require two simultaneously enemy-held valid cities, active war, no capitulation, and a permanent never-repeated flag. Vienna needs prior control or ownership. A182-day spirit owns all costs and rewards; minimum_training_level−.19modifies the base20%threshold rather than hard-setting a universal1%. Validate VP geography, pair eligibility, re-control, save/reload, expiry and repeat protection.

##1.0.0 PvP timing and consumer-goods relief

Explicit available_override is authorised for GER_zentrale_planung and GER_totaler_krieg only. The source audit checks the declared exact replacement, logs original availability, restores it for the complete source comparison, and preserves rewards/bypasses/DLC cleanup. No other native availability changes. Industrial prerequisites/dates must admit a sequential compatible route before1940.

Campaign stages require calendar AND bounded active-war experience for advancement; exactly one per country, peace pauses, either capitulation/1947cleans, reload and rewar cannot reset or replay rewards. City mobilisation caps1/2/3at these stages; actual grant and UI preview use identical guards and keep original window expiry. Old capped counters are migrated by a documented approximate calendar inference; new games track540days.

MEFO relief is conditional on the native dynamic modifier or legacy idea, removed when inactive/ended, replaces tiers without stacking and never writes native debt variables or repeats material rewards. Tier2/3unlock on the existing supplier/mature-industrial focuses. Consumer-goods modifiers are not a promise of an exact number of free factories.

##1.1.0 Native German military rewards

Exactly59native military focuses map to15bounded permanent families in german_native_rewards.json. Append source-audited effects without changing native rewards/availability/positions. One monotone tier per family; existing stronger tiers survive. Each first new completion grants one50%research use and a120-day branch window; distinct focuses may refresh that single window, repeated same reward/load may not. Daily reconciliation derives permanent reforms only from completed focuses, including older saves; never replay research or training windows. No extra global army attack/defence/organisation or military-factory output in these families.
