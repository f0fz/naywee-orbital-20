#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import requests
import json
import datetime
import telegram

from telegram.ext import Updater, Filters, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


# ConversationHandler states
TIMETABLE = range(1)


# User's timetable data
module_data = []
lesson_formatted = []


########## STATES ##########

def start(update, context):
    update.message.reply_text(main_menu_msg(),
                              reply_markup=main_menu_keyboard(),
                              parse_mode=ParseMode.MARKDOWN_V2)


# All state functions are appended with _page for consistency
def main_menu_page(update, context):
    query = update.callback_query
    query.edit_message_text(text=main_menu_msg(),
                            reply_markup=main_menu_keyboard(),
                            parse_mode=ParseMode.MARKDOWN_V2)


# "Send me your NUSMods timetable"
def timetable_page(update, context):
    query = update.callback_query
    query.edit_message_text(text=timetable_msg(),
                            parse_mode=ParseMode.MARKDOWN_V2)
    return TIMETABLE


# User input valid NUSMods timetable link
def timetable_input_page(update, context):
    update.message.reply_text("Syncing...")

    url = update.message.text
    semester = url.split('?')[0].split('-')[1][0]
    url = url.split('?')[1].split('&')
    module_data.clear()

    for data in url:
        data = data.split('=')
        data[1] = data[1].split(',')
        module_data.append(data)

    for data in module_data:
        for x in range(len(data[1])):
            data[1][x] = data[1][x].split(':')
            lesson_type = data[1][x][0]
            if lesson_type == "LEC":
                data[1][x][0] = "Lecture"
            elif lesson_type == "TUT":
                data[1][x][0] = "Tutorial"
            elif lesson_type == "REC":
                data[1][x][0] = "Recitation"
            elif lesson_type == "LAB":
                data[1][x][0] = "Laboratory"
            elif lesson_type == "SEC":
                data[1][x][0] = "Sectional Teaching"

    for i in range(len(module_data)):
        page = requests.get('https://api.nusmods.com/v2/2019-2020/modules/' + module_data[i][0] + '.json')
        page_py = json.loads(page.text)
        for x in page_py["semesterData"][int(semester) - 1]["timetable"]:
            for j in range(len(module_data[i][1])):
                if x["classNo"] == module_data[i][1][j][1] and x["lessonType"] == module_data[i][1][j][0]:
                    l_id = module_data[i][0] + "=" + module_data[i][1][j][0] + ":" + module_data[i][1][j][1]
                    days = x["day"]
                    venues = x["venue"]
                    periods = x["startTime"] + "-" + x["endTime"]
                    data_to_post = dict(l_id=l_id, days=days, venues=venues, periods=periods)
                    # requests.post("https://nusmods-tb-website.herokuapp.com/api/lessons", data=data_to_post)
                    lesson_formatted.append(data_to_post)

    update.message.reply_text(timetable_input_msg(),
                              reply_markup=return_keyboard(),
                              parse_mode=ParseMode.MARKDOWN_V2)

    return ConversationHandler.END


# User input invalid link
def invalid_input_page(update, context):
    update.message.reply_text(invalid_input_msg(),
                              parse_mode=ParseMode.MARKDOWN_V2)
    return TIMETABLE


# User types /cancel
def cancel_page(update, context):
    update.message.reply_text(cancel_msg(),
                              reply_markup=return_keyboard(),
                              parse_mode=ParseMode.MARKDOWN_V2)
    return ConversationHandler.END


# "Change settings"
def settings_page(update, context):
    query = update.callback_query
    query.edit_message_text(text=settings_msg(),
                            reply_markup=return_keyboard(),
                            parse_mode=ParseMode.MARKDOWN_V2)


# "Learn more"
def help_page(update, context):
    query = update.callback_query
    query.edit_message_text(text=help_msg(),
                            reply_markup=return_keyboard(),
                            parse_mode=ParseMode.MARKDOWN_V2)


# List all modules added by the user
def list_module_page(update, context):
    query = update.callback_query
    if len(module_data) == 0:
        text = "No modules added yet!"
        query.edit_message_text(text,
                                reply_markup=return_keyboard())
    else:
        text = "Here is the list of your modules:\n\n"
        for data in module_data:
            text = text + data[0] + "\n"
        query.edit_message_text(text,
                                reply_markup=return_keyboard())


########## KEYBOARDS ##########

