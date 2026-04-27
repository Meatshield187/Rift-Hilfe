import streamlit as st
import json
from pathlib import Path
import math

st.set_page_config(page_title="Rift Event Boss Viewer", layout="wide")
st.title("🔥 RIFT EVENT BOSS VIEWER")
st.caption("Herrin des Verfalls + Myzel-Souverän – JSON-Schutzwerte + Tool-Rechner")

# JSONs laden
BOSS_PATH = Path("combined_raidboss_sortiert.json")
TOOLS_PATH = Path("tools.json")

if not BOSS_PATH.exists() or not TOOLS_PATH.exists():
    st.error("❌ Bitte combined_raidboss_sortiert.json und tools.json im gleichen Ordner haben!")
    st.stop()

with open(BOSS_PATH, "r", encoding="utf-8") as f:
    raw_data = json.load(f)

with open(TOOLS_PATH, "r", encoding="utf-8") as f:
    tools = json.load(f)

# Zombi Boss Strategie-Guide laden
ZOMBI_BOSS_PATH = Path("Zombi Boss.txt")
if ZOMBI_BOSS_PATH.exists():
    with open(ZOMBI_BOSS_PATH, "r", encoding="utf-8") as f:
        zombi_boss_raw = f.read()
        zombi_boss_text = zombi_boss_raw.lstrip('\ufeff')
else:
    zombi_boss_text = "❌ Zombi Boss.txt nicht gefunden!"

def to_int(value, default=0):
    try:
        if isinstance(value, str):
            value = value.replace("%", "").replace(",", ".").strip()
        return int(float(value))
    except Exception:
        return default

def to_float(value, default=0.0):
    try:
        if isinstance(value, str):
            value = value.replace("%", "").replace(",", ".").strip()
        return float(value)
    except Exception:
        return default

def format_number(num):
    if isinstance(num, (int, float)):
        if num == int(num):
            return str(int(num))
        else:
            return f"{num:.2f}".rstrip('0').rstrip('.')
    return str(num)

boss_data = {
    1: {"name": "Herrin des Verfalls", "data": {}},
    2: {"name": "Myzel-Souverän", "data": {}},
}

for level_entry in raw_data:
    boss_id = int(level_entry["raidBossID"])
    if boss_id not in boss_data:
        continue
    level = int(level_entry["level"])
    if level not in boss_data[boss_id]["data"]:
        seconds = int(level_entry.get("wallRegenerationTime", 1200))
        mauerzeit = f"{seconds//60:02d}:{seconds%60:02d}"
        boss_data[boss_id]["data"][level] = {
            "mauer_aufladezeit": mauerzeit,
            "innenhof_kap": int(level_entry.get("courtyardSize", 0)),
            "phasen": {},
        }
    for phase_idx, stage in enumerate(level_entry.get("stages", [])):
        phase = phase_idx
        effects = stage.get("defenderBattleEffects", "")
        effect_dict = {}
        for part in effects.split(","):
            if "&" in part:
                try:
                    k, v = part.split("&")
                    effect_dict[int(k)] = int(v)
                except ValueError:
                    pass

        def parse_units(s):
            if not s or "#" not in s:
                return 0, 0
            try:
                a, b = s.split("#")
                return int(a.split("+")[-1]), int(b.split("+")[-1])
            except Exception:
                return 0, 0

        linke_a, linke_b = parse_units(stage.get("leftWallUnits", ""))
        front_a, front_b = parse_units(stage.get("frontWallUnits", ""))
        rechte_a, rechte_b = parse_units(stage.get("rightWallUnits", ""))
        innen_a, innen_b = parse_units(level_entry.get("courtyardReserveUnits", ""))

        boss_data[boss_id]["data"][level]["phasen"][phase] = {
            "gesundheit": f"{stage.get('health', 0)}%",
            "mauer_schutz": f"{effect_dict.get(445, 0)}%",
            "tor_schutz": f"{effect_dict.get(446, 0)}%",
            "flanken": f"{effect_dict.get(510, 0)}%",
            "front": f"{effect_dict.get(509, 0)}%",
            "innenhof_kampf": f"{effect_dict.get(501, 0)}%",
            "einheiten": {
                "linke_a": linke_a,
                "linke_b": linke_b,
                "front_a": front_a,
                "front_b": front_b,
                "rechte_a": rechte_a,
                "rechte_b": rechte_b,
                "innen_a": innen_a,
                "innen_b": innen_b,
            },
        }

