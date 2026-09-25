import streamlit as st
import pandas as pd
import datetime
import os
import re
from google import genai

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

    .stButton > button {
        border-radius: 12px !important;
        font-weight: 700 !important;
        border: none !important;
        transition: all 0.2s ease-in-out !important;
        padding: 0.55rem 1.25rem !important;
    }

    .metric-card {
        background: white;
        border-radius: 16px;
        padding: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -2px rgba(0,0,0,0.05);
        border: 1px solid #F1F5F9;
        text-align: center;
    }

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

    .chat-bubble {
        padding: 1rem 1.25rem;
        border-radius: 14px;
        margin-bottom: 0.8rem;
        line-height: 1.5;
    }
    .chat-user {
        background: #E2E8F0;
        color: #1E293B;
        text-align: right;
    }
    .chat-margot {
        background: #F0FDF4;
        border: 1px solid #BBF7D0;
        color: #166534;
    }

    .grocery-section-header {
        background: #F1F5F9;
        padding: 8px 14px;
        border-radius: 10px;
        font-weight: 700;
        font-size: 1rem;
        color: #1E293B;
        margin-top: 15px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. NUMERIC DATA CLEANER HELPER
# ==========================================
def extract_numeric(val, default=0.0):
    if pd.isna(val):
        return default
    val_str = str(val).strip()
    match = re.search(r"[-+]?\d*\.\d+|\d+", val_str)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return default
    return default

# ==========================================
# 3. SUPERMARKET AISLE CLASSIFIER
# ==========================================
def categorize_ingredient(name):
    n = str(name).lower()
    if any(k in n for k in ["lettuce", "rocca", "cucumber", "tomato", "onion", "garlic", "spinach", "cabbage", "pepper", "broccoli", "carrot", "herb", "parsley", "mint", "cilantro", "zucchini", "mushroom", "potato", "corn"]):
        return "🥬 Vegetables & Greens"
    elif any(k in n for k in ["apple", "banana", "berry", "berries", "strawberry", "lemon", "lime", "date", "orange", "avocado", "mango", "pomegranate"]):
        return "🍎 Fresh Fruits"
    elif any(k in n for k in ["chicken", "beef", "meat", "turkey", "fish", "salmon", "tuna", "shrimp"]):
        return "🥩 Meat, Poultry & Seafood"
    elif any(k in n for k in ["milk", "yogurt", "cheese", "halloumi", "labneh", "butter", "egg", "cream"]):
        return "🥛 Dairy, Milk & Eggs"
    elif any(k in n for k in ["rice", "bread", "toast", "oat", "quinoa", "freekeh", "pasta", "fettuccine", "flour", "tortilla"]):
        return "🌾 Grains, Pasta & Bakery"
    elif any(k in n for k in ["almond", "walnut", "cashew", "peanut", "seed", "chia"]):
        return "🥜 Nuts & Seeds"
    else:
        return "🧂 Pantry, Oils, Spices & Dressings"

# ==========================================
# 4. SESSION STATE MANAGEMENT
# ==========================================
if "page" not in st.session_state:
    st.session_state.page = 1

if "plan_mode" not in st.session_state:
    st.session_state.plan_mode = "Today (1 Day)"

# Stores: { "ingredient_name": { "quantity": float, "unit": str, "category": str } }
if "raw_grocery_items" not in st.session_state:
    st.session_state.raw_grocery_items = {}

if "margot_history" not in st.session_state:
    st.session_state.margot_history = [
        {"role": "margot", "content": "👋 Marhaban! I am Margot, your personal culinary nutritionist. How can I assist you with meal prep, custom substitutions, or recipes today?"}
    ]

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
        "consumed_calories": 0.0,
        "consumed_protein": 0.0,
        "consumed_carbs": 0.0,
        "consumed_fat": 0.0,
        "selected_recipe": None
    }

# ==========================================
# 5. MEAL SLOTS & CATEGORY HIERARCHY
# ==========================================
MEAL_STRUCTURE = {
    "Breakfast": [
        "Egg Breakfast",
        "Breakfast Smoothies",
        "Savory Breakfast",
        "Sweet Breakfast"
    ],
    "Lunch": [
        "Chicken Meals",
        "Fish Meals",
        "Meat Meals",
        "Salads",
        "Vegetarian Meals"
    ],
    "Dinner": [
        "Chicken Meals",
        "Fish Meals",
        "Meat Meals",
        "Salads",
        "Vegetarian Meals"
    ],
    "Snacks": [
        "Side Salads",
        "Drinks",
        "Savory Snacks",
        "Sweet Snacks"
    ]
}

