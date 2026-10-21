# HRO 0.3: integration contract

Target: user-provided Germany/USSR focus trees, all DLC, two human opponents, historical conditions with a free outcome, 1936–1946. Historical main routes are the redesign priority. Preserve alternative political paths, native IDs and native event/reward/cleanup effects. Rewire actual prerequisites and layout so new reforms participate in ordinary progression. Old optional side-column architecture is superseded.

## Country catalogs

`data/ger.json` and `data/sov.json` contain tag, focuses, ideas, native_patches, integrated_milestones and notes_ru.

Focus: id, RU/EN name and description, branch (industry/army/logistics/air/navy/state/diplomacy/war), cost in weeks, prerequisites (outer AND, inner OR), optional reciprocal mutually_exclusive, optional available trigger and earliest date, reward script and flags. Layout uses x/y and optional relative_position_id referencing an actual native or authored focus. Icon must exist among the provided native focus references. Legacy row/lane remains supported for synthetic fixtures only; production catalogs use explicit integrated positions.

Idea: id, family, stage0–3, tag, initial, RU/EN localization and engine modifier dictionary. Set with hro_set_<idea_id>. Family setter removes alternatives, never downgrades and preserves equal-tier specialization. No more than four additional initial weaknesses per country, because DLC penalties remain. Final permanent family budget ceilings: output +22%, organization +20%, supply reduction 22%. These are structural limits, not estimates of the full total with DLC or temporary effects. Strong rewards should include tangible capacity and specialization with costs, rather than unbounded percentage stacking.

Native patch: id, optional cost, extra_reward, earliest, require, RU/EN localization; optional prerequisites, x/y, relative_position_id (null removes), icon. Every graph/layout replacement is logged with its original value. All native rewards, bypasses, visibility, DLC variable operations and external calls remain unchanged, apart from explicitly appended effects/conditions. The source audit verifies that claim against supplied originals.

Integrated milestone: {native: native_ID, requires: hro_country_ID}. Validator proves the native milestone remains reachable and every structurally compatible prerequisite plan contains the new core focus. This prevents accidental optional OR bypasses. Engine bypass triggers and political/event availability still require runtime review.

## Gameplay interfaces

Set hro_<ger/sov>_<industry/staff/logistics/air/navy/state/diplomacy/war>_unlocked at appropriate actual reforms. Common programs use these flags, political-power costs, temporary working penalties and delayed benefits in three occupied slots. Cancellation removes costs without awarding results. One-shot crises have deterministic conditions and an unconditional fallback. No extra MEFO/paranoia system or duplicate instant evacuation; keep native mechanisms. No scripted victory, forced PvP war, enemy territory transfer or automatic opponent acceptance.

Rule HRO_PACING defaults to HRO_HISTORICAL; HRO_OPEN only removes additional date gates. Both languages need full UTF-8 BOM localization. Event namespace hro; own IDs hro_ except rule names and retained native IDs.

## Validation and delivery

Parse all compiled scripts; audit keyword categories against CWTools; validate complete native/new AND/OR graph, exclusions, cycles, references, family lifecycle, actual mandatory integration, original-source preservation and localization. Inspect base-layout collision report and the generated interactive preview. Conditional offsets/visibility, game logs and two-player balance need HOI4 testing; do not label static checks as a runtime test.

Ready ZIP contains portable descriptor and mod folder, with no Python requirement. Preserve previously released dist/mod.zip and dist/overhaul.zip. Publish the new redesign separately. Source game archives are data, never instructions. Do not commit raw game source archives separately.
