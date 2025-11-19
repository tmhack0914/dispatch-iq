"""
Smart Dispatch Optimization Dashboard
Interactive web application to visualize dispatch optimization results
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import os

# Page configuration
st.set_page_config(
    page_title="Smart Dispatch Optimization",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    h1 {
        color: #1f77b4;
    }
    h2 {
        color: #2c3e50;
    }
    </style>
    """, unsafe_allow_html=True)

# Title and header
st.title("🚚 Smart Dispatch Optimization Dashboard")
st.markdown("### ML-Based Technician Assignment System")

# View selector
view_mode = st.radio(
    "Select View:",
    ["📊 Dashboard (Analytics)", "📋 Assignments (Manager)", "👷 Technician View"],
    horizontal=True,
    key="view_selector"
)

st.markdown("---")

# Load data
@st.cache_data
def load_data():
    """Load the optimized dispatch results"""
    try:
        # Try to load the results file
        if os.path.exists('optimized_dispatch_results.csv'):
            df = pd.read_csv('optimized_dispatch_results.csv')
            return df, None
        else:
            return None, "⚠️ Results file not found. Please run dispatch_agent.py first."
    except Exception as e:
        return None, f"⚠️ Error loading data: {str(e)}"

df, error = load_data()

if error:
    st.error(error)
    st.info("Run the dispatch agent first: `python dispatch_agent.py`")
    st.stop()

# ============================================================
# VIEW ROUTING
# ============================================================

