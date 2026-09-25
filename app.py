import streamlit as st
import pandas as pd
import datetime
import os
import re
import math
from google import genai

# ==========================================
# 1. PAGE SETUP & MODERN STYLING
# ==========================================
st.set_page_config(
    page_title="Munch Me | Smart Nutrition & Chef Assistant",
    page_icon="🍏",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if "lang" not in st.session_state:
    st.session_state.lang = "English"

is_ar = (st.session_state.lang == "العربية")
text_dir = "rtl" if is_ar else "ltr"
font_align = "right" if is_ar else "left"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Tajawal:wght@400;500;700;800&display=swap');
    
    html, body, [class*="css"] {{
        font-family: {'"Tajawal", sans-serif' if is_ar else '"Plus Jakarta Sans", sans-serif'} !important;
        background-color: #F8FAFC;
        color: #1E293B;
        direction: {text_dir};
        text-align: {font_align};
    }}

    .stButton > button {{
        border-radius: 12px !important;
        font-weight: 700 !important;
        border: none !important;
        transition: all 0.2s ease-in-out !important;
        padding: 0.55rem 1.25rem !important;
    }}

    .metric-card {{
        background: white;
        border-radius: 16px;
        padding: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -2px rgba(0,0,0,0.05);
        border: 1px solid #F1F5F9;
        text-align: center;
    }}

    .recipe-card {{
        background: white;
        border-radius: 20px;
        border: 1.5px solid #E2E8F0;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        display: flex;
        flex-direction: column;
        height: 100%;
    }}
    .recipe-card-header {{
        position: relative;
        height: 165px;
        background-color: #F1F5F9;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
    }}
    .recipe-card-header img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
    }}
    .badge-count {{
        position: absolute;
        top: 12px;
        {'left: 12px;' if is_ar else 'right: 12px;'}
        background: rgba(30, 41, 59, 0.85);
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        z-index: 2;
    }}
    .recipe-card-body {{
        padding: 1.25rem;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
    }}
    .macro-pill {{
        border-radius: 10px;
        padding: 6px 10px;
        font-size: 0.8rem;
        font-weight: 700;
        text-align: center;
    }}
    .macro-p {{ background-color: #ECFDF5; color: #059669; }}
    .macro-c {{ background-color: #FEF9C3; color: #CA8A04; }}
    .macro-f {{ background-color: #FFE4E6; color: #E11D48; }}

    .ing-card {{
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 10px 14px;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .ing-title {{
        font-weight: 700;
        color: #1E293B;
        font-size: 0.95rem;
    }}
    .ing-amount {{
        font-weight: 800;
        color: #059669;
        background: #F0FDF4;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.85rem;
    }}

    .note-card {{
        background: #FFFDF9;
        border: 1.5px solid #FDE68A;
        {'border-right: 6px solid #F59E0B;' if is_ar else 'border-left: 6px solid #F59E0B;'}
        border-radius: 14px;
        padding: 0.75rem 1.25rem;
        margin-bottom: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }}
    .note-header {{
        font-weight: 800;
        font-size: 1.05rem;
        color: #92400E;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}

    .chat-bubble {{
        padding: 1rem 1.25rem;
        border-radius: 14px;
        margin-bottom: 0.8rem;
        line-height: 1.5;
    }}
    .chat-user {{
        background: #E2E8F0;
        color: #1E293B;
        text-align: {'left' if is_ar else 'right'};
    }}
    .chat-margot {{
        background: #F0FDF4;
        border: 1px solid #BBF7D0;
        color: #166534;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. BILINGUAL INGREDIENTS & UNIT TRANSLATOR
# ==========================================
INGREDIENTS_TRANSLATION_MAP = {
    "egg": "بيض",
    "eggs": "بيض",
    "olive oil": "زيت زيتون",
    "sourdough": "خبز الساوردو",
    "pita bread (small)": "خبز بيتا صغير",
    "pita bread": "خبز بيتا",
    "toast": "توست أسمر / أبيض",
    "black olives": "زيتون أسود",
    "olives": "زيتون",
    "makdoos": "مكدوس",
    "labneh": "لبنة",
    "cucumber": "خيار",
    "cherry tomatoes": "طماطم كرزية",
    "tomato": "طماطم",
    "tomatoes": "طماطم",
    "chilli flakes": "رقائق الفلفل الحار",
    "chili flakes": "رقائق الفلفل الحار",
    "salt": "ملح طعام",
    "black pepper": "فلفل أسود",
    "avocado": "أفوكادو",
    "lettuce": "خس طازج",
    "rocca": "جرجير",
    "parsley": "بقدونس",
    "mint": "نعناع",
    "cilantro": "كزبرة خضراء",
    "spinach": "سبانخ",
    "chicken breast": "صدر دجاج",
    "chicken": "دجاج",
    "chicken broth": "مرق دجاج",
    "quinoa": "كينوا",
    "mix beans": "فاصولياء مشكلة",
    "corn": "ذرة صفراء",
    "bell pepper": "فلفل رومي حلو",
    "feta cheese": "جبنة فيتا",
    "halloumi": "جبنة حلوم",
    "parmesan": "جبن بارميزان",
    "cheddar": "جبن شيدر",
    "greek yogurt": "زبادي يوناني",
    "yogurt": "زبادي",
    "milk": "حليب",
    "almond milk": "حليب لوز",
    "skim milk": "حليب خالي الدسم",
    "oats": "شوفان",
    "rolled oats": "شوفان حبة كاملة",
    "chia seeds": "بذور الشيا",
    "flax seeds": "بذور الكتان",
    "peanut butter": "زبدة الفول السوداني",
    "almond": "لوز",
    "almonds": "لوز",
    "walnut": "جوز (عين جمل)",
    "walnuts": "جوز",
    "cashew": "كاجو",
    "dates": "تمر",
    "date": "تمر",
    "banana": "موز",
    "green apple": "تفاح أخضر",
    "apple": "تفاح",
    "blueberry": "توت أزرق",
    "blueberries": "توت أزرق",
    "lemon juice": "عصير ليمون",
    "lime juice": "عصير ليمون حامض",
    "garlic": "ثوم",
    "garlic powder": "بودرة ثوم",
    "onion": "بصل",
    "cumin": "كمون",
    "paprika": "بابريكا",
    "smoked paprika": "بابريكا مدخنة",
    "mustard": "خردل",
    "mayonnaise": "مايونيز لايت",
    "honey": "عسل طبيعي"
}

UNITS_TRANSLATION_MAP = {
    "g": "غ",
    "gram": "غ",
    "grams": "غ",
    "ml": "مل",
    "pcs": "حبة",
    "pc": "حبة",
    "slice": "شريحة",
    "slices": "شرائح",
    "tbsp": "ملعقة كبيرة",
    "tsp": "ملعقة صغيرة",
    "cup": "كوب"
}

def translate_ingredient(name):
    if not is_ar:
        return str(name).strip()
    clean_key = str(name).strip().lower()
    return INGREDIENTS_TRANSLATION_MAP.get(clean_key, str(name).strip())

def translate_unit(unit):
    if not is_ar:
        return str(unit).strip()
    clean_u = str(unit).strip().lower()
    return UNITS_TRANSLATION_MAP.get(clean_u, str(unit).strip())

# ==========================================
# 3. NUMERIC & IMAGE HELPERS
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

def resolve_image_url(img_val):
    if not img_val or pd.isna(img_val):
        return ""
    val = str(img_val).strip()
    if not val or val.lower() in ["none", "nan", "#n/a"]:
        return ""

    # Convert Google Drive links
    if "drive.google.com" in val:
        file_id_match = re.search(r"/(?:d|folders|file/d)/([a-zA-Z0-9_-]+)", val) or re.search(r"id=([a-zA-Z0-9_-]+)", val)
        if file_id_match:
            return f"https://drive.google.com/thumbnail?id={file_id_match.group(1)}&sz=w1000"

    # Local file exists
    if os.path.exists(val):
        return val
    if os.path.exists(os.path.join("images", val)):
        return os.path.join("images", val)

    # Raw filename in GitHub repository
    if not val.startswith("http"):
        clean_file = val.replace(" ", "%20")
        return f"https://raw.githubusercontent.com/mevenj-hub/MunchMe/main/{clean_file}"

    return val

def categorize_ingredient(name):
    n = str(name).lower()
    if any(k in n for k in ["sourdough", "bread", "toast", "pita", "rice", "oat", "quinoa", "freekeh", "pasta", "fettuccine", "flour", "tortilla"]):
        return "حبوب ونشويات ومخبوزات" if is_ar else "🌾 Grains, Pasta & Bakery"
    elif any(k in n for k in ["lettuce", "rocca", "cucumber", "tomato", "onion", "garlic", "spinach", "cabbage", "pepper", "broccoli", "carrot", "herb", "parsley", "mint", "cilantro", "zucchini", "mushroom", "potato", "corn"]):
        return "خضار وأعشاب طازجة" if is_ar else "🥬 Vegetables & Greens"
    elif any(k in n for k in ["apple", "banana", "berry", "berries", "strawberry", "lemon", "lime", "date", "orange", "avocado", "mango", "pomegranate"]):
        return "فواكه طازجة" if is_ar else "🍎 Fresh Fruits"
    elif any(k in n for k in ["chicken", "beef", "meat", "turkey", "fish", "salmon", "tuna", "shrimp"]):
        return "لحوم ودواجن وأسماك" if is_ar else "🥩 Meat, Poultry & Seafood"
    elif any(k in n for k in ["milk", "yogurt", "cheese", "halloumi", "labneh", "butter", "egg", "cream"]):
        return "ألبان وأجبان وبيض" if is_ar else "🥛 Dairy, Milk & Eggs"
    elif any(k in n for k in ["almond", "walnut", "cashew", "peanut", "seed", "chia"]):
        return "مكسرات وبذور" if is_ar else "🥜 Nuts & Seeds"
    else:
        return "بهارات وزيوت ومستلزمات" if is_ar else "🧂 Pantry, Oils, Spices & Dressings"

def generate_donut_chart_svg(pro_kcal, carb_kcal, fat_kcal, total_cals):
    total = max(1.0, pro_kcal + carb_kcal + fat_kcal)
    p_pct = round((pro_kcal / total) * 100, 1)
    c_pct = round((carb_kcal / total) * 100, 1)
    p_end = p_pct
    c_end = round(p_pct + c_pct, 1)

    return (
        f'<div style="display:flex; justify-content:center; align-items:center; padding: 15px 0;">'
        f'<div style="width: 175px; height: 175px; border-radius: 50%; '
        f'background: conic-gradient(#059669 0% {p_end}%, #CA8A04 {p_end}% {c_end}%, #E11D48 {c_end}% 100%); '
        f'display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.06);">'
        f'<div style="width: 118px; height: 118px; background: #FFFFFF; border-radius: 50%; '
        f'display: flex; flex-direction: column; align-items: center; justify-content: center;">'
        f'<span style="font-size: 1.6rem; font-weight: 800; color: #0F172A; line-height: 1;">{int(total_cals)}</span>'
        f'<span style="font-size: 0.75rem; font-weight: 700; color: #64748B; margin-top: 4px;">KCAL</span>'
        f'</div></div></div>'
    )

# ==========================================
# 4. SESSION STATE MANAGEMENT
# ==========================================
if "page" not in st.session_state:
    st.session_state.page = 1

if "plan_mode" not in st.session_state:
    st.session_state.plan_mode = "Today (1 Day)"

if "raw_grocery_items" not in st.session_state:
    st.session_state.raw_grocery_items = {}

if "grocery_checked" not in st.session_state:
    st.session_state.grocery_checked = {}

if "recipe_steps_checked" not in st.session_state:
    st.session_state.recipe_steps_checked = {}

if "margot_history" not in st.session_state:
    st.session_state.margot_history = [
        {"role": "margot", "content": "مرحباً بك! أنا مارغو، شيف Munch Me ومساعدتك التغذوية الذكية. كيف يمكنني مساعدتك اليوم؟" if is_ar else "👋 Marhaban! I am Margot, your personal culinary nutritionist. How can I assist you with meal prep, custom substitutions, or recipes today?"}
    ]

if "active_modal_recipe" not in st.session_state:
    st.session_state.active_modal_recipe = None

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
    }

# ==========================================
# 5. MEAL SLOTS & CATEGORIES HIERARCHY
# ==========================================
MEAL_STRUCTURE = {
    "Breakfast": ["Egg Breakfast", "Breakfast Smoothies", "Savory Breakfast", "Sweet Breakfast"],
    "Lunch": ["Chicken Meals", "Fish Meals", "Meat Meals", "Salads", "Vegetarian Meals"],
    "Dinner": ["Chicken Meals", "Fish Meals", "Meat Meals", "Salads", "Vegetarian Meals"],
    "Snacks": ["Side Salads", "Drinks", "Savory Snacks", "Sweet Snacks"]
}

MEAL_SLOTS_AR = {
    "Breakfast": "الفطور",
    "Lunch": "الغداء",
    "Dinner": "العشاء",
    "Snacks": "وجبات خفيفة (سناك)"
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

recipes_summary_df = load_sheet_by_gid("0")
recipe_details_df = load_sheet_by_gid("45255346")

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
        elif "method" in cl:
            col_map[c] = "Method"
        elif "image" in cl:
            col_map[c] = "Image URL"
    recipe_details_df.rename(columns=col_map, inplace=True)
    if "Recipe Name" in recipe_details_df.columns:
        recipe_details_df["Recipe Name"] = recipe_details_df["Recipe Name"].ffill()

if not recipes_summary_df.empty and "Total Calories" in recipes_summary_df.columns:
    recipes_clean_df = recipes_summary_df.dropna(subset=["Menu Item", "Total Calories"]).copy()
    for col in ["Total Calories", "Total Protein", "Total Carbs", "Total Fat"]:
        if col in recipes_clean_df.columns:
            recipes_clean_df[col] = pd.to_numeric(recipes_clean_df[col], errors="coerce")
    recipes_clean_df = recipes_clean_df.dropna(subset=["Total Calories"])
else:
    recipes_clean_df = pd.DataFrame()

# ==========================================
# 7. ENHANCED RECIPE MODAL (IMAGE, DONUT & STEPS)
# ==========================================
if hasattr(st, "dialog"):
    @st.dialog("Recipe Guide / دليل الوصفة", width="large")
    def display_recipe_dialog(rec):
        title_view = f"📖 {rec['name_ar']} ({rec['name']})" if is_ar else f"📖 {rec['name']} ({rec['name_ar']})"
        st.markdown(f"### {title_view}")

        # Top Recipe Image Header inside Dialog
        modal_img = rec.get("resolved_image", "")
        if modal_img:
            st.image(modal_img, use_container_width=True)

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("السعرات" if is_ar else "Calories", f"{int(rec['cals'])} kcal")
        m_col2.metric("بروتين" if is_ar else "Protein", f"{rec['pro']:.1f} g")
        m_col3.metric("كاربوهيدرات" if is_ar else "Carbs", f"{rec['carb']:.1f} g")
        m_col4.metric("دهون" if is_ar else "Fat", f"{rec['fat']:.1f} g")

        guide_tab1, guide_tab2 = st.tabs([
            "📝 المكونات وطريقة الإعداد" if is_ar else "📝 Ingredients & Method", 
            "📊 تحليل نسب الماكروز" if is_ar else "📊 Macro Analytics"
        ])

        with guide_tab1:
            clean_match_name = rec.get("clean_name", rec['name'].replace(" (Side Salad ½)", ""))
            matched_items = pd.DataFrame()
            if not recipe_details_df.empty:
                matched_items = recipe_details_df[
                    recipe_details_df.astype(str).apply(lambda row: clean_match_name.lower() in row.to_string().lower(), axis=1)
                ]

            col_ing, col_steps = st.columns([1, 1.2], gap="medium")

            with col_ing:
                st.markdown(f"**{'🥗 قائمة المقادير:' if is_ar else '🥗 Ingredients:'}**")
                if not matched_items.empty and "Ingredients" in matched_items.columns:
                    for _, irow in matched_items.iterrows():
                        raw_ing_n = str(irow.get("Ingredients", "")).strip()
                        if raw_ing_n and raw_ing_n.lower() != "nan" and raw_ing_n.lower() != "ingredients":
                            q_val = extract_numeric(irow.get("Qtty.", 1))
                            raw_u = str(irow.get("Unit", "g")).strip()
                            if not raw_u or raw_u.lower() == "nan":
                                raw_u = "g"
                            
                            display_ing = translate_ingredient(raw_ing_n)
                            display_u = translate_unit(raw_u)

                            st.markdown(
                                f'<div class="ing-card">'
                                f'<span class="ing-title">{display_ing}</span>'
                                f'<span class="ing-amount">{q_val:g} {display_u}</span>'
                                f'</div>',
                                unsafe_allow_html=True
                            )
                else:
                    st.info("تم تحميل المكونات الأساسية." if is_ar else "Ingredients loaded from master sheet.")

            with col_steps:
                st.markdown(f"**{'👨‍🍳 خطوات التحضير:' if is_ar else '👨‍🍳 Preparation Steps:'}**")
                raw_method = ""
                if not matched_items.empty and "Method" in matched_items.columns:
                    method_vals = matched_items["Method"].dropna().tolist()
                    if method_vals:
                        raw_method = str(method_vals[0]).strip()

                if raw_method and raw_method.lower() != "none" and raw_method.lower() != "nan":
                    steps = [s.strip() for s in re.split(r'\n+|\d+\.\s*', raw_method) if len(s.strip()) > 3]
                    if not steps:
                        steps = [raw_method]

                    for idx, step_text in enumerate(steps, 1):
                        step_key = f"step_{rec['clean_name']}_{idx}"
                        c_chk, c_desc = st.columns([0.15, 0.85])
                        with c_chk:
                            is_done = st.checkbox("", key=step_key, value=st.session_state.recipe_steps_checked.get(step_key, False), label_visibility="collapsed")
                            st.session_state.recipe_steps_checked[step_key] = is_done
                        with c_desc:
                            if is_done:
                                st.markdown(f"<span style='text-decoration: line-through; color: #94A3B8; font-weight:500;'><b>{idx}.</b> {step_text}</span>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"<span style='color: #1E293B; font-weight:600;'><b>{idx}.</b> {step_text}</span>", unsafe_allow_html=True)
                else:
                    st.info("لا توجد تعليمات تحضير مفصلة لهذه الوصفة." if is_ar else "No step-by-step instructions recorded for this meal.")

        with guide_tab2:
            st.markdown(f"#### {'توزيع السعرات الحرارية حسب الماكروز' if is_ar else 'Caloric Contribution by Macro'}")
            
            pro_kcal = float(rec['pro']) * 4
            carb_kcal = float(rec['carb']) * 4
            fat_kcal = float(rec['fat']) * 9
            total_macro_cals = pro_kcal + carb_kcal + fat_kcal

            if total_macro_cals > 0:
                p_pct = round((pro_kcal / total_macro_cals) * 100)
                c_pct = round((carb_kcal / total_macro_cals) * 100)
                f_pct = round((fat_kcal / total_macro_cals) * 100)

                chart_col, legend_col = st.columns([1, 1.2], gap="large")

                with chart_col:
                    donut_html = generate_donut_chart_svg(pro_kcal, carb_kcal, fat_kcal, rec['cals'])
                    st.markdown(donut_html, unsafe_allow_html=True)

                with legend_col:
                    st.markdown(f"<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:12px; padding:12px; margin-bottom:10px;">
                        <span style="font-weight:700; color:#059669;">{'البروتين (4 kcal/g)' if is_ar else 'Protein (4 kcal/g)'}</span>
                        <div style="font-size:1.15rem; font-weight:800; color:#047857;">{rec['pro']:.1f}g ({pro_kcal:.0f} kcal) — {p_pct}%</div>
                    </div>
                    <div style="background:#FEFCE8; border:1px solid #FEF08A; border-radius:12px; padding:12px; margin-bottom:10px;">
                        <span style="font-weight:700; color:#CA8A04;">{'الكاربوهيدرات (4 kcal/g)' if is_ar else 'Carbohydrates (4 kcal/g)'}</span>
                        <div style="font-size:1.15rem; font-weight:800; color:#A16207;">{rec['carb']:.1f}g ({carb_kcal:.0f} kcal) — {c_pct}%</div>
                    </div>
                    <div style="background:#FFF1F2; border:1px solid #FECDD3; border-radius:12px; padding:12px;">
                        <span style="font-weight:700; color:#E11D48;">{'الدهون (9 kcal/g)' if is_ar else 'Total Fat (9 kcal/g)'}</span>
                        <div style="font-size:1.15rem; font-weight:800; color:#BE123C;">{rec['fat']:.1f}g ({fat_kcal:.0f} kcal) — {f_pct}%</div>
                    </div>
                    """, unsafe_allow_html=True)
else:
    def display_recipe_dialog(rec):
        st.session_state.active_modal_recipe = rec

# ==========================================
# 8. HEADER, LOGO & LANGUAGE SWITCHER
# ==========================================
h_col1, h_col2, h_col3 = st.columns([1.5, 6, 2.5])

with h_col1:
    if os.path.exists("logo.jpg"):
        st.image("logo.jpg", width=85)
    elif os.path.exists("logo.png"):
        st.image("logo.png", width=85)
    elif os.path.exists("Munch Me App Logo.jpg"):
        st.image("Munch Me App Logo.jpg", width=85)
    else:
        st.image("https://raw.githubusercontent.com/mevenj-hub/MunchMe/main/logo.jpg", width=85)

with h_col2:
    if is_ar:
        st.markdown("<h2 style='margin-bottom:0; font-weight:800; color:#0F172A;'>مانش مي | Munch Me</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color:#64748B; margin-top:0; font-size:0.95rem;'>محرك التغذية الدقيقة والشيف الذكي</p>", unsafe_allow_html=True)
    else:
        st.markdown("<h2 style='margin-bottom:0; font-weight:800; color:#0F172A;'>Munch Me</h2>", unsafe_allow_html=True)
        st.markdown("<p style='color:#64748B; margin-top:0; font-size:0.95rem;'>Smart Nutrition & Chef Assistant</p>", unsafe_allow_html=True)

with h_col3:
    lang_selection = st.radio(
        "Language / اللغة",
        ["English", "العربية"],
        horizontal=True,
        index=0 if st.session_state.lang == "English" else 1
    )
    if lang_selection != st.session_state.lang:
        st.session_state.lang = lang_selection
        st.rerun()

st.markdown("<hr style='border:0; border-top:1px solid #E2E8F0; margin: 10px 0 25px 0;'>", unsafe_allow_html=True)


# ==============================================================================
# PAGE 1: USER ONBOARDING
# ==============================================================================
if st.session_state.page == 1:
    st.markdown(f"### {'الملف الشخصي والأهداف التغذوية' if is_ar else 'Profile & Nutrition Goals'}")
    st.caption("أدخل بياناتك الفسيولوجية لاحتساب معدل الأيض وضبط الماكروز." if is_ar else "Complete your physiological parameters to configure your meal matrix.")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.session_state.user["name"] = st.text_input(
            "الاسم الكامل" if is_ar else "Full Name",
            value=st.session_state.user["name"],
            placeholder="سارة الأحمد" if is_ar else "e.g. Sarah"
        )
        
        st.session_state.user["dob"] = st.date_input(
            "تاريخ الميلاد" if is_ar else "Date of Birth (Calendar Select)",
            value=st.session_state.user["dob"],
            min_value=datetime.date(1940, 1, 1),
            max_value=datetime.date.today()
        )

        st.markdown(f"<label style='font-size:0.9rem; font-weight:600;'>{'الجنس' if is_ar else 'Biological Sex'}</label>", unsafe_allow_html=True)
        gender_options = ["أنثى", "ذكر"] if is_ar else ["Female", "Male"]
        curr_g = "أنثى" if (st.session_state.user.get("gender") == "Female" and is_ar) else ("ذكر" if is_ar else st.session_state.user.get("gender", "Female"))
        
        if hasattr(st, "pills"):
            selected_gender = st.pills("Sex", options=gender_options, default=curr_g, label_visibility="collapsed")
            if selected_gender:
                st.session_state.user["gender"] = "Female" if (selected_gender in ["Female", "أنثى"]) else "Male"
        else:
            selected_gender = st.radio("Sex", gender_options, index=gender_options.index(curr_g), horizontal=True, label_visibility="collapsed")
            st.session_state.user["gender"] = "Female" if (selected_gender in ["Female", "أنثى"]) else "Male"

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        h_col1, h_col2 = st.columns([3, 2])
        with h_col1:
            st.session_state.user["height_val"] = st.number_input("الطول" if is_ar else "Height", value=float(st.session_state.user["height_val"]), step=0.5)
        with h_col2:
            st.session_state.user["height_unit"] = st.selectbox("الوحدة" if is_ar else "Height Unit", ["cm", "inch", "foot"], index=["cm", "inch", "foot"].index(st.session_state.user["height_unit"]))

        w_col1, w_col2 = st.columns([3, 2])
        with w_col1:
            st.session_state.user["weight_val"] = st.number_input("الوزن" if is_ar else "Weight", value=float(st.session_state.user["weight_val"]), step=0.5)
        with w_col2:
            st.session_state.user["weight_unit"] = st.selectbox("الوحدة" if is_ar else "Weight Unit", ["kg", "pound"], index=["kg", "pound"].index(st.session_state.user["weight_unit"]))

    with col2:
        st.markdown(f"<label style='font-size:0.9rem; font-weight:600;'>{'الهدف الأساسي' if is_ar else 'Primary Goal'}</label>", unsafe_allow_html=True)
        goal_map = {
            "خسارة وزن": "Weight Loss", "بناء عضل": "Muscle Gain", "تثبيت الوزن": "Maintenance", "لياقة وتحمل": "Endurance"
        } if is_ar else {
            "Weight Loss": "Weight Loss", "Muscle Gain": "Muscle Gain", "Maintenance": "Maintenance", "Endurance": "Endurance"
        }
        goal_options = list(goal_map.keys())
        curr_goal_display = [k for k, v in goal_map.items() if v == st.session_state.user.get("goal")][0]

        if hasattr(st, "pills"):
            selected_goal = st.pills("Goal", options=goal_options, default=curr_goal_display, label_visibility="collapsed")
            if selected_goal:
                st.session_state.user["goal"] = goal_map[selected_goal]
        else:
            selected_goal = st.radio("Goal", goal_options, index=goal_options.index(curr_goal_display), horizontal=True, label_visibility="collapsed")
            st.session_state.user["goal"] = goal_map[selected_goal]

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        st.markdown(f"<label style='font-size:0.9rem; font-weight:600;'>{'نوع الحمية الغذائية' if is_ar else 'Type of Diet'}</label>", unsafe_allow_html=True)
        diet_map = {
            "متوازنة": "Balanced", "عالية البروتين": "High Protein", "قليلة الكارب": "Low Carb", "كيتو": "Keto", "نباتية": "Vegetarian"
        } if is_ar else {
            "Balanced": "Balanced", "High Protein": "High Protein", "Low Carb": "Low Carb", "Keto": "Keto", "Vegetarian": "Vegetarian"
        }
        diet_options = list(diet_map.keys())
        curr_diet_display = [k for k, v in diet_map.items() if v == st.session_state.user.get("diet_type")][0]

        if hasattr(st, "pills"):
            selected_diet = st.pills("Diet", options=diet_options, default=curr_diet_display, label_visibility="collapsed")
            if selected_diet:
                st.session_state.user["diet_type"] = diet_map[selected_diet]
        else:
            selected_diet = st.radio("Diet", diet_options, index=diet_options.index(curr_diet_display), horizontal=True, label_visibility="collapsed")
            st.session_state.user["diet_type"] = diet_map[selected_diet]

        st.markdown("<div style='height: 35px;'></div>", unsafe_allow_html=True)

        btn_continue_text = "الانتقال إلى جدول الوجبات ←" if is_ar else "Continue to Meal Dashboard →"
        if st.button(btn_continue_text, type="primary", use_container_width=True):
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
# PAGE 2: MEAL DASHBOARD, NOTE-STYLE GROCERY & MARGOT
# ==============================================================================
elif st.session_state.page == 2:
    nav1, nav2, nav3 = st.columns([4, 2, 1])
    with nav1:
        st.markdown(f"### {'لوحة تحكم الوجبات والماكروز' if is_ar else 'Meal & Recipe Nutrition Dashboard'}")
        st.caption("تحليل الماكروز، وصفات دقيقة بدليل التحضير وقائمة التسوق الذكية" if is_ar else "Interactive macro analysis, recipe guides, and grocery planning")
    
    with nav2:
        plan_options = ["اليوم (يوم واحد)", "هذا الأسبوع (7 أيام)"] if is_ar else ["Today (1 Day)", "This Week (7 Days)"]
        curr_plan_idx = 0 if "1" in st.session_state.plan_mode else 1
        plan_selection = st.radio(
            "Horizon",
            plan_options,
            horizontal=True,
            index=curr_plan_idx,
            label_visibility="collapsed"
        )
        norm_plan = "Today (1 Day)" if ("1" in plan_selection or "اليوم" in plan_selection) else "This Week (7 Days)"
        if norm_plan != st.session_state.plan_mode:
            st.session_state.plan_mode = norm_plan
            st.rerun()

    with nav3:
        btn_back_text = "تعديل الملف →" if is_ar else "← Edit Profile"
        if st.button(btn_back_text, use_container_width=True):
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
            <span style="font-size: 0.85rem; color: #64748B; font-weight:700;">{'السعرات الحرارية' if is_ar else 'ENERGY'} ({st.session_state.plan_mode})</span>
            <h3 style="margin:4px 0 0 0; color:#0F172A;">{int(c_cals)} <span style="font-size:0.9rem; font-weight:500;">/ {target_cals} kcal</span></h3>
            <p style="margin:2px 0 0 0; font-size:0.8rem; color:#10B981; font-weight:700;">{'المستهلك' if is_ar else 'Consumed'}: {int(c_cals)} | {'المتبقي' if is_ar else 'Left'}: {int(left_cals)} kcal</p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(min(1.0, c_cals / max(1, target_cals)))

    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <span style="font-size: 0.85rem; color: #059669; font-weight:700;">{'البروتين' if is_ar else 'PROTEIN'}</span>
            <h3 style="margin:4px 0 0 0; color:#0F172A;">{int(c_pro)}g <span style="font-size:0.9rem; font-weight:500;">/ {target_pro}g</span></h3>
            <p style="margin:2px 0 0 0; font-size:0.8rem; color:#059669; font-weight:700;">{'المستهلك' if is_ar else 'Consumed'}: {int(c_pro)}g | {'المتبقي' if is_ar else 'Left'}: {int(left_pro)}g</p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(min(1.0, c_pro / max(1, target_pro)))

    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <span style="font-size: 0.85rem; color: #CA8A04; font-weight:700;">{'الكاربوهيدرات' if is_ar else 'CARBS'}</span>
            <h3 style="margin:4px 0 0 0; color:#0F172A;">{int(c_carb)}g <span style="font-size:0.9rem; font-weight:500;">/ {target_carb}g</span></h3>
            <p style="margin:2px 0 0 0; font-size:0.8rem; color:#CA8A04; font-weight:700;">{'المستهلك' if is_ar else 'Consumed'}: {int(c_carb)}g | {'المتبقي' if is_ar else 'Left'}: {int(left_carb)}g</p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(min(1.0, c_carb / max(1, target_carb)))

    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <span style="font-size: 0.85rem; color: #E11D48; font-weight:700;">{'الدهون' if is_ar else 'FAT'}</span>
            <h3 style="margin:4px 0 0 0; color:#0F172A;">{int(c_fat)}g <span style="font-size:0.9rem; font-weight:500;">/ {target_fat}g</span></h3>
            <p style="margin:2px 0 0 0; font-size:0.8rem; color:#E11D48; font-weight:700;">{'المستهلك' if is_ar else 'Consumed'}: {int(c_fat)}g | {'المتبقي' if is_ar else 'Left'}: {int(left_fat)}g</p>
        </div>
        """, unsafe_allow_html=True)
        st.progress(min(1.0, c_fat / max(1, target_fat)))

    st.markdown("<hr style='border:0; border-top:1px solid #E2E8F0; margin: 25px 0;'>", unsafe_allow_html=True)

    tab_titles = ["🍽️ دليل وقائمة الوجبات", "📝 قائمة التسوق الذكية", "👩‍🍳 الشيف مارغو AI"] if is_ar else ["🍽️ Recipes & Meal Catalog", "📝 Grocery Shopping Note", "👩‍🍳 Margot AI Chef Assistant"]
    tab_meals, tab_grocery, tab_margot = st.tabs(tab_titles)

    # ==========================================
    # TAB 1: MEAL CATALOG & SEARCH
    # ==========================================
    with tab_meals:
        if recipes_clean_df.empty:
            st.warning("Connecting to Google Sheets...")
        else:
            search_query = st.text_input(
                "🔍 بحث عن وجبة بالاسم (عربي أو إنجليزي)..." if is_ar else "🔍 Search recipe by name (English or Arabic)...",
                value="",
                placeholder="e.g. Chicken Wrap, دجاج سيزر, Salad..."
            )

            st.markdown(f"#### {'اختر نوع الوجبة' if is_ar else 'Select Meal Slot'}")
            slot_options = list(MEAL_STRUCTURE.keys())
            slot_display = [MEAL_SLOTS_AR[s] for s in slot_options] if is_ar else slot_options
            
            selected_slot_raw = st.pills("Slot", options=slot_display, default=slot_display[0], label_visibility="collapsed") or slot_display[0]
            meal_slot = slot_options[slot_display.index(selected_slot_raw)]

            available_subcats = MEAL_STRUCTURE[meal_slot]
            st.markdown(f"**{'التصنيفات المتاحة:' if is_ar else 'Categories:'}**")
            subcat_choice = st.pills(
                "Subcats",
                options=["All" if not is_ar else "الكل"] + available_subcats,
                default="All" if not is_ar else "الكل",
                label_visibility="collapsed"
            ) or ("All" if not is_ar else "الكل")

            if meal_slot == "Snacks" and (subcat_choice in ["All", "الكل", "Side Salads"]):
                target_categories = [c for c in available_subcats if c != "Side Salads"] + ["Salads"]
            else:
                target_categories = available_subcats

            if subcat_choice in ["All", "الكل"]:
                filtered_df = recipes_clean_df[recipes_clean_df["Categories"].isin(target_categories)].copy()
            elif subcat_choice == "Side Salads":
                filtered_df = recipes_clean_df[recipes_clean_df["Categories"] == "Salads"].copy()
            else:
                filtered_df = recipes_clean_df[recipes_clean_df["Categories"] == subcat_choice].copy()

            if search_query.strip():
                q = search_query.strip().lower()
                filtered_df = filtered_df[
                    filtered_df["Menu Item"].astype(str).str.lower().str.contains(q, na=False) |
                    filtered_df["Menu Item Ar"].astype(str).str.lower().str.contains(q, na=False)
                ]

            if filtered_df.empty:
                st.info("لا توجد وجبات تطابق البحث حالياً." if is_ar else "No recipes found matching your selection.")
            else:
                recipes = filtered_df.to_dict(orient="records")
                cols = st.columns(4)

                for idx, recipe in enumerate(recipes):
                    with cols[idx % 4]:
                        raw_cat = str(recipe.get("Categories", "")).strip()
                        name_en = str(recipe.get("Menu Item", f"Recipe #{idx+1}")).strip()
                        name_ar = str(recipe.get("Menu Item Ar", "")).strip()

                        # Image resolution (from Items Menu sheet or Calories Data details)
                        raw_img = recipe.get("Image", recipe.get("image", recipe.get("Image URL", "")))
                        if not raw_img and not recipe_details_df.empty and "Image URL" in recipe_details_df.columns:
                            m_match = recipe_details_df[recipe_details_df["Recipe Name"].astype(str).str.lower().str.strip() == name_en.lower()]
                            if not m_match.empty:
                                raw_img = m_match["Image URL"].dropna().iloc[0] if not m_match["Image URL"].dropna().empty else ""
                        
                        resolved_img = resolve_image_url(raw_img)

                        is_side_salad = (meal_slot == "Snacks" and (raw_cat == "Salads" or subcat_choice == "Side Salads"))
                        portion_multiplier = 0.5 if is_side_salad else 1.0

                        cals = float(recipe.get("Total Calories", 0)) * portion_multiplier
                        pro = float(recipe.get("Total Protein", 0)) * portion_multiplier
                        carb = float(recipe.get("Total Carbs", 0)) * portion_multiplier
                        fat = float(recipe.get("Total Fat", 0)) * portion_multiplier

                        display_title = f"{name_ar}<br><span style='font-size:0.85rem; color:#64748B; font-weight:500;'>{name_en}</span>" if is_ar else f"{name_en}<br><span style='font-size:0.85rem; color:#64748B; font-weight:500;'>{name_ar}</span>"
                        display_badge = ("سلطة جانبية (نصف حصة)" if is_ar else "Side Salad (½ Portion)") if is_side_salad else raw_cat

                        header_media = f'<img src="{resolved_img}">' if resolved_img else '<div style="font-size:3.5rem;">🥗</div>'

                        st.markdown(f"""
                        <div class="recipe-card">
                            <div class="recipe-card-header">
                                {header_media}
                                <div class="badge-count">{display_badge}</div>
                            </div>
                            <div class="recipe-card-body">
                                <div style="font-weight:700; font-size:1rem; color:#0F172A; min-height:48px; line-height:1.2;">
                                    {display_title}
                                </div>
                                <div style="display:flex; justify-content:space-between; align-items:center; margin: 8px 0;">
                                    <div>
                                        <span style="font-size:0.75rem; color:#64748B; font-weight:700;">{'السعرات' if is_ar else 'ENERGY'}</span>
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
                            guide_btn_label = "طريقة التحضير" if is_ar else "View Guide"
                            if st.button(guide_btn_label, key=f"guide_{meal_slot}_{idx}", use_container_width=True):
                                current_selected = {
                                    "name": f"{name_en} (Side Salad ½)" if is_side_salad else name_en,
                                    "clean_name": name_en,
                                    "name_ar": name_ar,
                                    "cals": cals,
                                    "pro": pro,
                                    "carb": carb,
                                    "fat": fat,
                                    "resolved_image": resolved_img,
                                    "details": recipe
                                }
                                display_recipe_dialog(current_selected)

                        with c_action2:
                            add_label = ("+ تناول اليوم" if "1" in st.session_state.plan_mode else "+ أضف للأسبوع") if is_ar else ("+ Eat Today" if "Today" in st.session_state.plan_mode else "+ Add to Week")
                            if st.button(add_label, key=f"eat_{meal_slot}_{idx}", use_container_width=True):
                                st.session_state.user["consumed_calories"] += cals
                                st.session_state.user["consumed_protein"] += pro
                                st.session_state.user["consumed_carbs"] += carb
                                st.session_state.user["consumed_fat"] += fat

                                if not recipe_details_df.empty and "Ingredients" in recipe_details_df.columns:
                                    matched_rows = recipe_details_df[
                                        recipe_details_df["Recipe Name"].astype(str).str.lower().str.strip() == name_en.lower()
                                    ]
                                    if matched_rows.empty:
                                        matched_rows = recipe_details_df[
                                            recipe_details_df.astype(str).apply(lambda r: name_en.lower() in r.to_string().lower(), axis=1)
                                        ]

                                    for _, ing_row in matched_rows.iterrows():
                                        raw_ing_n = str(ing_row.get("Ingredients", "")).strip()
                                        if raw_ing_n and raw_ing_n.lower() != "nan" and raw_ing_n.lower() != "ingredients":
                                            raw_q = extract_numeric(ing_row.get("Qtty.", 100)) * portion_multiplier
                                            raw_u = str(ing_row.get("Unit", "g")).strip()
                                            if not raw_u or raw_u.lower() == "nan":
                                                raw_u = "g"
                                            
                                            ing_cat = categorize_ingredient(raw_ing_n)

                                            if raw_ing_n in st.session_state.raw_grocery_items:
                                                st.session_state.raw_grocery_items[raw_ing_n]["quantity"] += raw_q
                                            else:
                                                st.session_state.raw_grocery_items[raw_ing_n] = {
                                                    "quantity": raw_q,
                                                    "unit": raw_u,
                                                    "category": ing_cat
                                                }
                                st.rerun()

    # ==========================================
    # TAB 2: NOTE-STYLE GROCERY LIST WITH CHECKBOXES
    # ==========================================
    with tab_grocery:
        st.markdown(f"### {'📝 مفكرة التسوق الذكية للمكونات' if is_ar else '📝 Smart Grocery Notepad'} ({st.session_state.plan_mode})")
        st.caption("قائمة تفاعلية بالمكونات مقسمة حسب أقسام السوبرماركت مع خاصية الشطب عند الشراء أو التوفر." if is_ar else "Interactive grocery checklist grouped by supermarket aisle with live check-off features.")

        if not st.session_state.raw_grocery_items:
            st.info("مفكرة التسوق فارغة! اضغط على '+ تناول اليوم' أو '+ أضف للأسبوع' في أي وصفة لإضافة مقاديرها تلقائياً." if is_ar else "Your notepad is empty! Click '+ Eat Today' or '+ Add to Week' on any recipe card to build your ingredient list.")
        else:
            items_by_cat = {}
            for raw_ing_name, data in st.session_state.raw_grocery_items.items():
                cat = data.get("category", "بهارات وزيوت ومستلزمات" if is_ar else "🧂 Pantry, Oils, Spices & Dressings")
                if cat not in items_by_cat:
                    items_by_cat[cat] = []
                
                q_val = round(data["quantity"], 1)
                if q_val.is_integer():
                    q_val = int(q_val)
                
                display_name = translate_ingredient(raw_ing_name)
                display_unit = translate_unit(data["unit"])
                    
                items_by_cat[cat].append({
                    "raw_key": raw_ing_name,
                    "name": display_name,
                    "amount": f"{q_val} {display_unit}"
                })

            for section, items in sorted(items_by_cat.items()):
                st.markdown(f"""
                <div class="note-card">
                    <div class="note-header">
                        <span>{section}</span>
                        <span style="font-size:0.85rem; font-weight:700; color:#B45309;">({len(items)} {'أصناف' if is_ar else 'items'})</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                for item in items:
                    c_chk, c_txt = st.columns([1, 11])
                    chk_key = f"chk_{item['raw_key']}"
                    
                    with c_chk:
                        is_checked = st.checkbox("", key=chk_key, value=st.session_state.grocery_checked.get(item['raw_key'], False), label_visibility="collapsed")
                        st.session_state.grocery_checked[item['raw_key']] = is_checked
                    
                    with c_txt:
                        if is_checked:
                            st.markdown(f"<span style='text-decoration: line-through; color: #94A3B8; font-weight:500;'>{item['name']} — <b>{item['amount']}</b> ✅ ({'متوفر / تم الشراء' if is_ar else 'Bought / Available'})</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<span style='color: #1E293B; font-weight:600;'>{item['name']}</span> — <span style='color:#059669; font-weight:700;'>{item['amount']}</span>", unsafe_allow_html=True)

                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            if st.button("مسح قائمة التسوق بالكامل" if is_ar else "Clear Shopping Notepad", type="secondary"):
                st.session_state.raw_grocery_items = {}
                st.session_state.grocery_checked = {}
                st.session_state.user["consumed_calories"] = 0.0
                st.session_state.user["consumed_protein"] = 0.0
                st.session_state.user["consumed_carbs"] = 0.0
                st.session_state.user["consumed_fat"] = 0.0
                st.rerun()

    # ==========================================
    # TAB 3: MARGOT AI CHEF ASSISTANT
    # ==========================================
    with tab_margot:
        st.markdown(f"### {'👩‍🍳 الشيف مارغو | أخصائية الطهي والتغذية' if is_ar else '👩‍🍳 Margot | Culinary Nutritionist & AI Chef'}")
        st.caption("اسأل مارغو عن بدائل المكونات، أسرار الطهي الصحي، أو تعديل الوصفات حسب هدفك." if is_ar else "Ask Margot about ingredient swaps, culinary techniques, prep steps, or diet tailoring.")

        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.margot_history:
                if msg["role"] == "user":
                    st.markdown(f"<div class='chat-bubble chat-user'><b>{'أنت' if is_ar else 'You'}:</b><br>{msg['content']}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='chat-bubble chat-margot'><b>👩‍🍳 {'مارغو' if is_ar else 'Margot'}:</b><br>{msg['content']}</div>", unsafe_allow_html=True)

        user_input = st.chat_input("اطلب من مارغو بديلاً، نصيحة تحضير، أو تعديل حصة..." if is_ar else "Ask Margot for a recipe substitution, cooking tip, or custom portion...")
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
                    lang_instruction = "Respond fluently in clear Modern Standard Arabic (العربية الفصحى)." if is_ar else "Respond in English."
                    sys_prompt = f"""
                    You are Margot, the personal AI Chef Assistant for Munch Me. 
                    You specialize in clinical nutrition, wholesome Middle Eastern and international cooking, and precision ingredient scaling.
                    User Profile:
                    - Goal: {st.session_state.user['goal']}
                    - Diet Type: {st.session_state.user['diet_type']}
                    - Target Calories: {st.session_state.user['daily_calories']} kcal
                    Language directive: {lang_instruction}
                    Keep answers warm, concise, culinary-focused, and practical.
                    """
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=f"{sys_prompt}\nUser: {user_input}"
                    )
                    margot_reply = response.text
                except Exception as e:
                    margot_reply = f"ملاحظة الشيف مارغو: واجهت مشكلة في الوصول للذكاء الاصطناعي ({e})" if is_ar else f"Chef Margot note: I encountered an issue accessing my AI model ({e})."
            else:
                margot_reply = "لتفعيل ذكاء الشيف مارغو، يرجى إضافة مفتاح `GEMINI_API_KEY` داخل إعدادات Streamlit Secrets." if is_ar else "I'm ready to cook! To activate my full AI brain, please add `GEMINI_API_KEY` into your Streamlit Cloud Secrets (`Settings -> Secrets`)."

            st.session_state.margot_history.append({"role": "margot", "content": margot_reply})
            st.rerun()
