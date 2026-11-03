import streamlit as st
import pandas as pd
import numpy as np
import io

# Set page layout to wide for better comparison view
st.set_page_config(layout="wide", page_title="Era Stat Matchup")

st.title("🏀 Era Stat Matchup & Box Score Aggregator")
st.markdown("Paste raw player season/game rows (like from *Basketball-Reference*) into the respective buckets to compare weighted averages.")

# Key tracking metrics modeled after BBRef summary boxes
CORE_METRICS = ['G', 'MP', 'FG%', '3P%', 'FT%', 'TRB', 'AST', 'STL', 'BLK', 'PTS']

def parse_pasted_stats(raw_text):
    """
    Intelligently cleans and parses varied whitespace-separated or tab-separated 
    text rows copied straight out of browser tables into a clean Pandas DataFrame.
    """
    if not raw_text.strip():
        return None
    try:
        # Standardize common BBRef shorthand column names to keep code robust
        rename_dict = {
            'g': 'G', 'gs': 'GS', 'mp': 'MP', 'pts': 'PTS', 'trb': 'TRB', 
            'ast': 'AST', 'stl': 'STL', 'blk': 'BLK', 'fg_pct': 'FG%', 
            'fg%': 'FG%', 'fg3_pct': '3P%', '3p%': '3P%', 'ft_pct': 'FT%', 'ft%': 'FT%'
        }
        
        # Read the text string as a dataframe using flexible whitespace delimiter
        df = pd.read_csv(io.StringIO(raw_text.strip()), sep=r'\s+|\t', engine='python')
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns=rename_dict)
        
        # Ensure essential columns exist, fill missing with 0s if necessary
        for metric in CORE_METRICS:
            if metric not in df.columns:
                df[metric] = 0.0 if '%' in metric else 0
                
        # Force numeric types and strip non-numeric noise
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
        return df
    except Exception as e:
        st.error(f"Error parsing text input. Make sure it's tabular row data. Detals: {e}")
        return None

def calculate_weighted_box_score(df):
    """
    Calculates weighted per-game metrics and percentage averages based on 
    total games played to exactly replicate a Basketball-Reference career box.
    """
    if df is None or df.empty:
        return None
    
    total_games = df['G'].sum()
    if total_games == 0:
        return None
        
    summary = {}
    summary['G'] = int(total_games)
    
    # Calculate weighted averages or direct per-game means based on volume
    summary['MP'] = round(df['MP'].mean(), 1) if 'MP' in df.columns else 0.0
    summary['PTS'] = round((df['PTS'] * df['G']).sum() / total_games, 1)
    summary['TRB'] = round((df['TRB'] * df['G']).sum() / total_games, 1)
    summary['AST'] = round((df['AST'] * df['G']).sum() / total_games, 1)
    summary['STL'] = round((df['STL'] * df['G']).sum() / total_games, 1)
    summary['BLK'] = round((df['BLK'] * df['G']).sum() / total_games, 1)
    
    # Percentage splits are weighted against games to prevent low-volume season distortion
    summary['FG%'] = round((df['FG%'] * df['G']).sum() / total_games, 3)
    summary['3P%'] = round((df['3P%'] * df['G']).sum() / total_games, 3)
    summary['FT%'] = round((df['FT%'] * df['G']).sum() / total_games, 3)
    
    return pd.Series(summary).reindex(CORE_METRICS)

# --- USER INTERFACE LAYOUT ---

col1, col2 = st.columns(2)

with col1:
    st.header("⏳ Bucket 1: 80s-90s Legends")
    classic_name = st.text_input("Player/Group Name (Bucket 1)", "90s Legends", key="c_name")
    classic_raw = st.text_area(
        "Paste row data here (Include header row if copying multiple rows):",
        value="G   MP   FG%   3P%   FT%   TRB  AST  STL  BLK  PTS\n82  40.4  .535  .132  .841  8.0  5.8  2.2  0.8  35.0\n78  38.3  .519  .312  .850  6.5  5.5  2.7  0.7  31.5",
        height=180,
        key="classic_paste"
    )

with col2:
    st.header("⚡ Bucket 2: Modern Era Legends")
    modern_name = st.text_input("Player/Group Name (Bucket 2)", "Modern Icons", key="m_name")
    modern_raw = st.text_area(
        "Paste row data here:",
        value="G   MP   FG%   3P%   FT%   TRB  AST  STL  BLK  PTS\n75  37.4  .493  .404  .885  8.0  8.0  1.2  0.6  30.1\n68  35.2  .504  .383  .910  5.2  5.6  1.3  0.4  28.2",
        height=180,
        key="modern_paste"
    )

# Process raw pasted inputs into tables
df_classic = parse_pasted_stats(classic_raw)
df_modern = parse_pasted_stats(modern_raw)

box_classic = calculate_weighted_box_score(df_classic)
box_modern = calculate_weighted_box_score(df_modern)

# --- COMPARISON VIEW & HIGHLIGHTING ---
st.write("---")
st.subheader("📊 Head-to-Head Box Score Comparison")

if box_classic is not None and box_modern is not None:
    # Build final comparative frame
    comparison_df = pd.DataFrame({
        f"{classic_name}": box_classic,
        f"{modern_name}": box_modern
    })
    
    # Custom display formatting so decimals and percentages look authentic
    format_dict = {
        'G': '{:,.0f}', 'MP': '{:.1f}', 'PTS': '{:.1f}', 'TRB': '{:.1f}', 
        'AST': '{:.1f}', 'STL': '{:.1f}', 'BLK': '{:.1f}', 
        'FG%': '{:.3f}', '3P%': '{:.3f}', 'FT%': '{:.3f}'
    }
    
    def highlight_higher_metric(row):
        """Styles the cell background green for whichever value is statistically superior."""
        color_classic = 'background-color: rgba(46, 204, 113, 0.3)' # Soft green
        color_modern = 'background-color: rgba(46, 204, 113, 0.3)'
        
        # Don't color-code absolute sample sizing fields like total Games Played
        if row.name == 'G':
            return ['', '']
            
        if row[0] > row[1]:
            return [color_classic, '']
        elif row[1] > row[0]:
            return ['', color_modern]
        return ['', '']

    # Apply style maps and render the interactive table
    styled_comp = comparison_df.style.apply(highlight_higher_metric, axis=1)
    
    # Display the final box score component
    st.table(styled_comp)
    st.caption("💡 Green cells indicate which era or player achieved the higher statistical mark.")
else:
    st.info("Paste valid box score rows into both inputs above to generate your comparison matrix.")
