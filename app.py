import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import random
from treys import Card, Evaluator, Deck
from matplotlib.colors import ListedColormap
import os

# --- STREAMLIT UI SETUP & CUSTOM CSS (BLACK & YELLOW) ---
st.set_page_config(page_title="YAMALcity.pokahh - Calculator", layout="wide")

st.markdown("""
    <style>
    /* HIDE STREAMLIT BRANDING & MENUS */
    [data-testid="stHeader"] {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    footer {visibility: hidden;}

    /* Forces the app to allow pinch-to-zoom on mobile */
    html, body, [class*="css"] {
        touch-action: manipulation;
        zoom: 1;
    }
    
    /* Makes sure data grids can be scrolled horizontally on small screens */
    div[data-testid="stDataFrame"] {
        overflow-x: auto;
        touch-action: pan-x pan-y pinch-zoom;
    }
    .stApp { background-color: #0E1117; color: white; }
    label, p, .stRadio > div > label, .stSelectbox > label {
        color: white !important;
        font-weight: 500 !important;
    }
    div.stButton > button:first-child, div.stButton > button:first-child * {
        background-color: #FFD700 !important;
        color: black !important;
        font-weight: bold !important;
        border: none !important;
    }
    div.stButton > button:first-child:hover, div.stButton > button:first-child:hover * {
        background-color: #E6C200 !important;
        color: black !important;
    }
    </style>
""", unsafe_allow_html=True)

if os.path.exists("logo.jpg"): st.image("logo.jpg", width=120)
elif os.path.exists("logo.png"): st.image("logo.png", width=120)

st.title("♠️ YAMALcity.pokahh")
st.divider()

# ---------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------
pos_full_names = {
    "UTG": "Under the Gun", "MP": "Middle Position", "CO": "Cutoff", 
    "BTN": "Button", "SB": "Small Blind", "BB": "Big Blind"
}

def card_to_emoji(card_str):
    if not card_str or len(card_str) < 2: return card_str
    mapping = {'s': '♠️', 'h': '♥️', 'd': '♦️', 'c': '♣️'}
    return f"{card_str[0].upper()}{mapping.get(card_str[1].lower(), card_str[1])}"

# ---------------------------------------------------------------
# DEFAULT RANGES & SESSION STATE 
# ---------------------------------------------------------------
ranks_str = "AKQJT98765432"
suits = ['s','h','d','c']

DEFAULT_RANGES = {
    "UTG": {"Open": "22+, A2s+, KTs+, QTs+, JTs, T9s, 98s, 87s, 76s, AKo, AQo, AJo", "3-Bet": "QQ+, T9s, 87s, AKs, AKo, A5s, A4s, A3s, A2s"},
    "MP": {"Open": "22+, A2s+, KTs+, QTs+, JTs, T9s, 98s, 87s, 76s, AKo, AQo, AJo", "3-Bet": "QQ+, T9s, 87s, AKs, AKo, A5s, A4s, A3s, A2s"},
    "CO": {"Open": "22+, A2s+, K7s+, Q9s+, JTs-43s, J9s-53s, ATo+, KJo+", "3-Bet": "JJ+, AKs, AKo, A7s, A5s-A2s, T9s, 87s, 54s"},
    "BTN": {"Open": "22+, A2s+, K2s+, Q5s+, J7s+, T9s-43s, T8s-53s, T7s-96s, A7o+, K9o+, QTo+, JTo", "3-Bet": "99+, ATs+, KJs+, QJs, JTs, AQo+, A5s-A2s, 97s, 75s"},
    "SB": {
        "Open": "22+, A2s+, K2s+, Q5s+, J7s+, T9s-43s, T8s-53s, T7s-96s, A8o+, K9o+, QTo+, J9o+, 98o",
        "3-Bet vs Early": "QQ+, AKs, AKo, T9s, 87s, A5s-A2s",
        "3-Bet vs Late": "99+, 44-22, A2s+, KJs+, K7s-K5s, Q9s, J9s, T8s, 98s, 87s, 76s, 65s, 54s, AJo+, KQo"
    },
    "BB": {
        "Open": "22+, A2s+, K2s+, Q5s+, J7s+, T9s-43s, T8s-53s, T7s-96s, A8o+, K9o+, QTo+, J9o+, 98o",
        "3-Bet vs Early": "QQ+, AKs, AKo, T9s, 87s, A5s-A2s",
        "3-Bet vs Late": "99+, 44-22, A2s+, KJs+, K7s-K5s, Q9s, J9s, T8s, 98s, 87s, 76s, 65s, 54s, AJo+, KQo"
    }
}

