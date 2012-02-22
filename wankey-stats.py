#!/usr/bin/env python

"""wankey-stat.py: Program to get stats from gmail activity

Being written with the aim of answering that age old question:
    "How many 'Wankey's are there?"
Will eventually collect stats and output a nice condensed summery of activity."""


import imaplib
import os
import cPickle
import time
from types import *
from email.parser import HeaderParser

#####################
#   Customise run:
#####################

debug = False       # Set to display debug info.
output = False      # Toggle printing output as it walks the chosen label.
save = True         # Toggle building dict of repeating info.
disp_count = False  # Toggle count of msgs on label list. (slower)
ask_label = True    # Toggle asking for a label or default to one. (set below)
delve = False       # Toggle displaying of label stats.
look = True         # Toggle parsing email stream for chosen label.
info = True         # Toggle displaying dict info at end. ('save' must be "True" above)
limit = True       # Toggle to enable stopping after a set amount of emails. (set below)
autoreconn = True  # Reconnect to saved account info automatically

#   Set your default label here "parent/child", case sensitive.
#   If you want a system label (All, sent etc) use "[Gmail]/child" format incl. brackets
default_label = '[Gmail]/Starred'
#   Set maximum emails to parse at a time. Limit for testing purposes.
max_limit = 80

#   Global vars:
email = ''
password = ''

####################
#   TODO:
####################

# - ask for email and password at runtime.                                  75%
# - parse subjects in label and count unique threads (-Re: Re: Fw:)         50%
# - display top thread counts (5+?)                                         0%
# - parse ALL mail and gather thread counts (in case of lazy labels)        20%
# - write a nav system for labels. with children, without, is parent etc    60%
# - allow choosing multiple labels and multiple threads                     5%
# - proper error handling                                                   0%
# - forget whole email data and just get sub, to, from, cc, date etc.       0%


####################
#   Classes:
####################

