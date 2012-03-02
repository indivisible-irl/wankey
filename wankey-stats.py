#!/usr/bin/env python

"""wankey-stat.py: Program to get stats from gmail activity

Being written with the aim of answering that age old question:
    "How many 'Wankey's are there?"
Will eventually collect stats and output a nice condensed summery of activity."""

import imaplib
import os
import re
import cPickle
import time
#from types import *
from email.parser import HeaderParser
from email.header import decode_header
import cProfile

#####################
##  Customise run: ##
#####################

test = False         # Used for testing specific functionality. Placed as needed.
debug = False       # Set to display debug info.
output = False      # Toggle printing output as it walks the chosen label.
save = False         # Toggle building dict of repeating info.
disp_labels = False # Toggle displaying of the label tree
disp_count = False  # Toggle count of msgs on label list. (slower)
ask_label = False    # Toggle asking for a label or default to one. (set below)
delve = False       # Toggle displaying of chosen label stats.
look = True         # Toggle parsing email stream for chosen label.
info = True         # Toggle displaying dict info at end. ('save' must be "True" above)
limit = True       # Toggle to enable stopping after a set amount of emails. (set below)
autoreconn = True   # Reconnect to saved account info automatically (Still asks if none exists)
testcase = False     # Set to a message number or "False" for testing purposes

max_limit = 5000      # Set max emails to parse in a run. Limit for testing. (See limit above to toggle)
default_label = '[Gmail]/All Mail'   # Set your default label here "parent/child", case sensitive.
# NB: If you want a system label (All, sent etc) use "[Gmail]/child" format incl. sq brackets '[]'

#   Global vars:
email = ''
password = ''
regex_sub = re.compile('\s*(re|fw|fwd)\s*:\s*', re.IGNORECASE)
regex_email = re.compile('\<(.+?@.+?\.+?.+?)\>')
regex_chars = re.compile('=\?(utf|iso|win)', re.IGNORECASE)

####################
##   TODO:        ##
####################

# - ask for email and password at runtime.                                  100%
# - parse subjects in label and count unique threads (-Re: Re: Fw:)         90%
# - display only top thread counts (10+?)                                   0%
# - parse ALL mail and gather thread counts (in case of lazy labels)        20%
# - write a nav system for labels. with children, without, is parent etc    70%
# - allow choosing multiple labels and multiple threads                     5%
# - proper error handling                                                   0%
# - move over to a sql db??                                                 0%
# - ask_details() needs attention                                           5%

####################
##   Classes:     ##
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

        self.get_sub = self.info['email_sub'].get
        self.get_from = self.info['email_from'].get
        self.get_to = self.info['email_to'].get
        self.get_cc = self.info['email_cc'].get
        self.get_star = self.info['email_star'].get
        

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
        if testcase:        # for debugging only: can choose a single email to test on. (set at top)
            print '\n-------- SINGLE TESTCASE:', testcase
            resp, header = self.M.FETCH(testcase, '(BODY[HEADER])')
            msg = HeaderParser().parsestr(header[0][1])
            e_sub = re_sub(msg['Subject'])
            print msg['From'], '---'
            e_from = extract_emails(msg['From'])
            e_to = extract_emails(msg['To'])
            e_cc = extract_emails(msg['CC'])
            for key in msg.keys():
                print key, ':\n', msg[key], '\n'
            print 'Sub:', e_sub
            print 'Frm:', e_from
            print 'To: ', e_to
            print 'CC: '
            for email in e_cc:
                print '\t', email
            #print 'Dte:', e_date
            print '\n'
        else:               # normal functionality - iterates over labels returned num list.
            total = self.get_count()
            for num in data[0].split():
                #percent_done = get_percentage(i, total)
                print 'Grabbing', str(num).zfill(len(total)), 'of', total#, '\tComplete:', percent_done
                resp, header = self.M.FETCH(num, '(BODY[HEADER])')
                if debug: print 'header_data:\n', header
                msg = HeaderParser().parsestr(header[0][1])
                e_sub = re_sub(msg['Subject'])
                e_from = extract_emails(msg['From'])
                e_to = extract_emails(msg['To'])
                e_cc = extract_emails(msg['CC'])
                #e_date = date_to_epoch(msg['Date'])
                self.add_info_norm(e_sub, e_from, e_to, e_cc)
                if debug:
                    print 'Sub: ', e_sub
                    print 'Frm: ', e_from
                    print 'To:  ', e_to
                    print 'CC: '
                    for email in e_cc:
                        print '\t', email
                    #print 'Date:', e_date
                    print '\n'
                i += 1
                if limit:
                    if i > max_limit:
                        print '\nReached "max_limit" of', max_limit, '- Ending c.gather_info()\n'
                        break

    def gather_starred(self, wankey=True):
        # Unused so far
        self.M.select('[Gmail]/Starred')
        rc, data = self.M.search(None, 'ALL')
        i = 1
        total = self.get_count()
        for uid in data[0].split():
            print 'Grabbing', uid, 'of', total
            resp, header = self.M.FETCH(uid, '(BODY[HEADER])')
            msg = HeaderParser().parsestr(header[0][1])
            e_sub = remove_re(msg['Subject'])
            e_from = extract_to(msg['From'])
            e_to = extract_to(msg['To'])
            e_cc = extract_cc(msg['CC'])

    def add_info_norm(self, e_sub, e_from, e_to, e_cc):
        """Collect the email info into a dictionary and count some stats"""
        # Subject:
        if e_sub not in self.info['email_sub']:
            self.info['email_sub'][e_sub] = 0
        self.info['email_sub'][e_sub] += 1
        # From:
        use = e_from[0].lower()
        if use not in self.info['email_from']:
            self.info['email_from'][use] = 0
        self.info['email_from'][use] += 1
        # To:
        if e_to == None:
            pass
        else:
            for email in e_to:
                if email not in self.info['email_to']:
                    self.info['email_to'][email] = 0
                self.info['email_to'][email] += 1
        # CC:
        if e_cc == None:
            pass
        else:
            for email in e_cc:
                use = email.lower()
                if use not in self.info['email_cc']:
                    self.info['email_cc'][use] = 0
                self.info['email_cc'][use] += 1

    def add_info_starred():
        ## TODO
        pass

    def disp_info(self):
        """Print out the contents of the info dictionary"""
        if self.info['email_sub'] != {}:
            for field in self.info:
                print 'Field:', field
                if field == 'used_labels':
                    print '\tSkipping used_labels [list]'
                    continue
                for entry in self.info[field]:
                    print '\tEntry:', str(self.info[field][entry]).zfill(3), str(entry).strip()
        else:
            print '\nDictionary is empty. Please run c.parse_emails() first'

    def dump_info(self):
        if self.info['email_sub'] != {}:
            f_out = open('./info.dat', 'w')
            cPickle.dump(self.info, f_out)
            print '\n...Info dictionary dumped! (./info.dat)'


