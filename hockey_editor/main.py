from ui.main_window import MainWindow
from core.video_controller import VideoController

if __name__ == "__main__":
    controller = VideoController()
    app = MainWindow(controller)
    controller.set_view(app)
    app.run()  # ← mainloop() здесь
