from tkinter import messagebox, filedialog
import csv
from config import logger # Use logger from config  
import shared_state # To access racers_data  

class RaceResultsExporter:
    def __init__(self, shared_state_ref, race_timer_ref):
        """Initialize the exporter with references to shared state and race timer"""
        self.shared_state = shared_state_ref
        self.race_timer = race_timer_ref # To use format_time  

    def prompt_export_results(self):
        """Prompt user to export race results after race ends."""
        if messagebox.askyesno("Export Results", "Race has ended. Do you want to export the results to a CSV file?"): #  
            self.export_results_to_csv()

    def export_results_to_csv(self):
        """Export current race results to a CSV file, with race name and datetime."""
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

                # UPDATED header row to include race name and datetime
                csv_writer.writerow([
                    "Race Name",  # NEW COLUMN
                    "Race Date/Time",  # NEW COLUMN
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
                
                # NEW: Format race name and datetime
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
                    
                    # Get race mode display name
                    race_mode_display = "Start Line Race" if shared_state.race_mode == shared_state.RACE_MODE_START_LINE else "Rolling Start"

                    # Format start speed for display
                    if shared_state.race_mode == shared_state.RACE_MODE_START_LINE and racer.get("start_speed") is not None:
                        formatted_start_speed = f"{racer['start_speed']:.3f}"
                    else:
                        formatted_start_speed = "-"

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

                        # Show start speed only on the first lap row
                        start_speed_for_row = formatted_start_speed if lap_num == 1 else "-"

                        csv_writer.writerow([
                            race_name_display,  # NEW: Race name
                            race_datetime_display,  # NEW: Race datetime
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