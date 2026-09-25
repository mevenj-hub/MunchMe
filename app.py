import streamlit as st
import pandas as pd
import requests
import io
import re
import os
from google import genai
from typing import Dict, Any, List

# =========================================================
# 1. PAGE CONFIG & BRAND STYLING
# =========================================================
st.set_page_config(
    page_title="Munch Me | Smart Nutrition & Chef Assistant",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #242D35;
    }

    .stApp {
        background-color: #F9FAFB;
    }

    /* Vibrant Primary Actions - Peach Coral */
    .stButton>button {
        background: linear-gradient(135deg, #FF6B58 0%, #FF8575 100%) !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 0.5rem 1.25rem !important;
        box-shadow: 0 4px 12px rgba(255, 107, 88, 0.25) !important;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(255, 107, 88, 0.35) !important;
    }

    .metric-card {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        border: 1px solid #E5E7EB;
        text-align: center;
    }

    .recipe-card {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 16px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        margin-bottom: 20px;
    }

    .badge-category {
        background-color: #E6FAF8;
        color: #2EC4B6;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.75rem;
        display: inline-block;
        margin-bottom: 8px;
    }

    .pill {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-right: 4px;
    }
    .pill-cal { background: #F1F5F9; color: #242D35; }
    .pill-p { background: #FFEBE9; color: #FF6B58; }
    .pill-c { background: #E6FAF8; color: #2EC4B6; }
    .pill-f { background: #FFF7E6; color: #D97706; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. SESSION STATE
# =========================================================
if "user_profile" not in st.session_state:
    st.session_state.user_profile = None

if "daily_log" not in st.session_state:
    st.session_state.daily_log = []

if "water_intake_ml" not in st.session_state:
    st.session_state.water_intake_ml = 0

# =========================================================
# 3. DATA LOADER & DRIVE LINK CONVERTER
# =========================================================
SHEET_ID = "1LQsOAfiVeFzsukc1FMfGtmJgx1IcOYxBbPy_PGuIXKw"

def convert_drive_url(url: str) -> str:
    if not url or not isinstance(url, str):
        return ""
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
    if match:
        return f"https://lh3.googleusercontent.com/d/{match.group(1)}"
    match_id = re.search(r'id=([a-zA-Z0-9_-]+)', url)
    if match_id:
        return f"https://lh3.googleusercontent.com/d/{match_id.group(1)}"
    return url

@st.cache_data(ttl=600)
def load_all_sheet_data():
    def fetch_csv(gid: str, keyword: str = None) -> pd.DataFrame:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
        res = requests.get(url)
        res.raise_for_status()
        raw = pd.read_csv(io.StringIO(res.text), header=None)
        if keyword:
            m = raw[raw.apply(lambda r: r.astype(str).str.contains(keyword, case=False, na=False).any(), axis=1)]
            if not m.empty:
                idx = m.index[0]
                df = raw.iloc[idx + 1:].copy()
                df.columns = raw.iloc[idx].values
            else:
                df = pd.read_csv(io.StringIO(res.text))
        else:
            df = pd.read_csv(io.StringIO(res.text))
        df.columns = [str(c).strip().lower().replace(" ", "_").replace(".", "") for c in df.columns]
        return df

    # Categories
    cat = fetch_csv("0", "categor")
    cat_col = [c for c in cat.columns if "categor" in c][0]
    cat = cat.dropna(subset=[cat_col])

    # Recipes
    rec = fetch_csv("45255346", "ingredient")
    meal_col = [c for c in rec.columns if "meal" in c or "recipe" in c or "item" in c]
    m_col_name = meal_col[0] if meal_col else rec.columns[0]
    rec[m_col_name] = rec[m_col_name].ffill()
    ing_col = [c for c in rec.columns if "ingred" in c]
    if ing_col:
        rec = rec.dropna(subset=[ing_col[0]])

    return cat, rec, m_col_name

try:
    categories_df, recipes_df, meal_col_name = load_all_sheet_data()
except Exception as e:
    st.error(f"Error connecting to Google Sheets: {e}")
    st.stop()

# =========================================================
# 4. ONBOARDING MODAL / SCREEN
# =========================================================
if st.session_state.user_profile is None:
    st.markdown("<h2 style='text-align: center; color: #242D35;'>Welcome to Munch Me 🥗</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748B;'>Set up your profile to personalize your daily targets and meal planning.</p>", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        with st.form("onboarding_form"):
            st.subheader("Your Personal Metrics")
            gender = st.radio("Biological Sex", ["Female", "Male"], horizontal=True)
            c1, c2 = st.columns(2)
            age = c1.number_input("Age (years)", min_value=15, max_value=95, value=28)
            weight = c2.number_input("Weight (kg)", min_value=35.0, max_value=200.0, value=68.0, step=0.5)
            height = c1.number_input("Height (cm)", min_value=120.0, max_value=220.0, value=165.0, step=0.5)
            activity = c2.selectbox("Activity Level", ["Sedentary (mostly seated)", "Lightly Active (1-3 days/wk)", "Moderately Active (3-5 days/wk)", "Very Active (6-7 days/wk)"])

            st.subheader("Dietary Strategy")
            c3, c4 = st.columns(2)
            goal = c3.selectbox("Goal", ["Weight Loss", "Maintenance", "Muscle Gain"])
            protocol = c4.selectbox("Protocol", ["Balanced", "High Protein", "Low Carb", "Keto"])

            submit = st.form_submit_button("Lock In My Personal Plan ✨")
            if submit:
                # Mifflin-St Jeor
                if gender == "Male":
                    bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
                else:
                    bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161

                mult = {"Sedentary (mostly seated)": 1.2, "Lightly Active (1-3 days/wk)": 1.375, "Moderately Active (3-5 days/wk)": 1.55, "Very Active (6-7 days/wk)": 1.725}[activity]
                tdee = bmr * mult
                cal_mod = {"Weight Loss": -450, "Maintenance": 0, "Muscle Gain": 350}[goal]
                target_cal = max(1200, tdee + cal_mod)

                p_pct, c_pct, f_pct = {
                    "Balanced": (0.25, 0.50, 0.25),
                    "High Protein": (0.35, 0.40, 0.25),
                    "Low Carb": (0.30, 0.20, 0.50),
                    "Keto": (0.20, 0.05, 0.75)
                }[protocol]

                st.session_state.user_profile = {
                    "gender": gender, "age": age, "weight": weight, "height": height,
                    "target_cal": round(target_cal),
                    "protein_g": round((target_cal * p_pct) / 4),
                    "carbs_g": round((target_cal * c_pct) / 4),
                    "fat_g": round((target_cal * f_pct) / 9),
                    "water_target_ml": round(weight * 35),
                    "protocol": protocol, "goal": goal
                }
                st.rerun()
    st.stop()

# =========================================================
# 5. DASHBOARD & REMAINING MACRO BUDGET
# =========================================================
prof = st.session_state.user_profile

c_head1, c_head2 = st.columns([3, 1])
c_head1.markdown(f"### 👋 Target: **{prof['target_cal']} kcal** ({prof['protocol']} Plan)")
if c_head2.button("⚙️ Edit Profile"):
    st.session_state.user_profile = None
    st.rerun()

# Dynamic Depletion
c_cal = sum(m['calories'] for m in st.session_state.daily_log)
c_p = sum(m['protein'] for m in st.session_state.daily_log)
c_c = sum(m['carbs'] for m in st.session_state.daily_log)
c_f = sum(m['fat'] for m in st.session_state.daily_log)

rem_cal = max(0, prof['target_cal'] - c_cal)
rem_p = max(0, prof['protein_g'] - c_p)
rem_c = max(0, prof['carbs_g'] - c_c)
rem_f = max(0, prof['fat_g'] - c_f)

m1, m2, m3, m4, m5 = st.columns(5)
m1.markdown(f"<div class='metric-card'><h4 style='color:#FF6B58; margin:0;'>Calories Left</h4><h2 style='margin:4px 0;'>{rem_cal}</h2><small style='color:#64748B;'>Target: {prof['target_cal']} kcal</small></div>", unsafe_allow_html=True)
m2.markdown(f"<div class='metric-card'><h4 style='color:#FF6B58; margin:0;'>Protein</h4><h2 style='margin:4px 0;'>{rem_p}g</h2><small style='color:#64748B;'>Consumed: {c_p}g</small></div>", unsafe_allow_html=True)
m3.markdown(f"<div class='metric-card'><h4 style='color:#2EC4B6; margin:0;'>Carbs</h4><h2 style='margin:4px 0;'>{rem_c}g</h2><small style='color:#64748B;'>Consumed: {c_c}g</small></div>", unsafe_allow_html=True)
m4.markdown(f"<div class='metric-card'><h4 style='color:#FFB703; margin:0;'>Fats</h4><h2 style='margin:4px 0;'>{rem_f}g</h2><small style='color:#64748B;'>Consumed: {c_f}g</small></div>", unsafe_allow_html=True)

with m5:
    st.markdown(f"<div class='metric-card'><h4 style='color:#2EC4B6; margin:0;'>Water Intake</h4><h2 style='margin:4px 0;'>{st.session_state.water_intake_ml} ml</h2><small style='color:#64748B;'>Goal: {prof['water_target_ml']} ml</small></div>", unsafe_allow_html=True)
    w1, w2 = st.columns(2)
    if w1.button("+250ml"):
        st.session_state.water_intake_ml += 250
        st.rerun()
    if w2.button("+500ml"):
        st.session_state.water_intake_ml += 500
        st.rerun()

st.markdown("<hr style='margin: 20px 0; border: 0.5px solid #E5E7EB;'/>", unsafe_allow_html=True)

# =========================================================
# 6. APP TABS: CHOOSE MEALS, EATEN TODAY, GROCERY, AI CHEF
# =========================================================
tab_meals, tab_today, tab_grocery, tab_ai = st.tabs([
    "🍽️ Choose & Log Meals",
    f"📋 Eaten Today ({len(st.session_state.daily_log)})",
    "🛒 Auto Grocery List",
    "👨‍🍳 Munch Me Chef Assistant"
])

with tab_meals:
    cat_field = [c for c in categories_df.columns if "categor" in c][0]
    item_field = [c for c in categories_df.columns if "item" in c or "menu" in c][0]

    categories_list = ["All Categories"] + sorted(list(categories_df[cat_field].dropna().unique()))
    selected_cat = st.selectbox("Category", categories_list)
    search_query = st.text_input("🔍 Search recipe or ingredient...", "")

    filtered = categories_df.copy()
    if selected_cat != "All Categories":
        filtered = filtered[filtered[cat_field] == selected_cat]
    if search_query:
        filtered = filtered[filtered[item_field].str.contains(search_query, case=False, na=False)]

    st.caption(f"Showing {len(filtered)} recipes")

    cols = st.columns(3)
    for idx, (_, item) in enumerate(filtered.iterrows()):
        col = cols[idx % 3]
        meal_name = item[item_field]
        recipe_rows = recipes_df[recipes_df[meal_col_name].str.strip().str.lower() == str(meal_name).strip().lower()]

        with col:
            st.markdown("<div class='recipe-card'>", unsafe_allow_html=True)
            st.markdown(f"<span class='badge-category'>{item.get(cat_field, 'Meal')}</span>", unsafe_allow_html=True)
            st.markdown(f"<h4 style='margin: 0 0 8px 0;'>{meal_name}</h4>", unsafe_allow_html=True)

            # Direct Image URL
            img_url = ""
            if not recipe_rows.empty:
                img_col = [c for c in recipe_rows.columns if "image" in c or "url" in c]
                if img_col:
                    img_url = convert_drive_url(recipe_rows.iloc[0][img_col[0]])
            if img_url:
                st.image(img_url, use_container_width=True)

            # Numerical macros
            cal_col = [c for c in item.index if "cal" in c or "kcal" in c][0]
            p_col = [c for c in item.index if "prot" in c][0]
            c_col = [c for c in item.index if "carb" in c][0]
            f_col = [c for c in item.index if "fat" in c][0]

            m_cal = round(pd.to_numeric(item.get(cal_col, 0), errors='coerce') or 0)
            m_p = round(pd.to_numeric(item.get(p_col, 0), errors='coerce') or 0)
            m_c = round(pd.to_numeric(item.get(c_col, 0), errors='coerce') or 0)
            m_f = round(pd.to_numeric(item.get(f_col, 0), errors='coerce') or 0)

            st.markdown(f"""
                <div style='margin: 8px 0;'>
                    <span class='pill pill-cal'>{m_cal} kcal</span>
                    <span class='pill pill-p'>P: {m_p}g</span>
                    <span class='pill pill-c'>C: {m_c}g</span>
                    <span class='pill pill-f'>F: {m_f}g</span>
                </div>
            """, unsafe_allow_html=True)

            with st.expander("📖 View Recipe & Method"):
                if not recipe_rows.empty:
                    meth_col = [c for c in recipe_rows.columns if "method" in c or "prep" in c]
                    if meth_col:
                        st.write(f"**Preparation:**\n{recipe_rows.iloc[0][meth_col[0]]}")
                    st.write("**Ingredients:**")
                    ing_c = [c for c in recipe_rows.columns if "ingred" in c][0]
                    qty_c = [c for c in recipe_rows.columns if "qtty" in c or "qty" in c][0]
                    unit_c = [c for c in recipe_rows.columns if "unit" in c][0]
                    for _, r in recipe_rows.iterrows():
                        st.write(f"• {r[ing_c]}: {r[qty_c]} {r[unit_c]}")

            if st.button(f"+ Log for Today", key=f"btn_{idx}_{meal_name}"):
                st.session_state.daily_log.append({
                    "name": meal_name,
                    "calories": m_cal, "protein": m_p, "carbs": m_c, "fat": m_f,
                    "ingredients": recipe_rows.to_dict('records') if not recipe_rows.empty else []
                })
                st.success(f"Added {meal_name}!")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

with tab_today:
    if not st.session_state.daily_log:
        st.info("No meals logged yet today.")
    else:
        for i, logged in enumerate(st.session_state.daily_log):
            c1, c2, c3 = st.columns([3, 2, 1])
            c1.markdown(f"**{logged['name']}**")
            c2.markdown(f"{logged['calories']} kcal | P: {logged['protein']}g | C: {logged['carbs']}g | F: {logged['fat']}g")
            if c3.button("Remove", key=f"remove_{i}"):
                st.session_state.daily_log.pop(i)
                st.rerun()

with tab_grocery:
    st.subheader("Consolidated Shopping List")
    if not st.session_state.daily_log:
        st.info("Log meals to compile your shopping list.")
    else:
        g_dict = {}
        for m in st.session_state.daily_log:
            for row in m.get('ingredients', []):
                ing_key = [k for k in row.keys() if "ingred" in k]
                qty_key = [k for k in row.keys() if "qtty" in k or "qty" in k]
                unit_key = [k for k in row.keys() if "unit" in k]
                if ing_key and qty_key and unit_key:
                    name = str(row[ing_key[0]]).strip()
                    unit = str(row[unit_key[0]]).strip()
                    q = pd.to_numeric(row[qty_key[0]], errors='coerce') or 0.0
                    g_dict[(name, unit)] = g_dict.get((name, unit), 0.0) + q

        for (name, unit), total in sorted(g_dict.items()):
            if name:
                st.checkbox(f"**{name}**: {round(total, 1)} {unit}")

with tab_ai:
    st.subheader("👨‍🍳 Ask Munch Me Chef")
    st.caption("Clinical substitutions, preparation techniques, and macro balancing.")
    user_q = st.text_input("Ask a question about your meals or swaps:", placeholder="e.g. How can I increase protein in my lunch without extra fat?")
    if st.button("Ask Assistant"):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            st.warning("Please configure your GEMINI_API_KEY in Replit Secrets (Tools > Secrets).")
        elif not user_q:
            st.warning("Please enter a question first.")
        else:
            with st.spinner("Chef is formulating advice..."):
                try:
                    client = genai.Client(api_key=api_key)
                    sys_prompt = f"""
                    You are Munch Me Smart Chef & Nutrition Assistant.
                    User Profile:
                    - Protocol: {prof['protocol']}
                    - Daily Target: {prof['target_cal']} kcal (P: {prof['protein_g']}g, C: {prof['carbs_g']}g, F: {prof['fat_g']}g)
                    - Remaining Today: {rem_cal} kcal (P: {rem_p}g, C: {rem_c}g, F: {rem_f}g)

                    Provide concise, practical culinary advice and ingredient substitutions.
                    """
                    resp = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=f"{sys_prompt}\nUser Question: {user_q}"
                    )
                    st.markdown(resp.text)
                except Exception as err:
                    st.error(f"AI Assistant Error: {err}")

