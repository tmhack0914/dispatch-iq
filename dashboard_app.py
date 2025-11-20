"""
Dispatch-IQ: Smart Dispatch Dashboard
AI-powered interactive web application for dispatch optimization and technician assignment
Version: 2.1.3 (Pandas 3.x Compatible - Full Array Support)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import os

# Import AI Assistant
try:
    from ai_assistant import DispatchAIAssistant
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("AI Assistant not available. Install ai_assistant.py to enable.")

# Global helper function for pandas scalar conversion
def to_scalar(value):
    """
    Convert pandas Series/scalar to Python native type.
    Handles pandas 3.x stricter type conversion and various data types.
    """
    # Already a Python scalar type
    if isinstance(value, (int, float, bool, str)):
        return value
    
    # Handle pandas Series FIRST (before pd.isna check)
    if hasattr(value, 'iloc'):
        if len(value) == 0:
            return 0
        elif len(value) == 1:
            return to_scalar(value.iloc[0])  # Recursive call for nested types
        else:
            # Multiple values - shouldn't happen for aggregations, but handle it
            # Take the first value as a fallback
            return to_scalar(value.iloc[0])
    
    # Handle numpy arrays
    if isinstance(value, np.ndarray):
        if value.size == 0:
            return 0
        elif value.size == 1:
            return to_scalar(value.flat[0])  # Get the single element
        else:
            # Multiple values - take first
            return to_scalar(value.flat[0])
    
    # Handle NaN/None (only for scalar values, after Series/array handling)
    try:
        if pd.isna(value):
            return 0
    except (ValueError, TypeError):
        # If pd.isna fails on the value type, continue to other checks
        pass
    
    # Handle numpy scalar types
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        return value.item()
    
    # Try .item() method for pandas/numpy scalars
    if hasattr(value, 'item'):
        try:
            return value.item()
        except (ValueError, TypeError) as e:
            # If .item() fails, try alternative extraction
            pass
    
    # Try converting to float/int directly
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    
    try:
        return int(value)
    except (TypeError, ValueError):
        pass
    
    # Last resort - return 0 for safety
    print(f"Warning: Could not convert value to scalar: {type(value)}, returning 0")
    return 0

# Page configuration
st.set_page_config(
    page_title="Dispatch-IQ",
    page_icon="🧠",
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
st.title("🧠 Dispatch-IQ: Smart Dispatch Dashboard")
st.markdown("### AI-Powered Technician Assignment & Optimization")

# Data source indicator
data_source = "optimized_assignments.csv" if os.path.exists('optimized_assignments.csv') else "optimized_dispatch_results.csv"
st.caption(f"📊 Data Source: `{data_source}` | Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 🔧 v2.1.0 (Fixed)")

# View selector
view_mode = st.radio(
    "Select View:",
    ["📊 Dashboard (Analytics)", "📋 Assignments (Manager)", "👷 Technician View", "🤖 AI Assistant"],
    horizontal=True,
    key="view_selector"
)

st.markdown("---")

# Load data
@st.cache_data
def load_data():
    """Load the optimized dispatch results from optimize_dispatches.py output"""
    try:
        # Check if optimized_assignments.csv exists (new format)
        if os.path.exists('optimized_assignments.csv'):
            # Load optimized assignments
            optimized = pd.read_csv('optimized_assignments.csv')
            
            # Load current dispatches for full details
            if not os.path.exists('current_dispatches.csv'):
                return None, "⚠️ current_dispatches.csv not found. Please ensure your data files are present."
            
            dispatches = pd.read_csv('current_dispatches.csv')
            
            # Standardize column names for merging
            # optimized_assignments.csv uses lowercase dispatch_id
            # current_dispatches.csv might use Dispatch_id
            if 'Dispatch_id' in dispatches.columns:
                dispatches = dispatches.rename(columns={'Dispatch_id': 'dispatch_id'})
            
            # Before merging, drop any columns from dispatches that would conflict
            # This prevents duplicate columns after merge
            columns_to_add = ['optimized_technician_id', 'success_probability', 
                            'estimated_duration', 'distance', 'skill_match', 'score', 
                            'has_warnings', 'warning_count']
            for col in columns_to_add:
                if col in dispatches.columns:
                    dispatches = dispatches.drop(columns=[col])
            
            # Merge optimized assignments with dispatch details
            df = dispatches.merge(
                optimized[['dispatch_id', 'optimized_technician_id', 'success_probability', 
                          'estimated_duration', 'distance', 'skill_match', 'score', 
                          'has_warnings', 'warning_count']],
                on='dispatch_id',
                how='left'
            )
            
            # Remove any duplicate columns that may have been created
            df = df.loc[:, ~df.columns.duplicated()]
            
            # Remove duplicate index labels if any exist
            if df.index.duplicated().any():
                df = df[~df.index.duplicated(keep='first')]
            
            # Standardize column names to match dashboard expectations
            column_mapping = {
                'dispatch_id': 'Dispatch_id',
                'ticket_type': 'Ticket_type',
                'order_type': 'Order_type',
                'priority': 'Priority',
                'required_skill': 'Required_skill',
                'status': 'Status',
                'street': 'Street',
                'city': 'City',
                'county': 'County',
                'state': 'State',
                'postal_code': 'Postal_code',
                'customer_latitude': 'Customer_latitude',
                'customer_longitude': 'Customer_longitude',
                'appointment_start_datetime': 'Appointment_start_datetime',
                'appointment_end_datetime': 'Appointment_end_datetime',
                'duration_min': 'Duration_min',
                'assigned_technician_id': 'Assigned_technician_id',
                'optimized_technician_id': 'Optimized_technician_id',
                'success_probability': 'Predicted_success_prob',
                'estimated_duration': 'Optimized_predicted_duration_min',
                'distance': 'Optimized_distance_km',
                'skill_match': 'Skill_match_score',
                'score': 'Optimization_score',
                'has_warnings': 'Has_warnings',
                'warning_count': 'Warning_count'
            }
            
            # Apply column mapping (only for columns that exist)
            df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
            
            # Ensure required columns exist with defaults if missing
            if 'Appointment_date' not in df.columns and 'Appointment_start_datetime' in df.columns:
                df['Appointment_date'] = pd.to_datetime(df['Appointment_start_datetime'], errors='coerce').dt.date
            
            if 'Appointment_start_time' not in df.columns and 'Appointment_start_datetime' in df.columns:
                df['Appointment_start_time'] = pd.to_datetime(df['Appointment_start_datetime'], errors='coerce').dt.time
            
            # Add derived columns for dashboard compatibility
            if 'Initial_success_prob' not in df.columns:
                # Use a baseline success probability if not available
                df['Initial_success_prob'] = 0.5
            
            if 'Initial_distance_km' not in df.columns:
                df['Initial_distance_km'] = df.get('Optimized_distance_km', 0)
            
            if 'Initial_workload_ratio' not in df.columns:
                df['Initial_workload_ratio'] = 0.5
            
            if 'Optimized_workload_ratio' not in df.columns:
                df['Optimized_workload_ratio'] = 0.6
            
            # Add comparison metrics
            if 'Success_prob_improvement' not in df.columns and 'Predicted_success_prob' in df.columns:
                df['Success_prob_improvement'] = df['Predicted_success_prob'] - df['Initial_success_prob']
            
            if 'Distance_change_km' not in df.columns:
                df['Distance_change_km'] = df.get('Optimized_distance_km', 0) - df.get('Initial_distance_km', 0)
            
            if 'Workload_ratio_change' not in df.columns:
                df['Workload_ratio_change'] = df.get('Optimized_workload_ratio', 0) - df.get('Initial_workload_ratio', 0)
            
            # Add fallback level (from new system)
            if 'Fallback_level' not in df.columns:
                df['Fallback_level'] = 'ml_optimized'
            
            # Add optimization confidence
            if 'Optimization_confidence' not in df.columns and 'Predicted_success_prob' in df.columns:
                df['Optimization_confidence'] = df['Predicted_success_prob']
            
            # Add optimization timestamp
            if 'Optimization_timestamp' not in df.columns:
                df['Optimization_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Add service tier and equipment if missing
            if 'Service_tier' not in df.columns:
                df['Service_tier'] = 'Standard'
            
            if 'Equipment_installed' not in df.columns:
                df['Equipment_installed'] = 'None'
            
            # Add first time fix if missing
            if 'First_time_fix' not in df.columns:
                df['First_time_fix'] = 1
            
            return df, None
            
        # Fall back to old format if new format not available
        elif os.path.exists('optimized_dispatch_results.csv'):
            df = pd.read_csv('optimized_dispatch_results.csv')
            
            # Remove any duplicate columns
            df = df.loc[:, ~df.columns.duplicated()]
            
            # Remove duplicate index labels if any exist
            if df.index.duplicated().any():
                df = df[~df.index.duplicated(keep='first')]
            
            return df, None
        else:
            return None, "⚠️ No results file found. Please run: `python optimize_dispatches.py`"
            
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return None, f"⚠️ Error loading data: {str(e)}\n\nDetails:\n{error_details}"

# Add data management sidebar
st.sidebar.markdown("---")
st.sidebar.header("🔄 Data Management")

# Show data source info
st.sidebar.markdown("**Current Data Source:**")
if os.path.exists('optimized_assignments.csv'):
    file_stats = os.stat('optimized_assignments.csv')
    file_time = datetime.fromtimestamp(file_stats.st_mtime)
    st.sidebar.success(f"✅ optimized_assignments.csv")
    st.sidebar.caption(f"Modified: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
    st.sidebar.caption(f"Size: {file_stats.st_size / 1024:.1f} KB")
elif os.path.exists('optimized_dispatch_results.csv'):
    file_stats = os.stat('optimized_dispatch_results.csv')
    file_time = datetime.fromtimestamp(file_stats.st_mtime)
    st.sidebar.info(f"ℹ️ optimized_dispatch_results.csv (legacy)")
    st.sidebar.caption(f"Modified: {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    st.sidebar.warning("⚠️ No data file found")

st.sidebar.markdown("---")

# Buttons for data management
col1, col2 = st.sidebar.columns(2)

with col1:
    # Check if optimization script and dependencies exist
    optimization_available = os.path.exists('optimize_dispatches.py')
    
    # For Streamlit Cloud, always show as unavailable with explanation
    is_cloud = not optimization_available or not os.path.exists('.git')
    
    button_label = "🚀 Run Optimization (Local Only)"
    button_help = "Run optimization locally, then upload results" if is_cloud else "Execute optimize_dispatches.py"
    
    if st.button(button_label, 
                 help=button_help,
                 disabled=is_cloud,
                 use_container_width=True):
        with st.spinner("Running optimization..."):
            try:
                import subprocess
                result = subprocess.run(['python', 'optimize_dispatches.py'], 
                                       capture_output=True, 
                                       text=True,
                                       timeout=300)
                
                if result.returncode == 0:
                    st.success("✅ Optimization complete!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"❌ Failed:\n{result.stderr[:200]}")
            except subprocess.TimeoutExpired:
                st.error("⏱️ Timeout (> 5 min)")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

with col2:
    if st.button("🔄 Refresh", help="Reload data from CSV", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.sidebar.markdown("---")

# Show optimization settings info
st.sidebar.header("⚙️ How to Update Data")

# Always show instructions (works for both cloud and local)
st.sidebar.info("""
**📝 Workflow:**

