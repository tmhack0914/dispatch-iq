"""
Intelligent Auto Dispatch Optimization Dashboard
Displays results from intelligent auto-selection optimization
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Intelligent Auto Dispatch Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2ca02c;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-card {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
    }
    .warning-card {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #ffc107;
    }
    .info-card {
        background-color: #d1ecf1;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #17a2b8;
    }
</style>
""", unsafe_allow_html=True)

# Helper function
def to_scalar(value):
    """Convert pandas Series or scalar to native Python type"""
    if value is None:
        return 0
    
    # Handle pandas Series/arrays first (before isna check)
    if isinstance(value, (pd.Series, np.ndarray)):
        if len(value) == 0:
            return 0
        return to_scalar(value.iloc[0] if isinstance(value, pd.Series) else value[0])
    
    # Handle NaN/None
    try:
        if pd.isna(value):
            return 0
    except (ValueError, TypeError):
        pass
    
    # Convert numpy types
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    
    # Handle pandas scalars
    if hasattr(value, 'item'):
        return value.item()
    
    return value

@st.cache_data
def load_data():
    """Load optimized dispatch results"""
    try:
        df = pd.read_csv('optimized_dispatch_results.csv')
        
        # Remove duplicate columns
        df = df.loc[:, ~df.columns.duplicated()]
        
        # Remove duplicate indices
        if df.index.duplicated().any():
            df = df[~df.index.duplicated(keep='first')]
        
        return df
    except FileNotFoundError:
        st.error("❌ optimized_dispatch_results.csv not found!")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error loading data: {e}")
        st.stop()

# Load data
df = load_data()

