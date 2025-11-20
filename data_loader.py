"""
Data Loader with PostgreSQL to CSV Fallback
Attempts PostgreSQL connection first, falls back to CSV files if connection fails
"""

import pandas as pd
import psycopg2
import os
from typing import Tuple, Optional
import warnings


class DataLoader:
    """Handles data loading from PostgreSQL with CSV fallback"""
    
    def __init__(self):
        self.connection = None
        self.using_fallback = False
        self.schema = os.getenv('DB_SCHEMA', 'team_faiber_force')
        
    def connect(self) -> bool:
        """
        Attempt to connect to PostgreSQL database
        Returns True if successful, False if fallback needed
        """
        try:
            # Get database credentials from environment variables
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = os.getenv('DB_PORT', '5432')
            db_name = os.getenv('DB_NAME', 'dispatch_db')
            db_user = os.getenv('DB_USER', 'postgres')
            db_password = os.getenv('DB_PASSWORD', '')
            
            # Attempt connection
            self.connection = psycopg2.connect(
                host=db_host,
                port=db_port,
                dbname=db_name,
                user=db_user,
                password=db_password
            )
            
            print("  ✓ Connected to PostgreSQL database")
            return True
            
        except (psycopg2.OperationalError, psycopg2.Error) as e:
            print(f"  ⚠️  PostgreSQL connection failed: {str(e)}")
            print("  → Falling back to CSV files...")
            self.using_fallback = True
            return False
        except Exception as e:
            print(f"  ⚠️  Unexpected error: {str(e)}")
            print("  → Falling back to CSV files...")
            self.using_fallback = True
            return False
    
    def disconnect(self):
        """Close database connection if open"""
        if self.connection:
            try:
                self.connection.close()
                print("  ✓ Database connection closed")
            except:
                pass
    
    def load_dispatches(self, date_filter: str = '2025-11-12') -> pd.DataFrame:
        """
        Load dispatch data from PostgreSQL or CSV fallback
        
        Args:
            date_filter: Only load dispatches from this date onwards
            
        Returns:
            DataFrame with dispatch data
        """
        if not self.using_fallback and self.connection:
            try:
                query = f"""
                SELECT 
                    cd."Dispatch_id" as dispatch_id,
                    cd."Ticket_type" as ticket_type,
                    cd."Order_type" as order_type,
                    cd."Priority" as priority,
                    cd."Required_skill" as required_skill,
                    cd."Assigned_technician_id" as assigned_technician_id,
                    cd."Customer_latitude" as customer_latitude,
                    cd."Customer_longitude" as customer_longitude,
                    cd."Duration_min" as expected_duration,
                    cd."Appointment_start_datetime" as appointment_start_datetime,
                    cd."Appointment_end_datetime" as appointment_end_datetime,
                    cd."State" as state,
                    cd."City" as city
                FROM {self.schema}.current_dispatches_csv cd
                WHERE cd."Customer_latitude" IS NOT NULL 
                    AND cd."Customer_longitude" IS NOT NULL
                    AND cd."State" IS NOT NULL
                    AND DATE(cd."Appointment_start_datetime") >= '{date_filter}';
                """
                
                dispatches = pd.read_sql_query(query, self.connection)
                dispatches['appointment_start_datetime'] = pd.to_datetime(dispatches['appointment_start_datetime'])
                dispatches['appointment_end_datetime'] = pd.to_datetime(dispatches['appointment_end_datetime'])
                
                print(f"  ✓ Loaded {len(dispatches)} dispatches from PostgreSQL")
                return dispatches
                
            except Exception as e:
                print(f"  ⚠️  PostgreSQL query failed: {str(e)}")
                print("  → Falling back to CSV...")
                self.using_fallback = True
        
        # CSV Fallback
        try:
            if not os.path.exists('current_dispatches.csv'):
                raise FileNotFoundError("current_dispatches.csv not found")
            
            dispatches = pd.read_csv('current_dispatches.csv')
            
            # Standardize column names (handle different cases)
            column_mapping = {
                'Dispatch_id': 'dispatch_id',
                'Ticket_type': 'ticket_type',
                'Order_type': 'order_type',
                'Priority': 'priority',
                'Required_skill': 'required_skill',
                'Assigned_technician_id': 'assigned_technician_id',
                'Customer_latitude': 'customer_latitude',
                'Customer_longitude': 'customer_longitude',
                'Duration_min': 'expected_duration',
                'Appointment_start_datetime': 'appointment_start_datetime',
                'Appointment_end_datetime': 'appointment_end_datetime',
                'State': 'state',
                'City': 'city'
            }
            
            # Rename columns that exist
            dispatches = dispatches.rename(columns={k: v for k, v in column_mapping.items() if k in dispatches.columns})
            
            # Parse datetime columns
            dispatches['appointment_start_datetime'] = pd.to_datetime(dispatches['appointment_start_datetime'], errors='coerce')
            dispatches['appointment_end_datetime'] = pd.to_datetime(dispatches['appointment_end_datetime'], errors='coerce')
            
            # Apply date filter
            dispatches = dispatches[
                (dispatches['customer_latitude'].notna()) &
                (dispatches['customer_longitude'].notna()) &
                (dispatches['state'].notna()) &
                (dispatches['appointment_start_datetime'] >= pd.to_datetime(date_filter))
            ]
            
            print(f"  ✓ Loaded {len(dispatches)} dispatches from CSV (filtered >= {date_filter})")
            return dispatches
            
        except Exception as e:
            print(f"  ✗ Failed to load dispatches from CSV: {str(e)}")
            raise
    
    def load_technicians(self) -> pd.DataFrame:
        """Load technician data from PostgreSQL or CSV fallback"""
        if not self.using_fallback and self.connection:
            try:
                query = f"""
                SELECT 
                    "Technician_id" as technician_id,
                    "Name" as technician_name,
                    "Primary_skill" as technician_skill,
                    "Latitude" as technician_latitude,
                    "Longitude" as technician_longitude,
                    "Workload_capacity" as workload_capacity,
                    "State" as state,
                    "City" as city
                FROM {self.schema}.technicians_10k;
                """
                
                technicians = pd.read_sql_query(query, self.connection)
                print(f"  ✓ Loaded {len(technicians)} technicians from PostgreSQL")
                return technicians
                
            except Exception as e:
                print(f"  ⚠️  PostgreSQL query failed: {str(e)}")
                print("  → Falling back to CSV...")
                self.using_fallback = True
        
        # CSV Fallback
        try:
            if not os.path.exists('technicians.csv'):
                raise FileNotFoundError("technicians.csv not found")
            
            technicians = pd.read_csv('technicians.csv')
            
            # Standardize column names
            column_mapping = {
                'Technician_id': 'technician_id',
                'Name': 'technician_name',
                'Primary_skill': 'technician_skill',
                'Latitude': 'technician_latitude',
                'Longitude': 'technician_longitude',
                'Workload_capacity': 'workload_capacity',
                'State': 'state',
                'City': 'city'
            }
            
            technicians = technicians.rename(columns={k: v for k, v in column_mapping.items() if k in technicians.columns})
            
            print(f"  ✓ Loaded {len(technicians)} technicians from CSV")
            return technicians
            
        except Exception as e:
            print(f"  ✗ Failed to load technicians from CSV: {str(e)}")
            raise
    
    def load_calendar(self) -> pd.DataFrame:
        """Load technician calendar from PostgreSQL or CSV fallback"""
        if not self.using_fallback and self.connection:
            try:
                query = f"""
                SELECT 
                    "Technician_id" as technician_id,
                    "Date" as date,
                    "Available" as available,
                    "Start_time" as start_time,
                    "End_time" as end_time,
                    "Max_assignments" as max_assignments
                FROM {self.schema}.technician_calendar_10k
                WHERE "Available" = 1;
                """
                
                calendar = pd.read_sql_query(query, self.connection)
                calendar['date'] = pd.to_datetime(calendar['date']).dt.date
                
                # Save to CSV for future fallback use (always update to keep it fresh)
                calendar.to_csv('technician_calendar_10k.csv', index=False)
                print(f"  ✓ Loaded {len(calendar)} calendar entries from PostgreSQL")
                print(f"  ✓ Updated technician_calendar_10k.csv for future fallback use")
                
                return calendar
                
            except Exception as e:
                print(f"  ⚠️  PostgreSQL query failed: {str(e)}")
                print("  → Falling back to CSV...")
                self.using_fallback = True
        
        # CSV Fallback
        try:
            if not os.path.exists('technician_calendar_10k.csv'):
                raise FileNotFoundError(
                    "technician_calendar_10k.csv not found! Please run 'python export_calendar.py' "
                    "to export calendar data from PostgreSQL first."
                )
            
            calendar = pd.read_csv('technician_calendar_10k.csv')
            
            # Standardize column names
            column_mapping = {
                'Technician_id': 'technician_id',
                'Date': 'date',
                'Available': 'available',
                'Start_time': 'start_time',
                'End_time': 'end_time',
                'Max_assignments': 'max_assignments'
            }
            
            calendar = calendar.rename(columns={k: v for k, v in column_mapping.items() if k in calendar.columns})
            calendar['date'] = pd.to_datetime(calendar['date']).dt.date
            
            # Filter for available only
            if 'available' in calendar.columns:
                calendar = calendar[calendar['available'] == 1]
            
            print(f"  ✓ Loaded {len(calendar)} calendar entries from CSV")
            return calendar
            
        except FileNotFoundError as e:
            print(f"  ✗ {str(e)}")
            raise
        except Exception as e:
            print(f"  ✗ Failed to load calendar from CSV: {str(e)}")
            raise
    
    def export_calendar_from_db(self, force: bool = False):
        """
        Export calendar from PostgreSQL to CSV (same name as DB table)
        
        Args:
            force: Force re-export even if technician_calendar_10k.csv exists
        """
        if os.path.exists('technician_calendar_10k.csv') and not force:
            print("  ℹ️  technician_calendar_10k.csv already exists. Use force=True to overwrite.")
            return
        
        if not self.connection:
            if not self.connect():
                print("  ✗ Cannot export calendar: Database connection failed")
                return
        
        try:
            query = f"""
            SELECT 
                "Technician_id" as technician_id,
                "Date" as date,
                "Available" as available,
                "Start_time" as start_time,
                "End_time" as end_time,
                "Max_assignments" as max_assignments
            FROM {self.schema}.technician_calendar_10k;
            """
            
            calendar = pd.read_sql_query(query, self.connection)
            calendar.to_csv('technician_calendar_10k.csv', index=False)
            
            print(f"  ✓ Exported {len(calendar)} calendar entries to technician_calendar_10k.csv")
            
        except Exception as e:
            print(f"  ✗ Failed to export calendar: {str(e)}")


if __name__ == "__main__":
    # Test the data loader
    print("Testing DataLoader with fallback...")
    loader = DataLoader()
    loader.connect()
    
    try:
        dispatches = loader.load_dispatches()
        print(f"\nDispatches loaded: {len(dispatches)}")
        
        technicians = loader.load_technicians()
        print(f"Technicians loaded: {len(technicians)}")
        
        calendar = loader.load_calendar()
        print(f"Calendar entries loaded: {len(calendar)}")
        
    finally:
        loader.disconnect()