if "custom_ranges" not in st.session_state or "3-Bet vs Late" not in st.session_state.custom_ranges["SB"]:
    st.session_state.custom_ranges = DEFAULT_RANGES.copy()

# ---------------------------------------------------------------
# ADVANCED POKER MATH ENGINE (Hybrid Exact/Monte Carlo)
# ---------------------------------------------------------------
def expand_range(range_string):
    if not range_string or range_string.strip() == "": return []
    rng = range_string.replace(" ", "").split(",")
    out = []
    for itm in rng:
        try:
            if '-' in itm:
                start, end = itm.split('-')
                if len(start) == 2 and len(end) == 2:
                    i1, i2 = ranks_str.index(start[0]), ranks_str.index(end[0])
                    out.extend([ranks_str[i]*2 for i in range(min(i1,i2), max(i1,i2)+1)])
                elif len(start) == 3 and len(end) == 3:
                    s_type = start[2]
                    if start[0] == end[0]:
                        i1, i2 = ranks_str.index(start[1]), ranks_str.index(end[1])
                        out.extend([f"{start[0]}{ranks_str[i]}{s_type}" for i in range(min(i1,i2), max(i1,i2)+1)])
                    else:
                        i1, i2 = ranks_str.index(start[0]), ranks_str.index(end[0])
                        gap = ranks_str.index(start[1]) - i1
                        out.extend([f"{ranks_str[i]}{ranks_str[i+gap]}{s_type}" for i in range(min(i1,i2), max(i1,i2)+1)])
            elif itm.endswith('+'):
                if len(itm) == 3:
                    idx = ranks_str.index(itm[0])
                    out.extend([ranks_str[i]*2 for i in range(0, idx+1)])
                elif len(itm) == 4:
                    h, l, s = itm[0], itm[1], itm[2]
                    idx_h, idx_l = ranks_str.index(h), ranks_str.index(l)
                    out.extend([f"{h}{ranks_str[i]}{s}" for i in range(idx_h+1, idx_l+1)])
            else:
                out.append(itm)
        except Exception: pass
    return list(set(out))

def exact_cards(hand_str, dead_cards=None):
    dead_cards = dead_cards or []
    if len(hand_str) < 2: return None, None
    r1, r2 = hand_str[0], hand_str[1]
    def get_card(rank, avoid):
        for _ in range(50):
            c_str = rank + random.choice(suits)
            c = Card.new(c_str)
            if c not in avoid: return c, c_str
        return None, None
    if len(hand_str) == 2: 
        c1, s1 = get_card(r1, dead_cards)
        c2, s2 = get_card(r2, dead_cards + [c1])
        return [c1, c2], s1 + s2
    elif hand_str[2] == 's': 
        for _ in range(50):
            s = random.choice(suits)
            c1, c2 = Card.new(r1+s), Card.new(r2+s)
            if c1 not in dead_cards and c2 not in dead_cards: return [c1, c2], (r1+s) + (r2+s)
    elif hand_str[2] == 'o': 
        for _ in range(50):
            s1, s2 = random.choice(suits), random.choice(suits)
            if s1 != s2:
                c1, c2 = Card.new(r1+s1), Card.new(r2+s2)
                if c1 not in dead_cards and c2 not in dead_cards: return [c1, c2], (r1+s1) + (r2+s2)
    return None, None

def get_all_combos(hand_str, dead_cards):
    combos = []
    if len(hand_str) < 2: return combos
    r1, r2 = hand_str[0], hand_str[1]
    if len(hand_str) == 2:
        for i in range(4):
            for j in range(i+1, 4):
                c1, c2 = Card.new(r1+suits[i]), Card.new(r2+suits[j])
                if c1 not in dead_cards and c2 not in dead_cards: combos.append([c1, c2])
    elif hand_str[2] == 's':
        for s in suits:
            c1, c2 = Card.new(r1+s), Card.new(r2+s)
            if c1 not in dead_cards and c2 not in dead_cards: combos.append([c1, c2])
    elif hand_str[2] == 'o':
        for s1 in suits:
            for s2 in suits:
                if s1 != s2:
                    c1, c2 = Card.new(r1+s1), Card.new(r2+s2)
                    if c1 not in dead_cards and c2 not in dead_cards: combos.append([c1, c2])
    return combos

