"""
Export Technician Calendar from PostgreSQL to CSV
Run this script to create technician_calendar_10k.csv from database
"""

from data_loader import DataLoader


def main():
    print("="*70)
    print("EXPORT TECHNICIAN CALENDAR FROM POSTGRESQL")
    print("="*70)
    print("\nThis will export technician_calendar_10k table to CSV")
    print("Output file: technician_calendar_10k.csv\n")
    
    # Create data loader
    loader = DataLoader()
    
    # Connect to database
    print("Connecting to PostgreSQL...")
    if not loader.connect():
        print("\n✗ Failed to connect to PostgreSQL database")
        print("\nPlease check:")
        print("  1. Database credentials are set in environment variables")
        print("  2. Database server is accessible")
        print("  3. Network connection is working")
        print("\nEnvironment variables needed:")
        print("  - DB_HOST")
        print("  - DB_PORT")
        print("  - DB_NAME")
        print("  - DB_USER")
        print("  - DB_PASSWORD")
        print("  - DB_SCHEMA")
        return
    
    try:
        # Export calendar
        print("\nExporting calendar data...")
        loader.export_calendar_from_db(force=True)
        
        print("\n" + "="*70)
        print("✓ SUCCESS!")
        print("="*70)
        print("\ntechnician_calendar_10k.csv has been created")
        print("This file will be used as fallback when PostgreSQL is unavailable")
        print("\nYou can now:")
        print("  1. Add technician_calendar_10k.csv to Git repository")
        print("  2. Run optimize_dispatches.py with CSV fallback support")
        
    except Exception as e:
        print(f"\n✗ Export failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        loader.disconnect()
        print("\n" + "="*70)


if __name__ == "__main__":
    main()