# ==========================================
# 6. GOOGLE SHEETS DATA LOADER
# ==========================================
SHEET_ID = "1LQsOAfiVeFzsukc1FMfGtmJgx1IcOYxBbPy_PGuIXKw"

@st.cache_data(ttl=60)
def load_sheet_by_gid(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url, na_values=["#N/A", "N/A", "#VALUE!", "nan", "None"])
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()

# Sheet 1: Items Menu (gid=0)
recipes_summary_df = load_sheet_by_gid("0")

# Sheet 2: Calories Data (Detailed ingredients and recipes) (gid=45255346)
recipe_details_df = load_sheet_by_gid("45255346")

# Clean recipe details columns if present
if not recipe_details_df.empty:
    col_map = {}
    for c in recipe_details_df.columns:
        cl = c.lower()
        if "greek" in cl or "recipe" in cl or "menu" in cl:
            col_map[c] = "Recipe Name"
        elif "ingredient" in cl:
            col_map[c] = "Ingredients"
        elif "qtt" in cl or "qty" in cl:
            col_map[c] = "Qtty."
        elif "unit" in cl:
            col_map[c] = "Unit"
    recipe_details_df.rename(columns=col_map, inplace=True)
    # Forward fill recipe names for grouped rows
    if "Recipe Name" in recipe_details_df.columns:
        recipe_details_df["Recipe Name"] = recipe_details_df["Recipe Name"].ffill()

# Filter out uncompleted / #N/A rows from Items Menu
if not recipes_summary_df.empty and "Total Calories" in recipes_summary_df.columns:
    recipes_clean_df = recipes_summary_df.dropna(subset=["Menu Item", "Total Calories"]).copy()
    for col in ["Total Calories", "Total Protein", "Total Carbs", "Total Fat"]:
        if col in recipes_clean_df.columns:
            recipes_clean_df[col] = pd.to_numeric(recipes_clean_df[col], errors="coerce")
    recipes_clean_df = recipes_clean_df.dropna(subset=["Total Calories"])
else:
    recipes_clean_df = pd.DataFrame()

# ==========================================
# 7. BRAND HEADER & LOGO
# ==========================================
col_logo, col_title = st.columns([1, 6])
with col_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=90)
    else:
        st.markdown("<h1 style='color:#10B981; margin:0;'>🍏</h1>", unsafe_allow_html=True)

with col_title:
    st.markdown("<h2 style='margin-bottom:0; font-weight:800; color:#0F172A;'>Munch Me</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#64748B; margin-top:0; font-size:0.95rem;'>Smart Nutrition & Chef Assistant</p>", unsafe_allow_html=True)

st.markdown("<hr style='border:0; border-top:1px solid #E2E8F0; margin: 10px 0 25px 0;'>", unsafe_allow_html=True)


