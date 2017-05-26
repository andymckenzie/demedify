import pandas
import praw
import datetime
import time
import re
import json
import os
from pathlib import Path

########
# setting parameters and loading data

os.chdir("/Users/amckenz/Documents/github/demedify/")
subreddit_string = "medicine"
test = True
keys = pandas.read_table("/Users/amckenz/Desktop/token_reddit_info.tsv", names = ['a', 'b'], sep = ' ')
acronyms = pandas.read_table(subreddit_string + "/" + subreddit_string + "_acronyms.tsv", sep =';')
dict_file = subreddit_string + "/" + subreddit_string + "_dict.json"
thread_limit = 100

reddit = praw.Reddit(user_agent='Demedify v0.1',
                  client_id=keys.ix[keys['a'] == "client_id", 'b'].item(),
                  client_secret=keys.ix[keys['a'] == "client_secret", 'b'].item(),
                  username=keys.ix[keys['a'] == "username", 'b'].item(),
                  password=keys.ix[keys['a'] == "password", 'b'].item())

#loads table of acronyms, actual phrases, +/- defintions
acronym_list = acronyms["Phrase"].tolist()

subreddit = reddit.subreddit(subreddit_string)

#the dictionary keys are the submission ids.
#the values are lists:
#first entry of the list is the associated comment id.
#second entry of the list is a list of the expanded acronyms entered into that comment.

my_file = Path(dict_file)
if my_file.is_file():
    with open(dict_file, 'r') as fp:
        active_threads = json.load(fp)
else:
    active_threads = {}

#############
# functions

def string_found(string1, string2):
   if re.search(r"\b" + re.escape(string1) + r"\b", string2):
      return True
   return False

#http://praw.readthedocs.io/en/latest/tutorials/comments.html
def get_all_thread_text(submission):
    title = submission.title
    selftext = submission.selftext
    running_comments = ""
    submission.comments.replace_more(limit=0)
    for comment in submission.comments.list():
        running_comments = " ".join((running_comments, comment.body))
    thread_text = " ".join((title, selftext, running_comments))
    return thread_text

def create_comment_table(acronyms_present_list):
    list(acronyms.index)
    acronyms_include = []
    message = "Acroynm|Expansion" + "\n" + ":- |:- " + "\n"
    for i in acronyms_present_list:
        tmp_message = acronyms.ix[acronym_list.index(i), "Phrase"] + "|" + acronyms.ix[acronym_list.index(i), "Description"] + "\n"
        message = message + tmp_message
    message = message + "---" + "\n"
    message = message + "I'm a medical acronym expander bot. " + "| [Source Code](https://github.com/andymckenzie/demedify) " + "| [Feedback Welcome](https://github.com/andymckenzie/demedify/issues)"
    return message

###########
# querying reddit

while True:
    active_threads_ids = list(active_threads.keys())
    for submission in subreddit.new(limit = thread_limit):
        print(submission.title)
        thread_text = get_all_thread_text(submission)
        acronyms_present_list = []
        for word in acronym_list:
            if(string_found(word, thread_text)):
                acronyms_present_list.append(word)
        if submission.id not in active_threads and len(acronyms_present_list) > 0:
            table = create_comment_table(acronyms_present_list)
            print(table)
            if not test:
                comment = submission.reply(table)
                active_threads[submission.id] = [comment.id, acronyms_present_list]
                with open(my_file, 'w') as fp:
                    json.dump(active_threads, fp)
                # active_threads[submission.id] = ["test", acronyms_present_list]
                time.sleep(600) #praw likes it when i sleep for 9 minutes between posting new comments
        if submission.id in active_threads:
            #compare the current list of terms found for this submission to the one in the corresponding dictionary entry
            #if there are new acronyms present, then update the comment
            if set(active_threads[submission.id][1]) != set(acronyms_present_list):
                #update the table based on the acronyms now present
                table = create_comment_table(acronyms_present_list)
                print("updating...")
                print(table)
                if not test:
                    #retrieve and then edit the comment to add the new table
                    comment = reddit.comment(active_threads[submission.id][0])
                    comment = comment.edit(table)
                    #update the dictionary with the new list of acronyms
                    active_threads[submission.id] = [comment.id, acronyms_present_list]
                    with open(my_file, 'w') as fp:
                        json.dump(active_threads, fp)
        time.sleep(5)
