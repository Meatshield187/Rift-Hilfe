import streamlit as st
import json
from pathlib import Path

st.set_page_config(page_title="Rift Event Boss Helfer", layout="wide")
st.title("🔥 RIFT EVENT BOSS Helfer")
st.caption("Rift Hilfe")

# JSONs laden
BOSS_PATH = Path("combined_raidboss_sortiert.json")
TOOLS_PATH = Path("tools.json")

if not BOSS_PATH.exists() or not TOOLS_PATH.exists():
    st.error("❌ Bitte beide Dateien im gleichen Ordner haben!")
    st.stop()

with open(BOSS_PATH, "r", encoding="utf-8") as f:
    raw_data = json.load(f)
with open(TOOLS_PATH, "r", encoding="utf-8") as f:
    tools = json.load(f)

# Nur Mauer-Tools für die Flanken
mauer_tools = [t for t in tools if t.get("target") in ["mauer", "both"]]

# Boss-Daten
boss_data = {1: {"name": "Herrin des Verfalls", "data": {}}, 2: {"name": "Myzel-Souverän", "data": {}}}

for level_entry in raw_data:
    boss_id = int(level_entry["raidBossID"])
    level = int(level_entry["level"])

    if level not in boss_data[boss_id]["data"]:
        seconds = int(level_entry.get("wallRegenerationTime", 1200))
        mauerzeit = f"{seconds//60:02d}:{seconds%60:02d}"
        boss_data[boss_id]["data"][level] = {
            "mauer_aufladezeit": mauerzeit,
            "innenhof_kap": int(level_entry.get("courtyardSize", 0)),
            "phasen": {}
        }

    for phase_idx, stage in enumerate(level_entry.get("stages", [])):
        phase = phase_idx
        effects = stage.get("defenderBattleEffects", "")
        effect_dict = {}
        for part in effects.split(","):
            if "&" in part:
                k, v = part.split("&")
                effect_dict[int(k)] = int(v)

        def parse_units(s):
            if not s or "#" not in s: return 0, 0
            try:
                a, b = s.split("#")
                return int(a.split("+")[-1]), int(b.split("+")[-1])
            except:
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
            "einheiten": {"linke_a": linke_a, "linke_b": linke_b, "front_a": front_a, "front_b": front_b,
                          "rechte_a": rechte_a, "rechte_b": rechte_b, "innen_a": innen_a, "innen_b": innen_b}
        }

tab1, tab2 = st.tabs(["👑 Herrin des Verfalls", "🍄 Myzel-Souverän"])

def show_boss(boss_id):
    boss_name = boss_data[boss_id]["name"]
    levels = sorted(boss_data[boss_id]["data"].keys())
    
    col_sel, col_innen = st.columns([2, 1])
    with col_sel:
        level = st.selectbox("Level", levels, key=f"level_{boss_id}")
        phase = st.selectbox("Phase", list(range(6)), key=f"phase_{boss_id}")

    base = boss_data[boss_id]["data"][level]
    phase_data = base["phasen"].get(phase, {})
    e = phase_data.get("einheiten", {})

    innen_a = e.get("innen_a", 0)
    innen_b = e.get("innen_b", 0)

    with col_innen:
        st.metric("🏰 Gesamt Truppen", f"{innen_a + innen_b:,}")
        st.caption(f" Nah-deff: {innen_a:,} + Fern-deff: {innen_b:,}")

    st.subheader(f"Level {level} – Phase {phase} – {boss_name}")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1: st.metric("Maueraufladezeit", base["mauer_aufladezeit"])
    with c2: st.metric("Innenhof-Kapazität", f"{base['innenhof_kap']:,}")
    with c3: st.metric("Gesundheit", phase_data.get("gesundheit", "–"))
    with c4: st.metric("🛡️ Mauerschutz", phase_data.get("mauer_schutz", "–"))
    with c5: st.metric("🚪 Torschutz", phase_data.get("tor_schutz", "–"))
    with c6: st.metric("🏰 Innenhof-Kampfkraft", phase_data.get("innenhof_kampf", "–"))

    st.divider()

    col_l, col_m, col_r = st.columns(3)
    with col_l: st.subheader("🛡️ Linke Flanke"); st.write(f"**A - Fern-deff** : {e.get('linke_a', 0):,}"); st.write(f"**B - Nah-deff** : {e.get('linke_b', 0):,}")
    with col_m: st.subheader("🛡️ Front"); st.write(f"**A - Fern-deff** : {e.get('front_a', 0):,}"); st.write(f"**B - Nah-deff** : {e.get('front_b', 0):,}")
    with col_r: st.subheader("🛡️ Rechte Flanke"); st.write(f"**A - Fern-deff** : {e.get('rechte_a', 0):,}"); st.write(f"**B - Nah-deff** : {e.get('rechte_b', 0):,}")

    st.divider()

    mauer = int(phase_data.get("mauer_schutz", "0").replace("%", ""))

    st.subheader("🧮 Rift Mauer Rechner ")

    # Hilfsfunktion für eine Flanke
    def flank_rechner(flanke_name, slots, key_prefix):
        st.subheader(flanke_name)
        power = 0
        for i in range(slots):
            col_t, col_a = st.columns([3, 2])
            with col_t:
                tool = st.selectbox(f"Tool {i+1}", mauer_tools, format_func=lambda x: x["name"], key=f"{key_prefix}_tool_{i}_{boss_id}")
            with col_a:
                anz = st.number_input("Anzahl", min_value=0, value=0, step=1, key=f"{key_prefix}_anz_{i}_{boss_id}")
            power += tool["power"] * anz

        st.metric(f"**Mauerschutz der Bis jetzt abgzogen wird {flanke_name}**", f"{power:,} %")
        if power >= mauer:
            st.success("✅ Diese Flanke reicht aus!")
        else:
            st.error(f"❌ Fehlen noch {mauer - power:,} %")

        return power

    # Die drei Flanken mit eigenem Rechner
    total_mauer = 0
    total_mauer += flank_rechner("Linke Flanke", 2, "left")
    total_mauer += flank_rechner("Front", 3, "front")
    total_mauer += flank_rechner("Rechte Flanke", 2, "right")

   

with tab1:
    show_boss(1)
with tab2:
    show_boss(2)

st.sidebar.success("✅ Nur Mauer-Tools + Rechner pro Flanke")