class pygmail:
    """Class to contain imap related functionality and email info"""
    def __init__(self):
        """Initialise various variables."""
        if debug: print 'init...'
        self.IMAP_SERVER='imap.gmail.com'
        self.IMAP_PORT=993
        self.M = None
        self.response = None

        self.all_labels = []
        self.label = ''
        self.to = []
        self.cc = []
        self.sys = []
        self.emails = []

        self.info = {}      # dict to hold the collected info
        self.info['email_sub'] = {}
        self.info['email_from'] = {}
        self.info['email_to'] = {}
        self.info['email_cc'] = {}
        self.info['email_star'] = {}
        self.info['used_labels'] = []

    def login(self, username, password):
        """Create connection and login."""
        ### TODO: error handling with dialogue output
        if debug: print 'logon...'
        self.M = imaplib.IMAP4_SSL(self.IMAP_SERVER, self.IMAP_PORT)
        try:
            rc, self.response = self.M.login(username, password)
            if debug: print 'Logon rc:', rc
            return rc
        except:
            print 'Unable to login. Please check your address and password and try again.'
            return -1

    def logout(self):
        """Logout and close connection."""
        self.M.logout()
        print '\n...logged out.'

    def get_all_labels(self):
        """Gather listing of labels
        Return status, append sys and labels lists"""
        rc, self.response = self.M.list()
        i = 1
        for item in self.response:
            self.label = item.split('"')[-2]
            if self.label.startswith('[Gmail]'):
                if debug: print i, '--- is  sys:', item
                self.sys.append(self.label)
                i += 1
                continue
            if debug: print i, '--- not sys:', item
            self.all_labels.append(self.label)
            i += 1
        self.all_labels.sort()
        self.sys.sort()
        for item in self.sys:
            self.all_labels.append(item) # append system labels to the end of 'self.all_labels'
        return rc

    def disp_all_labels(self):
        """Display all parent and child labels with an index."""
        if self.all_labels == []:
            print 'No labels collected yet, please run self.get_labels() first.'
            return -1
        i = 0
        print 'Num | Label (children indented)'.ljust(33), '| Email count'
        print '-'*50
        for item in c.all_labels:
            i += 1
            tmp = str(i).zfill(2)
            try:
                item.index('/') # Test to see if item is a 'child label'
            except:
                label_display = item.strip('[]')    # special system case
            else:
                label_display = '    ' + item.split('/')[-1].strip('[]')
            if disp_count:
                self.set_label(item)
                print tmp.ljust(4) + '|', label_display.ljust(27), '|', self.get_count()
            else:
                print tmp.ljust(4) + '|', label_display

    def get_count(self):
        """Get the message count for a label."""
        if self.label == '[Gmail]':
            return 'Root'
        rc, count = self.M.select(self.label)
        return count[0]

    """Various label info:"""
    def get_status_messages(self):
        rc, self.emails = self.M.status(self.label, "(MESSAGES)")
        return self.emails
    def get_status_recent(self):
        rc, self.emails = self.M.status(self.label, "(RECENT)")
        return self.emails
    def get_status_uidnext(self):
        rc, self.emails = self.M.status(self.label, "(UIDNEXT)")
        return self.emails
    def get_status_uidval(self):
        rc, self.emails = self.M.status(self.label, "(UIDVALIDITY)")
        return self.emails
    def get_status_unread(self):
        rc, self.emails = self.M.status(self.label, "(UNSEEN)")
        return self.emails

    def disp_full_info(self):
        """Display label info for selected label (self.label)"""
        response = c.get_count()
        if str(response).startswith('[NONEXISTENT]'):
            print 'No label called', self.label, 'found.'
        else:
            print '\nThere are', response, 'email(s) in', self.label + ':'
            ### various 'status' returns for self.label:
            #print '\t', c.get_status_messages()
            #print '\t', c.get_status_recent()
            #print '\t', c.get_status_uidnext()
            #print '\t', c.get_status_uidval()
            print '\t', c.get_status_unread()

    def set_label(self, label):
        """Set the current label."""
        self.label = label

    def select_label(self):
        """Command line label select.
        Use only AFTER self.get_all_labels() and self.disp_all_labels()"""
        run = True
        while run:
            label_num = raw_input('\nPlease enter a label number to analyse: ')
            if str(label_num) == '':
                self.set_label('[Gmail]/All Mail')
                print "You didn't enter a choice so we've defaulted to 'All Mail'"
                run = False
            else:
                try:
                    self.set_label(c.all_labels[int(label_num)-1])
                    run = False
                except:
                    print 'Not a valid entry!\nPlease enter a number between 1 and', len(self.all_labels), 'only.'
        print '\nYou selected:', label_num, ': "' + self.label + '"'

    def gather_info(self):
        """Walk through emails within selected label and collect info."""
        self.M.select(self.label)
        rc, data = self.M.search(None, 'ALL')
        i = 1
        total = self.get_count()
        for uid in data[0].split():
            resp, header = self.M.FETCH(uid, '(BODY[HEADER])')
            if debug: print 'header_data:\n', header
            msg = HeaderParser().parsestr(header[0][1])
            e_sub = remove_re(msg['Subject'])
            e_from = extract_email(msg['From'])
            e_to = extract_email(msg['To'])
            e_cc = extract_emails(msg['CC'])
            #e_cc = extract_emails(msg['CC']
            #e_date = date_to_epoch(msg['Date'])
            self.add_info(e_sub, e_from, e_to, e_cc)
            #print 'Sub:', e_sub
            #print 'Frm:', e_from
            #print 'To: ', e_to
            #print 'CC: ', e_cc
            #print 'Dte:', e_date
            print '\n'
            i += 1
            if limit:
                if i > max_limit:
                    print 'Reached "max_limit". Ending c.gather_info()'
                    break

    def add_info(self, e_sub, e_from, e_to, e_cc):
        """Collect the email info into a dictionary and count some stats"""
        if e_sub in self.info['email_sub']:
            self.info['email_sub'][e_sub] += 1
        else:
            self.info['email_sub'][e_sub] = 1

        if e_from in self.info['email_from']:
            self.info['email_from'][e_from] += 1
        else:
            self.info['email_from'][e_from] = 1

        if e_to in self.info['email_to']:
            self.info['email_to'][e_to] += 1
        else:
            self.info['email_to'][e_to] = 1

        if e_cc == None:
            pass
        else:
            for email in e_cc:
                if email in self.info['email_cc']:
                    self.info['email_cc'][email] += 1
                else:
                    self.info['email_cc'][email] = 1
            
    '''
    def parse_emails(self):
        """Walk through emails within selected label."""

        self.M.select(self.label)
        typ, data = self.M.search(None, 'ALL')
        i = 1
        total = self.get_count()
        for num in data[0].split():
            print '\nFetching', str(i).zfill(3), 'of', total
            resp, data = self.M.FETCH(num, '(RFC822)')
            msg = HeaderParser().parsestr(data[0][1])
            if True:  # Filter here by subject if wanted
                if output:
                    print 'Subject:\t', remove_re(msg['Subject'])
                    print 'From:\t', extract_email(msg['From'])
                    print 'To:\t', extract_email(msg['To'])
                    print 'CC:'
                    if msg['cc'] != None:
                        self.cc = extract_emails(msg['cc'])
                    else:
                        self.cc = ['None']
                    for email in self.cc:
                        print '\t', email
                    print '\n\n'
                if save:
                    print 'Subject:\t', msg['Subject']
                    self.add_info(remove_re(msg['Subject']), extract_email(msg['From']), extract_email(msg['To']))
            print 'Done:', get_percentage(i, total)
            i += 1
            if limit:
                if i > max_limit:
                    print 'Reached "max_limit". Ending c.parse_emails()'
                    break
    '''

    def parse_starred_wankey(self):
        """Collect the authors of starred emails in wankey only"""
        subject_only = 'Christmas Day *generic e-mail wankey*'
        self.M.select('[Gmail]/Starred')
        typ, data = self.M.search(None, 'ALL')
        i = 1
        total = self.get_count()
        for num in data[0].split():
            print '\nFetching', str(i).zfill(3), 'of', total
            print 'Done:', get_percentage(i, total)
            resp, data = self.M.FETCH(num, '(RFC822)')
            msg = HeaderParser().parsestr(data[0][1])
            tmp = remove_re(msg['Subject'])
            if tmp == subject_only:
                print 'FOUND ONE!!!'
                if tmp in self.info['starred']:
                    self.info['starred'][tmp] += 1
                else:
                    self.info['starred'][tmp] = 1
            if limit:
                if i > max_limit:
                    print 'reached limit of', max_limit
                    break
            i +=1

    def disp_info(self):
        """Print out the contents of the info dictionary"""
        if self.info['email_sub'] != {}:
            for field in self.info:
                print 'Field:', field
                if field == 'used_labels':
                    print 'Skipping used_labels [list]'
                    continue
                for entry in self.info[field]:
                    print '\tEntry:', str(self.info[field][entry]).zfill(3), entry
        else:
            print '\nDictionary is empty. Please run c.parse_emails() first'

    def dump_info(self):
        if self.info['email_sub'] != {}:
            f_out = open('./info.dat', 'w')
            cPickle.dump(self.info, f_out)
            print '\n...Info dictionary dumped! (./info.dat)'


