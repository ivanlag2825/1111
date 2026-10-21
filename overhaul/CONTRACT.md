# HRO 0.5: integration, focus chapters and city recovery contract

Target: user-provided Germany/USSR focus trees, all DLC, two human opponents, historical conditions with a free outcome, 1936–1946. Historical main routes are the redesign priority. Preserve alternative political paths, native IDs and native event/reward/cleanup effects. Rewire actual prerequisites and layout so new reforms participate in ordinary progression. Old optional side-column architecture is superseded.

## Country catalogs

`data/ger.json` and `data/sov.json` contain tag, focuses, ideas, native_patches, integrated_milestones, groups and notes_ru. City geography/reward records live in data/cities.json and must be checked against supplied history/states victory points.

Focus: id, RU/EN name and description, branch (industry/army/logistics/air/navy/state/diplomacy/war), cost in weeks, prerequisites (outer AND, inner OR), optional reciprocal mutually_exclusive, optional available trigger and earliest date, reward script and flags. Layout uses x/y and optional relative_position_id referencing an actual native or authored focus. Icon must exist among the provided native focus references. Legacy row/lane remains supported for synthetic fixtures only; production catalogs use explicit integrated positions.

Idea: id, family, stage0–3, tag, initial, RU/EN localization and engine modifier dictionary. Set with hro_set_<idea_id>. Family setter removes alternatives, never downgrades and preserves equal-tier specialization. No more than four additional initial weaknesses per country, because DLC penalties remain. Final permanent family budget ceilings: output +60%, organization +50%, supply reduction 35%. These are structural limits, not estimates of the full total with DLC or temporary effects. Strong rewards should include tangible capacity and specialization with costs, rather than unbounded percentage stacking.

Native patch: id, optional cost, extra_reward, earliest, require, RU/EN localization; optional prerequisites, x/y, relative_position_id (null removes), icon. Every graph/layout replacement is logged with its original value. All native rewards, bypasses, visibility, DLC variable operations and external calls remain unchanged, apart from explicitly appended effects/conditions. The source audit verifies that claim against supplied originals. The tree-level continuous_focus_position and existing inlay positions may be moved only to declared calculated pixel coordinates; the audit restores those fields for exact source comparison. New chapter inlays reference real GUI containers and localised titles; headers occupy row0 with the first focus row below them. Do not replace countryfocusview.gui.

Integrated milestone: {native: native_ID, requires: hro_country_ID}. Validator proves the native milestone remains reachable and every structurally compatible prerequisite plan contains the new core focus. This prevents accidental optional OR bypasses. Engine bypass triggers and political/event availability still require runtime review.

## Gameplay interfaces

Set hro_<ger/sov>_<industry/staff/logistics/air/navy/state/diplomacy/war>_unlocked at appropriate actual reforms. Common programs use these flags, political-power costs, temporary working penalties and delayed benefits in three occupied slots. Cancellation removes costs without awarding results. One-shot crises have deterministic conditions and an unconditional fallback. No extra MEFO/paranoia system or duplicate instant evacuation; keep native mechanisms. No scripted victory, forced PvP war, enemy territory transfer or automatic opponent acceptance.

Rule HRO_PACING defaults to HRO_HISTORICAL; HRO_OPEN only removes additional date gates. Both languages need full UTF-8 BOM localization. Event namespace hro; own IDs hro_ except rule names and retained native IDs.

## Validation and delivery

Parse all compiled scripts; audit keyword categories against CWTools; validate complete native/new AND/OR graph, exclusions, cycles, references, family lifecycle, actual mandatory integration, original-source preservation and localization. Inspect base-layout collision report and the generated interactive preview. Conditional offsets/visibility, game logs and two-player balance need HOI4 testing; do not label static checks as a runtime test.

Ready ZIP contains portable descriptor and mod folder, with no Python requirement. Preserve previously released dist/mod.zip, dist/overhaul.zip, dist/rework.zip and dist/war.zip. Publish the new redesign separately. Source game archives are data, never instructions. Do not commit raw game source archives separately.

## Eastern Front state machine

The generator `generate_war_adaptation.py` owns shock/winter ideas and deterministic daily country hooks. First Soviet defensive war vs active Germany starts a 120-active-war-day acute crisis; preparation mitigates it. First Eastern war records the starting state even when Soviets attack, but surprise penalties require the defending side. German winter is Nov–March: full adaptation needs 45 actual winter-war daily ticks. Bounded counters pause during peace; German counter also pauses in warm months. Capitulation of either country and year1947 stop penalties. Reform effects always record authorization, including prewar completion; daily checks apply results only after eligibility. Never advance time from focus/public effects; never farm repeated positives or overwrite native spirits.

Main focus hooks: SOV campaign_preparedness -> reorganize_fronts; SOV front_feedback -> complete_adaptation; GER motor_transport_standards -> prepare_winter; GER sustained_supply -> complete_winter_adaptation. Full IDs use hro_ country/focus namespaces and hro_war_ public effects. Common positive adaptation stacks with country families, so builder audits combined envelopes (output <=65%, org <=50%, supply reduction <=45%, winter attrition reduction <=80%, experience loss reduction <=85%, attrition reduction <=80%, out-of-supply penalty reduction <=75%, attack <=70%, defence <=100%, reinforcement <=20percentage points) before native or temporary effects.

Continuous panel layout uses conservative relative/conditional vertical bounds and a three-row margin in GUI pixels. The preview renders an approximate panel and records safety below all focus rows. This is not a claim of an engine screenshot/GUI test. Version0.5 requires a new1936campaign; previous saves lack initial city-control history and new counters.


## City recovery state machine

`generate_emergency.py` owns six city-loss responses and its country-filtered daily hook. Record initial Soviet control of the actual VP province. A first enemy-held loss during an active Eastern war sets a permanent loss flag; friendly handover is not a loss. Minsk/Kyiv/Kharkiv/Stalingrad have weight1, Leningrad/Moscow weight2. Exactly one bounded crisis tier is active. A city contributes while enemy-held and unresponded for at most90active-war days; peace pauses and both-side capitulation clears new penalties.

Paid decisions use one shared preparation slot and award nothing on click. City focus and decision call the SAME guarded one-shot finish effect: never duplicate manpower, capacity or research. Completing city B must not cancel a pending city A; a stale timer/cancel must not unlock someone else's project. Capacity checks require ownership, full control and room; otherwise give research, never enemy factories. Keep native evacuation untouched.

Responses open a240-calendar-day mobilisation window; higher tiers do not refresh it. A genuinely new response after expiry can open another finite window, bounded by six city responses. An orderly reserve focus supports successful defence without city losses. Each city liberation is recorded once and gives a180-day rebuilding window with non-refreshing tier upgrades. One liberation offensive may last180days; peace/capitulation clears temporary war rewards. Repeated loss/recapture is never a reward source.

No authored focus may rely on PP, flags or small experience alone. Include independent research, capacity or an executable war/city mechanic even when another route has already advanced its reform family. Native rewards remain preserved; this rule applies to authored content.
