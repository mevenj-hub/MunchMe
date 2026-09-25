import streamlit as st
import pandas as pd
import datetime
import os

# ==========================================
# 1. PAGE SETUP & MODERN CSS
# ==========================================
st.set_page_config(
    page_title="Munch Me | Smart Nutrition & Chef Assistant",
    page_icon="🍏",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        background-color: #F8FAFC;
        color: #1E293B;
    }

    /* Primary Accent Buttons */
    .stButton > button {
        border-radius: 12px !important;
        font-weight: 700 !important;
        border: none !important;
        transition: all 0.2s ease-in-out !important;
        padding: 0.55rem 1.25rem !important;
    }
    
    /* Segmented/Option Button Styling */
    div[data-testid="stHorizontalBlock"] .stButton > button {
        background-color: #FFFFFF;
        color: #475569;
        border: 1.5px solid #E2E8F0 !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    div[data-testid="stHorizontalBlock"] .stButton > button:hover {
        border-color: #10B981 !important;
        color: #10B981;
    }

    /* Metric Cards */
    .metric-card {
        background: white;
        border-radius: 16px;
        padding: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -2px rgba(0,0,0,0.05);
        border: 1px solid #F1F5F9;
        text-align: center;
    }

    /* Recipe / Meal Cards */
    .recipe-card {
        background: white;
        border-radius: 20px;
        border: 1.5px solid #E2E8F0;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        display: flex;
        flex-direction: column;
        height: 100%;
    }
    .recipe-card-header {
        position: relative;
        height: 160px;
        background-color: #F1F5F9;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .recipe-card-header img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .badge-count {
        position: absolute;
        top: 12px;
        right: 12px;
        background: rgba(30, 41, 59, 0.85);
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .recipe-card-body {
        padding: 1.25rem;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
    }
    .macro-pill {
        border-radius: 10px;
        padding: 6px 10px;
        font-size: 0.8rem;
        font-weight: 700;
        text-align: center;
    }
    .macro-p { background-color: #ECFDF5; color: #059669; }
    .macro-c { background-color: #FEF9C3; color: #CA8A04; }
    .macro-f { background-color: #FFE4E6; color: #E11D48; }

    /* Progress Bar */
    .stProgress > div > div > div > div {
        background-color: #10B981 !important;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SESSION STATE MANAGEMENT
# ==========================================
if "page" not in st.session_state:
    st.session_state.page = 1

if "user" not in st.session_state:
    st.session_state.user = {
        "name": "",
        "dob": datetime.date(2000, 1, 1),
        "gender": "Female",
        "height_val": 165.0,
        "height_unit": "cm",
        "weight_val": 60.0,
        "weight_unit": "kg",
        "goal": "Weight Loss",
        "diet_type": "Balanced",
        "daily_calories": 1800,
        "target_protein": 120,
        "target_carbs": 180,
        "target_fat": 50,
        "consumed_calories": 0,
        "consumed_protein": 0,
        "consumed_carbs": 0,
        "consumed_fat": 0,
        "selected_recipe": None
    }

# ==========================================
# 3. GOOGLE SHEETS DATA LOADER
# ==========================================
SHEET_ID = "1LQsOAfiVeFzsukc1FMfGtmJgx1IcOYxBbPy_PGuIXKw"

@st.cache_data(ttl=600)
def load_sheet(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()

# Load Data from GIDs provided
recipes_summary_df = load_sheet("0")
recipe_details_df = load_sheet("45255346")
ingredients_master_df = load_sheet("1075366356")

# ==========================================
# 4. HEADER BRANDING & LOGO
# ==========================================
col_logo, col_title = st.columns([1, 6])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=95)
    else:
        st.markdown("<h1 style='color:#10B981; margin:0;'>🍏</h1>", unsafe_allow_html=True)

with col_title:
    st.markdown("<h2 style='margin-bottom:0; font-weight:800; color:#0F172A;'>Munch Me</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#64748B; margin-top:0; font-size:0.95rem;'>Smart Nutrition & Chef Assistant</p>", unsafe_allow_html=True)

st.markdown("<hr style='border:0; border-top:1px solid #E2E8F0; margin: 10px 0 25px 0;'>", unsafe_allow_html=True)


# ==============================================================================
# PAGE 1: USER PROFILE & ONBOARDING
# ==============================================================================
if st.session_state.page == 1:
    st.markdown("### Profile & Nutrition Goals")
    st.caption("Complete your physiological parameters to configure your meal matrix.")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.session_state.user["name"] = st.text_input("Full Name", value=st.session_state.user["name"], placeholder="e.g. Sarah Al-Ahmad")
        
        # Date of Birth Calendar Picker
        st.session_state.user["dob"] = st.date_input(
            "Date of Birth (Calendar Select)",
            value=st.session_state.user["dob"],
            min_value=datetime.date(1940, 1, 1),
            max_value=datetime.date.today()
        )

        # Gender Selection Buttons
        st.markdown("<label style='font-size:0.9rem; font-weight:600;'>Biological Sex</label>", unsafe_allow_html=True)
        g_col1, g_col2 = st.columns(2)
        if g_col1.button("👩 Female", use_container_width=True, type="primary" if st.session_state.user["gender"] == "Female" else "secondary"):
            st.session_state.user["gender"] = "Female"
            st.rerun()
        if g_col2.button("👨 Male", use_container_width=True, type="primary" if st.session_state.user["gender"] == "Male" else "secondary"):
            st.session_state.user["gender"] = "Male"
            st.rerun()

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        # Height with Unit Picker
        h_col1, h_col2 = st.columns([3, 2])
        with h_col1:
            st.session_state.user["height_val"] = st.number_input("Height", value=float(st.session_state.user["height_val"]), step=0.5)
        with h_col2:
            st.session_state.user["height_unit"] = st.selectbox("Height Unit", ["cm", "inch", "foot"], index=["cm", "inch", "foot"].index(st.session_state.user["height_unit"]))

        # Weight with Unit Picker
        w_col1, w_col2 = st.columns([3, 2])
        with w_col1:
            st.session_state.user["weight_val"] = st.number_input("Weight", value=float(st.session_state.user["weight_val"]), step=0.5)
        with w_col2:
            st.session_state.user["weight_unit"] = st.selectbox("Weight Unit", ["kg", "pound"], index=["kg", "pound"].index(st.session_state.user["weight_unit"]))

    with col2:
        # Goal Buttons
        st.markdown("<label style='font-size:0.9rem; font-weight:600;'>Primary Goal</label>", unsafe_allow_html=True)
        goal_options = ["Weight Loss", "Muscle Gain", "Maintenance", "Endurance"]
        btn_cols = st.columns(2)
        for i, g in enumerate(goal_options):
            col_target = btn_cols[i % 2]
            if col_target.button(g, key=f"goal_{g}", use_container_width=True, type="primary" if st.session_state.user["goal"] == g else "secondary"):
                st.session_state.user["goal"] = g
                st.rerun()

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # Diet Type Buttons (formerly Protocol)
        st.markdown("<label style='font-size:0.9rem; font-weight:600;'>Type of Diet</label>", unsafe_allow_html=True)
        diet_options = ["Balanced", "High Protein", "Low Carb", "Keto", "Vegetarian"]
        d_cols = st.columns(3)
        for i, d in enumerate(diet_options):
            col_target = d_cols[i % 3]
            if col_target.button(d, key=f"diet_{d}", use_container_width=True, type="primary" if st.session_state.user["diet_type"] == d else "secondary"):
                st.session_state.user["diet_type"] = d
                st.rerun()

        st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True)

        # Transition Button to Page 2
        if st.button("Continue to Meal Dashboard →", type="primary", use_container_width=True):
            # Unit conversions to metric for BMR
            weight_kg = st.session_state.user["weight_val"]
            if st.session_state.user["weight_unit"] == "pound":
                weight_kg = weight_kg * 0.453592

            height_cm = st.session_state.user["height_val"]
            if st.session_state.user["height_unit"] == "inch":
                height_cm = height_cm * 2.54
            elif st.session_state.user["height_unit"] == "foot":
                height_cm = height_cm * 30.48

            age = max(18, (datetime.date.today() - st.session_state.user["dob"]).days // 365)

            # Clinical Mifflin-St Jeor Formula
            if st.session_state.user["gender"] == "Male":
                bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
            else:
                bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

            tdee = bmr * 1.375

            # Goal Calorie Adjustment
            if st.session_state.user["goal"] == "Weight Loss":
                target_kcal = tdee - 450
            elif st.session_state.user["goal"] == "Muscle Gain":
                target_kcal = tdee + 350
            else:
                target_kcal = tdee

            st.session_state.user["daily_calories"] = int(target_kcal)
            st.session_state.user["target_protein"] = int((target_kcal * 0.28) / 4)
            st.session_state.user["target_carbs"] = int((target_kcal * 0.42) / 4)
            st.session_state.user["target_fat"] = int((target_kcal * 0.30) / 9)

            st.session_state.page = 2
            st.rerun()


# ==============================================================================
# PAGE 2: MEAL DASHBOARD & RECIPES
# ==============================================================================
elif st.session_state.page == 2:
    nav_col1, nav_col2 = st.columns([6, 1])
    with nav_col1:
        st.markdown("### Meal & Recipe Nutrition Dashboard")
        st.caption("Interactive meal macro analysis, image representation & preparation guide")
    with nav_col2:
        if st.button("← Edit Profile", use_container_width=True):
            st.session_state.page = 1
            st.rerun()

    # Progress & Depletion Bars
    cal_left = max(0, st.session_state.user["daily_calories"] - st.session_state.user["consumed_calories"])
    pro_left = max(0, st.session_state.user["target_protein"] - st.session_state.user["consumed_protein"])
    carb_left = max(0, st.session_state.user["target_carbs"] - st.session_state.user["consumed_carbs"])
    fat_left = max(0, st.session_state.user["target_fat"] - st.session_state.user["consumed_fat"])

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <span style="font-size: 0.85rem; color: #64748B; font-weight:700;">ENERGY</span>
            <h3 style="margin:4px 0 0 0; color:#0F172A;">{st.session_state.user['consumed_calories']} <span style="font-size:0.9rem; font-weight:500;">/ {st.session_state.user['daily_calories']} kcal</span></h3>
            <p style="margin:0; font-size:0.8rem; color:#10B981; font-weight:700;">{cal_left} kcal left</p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(min(1.0, st.session_state.user["consumed_calories"] / max(1, st.session_state.user["daily_calories"])))

    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <span style="font-size: 0.85rem; color: #059669; font-weight:700;">PROTEIN</span>
            <h3 style="margin:4px 0 0 0; color:#0F172A;">{st.session_state.user['consumed_protein']} <span style="font-size:0.9rem; font-weight:500;">/ {st.session_state.user['target_protein']} g</span></h3>
            <p style="margin:0; font-size:0.8rem; color:#059669; font-weight:700;">{pro_left}g left</p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(min(1.0, st.session_state.user["consumed_protein"] / max(1, st.session_state.user["target_protein"])))

    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <span style="font-size: 0.85rem; color: #CA8A04; font-weight:700;">CARBS</span>
            <h3 style="margin:4px 0 0 0; color:#0F172A;">{st.session_state.user['consumed_carbs']} <span style="font-size:0.9rem; font-weight:500;">/ {st.session_state.user['target_carbs']} g</span></h3>
            <p style="margin:0; font-size:0.8rem; color:#CA8A04; font-weight:700;">{carb_left}g left</p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(min(1.0, st.session_state.user["consumed_carbs"] / max(1, st.session_state.user["target_carbs"])))

    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <span style="font-size: 0.85rem; color: #E11D48; font-weight:700;">FAT</span>
            <h3 style="margin:4px 0 0 0; color:#0F172A;">{st.session_state.user['consumed_fat']} <span style="font-size:0.9rem; font-weight:500;">/ {st.session_state.user['target_fat']} g</span></h3>
            <p style="margin:0; font-size:0.8rem; color:#E11D48; font-weight:700;">{fat_left}g left</p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(min(1.0, st.session_state.user["consumed_fat"] / max(1, st.session_state.user["target_fat"])))

    st.markdown("<hr style='border:0; border-top:1px solid #E2E8F0; margin: 25px 0;'>", unsafe_allow_html=True)

    # Recipe Cards Display
    if recipes_summary_df.empty:
        st.warning("Connecting to Google Sheets... Ensure your Google Sheet is set to 'Anyone with the link can view'.")
    else:
        # Normalize column names
        recipes = recipes_summary_df.to_dict(orient="records")
        cols = st.columns(4)

        for idx, recipe in enumerate(recipes):
            with cols[idx % 4]:
                name = recipe.get("Recipe Name", recipe.get("name", recipe.get("Name", f"Recipe #{idx+1}")))
                cals = recipe.get("Calories", recipe.get("calories", recipe.get("Energy", 350)))
                pro = recipe.get("Protein", recipe.get("protein", 25))
                carb = recipe.get("Carbs", recipe.get("carbs", 35))
                fat = recipe.get("Fat", recipe.get("fat", 12))
                img_url = recipe.get("Image", recipe.get("image", recipe.get("Image URL", "")))
                item_count = recipe.get("Items", recipe.get("items", 4))

                st.markdown(f"""
                <div class="recipe-card">
                    <div class="recipe-card-header">
                        {f'<img src="{img_url}">' if img_url and str(img_url).startswith('http') else '<div style="font-size:3.5rem; color:#CBD5E1;">🍽️</div>'}
                        <div class="badge-count">🍽️ {item_count} items</div>
                    </div>
                    <div class="recipe-card-body">
                        <div style="font-weight:700; font-size:1.05rem; color:#0F172A; min-height:48px; line-height:1.3;">{name}</div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin: 10px 0;">
                            <div>
                                <span style="font-size:0.75rem; color:#64748B; font-weight:700;">ENERGY</span>
                                <div style="font-weight:800; font-size:1rem; color:#0F172A;">🔥 {cals} kcal</div>
                            </div>
                        </div>
                        <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:6px; margin-bottom:12px;">
                            <div class="macro-pill macro-p">P {pro}g</div>
                            <div class="macro-pill macro-c">C {carb}g</div>
                            <div class="macro-pill macro-f">F {fat}g</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                c_action1, c_action2 = st.columns(2)
                with c_action1:
                    if st.button("View Guide", key=f"guide_{idx}", use_container_width=True):
                        st.session_state.user["selected_recipe"] = {
                            "name": name,
                            "cals": cals,
                            "pro": pro,
                            "carb": carb,
                            "fat": fat,
                            "details": recipe
                        }
                        st.rerun()

                with c_action2:
                    if st.button("+ Eat", key=f"eat_{idx}", use_container_width=True):
                        st.session_state.user["consumed_calories"] += int(float(cals))
                        st.session_state.user["consumed_protein"] += int(float(pro))
                        st.session_state.user["consumed_carbs"] += int(float(carb))
                        st.session_state.user["consumed_fat"] += int(float(fat))
                        st.rerun()

    # Modal Guide / Nutrition Analytics
    if st.session_state.user["selected_recipe"] is not None:
        rec = st.session_state.user["selected_recipe"]
        st.markdown("<hr style='border:0; border-top:2px solid #10B981; margin: 30px 0;'>", unsafe_allow_html=True)
        
        with st.container():
            st.markdown(f"## 📖 {rec['name']}")
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("Calories", f"{rec['cals']} kcal")
            m_col2.metric("Protein", f"{rec['pro']} g")
            m_col3.metric("Carbs", f"{rec['carb']} g")
            m_col4.metric("Fat", f"{rec['fat']} g")

            tab1, tab2 = st.tabs(["📝 Recipe Instructions & Ingredients", "📊 Nutritional Macro Analytics"])

            with tab1:
                # Find matching ingredients from the detailed table
                st.markdown("#### Ingredients Baseline")
                if not recipe_details_df.empty:
                    # Filter matching recipe details
                    matched_items = recipe_details_df[
                        recipe_details_df.astype(str).apply(lambda row: rec['name'].lower() in row.to_string().lower(), axis=1)
                    ]
                    if not matched_items.empty:
                        st.dataframe(matched_items, use_container_width=True)
                    else:
                        st.info("Ingredients and preparation instructions loaded directly from your Google Sheet.")
                else:
                    st.info("Reference ingredients loaded from Google Sheet table.")

            with tab2:
                st.markdown("#### Caloric Contribution by Macro")
                total_macro_cals = (float(rec['pro']) * 4) + (float(rec['carb']) * 4) + (float(rec['fat']) * 9)
                if total_macro_cals > 0:
                    p_pct = round(((float(rec['pro']) * 4) / total_macro_cals) * 100)
                    c_pct = round(((float(rec['carb']) * 4) / total_macro_cals) * 100)
                    f_pct = round(((float(rec['fat']) * 9) / total_macro_cals) * 100)

                    c_pct1, c_pct2, c_pct3 = st.columns(3)
                    c_pct1.success(f"Protein: {p_pct}% ({float(rec['pro']) * 4:.0f} kcal)")
                    c_pct2.warning(f"Carbohydrates: {c_pct}% ({float(rec['carb']) * 4:.0f} kcal)")
                    c_pct3.error(f"Fat: {f_pct}% ({float(rec['fat']) * 9:.0f} kcal)")

            if st.button("Close Recipe Guide", type="secondary"):
                st.session_state.user["selected_recipe"] = None
                st.rerun()
