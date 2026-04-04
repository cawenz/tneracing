#!/usr/bin/env python3
"""Debug the last race attempt"""
import shared_state
from data_exporter import RaceResultsExporter
from race_timer import RaceTimer

# Print current shared_state
print("=" * 60)
print("CURRENT SHARED STATE")
print("=" * 60)
print(f"Race name: {shared_state.race_name}")
print(f"Race datetime: {shared_state.race_start_datetime}")
print(f"Race mode: {shared_state.race_mode}")
print(f"Num laps: {shared_state.num_laps}")
print(f"Racers data count: {len(shared_state.racers_data)}")
print(f"Racers data keys: {list(shared_state.racers_data.keys())}")

if shared_state.racers_data:
    print("\nRacer details:")
    for tag, racer in shared_state.racers_data.items():
        print(f"  {tag}: {racer['name']}")
        print(f"    Laps: {racer['laps']}")
        print(f"    Lap times: {racer['lap_times']}")
        print(f"    Position: {racer['position']}")

# Try to save again
print("\n" + "=" * 60)
print("ATTEMPTING TO SAVE TO CACHE")
print("=" * 60)

exporter = RaceResultsExporter(shared_state, RaceTimer)
result = exporter.save_race_to_cache()

print(f"\nResult: {result}")

# Check database
print("\n" + "=" * 60)
print("CHECKING DATABASE")
print("=" * 60)

import sqlite3
conn = sqlite3.connect("race_results_cache.db")
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM races")
print(f"Total races: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM race_results")
print(f"Total lap records: {cursor.fetchone()[0]}")

conn.close()