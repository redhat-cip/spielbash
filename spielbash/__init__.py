#!/usr/bin/env python
#
# Copyright (C) 2016 Red Hat
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
# -*- coding: utf-8 -*-

import argparse
import json
import pipes
import re
import subprocess
import sys
import time
import yaml


# TODO should be settable
READING_TIME = 2
TYPING_SPEED = 0.1


def pause(t):
    time.sleep(t)


def is_process_running_in_tmux(session):
    """Find out whether there is a process currently running or not in tmux"""
    # since processes are launched as bash -c 'xx yy zz' the only pid
    # we can get at first is the one of the bash process.
    cmd = 'tmux list-panes -a -F #{pane_pid} -t %s' % session
    father = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
    father = father.stdout.readlines()[0].strip('\n')
    # then we just check whether this process still has children:
    cmd = 'pgrep -P %s' % father
    child = subprocess.Popen(cmd.split(' '), stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    child = child.stdout.readlines()
    if child:
        return child[0].strip('\n')
    return False


class Command(object):
    def __init__(self, cmd):
        if not isinstance(cmd, list):
            self.cmd = cmd.split(' ')
        else:
            self.cmd = cmd
        self.process = subprocess.Popen(self.cmd, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)

    @property
    def output(self):
        self.process.wait()
        return (self.process.stdout, self.process.stderr)

    def communicate(self, input):
        return self.process.communicate(input)


class TmuxSendKeys(Command):
    def __init__(self, tmux_session, keys):
        cmd = "tmux send-keys -t %s %s" % (tmux_session, keys)
        super(TmuxSendKeys, self).__init__(cmd)


class BaseAction:
    def emulate_typing(self, line, session, discard=False):
        for char in line:
            if char == ' ':
                char = 'Space'
            tmux = TmuxSendKeys(session, char)
            # wait for execution
            tmux.output
            pause(TYPING_SPEED)
        pause(READING_TIME)
        if discard:
            for char in line:
                tmux = TmuxSendKeys(session, 'C-h')
                tmux.output
                pause(TYPING_SPEED)

    def send_enter(self, session):
        tmux = TmuxSendKeys(session, 'C-m')
        # wait for execution
        tmux.output


class PressKey:
    def __init__(self, key, session):
        self.key = {'ENTER': 'C-m',
                    'BACKSPACE': 'C-h'}.get(key.upper(), 'C-m')
        self.session = session

    def run(self):
        tmux = TmuxSendKeys(self.session, self.key)
        tmux.output


class Dialogue(BaseAction):
    def __init__(self, line, session):
        self.line = line
        self.session = session

    def run(self):
        self.emulate_typing(self.line, self.session, discard=True)


class Scene(BaseAction):
    def __init__(self, name, cmd, session, keep, movie,
                 wait_for_execution, *args, **kwargs):
        self.name = name
        self.cmd = cmd
        self.session = session
        self.original_buffer = self._get_buffer().strip('\n')
        self.output = None
        self.movie = movie
        self.wait_for_execution = wait_for_execution
        self.to_keep = dict((u['var'],
                             re.compile(u['regex'], re.M)) for u in keep)

    def _get_buffer(self):
        capture_cmd = ['tmux', 'capture-pane', '-S', '-', '-t', self.session]
        capture = subprocess.Popen(capture_cmd,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        capture.wait()
        buffer = subprocess.Popen(['tmux', 'show-buffer'],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE).communicate()[0]
        return buffer

    def run(self):
        # replace vars if needed
        for var in self.movie.vars:
            if var in self.cmd:
                self.cmd = self.cmd.replace(var, self.movie.vars[var])
        self.emulate_typing(self.cmd, self.session, discard=False)
        self.send_enter(self.session)
        if self.wait_for_execution:
            while is_process_running_in_tmux(self.session):
                pause(0.1)
        # output will be after the sent command. Remove old buffer first:
        b = self._get_buffer()[len(self.original_buffer):]
        self.output = b.split(self.cmd)[-1].strip('\n')
        for var, regex in self.to_keep.items():
            match = regex.findall(self.output)
            if match:
                # TODO support multiple outputs
                self.movie.vars[var] = match[0]


class Movie:
    def __init__(self, name, script, output_file):
        self.script = script
        self.session_name = name
        self.output_file = output_file
        self.reel = None
        self.vars = {}

    def shoot(self):
        """shoot the movie."""
        self.reel = Command('tmux new-session -d -s %s' % self.session_name)
        # start filming
        asciinema_cmd = 'asciinema rec -c "tmux attach -t %s" -y'
        if self.script.get('title'):
            asciinema_cmd += ' -t %s' % pipes.quote(self.script.get('title'))
        asciinema_cmd += ' %s'
        movie = subprocess.Popen(asciinema_cmd % (self.session_name,
                                                  self.output_file),
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 shell=True)
        # pause to make sure asciinema is ready
        pause(0.4)
        for scene in self.script['scenes']:
            print "Rolling scene \"%s\"..." % scene['name'],
            s = None
            if 'action' in scene:
                s = Scene(scene['name'], scene.get('action', ''),
                          self.session_name,
                          scene.get('keep', {}), self,
                          wait_for_execution=scene.get('wait', False))
            elif 'line' in scene:
                s = Dialogue(scene['line'], self.session_name)
            elif 'press_key' in scene:
                s = PressKey(scene['press_key'], self.session_name)
            elif 'pause' in scene:
                pause(scene.get('pause', 1))
                s = None
            else:
                sys.exit(1)
            if s:
                s.run()
            print " Cut !"
            pause(READING_TIME)
        TmuxSendKeys(self.session_name, 'exit')
        TmuxSendKeys(self.session_name, 'C-m')
        self.reel.communicate('exit')
        out, err = movie.communicate()
        return out, err


def main():
    parser = argparse.ArgumentParser(description="spielbash CLI")
    parser.add_argument('--script', metavar='RaidersOfTheLostArk.yaml',
                        help='The script to execute with asciinema',
                        required=True)
    parser.add_argument('--output', metavar='RaidersOfTheLostArk.json',
                        help='where to record the movie',
                        required=False, default='movie.json')
    args = parser.parse_args()
    script_file = args.script
    output_file = args.output
    try:
        with open(script_file, 'r') as s:
            script = yaml.load(s)
    except Exception as e:
        sys.exit('There was a problem with loading the script: %s' % e)
    movie = Movie('howdy', script, output_file)
    # CAMERAS, LIGHTS AAAAAAAND ACTION !
    out, err = movie.shoot()
    if err:
        print err
    else:
        # set default width and height
        with open(output_file, 'r') as m:
            j = json.load(m)
        if not j.get('width'):
            j['width'] = 80
        if not j.get('height'):
            j['height'] = 25
        with open(output_file, 'w') as m:
            json.dump(j, m)
        print "movie recorded as %s" % output_file
        print "to replay: asciinema play %s" % output_file
        print "to upload: asciinema upload %s" % output_file


if __name__ == '__main__':
    main()