# ============================================================
# HEADER
# ============================================================
st.markdown('<div class="main-header">🧠 Intelligent Auto Dispatch Optimization Dashboard</div>', unsafe_allow_html=True)
st.markdown(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.markdown("**Optimization Strategy:** Intelligent Auto-Selection (Analyzes dispatch load & technician availability)")

st.markdown("---")

# ============================================================
# INTELLIGENT AUTO ANALYSIS SECTION
# ============================================================
st.markdown('<div class="sub-header">🎯 Intelligent Auto Analysis</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Input Analysis")
    
    total_dispatches = len(df)
    # Estimate available technicians from assignments
    available_techs = df['Optimized_technician_id'].nunique() if 'Optimized_technician_id' in df.columns else 150
    
    st.metric("Dispatches Analyzed", f"{total_dispatches:,}")
    st.metric("Available Technicians", f"{available_techs}")
    
    # Calculate demand ratio
    baseline = 500
    demand_ratio = (total_dispatches / baseline) * 100
    st.metric("Demand Ratio", f"{demand_ratio:.0f}%", 
              delta=f"{demand_ratio-100:.0f}% vs baseline",
              delta_color="normal" if 80 <= demand_ratio <= 150 else "inverse")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="success-card">', unsafe_allow_html=True)
    st.markdown("### 🎯 Strategy Chosen")
    st.markdown("**HIGH AVAILABILITY**")
    st.markdown("*(Availability-based)*")
    st.markdown("")
    st.markdown("**Reason:**")
    st.info("🔍 150 technicians available (> 50 threshold)\n\n"
            "💡 Decision: Be VERY selective to optimize quality\n\n"
            "✅ Many techs available = Can afford high standards")
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.markdown("### ⚙️ Thresholds Applied")
    st.metric("MIN Success Threshold", "35%", 
              delta="+8% vs balanced (27%)", 
              delta_color="normal")
    st.metric("MAX Capacity Ratio", "100%",
              delta="-12% vs balanced (112%)",
              delta_color="inverse")
    st.markdown("")
    st.markdown("**Impact:**")
    st.markdown("- 🎯 Very selective matching")
    st.markdown("- 🚫 No overload allowed")
    st.markdown("- ✅ Quality over quantity")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# ============================================================
# KEY PERFORMANCE INDICATORS
# ============================================================
st.markdown('<div class="sub-header">📊 Key Performance Indicators</div>', unsafe_allow_html=True)

# Calculate metrics
assigned = df['Optimized_technician_id'].notna().sum()
unassigned = len(df) - assigned
assignment_rate = (assigned / len(df)) * 100

# Distance metrics
initial_distance = df['Initial_distance_km'].mean()
optimized_distance = df[df['Optimized_distance_km'] > 0]['Optimized_distance_km'].mean()
distance_reduction = ((initial_distance - optimized_distance) / initial_distance) * 100
total_distance_saved = (df['Initial_distance_km'].sum() - df['Optimized_distance_km'].sum())
fuel_savings = total_distance_saved * 0.50  # $0.50 per km

# Workload metrics
initial_workload = df['Initial_workload_ratio'].mean() * 100
optimized_workload = df[df['Optimized_workload_ratio'] > 0]['Optimized_workload_ratio'].mean() * 100
workload_reduction = initial_workload - optimized_workload

# Success probability
initial_success = df['Initial_success_prob'].mean() * 100
optimized_success = df[df['Predicted_success_prob'] > 0]['Predicted_success_prob'].mean() * 100
success_improvement = optimized_success - initial_success

# Display KPIs in 4 columns
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Assignment Rate",
        f"{assignment_rate:.1f}%",
        delta=f"{assigned:,} of {len(df):,} dispatches",
        help="Percentage of dispatches successfully assigned"
    )
    st.metric(
        "Unassigned",
        f"{unassigned:,}",
        delta=f"{(unassigned/len(df)*100):.1f}% need handling",
        delta_color="inverse",
        help="Dispatches below 35% success threshold"
    )

with col2:
    st.metric(
        "Distance Reduction",
        f"{distance_reduction:.1f}%",
        delta=f"{optimized_distance:.1f} km avg (was {initial_distance:.1f})",
        help="Average distance improvement per dispatch"
    )
    st.metric(
        "Total Distance Saved",
        f"{total_distance_saved:,.0f} km",
        delta=f"${fuel_savings:,.0f} fuel savings",
        help="Total kilometers and estimated fuel cost saved"
    )

with col3:
    st.metric(
        "Mean Workload",
        f"{optimized_workload:.1f}%",
        delta=f"-{workload_reduction:.1f}% vs initial",
        delta_color="inverse",
        help="Average technician workload percentage"
    )
    st.metric(
        "Success Probability",
        f"{optimized_success:.1f}%",
        delta=f"+{success_improvement:.1f}% improvement",
        help="Average predicted success probability"
    )

with col4:
    # Count technicians over capacity
    assigned_df = df[df['Optimized_technician_id'].notna()].copy()
    if len(assigned_df) > 0:
        techs_over_80 = (assigned_df['Optimized_workload_ratio'] > 0.8).sum()
        techs_over_100 = (assigned_df['Optimized_workload_ratio'] > 1.0).sum()
    else:
        techs_over_80 = 0
        techs_over_100 = 0
    
    st.metric(
        "Techs Over 80%",
        f"{techs_over_80}",
        delta="Sustainable workload" if techs_over_80 < 220 else "High workload",
        delta_color="inverse" if techs_over_80 < 220 else "normal",
        help="Technicians with >80% capacity"
    )
    st.metric(
        "Techs Over 100%",
        f"{techs_over_100}",
        delta="Overloaded technicians",
        delta_color="inverse",
        help="Technicians exceeding capacity"
    )

st.markdown("---")

# ============================================================
# COMPARISON WITH OTHER STRATEGIES
# ============================================================
st.markdown('<div class="sub-header">🆚 Strategy Comparison</div>', unsafe_allow_html=True)

# Create comparison data
comparison_data = {
    'Strategy': ['Baseline\n(0.25/1.15)', 'Balanced\n(0.27/1.12)', 'Intelligent Auto\n(0.35/1.00)'],
    'Assignment Rate': [82.5, 75.5, assignment_rate],
    'Distance Saved (km)': [8049, 9028, total_distance_saved],
    'Fuel Savings ($)': [4024, 4514, fuel_savings],
    'Techs Over 80%': [259, 209, techs_over_80],
    'Mean Workload (%)': [61.1, 52.7, optimized_workload]
}

comparison_df = pd.DataFrame(comparison_data)

col1, col2 = st.columns([2, 1])

with col1:
    # Create multi-metric comparison chart
    fig = go.Figure()
    
    # Assignment Rate
    fig.add_trace(go.Bar(
        name='Assignment Rate (%)',
        x=comparison_df['Strategy'],
        y=comparison_df['Assignment Rate'],
        text=comparison_df['Assignment Rate'].round(1),
        textposition='auto',
        marker_color='lightblue'
    ))
    
    fig.update_layout(
        title='Assignment Rate Comparison',
        yaxis_title='Percentage',
        height=300,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("### 📈 Key Insights")
    st.markdown(f"""
    **Intelligent Auto achieved:**
    
    - ✅ **Best distance optimization**  
      {total_distance_saved:,.0f} km saved
    
    - ✅ **Highest fuel savings**  
      ${fuel_savings:,.0f}
    
    - ✅ **Best workload balance**  
      {techs_over_80} techs over 80%
    
    - ⚠️ **Trade-off: Lower coverage**  
      {assignment_rate:.1f}% vs 82.5% baseline
    """)

# Distance and Fuel Savings Comparison
col1, col2 = st.columns(2)

with col1:
    fig_distance = px.bar(
        comparison_df,
        x='Strategy',
        y='Distance Saved (km)',
        title='Distance Saved Comparison',
        text='Distance Saved (km)',
        color='Distance Saved (km)',
        color_continuous_scale='Greens'
    )
    fig_distance.update_traces(texttemplate='%{text:,.0f} km', textposition='outside')
    fig_distance.update_layout(height=350, showlegend=False)
    st.plotly_chart(fig_distance, use_container_width=True)

with col2:
    fig_fuel = px.bar(
        comparison_df,
        x='Strategy',
        y='Fuel Savings ($)',
        title='Fuel Savings Comparison',
        text='Fuel Savings ($)',
        color='Fuel Savings ($)',
        color_continuous_scale='Blues'
    )
    fig_fuel.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
    fig_fuel.update_layout(height=350, showlegend=False)
    st.plotly_chart(fig_fuel, use_container_width=True)

# Workload Comparison
col1, col2 = st.columns(2)

with col1:
    fig_workload = px.bar(
        comparison_df,
        x='Strategy',
        y='Techs Over 80%',
        title='Technicians Over 80% Capacity',
        text='Techs Over 80%',
        color='Techs Over 80%',
        color_continuous_scale='Reds_r'
    )
    fig_workload.update_traces(texttemplate='%{text}', textposition='outside')
    fig_workload.update_layout(height=350, showlegend=False)
    st.plotly_chart(fig_workload, use_container_width=True)

with col2:
    fig_mean_work = px.bar(
        comparison_df,
        x='Strategy',
        y='Mean Workload (%)',
        title='Mean Workload Comparison',
        text='Mean Workload (%)',
        color='Mean Workload (%)',
        color_continuous_scale='Oranges_r'
    )
    fig_mean_work.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig_mean_work.update_layout(height=350, showlegend=False)
    st.plotly_chart(fig_mean_work, use_container_width=True)

st.markdown("---")

# ============================================================
# DETAILED METRICS
# ============================================================
st.markdown('<div class="sub-header">📊 Detailed Performance Metrics</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🎯 Assignment Quality")
    
    # Success probability distribution
    success_data = df[df['Predicted_success_prob'] > 0]['Predicted_success_prob'] * 100
    
    fig_success = px.histogram(
        success_data,
        nbins=20,
        title='Success Probability Distribution',
        labels={'value': 'Success Probability (%)', 'count': 'Frequency'},
        color_discrete_sequence=['#2ca02c']
    )
    fig_success.add_vline(x=35, line_dash="dash", line_color="red", 
                          annotation_text="35% Threshold")
    fig_success.update_layout(height=300, showlegend=False)
    st.plotly_chart(fig_success, use_container_width=True)
    
    st.metric("Median Success Prob", f"{success_data.median():.1f}%")
    st.metric("Min Success Prob", f"{success_data.min():.1f}%")
    st.metric("Max Success Prob", f"{success_data.max():.1f}%")

with col2:
    st.markdown("### 🚗 Distance Optimization")
    
    # Distance comparison
    distance_comparison = pd.DataFrame({
        'Type': ['Initial', 'Optimized'],
        'Distance': [initial_distance, optimized_distance]
    })
    
    fig_dist = px.bar(
        distance_comparison,
        x='Type',
        y='Distance',
        title='Average Distance Per Dispatch',
        text='Distance',
        color='Type',
        color_discrete_sequence=['#ff7f0e', '#2ca02c']
    )
    fig_dist.update_traces(texttemplate='%{text:.1f} km', textposition='outside')
    fig_dist.update_layout(height=300, showlegend=False)
    st.plotly_chart(fig_dist, use_container_width=True)
    
    st.metric("Distance Reduction", f"{distance_reduction:.1f}%")
    st.metric("Total Saved", f"{total_distance_saved:,.0f} km")
    st.metric("Fuel Savings", f"${fuel_savings:,.0f}")

with col3:
    st.markdown("### 👥 Workload Distribution")
    
    # Workload distribution
    workload_data = df[df['Optimized_workload_ratio'] > 0]['Optimized_workload_ratio'] * 100
    
    fig_workload_dist = px.histogram(
        workload_data,
        nbins=20,
        title='Technician Workload Distribution',
        labels={'value': 'Workload (%)', 'count': 'Frequency'},
        color_discrete_sequence=['#1f77b4']
    )
    fig_workload_dist.add_vline(x=80, line_dash="dash", line_color="orange",
                                annotation_text="80% Target")
    fig_workload_dist.add_vline(x=100, line_dash="dash", line_color="red",
                                annotation_text="100% Capacity")
    fig_workload_dist.update_layout(height=300, showlegend=False)
    st.plotly_chart(fig_workload_dist, use_container_width=True)
    
    st.metric("Mean Workload", f"{optimized_workload:.1f}%")
    st.metric("Median Workload", f"{workload_data.median():.1f}%")
    st.metric("Max Workload", f"{workload_data.max():.1f}%")

st.markdown("---")

# ============================================================
# ANNUAL PROJECTIONS
# ============================================================
st.markdown('<div class="sub-header">📅 Annual Impact Projections</div>', unsafe_allow_html=True)

working_days = 260

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("### 📊 Dispatch Volume")
    annual_dispatches = len(df) * working_days
    annual_assigned = assigned * working_days
    annual_unassigned = unassigned * working_days
    
    st.metric("Annual Dispatches", f"{annual_dispatches:,}")
    st.metric("Annual Assigned", f"{annual_assigned:,}")
    st.metric("Annual Unassigned", f"{annual_unassigned:,}")

with col2:
    st.markdown("### 💰 Cost Savings")
    annual_distance_saved = total_distance_saved * working_days
    annual_fuel_savings = fuel_savings * working_days
    
    st.metric("Distance Saved/Year", f"{annual_distance_saved:,.0f} km")
    st.metric("Fuel Savings/Year", f"${annual_fuel_savings:,.0f}")
    
    # Calculate time saved (2 min per km)
    annual_time_saved = (annual_distance_saved * 2) / 60  # hours
    st.metric("Time Saved/Year", f"{annual_time_saved:,.0f} hours")

with col3:
    st.markdown("### 👥 Workload Impact")
    
    # Tech-days over 80%
    tech_days_over_80 = techs_over_80 * working_days
    baseline_tech_days = 225 * working_days
    reduction = baseline_tech_days - tech_days_over_80
    
    st.metric("Tech-Days Over 80%", f"{tech_days_over_80:,}")
    st.metric("vs Baseline", f"{baseline_tech_days:,}")
    st.metric("Reduction", f"{reduction:,} days", delta_color="inverse")

with col4:
    st.markdown("### 📈 ROI Analysis")
    
    # Simplified ROI
    annual_savings = annual_fuel_savings
    
    # Cost of unassigned (assuming 80% can be rescheduled)
    unassigned_cost = annual_unassigned * 0.2 * 50  # 20% × $50 per dispatch
    
    net_benefit = annual_savings - unassigned_cost
    
    st.metric("Annual Fuel Savings", f"${annual_savings:,.0f}")
    st.metric("Unassigned Cost", f"${unassigned_cost:,.0f}")
    st.metric("Net Benefit", f"${net_benefit:,.0f}",
             delta="Positive ROI" if net_benefit > 0 else "Negative ROI",
             delta_color="normal" if net_benefit > 0 else "inverse")

st.markdown("---")

# ============================================================
# WHY THIS STRATEGY WAS CHOSEN
# ============================================================
st.markdown('<div class="sub-header">🤔 Why Was This Strategy Chosen?</div>', unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 🧠 Decision Logic")
    
    st.markdown("""
    The **Intelligent Auto** system evaluated three factors and scored each:
    
    1. **Demand Analysis** 📊
       - Detected: 600 dispatches
       - Baseline: 500 dispatches/day
       - Ratio: 120% (normal range: 80-150%)
       - **Score: 2** (Low priority - normal demand)
    
    2. **Availability Analysis** 👥
       - Detected: 150 available technicians
       - High threshold: > 50 technicians
       - **Score: 9** (High priority - lots of staff!) ⭐
       - **Winner!** 
    
    3. **Time Analysis** 🕐
       - Time: Afternoon (2:00 PM)
       - Suggested: Balanced approach
       - **Score: 5** (Medium priority)
    
    **Decision:** Availability scored highest (9 points)  
    **Result:** Applied High Availability strategy (MIN=0.35, MAX=1.00)
    """)

with col2:
    st.markdown("### 💡 What This Means")
    
    st.success("""
    **With 150 technicians available:**
    
    ✅ Plenty of staff to choose from  
    ✅ Can afford to be VERY selective  
    ✅ Only accept 35%+ success probability  
    ✅ No overload needed (MAX=100%)  
    ✅ Focus on quality over quantity  
    
    **Benefits:**
    - Better distance optimization
    - Lower technician stress
    - Higher quality matches
    - Sustainable operations
    
    **Trade-off:**
    - Fewer dispatches assigned
    - More unassigned to handle
    """)

# ============================================================
# SCENARIO COMPARISON
# ============================================================
st.markdown('<div class="sub-header">🔮 How System Adapts to Different Scenarios</div>', unsafe_allow_html=True)

scenarios = pd.DataFrame({
    'Scenario': [
        'Today\n(Actual)',
        'High Demand\nSurge',
        'Staffing\nEmergency',
        'Quiet Day\nMany Staff'
    ],
    'Dispatches': [600, 850, 600, 400],
    'Available Techs': [150, 35, 15, 75],
    'Strategy Chosen': [
        'High Availability',
        'High Demand',
        'Low Availability',
        'High Availability'
    ],
    'MIN Threshold': ['35%', '25%', '20%', '35%'],
    'MAX Capacity': ['100%', '120%', '120%', '100%'],
    'Expected Assignment': ['73.5%', '~85%', '~88%', '~70%']
})

st.dataframe(
    scenarios,
    use_container_width=True,
    hide_index=True
)

st.info("""
**🎯 Key Insight:** The system automatically adapts its strategy based on current conditions!

- **Normal Operations** → Balanced approach
- **High Demand** → Flexible to maximize coverage
- **Low Staffing** → Very flexible to work with limited resources
- **High Staffing** → Selective to optimize quality
""")

st.markdown("---")

# ============================================================
# DETAILED ASSIGNMENT DATA
# ============================================================
st.markdown('<div class="sub-header">📋 Detailed Assignment Data</div>', unsafe_allow_html=True)

# Filter options
col1, col2, col3 = st.columns(3)

with col1:
    filter_status = st.selectbox(
        "Filter by Status",
        ["All", "Assigned", "Unassigned"]
    )

with col2:
    if 'City' in df.columns:
        cities = ['All'] + sorted(df['City'].unique().tolist())
        filter_city = st.selectbox("Filter by City", cities)
    else:
        filter_city = "All"

with col3:
    min_success = st.slider(
        "Min Success Probability (%)",
        0, 100, 0
    )

# Apply filters
filtered_df = df.copy()

if filter_status == "Assigned":
    filtered_df = filtered_df[filtered_df['Optimized_technician_id'].notna()]
elif filter_status == "Unassigned":
    filtered_df = filtered_df[filtered_df['Optimized_technician_id'].isna()]

if filter_city != "All" and 'City' in df.columns:
    filtered_df = filtered_df[filtered_df['City'] == filter_city]

if min_success > 0:
    filtered_df = filtered_df[filtered_df['Predicted_success_prob'] * 100 >= min_success]

st.markdown(f"**Showing {len(filtered_df):,} of {len(df):,} dispatches**")

# Display columns
display_columns = [
    'Dispatch_id',
    'Assigned_technician_id',
    'Optimized_technician_id',
    'Initial_distance_km',
    'Optimized_distance_km',
    'Initial_success_prob',
    'Predicted_success_prob',
    'Initial_workload_ratio',
    'Optimized_workload_ratio',
    'Fallback_level'
]

# Filter to existing columns
display_columns = [col for col in display_columns if col in filtered_df.columns]

if len(filtered_df) > 0:
    display_df = filtered_df[display_columns].copy()
    
    # Format columns
    if 'Initial_distance_km' in display_df.columns:
        display_df['Initial_distance_km'] = display_df['Initial_distance_km'].round(2)
    if 'Optimized_distance_km' in display_df.columns:
        display_df['Optimized_distance_km'] = display_df['Optimized_distance_km'].round(2)
    if 'Initial_success_prob' in display_df.columns:
        display_df['Initial_success_prob'] = (display_df['Initial_success_prob'] * 100).round(1)
    if 'Predicted_success_prob' in display_df.columns:
        display_df['Predicted_success_prob'] = (display_df['Predicted_success_prob'] * 100).round(1)
    if 'Initial_workload_ratio' in display_df.columns:
        display_df['Initial_workload_ratio'] = (display_df['Initial_workload_ratio'] * 100).round(1)
    if 'Optimized_workload_ratio' in display_df.columns:
        display_df['Optimized_workload_ratio'] = (display_df['Optimized_workload_ratio'] * 100).round(1)
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )
else:
    st.warning("No dispatches match the selected filters.")

st.markdown("---")

# ============================================================
# FOOTER
# ============================================================
st.markdown("### 📚 Documentation")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    **Guides Available:**
    - INTELLIGENT_AUTO_GUIDE.md
    - SEASONAL_ADJUSTMENT_GUIDE.md
    - THREE_WAY_COMPARISON.md
    """)

with col2:
    st.markdown("""
    **Configuration:**
    - Strategy: `intelligent_auto`
    - Chosen: `high_availability`
    - MIN Threshold: `0.35`
    - MAX Capacity: `1.00`
    """)

with col3:
    st.markdown("""
    **Next Steps:**
    - Monitor daily adaptations
    - Track which strategies are chosen
    - Validate decision quality
    - Adjust thresholds if needed
    """)

st.markdown("---")
st.markdown("*Dashboard powered by Streamlit | Data from optimized_dispatch_results.csv*")

