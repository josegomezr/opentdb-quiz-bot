#!/usr/bin/env python

from config import BOT_TOKEN

import logging
import re
import textwrap
import math
import random
from time import sleep

import requests
import telegram

from telegram.ext import Updater, CommandHandler, MessageHandler, filters
from telegram.error import NetworkError, Unauthorized


class GameState(object):
    def __init__(self, in_game=False, question="question", question_type='multiple', answer="CORRECT", chat_id=-1
        ):
        self.in_game = in_game
        self._question = question
        self.answer = answer
        self.question_type = question_type
        self.chat_id = chat_id
        self.reply_count = 0
        self.reply_max = 4
        self.random = random.Random(chat_id)
        self._clue = ' '.join(map(lambda x: '_'*len(x), self.answer.split(' ')))

    def tick(self):
        self.reply_count += 1
        return self

    @property
    def question(self):
        if self.question_type == 'boolean':
            return self._question[0:-1] + '?'
        return self._question

    @staticmethod
    def sanitize(input_str):
        return re.sub(r"[^\w ]", "", input_str).strip()

    def valid_answer(self, prompted_answer):
        regex = "{}"

        if self.question_type == 'boolean':
            alternative = "yes" if self.answer == "True" else "no"
            regex += "|" + alternative

        regex = regex.format(re.escape(self.sanitize(self.answer)))
        saned_answer = self.sanitize(prompted_answer)

        print(regex, saned_answer)
        return bool(re.search(regex, saned_answer, re.I))

    @property
    def clue(self):
        t = sum(map(lambda x: len(x), self.answer.split(' ')))

        if self.reply_count == 0:
            return self._clue

        rendered = list(self._clue)
        clues = math.floor((float(t)/(self.reply_max+1)) * self.reply_count)
        while clues > 0:
            i = self.random.randint(0, t-1)
            rendered[i] = self.answer[i]
            clues -= 1
        self._clue = ''.join(rendered)
        return self._clue


def new_game_state(chat_id):
    question = requests.get('https://opentdb.com/api.php?amount=1&difficulty=easy').json()['results'][0]

    state = GameState(
        in_game=True,
        question_type=question['type'],
        chat_id=chat_id,
        question=question['question'],
        answer=question['correct_answer']
    )

    logging.info("question: {}\nanswer: {}\n".format(state.question, state.answer))

    return state


def quiz(context):
    job = context.job
    state = job.context

    logging.info("[%s] reply_count=%s question='%s' answer='%s'", state.chat_id, state.reply_count, state.question, state.answer)

    if not state.in_game:
        return

    msg = textwrap.dedent("""
        ❓: {0}

        {1}
    """).format(state.question, state.clue)
    state.tick()

    try:
        context.bot.send_message(state.chat_id, text=msg, parse_mode='HTML')

        delay = state.reply_count * 8
        callback = quiz
        if state.reply_count >= state.reply_max:
            callback = failed
        context.job_queue.run_once(callback, delay, context=state)
    except Unauthorized:
        state.in_game = False


def failed(context):
    job = context.job
    state = job.context

    if not state.in_game:
        return

    msg = textwrap.dedent("""
        ❌ Nobody guessed it!

        Question: *{0}*
        Answer: *{1}*
    """).format(state.question, state.answer)

    try:
        context.bot.send_message(state.chat_id, text=msg, parse_mode='MARKDOWN')

        state = new_game_state(state.chat_id)
        context.dispatcher.chat_data[state.chat_id]['game_state'] = state
        context.job_queue.run_once(quiz, 1, context=state)
    except Unauthorized:
        state.in_game = False


def stop(update, context):
    state = context.chat_data.get('game_state')
    if not state or not state.in_game:
        return
    state.in_game = False
    context.chat_data['game_state'] = None

    try:
        context.bot.send_message(state.chat_id, text='🛑 Stopped', parse_mode='MARKDOWN')
    except Unauthorized:
        pass


def next_question(update, context):
    state = context.chat_data.get('game_state')
    if not state or not state.in_game:
        return
    state.in_game = False
    context.chat_data['game_state'] = None

    try:
        context.bot.send_message(state.chat_id, text='Next Question!!!', parse_mode='MARKDOWN')

        state = new_game_state(state.chat_id)
        context.chat_data['game_state'] = state
        context.job_queue.run_once(quiz, 1, context=state)
    except Unauthorized:
        state.in_game = False


def start_new(update, context):
    chat_id = update.message.chat_id

    state = context.chat_data.get('game_state')

    if state and state.in_game:
        update.message.reply_markdown("Already in a game")
        return

    try:
        update.message.reply_text("Let's start!")
        logging.info("(Fetching question from api)")

        state = new_game_state(chat_id)
        context.chat_data['game_state'] = state

        context.job_queue.run_once(quiz, 1, context=state)
    except Unauthorized:
        state.in_game = False


def answer(update, context):
    chat_id = update.message.chat_id
    state = context.chat_data.get('game_state')

    if not state:
        return

    prompted_answer = update.message.text.lower()

    if not state.in_game:
        return

    valid = state.valid_answer(prompted_answer)

    logging.info("[%s] reply_count=%s question='%s' answer='%s' prompt='%s' valid='%s'", state.chat_id, state.reply_count, state.question, state.answer, prompted_answer, valid)

    if not valid:
        return

    answer = state.answer

    if state.question_type == 'boolean':
        answer = state.answer + ("/yes" if state.answer == "True" else "/no")

    state.in_game = False
    msg = textwrap.dedent("""
        ✅ *{1}* nailed it! The answer is *{0}*
    """).format(answer, update.message.from_user.first_name)

    try:
        update.message.reply_markdown(msg, quote=True)

        state = new_game_state(chat_id)
        context.chat_data['game_state'] = state
        context.job_queue.run_once(quiz, 1, context=state)
    except Unauthorized:
        state.in_game = False


def error(update, context):
    """Log Errors caused by Updates."""
    logging.warning('Update "%s" caused error "%s"', update, context.error)

def start(update, context):
    """Log Errors caused by Updates."""
    try:
        update.message.reply_text(
            textwrap.dedent("""
                /start - ashura
                /new   - empezar
                /stop  - terminar
                /next  - OTRA!
                """
            )
        )
    except Unauthorized:
        pass


def main():
    """Run the bot."""
    # Telegram Bot Authorization Token
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    dp.add_handler(CommandHandler("next", next_question))
    dp.add_handler(CommandHandler("new", start_new))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(filters.Filters.text, answer))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
