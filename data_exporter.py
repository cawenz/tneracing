from tkinter import messagebox, filedialog
import csv
from config import logger # Use logger from config  
import shared_state # To access racers_data  

class RaceResultsExporter:
    def __init__(self, shared_state_ref, race_timer_ref):
        self.shared_state = shared_state_ref
        self.race_timer = race_timer_ref # To use format_time  

    def prompt_export_results(self):
        """Prompt user to export race results after race ends."""
        if messagebox.askyesno("Export Results", "Race has ended. Do you want to export the results to a CSV file?"): #  
            self.export_results_to_csv()

    def export_results_to_csv(self):
        """Export current race results to a CSV file, with one row per lap."""
        if not self.shared_state.racers_data: # [13]
            messagebox.showinfo("No Results", "No race results to export.") # [13]
            return

        file_path = filedialog.asksaveasfilename( # [13]
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save Race Results (Lap by Lap)"
        )

        if not file_path:
            return # User cancelled

        try:
            # Sort racers for consistent output, e.g., by name or final position if available
            # We'll use the existing final position sorting as a primary sort,
            # then fall back to name for consistency in output [7]
            export_racers = list(self.shared_state.racers_data.values())
            export_racers.sort(key=lambda x: (x["position"] if x["position"] > 0 else float('inf'), x["name"])) # [7]

            with open(file_path, 'w', newline='') as csvfile: # [7]
                csv_writer = csv.writer(csvfile)

                # New header row to include lap-specific details [User Request]
                csv_writer.writerow([
                    "Racer Name",
                    "Final Position",
                    "Lap Number",
                    "Total Laps in Race",
                    "Race Mode",  # NEW
                    "Lap Time (Duration)",
                    "Total Elapsed Time (Cumulative)",
                    "Racer Total Time"  # NEW - actual race time for the racer
                ])

                total_race_laps = self.shared_state.num_laps # Get total race laps from shared_state [2]

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
                    
                    # Get race mode display name
                    race_mode_display = "Start Line Race" if shared_state.race_mode == shared_state.RACE_MODE_START_LINE else "Rolling Start"

                    # Iterate through each lap recorded for the racer
                    for i, cumulative_lap_time in enumerate(racer["lap_times"]):
                        lap_num = i + 1

                        # Calculate individual lap duration based on race mode
                        if i == 0:
                            if shared_state.race_mode == shared_state.RACE_MODE_START_LINE and racer.get("start_time") is not None:
                                individual_lap_duration = cumulative_lap_time - racer["start_time"]
                            elif shared_state.race_mode == shared_state.RACE_MODE_ROLLING and racer.get("rolling_start_time") is not None:
                                individual_lap_duration = cumulative_lap_time - racer["rolling_start_time"]
                            else:
                                individual_lap_duration = cumulative_lap_time
                        else:
                            individual_lap_duration = cumulative_lap_time - racer["lap_times"][i-1]

                        # Format times for output  
                        formatted_lap_duration = self.race_timer.format_time(individual_lap_duration)
                        formatted_total_elapsed_time = self.race_timer.format_total_time(cumulative_lap_time)

                        csv_writer.writerow([
                            racer_name,
                            final_position_str,
                            lap_num,
                            total_race_laps,
                            race_mode_display,  # NEW
                            formatted_lap_duration,
                            formatted_total_elapsed_time,
                            racer_total_time if i == len(racer["lap_times"]) - 1 else "-"  # NEW - only on last lap
                        ])

            messagebox.showinfo("Export Successful", f"Race results (lap by lap) saved to:\n{file_path}") # 
            logger.info(f"Race results (lap by lap) exported to {file_path}") # [

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export results: {e}") # 
            logger.error(f"Error exporting results to CSV: {e}", exc_info=True) #