1️⃣ **Run Locally**
```bash
python optimize_dispatches.py
```

2️⃣ **Upload to GitHub**
```bash
git add optimized_assignments.csv
git commit -m "Update results"
git push
```

3️⃣ **Wait 1-2 min**
Dashboard auto-updates!

🔄 Click "Refresh" button to reload
""")

with st.sidebar.expander("ℹ️ About Optimization"):
    st.markdown("""
    **Scoring Weights:**
    - Success Probability: 50%
    - Workload Balance: 35%
    - Travel Distance: 10%
    - Estimated Overrun: 5%

    **Requirements:**
    - PostgreSQL database
    - ML models (local)
    - Python dependencies
    
    **Why local-only?**
    Needs database access and large ML model files not suitable for cloud deployment.
    """)

# ============================================================
# AI ASSISTANT CHAT (Placeholder - initialized after data loads)
# ============================================================
st.sidebar.markdown("---")
st.sidebar.header("🤖 AI Assistant")

if not AI_AVAILABLE:
    st.sidebar.warning("AI Assistant not available. Please ensure ai_assistant.py is in the project directory.")
    st.sidebar.caption("The AI assistant helps answer questions about dispatches, routes, and assignments.")
else:
    st.sidebar.info("💬 AI Assistant will be available after data loads. Use the chat expander below or switch to the AI Assistant view.")

# Load data
df, error = load_data()

if error:
    st.error(error)
    st.info("""
    **To generate optimization results:**
    1. Ensure you have `current_dispatches.csv` in the project directory
    2. Click the '🚀 Run Optimization' button in the sidebar, OR
    3. Run from terminal: `python optimize_dispatches.py`
    4. The dashboard will automatically load `optimized_assignments.csv`
    """)
    st.stop()

# ============================================================
# AI ASSISTANT INITIALIZATION (After data is loaded)
# ============================================================

if AI_AVAILABLE and df is not None:
    # Initialize AI Assistant with loaded data
    if 'ai_assistant' not in st.session_state:
        st.session_state.ai_assistant = DispatchAIAssistant(df)
    
    # Update sidebar with AI Assistant chat
    with st.sidebar:
        st.markdown("---")
        
        # User role selection
        user_role = st.radio(
            "I am a:",
            ["👔 Dispatch Manager", "👷 Technician"],
            key="sidebar_user_role"
        )
        
        role = "manager" if "Manager" in user_role else "technician"
        
        # Technician ID input for technicians
        tech_context = {}
        if role == "technician":
            tech_id = st.text_input(
                "Your Technician ID:",
                placeholder="e.g., T900001",
                key="sidebar_tech_id"
            )
            if tech_id:
                tech_context['technician_id'] = tech_id
        
        # Chat interface in expander
        with st.expander("💬 Ask AI Assistant", expanded=False):
            # Initialize chat history
            if 'sidebar_chat_history' not in st.session_state:
                st.session_state.sidebar_chat_history = []
            
            # Chat input
            user_query = st.text_area(
                "Ask me anything:",
                placeholder="e.g., Show me dispatch #200000016 details",
                height=100,
                key="sidebar_ai_query"
            )
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("🚀 Ask", use_container_width=True, key="sidebar_ask_btn"):
                    if user_query:
                        # Process query
                        response = st.session_state.ai_assistant.process_query(
                            user_query, 
                            user_role=role,
                            context=tech_context
                        )
                        
                        # Add to chat history
                        st.session_state.sidebar_chat_history.append({
                            'query': user_query,
                            'response': response,
                            'timestamp': datetime.now().strftime('%H:%M:%S')
                        })
                        st.rerun()
            
            with col2:
                if st.button("🗑️ Clear", use_container_width=True, key="sidebar_clear_btn"):
                    st.session_state.sidebar_chat_history = []
                    st.rerun()
            
            # Show help button
            if st.button("❓ Help", use_container_width=True, key="sidebar_help_btn"):
                help_msg = st.session_state.ai_assistant._get_help_message(role)
                st.session_state.sidebar_chat_history.append({
                    'query': 'Help',
                    'response': help_msg,
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                })
                st.rerun()
            
            # Display chat history (most recent first)
            st.markdown("---")
            st.markdown("**💬 Recent Chats:**")
            
            if st.session_state.sidebar_chat_history:
                for i, chat in enumerate(reversed(st.session_state.sidebar_chat_history[-3:])):  # Show last 3
                    st.markdown(f"**[{chat['timestamp']}] You:**")
                    st.info(chat['query'])
                    st.markdown(f"**AI:**")
                    st.success(chat['response'])
                    if i < min(2, len(st.session_state.sidebar_chat_history) - 1):
                        st.markdown("---")
            else:
                st.caption("No chat history yet. Ask me a question!")

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
        assigned = int(to_scalar(filtered_assignments['Optimized_technician_id'].notna().sum()))
        st.metric("Assigned", assigned, f"{(assigned/len(filtered_assignments)*100):.1f}%")
    
    with col3:
        unassigned = int(to_scalar(filtered_assignments['Optimized_technician_id'].isna().sum()))
        st.metric("Unassigned", unassigned, delta_color="inverse" if unassigned > 0 else "off")
    
    with col4:
        avg_success = float(to_scalar(filtered_assignments['Predicted_success_prob'].mean()))
        st.metric("Avg Success Prob", f"{avg_success:.3f}")
    
    with col5:
        avg_distance = float(to_scalar(filtered_assignments['Optimized_distance_km'].mean()))
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
        avg_success = float(to_scalar(tech_assignments['Predicted_success_prob'].mean()))
        success_color = "🟢" if avg_success >= 0.7 else "🟡" if avg_success >= 0.5 else "🔴"
        st.metric("🎯 Avg Success", f"{avg_success:.1%}", f"{success_color}")
    
    with col3:
        total_distance = float(to_scalar(tech_assignments['Optimized_distance_km'].sum()))
        st.metric("🚗 Total Distance", f"{total_distance:.1f} km")
    
    with col4:
        total_duration = float(to_scalar(tech_assignments['Optimized_predicted_duration_min'].sum()))
        hours = total_duration / 60
        st.metric("⏱️ Est. Time", f"{hours:.1f} hrs")
    
    with col5:
        avg_workload = float(to_scalar(tech_assignments['Optimized_workload_ratio'].mean()))
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
                # Determine priority and status - safe column access
                success_prob = row.get('Predicted_success_prob', 0.5)
                distance = row.get('Optimized_distance_km', 0)
                duration = row.get('Optimized_predicted_duration_min', 0)
                
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
                
                # Safe access to card header fields
                appt_time_header = row.get('Appointment_start_time', 'N/A')
                dispatch_id_header = row.get('Dispatch_id', 'N/A')
                city_header = row.get('City', 'N/A')
                
                # Create expandable card
                with st.expander(
                    f"🔧 {appt_time_header} - Dispatch #{dispatch_id_header} | {city_header} | {priority}",
                    expanded=False
                ):
                    # Card layout
                    card_col1, card_col2, card_col3 = st.columns([2, 2, 1])
                    
                    with card_col1:
                        # Safe column access with defaults
                        city = row.get('City', 'N/A')
                        cust_lat = row.get('Customer_latitude', 0)
                        cust_lon = row.get('Customer_longitude', 0)
                        required_skill = row.get('Required_skill', 'N/A')
                        service_tier = row.get('Service_tier', 'Standard')
                        equipment = row.get('Equipment_installed', 'None')
                        
                        st.markdown(f"""
                        **📍 Location Details**
                        - **City:** {city}
                        - **Coordinates:** {cust_lat:.4f}, {cust_lon:.4f}
                        - **Distance:** {distance:.1f} km from base
                        
                        **🔧 Job Details**
                        - **Required Skill:** {required_skill}
                        - **Service Tier:** {service_tier}
                        - **Equipment:** {equipment}
                        """)
                    
                    with card_col2:
                        # Safe column access with defaults
                        appt_time = row.get('Appointment_start_time', 'N/A')
                        opt_confidence = row.get('Optimization_confidence', 0)
                        opt_workload = row.get('Optimized_workload_ratio', 0)
                        
                        st.markdown(f"""
                        **⏱️ Time & Duration**
                        - **Appointment:** {appt_time}
                        - **Estimated Duration:** {duration:.0f} minutes
                        - **End Time:** ~{appt_time}
                        
                        **📊 Performance Metrics**
                        - **Success Probability:** {success_prob:.1%}
                        - **Confidence Score:** {opt_confidence:.1%}
                        - **Workload Ratio:** {opt_workload:.1%}
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
                    
                    # Safe column access for buttons
                    btn_dispatch_id = row.get('Dispatch_id', idx)
                    btn_cust_lat = row.get('Customer_latitude', 0)
                    btn_cust_lon = row.get('Customer_longitude', 0)
                    
                    with btn_col1:
                        if st.button(f"📍 View Map", key=f"map_{btn_dispatch_id}"):
                            st.info(f"Map view: ({btn_cust_lat}, {btn_cust_lon})")
                    
                    with btn_col2:
                        if st.button(f"📞 Contact", key=f"contact_{btn_dispatch_id}"):
                            st.info("Customer contact feature")
                    
                    with btn_col3:
                        if st.button(f"📝 Notes", key=f"notes_{btn_dispatch_id}"):
                            st.info("Add notes feature")
                    
                    with btn_col4:
                        if st.button(f"✅ Complete", key=f"complete_{btn_dispatch_id}"):
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
            
            st.markdown(f"\n**Total Travel Distance:** {float(tech_assignments['Optimized_distance_km'].sum()):.1f} km")
            st.markdown(f"**Average Distance per Job:** {float(tech_assignments['Optimized_distance_km'].mean()):.1f} km")
            st.markdown(f"**Longest Trip:** {float(tech_assignments['Optimized_distance_km'].max()):.1f} km")
        
        with col2:
            st.markdown("#### ⏱️ Time Management")
            
            total_time = float(tech_assignments['Optimized_predicted_duration_min'].sum())
            total_travel = float(tech_assignments['Optimized_distance_km'].sum()) * 2  # Estimate 2 min per km
            
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
        high_success = int((tech_assignments['Predicted_success_prob'] >= 0.7).sum())
        st.markdown(f"**🎯 High Confidence Jobs:** {high_success} ({(high_success/len(tech_assignments)*100):.1f}%)")
        
        low_success = int((tech_assignments['Predicted_success_prob'] < 0.5).sum())
        if low_success > 0:
            st.warning(f"⚠️ {low_success} assignment(s) may need extra preparation")
        else:
            st.success("✅ All assignments have good success probability")
    
    with col2:
        long_distance = int((tech_assignments['Optimized_distance_km'] > 30).sum())
        st.markdown(f"**🚗 Long Distance Trips:** {long_distance}")
        
        if long_distance > 0:
            st.info(f"💡 Consider optimizing route planning")
        else:
            st.success("✅ All jobs are within reasonable distance")
    
    with col3:
        total_duration = float(tech_assignments['Optimized_predicted_duration_min'].sum())
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

