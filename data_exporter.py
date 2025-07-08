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
                    "Final Position", # Added final position for context
                    "Lap Number",
                    "Total Laps in Race",
                    "Lap Time (Duration)",
                    "Total Elapsed Time (Cumulative)"
                    # "Current Position in Race when Lap was Recorded" cannot be included from sources
                ])

                total_race_laps = self.shared_state.num_laps # Get total race laps from shared_state [2]

                for racer in export_racers:
                    racer_name = racer["name"] # [4, 6, 7]
                    final_position_str = str(racer["position"]) if racer["position"] > 0 else "-" # [7, 8, 11]

                    # Iterate through each lap recorded for the racer [User Request]
                    for i, cumulative_lap_time in enumerate(racer["lap_times"]): # [6]
                        lap_num = i + 1 # Lap number is 1-indexed [6]

                        # Calculate individual lap duration [4, 6]
                        if i == 0:
                            # First lap's duration is its cumulative time
                            individual_lap_duration = cumulative_lap_time
                        else:
                            # Subsequent laps: current cumulative time minus previous cumulative time
                            individual_lap_duration = cumulative_lap_time - racer["lap_times"][i-1] #

                        # Format times for output  
                        formatted_lap_duration = self.race_timer.format_time(individual_lap_duration)
                        formatted_total_elapsed_time = self.race_timer.format_total_time(cumulative_lap_time)

                        csv_writer.writerow([
                            racer_name,
                            final_position_str, # Includes final position for each lap row
                            lap_num,
                            total_race_laps,
                            formatted_lap_duration,
                            formatted_total_elapsed_time
                        ])

            messagebox.showinfo("Export Successful", f"Race results (lap by lap) saved to:\n{file_path}") # 
            logger.info(f"Race results (lap by lap) exported to {file_path}") # [

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export results: {e}") # 
            logger.error(f"Error exporting results to CSV: {e}", exc_info=True) #
