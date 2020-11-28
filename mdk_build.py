import sublime
import sublime_plugin

import os
import subprocess
import threading

import re
import glob
import json
import shutil
import traceback
from datetime import datetime

# def copy(view, text):
#     sublime.set_clipboard(text)
#     view.hide_popup()
#     sublime.status_message('Scope name copied to clipboard')
# self.win_temp = manifest.get('win_temp', '/mnt/c/Users/mcgow/AppData/Local/Temp')
# self.mdk_root = manifest.get('mdk_root', '$(cd $(dirname $0)/.. && pwd)')
# self.mdk_root_win = manifest.get('mdk_root_win', '$(wslpath -w $mdk_root)')
# self.compileFiles = manifest.get('compileFiles', '()')

# cmd = "path to the .exe file " + view.fileName()
#       view.window().runCommand("exec","",cmd])

class MdkBuildCommand(sublime_plugin.WindowCommand):
    mdk_root = os.path.dirname(os.path.abspath(__file__))
    manifest_filename = 'mdk.sublime-settings'
    panel = None
    manifest_dir = None
    manifest_dir = None
    file_regex = None
    encoding = None
    build_dir = None
    output = None
    main = None
    files = None
    thumb = None
    se_game_dir = None

    panel_lock = threading.Lock()
    killed = False
    proc = None
    encoding = 'utf-8'

    def run(self, **kwargs):
        try:
            self.build()

        except:
            self.log(traceback.format_exc())

    def build(self):
        if not self.import_settings():
            return 1

        targets = self.collect_build_files()
        if targets is None:
            self.log("No files to build")
            return 1

        compile_files = self.prepare(targets)
        self.log("\n".join(compile_files))
        bat_file = self.compile(compile_files)
        exitcode = self.run_bat(bat_file)

        if exitcode == 0:
            self.onSuccess(targets)
            self.log('Build success')
        else:
            self.log('Build failed')

    def setup_build_panel(self, working_dir=None):
        if working_dir == None:
            working_dir = self.manifest_dir

        with self.panel_lock:
            self.panel = self.window.create_output_panel("panel")
            settings = self.panel.settings()
            settings.set('result_file_regex', r"^(.*\.cs)\((\d*),(\d*)\): .*")
            settings.set('result_line_regex', r"^(.*\.cs)\((\d*),(\d*)\): .*")
            settings.set('result_base_dir', self.working_dir)

            preferences = sublime.load_settings('Preferences.sublime-settings')
            if preferences.get('show_panel_on_build'):
                self.window.run_command('show_panel', { "panel": "output.panel" })

    def compile(self, files):
        bat_out = os.path.join(self.build_dir, "compile.bat")
        bat_tpl = os.path.join(self.mdk_root, 'MDK/compile.bat')

        try:
            os.remove(bat_out)
        except:
            pass

        with open(bat_out, "a") as bat_file:
            with open(bat_tpl, "r") as bat_head:
                content = " ".join(
                    bat_head.read().replace('MDK_ROOT', self.mdk_root)
                    .replace('SE_GAME_DIR', self.se_game_dir).split("\n")
                    )
                bat_file.write(content)

            bat_file.write('"{}"'.format('" "'.join(files)))

        return bat_out

    def onSuccess(self, files):
        for file in ['Bootstrapper.exe', 'compile.bat']:
            try:
                os.remove(os.path.join(self.build_dir, file))
            except:
                pass

        with open(self.output, 'wb') as out_fd:
            for f in files:
                with open(f, 'rb') as in_fd:
                    shutil.copyfileobj(in_fd, out_fd)

    def prepare(self, targets):
        shutil.rmtree(self.build_dir, ignore_errors=True)
        compile_files = []

        def to_build_dir(full_path):
            shared_root = os.path.commonprefix([self.build_dir, full_path])
            return full_path.replace(shared_root, '')

        with open(os.path.join(self.mdk_root, 'MDK/head.cs')) as head_file:
            head = head_file.read().rstrip()

        with open(os.path.join(self.mdk_root, 'MDK/tail.cs')) as tail_file:
            tail = tail_file.read().rstrip()

        for target in targets:
            out_file = os.path.join(self.build_dir, to_build_dir(target))

            try:
                os.makedirs(os.path.dirname(out_file))
            except Exception:
                pass

            with open(out_file, 'w') as output:
                output.write(head)
                with open(target) as in_fd:
                    output.write(in_fd.read())
                output.write(tail)

            compile_files.append(out_file)

        compile_files.reverse() # make main last

        return compile_files

    def collect_build_files(self):
        files = {}

        def add_file(file_path):
            filename = os.path.realpath(file_path)
            _, file_extension = os.path.splitext(filename)

            if (
                file_extension != '.cs' or
                filename == self.output or
                filename == self.main or
                filename == self.build_dir
                ):
                return

            files[filename] = True

        for part in re.split(r'\ *,+\ *', self.files):
            for file in glob.glob(part):
                if os.path.isdir(file):
                    for script in glob.glob("{}/**".format(file)):
                        add_file(script)
                else:
                    add_file(file)

        targets = list(files.keys())
        if os.path.isfile(self.main):
            targets.insert(0, self.main)

        return targets if len(targets) else None

    def import_settings(self):
        window_vars = self.window.extract_variables()
        self.working_dir = window_vars['file_path']

        self.setup_build_panel(self.working_dir)

        manifest = self.find_manifest()
        if manifest is None:
            return False

        settings = self.panel.settings()
        settings.set("result_base_dir", self.manifest_dir)
        self.encoding = manifest.get("encoding", "utf-8")
        self.build_dir = os.path.realpath(manifest.get("build_dir", "{}/build".format(os.getcwd())))
        self.output = os.path.realpath(manifest.get("output", "Script.cs"))
        self.main = os.path.realpath(manifest.get("main", "main.cs"))
        self.files = manifest.get("files", "*")
        self.thumb = manifest.get("thumb", True)
        self.se_game_dir = os.path.realpath(manifest.get("se_game_dir", "c:\\program files (x86)\\steam\\SteamApps\\common\\SpaceEngineers"))

        return True

    def find_manifest(self):
        os.chdir(self.working_dir)
        for i in range(100):
            here = os.getcwd()
            if os.path.isfile(self.manifest_filename):
                if here == self.mdk_root:
                    self.log("Refusing to build the plugin folder")
                    return None
                else:
                    with open(os.path.join(os.getcwd(), self.manifest_filename)) as settings:
                        self.manifest_dir = here
                        return sublime.decode_value(settings.read())

            os.chdir('../')
            if os.getcwd() == here:
                self.log("No {} found from {} to {}".format(self.manifest_filename, self.working_dir, os.getcwd()))
                return None

        os.chdir(self.manifest_dir)

    def log(self, msg, newline=True):
        if self.panel is not None:
            with self.panel_lock:
                self.panel.run_command("append", {
                    "characters": "{}{}".format(msg, "\n" if newline else None)
                })

    def run_bat(self, path_to_bat):
        if self.proc is not None:
            self.proc.terminate()
            self.proc = None

        SW_HIDE = 0
        info = subprocess.STARTUPINFO()
        info.dwFlags = subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = SW_HIDE

        self.proc = subprocess.Popen(
            path_to_bat,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self.build_dir,
            startupinfo=info
        )
        self.killed = False

        threading.Thread(target=self.read_handle, args=(self.proc.stdout,)).start()
        return self.proc.wait()

    def read_handle(self, handle):
        chunk_size = 2 ** 13
        out = b''
        while True:
            try:
                data = os.read(handle.fileno(), chunk_size)
                # If exactly the requested number of bytes was
                # read, there may be more data, and the current
                # data may contain part of a multibyte char
                out += data
                if len(data) == chunk_size:
                    continue
                if data == b'' and out == b'':
                    raise IOError('EOF')
                # We pass out to a function to ensure the
                # timeout gets the value of out right now,
                # rather than a future (mutated) version
                self.queue_write(out.decode(self.encoding))
                if data == b'':
                    raise IOError('EOF')
                out = b''

            except (UnicodeDecodeError) as e:
                self.queue_write('Error decoding output using {} - {}'.format(self.encoding, str(e)))
                break

            except (IOError):
                if self.killed:
                    msg = 'Cancelled'
                else:
                    msg = 'Finished'
                self.queue_write('\n[{}]'.format(msg))
                break

    def queue_write(self, text):
        sublime.set_timeout(lambda: self.log(text.replace(self.build_dir, self.manifest_dir)), 1)

    def is_enabled(self, lint=False, integration=False, kill=False):
        # The Cancel build option should only be available
        # when the process is still running
        if kill:
            return self.proc is not None and self.proc.poll() is None
        return True


#         scope = self.view.scope_name(self.view.sel()[-1].b)

#         html = """
# <style>
# body { margin: 0 8; }
# </style>
# <p>%s</p><p><a href="%s">Copy</a></p>
# """ % (scope.replace(' ', '<br>'), scope.rstrip())

#         self.view.show_popup(html, on_navigate=lambda x: copy(self.view, x))
