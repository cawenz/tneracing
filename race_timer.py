import time

class RaceTimer:
    def __init__(self, monitor_callback_interface): # 'monitor_callback_interface' will be an instance of RFIDTagMonitor
        self.monitor = monitor_callback_interface
        self.is_running = False 
        self.start_time = 0 
        self.timer_id = None 

    def start(self):
        """Start the race timer"""
        self.is_running = True 
        self.start_time = time.time() 
        self.update_display() 

    def stop(self):
        """Stop the race timer"""
        self.is_running = False 
        if self.timer_id:
            self.monitor.root.after_cancel(self.timer_id) 
        self.timer_id = None 

    def update_display(self):
        """Update the timer display"""
        if not self.is_running: 
            return
        elapsed_time = time.time() - self.start_time 
        time_str = self.format_time(elapsed_time)
        self.monitor.update_timer_display(time_str) # Calls a method on the main UI
        self.timer_id = self.monitor.root.after(100, self.update_display)

    @staticmethod
    def format_time(seconds):
        """Format time in H:MM:SS.ss format"""
        hours = int(seconds // 3600) 
        minutes = int((seconds % 3600) // 60) 
        seconds = seconds % 60 
        return f"{hours}:{minutes:02d}:{seconds:06.3f}"
    
    @staticmethod
    def format_total_time(seconds):
    # Format time in MM:SS.000 format for Total Time display
        if seconds <= 0:
            return "-"
        minutes = int(seconds // 60)
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:06.3f}"