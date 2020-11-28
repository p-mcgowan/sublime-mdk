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
    working_dir = None
    file_regex = None
    panel = None
    encoding = None
    build_dir = None
    output = None
    main = None
    files = None
    thumb = None

    def run(self, **kwargs):
        try:
            if not self.import_settings():
                return 1

            targets = self.collect_build_files()
            if targets is None:
                self.log("No files to build")
                return 1

            self.log("will build: \n  {}".format("\n  ".join(targets)))
            self.build(targets)

        except Exception as Argument:
            self.log(traceback.format_exc())

    def build(self, targets):
        self.log("building")
        out_path = os.path.realpath(self.build_dir)
        shutil.rmtree(out_path, ignore_errors=True)

        def to_build_dir(full_path):
            shared_root = os.path.commonprefix([out_path, full_path])
            return full_path.replace(shared_root, '')

        head = os.path.join(self.mdk_root, 'lib/head.cs')
        tail = os.path.join(self.mdk_root, 'lib/tail.cs')

        # wrap and copy to build
        for target in targets:
            out_file = os.path.join(out_path, to_build_dir(target))
            try:
                os.makedirs(os.path.dirname(out_file))
            except Exception:
                pass

            self.log(out_file)
            with open(out_file, 'wb') as out_fd:
                for f in [head, target, tail]:
                    with open(f, 'rb') as in_fd:
                        shutil.copyfileobj(in_fd, out_fd)

    def collect_build_files(self):
        files = {}
        output = os.path.realpath(self.output)
        main = os.path.realpath(self.main)
        build_dir = os.path.realpath(self.build_dir)

        def add_file(file_path):
            filename = os.path.realpath(file_path)
            _, file_extension = os.path.splitext(filename)
            if (
                file_extension != '.cs' or
                filename == output or
                filename == main or
                filename == build_dir
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
        if os.path.isfile(main):
            targets.insert(0, main)

        return targets if len(targets) else None

    def import_settings(self):
        window_vars = self.window.extract_variables()
        self.working_dir = window_vars['file_path']

        self.file_regex = "\\(.*\\.cs\\)\\(([\\d]+),([\\d]+)\\): (.*)"
        self.panel = self.window.create_output_panel("panel")

        preferences = sublime.load_settings('Preferences.sublime-settings')
        if preferences.get('show_panel_on_build'):
            self.window.run_command('show_panel', { "panel": "output.panel" })

        manifest = self.find_manifest()
        if manifest is None:
            return False

        self.encoding = manifest.get('encoding', 'utf-8')
        self.build_dir = manifest.get('build_dir', "{}/build".format(os.getcwd()))
        self.output = manifest.get('output', 'Script.cs')
        self.main = manifest.get('main', 'main.cs')
        self.files = manifest.get('files', '*')
        self.thumb = manifest.get('thumb', True)

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
                        return sublime.decode_value(settings.read())

            os.chdir('../')
            if os.getcwd() == here:
                self.log("No {} found from {} to {}".format(self.manifest_filename, self.working_dir, os.getcwd()))
                return None

    def log(self, msg, newline=True):
        if self.panel is not None:
            self.panel.run_command("append", {
                "characters": "{}{}".format(msg, "\n" if newline else None)
            })


#         scope = self.view.scope_name(self.view.sel()[-1].b)

#         html = """
# <style>
# body { margin: 0 8; }
# </style>
# <p>%s</p><p><a href="%s">Copy</a></p>
# """ % (scope.replace(' ', '<br>'), scope.rstrip())

#         self.view.show_popup(html, on_navigate=lambda x: copy(self.view, x))
