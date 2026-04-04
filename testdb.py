#!/usr/bin/env python3
"""Quick database viewer"""
import sqlite3
from pathlib import Path

db_path = Path("race_results_cache.db")

if not db_path.exists():
    print("❌ Database file not found!")
    exit(1)

print("✓ Database found!\n")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Show all races
print("=" * 80)
print("RACES IN DATABASE")
print("=" * 80)

cursor.execute("""
    SELECT race_id, race_name, race_datetime, race_mode, total_laps, synced_to_remote
    FROM races
    ORDER BY race_datetime DESC
""")

races = cursor.fetchall()

if not races:
    print("No races found in database.")
else:
    for race in races:
        sync_status = "✓ Synced" if race[5] else "⏳ Not synced"
        print(f"\nRace ID: {race[0]}")
        print(f"  Name: {race[1]}")
        print(f"  Date/Time: {race[2]}")
        print(f"  Mode: {race[3]}")
        print(f"  Laps: {race[4]}")
        print(f"  Status: {sync_status}")
        
        # Count results for this race
        cursor.execute("SELECT COUNT(*) FROM race_results WHERE race_id = ?", (race[0],))
        result_count = cursor.fetchone()[0]
        print(f"  Lap Records: {result_count}")

# Show detailed results for the most recent race
if races:
    print("\n" + "=" * 80)
    print("DETAILED RESULTS - MOST RECENT RACE")
    print("=" * 80)
    
    most_recent_race_id = races[0][0]
    
    cursor.execute("""
        SELECT racer_name, lap_number, lap_duration, cumulative_time, 
               final_position, start_speed, racer_total_time
        FROM race_results
        WHERE race_id = ?
        ORDER BY lap_number, cumulative_time
    """, (most_recent_race_id,))
    
    results = cursor.fetchall()
    
    current_racer = None
    for result in results:
        racer_name = result[0]
        lap_num = result[1]
        lap_duration = result[2]
        cumulative = result[3]
        position = result[4]
        start_speed = result[5]
        total_time = result[6]
        
        if racer_name != current_racer:
            current_racer = racer_name
            pos_str = f"Position #{position}" if position else "No position"
            print(f"\n{racer_name} ({pos_str}):")
            if start_speed:
                print(f"  Start Speed: {start_speed:.3f}s")
        
        print(f"  Lap {lap_num}: {lap_duration:.3f}s (Total: {cumulative:.3f}s)", end="")
        if total_time:
            print(f" - Final Time: {total_time:.3f}s")
        else:
            print()

conn.close()

print("\n" + "=" * 80)
print(f"Total Races: {len(races)}")