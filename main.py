import os
import requests
os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "0"
os.environ["WLR_RENDERER"] = "gles2"
os.environ["WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS"] = "1"

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('WebKit', '6.0')
gi.require_version('Gdk', '4.0')
from gi.repository import Gtk, WebKit, GLib, Gdk

BASE_DIR = '/home/omethsk/jarvis'
SCREEN_PATH = 'file:///home/omethsk/jarvis/assets/desktop.html'

class JarvisApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='com.jarvis.os')
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        self.win = JarvisWindow(app)
        self.win.present()

class JarvisWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title('JARVIS OS')
        self.fullscreen()
        self.set_decorated(False)
        self.webview = WebKit.WebView()
        self.webview.set_hexpand(True)
        self.webview.set_vexpand(True)
        settings = self.webview.get_settings()
        settings.set_allow_universal_access_from_file_urls(True)
        settings.set_allow_file_access_from_file_urls(True)
        GLib.timeout_add(15000, self._push_weather)
        self.webview.get_settings().set_enable_write_console_messages_to_stdout(True)
        rgba = Gdk.RGBA()
        rgba.parse('#0d1b35')
        self.webview.set_background_color(rgba)
        self.webview.load_uri(SCREEN_PATH)
        self.set_child(self.webview)


    def _push_weather(self):
        try:
            r = requests.get('http://127.0.0.1:5000/weather', timeout=5)
            d = r.json()
            temp = round(d.get('temp', 0))
            code = d.get('code', 0)
            script = rf"""
            if (document.getElementById('jv-temp')) {{
                document.getElementById('jv-temp').textContent = '{temp}\u00b0';
                var icons = {{0:'\u2600\ufe0f',1:'\ud83c\udf24\ufe0f',2:'\u26c5',3:'\u2601\ufe0f',45:'\ud83c\udf2b\ufe0f',48:'\ud83c\udf2b\ufe0f',51:'\ud83c\udf27\ufe0f',61:'\ud83c\udf27\ufe0f',80:'\ud83c\udf26\ufe0f',95:'\u26c8\ufe0f'}};
                document.getElementById('jv-wicon').textContent = icons[{code}] || '\u2601\ufe0f';
                document.getElementById('jv-wdesc').textContent = 'COLOMBO';
            }}
            """
            self.webview.evaluate_javascript(script, -1, None, None, None, None, None)
            print(f'[Weather Push] Success: {temp} deg')
        except Exception as e:
            print(f'[Weather Push] {e}')
        return True

if __name__ == '__main__':
    app = JarvisApp()
    app.run()
