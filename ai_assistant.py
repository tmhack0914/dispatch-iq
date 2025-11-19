"""
AI Assistant for F-Ai-ber Force Smart Dispatch Dashboard
Provides intelligent assistance for dispatch managers and technicians
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import json


class DispatchAIAssistant:
    """AI Assistant for dispatch optimization queries"""
    
    def __init__(self, dispatches_df: pd.DataFrame, technicians_df: Optional[pd.DataFrame] = None):
        """
        Initialize the AI Assistant
        
        Args:
            dispatches_df: DataFrame with dispatch and optimization data
            technicians_df: Optional DataFrame with technician details
        """
        self.dispatches = dispatches_df
        self.technicians = technicians_df
        
    def get_dispatch_overview(self, dispatch_id: str) -> str:
        """Get a quick overview of a specific dispatch"""
        try:
            dispatch = self.dispatches[self.dispatches['Dispatch_id'] == int(dispatch_id)].iloc[0]
            
            overview = f"""
**📋 Dispatch Overview: #{dispatch_id}**

**Location & Timing:**
- 📍 Location: {dispatch.get('City', 'N/A')}, {dispatch.get('Street', 'N/A')}
- 📅 Appointment: {dispatch.get('Appointment_start_datetime', 'N/A')}
- ⏱️ Estimated Duration: {dispatch.get('Optimized_predicted_duration_min', 0):.0f} minutes

**Job Details:**
- 🔧 Required Skill: {dispatch.get('Required_skill', 'N/A')}
- ⚡ Priority: {dispatch.get('Priority', 'N/A')}
- 🎫 Type: {dispatch.get('Ticket_type', 'N/A')}
- 📦 Equipment: {dispatch.get('Equipment_installed', 'None')}
- 🎖️ Service Tier: {dispatch.get('Service_tier', 'Standard')}

**Assignment:**
- 👤 Assigned Technician: {dispatch.get('Optimized_technician_id', 'Unassigned')}
- 🚗 Distance: {dispatch.get('Optimized_distance_km', 0):.1f} km
- 🎯 Success Probability: {dispatch.get('Predicted_success_prob', 0):.1%}
- ⭐ Optimization Score: {dispatch.get('Optimization_score', 0):.1f}/100

**Performance Indicators:**
- ✅ Confidence: {dispatch.get('Optimization_confidence', 0):.1%}
- ⚖️ Tech Workload: {dispatch.get('Optimized_workload_ratio', 0):.0%}
- ⚠️ Warnings: {'Yes' if dispatch.get('Has_warnings', False) else 'None'}
"""
            return overview.strip()
            
        except Exception as e:
            return f"❌ Could not find dispatch #{dispatch_id}. Error: {str(e)}"
    
    def get_alternative_assignments(self, dispatch_id: str, top_n: int = 5) -> str:
        """Get alternative technician assignments for a dispatch"""
        try:
            # This would require the full optimization data
            # For now, we'll provide a framework
            dispatch = self.dispatches[self.dispatches['Dispatch_id'] == int(dispatch_id)].iloc[0]
            
            response = f"""
**🔄 Alternative Assignments for Dispatch #{dispatch_id}**

**Current Assignment:**
- 👤 Technician: {dispatch.get('Optimized_technician_id', 'None')}
- 🎯 Success Prob: {dispatch.get('Predicted_success_prob', 0):.1%}
- 🚗 Distance: {dispatch.get('Optimized_distance_km', 0):.1f} km
- ⭐ Score: {dispatch.get('Optimization_score', 0):.1f}

**To see alternative technicians:**
This feature requires running the optimization with alternative suggestions enabled.

**Quick Tips:**
- Current assignment is optimized for best overall outcome
- Consider alternatives if:
  - Current tech is unavailable
  - Skill mismatch concerns
  - Distance is prohibitive
  - Workload rebalancing needed
"""
            return response.strip()
            
        except Exception as e:
            return f"❌ Could not analyze alternatives for dispatch #{dispatch_id}. Error: {str(e)}"
    
    def get_route_info(self, dispatch_id: str, technician_id: Optional[str] = None) -> str:
        """Get route information for a dispatch"""
        try:
            dispatch = self.dispatches[self.dispatches['Dispatch_id'] == int(dispatch_id)].iloc[0]
            
            tech_id = technician_id or dispatch.get('Optimized_technician_id', 'Unknown')
            lat = dispatch.get('Customer_latitude', 0)
            lon = dispatch.get('Customer_longitude', 0)
            distance = dispatch.get('Optimized_distance_km', 0)
            
            response = f"""
**🗺️ Route Information**

**Dispatch:** #{dispatch_id}
**Destination:** {dispatch.get('City', 'N/A')}, {dispatch.get('Street', 'N/A')}
**Coordinates:** {lat:.4f}, {lon:.4f}

**Route Details:**
- 🚗 Distance: {distance:.1f} km
- ⏱️ Estimated Travel Time: {(distance * 2):.0f} minutes (avg speed 30 km/h)
- 🎯 Assigned to: {tech_id}

