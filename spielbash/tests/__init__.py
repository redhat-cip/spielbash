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


from unittest import TestCase
import mock
import subprocess

import spielbash


class TestSpielbash(TestCase):
    def test_TmuxSendKeys(self):
        with mock.patch('subprocess.Popen') as popen:
            session, cmd = ('test_session', 'abcd')
            spielbash.TmuxSendKeys(session, cmd)
            p_call = "tmux send-keys -t %s %s" % (session, cmd)
            popen.assert_called_with(p_call.split(' '),
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)

    def _test_BaseAction(self, action, discard):
        session = 'test_session'
        ba = spielbash.BaseAction()
        with mock.patch('subprocess.Popen') as popen:
            ba.emulate_typing(action, session, discard=discard)
            calls = []
            for char in action:
                if char == ' ':
                    char = 'Space'
                p_call = "tmux send-keys -t %s %s" % (session, char)
                calls.append(mock.call(p_call.split(' '),
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE))
                calls.append(mock.call().wait())
            if discard:
                for char in action:
                    cmd = "tmux send-keys -t %s %s" % (session, 'C-h')
                    calls.append(mock.call(cmd.split(' '),
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE))
                    calls.append(mock.call().wait())
            popen.assert_has_calls(calls)

    def test_BaseAction(self):
        self._test_BaseAction(action="azertyyuiop", discard=False)
        self._test_BaseAction(action="azertyyuiop", discard=True)
        self._test_BaseAction(action="Hello World", discard=False)
        self._test_BaseAction(action="Hello World", discard=True)