def build_grid():
    r = list("AKQJT98765432")
    g = pd.DataFrame("", index=r, columns=r)
    for r1 in r:
        for r2 in r:
            if r1==r2: g.loc[r1,r2]=r1+r2
            elif ranks_str.index(r1) < ranks_str.index(r2): g.loc[r1,r2]=r1+r2+"s"
            else: g.loc[r1,r2]=r2+r1+"o"
    return g

def evaluate_street_equity(hero_cards, vill_range, current_board, evaluator, deck_cards):
    results = {}
    total_w, total_l, total_t = 0, 0, 0
    dead_base = hero_cards + current_board
    
    cards_to_draw = 5 - len(current_board)
    
    for hand_str in vill_range:
        valid_combos = get_all_combos(hand_str, dead_base)
        if not valid_combos: continue
        
        w, l, t = 0, 0, 0
        for v_cards in valid_combos:
            # --- THE HYBRID ROUTER ---
            
            # 1. RIVER: Exact Evaluation (No Runouts)
            if cards_to_draw == 0:
                hs = evaluator.evaluate(current_board, hero_cards)
                vs = evaluator.evaluate(current_board, v_cards)
                if hs < vs: w += 1
                elif hs > vs: l += 1
                else: t += 1
                continue
            
            # 2. FLOP & TURN: Runouts Needed
            dead_now = dead_base + v_cards
            available_deck = [c for c in deck_cards if c not in dead_now]
            
            if cards_to_draw == 1:
                runouts = [[c] for c in available_deck] # Exact Turn Math (44 cards)
            else:
                runouts = [random.sample(available_deck, 2) for _ in range(150)] # Monte Carlo Flop
                
            for runout in runouts:
                final_board = current_board + runout
                hs = evaluator.evaluate(final_board, hero_cards)
                vs = evaluator.evaluate(final_board, v_cards)
                if hs < vs: w += 1
                elif hs > vs: l += 1
                else: t += 1
                
        total_cell = w + l + t
        if total_cell > 0:
            cell_eq = (w + 0.5 * t) / total_cell
            
            if cell_eq > 0.505: results[hand_str] = 1       # Green
            elif cell_eq < 0.495: results[hand_str] = -1    # Red
            else: results[hand_str] = 0                     # Orange (Tie)
            
            total_w += w; total_l += l; total_t += t
            
    total_combos = total_w + total_l + total_t
    overall_eq = ((total_w + 0.5 * total_t) / total_combos * 100) if total_combos > 0 else 0.0
    return results, round(overall_eq, 1)

def get_action_key(pos, opponent_pos, base_action):
    if base_action == "Open Pot": return "Open"
    if pos in ["SB", "BB"]:
        if opponent_pos in ["UTG", "MP"]: return "3-Bet vs Early"
        else: return "3-Bet vs Late"
    return "3-Bet"

# --- VISUALIZATION BUILDER ---
plt.style.use('dark_background') 

def draw_range_preview(range_str):
    expanded = expand_range(range_str)
    grid = build_grid()
    R13 = list("AKQJT98765432")
    df = pd.DataFrame(-1, index=R13, columns=R13) 
    for r1 in R13:
        for r2 in R13:
            if grid.loc[r1, r2] in expanded: df.loc[r1, r2] = 1 
            
    fig, ax = plt.subplots(figsize=(5, 4))
    fig.patch.set_facecolor('#0E1117') 
    ax.set_facecolor('#0E1117')
    
    custom_cmap = ListedColormap(["#4D4D4D", "#FFD700"]) 
    sns.heatmap(df, cmap=custom_cmap, vmin=-1, vmax=1, annot=grid.values, fmt="", 
                cbar=False, ax=ax, linewidths=.5, linecolor="black", 
                xticklabels=False, yticklabels=False, annot_kws={"color": "black", "size": 9, "weight": "bold"})
    plt.tight_layout()
    return fig