**Fastest Route Recommendation:**
1. Use GPS navigation with coordinates: {lat:.4f}, {lon:.4f}
2. Check real-time traffic conditions
3. Estimated arrival: ~{(distance * 2):.0f} minutes from base

**Google Maps Link:**
https://www.google.com/maps/dir/?api=1&destination={lat},{lon}

**Pro Tips:**
- 📞 Call customer if running late
- 🧰 Verify equipment before departure
- ⏰ Budget extra time for complex jobs
"""
            return response.strip()
            
        except Exception as e:
            return f"❌ Could not get route info for dispatch #{dispatch_id}. Error: {str(e)}"
    
    def get_technician_schedule(self, technician_id: str) -> str:
        """Get today's schedule for a technician"""
        try:
            tech_dispatches = self.dispatches[
                self.dispatches['Optimized_technician_id'] == technician_id
            ].sort_values('Appointment_start_datetime')
            
            if len(tech_dispatches) == 0:
                return f"📭 No assignments found for technician {technician_id} today."
            
            response = f"""
**📅 Schedule for Technician {technician_id}**

**Summary:**
- Total Jobs: {len(tech_dispatches)}
- Total Distance: {tech_dispatches['Optimized_distance_km'].sum():.1f} km
- Total Time: {tech_dispatches['Optimized_predicted_duration_min'].sum():.0f} minutes ({tech_dispatches['Optimized_predicted_duration_min'].sum()/60:.1f} hours)
- Avg Success Prob: {tech_dispatches['Predicted_success_prob'].mean():.1%}

**Assignments:**
"""
            for idx, dispatch in tech_dispatches.iterrows():
                response += f"""
{idx + 1}. **Dispatch #{dispatch['Dispatch_id']}** - {dispatch.get('Appointment_start_datetime', 'TBD')}
   - 📍 {dispatch.get('City', 'N/A')} ({dispatch.get('Optimized_distance_km', 0):.1f} km)
   - 🔧 {dispatch.get('Required_skill', 'N/A')}
   - ⏱️ {dispatch.get('Optimized_predicted_duration_min', 0):.0f} min
   - 🎯 {dispatch.get('Predicted_success_prob', 0):.0%} success
"""
            
            return response.strip()
            
        except Exception as e:
            return f"❌ Could not get schedule for technician {technician_id}. Error: {str(e)}"
    
    def get_high_priority_dispatches(self) -> str:
        """Get list of high priority dispatches"""
        try:
            high_priority = self.dispatches[
                self.dispatches['Priority'].isin(['Critical', 'High'])
            ].sort_values('Predicted_success_prob')
            
            response = f"""
**🚨 High Priority Dispatches**

**Total:** {len(high_priority)} critical/high priority jobs

**Attention Required:**
"""
            
            for idx, dispatch in high_priority.head(10).iterrows():
                status = "✅ Assigned" if pd.notna(dispatch.get('Optimized_technician_id')) else "⚠️ UNASSIGNED"
                response += f"""
- **#{dispatch['Dispatch_id']}** [{dispatch.get('Priority')}] - {status}
  🎯 Success: {dispatch.get('Predicted_success_prob', 0):.0%} | 
  👤 {dispatch.get('Optimized_technician_id', 'None')} | 
  📍 {dispatch.get('City', 'N/A')}
"""
            
            return response.strip()
            
        except Exception as e:
            return f"❌ Could not retrieve high priority dispatches. Error: {str(e)}"
    
    def get_unassigned_dispatches(self) -> str:
        """Get list of unassigned dispatches"""
        try:
            unassigned = self.dispatches[
                self.dispatches['Optimized_technician_id'].isna()
            ].sort_values('Priority')
            
            if len(unassigned) == 0:
                return "✅ Great news! All dispatches have been assigned."
            
            response = f"""
**⚠️ Unassigned Dispatches**

**Total Unassigned:** {len(unassigned)}

**Action Required:**
"""
            
            for idx, dispatch in unassigned.head(10).iterrows():
                response += f"""
- **#{dispatch['Dispatch_id']}** [{dispatch.get('Priority')}]
  📍 {dispatch.get('City', 'N/A')} | 
  🔧 {dispatch.get('Required_skill', 'N/A')} | 
  📅 {dispatch.get('Appointment_start_datetime', 'TBD')}
"""
            
            response += f"""

**Recommendations:**
- Review technician availability
- Check skill requirements
- Consider overtime or contractors
- Prioritize by appointment time
"""
            
            return response.strip()
            
        except Exception as e:
            return f"❌ Could not retrieve unassigned dispatches. Error: {str(e)}"
    
    def get_workload_summary(self) -> str:
        """Get technician workload summary"""
        try:
            workload = self.dispatches.groupby('Optimized_technician_id').agg({
                'Dispatch_id': 'count',
                'Optimized_distance_km': 'sum',
                'Optimized_predicted_duration_min': 'sum',
                'Predicted_success_prob': 'mean',
                'Optimized_workload_ratio': 'mean'
            }).reset_index()
            
            workload.columns = ['Technician', 'Jobs', 'Distance', 'Duration', 'Avg_Success', 'Workload']
            workload = workload.sort_values('Workload', ascending=False)
            
            response = f"""
**⚖️ Technician Workload Summary**

**Top Loaded Technicians:**
"""
            
            for idx, tech in workload.head(10).iterrows():
                status = "🔴" if tech['Workload'] > 1.0 else "🟡" if tech['Workload'] > 0.8 else "🟢"
                response += f"""
{status} **{tech['Technician']}**
   - Jobs: {tech['Jobs']:.0f} | Workload: {tech['Workload']:.0%}
   - Distance: {tech['Distance']:.1f} km | Time: {(tech['Duration']/60):.1f} hrs
   - Avg Success: {tech['Avg_Success']:.0%}
"""
            
            # Summary stats
            over_capacity = (workload['Workload'] > 1.0).sum()
            high_load = ((workload['Workload'] > 0.8) & (workload['Workload'] <= 1.0)).sum()
            
            response += f"""

**Overall Status:**
- 🔴 Over Capacity: {over_capacity} technicians
- 🟡 High Load (>80%): {high_load} technicians
- 🟢 Normal: {len(workload) - over_capacity - high_load} technicians
"""
            
            return response.strip()
            
        except Exception as e:
            return f"❌ Could not generate workload summary. Error: {str(e)}"
    
    def process_query(self, query: str, user_role: str = "manager", context: Optional[Dict] = None) -> str:
        """
        Process a natural language query from user
        
        Args:
            query: User's question
            user_role: 'manager' or 'technician'
            context: Optional context (e.g., current technician ID, dispatch ID)
        
        Returns:
            Response string
        """
        query_lower = query.lower()
        
        # Extract dispatch ID if mentioned
        import re
        dispatch_match = re.search(r'#?(\d{9})', query)
        dispatch_id = dispatch_match.group(1) if dispatch_match else context.get('dispatch_id') if context else None
        
        tech_match = re.search(r'(T\d{6})', query, re.IGNORECASE)
        tech_id = tech_match.group(1) if tech_match else context.get('technician_id') if context else None
        
        # Route-related queries
        if any(word in query_lower for word in ['route', 'directions', 'how to get', 'navigate', 'drive']):
            if dispatch_id:
                return self.get_route_info(dispatch_id, tech_id)
            return "❓ Please specify a dispatch ID (e.g., #200000016) to get route information."
        
        # Dispatch overview queries
        if any(word in query_lower for word in ['overview', 'details', 'information about', 'tell me about']):
            if dispatch_id:
                return self.get_dispatch_overview(dispatch_id)
            return "❓ Please specify a dispatch ID (e.g., #200000016) to get details."
        
        # Alternative assignment queries
        if any(word in query_lower for word in ['alternative', 'second best', 'other technician', 'backup']):
            if dispatch_id:
                return self.get_alternative_assignments(dispatch_id)
            return "❓ Please specify a dispatch ID to find alternative assignments."
        
        # Schedule queries
        if any(word in query_lower for word in ['schedule', 'my assignments', 'my jobs', 'today']):
            if tech_id or (context and context.get('technician_id')):
                return self.get_technician_schedule(tech_id or context.get('technician_id'))
            return "❓ Please specify a technician ID (e.g., T900001) to see schedule."
        
        # High priority queries
        if any(word in query_lower for word in ['critical', 'urgent', 'high priority', 'important']):
            return self.get_high_priority_dispatches()
        
        # Unassigned queries
        if any(word in query_lower for word in ['unassigned', 'not assigned', 'need assignment']):
            return self.get_unassigned_dispatches()
        
        # Workload queries
        if any(word in query_lower for word in ['workload', 'capacity', 'busy', 'overload']):
            return self.get_workload_summary()
        
        # Default help message
        return self._get_help_message(user_role)
    
    def _get_help_message(self, user_role: str) -> str:
        """Get help message based on user role"""
        if user_role == "technician":
            return """
**👷 Technician Assistant - What I Can Help With:**

**My Schedule:**
- "Show my schedule"
- "What are my assignments today?"
- "How many jobs do I have?"

**Dispatch Details:**
- "Tell me about dispatch #200000016"
- "Overview of dispatch #200000016"
- "Details on my next job"

**Route Help:**
- "Fastest route to dispatch #200000016"
- "How do I get to dispatch #200000016?"
- "Directions to customer"

**Examples:**
- "Show me dispatch #200000016 details"
- "Route to #200000016"
- "What's my schedule?"
"""
        else:  # manager
            return """
**👔 Manager Assistant - What I Can Help With:**

**Dispatch Management:**
- "Show unassigned dispatches"
- "High priority jobs"
- "Details on dispatch #200000016"

**Alternative Assignments:**
- "Who else can handle dispatch #200000016?"
- "Second best technician for #200000016"
- "Alternative assignments"

**Workload Analysis:**
- "Show technician workload"
- "Who is over capacity?"
- "Workload summary"

**Technician Schedules:**
- "Show schedule for T900001"
- "What jobs does T900001 have?"

**Examples:**
- "Show me high priority dispatches"
- "Alternative assignments for #200000016"
- "Technician workload summary"
"""

