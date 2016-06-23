#!/usr/bin/env python

import argparse
import json
import subprocess
import sys
import time
import yaml


# TODO should be settable
READING_TIME = 2
TYPING_SPEED = 0.1


def pause(t):
    time.sleep(t)


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


class Dialogue(BaseAction):
    def __init__(self, line, session):
        self.line = line
        self.session = session

    def run(self):
        self.emulate_typing(self.line, self.session, discard=True)


class Scene(BaseAction):
    def __init__(self, name, cmd, session, *args, **kwargs):
        self.name = name
        self.cmd = cmd
        self.session = session
        self.original_buffer = self._get_buffer().strip('\n')
        self.output = None

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
        self.emulate_typing(self.cmd, self.session, discard=False)
        self.send_enter(self.session)
        # output will be after the sent command. Remove old buffer first:
        b = self._get_buffer()[len(self.original_buffer):]
        self.output = b.split(self.cmd)[-1].strip('\n')


class Movie:
    def __init__(self, name, script, output_file):
        self.script = script
        self.session_name = name
        self.output_file = output_file
        self.reel = None

    def shoot(self):
        """shoot the movie."""
        self.reel = Command('tmux new-session -d -s %s' % self.session_name)
        # start filming
        asciinema_cmd = 'asciinema rec -c "tmux attach -t %s" -y %s'
        movie = subprocess.Popen(asciinema_cmd % (self.session_name,
                                                  self.output_file),
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 shell=True)
        for scene in self.script['scenes']:
            print "Rolling scene \"%s\"..." % scene['name'],
            if 'action' in scene:
                s = Scene(scene['name'], scene['action'], self.session_name)
            elif 'line' in scene:
                s = Dialogue(scene['line'], self.session_name)
            else:
                sys.exit(1)
            s.run()
            print " Cut !"
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