def run_simulation(hero_hand_str, hero_pos, vill_pos, vill_action_key, custom_board_str, use_custom_ranges):
    evaluator = Evaluator()
    active_ranges = st.session_state.custom_ranges if use_custom_ranges else DEFAULT_RANGES
    vill_range = expand_range(active_ranges[vill_pos][vill_action_key])
    
    if not vill_range:
        st.error(f"Villain's {vill_action_key} range from {vill_pos} is empty.")
        return

    try: hero_cards = [Card.new(hero_hand_str[:2]), Card.new(hero_hand_str[2:])]
    except:
        st.error("Invalid Hero Hand format. Use 'AhKh'")
        return

    full_deck = Deck().cards
    
    if custom_board_str:
        try:
            b_list = custom_board_str.strip().split(" ")
            board_cards = [Card.new(c) for c in b_list]
            deck = Deck()
            deck.cards = [c for c in full_deck if c not in hero_cards + board_cards]
            while len(board_cards) < 5: 
                board_cards.append(deck.draw(1)[0] if type(deck.draw(1)) is list else deck.draw(1))
        except:
            st.error("Invalid Board format. Please use format: 'As Ks Qs'")
            return
    else:
        deck = Deck()
        deck.cards = [c for c in full_deck if c not in hero_cards]
        board_cards = deck.draw(5)
        
    flop, turn, river = board_cards[:3], board_cards[:4], board_cards[:5]
    f_res, flop_eq = evaluate_street_equity(hero_cards, vill_range, flop, evaluator, full_deck)
    t_res, turn_eq = evaluate_street_equity(hero_cards, vill_range, turn, evaluator, full_deck)
    r_res, river_eq = evaluate_street_equity(hero_cards, vill_range, river, evaluator, full_deck)

    grid = build_grid()
    R13 = list("AKQJT98765432")
    def mkmap(res_dict):
        df = pd.DataFrame(-2, index=R13, columns=R13) 
        for r1 in R13:
            for r2 in R13:
                hand_name = grid.loc[r1, r2]
                if hand_name in res_dict: df.loc[r1, r2] = res_dict[hand_name]
        return df

    fM, tM, rM = mkmap(f_res), mkmap(t_res), mkmap(r_res)
    hero_emoji = f"{card_to_emoji(hero_hand_str[:2])}{card_to_emoji(hero_hand_str[2:])}"
    
    st.markdown(f"### You get dealt {hero_emoji}, you're in the {pos_full_names[hero_pos]}. Your opponent is in the {pos_full_names[vill_pos]}.")
    
    fig, ax = plt.subplots(1, 3, figsize=(20, 6))
    fig.patch.set_facecolor('#0E1117') 
    
    discrete_cmap = ListedColormap(["#4D4D4D", "#ff4d4d", "#ffb84d", "#47d147"])
    
    sets = [
        (fM, flop, flop_eq, "FLOP EQUITY"), 
        (tM, turn, turn_eq, "TURN EQUITY"), 
        (rM, river, river_eq, "RIVER EQUITY")
    ]
    
    for a, (m, cards, pctv, street_name) in zip(ax, sets):
        a.set_facecolor('#4D4D4D') 
        txt = [card_to_emoji(Card.int_to_str(c)) for c in cards]
        
        sns.heatmap(m, cmap=discrete_cmap, vmin=-2, vmax=1, annot=grid.values, fmt="", 
                    cbar=False, ax=a, linewidths=.5, linecolor="black", 
                    xticklabels=False, yticklabels=False, annot_kws={"color": "black", "weight": "bold"})
        a.set_title(f"{' '.join(txt)}\n{street_name}: {pctv}%", fontsize=16, fontweight='normal', color='white', pad=15)
        
    plt.tight_layout()
    st.pyplot(fig)
    
    st.markdown("""
        <div style='text-align: center; background-color: #1E1E1E; padding: 10px; border-radius: 5px; margin-top: 10px;'>
            <span style='color: #47d147;'>🟩 <b>Advantage (>50%)</b></span> &nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp; 
            <span style='color: #ffb84d;'>🟧 <b>Tie / Coinflip (50%)</b></span> &nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp; 
            <span style='color: #ff4d4d;'>🟥 <b>Disadvantage (<50%)</b></span> &nbsp;&nbsp;&nbsp;&nbsp;|&nbsp;&nbsp;&nbsp;&nbsp; 
            <span style='color: #A9A9A9;'>🔲 <b>Out of Range</b></span>
        </div>
    """, unsafe_allow_html=True)
    plt.close(fig) 