# All functions here are appended with _keyboard for consistency
def main_menu_keyboard():
    keyboard = [[InlineKeyboardButton("Sync timetable",
                                      callback_data='sync')],
                [InlineKeyboardButton("Change settings",
                                      callback_data='settings')],
                [InlineKeyboardButton("Learn more about me",
                                      callback_data='help')],
                [InlineKeyboardButton("List my module(s)",
                                      callback_data='list')]]
    return InlineKeyboardMarkup(keyboard)


# Keyboard that returns user to main page
def return_keyboard():
    keyboard = [[InlineKeyboardButton('Return to main page', callback_data='main')]]
    return InlineKeyboardMarkup(keyboard)


########## MESSAGES ##########

# All functions here are appended with _msg for consistency
def main_menu_msg():
    return ("*Hi there\! I am the NUSMods Telebot\.*\nIf it is your first time using this bot, please select "
            "'Learn more' below to learn what I can do for you\.")


def timetable_msg():
    return ("*Timetable page:*\nSend me a link to your NUSMods timetable for me to sync\!")


def timetable_input_msg():
    return ("Your timetable is now synced\! Type \/reminder to start receving reminders\.")


def invalid_input_msg():
    return ("Invalid input\! Please send me a url link instead\. Enter \/cancel to go back to the main page\.")


def cancel_msg():
    return ("Action cancelled\.")


def settings_msg():
    return ("*Settings page:*\n"
            "I can't do anything yet\! Go back\!")


def help_msg():
    return ("*Hi\! I am NUSMods Telebot\.*\n\nBy sending me the link to your NUSMods timetable, I can link "
            "myself up with NUSMods’ data to send you reminders on lesson timings and venues\. If there is "
            "a change in your timetable, simply send your timetable link to me again\!\n\nI will send you daily "
            "reminders by default, but you can disable and then subsequently restart certain reminders if you "
            "wish\. You can also create custom reminders and change the frequency of your reminders\.\n\nYou can "
            "view announcements given by your faculty members through me as well\!")


########## HANDLERS ##########

def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    updater = Updater(os.environ['TELE_TOKEN'], use_context=True)
    job_queue = updater.job_queue
    dispatcher = updater.dispatcher

    timetable_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(timetable_page, pattern='sync')],
        states={TIMETABLE: [MessageHandler(Filters.regex(r'https:\/\/nusmods\.com(.*)'), timetable_input_page),
                            MessageHandler(Filters.all & ~Filters.command, invalid_input_page)]},
        fallbacks=[CommandHandler('cancel', cancel_page),
                   CommandHandler('start', cancel_page)]
    )

    def reminders(update: telegram.Update, context: telegram.ext.CallbackContext):
        update.message.reply_text(text="You will now start receiving reminders.")
        for lesson in lesson_formatted:
            day_number = -1
            text = "Your " + lesson["l_id"] + " lesson at " + lesson["venues"] + " is coming up from " + \
                   lesson["periods"] + "!"
            day = lesson["days"]
            if day == "Monday":
                day_number = 0
            elif day == "Tuesday":
                day_number = 1
            elif day == "Wednesday":
                day_number = 2
            elif day == "Thursday":
                day_number = 3
            elif day == "Friday":
                day_number = 4
            lesson_time_hour = lesson["periods"].split('-')[0][0:2]
            lesson_time_minute = lesson["periods"].split('-')[0][2:4]
            lesson_time_formatted = datetime.time(int(lesson_time_hour) - 1, int(lesson_time_minute) + 29, 0,
                                                  0, tzinfo=datetime.timezone(datetime.timedelta(seconds=28800)))
            job_queue.run_daily(send_reminder, lesson_time_formatted, days=tuple([day_number]),
                                context=[update.message.chat_id, text])

    def send_reminder(context: telegram.ext.CallbackContext):
        context.bot.send_message(chat_id=context.job.context[0], text=context.job.context[1])

    dispatcher.add_handler(timetable_conv)
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('reminder', reminders, pass_job_queue=True))
    dispatcher.add_handler(CallbackQueryHandler(main_menu_page, pattern='main'))
    dispatcher.add_handler(CallbackQueryHandler(timetable_page, pattern='sync'))
    dispatcher.add_handler(CallbackQueryHandler(settings_page, pattern='settings'))
    dispatcher.add_handler(CallbackQueryHandler(help_page, pattern='help'))
    dispatcher.add_handler(CallbackQueryHandler(list_module_page, pattern='list'))

    dispatcher.add_error_handler(error)

    logger.info("Starting NUSMods Telebot...")
    updater.start_polling()
    logger.info("Bot is running!")
    updater.idle()


if __name__ == '__main__':
    main()