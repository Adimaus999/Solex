from PyQt6.QtCore import QUrl, QTimer
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.uic import loadUi
import sys

class MapWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Load the UI file created in Qt Designer (Map.ui)
        loadUi("Map.ui", self)

        # Set the URL to load the HTML file from the local HTTP server
        self.webView.setUrl(QUrl("http://localhost:8000/map.html"))

        # Hard-coded Latitude and Longitude values
        self.lat = 51.5074  # Example latitude (London)
        self.lon = -1  # Example longitude (London)

        # Set up a QTimer to periodically update the map with the new coordinates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_location)
        self.timer.start(2000)  # Update every 2 seconds (2000 milliseconds)

        # Initial update when the program starts
        self.update_location()

    def update_location(self):
        """Update the map with the predefined latitude and longitude."""
        # Update the map with the new coordinates by invoking JavaScript
        script = f"updateMap({self.lat}, {self.lon});"
        self.webView.page().runJavaScript(script)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Start the local HTTP server in a separate thread to serve the HTML file
    import threading
    def start_http_server():
        import os
        os.system('python -m http.server 8000')

    # Start the server in a separate thread
    server_thread = threading.Thread(target=start_http_server)
    server_thread.daemon = True  # Makes sure the server stops when the program ends
    server_thread.start()

    # Create the main window and show it
    window = MapWindow()
    window.show()

    sys.exit(app.exec())












    