elif view_mode == "🤖 AI Assistant":
    # ============================================================
    # AI ASSISTANT VIEW - INTERACTIVE CHAT
    # ============================================================
    st.header("🤖 AI Assistant - Smart Dispatch Helper")
    st.markdown("Ask me anything about dispatches, assignments, routes, and schedules")
    
    if not AI_AVAILABLE:
        st.error("❌ AI Assistant is not available. Please ensure `ai_assistant.py` is in the project directory.")
        st.info("""
        **To enable AI Assistant:**
        1. Ensure `ai_assistant.py` is uploaded to GitHub
        2. Refresh the dashboard
        3. AI Assistant will be ready to help!
        """)
        st.stop()
    
    # AI Assistant should already be initialized after data load
    # Just ensure it exists (fallback)
    if 'ai_assistant' not in st.session_state:
        st.session_state.ai_assistant = DispatchAIAssistant(df)
    
    if 'main_chat_history' not in st.session_state:
        st.session_state.main_chat_history = []
    
    # User role and context
    col1, col2 = st.columns([1, 2])
    
    with col1:
        user_role = st.radio(
            "I am a:",
            ["👔 Dispatch Manager", "👷 Technician"],
            key="main_user_role"
        )
        
        role = "manager" if "Manager" in user_role else "technician"
    
    with col2:
        tech_context = {}
        if role == "technician":
            tech_id = st.text_input(
                "Your Technician ID:",
                placeholder="e.g., T900001",
                key="main_tech_id"
            )
            if tech_id:
                tech_context['technician_id'] = tech_id
                st.success(f"✅ Logged in as {tech_id}")
    
    st.markdown("---")
    
    # Quick action buttons
    st.markdown("### 🚀 Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🚨 High Priority", use_container_width=True):
            response = st.session_state.ai_assistant.get_high_priority_dispatches()
            st.session_state.main_chat_history.append({
                'query': 'Show high priority dispatches',
                'response': response,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
    
    with col2:
        if st.button("⚠️ Unassigned", use_container_width=True):
            response = st.session_state.ai_assistant.get_unassigned_dispatches()
            st.session_state.main_chat_history.append({
                'query': 'Show unassigned dispatches',
                'response': response,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
    
    with col3:
        if st.button("⚖️ Workload", use_container_width=True):
            response = st.session_state.ai_assistant.get_workload_summary()
            st.session_state.main_chat_history.append({
                'query': 'Show workload summary',
                'response': response,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
    
    with col4:
        if role == "technician" and tech_context.get('technician_id'):
            if st.button("📅 My Schedule", use_container_width=True):
                response = st.session_state.ai_assistant.get_technician_schedule(tech_context['technician_id'])
                st.session_state.main_chat_history.append({
                    'query': f"Show schedule for {tech_context['technician_id']}",
                    'response': response,
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                })
        else:
            if st.button("❓ Help", use_container_width=True):
                response = st.session_state.ai_assistant._get_help_message(role)
                st.session_state.main_chat_history.append({
                    'query': 'Help',
                    'response': response,
                    'timestamp': datetime.now().strftime('%H:%M:%S')
                })
    
    st.markdown("---")
    
    # Main chat interface
    st.markdown("### 💬 Ask AI Assistant")
    
    # Chat input
    user_query = st.text_area(
        "Type your question here:",
        placeholder="Examples:\n- Show me dispatch #200000016 details\n- Route to dispatch #200000016\n- Who else can handle dispatch #200000016?\n- Show workload for all technicians",
        height=120,
        key="main_ai_query"
    )
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button("🚀 Ask AI", use_container_width=True, type="primary"):
            if user_query:
                with st.spinner("🤔 Thinking..."):
                    response = st.session_state.ai_assistant.process_query(
                        user_query, 
                        user_role=role,
                        context=tech_context
                    )
                    
                    st.session_state.main_chat_history.append({
                        'query': user_query,
                        'response': response,
                        'timestamp': datetime.now().strftime('%H:%M:%S')
                    })
                    st.rerun()
    
    with col2:
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.main_chat_history = []
            st.rerun()
    
    with col3:
        if st.button("❓ Show Help", use_container_width=True):
            help_msg = st.session_state.ai_assistant._get_help_message(role)
            st.session_state.main_chat_history.append({
                'query': 'Help - What can you do?',
                'response': help_msg,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
            st.rerun()
    
    # Display chat history
    st.markdown("---")
    st.markdown("### 📜 Conversation History")
    
    if st.session_state.main_chat_history:
        for i, chat in enumerate(reversed(st.session_state.main_chat_history)):
            with st.container():
                col1, col2 = st.columns([1, 12])
                with col1:
                    st.markdown(f"**{chat['timestamp']}**")
                with col2:
                    st.markdown(f"**You asked:**")
                    st.info(chat['query'])
                    st.markdown(f"**AI Assistant:**")
                    st.markdown(chat['response'])
                st.markdown("---")
    else:
        st.info("👋 No conversation yet! Ask me a question or try a quick action above.")
        
        # Show example queries
        st.markdown("### 💡 Example Questions:")
        
        if role == "technician":
            st.markdown("""
            - "Show my schedule"
            - "Tell me about dispatch #200000016"
            - "Route to dispatch #200000016"
            - "How many jobs do I have today?"
            """)
        else:
            st.markdown("""
            - "Show high priority dispatches"
            - "Who else can handle dispatch #200000016?"
            - "Show unassigned dispatches"
            - "Workload summary for all technicians"
            - "Show schedule for T900001"
            """)

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
    # OPTIMIZATION RESULTS OVERVIEW (HERO SECTION)
    # ============================================================
    st.header("📊 Optimization Results Overview")
    st.caption("*ML-driven optimization with weighted scoring: Success (50%), Workload (35%), Distance (10%), Overrun (5%)*")

    # Key Performance Indicators - Top Row
    col1, col2, col3, col4, col5 = st.columns(5)

    # Calculate key metrics
    total_dispatches = len(filtered_df)
    
    assigned_dispatches = int(to_scalar(filtered_df['Optimized_technician_id'].notna().sum()))
    unassigned_dispatches = int(total_dispatches - assigned_dispatches)
    assignment_rate = (assigned_dispatches / total_dispatches * 100) if total_dispatches > 0 else 0
    
    avg_success_prob = float(to_scalar(filtered_df['Predicted_success_prob'].mean() if 'Predicted_success_prob' in filtered_df.columns else 0))
    avg_opt_score = float(to_scalar(filtered_df['Optimization_score'].mean() if 'Optimization_score' in filtered_df.columns else 0))
    avg_distance = float(to_scalar(filtered_df['Optimized_distance_km'].mean() if 'Optimized_distance_km' in filtered_df.columns else 0))
    
    # Count warnings
    has_warnings = int(to_scalar(filtered_df['Has_warnings'].sum() if 'Has_warnings' in filtered_df.columns else 0))
    warning_rate = (has_warnings / total_dispatches * 100) if total_dispatches > 0 else 0

    with col1:
        st.metric(
            label="📋 Total Dispatches",
            value=f"{total_dispatches:,}",
            help="Total number of dispatches in current selection"
        )

    with col2:
        st.metric(
            label="✅ Successfully Assigned",
            value=f"{assigned_dispatches:,}",
            delta=f"{assignment_rate:.1f}% rate",
            delta_color="normal",
            help="Dispatches successfully matched with technicians"
        )

    with col3:
        st.metric(
            label="🎯 Avg Success Probability",
            value=f"{avg_success_prob:.1%}",
            delta="ML Predicted",
            delta_color="off",
            help="Average likelihood of first-time fix success"
        )

    with col4:
        st.metric(
            label="⭐ Avg Optimization Score",
            value=f"{avg_opt_score:.1f}",
            delta="out of 100",
            delta_color="off",
            help="Composite score based on success, workload, distance, and overrun"
        )

    with col5:
        st.metric(
            label="⚠️ Assignments with Warnings",
            value=f"{has_warnings}",
            delta=f"{warning_rate:.1f}%",
            delta_color="inverse" if warning_rate > 10 else "off",
            help="Assignments that require attention (overlaps, capacity issues, etc.)"
        )

    st.markdown("---")

    # Detailed Breakdown - Second Row
    st.subheader("📈 Assignment Quality Breakdown")
    
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("### 🎯 Success Distribution")
        high_success = int((filtered_df['Predicted_success_prob'] >= 0.7).sum() if 'Predicted_success_prob' in filtered_df.columns else 0)
        medium_success = int(((filtered_df['Predicted_success_prob'] >= 0.5) & (filtered_df['Predicted_success_prob'] < 0.7)).sum() if 'Predicted_success_prob' in filtered_df.columns else 0)
        low_success = int((filtered_df['Predicted_success_prob'] < 0.5).sum() if 'Predicted_success_prob' in filtered_df.columns else 0)
        
        st.markdown(f"""
        - 🟢 **High (≥70%)**: {high_success} ({(high_success/total_dispatches*100):.1f}%)
        - 🟡 **Medium (50-70%)**: {medium_success} ({(medium_success/total_dispatches*100):.1f}%)
        - 🔴 **Low (<50%)**: {low_success} ({(low_success/total_dispatches*100):.1f}%)
        """)

    with col2:
        st.markdown("### 🎖️ Skill Match Quality")
        perfect_match = int((filtered_df['Skill_match_score'] == 1).sum() if 'Skill_match_score' in filtered_df.columns else 0)
        partial_match = int((filtered_df['Skill_match_score'] == 0).sum() if 'Skill_match_score' in filtered_df.columns else 0)
        
        st.markdown(f"""
        - ✅ **Perfect Match**: {perfect_match} ({(perfect_match/assigned_dispatches*100 if assigned_dispatches > 0 else 0):.1f}%)
        - ⚡ **Cross-Trained**: {partial_match} ({(partial_match/assigned_dispatches*100 if assigned_dispatches > 0 else 0):.1f}%)
        - 📊 **Match Rate**: {(perfect_match/assigned_dispatches*100 if assigned_dispatches > 0 else 0):.1f}%
        """)

    with col3:
        st.markdown("### 🚗 Travel Efficiency")
        total_distance = float(filtered_df['Optimized_distance_km'].sum() if 'Optimized_distance_km' in filtered_df.columns else 0)
        avg_distance = float(filtered_df['Optimized_distance_km'].mean() if 'Optimized_distance_km' in filtered_df.columns else 0)
        
        st.markdown(f"""
        - 📍 **Total Distance**: {total_distance:.0f} km
        - 📏 **Avg per Job**: {avg_distance:.1f} km
        - 💰 **Est. Fuel Cost**: ${(total_distance * 0.50):.0f}
        """)

    with col4:
        st.markdown("### ⚖️ Workload Balance")
        avg_workload = float(filtered_df['Optimized_workload_ratio'].mean() if 'Optimized_workload_ratio' in filtered_df.columns else 0)
        over_capacity = int((filtered_df['Optimized_workload_ratio'] > 1.0).sum() if 'Optimized_workload_ratio' in filtered_df.columns else 0)
        high_load = int(((filtered_df['Optimized_workload_ratio'] > 0.8) & (filtered_df['Optimized_workload_ratio'] <= 1.0)).sum() if 'Optimized_workload_ratio' in filtered_df.columns else 0)
        
        st.markdown(f"""
        - 📊 **Avg Workload**: {avg_workload:.1%}
        - 🔴 **Over Capacity**: {over_capacity}
        - 🟡 **High Load (>80%)**: {high_load}
        """)

    st.markdown("---")

    # Visual Comparison - Third Row
    st.subheader("📊 Visual Performance Comparison")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Success probability gauge
        avg_success_display = avg_success_prob * 100
        
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=avg_success_display,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "Success Probability", 'font': {'size': 16}},
            number={'suffix': '%', 'font': {'size': 40}},
            gauge={
                'axis': {'range': [None, 100], 'ticksuffix': '%'},
                'bar': {'color': "#3498db"},
                'steps': [
                    {'range': [0, 50], 'color': "#ffe0b2"},
                    {'range': [50, 70], 'color': "#fff9c4"},
                    {'range': [70, 100], 'color': "#d5f4e6"}
                ],
                'threshold': {
                    'line': {'color': "#2ecc71", 'width': 4},
                    'thickness': 0.75,
                    'value': 70
                }
            }
        ))
        
        fig_gauge.update_layout(
            height=300,
            margin=dict(t=40, b=0, l=20, r=20)
        )
        
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col2:
        # Optimization score distribution
        if 'Optimization_score' in filtered_df.columns:
            fig_score = px.histogram(
                filtered_df,
                x='Optimization_score',
                nbins=25,
                title='Optimization Score Distribution',
                labels={'Optimization_score': 'Score', 'count': 'Count'},
                color_discrete_sequence=['#3498db']
            )
            
            fig_score.add_vline(
                x=filtered_df['Optimization_score'].mean(),
                line_dash="dash",
                line_color="red",
                annotation_text=f"Avg: {filtered_df['Optimization_score'].mean():.1f}"
            )
            
            fig_score.update_layout(
                height=300,
                showlegend=False,
                margin=dict(t=40, b=40, l=40, r=20)
            )
            
            st.plotly_chart(fig_score, use_container_width=True)
        else:
            st.info("Optimization score data not available")

    with col3:
        # Assignment vs unassigned pie
        fig_pie = go.Figure(data=[go.Pie(
            labels=['✅ Assigned', '❌ Unassigned'],
            values=[assigned_dispatches, unassigned_dispatches],
            hole=.4,
            marker_colors=['#2ecc71', '#e74c3c']
        )])
        
        fig_pie.update_layout(
            title='Assignment Status',
            height=300,
            showlegend=True,
            margin=dict(t=40, b=0, l=0, r=0)
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)

    # Second row of charts
    col1, col2 = st.columns(2)

    with col1:
        # Success probability by priority
        if 'Priority' in filtered_df.columns and 'Predicted_success_prob' in filtered_df.columns:
            priority_success = filtered_df.groupby('Priority')['Predicted_success_prob'].agg(['mean', 'count']).reset_index()
            
            fig_priority = px.bar(
                priority_success,
                x='Priority',
                y='mean',
                title='Success Probability by Priority Level',
                labels={'mean': 'Avg Success Prob', 'Priority': 'Priority'},
                text='count',
                color='mean',
                color_continuous_scale='RdYlGn',
                range_color=[0, 1]
            )
            
            fig_priority.update_traces(texttemplate='n=%{text}', textposition='outside')
            fig_priority.update_layout(height=350, showlegend=False)
            
            st.plotly_chart(fig_priority, use_container_width=True)
        else:
            st.info("Priority data not available")

    with col2:
        # Distance vs success scatter
        if 'Optimized_distance_km' in filtered_df.columns and 'Predicted_success_prob' in filtered_df.columns:
            fig_scatter = px.scatter(
                filtered_df.head(200),  # Limit to 200 points for performance
                x='Optimized_distance_km',
                y='Predicted_success_prob',
                title='Success Probability vs Distance (first 200)',
                labels={'Optimized_distance_km': 'Distance (km)', 'Predicted_success_prob': 'Success Prob'},
                color='Predicted_success_prob',
                color_continuous_scale='RdYlGn',
                opacity=0.6
            )
            
            fig_scatter.update_layout(height=350)
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info("Distance/Success data not available")

    st.markdown("---")

    # Key Insights & Recommendations
    st.subheader("💡 Key Insights & Recommendations")
    
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### ✅ Strengths")
        insights = []
        if assignment_rate > 90:
            insights.append("🌟 Excellent assignment rate (>90%)")
        if avg_success_prob > 0.7:
            insights.append("🎯 High success probability average")
        if warning_rate < 5:
            insights.append("✅ Very few warnings (<5%)")
        if 'Skill_match_score' in filtered_df.columns:
            perfect_match_rate = int((filtered_df['Skill_match_score'] == 1).sum()) / assigned_dispatches * 100 if assigned_dispatches > 0 else 0
            if perfect_match_rate > 80:
                insights.append("🎖️ Strong skill matching (>80%)")
        
        if insights:
            for insight in insights:
                st.markdown(f"- {insight}")
        else:
            st.markdown("- 📊 System operating normally")

    with col2:
        st.markdown("#### ⚠️ Areas of Concern")
        concerns = []
        if unassigned_dispatches > total_dispatches * 0.1:
            concerns.append(f"🔴 {unassigned_dispatches} dispatches unassigned")
        if warning_rate > 10:
            concerns.append(f"⚠️ High warning rate ({warning_rate:.1f}%)")
        if low_success > total_dispatches * 0.15:
            concerns.append(f"📉 {low_success} low-confidence assignments")
        if over_capacity > 0:
            concerns.append(f"🔴 {over_capacity} technicians over capacity")
        
        if concerns:
            for concern in concerns:
                st.markdown(f"- {concern}")
        else:
            st.markdown("- ✅ No major concerns identified")

    with col3:
        st.markdown("#### 🎯 Recommendations")
        recommendations = []
        if unassigned_dispatches > 0:
            recommendations.append(f"📞 Address {unassigned_dispatches} unassigned jobs")
        if low_success > 5:
            recommendations.append(f"📚 {low_success} jobs may need specialist training")
        if avg_distance > 30:
            recommendations.append("🗺️ Review territory assignments")
        if over_capacity > 0:
            recommendations.append("⚖️ Rebalance workload distribution")
        
        if recommendations:
            for rec in recommendations[:3]:  # Show top 3
                st.markdown(f"- {rec}")
        else:
            st.markdown("- ✅ System is well-optimized")

    st.markdown("---")

    # ============================================================
    # KEY METRICS OVERVIEW
    # ============================================================
    st.header("📊 Detailed Metrics")

    col1, col2, col3, col4, col5 = st.columns(5)

    # Calculate metrics
    assigned_count = int(filtered_df['Optimized_technician_id'].notna().sum())
    unassigned_count = int(filtered_df['Optimized_technician_id'].isna().sum())
    assignment_rate = (assigned_count / len(filtered_df)) * 100

    avg_initial_success = float(filtered_df['Initial_success_prob'].mean())
    avg_optimized_success = float(filtered_df['Predicted_success_prob'].mean())
    success_improvement = avg_optimized_success - avg_initial_success

    avg_initial_distance = float(filtered_df['Initial_distance_km'].mean())
    avg_optimized_distance = float(filtered_df['Optimized_distance_km'].mean())
    distance_reduction = avg_initial_distance - avg_optimized_distance

    total_distance_saved = float(filtered_df['Distance_change_km'].sum())
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
        improvement_rate = int((filtered_df['Success_prob_improvement'] > 0).sum())
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
        
        improved = int((filtered_df['Success_prob_improvement'] > 0).sum())
        worse = int((filtered_df['Success_prob_improvement'] < 0).sum())
        unchanged = int((filtered_df['Success_prob_improvement'] == 0).sum())
        
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
            total_initial = float(filtered_df['Initial_distance_km'].sum())
            total_optimized = float(filtered_df['Optimized_distance_km'].sum())
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
            
            initial_over_80 = int((filtered_df['Initial_workload_ratio'] > 0.8).sum())
            optimized_over_80 = int((filtered_df['Optimized_workload_ratio'] > 0.8).sum())
            
            initial_over_100 = int((filtered_df['Initial_workload_ratio'] > 1.0).sum())
            optimized_over_100 = int((filtered_df['Optimized_workload_ratio'] > 1.0).sum())
            
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
                <p>Dispatch-IQ: Smart Dispatch Dashboard v1.0</p>
                <p>Powered by ML-Based Assignment System | Built with Streamlit</p>
            </div>
            """,
            unsafe_allow_html=True
        )

