import tkinter as tk
import requests
import threading
import time

class MinimalDownloader:
    def __init__(self, master):
        self.master = master
        master.title("Text File Downloader")

        self.url_label = tk.Label(master, text="Text File URL:")
        self.url_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        self.url_entry = tk.Entry(master, width=50)
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky="we", padx=5, pady=5)
        self.url_entry.insert(0, "https://www.gutenberg.org/files/1342/1342-0.txt") # Default URL

        self.download_button = tk.Button(master, text="Hold to Download", relief=tk.RAISED)
        self.download_button.grid(row=1, column=0, columnspan=3, pady=10)
        self.download_button.bind("<ButtonPress-1>", self.start_download)
        self.download_button.bind("<ButtonRelease-1>", self.stop_download)

        self.line_number_area = tk.Text(master, width=4, padx=3, takefocus=0, borderwidth=1, relief=tk.FLAT, state='disabled', wrap='none')
        self.line_number_area.grid(row=2, column=0, sticky='nswe')

        self.text_area = tk.Text(master, wrap=tk.WORD, borderwidth=1, relief=tk.SUNKEN)
        self.text_area.grid(row=2, column=1, columnspan=2, sticky='nswe')

        self.scrollbar = tk.Scrollbar(master, command=self.yview)
        self.scrollbar.grid(row=2, column=3, sticky='ns')

        self.text_area.config(yscrollcommand=self.scrollbar.set)
        self.line_number_area.config(yscrollcommand=self.scrollbar.set)

        master.grid_columnconfigure(1, weight=1) # Make text area expand horizontally
        master.grid_rowconfigure(2, weight=1)    # Make text area expand vertically

        self.is_downloading = False
        self.download_thread = None
        self.downloaded_content = "" # Store downloaded content for resuming

        self.update_line_numbers() # Initial line numbers

        # --- Bind scroll events to both text areas for unified scrolling ---
        self.line_number_area.bind("<MouseWheel>", self.unified_scroll)
        self.text_area.bind("<MouseWheel>", self.unified_scroll)
        self.line_number_area.bind("<Button-4>", self.unified_scroll) # For Linux/Tk compatibility (scroll up)
        self.text_area.bind("<Button-4>", self.unified_scroll) # For Linux/Tk compatibility (scroll up)
        self.line_number_area.bind("<Button-5>", self.unified_scroll) # For Linux/Tk compatibility (scroll down)
        self.text_area.bind("<Button-5>", self.unified_scroll) # For Linux/Tk compatibility (scroll down)

    def yview(self, *args):
        self.text_area.yview(*args)
        self.line_number_area.yview(*args)

    def unified_scroll(self, event):
        if event.widget == self.text_area:
            scroll_amount = event.delta if hasattr(event, 'delta') else (1 if event.num == 5 else -1) # Determine scroll amount and direction
            self.line_number_area.yview_scroll(int(-1 * scroll_amount/120), "units") # Adjust divisor if needed for sensitivity
        elif event.widget == self.line_number_area:
            scroll_amount = event.delta if hasattr(event, 'delta') else (1 if event.num == 5 else -1)
            self.text_area.yview_scroll(int(-1 * scroll_amount/120), "units") # Adjust divisor if needed for sensitivity
        return "break" # Prevent default scrolling


    def update_line_numbers(self):
        self.line_number_area.config(state='normal')
        self.line_number_area.delete(1.0, tk.END)
        line_count = self.text_area.index('end - 1 line').split('.')[0]
        line_numbers = "\n".join(str(i) for i in range(1, int(line_count) + 1))
        self.line_number_area.insert(tk.END, line_numbers)
        self.line_number_area.config(state='disabled')

    def start_download(self, event):
        if not self.is_downloading:
            self.is_downloading = True
            self.download_button.config(relief=tk.SUNKEN) # Visual feedback
            self.download_thread = threading.Thread(target=self.download_text)
            self.download_thread.start()

    def stop_download(self, event):
        if self.is_downloading:
            self.is_downloading = False
            self.download_button.config(relief=tk.RAISED) # Visual feedback
            if self.download_thread and self.download_thread.is_alive():
                pass

    def download_text(self):
        url = self.url_entry.get()
        headers = {}
        downloaded_bytes = len(self.downloaded_content.encode('utf-8'))
        if downloaded_bytes > 0:
            headers['Range'] = f'bytes={downloaded_bytes}-' # Request remaining bytes

        try:
            response = requests.get(url, stream=True, headers=headers)
            response.raise_for_status() # Raise HTTPError for bad responses

            if downloaded_bytes > 0 and response.status_code == 206: # 206 Partial Content on resume
                pass # Continue download from where we left off
            elif downloaded_bytes > 0 and response.status_code != 206:
                self.text_area.insert(tk.END, "\n\nWarning: Server did not support resume, downloading from start again.")
                self.downloaded_content = "" # Reset and download from beginning if resume failed
                self.text_area.delete(1.0, tk.END) # Clear text area for fresh download


            for chunk in response.iter_content(chunk_size=1024): # Download in chunks
                if not self.is_downloading:
                    break # Stop if button released

                if chunk: # filter out keep-alive new chunks
                    decoded_chunk = chunk.decode('utf-8', errors='ignore') # Decode to text, ignore errors
                    self.downloaded_content += decoded_chunk # Append to existing content
                    self.text_area.insert(tk.END, decoded_chunk)
                    self.update_line_numbers() # Update line numbers after each chunk
                    self.text_area.see(tk.END) # Scroll to the end
                    self.master.update() # Force GUI update
                    time.sleep(0.01) # Optional delay

            if self.is_downloading: # Only if download completed naturally
                self.text_area.insert(tk.END, "\n\nDownload Complete.")
        except requests.exceptions.RequestException as e:
            self.text_area.insert(tk.END, f"\n\nError during download: {e}")
        finally:
            if self.is_downloading: # If it wasn't explicitly stopped
                self.is_downloading = False
                self.download_button.config(relief=tk.RAISED)


if __name__ == "__main__":
    root = tk.Tk()
    gui = MinimalDownloader(root)
    root.mainloop()