if view_mode == "📋 Assignments (Manager)":
    # ============================================================
    # ASSIGNMENTS VIEW - FOR DISPATCH MANAGERS
    # ============================================================
    st.header("📋 Assignment Management Dashboard")
    st.markdown("Track and manage all optimized dispatch assignments")
    
    # Filters in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        city_filter = st.selectbox("Filter by City", ['All'] + sorted(df['City'].dropna().unique().tolist()))
    
    with col2:
        status_filter = st.selectbox("Assignment Status", ['All', 'Assigned', 'Unassigned'])
    
    with col3:
        skill_filter = st.selectbox("Required Skill", ['All'] + sorted(df['Required_skill'].dropna().unique().tolist()))
    
    with col4:
        sort_by = st.selectbox("Sort By", ['Success Probability', 'Distance', 'Dispatch ID', 'Appointment Date'])
    
    # Apply filters
    filtered_assignments = df.copy()
    
    if city_filter != 'All':
        filtered_assignments = filtered_assignments[filtered_assignments['City'] == city_filter]
    
    if status_filter == 'Assigned':
        filtered_assignments = filtered_assignments[filtered_assignments['Optimized_technician_id'].notna()]
    elif status_filter == 'Unassigned':
        filtered_assignments = filtered_assignments[filtered_assignments['Optimized_technician_id'].isna()]
    
    if skill_filter != 'All':
        filtered_assignments = filtered_assignments[filtered_assignments['Required_skill'] == skill_filter]
    
    # Sort
    if sort_by == 'Success Probability':
        filtered_assignments = filtered_assignments.sort_values('Predicted_success_prob', ascending=False)
    elif sort_by == 'Distance':
        filtered_assignments = filtered_assignments.sort_values('Optimized_distance_km', ascending=True)
    elif sort_by == 'Dispatch ID':
        filtered_assignments = filtered_assignments.sort_values('Dispatch_id')
    elif sort_by == 'Appointment Date':
        filtered_assignments = filtered_assignments.sort_values('Appointment_date')
    
    # Summary metrics
    st.markdown("### 📊 Quick Summary")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Dispatches", len(filtered_assignments))
    
    with col2:
        assigned = filtered_assignments['Optimized_technician_id'].notna().sum()
        st.metric("Assigned", assigned, f"{(assigned/len(filtered_assignments)*100):.1f}%")
    
    with col3:
        unassigned = filtered_assignments['Optimized_technician_id'].isna().sum()
        st.metric("Unassigned", unassigned, delta_color="inverse" if unassigned > 0 else "off")
    
    with col4:
        avg_success = filtered_assignments['Predicted_success_prob'].mean()
        st.metric("Avg Success Prob", f"{avg_success:.3f}")
    
    with col5:
        avg_distance = filtered_assignments['Optimized_distance_km'].mean()
        st.metric("Avg Distance", f"{avg_distance:.1f} km")
    
    st.markdown("---")
    
    # Assignments table
    st.markdown("### 📋 Assignment Details")
    
    # Prepare display columns
    display_cols = [
        'Dispatch_id', 'Appointment_date', 'City', 'Required_skill',
        'Optimized_technician_id', 'Predicted_success_prob', 
        'Optimized_distance_km', 'Optimized_workload_ratio',
        'Optimization_confidence', 'Fallback_level'
    ]
    
    display_df = filtered_assignments[display_cols].copy()
    display_df.columns = [
        'Dispatch ID', 'Date', 'City', 'Required Skill',
        'Assigned Technician', 'Success Prob', 
        'Distance (km)', 'Tech Workload',
        'Confidence', 'Assignment Level'
    ]
    
    # Color coding function
    def color_assignments(row):
        if pd.isna(row['Assigned Technician']):
            return ['background-color: #fadbd8'] * len(row)  # Red for unassigned
        elif row['Success Prob'] >= 0.7:
            return ['background-color: #d5f4e6'] * len(row)  # Green for high success
        elif row['Success Prob'] >= 0.5:
            return ['background-color: #fff9c4'] * len(row)  # Yellow for medium
        else:
            return ['background-color: #ffe0b2'] * len(row)  # Orange for low
    
    # Display table
    st.dataframe(
        display_df.style.apply(color_assignments, axis=1),
        width='stretch',
        height=500
    )
    
    # Legend
    st.markdown("""
    **Color Legend:**
    - 🟢 Green: High success probability (≥70%)
    - 🟡 Yellow: Medium success probability (50-70%)
    - 🟠 Orange: Low success probability (<50%)
    - 🔴 Red: Unassigned dispatch
    """)
    
    # Download button
    csv = display_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Assignment List (CSV)",
        data=csv,
        file_name=f"assignments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
    
    # Assignment statistics by technician
    st.markdown("---")
    st.markdown("### 👷 Technician Workload Overview")
    
    tech_stats = filtered_assignments[filtered_assignments['Optimized_technician_id'].notna()].groupby('Optimized_technician_id').agg({
        'Dispatch_id': 'count',
        'Predicted_success_prob': 'mean',
        'Optimized_distance_km': 'mean',
        'Optimized_workload_ratio': 'first'
    }).reset_index()
    
    tech_stats.columns = ['Technician ID', 'Assignments', 'Avg Success Prob', 'Avg Distance (km)', 'Workload Ratio']
    tech_stats = tech_stats.sort_values('Assignments', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.dataframe(tech_stats, width='stretch', height=400)
    
    with col2:
        fig_tech = px.bar(
            tech_stats.head(10),
            x='Technician ID',
            y='Assignments',
            title='Top 10 Technicians by Assignment Count',
            color='Avg Success Prob',
            color_continuous_scale='RdYlGn'
        )
        st.plotly_chart(fig_tech, width='stretch')

elif view_mode == "👷 Technician View":
    # ============================================================
    # TECHNICIAN VIEW - INTERACTIVE DAILY ASSIGNMENT MANAGEMENT
    # ============================================================
    st.header("👷 My Daily Assignments Dashboard")
    st.markdown("Manage your daily schedule and track assignment details")
    
    # Technician selector
    assigned_df = df[df['Optimized_technician_id'].notna()].copy()
    technicians_list = sorted(assigned_df['Optimized_technician_id'].unique())
    
    if len(technicians_list) == 0:
        st.warning("No technicians have been assigned yet.")
        st.stop()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_tech = st.selectbox(
            "👤 Select Technician ID:",
            technicians_list,
            key="tech_selector"
        )
    
    with col2:
        # Date filter
        date_filter = st.selectbox(
            "📅 View:",
            ["All Assignments", "Today Only", "This Week", "Upcoming"],
            key="date_filter"
        )
    
    # Filter for selected technician
    tech_assignments = assigned_df[assigned_df['Optimized_technician_id'] == selected_tech].copy()
    
    # Parse dates for filtering
    tech_assignments['Appointment_date_parsed'] = pd.to_datetime(tech_assignments['Appointment_date'], errors='coerce')
    today = pd.Timestamp.now().normalize()
    week_end = today + pd.Timedelta(days=7)
    
    # Apply date filter
    if date_filter == "Today Only":
        tech_assignments = tech_assignments[tech_assignments['Appointment_date_parsed'] == today]
    elif date_filter == "This Week":
        tech_assignments = tech_assignments[
            (tech_assignments['Appointment_date_parsed'] >= today) & 
            (tech_assignments['Appointment_date_parsed'] <= week_end)
        ]
    elif date_filter == "Upcoming":
        tech_assignments = tech_assignments[tech_assignments['Appointment_date_parsed'] >= today]
    
    if len(tech_assignments) == 0:
        st.info(f"No assignments found for the selected time period ({date_filter}).")
        st.stop()
    
    # ============================================================
    # DASHBOARD METRICS
    # ============================================================
    st.markdown(f"### 📊 Overview - {len(tech_assignments)} Assignment(s)")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📋 Total Jobs", len(tech_assignments))
    
    with col2:
        avg_success = tech_assignments['Predicted_success_prob'].mean()
        success_color = "🟢" if avg_success >= 0.7 else "🟡" if avg_success >= 0.5 else "🔴"
        st.metric("🎯 Avg Success", f"{avg_success:.1%}", f"{success_color}")
    
    with col3:
        total_distance = tech_assignments['Optimized_distance_km'].sum()
        st.metric("🚗 Total Distance", f"{total_distance:.1f} km")
    
    with col4:
        total_duration = tech_assignments['Optimized_predicted_duration_min'].sum()
        hours = total_duration / 60
        st.metric("⏱️ Est. Time", f"{hours:.1f} hrs")
    
    with col5:
        avg_workload = tech_assignments['Optimized_workload_ratio'].mean()
        workload_emoji = "🔴" if avg_workload > 0.8 else "🟡" if avg_workload > 0.5 else "🟢"
        st.metric("📊 Workload", f"{avg_workload:.0%}", f"{workload_emoji}")
    
    st.markdown("---")
    
    # ============================================================
    # INTERACTIVE ASSIGNMENT CARDS
    # ============================================================
    st.markdown("### 📋 Assignment Details")
    
    # Sort by appointment date and time
    tech_assignments = tech_assignments.sort_values(['Appointment_date', 'Appointment_start_time'])
    
    # View mode selector
    view_mode_tech = st.radio(
        "Display Mode:",
        ["📇 Detailed Cards", "📊 Table View", "🗺️ Route Overview"],
        horizontal=True,
        key="tech_view_mode"
    )
    
    if view_mode_tech == "📇 Detailed Cards":
        # ============================================================
        # DETAILED CARD VIEW
        # ============================================================
        
        # Group by date
        tech_assignments['date_only'] = tech_assignments['Appointment_date_parsed'].dt.date
        
        for date, date_group in tech_assignments.groupby('date_only'):
            st.markdown(f"#### 📅 {date.strftime('%A, %B %d, %Y')}")
            st.markdown(f"*{len(date_group)} assignment(s) scheduled*")
            
            # Sort by time within date
            date_group = date_group.sort_values('Appointment_start_time')
            
            for idx, row in date_group.iterrows():
                # Determine priority and status
                success_prob = row['Predicted_success_prob']
                distance = row['Optimized_distance_km']
                duration = row['Optimized_predicted_duration_min']
                
                # Priority indicator
                if success_prob >= 0.7:
                    priority = "🟢 High Confidence"
                    card_color = "#d5f4e6"
                elif success_prob >= 0.5:
                    priority = "🟡 Medium Confidence"
                    card_color = "#fff9c4"
                else:
                    priority = "🔴 Needs Attention"
                    card_color = "#ffe0b2"
                
                # Create expandable card
                with st.expander(
                    f"🔧 {row['Appointment_start_time']} - Dispatch #{row['Dispatch_id']} | {row['City']} | {priority}",
                    expanded=False
                ):
                    # Card layout
                    card_col1, card_col2, card_col3 = st.columns([2, 2, 1])
                    
                    with card_col1:
                        st.markdown(f"""
                        **📍 Location Details**
                        - **City:** {row['City']}
                        - **Coordinates:** {row['Customer_latitude']:.4f}, {row['Customer_longitude']:.4f}
                        - **Distance:** {distance:.1f} km from base
                        
                        **🔧 Job Details**
                        - **Required Skill:** {row['Required_skill']}
                        - **Service Tier:** {row['Service_tier']}
                        - **Equipment:** {row['Equipment_installed']}
                        """)
                    
                    with card_col2:
                        st.markdown(f"""
                        **⏱️ Time & Duration**
                        - **Appointment:** {row['Appointment_start_time']}
                        - **Estimated Duration:** {duration:.0f} minutes
                        - **End Time:** ~{row['Appointment_start_time']}
                        
                        **📊 Performance Metrics**
                        - **Success Probability:** {success_prob:.1%}
                        - **Confidence Score:** {row['Optimization_confidence']:.1%}
                        - **Workload Ratio:** {row['Optimized_workload_ratio']:.1%}
                        """)
                    
                    with card_col3:
                        # Visual indicators
                        st.markdown("**Status**")
                        st.markdown(f"<div style='background-color: {card_color}; padding: 10px; border-radius: 5px; text-align: center;'>{priority}</div>", unsafe_allow_html=True)
                        
                        st.markdown("")
                        st.markdown("**Priority**")
                        if success_prob < 0.5:
                            st.warning("⚠️ Review Required")
                        elif distance > 50:
                            st.info("🚗 Long Distance")
                        else:
                            st.success("✅ Standard")
                    
                    # Action buttons
                    st.markdown("---")
                    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
                    
                    with btn_col1:
                        if st.button(f"📍 View Map", key=f"map_{row['Dispatch_id']}"):
                            st.info(f"Map view: ({row['Customer_latitude']}, {row['Customer_longitude']})")
                    
                    with btn_col2:
                        if st.button(f"📞 Contact", key=f"contact_{row['Dispatch_id']}"):
                            st.info("Customer contact feature")
                    
                    with btn_col3:
                        if st.button(f"📝 Notes", key=f"notes_{row['Dispatch_id']}"):
                            st.info("Add notes feature")
                    
                    with btn_col4:
                        if st.button(f"✅ Complete", key=f"complete_{row['Dispatch_id']}"):
                            st.success("Mark as complete feature")
            
            st.markdown("---")
    
    elif view_mode_tech == "📊 Table View":
        # ============================================================
        # TABLE VIEW
        # ============================================================
        
        # Prepare display columns
        display_cols = [
            'Dispatch_id', 'Appointment_date', 'Appointment_start_time',
            'City', 'Required_skill', 'Service_tier', 'Equipment_installed',
            'Optimized_distance_km', 'Predicted_success_prob',
            'Optimized_predicted_duration_min', 'Optimization_confidence'
        ]
        
        tech_display = tech_assignments[display_cols].copy()
        tech_display.columns = [
            'Dispatch ID', 'Date', 'Time',
            'City', 'Skill', 'Service Tier', 'Equipment',
            'Distance (km)', 'Success Prob',
            'Duration (min)', 'Confidence'
        ]
        
        # Color code by success probability
        def color_tech_rows(row):
            success = row['Success Prob']
            if success >= 0.7:
                return ['background-color: #d5f4e6'] * len(row)
            elif success >= 0.5:
                return ['background-color: #fff9c4'] * len(row)
            else:
                return ['background-color: #ffe0b2'] * len(row)
        
        st.dataframe(
            tech_display.style.apply(color_tech_rows, axis=1).format({
                'Success Prob': '{:.1%}',
                'Confidence': '{:.1%}',
                'Distance (km)': '{:.1f}',
                'Duration (min)': '{:.0f}'
            }),
            width='stretch',
            height=500
        )
        
        # Legend
        st.markdown("""
        **Color Legend:** 
        🟢 Green = High Success (≥70%) | 
        🟡 Yellow = Medium Success (50-70%) | 
        🔴 Orange = Needs Attention (<50%)
        """)
    
    else:
        # ============================================================
        # ROUTE OVERVIEW
        # ============================================================
        
        st.markdown("### 🗺️ Route Overview & Statistics")
        
        # Route statistics
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 Route Statistics")
            
            cities = tech_assignments['City'].value_counts()
            st.markdown(f"**Cities to Visit:** {len(cities)}")
            for city, count in cities.items():
                st.write(f"- {city}: {count} assignment(s)")
            
            st.markdown(f"\n**Total Travel Distance:** {tech_assignments['Optimized_distance_km'].sum():.1f} km")
            st.markdown(f"**Average Distance per Job:** {tech_assignments['Optimized_distance_km'].mean():.1f} km")
            st.markdown(f"**Longest Trip:** {tech_assignments['Optimized_distance_km'].max():.1f} km")
        
        with col2:
            st.markdown("#### ⏱️ Time Management")
            
            total_time = tech_assignments['Optimized_predicted_duration_min'].sum()
            total_travel = tech_assignments['Optimized_distance_km'].sum() * 2  # Estimate 2 min per km
            
            st.markdown(f"**Total Job Time:** {total_time:.0f} minutes ({(total_time/60):.1f} hours)")
            st.markdown(f"**Estimated Travel Time:** {total_travel:.0f} minutes ({(total_travel/60):.1f} hours)")
            st.markdown(f"**Total Working Time:** {(total_time + total_travel):.0f} minutes ({((total_time + total_travel)/60):.1f} hours)")
            
            # Time distribution by skill
            st.markdown("\n**Time by Skill:**")
            skill_time = tech_assignments.groupby('Required_skill')['Optimized_predicted_duration_min'].sum()
            for skill, time in skill_time.items():
                st.write(f"- {skill}: {time:.0f} min ({(time/60):.1f} hrs)")
        
        # Distance distribution chart
        st.markdown("#### 📍 Distance Distribution")
        
        fig_distance = px.bar(
            tech_assignments,
            x='Dispatch_id',
            y='Optimized_distance_km',
            color='City',
            title='Travel Distance by Assignment',
            labels={'Optimized_distance_km': 'Distance (km)', 'Dispatch_id': 'Assignment ID'},
            height=400
        )
        st.plotly_chart(fig_distance, width='stretch')
        
        # Timeline view
        st.markdown("#### 🕐 Daily Timeline")
        
        timeline_data = tech_assignments.sort_values('Appointment_start_time').copy()
        timeline_data['Job Duration (hrs)'] = timeline_data['Optimized_predicted_duration_min'] / 60
        
        fig_timeline = px.bar(
            timeline_data,
            x='Appointment_start_time',
            y='Job Duration (hrs)',
            color='Required_skill',
            title='Job Duration Timeline',
            labels={'Appointment_start_time': 'Appointment Time', 'Job Duration (hrs)': 'Duration (hours)'},
            height=400,
            hover_data=['Dispatch_id', 'City', 'Predicted_success_prob']
        )
        st.plotly_chart(fig_timeline, width='stretch')
    
    # ============================================================
    # PERFORMANCE INSIGHTS & TIPS
    # ============================================================
    st.markdown("---")
    st.markdown("### 💡 Performance Insights & Tips")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        high_success = (tech_assignments['Predicted_success_prob'] >= 0.7).sum()
        st.markdown(f"**🎯 High Confidence Jobs:** {high_success} ({(high_success/len(tech_assignments)*100):.1f}%)")
        
        low_success = (tech_assignments['Predicted_success_prob'] < 0.5).sum()
        if low_success > 0:
            st.warning(f"⚠️ {low_success} assignment(s) may need extra preparation")
        else:
            st.success("✅ All assignments have good success probability")
    
    with col2:
        long_distance = (tech_assignments['Optimized_distance_km'] > 30).sum()
        st.markdown(f"**🚗 Long Distance Trips:** {long_distance}")
        
        if long_distance > 0:
            st.info(f"💡 Consider optimizing route planning")
        else:
            st.success("✅ All jobs are within reasonable distance")
    
    with col3:
        total_duration = tech_assignments['Optimized_predicted_duration_min'].sum()
        if total_duration > 480:  # More than 8 hours
            st.markdown(f"**⏰ Workload:** Heavy ({(total_duration/60):.1f} hrs)")
            st.warning("⚠️ Consider scheduling breaks")
        elif total_duration > 360:  # 6-8 hours
            st.markdown(f"**⏰ Workload:** Moderate ({(total_duration/60):.1f} hrs)")
            st.info("💡 Manageable schedule")
        else:
            st.markdown(f"**⏰ Workload:** Light ({(total_duration/60):.1f} hrs)")
            st.success("✅ Comfortable schedule")
    
    # ============================================================
    # DOWNLOAD OPTIONS
    # ============================================================
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Download full schedule
        schedule_csv = tech_assignments.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Full Schedule (CSV)",
            data=schedule_csv,
            file_name=f"technician_{selected_tech}_schedule_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with col2:
        # Download daily summary
        summary_data = tech_assignments.groupby('Appointment_date').agg({
            'Dispatch_id': 'count',
            'Optimized_distance_km': 'sum',
            'Optimized_predicted_duration_min': 'sum',
            'Predicted_success_prob': 'mean'
        }).reset_index()
        summary_data.columns = ['Date', 'Assignments', 'Total Distance (km)', 'Total Time (min)', 'Avg Success Prob']
        
        summary_csv = summary_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📊 Download Daily Summary (CSV)",
            data=summary_csv,
            file_name=f"technician_{selected_tech}_summary_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with col3:
        # Download route details
        route_data = tech_assignments[['Dispatch_id', 'City', 'Customer_latitude', 'Customer_longitude', 
                                       'Appointment_start_time', 'Optimized_distance_km']].copy()
        route_csv = route_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="🗺️ Download Route Data (CSV)",
            data=route_csv,
            file_name=f"technician_{selected_tech}_route_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

else:
    # ============================================================
    # DASHBOARD VIEW - ANALYTICS (ORIGINAL)
    # ============================================================
    
    # Sidebar - Filters and Controls
    st.sidebar.header("🎛️ Filters & Controls")

    # City filter
    cities = ['All'] + sorted(df['City'].dropna().unique().tolist())
    selected_city = st.sidebar.selectbox("Select City", cities)

    # Required skill filter
    skills = ['All'] + sorted(df['Required_skill'].dropna().unique().tolist())
    selected_skill = st.sidebar.selectbox("Select Required Skill", skills)

    # Fallback level filter
    fallback_levels = ['All'] + sorted(df['Fallback_level'].dropna().unique().tolist())
    selected_fallback = st.sidebar.selectbox("Select Fallback Level", fallback_levels)

    # Assignment status filter
    assignment_status = st.sidebar.radio(
        "Assignment Status",
        ["All", "Assigned", "Unassigned"]
    )

    # Apply filters
    filtered_df = df.copy()

    if selected_city != 'All':
        filtered_df = filtered_df[filtered_df['City'] == selected_city]

    if selected_skill != 'All':
        filtered_df = filtered_df[filtered_df['Required_skill'] == selected_skill]

    if selected_fallback != 'All':
        filtered_df = filtered_df[filtered_df['Fallback_level'] == selected_fallback]

    if assignment_status == "Assigned":
        filtered_df = filtered_df[filtered_df['Optimized_technician_id'].notna()]
    elif assignment_status == "Unassigned":
        filtered_df = filtered_df[filtered_df['Optimized_technician_id'].isna()]

    # Display filter info
    st.sidebar.markdown("---")
    st.sidebar.metric("Filtered Dispatches", len(filtered_df))
    st.sidebar.metric("Total Dispatches", len(df))

    # Main dashboard content
    if len(filtered_df) == 0:
        st.warning("No dispatches match the selected filters.")
        st.stop()

    # ============================================================
    # INITIAL VS OPTIMIZED COMPARISON (HERO SECTION)
    # ============================================================
    st.header("📊 Initial vs Optimized Comparison")

    # Create comparison cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("### 🎯 Success Probability")
        initial_success = filtered_df['Initial_success_prob'].mean()
        optimized_success = filtered_df['Predicted_success_prob'].mean()
        success_change = optimized_success - initial_success
        
        st.metric(
            label="Initial",
            value=f"{initial_success:.3f}",
            delta=None
        )
        st.metric(
            label="Optimized",
            value=f"{optimized_success:.3f}",
            delta=f"{success_change:+.3f}",
            delta_color="normal" if success_change >= 0 else "inverse"
        )

    with col2:
        st.markdown("### 📍 Average Distance")
        initial_dist = filtered_df['Initial_distance_km'].mean()
        optimized_dist = filtered_df['Optimized_distance_km'].mean()
        dist_change = optimized_dist - initial_dist
        
        st.metric(
            label="Initial",
            value=f"{initial_dist:.1f} km",
            delta=None
        )
        st.metric(
            label="Optimized",
            value=f"{optimized_dist:.1f} km",
            delta=f"{dist_change:+.1f} km",
            delta_color="inverse" if dist_change < 0 else "normal"
        )

    with col3:
        st.markdown("### ⚖️ Workload Ratio")
        initial_workload = filtered_df['Initial_workload_ratio'].mean()
        optimized_workload = filtered_df['Optimized_workload_ratio'].mean()
        workload_change = optimized_workload - initial_workload
        
        st.metric(
            label="Initial",
            value=f"{initial_workload:.1%}",
            delta=None
        )
        st.metric(
            label="Optimized",
            value=f"{optimized_workload:.1%}",
            delta=f"{workload_change:+.1%}",
            delta_color="normal" if abs(workload_change) < 0.05 else "inverse"
        )

    with col4:
        st.markdown("### 💪 Confidence Score")
        initial_conf = filtered_df['Initial_confidence'].mean()
        optimized_conf = filtered_df['Optimization_confidence'].mean()
        conf_change = optimized_conf - initial_conf
        
        st.metric(
            label="Initial",
            value=f"{initial_conf:.3f}",
            delta=None
        )
        st.metric(
            label="Optimized",
            value=f"{optimized_conf:.3f}",
            delta=f"{conf_change:+.3f}",
            delta_color="normal" if conf_change >= 0 else "inverse"
        )

    # Summary bar with key improvements
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        total_distance_saved = (filtered_df['Initial_distance_km'].sum() - filtered_df['Optimized_distance_km'].sum())
        st.markdown(f"### 🚗 Distance Saved")
        st.markdown(f"<h2 style='text-align: center; color: #2ecc71;'>{abs(total_distance_saved):.0f} km</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center;'>Fuel savings: ${abs(total_distance_saved * 0.50):.0f}</p>", unsafe_allow_html=True)

    with col2:
        improved_count = (filtered_df['Success_prob_improvement'] > 0).sum()
        total_count = len(filtered_df)
        improvement_pct = (improved_count / total_count * 100) if total_count > 0 else 0
        st.markdown(f"### 📈 Improved Assignments")
        st.markdown(f"<h2 style='text-align: center; color: #3498db;'>{improved_count} / {total_count}</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center;'>{improvement_pct:.1f}% improved</p>", unsafe_allow_html=True)

    with col3:
        assigned_count = filtered_df['Optimized_technician_id'].notna().sum()
        assignment_rate = (assigned_count / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
        st.markdown(f"### ✅ Assignment Rate")
        st.markdown(f"<h2 style='text-align: center; color: #9b59b6;'>{assignment_rate:.1f}%</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center;'>{assigned_count} of {len(filtered_df)} assigned</p>", unsafe_allow_html=True)

    st.markdown("---")

    # Visual Comparison Chart
    st.subheader("📊 Visual Performance Comparison")

    comparison_data = pd.DataFrame({
        'Metric': ['Success Probability', 'Success Probability', 'Avg Distance (km)', 'Avg Distance (km)', 
                   'Workload Ratio', 'Workload Ratio', 'Confidence', 'Confidence'],
        'Type': ['Initial', 'Optimized', 'Initial', 'Optimized', 'Initial', 'Optimized', 'Initial', 'Optimized'],
        'Value': [
            initial_success, optimized_success,
            initial_dist, optimized_dist,
            initial_workload, optimized_workload,
            initial_conf, optimized_conf
        ]
    })

    fig_comparison = px.bar(
        comparison_data,
        x='Metric',
        y='Value',
        color='Type',
        barmode='group',
        title='Initial vs Optimized Performance Metrics',
        color_discrete_map={'Initial': '#e74c3c', 'Optimized': '#2ecc71'},
        height=400
    )

    fig_comparison.update_layout(
        xaxis_title='',
        yaxis_title='Value',
        legend_title='',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig_comparison, width='stretch')

    st.markdown("---")

    # ============================================================
    # KEY METRICS OVERVIEW
    # ============================================================
    st.header("📊 Detailed Metrics")

    col1, col2, col3, col4, col5 = st.columns(5)

    # Calculate metrics
    assigned_count = filtered_df['Optimized_technician_id'].notna().sum()
    unassigned_count = filtered_df['Optimized_technician_id'].isna().sum()
    assignment_rate = (assigned_count / len(filtered_df)) * 100

    avg_initial_success = filtered_df['Initial_success_prob'].mean()
    avg_optimized_success = filtered_df['Predicted_success_prob'].mean()
    success_improvement = avg_optimized_success - avg_initial_success

    avg_initial_distance = filtered_df['Initial_distance_km'].mean()
    avg_optimized_distance = filtered_df['Optimized_distance_km'].mean()
    distance_reduction = avg_initial_distance - avg_optimized_distance

    total_distance_saved = filtered_df['Distance_change_km'].sum()
    fuel_savings = abs(total_distance_saved) * 0.50  # $0.50 per km

    with col1:
        st.metric(
            "Assignment Rate",
            f"{assignment_rate:.1f}%",
            f"{assigned_count} / {len(filtered_df)}"
        )

    with col2:
        st.metric(
            "Avg Success Probability",
            f"{avg_optimized_success:.3f}",
            f"{success_improvement:+.3f}",
            delta_color="normal" if success_improvement >= 0 else "inverse"
        )

    with col3:
        st.metric(
            "Avg Distance (km)",
            f"{avg_optimized_distance:.1f}",
            f"{-distance_reduction:+.1f} km",
            delta_color="inverse" if distance_reduction > 0 else "normal"
        )

    with col4:
        st.metric(
            "Total Distance Saved",
            f"{abs(total_distance_saved):.0f} km",
            f"${fuel_savings:.0f} saved"
        )

    with col5:
        improvement_rate = (filtered_df['Success_prob_improvement'] > 0).sum()
        improvement_pct = (improvement_rate / len(filtered_df)) * 100
        st.metric(
            "Improved Assignments",
            f"{improvement_rate}",
            f"{improvement_pct:.1f}%"
        )

    st.markdown("---")

    # ============================================================
    # DETAILED COMPARISON CHARTS
    # ============================================================
    st.header("📈 Detailed Performance Analysis")

    # Create tabs for different visualizations
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview", "🎯 Success Probability", "📍 Distance Analysis", 
    "⚖️ Workload Balance", "🔍 Individual Dispatches"
    ])

    # TAB 1: Overview Comparisons
    with tab1:
        st.subheader("Initial vs Optimized Comparison")
        
        # Create comparison metrics
        col1, col2 = st.columns(2)
        
        with col1:
            # Success Probability Comparison
            fig_success = go.Figure()
            
            fig_success.add_trace(go.Box(
                y=filtered_df['Initial_success_prob'],
                name='Initial',
                marker_color='lightblue',
                boxmean='sd'
            ))
            
            fig_success.add_trace(go.Box(
                y=filtered_df['Predicted_success_prob'],
                name='Optimized',
                marker_color='lightgreen',
                boxmean='sd'
            ))
            
            fig_success.update_layout(
                title='Success Probability Distribution',
                yaxis_title='Success Probability',
                showlegend=True,
                height=400
            )
            
            st.plotly_chart(fig_success, width='stretch')
        
        with col2:
            # Distance Comparison
            fig_distance = go.Figure()
            
            fig_distance.add_trace(go.Box(
                y=filtered_df['Initial_distance_km'],
                name='Initial',
                marker_color='salmon',
                boxmean='sd'
            ))
            
            fig_distance.add_trace(go.Box(
                y=filtered_df['Optimized_distance_km'],
                name='Optimized',
                marker_color='lightcoral',
                boxmean='sd'
            ))
            
            fig_distance.update_layout(
                title='Distance Distribution (km)',
                yaxis_title='Distance (km)',
                showlegend=True,
                height=400
            )
            
            st.plotly_chart(fig_distance, width='stretch')
        
        # Improvement breakdown
        st.subheader("Improvement Breakdown")
        
        improved = (filtered_df['Success_prob_improvement'] > 0).sum()
        worse = (filtered_df['Success_prob_improvement'] < 0).sum()
        unchanged = (filtered_df['Success_prob_improvement'] == 0).sum()
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Improved', 'Worse', 'Unchanged'],
            values=[improved, worse, unchanged],
            hole=.3,
            marker_colors=['#2ecc71', '#e74c3c', '#95a5a6']
        )])
        
        fig_pie.update_layout(
            title='Assignment Outcome Distribution',
            height=400
        )
        
        st.plotly_chart(fig_pie, width='stretch')

        # TAB 2: Success Probability Analysis
    with tab2:
        st.subheader("Success Probability Deep Dive")
    
        col1, col2 = st.columns(2)
    
        with col1:
            # Histogram of success probability improvement
            fig_hist = px.histogram(
                filtered_df,
                x='Success_prob_improvement',
                nbins=50,
                title='Success Probability Improvement Distribution',
                labels={'Success_prob_improvement': 'Improvement', 'count': 'Number of Dispatches'},
                color_discrete_sequence=['#3498db']
            )
            fig_hist.add_vline(x=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_hist, width='stretch')
        
        with col2:
            # Success probability by skill
            skill_success = filtered_df.groupby('Required_skill').agg({
                'Initial_success_prob': 'mean',
                'Predicted_success_prob': 'mean'
            }).reset_index()
            
            fig_skill = go.Figure()
            fig_skill.add_trace(go.Bar(
                x=skill_success['Required_skill'],
                y=skill_success['Initial_success_prob'],
                name='Initial',
                marker_color='lightblue'
            ))
            fig_skill.add_trace(go.Bar(
                x=skill_success['Required_skill'],
                y=skill_success['Predicted_success_prob'],
                name='Optimized',
                marker_color='lightgreen'
            ))
            
            fig_skill.update_layout(
                title='Average Success Probability by Skill',
                xaxis_title='Required Skill',
                yaxis_title='Avg Success Probability',
                barmode='group',
                height=400,
                xaxis={'tickangle': -45}
            )
            
            st.plotly_chart(fig_skill, width='stretch')
        
        # Scatter plot: Success vs Distance
        st.subheader("Success Probability vs Distance")
        
        fig_scatter = px.scatter(
            filtered_df,
            x='Optimized_distance_km',
            y='Predicted_success_prob',
            color='Fallback_level',
            size='Optimized_workload_ratio',
            hover_data=['Dispatch_id', 'Required_skill', 'City'],
            title='Success Probability vs Distance (size = workload)',
            labels={
                'Optimized_distance_km': 'Distance (km)',
                'Predicted_success_prob': 'Success Probability'
            }
        )
        
        st.plotly_chart(fig_scatter, width='stretch')

        # TAB 3: Distance Analysis
    with tab3:
        st.subheader("Distance Optimization Analysis")
    
        col1, col2 = st.columns(2)
    
        with col1:
            # Distance change histogram
            fig_dist_change = px.histogram(
                filtered_df,
                x='Distance_change_km',
                nbins=50,
                title='Distance Change Distribution',
                labels={'Distance_change_km': 'Distance Change (km)', 'count': 'Number of Dispatches'},
                color_discrete_sequence=['#e67e22']
            )
            fig_dist_change.add_vline(x=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_dist_change, width='stretch')
            
            # Distance statistics
            st.markdown("**Distance Statistics:**")
            total_initial = filtered_df['Initial_distance_km'].sum()
            total_optimized = filtered_df['Optimized_distance_km'].sum()
            total_saved = total_initial - total_optimized
            
            st.write(f"- Total Initial Distance: **{total_initial:,.0f} km**")
            st.write(f"- Total Optimized Distance: **{total_optimized:,.0f} km**")
            st.write(f"- Total Distance Saved: **{total_saved:,.0f} km** ({(total_saved/total_initial*100):.1f}%)")
            st.write(f"- Estimated Fuel Savings: **${abs(total_saved * 0.50):,.0f}**")
            st.write(f"- Estimated Time Saved: **{abs(total_saved * 2):,.0f} minutes**")
        
        with col2:
            # Distance by city
            city_distance = filtered_df.groupby('City').agg({
                'Initial_distance_km': 'mean',
                'Optimized_distance_km': 'mean'
            }).reset_index()
            
            fig_city = go.Figure()
            fig_city.add_trace(go.Bar(
                x=city_distance['City'],
                y=city_distance['Initial_distance_km'],
                name='Initial',
                marker_color='salmon'
            ))
            fig_city.add_trace(go.Bar(
                x=city_distance['City'],
                y=city_distance['Optimized_distance_km'],
                name='Optimized',
                marker_color='lightcoral'
            ))
            
            fig_city.update_layout(
                title='Average Distance by City',
                xaxis_title='City',
                yaxis_title='Average Distance (km)',
                barmode='group',
                height=400,
                xaxis={'tickangle': -45}
            )
            
            st.plotly_chart(fig_city, width='stretch')

        # TAB 4: Workload Balance
    with tab4:
        st.subheader("Technician Workload Analysis")
    
        col1, col2 = st.columns(2)
    
        with col1:
            # Workload distribution
            fig_workload = go.Figure()
            
            fig_workload.add_trace(go.Histogram(
                x=filtered_df['Initial_workload_ratio'],
                name='Initial',
                opacity=0.7,
                marker_color='lightblue',
                nbinsx=30
            ))
            
            fig_workload.add_trace(go.Histogram(
                x=filtered_df['Optimized_workload_ratio'],
                name='Optimized',
                opacity=0.7,
                marker_color='lightgreen',
                nbinsx=30
            ))
            
            fig_workload.add_vline(x=0.8, line_dash="dash", line_color="orange", 
                                   annotation_text="80% capacity")
            fig_workload.add_vline(x=1.0, line_dash="dash", line_color="red", 
                                   annotation_text="100% capacity")
            
            fig_workload.update_layout(
                title='Workload Ratio Distribution',
                xaxis_title='Workload Ratio',
                yaxis_title='Number of Assignments',
                barmode='overlay',
                height=400
            )
            
            st.plotly_chart(fig_workload, width='stretch')
        
        with col2:
            # Workload statistics
            st.markdown("**Workload Statistics:**")
            
            initial_over_80 = (filtered_df['Initial_workload_ratio'] > 0.8).sum()
            optimized_over_80 = (filtered_df['Optimized_workload_ratio'] > 0.8).sum()
            
            initial_over_100 = (filtered_df['Initial_workload_ratio'] > 1.0).sum()
            optimized_over_100 = (filtered_df['Optimized_workload_ratio'] > 1.0).sum()
            
            st.write(f"**Initial Assignments:**")
            st.write(f"- Over 80% capacity: **{initial_over_80}** ({(initial_over_80/len(filtered_df)*100):.1f}%)")
            st.write(f"- Over 100% capacity: **{initial_over_100}** ({(initial_over_100/len(filtered_df)*100):.1f}%)")
            
            st.write(f"\n**Optimized Assignments:**")
            st.write(f"- Over 80% capacity: **{optimized_over_80}** ({(optimized_over_80/len(filtered_df)*100):.1f}%)")
            st.write(f"- Over 100% capacity: **{optimized_over_100}** ({(optimized_over_100/len(filtered_df)*100):.1f}%)")
            
            # Workload change
            fig_workload_change = px.histogram(
                filtered_df,
                x='Workload_ratio_change',
                nbins=50,
                title='Workload Ratio Change',
                labels={'Workload_ratio_change': 'Workload Change', 'count': 'Count'},
                color_discrete_sequence=['#9b59b6']
            )
            fig_workload_change.add_vline(x=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_workload_change, width='stretch')

        # TAB 5: Individual Dispatches
    with tab5:
        st.subheader("Individual Dispatch Details")
    
        # Search by Dispatch ID
        search_id = st.text_input("Search by Dispatch ID", "")
    
        if search_id:
            filtered_df = filtered_df[filtered_df['Dispatch_id'].astype(str).str.contains(search_id)]
        
        # Display mode
        display_mode = st.radio(
            "Display Mode",
            ["Show All Columns", "Show Key Metrics Only"],
            horizontal=True
        )
    
        if display_mode == "Show Key Metrics Only":
            columns_to_show = [
                'Dispatch_id', 'City', 'Required_skill',
                'Assigned_technician_id', 'Optimized_technician_id',
                'Initial_success_prob', 'Predicted_success_prob', 'Success_prob_improvement',
                'Initial_distance_km', 'Optimized_distance_km', 'Distance_change_km',
                'Fallback_level'
            ]
            display_df = filtered_df[columns_to_show]
        else:
            display_df = filtered_df
    
        # Color code improvements
        def highlight_improvements(row):
            if row['Success_prob_improvement'] > 0:
                return ['background-color: #d5f4e6'] * len(row)
            elif row['Success_prob_improvement'] < 0:
                return ['background-color: #fadbd8'] * len(row)
            else:
                return [''] * len(row)
        
        # Display dataframe
        st.dataframe(
            display_df.style.apply(highlight_improvements, axis=1),
            width='stretch',
            height=400
        )
    
        # Download filtered data
        csv = display_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered Data as CSV",
            data=csv,
            file_name=f"filtered_dispatches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

        # ============================================================
        # FALLBACK LEVEL ANALYSIS
        # ============================================================
        st.markdown("---")
        st.header("🎯 Fallback Level Analysis")

        col1, col2 = st.columns(2)

        with col1:
            # Fallback level distribution
            fallback_counts = filtered_df['Fallback_level'].value_counts()
            
            fig_fallback = px.pie(
                values=fallback_counts.values,
                names=fallback_counts.index,
                title='Fallback Level Distribution',
                hole=0.3
            )
            
            st.plotly_chart(fig_fallback, width='stretch')

        with col2:
            # Success probability by fallback level
            fallback_success = filtered_df.groupby('Fallback_level')['Predicted_success_prob'].agg(['mean', 'count']).reset_index()
            
            fig_fallback_success = px.bar(
                fallback_success,
                x='Fallback_level',
                y='mean',
                title='Average Success Probability by Fallback Level',
                labels={'mean': 'Avg Success Probability', 'Fallback_level': 'Fallback Level'},
                text='count',
                color='mean',
                color_continuous_scale='RdYlGn'
            )
            
            fig_fallback_success.update_traces(texttemplate='n=%{text}', textposition='outside')
            
            st.plotly_chart(fig_fallback_success, width='stretch')

        # ============================================================
        # SYSTEM INFORMATION
        # ============================================================
        st.markdown("---")
        st.header("ℹ️ System Information")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Assignment Mode:**")
            # Check if ml_based is in fallback levels
            if 'ml_based' in df['Fallback_level'].unique():
                st.success("🤖 ML-Based Assignment")
                st.write("Evaluates ALL available technicians using ML model")
            else:
                st.info("📋 Legacy Cascading Fallback")

        with col2:
            st.markdown("**Optimization Timestamp:**")
            if 'Optimization_timestamp' in df.columns:
                timestamp = df['Optimization_timestamp'].iloc[0]
                st.write(f"🕐 {timestamp}")
            else:
                st.write("N/A")

        with col3:
            st.markdown("**Data Summary:**")
            st.write(f"- Total Dispatches: **{len(df)}**")
            st.write(f"- Unique Cities: **{df['City'].nunique()}**")
            st.write(f"- Unique Skills: **{df['Required_skill'].nunique()}**")

        # Footer
        st.markdown("---")
        st.markdown(
            """
            <div style='text-align: center; color: #7f8c8d; padding: 20px;'>
                <p>Smart Dispatch Optimization Dashboard v1.0</p>
                <p>Powered by ML-Based Assignment System | Built with Streamlit</p>
            </div>
            """,
            unsafe_allow_html=True
        )