# ==============================================================================
# PAGE 1: USER ONBOARDING
# ==============================================================================
if st.session_state.page == 1:
    st.markdown("### Profile & Nutrition Goals")
    st.caption("Complete your physiological parameters to configure your meal matrix.")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.session_state.user["name"] = st.text_input("Full Name", value=st.session_state.user["name"], placeholder="e.g. Sarah")
        
        st.session_state.user["dob"] = st.date_input(
            "Date of Birth (Calendar Select)",
            value=st.session_state.user["dob"],
            min_value=datetime.date(1940, 1, 1),
            max_value=datetime.date.today()
        )

        st.markdown("<label style='font-size:0.9rem; font-weight:600;'>Biological Sex</label>", unsafe_allow_html=True)
        gender_options = ["Female", "Male"]
        curr_g = st.session_state.user.get("gender", "Female")
        if hasattr(st, "pills"):
            selected_gender = st.pills("Sex", options=gender_options, default=curr_g, label_visibility="collapsed")
            if selected_gender:
                st.session_state.user["gender"] = selected_gender
        elif hasattr(st, "segmented_control"):
            selected_gender = st.segmented_control("Sex", options=gender_options, default=curr_g, label_visibility="collapsed")
            if selected_gender:
                st.session_state.user["gender"] = selected_gender
        else:
            st.session_state.user["gender"] = st.radio("Sex", gender_options, index=gender_options.index(curr_g), horizontal=True, label_visibility="collapsed")

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        h_col1, h_col2 = st.columns([3, 2])
        with h_col1:
            st.session_state.user["height_val"] = st.number_input("Height", value=float(st.session_state.user["height_val"]), step=0.5)
        with h_col2:
            st.session_state.user["height_unit"] = st.selectbox("Height Unit", ["cm", "inch", "foot"], index=["cm", "inch", "foot"].index(st.session_state.user["height_unit"]))

        w_col1, w_col2 = st.columns([3, 2])
        with w_col1:
            st.session_state.user["weight_val"] = st.number_input("Weight", value=float(st.session_state.user["weight_val"]), step=0.5)
        with w_col2:
            st.session_state.user["weight_unit"] = st.selectbox("Weight Unit", ["kg", "pound"], index=["kg", "pound"].index(st.session_state.user["weight_unit"]))

    with col2:
        st.markdown("<label style='font-size:0.9rem; font-weight:600;'>Primary Goal</label>", unsafe_allow_html=True)
        goal_options = ["Weight Loss", "Muscle Gain", "Maintenance", "Endurance"]
        curr_goal = st.session_state.user.get("goal", "Weight Loss")
        if hasattr(st, "pills"):
            selected_goal = st.pills("Goal", options=goal_options, default=curr_goal, label_visibility="collapsed")
            if selected_goal:
                st.session_state.user["goal"] = selected_goal
        elif hasattr(st, "segmented_control"):
            selected_goal = st.segmented_control("Goal", options=goal_options, default=curr_goal, label_visibility="collapsed")
            if selected_goal:
                st.session_state.user["goal"] = selected_goal
        else:
            st.session_state.user["goal"] = st.radio("Goal", goal_options, index=goal_options.index(curr_goal), horizontal=True, label_visibility="collapsed")

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        st.markdown("<label style='font-size:0.9rem; font-weight:600;'>Type of Diet</label>", unsafe_allow_html=True)
        diet_options = ["Balanced", "High Protein", "Low Carb", "Keto", "Vegetarian"]
        curr_diet = st.session_state.user.get("diet_type", "Balanced")
        if hasattr(st, "pills"):
            selected_diet = st.pills("Diet", options=diet_options, default=curr_diet, label_visibility="collapsed")
            if selected_diet:
                st.session_state.user["diet_type"] = selected_diet
        elif hasattr(st, "segmented_control"):
            selected_diet = st.segmented_control("Diet", options=diet_options, default=curr_diet, label_visibility="collapsed")
            if selected_diet:
                st.session_state.user["diet_type"] = selected_diet
        else:
            st.session_state.user["diet_type"] = st.radio("Diet", diet_options, index=diet_options.index(curr_diet), horizontal=True, label_visibility="collapsed")

        st.markdown("<div style='height: 35px;'></div>", unsafe_allow_html=True)

        if st.button("Continue to Meal Dashboard →", type="primary", use_container_width=True):
            weight_kg = float(st.session_state.user["weight_val"])
            if st.session_state.user["weight_unit"] == "pound":
                weight_kg = weight_kg * 0.453592

            height_cm = float(st.session_state.user["height_val"])
            if st.session_state.user["height_unit"] == "inch":
                height_cm = height_cm * 2.54
            elif st.session_state.user["height_unit"] == "foot":
                height_cm = height_cm * 30.48

            age = max(18, (datetime.date.today() - st.session_state.user["dob"]).days // 365)

            if st.session_state.user["gender"] == "Male":
                bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
            else:
                bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

            tdee = bmr * 1.375

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
# PAGE 2: MEAL DASHBOARD, GROCERY LIST & MARGOT CHEF
# ==============================================================================
elif st.session_state.page == 2:
    nav1, nav2, nav3 = st.columns([4, 2, 1])
    with nav1:
        st.markdown("### Meal & Recipe Nutrition Dashboard")
        st.caption("Interactive macro analysis, recipe guides, and grocery planning")
    
    with nav2:
        plan_selection = st.radio(
            "Planning Horizon",
            ["Today (1 Day)", "This Week (7 Days)"],
            horizontal=True,
            index=0 if st.session_state.plan_mode == "Today (1 Day)" else 1,
            label_visibility="collapsed"
        )
        if plan_selection != st.session_state.plan_mode:
            st.session_state.plan_mode = plan_selection
            st.rerun()

    with nav3:
        if st.button("← Edit Profile", use_container_width=True):
            st.session_state.page = 1
            st.rerun()

    scale_factor = 7 if "Week" in st.session_state.plan_mode else 1
    target_cals = st.session_state.user["daily_calories"] * scale_factor
    target_pro = st.session_state.user["target_protein"] * scale_factor
    target_carb = st.session_state.user["target_carbs"] * scale_factor
    target_fat = st.session_state.user["target_fat"] * scale_factor

    c_cals = st.session_state.user["consumed_calories"]
    c_pro = st.session_state.user["consumed_protein"]
    c_carb = st.session_state.user["consumed_carbs"]
    c_fat = st.session_state.user["consumed_fat"]

    left_cals = max(0.0, target_cals - c_cals)
    left_pro = max(0.0, target_pro - c_pro)
    left_carb = max(0.0, target_carb - c_carb)
    left_fat = max(0.0, target_fat - c_fat)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <span style="font-size: 0.85rem; color: #64748B; font-weight:700;">ENERGY ({st.session_state.plan_mode})</span>
            <h3 style="margin:4px 0 0 0; color:#0F172A;">{int(c_cals)} <span style="font-size:0.9rem; font-weight:500;">/ {target_cals} kcal</span></h3>
            <p style="margin:2px 0 0 0; font-size:0.8rem; color:#10B981; font-weight:700;">Consumed: {int(c_cals)} kcal | Left: {int(left_cals)} kcal</p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(min(1.0, c_cals / max(1, target_cals)))

    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <span style="font-size: 0.85rem; color: #059669; font-weight:700;">PROTEIN</span>
            <h3 style="margin:4px 0 0 0; color:#0F172A;">{int(c_pro)}g <span style="font-size:0.9rem; font-weight:500;">/ {target_pro}g</span></h3>
            <p style="margin:2px 0 0 0; font-size:0.8rem; color:#059669; font-weight:700;">Consumed: {int(c_pro)}g | Left: {int(left_pro)}g</p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(min(1.0, c_pro / max(1, target_pro)))

    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <span style="font-size: 0.85rem; color: #CA8A04; font-weight:700;">CARBS</span>
            <h3 style="margin:4px 0 0 0; color:#0F172A;">{int(c_carb)}g <span style="font-size:0.9rem; font-weight:500;">/ {target_carb}g</span></h3>
            <p style="margin:2px 0 0 0; font-size:0.8rem; color:#CA8A04; font-weight:700;">Consumed: {int(c_carb)}g | Left: {int(left_carb)}g</p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(min(1.0, c_carb / max(1, target_carb)))

    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <span style="font-size: 0.85rem; color: #E11D48; font-weight:700;">FAT</span>
            <h3 style="margin:4px 0 0 0; color:#0F172A;">{int(c_fat)}g <span style="font-size:0.9rem; font-weight:500;">/ {target_fat}g</span></h3>
            <p style="margin:2px 0 0 0; font-size:0.8rem; color:#E11D48; font-weight:700;">Consumed: {int(c_fat)}g | Left: {int(left_fat)}g</p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(min(1.0, c_fat / max(1, target_fat)))

    st.markdown("<hr style='border:0; border-top:1px solid #E2E8F0; margin: 25px 0;'>", unsafe_allow_html=True)

    tab_meals, tab_grocery, tab_margot = st.tabs([
        "🍽️ Recipes & Meal Catalog", 
        "🛒 Grocery & Shopping List", 
        "👩‍🍳 Margot AI Chef Assistant"
    ])

    with tab_meals:
        if recipes_clean_df.empty:
            st.warning("No completed recipes found or sheet is still updating. Ensure columns have valid numbers!")
        else:
            st.markdown("#### Select Meal Slot")
            meal_slot = st.pills(
                "Meal Slot",
                options=list(MEAL_STRUCTURE.keys()),
                default="Breakfast",
                label_visibility="collapsed"
            ) or "Breakfast"

            available_subcats = MEAL_STRUCTURE[meal_slot]
            st.markdown(f"**Categories for {meal_slot}:**")
            subcat_choice = st.pills(
                "Subcategories",
                options=["All"] + available_subcats,
                default="All",
                label_visibility="collapsed"
            ) or "All"

            if meal_slot == "Snacks" and (subcat_choice in ["All", "Side Salads"]):
                target_categories = [c for c in available_subcats if c != "Side Salads"] + ["Salads"]
            else:
                target_categories = available_subcats

            if subcat_choice == "All":
                filtered_df = recipes_clean_df[recipes_clean_df["Categories"].isin(target_categories)].copy()
            elif subcat_choice == "Side Salads":
                filtered_df = recipes_clean_df[recipes_clean_df["Categories"] == "Salads"].copy()
            else:
                filtered_df = recipes_clean_df[recipes_clean_df["Categories"] == subcat_choice].copy()

            if filtered_df.empty:
                st.info(f"No completed recipes currently found for {subcat_choice} in {meal_slot}.")
            else:
                recipes = filtered_df.to_dict(orient="records")
                cols = st.columns(4)

                for idx, recipe in enumerate(recipes):
                    with cols[idx % 4]:
                        raw_cat = str(recipe.get("Categories", "")).strip()
                        name_en = str(recipe.get("Menu Item", f"Recipe #{idx+1}")).strip()
                        name_ar = str(recipe.get("Menu Item Ar", "")).strip()

                        is_side_salad = (meal_slot == "Snacks" and (raw_cat == "Salads" or subcat_choice == "Side Salads"))
                        portion_multiplier = 0.5 if is_side_salad else 1.0

                        cals = float(recipe.get("Total Calories", 0)) * portion_multiplier
                        pro = float(recipe.get("Total Protein", 0)) * portion_multiplier
                        carb = float(recipe.get("Total Carbs", 0)) * portion_multiplier
                        fat = float(recipe.get("Total Fat", 0)) * portion_multiplier

                        display_badge = "Side Salad (½ Portion)" if is_side_salad else raw_cat

                        st.markdown(f"""
                        <div class="recipe-card">
                            <div class="recipe-card-header">
                                <div style="font-size:3rem;">🥗</div>
                                <div class="badge-count">{display_badge}</div>
                            </div>
                            <div class="recipe-card-body">
                                <div style="font-weight:700; font-size:1rem; color:#0F172A; min-height:45px; line-height:1.2;">
                                    {name_en}<br><span style="font-size:0.85rem; color:#64748B; font-weight:500;">{name_ar}</span>
                                </div>
                                <div style="display:flex; justify-content:space-between; align-items:center; margin: 8px 0;">
                                    <div>
                                        <span style="font-size:0.75rem; color:#64748B; font-weight:700;">ENERGY</span>
                                        <div style="font-weight:800; font-size:1.05rem; color:#0F172A;">🔥 {cals:.0f} kcal</div>
                                    </div>
                                </div>
                                <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:6px; margin-bottom:12px;">
                                    <div class="macro-pill macro-p">P {pro:.1f}g</div>
                                    <div class="macro-pill macro-c">C {carb:.1f}g</div>
                                    <div class="macro-pill macro-f">F {fat:.1f}g</div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        c_action1, c_action2 = st.columns(2)
                        with c_action1:
                            if st.button("View Guide", key=f"guide_{meal_slot}_{idx}", use_container_width=True):
                                st.session_state.user["selected_recipe"] = {
                                    "name": f"{name_en} (Side Salad ½)" if is_side_salad else name_en,
                                    "clean_name": name_en,
                                    "name_ar": name_ar,
                                    "cals": cals,
                                    "pro": pro,
                                    "carb": carb,
                                    "fat": fat,
                                    "details": recipe
                                }
                                st.rerun()

                        with c_action2:
                            label_btn = "+ Eat Today" if "Today" in st.session_state.plan_mode else "+ Add to Week"
                            if st.button(label_btn, key=f"eat_{meal_slot}_{idx}", use_container_width=True):
                                st.session_state.user["consumed_calories"] += cals
                                st.session_state.user["consumed_protein"] += pro
                                st.session_state.user["consumed_carbs"] += carb
                                st.session_state.user["consumed_fat"] += fat

                                # Extract specific ingredients from Calories Data sheet
                                if not recipe_details_df.empty and "Ingredients" in recipe_details_df.columns:
                                    # Match by Recipe Name
                                    matched_rows = recipe_details_df[
                                        recipe_details_df["Recipe Name"].astype(str).str.lower().str.strip() == name_en.lower()
                                    ]
                                    if matched_rows.empty:
                                        # Fallback fuzzy match
                                        matched_rows = recipe_details_df[
                                            recipe_details_df.astype(str).apply(lambda r: name_en.lower() in r.to_string().lower(), axis=1)
                                        ]

                                    for _, ing_row in matched_rows.iterrows():
                                        ing_name = str(ing_row.get("Ingredients", "")).strip()
                                        if ing_name and ing_name.lower() != "nan" and ing_name.lower() != "ingredients":
                                            raw_q = extract_numeric(ing_row.get("Qtty.", 100)) * portion_multiplier
                                            raw_u = str(ing_row.get("Unit", "g")).strip()
                                            if not raw_u or raw_u.lower() == "nan":
                                                raw_u = "g"
                                            
                                            ing_cat = categorize_ingredient(ing_name)

                                            if ing_name in st.session_state.raw_grocery_items:
                                                st.session_state.raw_grocery_items[ing_name]["quantity"] += raw_q
                                            else:
                                                st.session_state.raw_grocery_items[ing_name] = {
                                                    "quantity": raw_q,
                                                    "unit": raw_u,
                                                    "category": ing_cat
                                                }
                                st.rerun()

        # Modal Recipe Details
        if st.session_state.user["selected_recipe"] is not None:
            rec = st.session_state.user["selected_recipe"]
            st.markdown("<hr style='border:0; border-top:2px solid #10B981; margin: 30px 0;'>", unsafe_allow_html=True)
            
            st.markdown(f"## 📖 {rec['name']}")
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("Calories", f"{int(rec['cals'])} kcal")
            m_col2.metric("Protein", f"{rec['pro']:.1f} g")
            m_col3.metric("Carbs", f"{rec['carb']:.1f} g")
            m_col4.metric("Fat", f"{rec['fat']:.1f} g")

            guide_tab1, guide_tab2 = st.tabs(["📝 Recipe Instructions & Ingredients", "📊 Nutritional Macro Analytics"])

            with guide_tab1:
                st.markdown("#### Ingredients Baseline & Method")
                if not recipe_details_df.empty:
                    clean_match_name = rec.get("clean_name", rec['name'].replace(" (Side Salad ½)", ""))
                    matched_items = recipe_details_df[
                        recipe_details_df.astype(str).apply(lambda row: clean_match_name.lower() in row.to_string().lower(), axis=1)
                    ]
                    if not matched_items.empty:
                        # Display clean columns
                        cols_to_show = [c for c in ["Ingredients", "Qtty.", "Unit", "Calories", "Protein", "Carbs", "Fat", "Method"] if c in matched_items.columns]
                        st.dataframe(matched_items[cols_to_show] if cols_to_show else matched_items, use_container_width=True)
                    else:
                        st.info("Ingredients loaded directly from your Google Sheet.")
                else:
                    st.info("Detailed ingredient rows loaded from Google Sheet table.")

            with guide_tab2:
                total_macro_cals = (rec['pro'] * 4) + (rec['carb'] * 4) + (rec['fat'] * 9)
                if total_macro_cals > 0:
                    p_pct = round(((rec['pro'] * 4) / total_macro_cals) * 100)
                    c_pct = round(((rec['carb'] * 4) / total_macro_cals) * 100)
                    f_pct = round(((rec['fat'] * 9) / total_macro_cals) * 100)

                    c_pct1, c_pct2, c_pct3 = st.columns(3)
                    c_pct1.success(f"Protein: {p_pct}% ({rec['pro'] * 4:.0f} kcal)")
                    c_pct2.warning(f"Carbohydrates: {c_pct}% ({rec['carb'] * 4:.0f} kcal)")
                    c_pct3.error(f"Fat: {f_pct}% ({rec['fat'] * 9:.0f} kcal)")

            if st.button("Close Recipe Guide", type="secondary"):
                st.session_state.user["selected_recipe"] = None
                st.rerun()

    # ==============================================================================
    # TAB 2: AISLE-GROUPED CONSOLIDATED GROCERY LIST
    # ==============================================================================
    with tab_grocery:
        st.markdown(f"### 🛒 Consolidated Grocery Shopping List ({st.session_state.plan_mode})")
        st.caption("Aggregated raw ingredients grouped by supermarket section based on your planned meals.")

        if not st.session_state.raw_grocery_items:
            st.info("Your shopping list is empty! Click '+ Eat Today' or '+ Add to Week' on any recipe card to build your ingredient list.")
        else:
            # Group items by aisle category
            items_by_cat = {}
            for ing_name, data in st.session_state.raw_grocery_items.items():
                cat = data.get("category", "🧂 Pantry, Oils, Spices & Dressings")
                if cat not in items_by_cat:
                    items_by_cat[cat] = []
                
                # Format quantity nicely (no decimal if integer)
                q_val = round(data["quantity"], 1)
                if q_val.is_integer():
                    q_val = int(q_val)
                    
                items_by_cat[cat].append({
                    "Ingredient": ing_name,
                    "Total Amount Needed": f"{q_val} {data['unit']}"
                })

            # Render tables per section
            for section, rows in sorted(items_by_cat.items()):
                st.markdown(f"<div class='grocery-section-header'>{section} ({len(rows)} items)</div>", unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
            if st.button("Clear Shopping List", type="secondary"):
                st.session_state.raw_grocery_items = {}
                st.session_state.user["consumed_calories"] = 0.0
                st.session_state.user["consumed_protein"] = 0.0
                st.session_state.user["consumed_carbs"] = 0.0
                st.session_state.user["consumed_fat"] = 0.0
                st.rerun()

    # ==============================================================================
    # TAB 3: MARGOT AI CHEF ASSISTANT
    # ==============================================================================
    with tab_margot:
        st.markdown("### 👩‍🍳 Margot | Culinary Nutritionist & AI Chef")
        st.caption("Ask Margot about ingredient swaps, culinary techniques, prep steps, or diet tailoring.")

        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.margot_history:
                if msg["role"] == "user":
                    st.markdown(f"<div class='chat-bubble chat-user'><b>You:</b><br>{msg['content']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='chat-bubble chat-margot'><b>👩‍🍳 Margot:</b><br>{msg['content']}</div>", unsafe_allow_html=True)

        user_input = st.chat_input("Ask Margot for a recipe substitution, cooking tip, or custom portion...")
        if user_input:
            st.session_state.margot_history.append({"role": "user", "content": user_input})

            api_key = None
            if "GEMINI_API_KEY" in st.secrets:
                api_key = st.secrets["GEMINI_API_KEY"]
            elif "GOOGLE_API_KEY" in st.secrets:
                api_key = st.secrets["GOOGLE_API_KEY"]
            elif os.getenv("GEMINI_API_KEY"):
                api_key = os.getenv("GEMINI_API_KEY")

            if api_key:
                try:
                    client = genai.Client(api_key=api_key)
                    sys_prompt = f"""
                    You are Margot, the personal AI Chef Assistant for Munch Me. 
                    You specialize in evidence-based nutrition, Middle Eastern and international wholesome cuisine, and precision 1g ingredient scaling.
                    User Profile:
                    - Goal: {st.session_state.user['goal']}
                    - Diet Type: {st.session_state.user['diet_type']}
                    - Target Calories: {st.session_state.user['daily_calories']} kcal
                    Keep your answers warm, concise, culinary-focused, and practical.
                    """
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=f"{sys_prompt}\nUser: {user_input}"
                    )
                    margot_reply = response.text
                except Exception as e:
                    margot_reply = f"Chef Margot note: I encountered an issue accessing my culinary AI model ({e}). Please ensure your GEMINI_API_KEY is configured in Streamlit Secrets."
            else:
                margot_reply = "I'm ready to cook! To activate my full AI brain, please add `GEMINI_API_KEY` into your Streamlit Cloud Secrets (`Settings -> Secrets`)."

            st.session_state.margot_history.append({"role": "margot", "content": margot_reply})
            st.rerun()
