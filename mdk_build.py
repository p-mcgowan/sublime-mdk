import sublime
import sublime_plugin

import os
import subprocess
import threading
import signal

import re
import glob
import shutil
import traceback
from datetime import datetime
import html

default_encoding = "utf-8"
default_build_dir = "./build"
default_output = "Script.cs"
default_main = "main.cs"
default_files = "*"
default_thumb = True
default_se_game_dir = "C:\\program files (x86)\\steam\\SteamApps\\common\\SpaceEngineers"
default_csc_dir = "C:\\Program Files\\dotnet\\sdk\\8.0.404\\Roslyn\\bincore"
default_dotnet_48_dir = "C:\\Program Files (x86)\\Reference Assemblies\\Microsoft\\Framework\\.NETFramework\\v4.8"

error_style = sublime.DRAW_NO_FILL | sublime.DRAW_NO_OUTLINE | sublime.DRAW_SQUIGGLY_UNDERLINE
errs_by_file = {}
error_regions = []

class MdkBuildCommand(sublime_plugin.WindowCommand):
    phantom_sets_by_buffer = None
    regions = []
    build_dir = None
    encoding = None
    file_regex = None
    files = None
    killed = False
    main = None
    manifest_dir = None
    manifest_filename = 'mdk.sublime-settings'
    mdk_root = os.path.dirname(os.path.abspath(__file__))
    output = None
    panel = None
    panel_lock = threading.Lock()
    proc = None
    se_game_dir = None
    csc_dir = None
    thumb = None
    ext = None
    manifest = None
    allowLinq = False
    minify = False
    unminified_file = None

    def run(self, **kwargs):
        try:
            self.build()

        except:
            self.log(traceback.format_exc())

    def build(self):
        if not self.import_settings():
            return 1
        self.log("Build started: {}".format(datetime.now()))

        self.hide_errors()

        # if minifier selected
        #   create minifier if not exists

        targets = self.collect_build_files()
        if targets is None:
            self.log("No files to build")
            return 1

        compile_files = self.prepare(targets)
        bat_tpl = os.path.join(self.mdk_root, "MDK/compile.bat")
        bat_out = os.path.join(self.build_dir, "compile.bat")

        bat_file = self.generate_bat_script(bat_tpl, bat_out, compile_files)
        thread = self.start_compile_thread(bat_file, targets)

    def setup_build_panel(self):
        with self.panel_lock:
            self.panel = self.window.create_output_panel("panel")
            settings = self.panel.settings()

            settings.set("result_file_regex", r"^(.*\.cs)\((\d*),(\d*),\d*,\d*\): (.*)")
            settings.set("result_line_regex", r"^(.*\.cs)\((\d*),(\d*),\d*,\d*\): (.*)")
            settings.set("result_base_dir", self.manifest_dir)

            preferences = sublime.load_settings("Preferences.sublime-settings")
            if preferences.get("show_panel_on_build"):
                self.window.run_command("show_panel", { "panel": "output.panel" })

    def generate_bat_script(self, bat_tpl, bat_out, files = []):
        try:
            os.remove(bat_out)
        except:
            pass

        content = None

        with open(bat_tpl, "r") as bat_tpl:
            tpl = (bat_tpl.read()
                .replace("MDK_ROOT", self.mdk_root)
                .replace("SE_GAME_DIR", self.se_game_dir)
                .replace("CSC_DIR", self.csc_dir)
                .replace("DOTNET_48_DIR", self.dotnet_48_dir)
                .replace("INJECT_FILES", '" "'.join(files)))
            if not self.allowLinq:
                tpl = tpl.replace(r"^.*Linq.*", "")
            content = tpl.replace("\n", " ").replace(", ", ",")

        with open(bat_out, "w") as bat_file:
            bat_file.write(content)

        return bat_out

    def on_success(self, files):
        for file in ['compile.bat']:
            try:
                os.remove(os.path.join(self.build_dir, file))
            except:
                pass

        thumb_src = None

        if self.thumb == True:
            thumb_src = os.path.join(self.mdk_root, 'MDK/thumb.png')
            # copy mdk thumb
        elif self.thumb:
            thumb_src = self.thumb

        if thumb_src is not None:
            shutil.copyfile(thumb_src, os.path.join(os.path.dirname(self.output), 'thumb.png'))

        with open(self.output, 'wb') as out_fd:
            for f in files:
                with open(f, 'rb') as in_fd:
                    shutil.copyfileobj(in_fd, out_fd)

        # self.proc = None
        if self.minify:
          self.log("Minification started: {}".format(datetime.now()))
          thread = threading.Thread(target=self.run_minify_in_thread)
          thread.start()

          return thread;

    def prepare(self, targets):
        shutil.rmtree(self.build_dir, ignore_errors=True)
        compile_files = []

        def to_build_dir(full_path):
            shared_root = os.path.commonprefix([self.build_dir, full_path])
            return full_path.replace(shared_root, '')

        with open(os.path.join(self.mdk_root, 'MDK/head.cs')) as head_file:
            head = head_file.read().rstrip()
            if not self.allowLinq:
                head = head.replace('using System.Linq;', '')

        with open(os.path.join(self.mdk_root, 'MDK/tail.cs')) as tail_file:
            tail = tail_file.read().rstrip()

        for target in targets:
            relative_output = to_build_dir(target)
            out_file = os.path.join(self.build_dir, relative_output)

            try:
                os.makedirs(os.path.dirname(out_file))
            except Exception:
                pass

            with open(out_file, 'w') as output:
                output.write(head)
                with open(target) as in_fd:
                    output.write(in_fd.read())
                output.write(tail)

            compile_files.append(os.path.normpath(relative_output))

        compile_files.reverse() # make main last

        return compile_files

    def collect_build_files(self):
        files = {}

        def add_file(file_path):
            filename = os.path.realpath(file_path)
            _, file_extension = os.path.splitext(filename)

            if (file_extension != '.cs' or filename == self.output or filename == self.main or filename == self.build_dir):
                return

            files[filename] = True

        def read_manifest_files(base_dir, target_files):
            for part in re.split(r'\ *,+\ *', target_files):
                for file in glob.glob(os.path.join(base_dir, part)):
                    if os.path.isdir(file):
                        if os.path.isfile(os.path.join(file, self.manifest_filename)):
                            manifest = self.read_manifest(os.path.join(file, self.manifest_filename))
                            if manifest is not None:
                                read_manifest_files(file, manifest.get("files", ""))
                        else:
                            for script in glob.glob("{}/**".format(file)):
                                add_file(script)
                    else:
                        add_file(os.path.join(base_dir, file))

        read_manifest_files("./", self.files)

        targets = sorted(list(files.keys()))
        if os.path.isfile(self.main):
            targets.insert(0, self.main)

        # files with ext classes must go last
        if os.path.isfile(self.ext):
            targets.append(self.ext)

        return targets if len(targets) else None

    def import_settings(self):
        window_vars = self.window.extract_variables()
        self.working_dir = window_vars['file_path']

        manifest = self.find_manifest()
        if manifest is None:
            print("no manifest")
            return False

        self.setup_build_panel()

        self.manifest = manifest
        self.encoding = manifest.get("encoding", default_encoding)
        self.build_dir = os.path.realpath(manifest.get("build_dir", default_build_dir))
        self.output = os.path.realpath(manifest.get("output", default_output))
        self.main = os.path.realpath(manifest.get("main", default_main))
        self.files = manifest.get("files", default_files)
        self.thumb = manifest.get("thumb", default_thumb)
        self.allowLinq = manifest.get("allowLinq", False)
        self.se_game_dir = os.path.realpath(manifest.get("se_game_dir", default_se_game_dir))
        self.csc_dir = os.path.realpath(manifest.get("csc_dir", default_csc_dir))
        self.dotnet_48_dir = os.path.realpath(manifest.get("dotnet_48_dir", default_dotnet_48_dir))
        self.ext = os.path.realpath(manifest.get("ext", ""))
        self.minify = manifest.get("minify", False)
        self.unminified_file = manifest.get("unminified_file", None)

        return True

    def read_manifest(self, file_path):
        with open(file_path) as settings:
            return sublime.decode_value(settings.read())

    def find_manifest(self):
        os.chdir(self.working_dir)
        for i in range(100):
            here = os.getcwd()
            if os.path.isfile(self.manifest_filename):
                if here == self.mdk_root:
                    self.log("Refusing to build the plugin folder")
                    return None
                self.manifest_dir = here
                return self.read_manifest(os.path.join(os.getcwd(), self.manifest_filename))

            os.chdir('../')
            if os.getcwd() == here:
                self.log("No {} found from {} to {}".format(self.manifest_filename, self.working_dir, os.getcwd()))
                return None

        os.chdir(self.manifest_dir)

    def log(self, msg, newline=True):
        if self.panel is not None:
            with self.panel_lock:
                data = "{}{}".format(msg, "\n" if newline else None).replace('\r\n', '\n').replace('\r', '\n')
                self.panel.run_command("append", { "characters": data })
        else:
            print(msg)

    def start_compile_thread(self, path_to_bat, targets):
        thread = threading.Thread(target=self.run_build_in_thread, args=(path_to_bat, targets,))
        thread.start()

        return thread;

    def run_build_in_thread(self, path_to_bat, targets):
        if self.proc is not None:
            self.proc.terminate()
            self.proc = None

        SW_HIDE = 0
        info = subprocess.STARTUPINFO()
        info.dwFlags = subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = SW_HIDE

        self.proc = subprocess.Popen(path_to_bat, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self.build_dir, startupinfo=info)
        self.killed = False

        def kill():
            self.log("Timeout - killing")
            subprocess.call(['taskkill', '/F', '/T', '/PID',  str(self.proc.pid)], startupinfo=info)

        t = threading.Timer(10.0, kill)
        t.start()
        stdout, stderr = self.proc.communicate()
        t.cancel()
        self.log(stdout.decode(self.encoding).replace(self.build_dir, self.manifest_dir))

        if self.proc.returncode == 0:
            self.log("Build success")
            self.on_success(targets)
        else:
            self.log("Build failed ({})".format(self.proc.returncode))
            self.show_errors()


        return self.proc.returncode

    def run_minify_in_thread(self):
        SW_HIDE = 0
        info = subprocess.STARTUPINFO()
        info.dwFlags = subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = SW_HIDE

        input_file = self.output
        output_file = self.output

        if self.unminified_file is not None:
          input_file = os.path.realpath(self.unminified_file)
          shutil.copyfile(self.output, input_file)

        if self.proc is not None:
            self.proc.terminate()
            self.proc = None

        path_to_exe = os.path.join(self.mdk_root, "MDK","bin","mdkmin.exe")
        if not os.path.isfile(path_to_exe):
            self.log("Minification cannot run .exe (needs to be build - good luck...). Looked here: {}".format(path_to_exe))
            raise "Minifier needs to be build - good luck..."

            print("Building minifier")
            bat_tpl = os.path.join(self.mdk_root, "MDK","minifier.bat")
            out_bat = os.path.join(self.mdk_root, "MDK","bin","minifier-compiled.bat")
            res = self.generate_bat_script(bat_tpl, out_bat)
            self.proc = subprocess.Popen([out_bat], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, startupinfo=info)
            stdout, stderr = self.proc.communicate()
            self.log(stdout.decode(self.encoding).replace(self.build_dir, self.manifest_dir))

            if self.proc.returncode != 0:
                self.log("Minification failed ({})".format(self.proc.returncode))
                self.show_errors()
                return self.proc.returncode
            else:
                print("worked?")
                print("C:\\Users\\mcgow\\AppData\\Roaming\\Sublime Text 3\\Packages\\se-mdk\\lib\\mdkmin.exe")
                print(path_to_exe)

        print("running {} on in: {} and out: {}".format(path_to_exe, input_file, output_file))
        self.proc = subprocess.Popen([path_to_exe, input_file, output_file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self.build_dir, startupinfo=info)
        self.killed = False

        def kill():
            self.log("Timeout - killing")
            subprocess.call(['taskkill', '/F', '/T', '/PID',  str(self.proc.pid)], startupinfo=info)

        t = threading.Timer(10.0, kill)
        t.start()
        stdout, stderr = self.proc.communicate()
        t.cancel()
        self.log(stdout.decode(self.encoding).replace(self.build_dir, self.manifest_dir))

        if self.proc.returncode == 0:
            self.log("Minification complete")
        else:
            self.log("Minification failed ({})".format(self.proc.returncode))
            self.show_errors()


        return self.proc.returncode

    def process_file(self, handle, fone):
        chunk_size = 2 ** 13
        out = b''
        while True:
            try:
                data = os.read(handle.fileno(), chunk_size)
                out += data
                if len(data) == chunk_size:
                    continue
                if data == b'' and out == b'':
                    raise IOError('EOF')
                self.queue_write(out.decode(self.encoding))
                if data == b'':
                    raise IOError('EOF')
                out = b''

            except (UnicodeDecodeError) as e:
                self.queue_write('Error decoding output using {} - {}'.format(self.encoding, str(e)))
                break

            except (IOError):
                if self.killed:
                    self.queue_write('\n[Cancelled]')
                else:
                    self.queue_write('\n[Finished]')
                break

    def queue_write(self, text):
        sublime.set_timeout(lambda: self.log(text.replace(self.build_dir, self.manifest_dir)), 1)

    def is_enabled(self, kill=False):
        if kill:
            return self.proc is not None and self.proc.poll() is None
        return True

    def hide_errors(self):
        global error_regions
        self.hide_phantoms()
        self.window.active_view().erase_regions("syntacticDiag")
        error_regions = []

    def show_errors(self):
        global errs_by_file
        self.hide_errors()

        preferences = sublime.load_settings("Preferences.sublime-settings")
        errs = self.panel.find_all_results_with_text()

        errs_by_file = {}
        for file, line, column, text in errs:
            if file not in errs_by_file:
                errs_by_file[file] = []
            errs_by_file[file].append((line, column, text))

        self.write_squigglies()

        if preferences.get("show_errors_inline", True):
            self.update_phantoms()

    def write_squigglies(self):
        global errs_by_file
        global error_regions

        for file, errs in errs_by_file.items():
            view = self.window.find_open_file(file)

            if view:
                regions = []

                for line, column, text in errs:
                    pt = view.text_point(line - 1, column - 1)
                    region = sublime.Region(pt, view.line(pt).b)
                    regions.append(region)
                    error_regions.append((region, (text, line, column)))

                view.add_regions("syntacticDiag", regions, "invalid.illegal", "", error_style)

    def on_phantom_navigate(self, url):
        self.hide_phantoms()

    def hide_phantoms(self):
        global errs_by_file

        for file, errs in errs_by_file.items():
            view = self.window.find_open_file(file)
            if view:
                view.erase_phantoms("exec")

        errs_by_file = {}
        self.phantom_sets_by_buffer = {}
        self.show_errors_inline = False

    def update_phantoms(self):
        stylesheet = '''
            <style>
                div.error-arrow {
                    border-top: 0.4rem solid transparent;
                    border-left: 0.5rem solid color(var(--redish) blend(var(--background) 30%));
                    width: 0;
                    height: 0;
                }
                div.error {
                    padding: 0.4rem 0 0.4rem 0.7rem;
                    margin: 0 0 0.2rem;
                    border-radius: 0 0.2rem 0.2rem 0.2rem;
                }

                div.error span.message {
                    padding-right: 0.7rem;
                }

                div.error a {
                    text-decoration: inherit;
                    padding: 0.35rem 0.7rem 0.45rem 0.8rem;
                    position: relative;
                    bottom: 0.05rem;
                    border-radius: 0 0.2rem 0.2rem 0;
                    font-weight: bold;
                }
                html.dark div.error a {
                    background-color: #00000018;
                }
                html.light div.error a {
                    background-color: #ffffff18;
                }
            </style>
        '''

        for file, errs in errs_by_file.items():
            view = self.window.find_open_file(file)

            if view:
                buffer_id = view.buffer_id()
                if buffer_id not in self.phantom_sets_by_buffer:
                    phantom_set = sublime.PhantomSet(view, "exec")
                    self.phantom_sets_by_buffer[buffer_id] = phantom_set
                else:
                    phantom_set = self.phantom_sets_by_buffer[buffer_id]

                phantoms = []

                for line, column, text in errs:
                    pt = view.text_point(line - 1, column - 1)
                    phantoms.append(sublime.Phantom(
                        sublime.Region(pt, view.line(pt).b),
                        ('<body id=inline-error>' + stylesheet +
                            '<div class="error-arrow"></div><div class="error">' +
                            '<span class="message">' + html.escape(text, quote=False) + '</span>' +
                            '<a href=hide>' + chr(0x00D7) + '</a></div>' +
                            '</body>'),
                        sublime.LAYOUT_BELOW,
                        on_navigate=self.on_phantom_navigate))

                phantom_set.update(phantoms)

class SeMdkEventListener(sublime_plugin.ViewEventListener):
    def is_csharp(self):
        if len(self.view.sel()) == 0:
            return False

        location = self.view.sel()[0].begin()

        return self.view.match_selector(location, 'source.cs')

    def on_hover(self, point, hover_zone=sublime.HOVER_TEXT):
        if not self.is_csharp():
            return

        global error_regions

        for region, data in error_regions:
            if region.contains(point):
                self.on_hover_error(self.view, data, point)

    def on_hover_error(self, view, data, point):
        if not self.is_csharp():
            return

        text, line, col = data
        view.show_popup(
            "<span>{0}</span>".format(text),
            flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
            location=point,
            max_height=300,
            max_width=view.viewport_extent()[0]
            # on_navigate=self.view.erase_regions("syntacticDiag")
        )

    # def on_modified(self):
    #     if not self.is_csharp():
    #         return

    #     self.view.erase_regions("syntacticDiag")