# ===============================================================
# MULTI-PAGE TABS UI
# ===============================================================
tab_practice, tab_custom, tab_ranges = st.tabs(["🎲 Practice Scenarios", "⚙️ Custom Scenarios", "🛠️ Range Builder"])

with tab_practice:
    st.subheader("Random Scenario Generator")
    col1, col2 = st.columns(2)
    with col1: p_action = st.radio("Scenario Type:", ["Open Pot", "3-Bet Pot"])
    with col2: p_ranges = st.radio("Range Source:", ["Use Default Ranges", "Use My Custom Ranges"])
    
    if st.button("Generate Scenario"):
        use_custom = (p_ranges == "Use My Custom Ranges")
        active_ranges = st.session_state.custom_ranges if use_custom else DEFAULT_RANGES
        pos_list = list(active_ranges.keys())
        h_pos = random.choice(pos_list)
        v_pos = random.choice([p for p in pos_list if p != h_pos])
        
        hero_action_key = get_action_key(h_pos, v_pos, p_action)
        vill_action_key = get_action_key(v_pos, h_pos, p_action)
        h_range_expanded = expand_range(active_ranges[h_pos][hero_action_key])
        
        if not h_range_expanded: st.error("Range is empty. Cannot generate hand.")
        else:
            hero_exact_cards, exact_str = exact_cards(random.choice(h_range_expanded))
            if exact_str:
                with st.spinner('Calculating Monte Carlo Equity...'):
                    run_simulation(exact_str, h_pos, v_pos, vill_action_key, "", use_custom)

with tab_custom:
    st.subheader("Custom Scenario Builder")
    c_ranges = st.radio("Range Source:", ["Use Default Ranges", "Use My Custom Ranges"], key="cust_radio")
    use_custom_c = (c_ranges == "Use My Custom Ranges")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: c_hero_pos = st.selectbox("Hero Position", list(DEFAULT_RANGES.keys()))
    with c2: c_hero_hand = st.text_input("Hero Exact Hand", "AhKh")
    with c3: c_vill_pos = st.selectbox("Villain Position", list(DEFAULT_RANGES.keys()), index=3)
    with c4: 
        if c_vill_pos in ["SB", "BB"]: c_action = st.selectbox("Villain Action", ["Open", "3-Bet vs Early", "3-Bet vs Late"])
        else: c_action = st.selectbox("Villain Action", ["Open", "3-Bet"])
            
    c_board = st.text_input("Board Cards (Leave blank for random)", "")
    st.markdown("<span style='color: white;'>*Please put spaces in between the cards (e.g., As Ks Qs)*</span>", unsafe_allow_html=True)
    
    if st.button("Calculate Equity"):
        with st.spinner('Calculating Math Engines...'):
            run_simulation(c_hero_hand, c_hero_pos, c_vill_pos, c_action, c_board, use_custom_c)

with tab_ranges:
    st.subheader("Range Builder")
    st.caption("*(Type your ranges and click anywhere outside the box to update the visual instantly)*")
    
    rb_col1, rb_col2 = st.columns([1, 1.5])
    with rb_col1:
        rb_pos = st.selectbox("Position", list(DEFAULT_RANGES.keys()))
        if rb_pos in ["SB", "BB"]: rb_act = st.selectbox("Action", ["Open", "3-Bet vs Early", "3-Bet vs Late"])
        else: rb_act = st.selectbox("Action", ["Open", "3-Bet"])
        
        current_range_str = st.session_state.custom_ranges[rb_pos][rb_act]
        new_range_str = st.text_area("Range Notation:", current_range_str, height=150)
        st.session_state.custom_ranges[rb_pos][rb_act] = new_range_str
        
        if st.button("Reset All to Default"):
            st.session_state.custom_ranges = DEFAULT_RANGES.copy()
            st.rerun() 
            
    with rb_col2:
        preview_fig = draw_range_preview(st.session_state.custom_ranges[rb_pos][rb_act])
        st.pyplot(preview_fig)
        plt.close(preview_fig)
