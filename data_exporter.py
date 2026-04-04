from tkinter import messagebox, filedialog
import csv
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from config import logger
import shared_state

class RaceResultsExporter:
    def __init__(self, shared_state_ref, race_timer_ref):
        """Initialize the exporter with references to shared state and race timer"""
        self.shared_state = shared_state_ref
        self.race_timer = race_timer_ref
        
        # Initialize SQLite cache database
        self.cache_db_path = Path("race_results_cache.db")
        logger.info(f"Initializing RaceResultsExporter with cache at: {self.cache_db_path.absolute()}")
        self.init_cache_database()
    
    def init_cache_database(self):
        """Initialize the SQLite cache database"""
        try:
            logger.info(f"Creating/opening database at: {self.cache_db_path.absolute()}")
            conn = sqlite3.connect(str(self.cache_db_path))
            cursor = conn.cursor()
            
            # Create races table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS races (
                    race_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    race_name TEXT NOT NULL,
                    race_datetime TEXT NOT NULL,
                    race_mode TEXT NOT NULL,
                    total_laps INTEGER NOT NULL,
                    synced_to_remote INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    UNIQUE(race_name, race_datetime)
                )
            ''')
            
            # Create race_results table (lap-by-lap data)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS race_results (
                    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    race_id INTEGER NOT NULL,
                    racer_name TEXT NOT NULL,
                    racer_tag TEXT NOT NULL,
                    final_position INTEGER,
                    lap_number INTEGER NOT NULL,
                    lap_duration REAL NOT NULL,
                    cumulative_time REAL NOT NULL,
                    racer_total_time REAL,
                    start_speed REAL,
                    FOREIGN KEY (race_id) REFERENCES races(race_id),
                    UNIQUE(race_id, racer_tag, lap_number)
                )
            ''')
            
            # Create index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_race_results_race_id 
                ON race_results(race_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_races_synced 
                ON races(synced_to_remote)
            ''')
            
            conn.commit()
            
            # Verify tables were created
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            logger.info(f"Database tables: {tables}")
            
            conn.close()
            logger.info("Cache database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing cache database: {e}", exc_info=True)
            raise
    
    def prompt_export_results(self):
        """Prompt user to export race results after race ends"""
        logger.info("prompt_export_results() called")
        
        # CRITICAL FIX: Copy the data immediately before any dialogs or delays
        # This protects against data being cleared by reset or cleanup code
        racers_data_copy = {}
        try:
            for tag, racer in self.shared_state.racers_data.items():
                # Deep copy the racer data
                racers_data_copy[tag] = {
                    "name": racer.get("name", ""),
                    "laps": racer.get("laps", 0),
                    "lap_times": racer.get("lap_times", []).copy(),
                    "start_time": racer.get("start_time"),
                    "rolling_start_time": racer.get("rolling_start_time"),
                    "start_speed": racer.get("start_speed"),
                    "has_started": racer.get("has_started", False),
                    "finished": racer.get("finished", False),
                    "position": racer.get("position", 0),
                    "finish_time": racer.get("finish_time", 0)
                }
        except Exception as e:
            logger.error(f"Error copying racer data: {e}", exc_info=True)
        
        logger.info(f"Copied {len(racers_data_copy)} racers for caching")
        
        # Save using the copied data
        cache_success = self._save_race_to_cache_with_data(racers_data_copy)
        logger.info(f"Cache save result: {cache_success}")
        
        if cache_success:
            message = "Race results saved to local cache.\n\nDo you want to export to CSV file?"
        else:
            message = "Warning: Could not save to cache.\n\nDo you want to export to CSV file?"
        
        if messagebox.askyesno("Export Results", message):
            self.export_results_to_csv()
    
    def _save_race_to_cache_with_data(self, racers_data):
        """Save race results to SQLite cache using provided data"""
        logger.info("=" * 60)
        logger.info("Starting _save_race_to_cache_with_data()")
        logger.info("=" * 60)
        
        logger.info(f"racers_data type: {type(racers_data)}")
        logger.info(f"racers_data length: {len(racers_data)}")
        logger.info(f"racers_data keys: {list(racers_data.keys())}")
        
        if not racers_data:
            logger.warning("No race data to cache - racers_data is empty!")
            return False
        
        try:
            logger.info(f"Connecting to database: {self.cache_db_path.absolute()}")
            conn = sqlite3.connect(str(self.cache_db_path))
            cursor = conn.cursor()
            
            # Prepare race metadata
            race_name = shared_state.race_name or "Unnamed Race"
            race_datetime = shared_state.race_start_datetime.strftime("%Y-%m-%d %H:%M:%S") if shared_state.race_start_datetime else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            race_mode = "Start Line Race" if shared_state.race_mode == shared_state.RACE_MODE_START_LINE else "Rolling Start"
            total_laps = self.shared_state.num_laps
            
            logger.info(f"Race metadata:")
            logger.info(f"  Name: {race_name}")
            logger.info(f"  DateTime: {race_datetime}")
            logger.info(f"  Mode: {race_mode}")
            logger.info(f"  Total Laps: {total_laps}")
            
            # Insert race record
            logger.info("Inserting race record...")
            cursor.execute('''
                INSERT OR IGNORE INTO races 
                (race_name, race_datetime, race_mode, total_laps, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (race_name, race_datetime, race_mode, total_laps, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            logger.info(f"Rows affected by race insert: {cursor.rowcount}")
            
            # Get the race_id
            cursor.execute('''
                SELECT race_id FROM races 
                WHERE race_name = ? AND race_datetime = ?
            ''', (race_name, race_datetime))
            
            result = cursor.fetchone()
            if not result:
                logger.error("Failed to retrieve race_id after insert!")
                conn.close()
                return False
            
            race_id = result[0]
            logger.info(f"Race ID: {race_id}")
            
            # Prepare racers data sorted by position
            export_racers = list(racers_data.values())
            export_racers.sort(key=lambda x: (x["position"] if x["position"] > 0 else float('inf'), x["name"]))
            
            logger.info(f"Processing {len(export_racers)} racers...")
            
            total_laps_inserted = 0
            
            # Insert lap-by-lap results
            for racer_idx, racer in enumerate(export_racers, 1):
                racer_name = racer["name"]
                final_position = racer["position"] if racer["position"] > 0 else None
                
                logger.info(f"  Racer {racer_idx}/{len(export_racers)}: {racer_name}")
                logger.info(f"    Position: {final_position}")
                logger.info(f"    Laps completed: {racer['laps']}")
                logger.info(f"    Lap times: {len(racer['lap_times'])}")
                
                # Get racer tag
                racer_tag = None
                for tag, data in racers_data.items():
                    if data["name"] == racer_name:
                        racer_tag = tag
                        break
                
                if not racer_tag:
                    logger.warning(f"    Could not find tag for racer {racer_name}, skipping...")
                    continue
                
                logger.info(f"    Tag: {racer_tag}")
                
                # Calculate racer's total race time
                racer_total_time = None
                if shared_state.race_mode == shared_state.RACE_MODE_ROLLING and racer.get("rolling_start_time") is not None and racer["lap_times"]:
                    racer_total_time = racer["lap_times"][-1] - racer["rolling_start_time"]
                elif shared_state.race_mode == shared_state.RACE_MODE_START_LINE and racer.get("start_time") is not None and racer["lap_times"]:
                    racer_total_time = racer["lap_times"][-1] - racer["start_time"]
                
                logger.info(f"    Total race time: {racer_total_time}")
                
                # Get start speed
                start_speed = racer.get("start_speed") if shared_state.race_mode == shared_state.RACE_MODE_START_LINE else None
                logger.info(f"    Start speed: {start_speed}")
                
                # Insert each lap
                for i, cumulative_lap_time in enumerate(racer["lap_times"]):
                    lap_num = i + 1
                    
                    # Calculate individual lap duration
                    if i == 0:
                        if shared_state.race_mode == shared_state.RACE_MODE_START_LINE and racer.get("start_time") is not None:
                            individual_lap_duration = cumulative_lap_time - racer["start_time"]
                        elif shared_state.race_mode == shared_state.RACE_MODE_ROLLING and racer.get("rolling_start_time") is not None:
                            individual_lap_duration = cumulative_lap_time - racer["rolling_start_time"]
                        else:
                            individual_lap_duration = cumulative_lap_time
                    else:
                        individual_lap_duration = cumulative_lap_time - racer["lap_times"][i-1]
                    
                    logger.debug(f"      Lap {lap_num}: duration={individual_lap_duration:.3f}s, cumulative={cumulative_lap_time:.3f}s")
                    
                    # Insert lap record
                    cursor.execute('''
                        INSERT OR REPLACE INTO race_results 
                        (race_id, racer_name, racer_tag, final_position, lap_number, 
                         lap_duration, cumulative_time, racer_total_time, start_speed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (race_id, racer_name, racer_tag, final_position, lap_num,
                          individual_lap_duration, cumulative_lap_time, 
                          racer_total_time if i == len(racer["lap_times"]) - 1 else None,
                          start_speed if lap_num == 1 else None))
                    
                    total_laps_inserted += 1
            
            logger.info(f"Total lap records inserted: {total_laps_inserted}")
            
            conn.commit()
            
            # Verify data was inserted
            cursor.execute("SELECT COUNT(*) FROM race_results WHERE race_id = ?", (race_id,))
            count = cursor.fetchone()[0]
            logger.info(f"Verification: {count} records found in database for race_id {race_id}")
            
            conn.close()
            
            logger.info(f"✓ Race '{race_name}' saved to cache database (race_id: {race_id})")
            logger.info("=" * 60)
            return True
            
        except Exception as e:
            logger.error(f"Error saving race to cache: {e}", exc_info=True)
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def save_race_to_cache(self):
        """Save race results to SQLite cache - wrapper for backward compatibility"""
        return self._save_race_to_cache_with_data(self.shared_state.racers_data)
    
    def get_unsynced_races(self):
        """Get list of races that haven't been synced to remote database"""
        try:
            conn = sqlite3.connect(str(self.cache_db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT race_id, race_name, race_datetime, race_mode, total_laps
                FROM races
                WHERE synced_to_remote = 0
                ORDER BY race_datetime DESC
            ''')
            
            races = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'race_id': r[0],
                    'race_name': r[1],
                    'race_datetime': r[2],
                    'race_mode': r[3],
                    'total_laps': r[4]
                }
                for r in races
            ]
            
        except Exception as e:
            logger.error(f"Error getting unsynced races: {e}", exc_info=True)
            return []
    
    def mark_race_as_synced(self, race_id):
        """Mark a race as synced to remote database"""
        try:
            conn = sqlite3.connect(str(self.cache_db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE races 
                SET synced_to_remote = 1
                WHERE race_id = ?
            ''', (race_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Race {race_id} marked as synced")
            return True
            
        except Exception as e:
            logger.error(f"Error marking race as synced: {e}", exc_info=True)
            return False
    
    def get_race_results(self, race_id):
        """Get all results for a specific race"""
        try:
            conn = sqlite3.connect(str(self.cache_db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT racer_name, racer_tag, final_position, lap_number,
                       lap_duration, cumulative_time, racer_total_time, start_speed
                FROM race_results
                WHERE race_id = ?
                ORDER BY lap_number, cumulative_time
            ''', (race_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'racer_name': r[0],
                    'racer_tag': r[1],
                    'final_position': r[2],
                    'lap_number': r[3],
                    'lap_duration': r[4],
                    'cumulative_time': r[5],
                    'racer_total_time': r[6],
                    'start_speed': r[7]
                }
                for r in results
            ]
            
        except Exception as e:
            logger.error(f"Error getting race results: {e}", exc_info=True)
            return []
    
    def export_results_to_csv(self):
        """Export current race results to a CSV file, with race name and datetime"""
        if not self.shared_state.racers_data:
            messagebox.showinfo("No Results", "No race results to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Race Results (Lap by Lap)"
        )

        if not file_path:
            return

        try:
            export_racers = list(self.shared_state.racers_data.values())
            export_racers.sort(key=lambda x: (x["position"] if x["position"] > 0 else float('inf'), x["name"]))

            with open(file_path, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile)

                # Header row
                csv_writer.writerow([
                    "Race Name",
                    "Race Date/Time",
                    "Racer Name",
                    "Final Position",
                    "Lap Number",
                    "Total Laps in Race",
                    "Race Mode",
                    "Start Speed",
                    "Lap Time (Duration)",
                    "Total Elapsed Time (Cumulative)",
                    "Racer Total Time"
                ])

                total_race_laps = self.shared_state.num_laps
                race_name_display = shared_state.race_name or "Unnamed Race"
                race_datetime_display = shared_state.race_start_datetime.strftime("%Y-%m-%d %H:%M:%S") if shared_state.race_start_datetime else "-"

                for racer in export_racers:
                    racer_name = racer["name"]
                    final_position_str = str(racer["position"]) if racer["position"] > 0 else "-"
                    
                    # Calculate racer's actual total race time
                    racer_total_time = "-"
                    if shared_state.race_mode == shared_state.RACE_MODE_ROLLING and racer.get("rolling_start_time") is not None and racer["lap_times"]:
                        total_seconds = racer["lap_times"][-1] - racer["rolling_start_time"]
                        racer_total_time = self.race_timer.format_total_time(total_seconds)
                    elif shared_state.race_mode == shared_state.RACE_MODE_START_LINE and racer.get("start_time") is not None and racer["lap_times"]:
                        total_seconds = racer["lap_times"][-1] - racer["start_time"]
                        racer_total_time = self.race_timer.format_total_time(total_seconds)
                    
                    race_mode_display = "Start Line Race" if shared_state.race_mode == shared_state.RACE_MODE_START_LINE else "Rolling Start"

                    if shared_state.race_mode == shared_state.RACE_MODE_START_LINE and racer.get("start_speed") is not None:
                        formatted_start_speed = f"{racer['start_speed']:.3f}"
                    else:
                        formatted_start_speed = "-"

                    for i, cumulative_lap_time in enumerate(racer["lap_times"]):
                        lap_num = i + 1

                        if i == 0:
                            if shared_state.race_mode == shared_state.RACE_MODE_START_LINE and racer.get("start_time") is not None:
                                individual_lap_duration = cumulative_lap_time - racer["start_time"]
                            elif shared_state.race_mode == shared_state.RACE_MODE_ROLLING and racer.get("rolling_start_time") is not None:
                                individual_lap_duration = cumulative_lap_time - racer["rolling_start_time"]
                            else:
                                individual_lap_duration = cumulative_lap_time
                        else:
                            individual_lap_duration = cumulative_lap_time - racer["lap_times"][i-1]

                        formatted_lap_duration = self.race_timer.format_time(individual_lap_duration)
                        formatted_total_elapsed_time = self.race_timer.format_total_time(cumulative_lap_time)

                        start_speed_for_row = formatted_start_speed if lap_num == 1 else "-"

                        csv_writer.writerow([
                            race_name_display,
                            race_datetime_display,
                            racer_name,
                            final_position_str,
                            lap_num,
                            total_race_laps,
                            race_mode_display,
                            start_speed_for_row,
                            formatted_lap_duration,
                            formatted_total_elapsed_time,
                            racer_total_time if i == len(racer["lap_times"]) - 1 else "-"
                        ])

            messagebox.showinfo("Export Successful", f"Race results for '{race_name_display}' saved to:\n{file_path}")
            logger.info(f"Race results for '{race_name_display}' exported to {file_path}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export results: {e}")
            logger.error(f"Error exporting results to CSV: {e}", exc_info=True)