####################
#   Functions:
####################

def ask_details():
    """Ask for user logon details, look in file or offer to change"""
    location = './account.dat'
    run = True
    while run:
        try:
            os.stat(location)
        except:
            #run = True
            #while run:
            file_email = raw_input('Please enter your full email address:\t')
            file_password = raw_input('Please enter your email password:\t')
            f_out = open(location, 'w')
            f_out.write(file_email + ':' + file_password)
            f_out.close()
            run = False
        else:
            f_in = open(location)
            s = f_in.read()
            f_in.close()
            tmp = s.split(':', 1)
            file_email = tmp[0]
            file_password = tmp[1]
            if autoreconn:
                response = 'y'
            else:
                response = raw_input('Settings found for "' + file_email + '"\n\tReconnect?  (y/n):')
            while response != 'y' and response != 'n':
                print 'r: "' + str(response) + '"'
                response = raw_input('Please enter either "y" or "n":')
            if response == 'n':
                print 'OK, removing settings for', file_email, '...\n'
                os.remove(location)
            if response == 'y':
                print 'OK. Reconnecting to', file_email, '...\n'
                run = False
    return file_email, file_password

def remove_re(sub):
    """Tidy up the email subject.
    TODO: include 'Fw:' to find
    TODO: make all this a while loop"""
    if sub.rfind('Re:') != -1:
        tmp = sub[sub.rfind('Re:')+3:].strip()
        while tmp.startswith('Re :'):
            tmp = tmp[4:].strip()
        return tmp
    else:
        return sub

def extract_email(line):
    """Remove extranious info from a string, return just the email."""
    try:
        line.index('<')
    except:
        return str(line).lower()
    else:
        return str(line[line.rfind('<')+1:line.rfind('>')]).strip().lower()

def extract_emails(data):
    """Run multiple lines through extract_email().
        Return list of just emails."""
    if data == None:
        return None
    emails = []
    lines = []
    for line in str(data).split(','):
        lines.append(line)
    for line in lines:
        tmp = extract_email(line)
        if not emails.__contains__(tmp):
            emails.append(extract_email(line))
    return emails

def get_percentage(now, total):
    int_now = float(now)
    int_total = float(total)
    pc = float(int_now / int_total * 100)
    return str(pc)[:4] + '%'

def date_to_epoch(long_date):
    """Convert email date to a timestamp for ease of storage.
    eg: Thu, 21 Feb 2008 19:37:41 +0000
    """
    pattern = '%a, %j %b %Y %H:%M:S'
    epoch = int(time.mktime(time.strptime(long_date[:-6], pattern)))
    return epoch

####################
#   Main:
####################

#   Ask user for account details if not saved in file
email, password = ask_details()

#   Initialise class and logon
c = pygmail()
c.login(email, password)

#   Gather labels then print them out with index
c.get_all_labels()
c.disp_all_labels()

#   Ask for a label
if ask_label:
    c.select_label()
else:
    c.label = default_label

#   Test starred:
#c.parse_starred_wankey()

#   Look into a label (readonly)
if delve:
    c.disp_full_info()

#   Parse emails
if look:
    c.gather_info()

#   Display collected info
if save:
    if info:
        c.disp_info()
        c.dump_info()

#   Logout
c.logout()


__author__      = "Dave A, aka indivisible, aka mbs-irl"
__email__       = "mbspare@gmail.com"
__copyright__   = "Copyright 2012, indivisible"
__license__     = "GPL"
__version__     = "0.1.2"
__date__        = "21/02/2012"
__status__      = "Prototype"