####################
##   Functions:   ##
####################

def ask_details():
    """Ask for user logon details, look in file or offer to change"""
    location = './account.dat'
    run = True
    while run:
        try:
            os.stat(location)       # Test is file exists
        except:
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
            ### TODO: Make a try...except...else for file exists but unusable/empty.
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

def re_sub(subject):
    """Tidy up email subjects for comparisson using regex."""
    if subject == None:
        return 'No subject'
    if regex_chars.search(subject):
        tmp = 'foo: ' + subject
        print tmp
        title, value = decode_header(tmp)
        return regex_sub.sub('', value[0].strip())
    else:
        return regex_sub.sub('', subject.strip())

def extract_to(line):
    # DEPRECIATED
    """Extract a single email from a string"""
    try:
        found = regex_email.search(line)
        return found.group(1).lower()
    except:
        return str(line).lower().strip()

def extract_cc(data):
    # DEPRECIATED
    """Take the email addresses from cc data"""
    return regex_email.findall(str(data))

def extract_emails(data):
    """Take the email addresses from cc data"""
    if data == None:
        return 'None'
    else:
        found = regex_email.search(data)
        if found == None:
            return str(data).lower().strip()
        else:
            return regex_email.findall(str(data))

def get_percentage(now, total):
    """Calculate percentage to 3 figures (excl decimal pt) and return as a string (w/% appended).

    get_percentage(now, total)"""
    return str(float(float(now) / float(total) * 100))[:4] + '%'

def date_to_epoch(long_date):
    """Convert email date to a timestamp for ease of storage.
    eg: Thu, 21 Feb 2008 19:37:41 +0000
    """
    pattern = '%a, %j %b %Y %H:%M:S'
    epoch = int(time.mktime(time.strptime(long_date[:-6], pattern)))
    return epoch

####################
##   Main:        ##
####################

if __name__ == '__main__':
    #   Note time for total run at end
    t1 = time.time()
    
    #   Ask user for account details if not saved in file
    email, password = ask_details()

    #   Initialise class and logon
    c = pygmail()
    c.login(email, password)

    #   Gather labels then print them out if desired
    c.get_all_labels()
    if disp_labels:
        c.disp_all_labels()
    else:
        print '\nSkipping label display...\n'

    #   Ask for a label or use default
    if ask_label:
        c.select_label()
    else:
        c.label = default_label

    #   Look into a label (readonly)
    if delve:
        c.disp_full_info()

    #   Parse emails and collect info (subject, to, from, cc)
    if look:
        c.gather_info()

    #   Display collected info if saved and desired
    if info:
        c.disp_info()
        if save:
            c.dump_info()

    #   Logout
    c.logout()

    #   Calc and print run time
    t2 = time.time()
    done = str(t2 - t1)
    print 'Total run time was', done[:done.find('.')+3], 'seconds.'

####################
##   Details:     ##
####################

__author__      = "Dave A, aka indivisible, aka mbs-irl"
__email__       = "mbspare (at) gmail (dot) com"
__copyright__   = "Copyright 2012, indivisible"
__license__     = "GPL, no warrenties or guarantees"
__version__     = "0.1.4"
__date__        = "01/03/2012"
__status__      = "Alpha"