def best_tool_combo(target_value, power1, power2, max_tools=40):
    if target_value <= 0:
        return {"count1": 0, "count2": 0, "total_tools": 0, "total_power": 0.0, "remaining": 0.0}
    if power1 <= 0 and power2 <= 0:
        return None

    best = None
    for count1 in range(max_tools, -1, -1):
        power_from_slot1 = count1 * power1
        remaining_target = target_value - power_from_slot1
        if remaining_target <= 0:
            best = {"count1": count1, "count2": 0, "total_tools": count1, "total_power": power_from_slot1, "remaining": 0.0}
            break
        if power2 > 0:
            count2_needed = math.ceil(remaining_target / power2)
        else:
            count2_needed = float("inf")
        if count1 + count2_needed <= max_tools:
            best = {"count1": count1, "count2": count2_needed, "total_tools": count1 + count2_needed, "total_power": power_from_slot1 + count2_needed * power2, "remaining": 0.0}
            break

    if best is None:
        best_power = -1
        best_candidate = None
        for count1 in range(max_tools + 1):
            count2 = max_tools - count1
            total_power = count1 * power1 + count2 * power2
            if total_power > best_power:
                best_power = total_power
                best_candidate = {"count1": count1, "count2": count2, "total_tools": max_tools, "total_power": total_power, "remaining": max(0.0, target_value - total_power)}
        best = best_candidate
    return best

st.header("⚙️ Einstellungen")
equipment_mauer = st.number_input("Mauerschutz-Reduktion durch Ausrüstung (%)", value=0.0, step=0.5, help="Wird automatisch vom Zielwert abgezogen")
st.divider()

tab1, tab2 = st.tabs(["👑 Herrin des Verfalls", "🍄 Myzel-Souverän"])

