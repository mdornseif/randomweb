"""Functions to generate some random words.

Influenced by jwz's webcollage."""

import os.path
import random
import log4py

log = log4py.Category().get_instance(__name__)
log.set_loglevel(log4py.LOGLEVEL_DEBUG)

dicts = ["/usr/dict/words",
         "/usr/share/dict/words",
         "/usr/share/dict/web2a",
         "/usr/share/lib/dict/words"]
wordlist = None

 
def pickDictionary():
    """Find the system dictionary."""

    global wordlist
    for x in dicts:
        if os.path.isfile(x):
            wordlist = x
            break
    if wordlist == None:
        raise RuntimeError, "Can't find any of this wordlists: %r" % (dicts)
    log.info("selected wordlist %s" % (wordlist))


def randomWord():
    """Return a random word from the system dictionary."""
    
    if wordlist == None:
        pickDictionary()
    word = ''
    fd = open(wordlist)
    size = os.path.getsize(wordlist)
    pos = random.randrange(size)
    fd.seek(pos)
    # toss partial line
    word = fd.readline()
    # keep next line
    word = fd.readline()

    # if at the end, loop to the beginning
    if word == '':
        fd.seek(0)
        # toss partial line
        word = fd.readline()
    fd.close()

    # beautify word
    word = word.strip().lower()
    # jwz has done also following translations which we will leave out for now
    #     $word =~ s/ly$//;
    #     $word =~ s/ys$/y/;
    #     $word =~ s/ies$/y/;
    #     $word =~ s/ally$//;
    #     $word =~ s/ally$/al/;
    #     $word =~ s/izes$/ize/;
    return word

def randomWords(numberofwords = 5):
    """Return a number of (defaults to 5) random words."""

    return map(lambda x: randomWord(), [0] * numberofwords)

if __name__ == '__main__':
    print randomWord()
    print randomWords()
