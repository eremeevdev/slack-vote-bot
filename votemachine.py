# -*- coding: utf-8 -*-
import time
import json
from collections import Counter
from slackclient import SlackClient

import settings


class BaseVoteState:

    def __init__(self, vote_machine):
        self.vote_machine = vote_machine

    def start_vote(self, vote_name, choices):
        return u'Чтобы начать новое голосование необходимо завершить текущее'

    def stop_vote(self):
        return u'Чтобы остановить голосование его нужно сначала начать'

    def vote(self, user, value):
        return u'Нет запущенного голосования'

    def stat(self):
        return u'Нет запущенного голосования'


class VoteWaitState(BaseVoteState):

    def start_vote(self, vote_name, choices):

        active_state = self.vote_machine.get_vote_active_state()
        self.vote_machine.set_state(active_state)

        return self.vote_machine._start_vote(vote_name, choices)


class VoteActiveState(BaseVoteState):

    def vote(self, user, value):
        return self.vote_machine._vote(user, value)

    def stop_vote(self):

        wait_state = self.vote_machine.get_vote_wait_state()
        self.vote_machine.set_state(wait_state)

        return self.vote_machine._stat()

    def stat(self):
        return self.vote_machine._stat()


class VoteMachine:

    def __init__(self):

        self.vote_wait_state = VoteWaitState(self)
        self.vote_active_state = VoteActiveState(self)
        self.state = self.vote_wait_state

        self.vote_name = None
        self.choices = []
        self.votes = {}

    # getters and setter

    def get_vote_wait_state(self):
        return self.vote_wait_state

    def get_vote_active_state(self):
        return self.vote_active_state

    def set_state(self, state):
        self.state = state

    # vote logic

    def _start_vote(self, vote_name, choices):

        self.vote_name = vote_name
        self.choices = choices
        self.votes = {}

        return 'ok'

    def _stat(self):

        vote_stat = Counter()

        for user, value in self.votes.items():
            vote_stat[value] += 1

        messages = []
        messages.append(self.vote_name)

        for choice in self.choices:
            count = vote_stat.get(choice, 0)
            messages.append(u'{}: {}'.format(choice, count))

        return '\n'.join(messages)

    def _vote(self, user, value):

        try:
            index = int(value)
            value = self.choices[index]

        except IndexError:
            return u'неверное значение'

        except ValueError:
            pass

        if value not in self.choices:
            return u'неверное значение'

        self.votes[user] = value

        return 'ok'

    # public methods

    def start_vote(self, vote_name, choices):
        return self.state.start_vote(vote_name, choices)

    def stop_vote(self):
        return self.state.stop_vote()

    def vote(self, user, value):
        return self.state.vote(user, value)

    def stat(self):
        return self.state.stat()


class VoteBot:

    def __init__(self, token, vote_machine):

        self.token = token

        self.sc = SlackClient(self.token)
        self.sc.rtm_connect()

        self.vote_machine = vote_machine

    def messages(self):

        while True:

            response = self.sc.rtm_read()

            if response:

                for data in response:
                    if 'type' in data and data['type'] == 'message':
                        yield data

            time.sleep(1)

    def process_message(self, data):

        lines = data['text'].split(u'\n')

        command = lines[0].split()

        response = None

        if command[0] == 'vote' and len(command) == 1:

            response = u'Чтобы начать голосование:\n' \
                       u'vote start [название]\n' \
                       u'вариант1\nвариант2\nвариант 3\n\n' \
                       u'Чтобы проголосовать:\n' \
                       u'vote вариант1 или vote 0\n\n' \
                       u'Посмотреть статистику: vote stat\n\n' \
                       u'Остановить голосование: vote stop'

        elif command[0] == 'vote' and command[1] == 'start':

            if len(lines) > 1:

                vote_name = ' '.join(command[2:])
                choices = lines[1:]

                response = self.vote_machine.start_vote(vote_name, choices)

            else:
                response = u'необходимо указать варианты'

        elif command[0] == 'vote' and command[1] == 'stop':

            response = self.vote_machine.stop_vote()

        elif command[0] == 'vote' and command[1] == 'stat':

            response = self.vote_machine.stat()

        elif command[0] == 'vote' and len(command) > 1:

            value = ' '.join(command[1:])

            response = self.vote_machine.vote(data['user'], value)

        if not response:
            return

        info = self.sc.api_call('users.info', user=data['user'])
        info = json.loads(info)
        user_name = info['user']['name']

        response = u'@{} {}'.format(user_name, response)

        self.sc.rtm_send_message(data['channel'], response)

    def run(self):

        for data in self.messages():
            self.process_message(data)


if __name__ == '__main__':

    vote_machine = VoteMachine()

    vote_bot = VoteBot(settings.API_TOKEN, vote_machine)
    vote_bot.run()