def show_boss(boss_id):
    boss_name = boss_data[boss_id]["name"]
    levels = sorted(boss_data[boss_id]["data"].keys())
    col_sel, col_innen = st.columns([2, 1])
    with col_sel:
        level = st.selectbox("Level", levels, key=f"level_{boss_id}")
        available_phases = sorted(boss_data[boss_id]["data"][level]["phasen"].keys())
        phase = st.selectbox("Phase", available_phases, key=f"phase_{boss_id}")
    base = boss_data[boss_id]["data"][level]
    phase_data = base["phasen"].get(phase, {})
    e = phase_data.get("einheiten", {})
    innen_a = e.get("innen_a", 0)
    innen_b = e.get("innen_b", 0)

    with col_innen:
        st.metric("🏰 Gesamt Truppen", f"{innen_a + innen_b:,}")
        st.caption(f"Nahdeff: {innen_a:,} | Ferndeff: {innen_b:,}")

    st.subheader(f"Level {level} – Phase {phase} – {boss_name}")

    mauer_schutz_wert = to_int(phase_data.get("mauer_schutz", "0%"), 0)
    effective_mauer = max(0.0, mauer_schutz_wert - equipment_mauer)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: st.metric("Maueraufladezeit", base["mauer_aufladezeit"])
    with c2: st.metric("Innenhof-Kapazität", f"{base['innenhof_kap']:,}")
    with c3: st.metric("Gesundheit", phase_data.get("gesundheit", "–"))
    with c4:
        st.metric("🛡️ Mauerschutz", f"{mauer_schutz_wert}%")
        st.caption(f"→ Effektiv: **{format_number(effective_mauer)}%**")
    with c5: st.metric("🏰 Innenhof-Kampfkraft", phase_data.get("innenhof_kampf", "–"))

    st.divider()
    st.subheader("🧮 Berechnung gegen Mauerschutz")

    calc_mode = st.radio("Zielwert", ["Kompletter Mauerschutz aus JSON", "Eigener Zielwert"], horizontal=True, key=f"calc_mode_{boss_id}")

    if calc_mode == "Kompletter Mauerschutz aus JSON":
        mauer_target = mauer_schutz_wert
    else:
        mauer_target = st.number_input("Eigener Zielwert Mauerschutz (%)", min_value=0, value=mauer_schutz_wert, step=1, key=f"mauer_target_{boss_id}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**🔥 Slot 1 (Priorität)**")
        tool1 = st.selectbox("Tool 1", tools, format_func=lambda x: x.get("name", "Unbekannt"), key=f"tool1_{boss_id}")
    with col2:
        st.markdown("**⚙️ Slot 2 (ergänzt nur wenn nötig)**")
        tool2 = st.selectbox("Tool 2", tools, format_func=lambda x: x.get("name", "Unbekannt"), key=f"tool2_{boss_id}")

    if st.button("🚀 Berechnen", type="primary", use_container_width=True, key=f"calc_{boss_id}"):
        if tool1 and tool2:
            base_power1 = to_float(tool1.get("power", 0), 0.0)
            base_power2 = to_float(tool2.get("power", 0), 0.0)
            eff_power1 = base_power1
            eff_power2 = base_power2

            target_for_calc = effective_mauer if calc_mode == "Kompletter Mauerschutz aus JSON" else max(0.0, mauer_target - equipment_mauer)
            best_mauer = best_tool_combo(target_for_calc, eff_power1, eff_power2, max_tools=40)

            if best_mauer is None:
                st.error("❌ Mit den aktuellen Tool-Werten kann nichts berechnet werden.")
                return

            st.success("**Ergebnis**")
            info1, info2, info3 = st.columns(3)
            with info1: st.metric("Effektiver Zielwert", f"{format_number(target_for_calc)}%")
            with info2: st.metric("Eff. Power Slot 1", format_number(eff_power1))
            with info3: st.metric("Eff. Power Slot 2", format_number(eff_power2))

            st.divider()
            st.subheader("🛡️ Berechnung gegen Mauerschutz")
            r1, r2, r3 = st.columns(3)
            with r1:
                st.write(f"**{tool1['name']}**")
                st.metric("Mitnehmen", f"{best_mauer['count1']:,} Stück")
            with r2:
                st.write(f"**{tool2['name']}**")
                st.metric("Mitnehmen", f"{best_mauer['count2']:,} Stück")
            with r3:
                st.metric("Gesamt Tools", f"{best_mauer['total_tools']:,} / 40")
                st.metric("Abgedeckt", format_number(best_mauer['total_power']))

            if best_mauer["remaining"] <= 0:
                st.success("✅ Mauerschutz komplett entfernt!")
            else:
                st.error(f"❌ Es fehlen noch {format_number(best_mauer['remaining'])} Mauerschutz (mit max. 40 Tools nicht möglich).")
        else:
            st.warning("Bitte beide Tools auswählen.")

    st.divider()
    col_l, col_m, col_r = st.columns(3)
    with col_l:
        st.subheader("🛡️ Linke Flanke")
        st.write(f"**A - Fern**: {e.get('linke_a', 0):,} | **B - Nah**: {e.get('linke_b', 0):,}")
    with col_m:
        st.subheader("🛡️ Front")
        st.write(f"**A - Fern**: {e.get('front_a', 0):,} | **B - Nah**: {e.get('front_b', 0):,}")
    with col_r:
        st.subheader("🛡️ Rechte Flanke")
        st.write(f"**A - Fern**: {e.get('rechte_a', 0):,} | **B - Nah**: {e.get('rechte_b', 0):,}")

    # === Zombi Boss Strategie direkt aus Datei ===
    if boss_id == 1:
        st.divider()
        st.subheader("📜 Zombi Boss – Komplette Strategie")
        

        # Saubere Formatierung Zeile für Zeile
        lines = zombi_boss_text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line == "Zombi Boss":
                st.markdown("## Zombi Boss")
            elif line in ["Fähigkeit", "Angriffsmuster", "Konstrukte / Dekos"]:
                st.markdown(f"### {line}")
            elif line in ["Mauer", "Innenhof", "Deko", "Rad", "Silbershop", "Events", "Sceatta", "Rubine", "Echtgeld / Gasha", "Geschenke"]:
                st.markdown(f"#### {line}")
            else:
                st.write(line)

with tab1:
    show_boss(1)
with tab2:
    show_boss(2)
