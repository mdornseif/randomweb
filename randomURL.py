#!/usr/bin/python

"""Functions to find some random URL on the Web."""

import urllib2
import random
import re
import log4py
import randomWord

log = log4py.Category().get_instance(__name__)
log.set_loglevel(log4py.LOGLEVEL_DEBUG)
#log.error("error")
#log.warn("hello")
#log.info("startup")
#log.debug("debug")

def pickFromSearchEngine(search_url):
    """Retrive a Page from a searchengine and get the links.

    Loads the given URL (a search on some search engine) and returns:
    - the total number of hits the search engine claimed it had;
    - a list of URLs from the page that the search engine returned;
    Note that this list contains all kinds of internal search engine
    junk URLs too -- caller must prune them.

    AT THE MOMENT WE DON'T RETURN THE NUMBER OF MATCHES.
    
    """

    #   my ( $timeout, $search_url, $words ) = @_; 
    #   $_ = $words;
    #   s/%20/ /g;

    log.debug("fetching %s" % (search_url))
    q = urllib2.urlopen(urllib2.Request(search_url, headers={'user-agent': 'randomURL.py'}))
    body = q.read()
    
    #   my $search_count = "?";
    #   if ($body =~ m@found (approximately |about )?(<B>)?(\d+)(</B>)? image@) {
    #     $search_count = $3;
    #   } elsif ($body =~ m@<NOBR>((\d{1,3})(,\d{3})*)&nbsp;@i) {
    #     $search_count = $1;
    #   } elsif ($body =~ m@found ((\d{1,3})(,\d{3})*|\d+) Web p@) {
    #     $search_count = $1;
    #   } elsif ($body =~ m@found about ((\d{1,3})(,\d{3})*|\d+) results@) {
    #     $search_count = $1;
    #   } elsif ($body =~ m@\b\d+ - \d+ of (\d+)\b@i) { # imagevista
    #     $search_count = $1;
    #   } elsif ($body =~ m@About ((\d{1,3})(,\d{3})*) images@i) { # imagevista
    #     $search_count = $1;
    #   } elsif ($body =~ m@We found ((\d{1,3})(,\d{3})*|\d+) results@i) { # *vista
    #     $search_count = $1;
    #   } elsif ($body =~ m@ of about <B>((\d{1,3})(,\d{3})*)<@i) { # googleimages
    #     $search_count = $1;
    #   } elsif ($body =~ m@<B>((\d{1,3})(,\d{3})*)</B> Web sites were found@i) {
    #     $search_count = $1;    # lycos
    #   } elsif ($body =~ m@WEB.*?RESULTS.*?\b((\d{1,3})(,\d{3})*)\b.*?Matches@i) {
    #     $search_count = $1;                          # hotbot
    #   } elsif ($body =~ m@no photos were found containing@i) { # imagevista
    #     $search_count = "0";
    #   } elsif ($body =~ m@found no document matching@i) { # altavista
    #     $search_count = "0";
    #   }
    #   1 while ($search_count =~ s/^(\d+)(\d{3})/$1,$2/);
    # 
    # #  if ($search_count eq "?" || $search_count eq "0") {
    # #    local *OUT;
    # #    my $file = "/tmp/wc.html";
    # #    open(OUT, ">$file") || error ("writing $file: $!");
    # #    print OUT $body;
    # #    close OUT;
    # #    print STDERR  blurb() . "###### wrote $file\n";
    # #  }

    length = len(body)
    href_count = 0
    # compress whitespace
    body = re.sub(r'[\r\n\t ]+', ' ', body)
    body = re.sub(r'(<[Aa] )', r'\n\1', body) 
    urlre1 = re.compile(r'<[Aa]\s.*\b[Hh][Rr][Ee][Ff]\s*=\s*([^>]+)>')
    urlre2 = re.compile(r'^\"([^\"]*)\"')
    urlre3 = re.compile(r'^([^\s]*)\s')
    subpages = []
    for x in body.split('\n'):
        href_count += 1
        u1 = urlre1.match(x)
        if u1 == None:
            continue
        u = u1.group(1)
        u2 = urlre2.match(u)
        u3 = urlre3.match(u)
        if u2 != None:
            # quoted string
            u = u2.group(1)   
        elif u3 != None:
            # or token
            u = u3.group(1)

        #     if ( $rejected_urls{$u} ) {
        #       LOG ($verbose_filter, "  pre-rejecting candidate: $u");
        #       next;
        #     }
        #     LOG ($verbose_http, "    HREF: $u");
        subpages.append(u)
        
    log.debug("found %d links" % (len(subpages)))
    return subpages


# sub url_quote {
#   my ($s) = @_;
#   $s =~ s|([^-a-zA-Z0-9.\@/_\r\n])|sprintf("%%%02X", ord($1))|ge;
#   return $s;
# }

 
def urlUnquote(s):
    s = s.replace('+', ' ')
    s = re.sub(r'%([A-Za-z0-9]{2})', lambda x: chr(int(x.group(1), 16)), s)
    return s


def getRandomURLyahoo():
    """Get a url via the Yahoo Random Link.

    Ported over from jwz's webcollage."""

    yahoo_random_link = "http://random.yahoo.com/bin/ryl"

    log.debug("%s" % (yahoo_random_link))
    request = urllib2.urlopen(yahoo_random_link)
    url = request.geturl()
    log.debug("redirected to %s" % (url))
    
    return [url]

def getRandomURLdmoz():
    """Get a url via the DMOZ Random Link."""

    # http://www.supersonic.it/dmoz/ provides same as the Yahoo Random Link
    dmoz_random_link = "http://www.supersonic.it/cgi-bin/jump.cgi?ID=random"

    log.debug("%s" % (dmoz_random_link))
    request = urllib2.urlopen(dmoz_random_link)
    url = request.geturl()
    log.debug("redirected to %s" % (url))
    
    return [url]


def getRandomURLaltavista():
    """Pick images by feeding random words into Alta Vista Text Search.
    
    Ported over from jwz's webcollage."""

    altavista_url_1 = "http://www.altavista.com/cgi-bin/query?pg=q&text=yes&kl=XX&stype=stext&q="
    altavista_url_2 = "http://www.altavista.com/sites/search/web?pg=q&kl=XX&search=Search&q="
    altavista_url = altavista_url_2

    words = randomWord.randomWords(3)
    page = random.randrange(10) + 1
    search_url = altavista_url + '%20'.join(['"%s"' % (x.replace(' ', '%20')) for x in words])

    if page > 1:
        search_url += "&pgno=%d&stq%d" % (page, (page-1) * 10)

    subpages = pickFromSearchEngine(search_url)
    candidates = []
    # jwz: Those altavista fuckers are playing really nasty
    # redirection games these days: the filter your clicks through
    # their site, but use onMouseOver to make it look like they're
    # not!  Well, it makes it easier for us to identify search
    # results...
    urlre = re.compile(r'^/r\?ck_sm=[a-zA-Z0-9]+.*\&uid=[a-zA-Z0-9]+\&r=(.*)')
    for x in subpages:
        m = urlre.match(x)
        if m == None:
            continue
        url = urlUnquote(m.group(1))
        candidates.append(url)
        log.debug("candidate %s" % (url))

    return candidates
 

def getRandomURLhotbot():
    """Pick images by feeding random words into Hotbot.

    Based on jwz's code.
    """

    # TODO:
    # They seemd to have some anti-robot code at hotbot.
    # At least they return always 'no results' to this scripts although
    # the same query URL leads to hundreds of hits in my browser

    hotbot_search_url = "http://hotbot.lycos.com/?SM=SC&DV=0&LG=any&FVI=1&DC=100&DE=0&SQ=1&TR=13&AM1=MC&MT="
 
    words = randomWord.randomWords(3)
    search_url = hotbot_search_url + '%20'.join(['"%s"' % (x.replace(' ', '%20')) for x in words])

    subpages = pickFromSearchEngine(search_url)
    candidates = []
    urlre = re.compile(r'^/director.asp\?target=([^&]+)')
    # Hotbot plays redirection games too
    for x in subpages:
        m = urlre.match(x)
        if m == None:
            continue
        url = urlUnquote(m.group(1))
        candidates.append(url)
        log.debug("candidate %s" % (url))

    return candidates

def getRandomURLlycos():
    """Pick images by feeding random words into Lycos.

    Based on webcollage by jwz."""

    lycos_search_url = "http://lycospro.lycos.com/srchpro/?lpv=1&t=any&query="

    words = randomWord.randomWords(3)
    start = random.randrange(9) * 10 + 1
    search_url = lycos_search_url + '%20'.join(['"%s"' % (x.replace(' ', '%20')) for x in words]) + '&start=%d' % (start)

    subpages = pickFromSearchEngine(search_url)
    candidates = []
    urlre = re.compile(r'^http://click.hotbot.com/director.asp\?id=[1-9]\d*&target=([^&]+)')
    # Lycos plays exact the same redirection game as hotbot.
    # Note that "id=0" is used for internal advertising links,
    # and 1+ are used for  search results.
    # Lycos doesn't give the strange behaviour hotbot does.
    for x in subpages:
        m = urlre.match(x)
        if m == None:
            continue
        url = urlUnquote(m.group(1))
        candidates.append(url)
        log.debug("candidate %s" % (url))

    return candidates

def getRandomURLyahoonews():
    """Pick images by feeding random words into news.yahoo.com.

    Based on webcolage by jwz"""

    yahoo_news_url = "http://search.news.yahoo.com/search/news_photos?&z=&n=100&o=o&2=&3=&p="

    # TODO: to find actual news we need more common words
    words = randomWord.randomWords(10)
    search_url = yahoo_news_url + '%20'.join(['"%s"' % (x.replace(' ', '%20')) for x in words])

    subpages = pickFromSearchEngine(search_url)
    candidates = []
    urlre = re.compile(r'^http://dailynews.yahoo.com/')
    for x in subpages:
        # only accept URLs on Yahoo's news site
        m = urlre.match(x)
        if m == None:
            continue
        url = urlUnquote(x)
        candidates.append(url)
        log.debug("candidate %s" % (url))

    return candidates


def getRandomURLaltavistanews():
    """Pick images by feeding random words into news.altavista.com."""

    altavista_news_url = "http://news.altavista.com/search?nc=&q="

    # TODO: to find actual news we need more common words
    words = randomWord.randomWords(2)
    search_url = altavista_news_url + '%20'.join(['"%s"' % (x.replace(' ', '%20')) for x in words])

    subpages = pickFromSearchEngine(search_url)
    candidates = []
    urlre = re.compile(r'^/r\?ck_sm=[a-zA-Z0-9]+.*\&r=(.*)')
    for x in subpages:
        m = urlre.match(x)
        if m == None:
            continue
        url = urlUnquote(m.group(1))
        candidates.append(url)
        log.debug("candidate %s" % (url))

    return candidates

def pickImageFromBody(base, body):
    """Extracting image URLs from HTML.

    given a URL and the body text at that URL, selects and returns a
    random image from it.  returns None if no suitable images found.

    From webcollage by jwz."""

   # if there's at least one slash after the host, take off the last
   # pathname component
   if re.match(r'^http://[^/]+/', base, re.IGNORECASE):
       base = re.sub(r'[^/]+$', '')
 
   # if there are no slashes after the host at all, put one on the end.
   if re.match(r'^http://[^/]+$', base, re.IGNORECASE):
       base += "/"
 
   # compress whitespace
   body = re.sub(r'[\r\n\t ]+', ' ', body)
   # nuke comments
   body = re.sub(r'<!--.*?-->', '', body)
 
   # jwz: There are certain web sites that list huge numbers of
   # dictionary words in their bodies or in their <META NAME=KEYWORDS>
   # tags (surprise!  Porn sites tend not to be reputable!)
   
   # I do not want webcollage to filter on content: I want it to select
   # randomly from the set of images on the web.  All the logic here for
   # rejecting some images is really a set of heuristics for rejecting
   # images that are not really images: for rejecting *text* that is in
   # GIF/JPEG form.  I don't want text, I want pictures, and I want the
   # content of the pictures to be randomly selected from among all the
   # available content.

   # So, filtering out "dirty" pictures by looking for "dirty" keywords
   # would be wrong: dirty pictures exist, like it or not, so webcollage
   # should be able to select them.
   
   # However, picking a random URL is a hard thing to do.  The mechanism I'm
   # using is to search for a selection of random words.  This is not
   # perfect, but works ok most of the time.  The way it breaks down is when
   # some URLs get precedence because their pages list *every word* as
   # related -- those URLs come up more often than others.

   # TODO:
   # So, after we've retrieved a URL, if it has too many keywords, reject
   # it.  We reject it not on the basis of what those keywords are, but on
   # the basis that by having so many, the page has gotten an unfair
   # advantage against our randomizer.
   
   #   my $trip_count = 0;
   #   foreach my $trip (@tripwire_words) {
   #     $trip_count++ if m/$trip/i;
   #   }
   # 
   #   if ($trip_count >= $#tripwire_words - 2) {
   #     LOG (($verbose_filter || $verbose_load),
   #          "there is probably a dictionary in \"$url\": rejecting.");
   #     $rejected_urls{$url} = -1;
   #     $body = undef;
   #     $_ = undef;
   #     return ();
   #   }



   #   my @urls;
   #   my %unique_urls;
   # 
   #   foreach (split(/ *</)) {
   #     if ( m/^meta /i ) {
   # 
   #       # Likewise, reject any web pages that have a KEYWORDS meta tag
   #       # that is too long.
   #       #
   #       if (m/name ?= ?\"?keywords\"?/i &&
   #           m/content ?= ?\"([^\"]+)\"/) {
   #         my $L = length($1);
   #         if ($L > 1000) {
   #           LOG (($verbose_filter || $verbose_load),
   #                "excessive keywords ($L bytes) in $url: rejecting.");
   #           $rejected_urls{$url} = $L;
   #           $body = undef;
   #           $_ = undef;
   #           return ();
   #         } else {
   #           LOG ($verbose_filter, "  keywords ($L bytes) in $url (ok)");
   #         }
   #       }
   # 
   #     } elsif ( m/^(img|a) .*(src|href) ?= ?\"? ?(.*?)[ >\"]/io ) {
   # 
   #       my $was_inline = ( "$1" eq "a" || "$1" eq "A" );
   #       my $link = $3;
   #       my ( $width )  = m/width ?=[ \"]*(\d+)/oi;
   #       my ( $height ) = m/height ?=[ \"]*(\d+)/oi;
   #       $_ = $link;
   # 
   #       if ( m@^/@o ) {
   #         my $site;
   #         ( $site = $base ) =~ s@^(http://[^/]*).*@$1@gio;
   #         $_ = "$site$link";
   #       } elsif ( ! m@^[^/:?]+:@ ) {
   #         $_ = "$base$link";
   #         s@/\./@/@g;
   #         while (s@/\.\./@/@g) {
   #         }
   #       }
   # 
   #       # skip non-http
   #       if ( ! m@^http://@io ) {
   #         next;
#       }
# 
#       # skip non-image
#       if ( ! m@[.](gif|jpg|jpeg|pjpg|pjpeg)$@io ) {
#         next;
#       }
# 
#       # skip really short or really narrow images
#       if ( $width && $width < $min_width) {
#         if (!$height) { $height = "?"; }
#         LOG ($verbose_filter, "  skip narrow image $_ (${width}x$height)");
#         next;
#       }
# 
#       if ( $height && $height < $min_height) {
#         if (!$width) { $width = "?"; }
#         LOG ($verbose_filter, "  skip short image $_ (${width}x$height)");
#         next;
#       }
# 
#       # skip images with ratios that make them look like banners.
#       if ($min_ratio && $width && $height &&
#           ($width * $min_ratio ) > $height) {
#         if (!$height) { $height = "?"; }
#         LOG ($verbose_filter, "  skip bad ratio $_ (${width}x$height)");
#         next;
#       }
# 
#       # skip GIFs with a small number of pixels -- those usually suck.
#       if ($width && $height &&
#           m/\.gif$/io &&
#           ($width * $height) < $min_gif_area) {
#         LOG ($verbose_filter, "  skip small GIF $_ (${width}x$height)");
#         next;
#       }
#       
# 
#       my $url = $_;
# 
#       if ($unique_urls{$url}) {
#         LOG ($verbose_filter, "  skip duplicate image $_");
#         next;
#       }
# 
#       LOG ($verbose_filter,
#            "  image $url" .
#            ($width && $height ? " (${width}x${height})" : "") .
#            ($was_inline ? " (inline)" : ""));
# 
#       $urls[++$#urls] = $url;
#       $unique_urls{$url}++;
# 
#       # jpegs are preferable to gifs.
#       $_ = $url;
#       if ( ! m@[.]gif$@io ) {
#         $urls[++$#urls] = $url;
#       }
# 
#       # pointers to images are preferable to inlined images.
#       if ( ! $was_inline ) {
#         $urls[++$#urls] = $url;
#         $urls[++$#urls] = $url;
#       }
#     }
#   }
# 
#   my $fsp = ($body =~ m@<frameset@i);
# 
#   $_ = undef;
#   $body = undef;
# 
#   @urls = depoison (@urls);
# 
#   if ( $#urls < 0 ) {
#     LOG ($verbose_load, "no images on $base" . ($fsp ? " (frameset)" : ""));
#     return ();
#   }
# 
#   # pick a random element of the table
#   my $i = int(rand($#urls+1));
#   $url = $urls[$i];
# 
#   LOG ($verbose_load, "picked image " .($i+1) . "/" . ($#urls+1) . ": $url");
# 
#   return $url;
# }
# 
# 
# 


def pickImageFromPages(urllist):
    """given a list of URLs, picks one at random; loads it; and
    returns a random image from it.  returns the url of the page
    loaded and the url of the image chosen."""

    # my ($base, $total_hit_count, $unfiltered_link_count, $timeout, @pages) = @_;
    
    # TODO: catch spammers
    #   @pages = depoison (@pages);
    if len(urllist) == 0:
        return
    page = random.choice(urllist)
    log.debug("fetching %s" % (page))
    q = urllib2.urlopen(urllib2.Request(page, headers={'user-agent': 'randomURL.py'}))
    body = q.read()
    base = q.geturl()
    
    img = pickImageFromBody(base, body)

    return (base, img)


def getRandomImagegoogle():
    """Pick images by feeding random words into Google Image Search.

    By Charles Gales <gales@us.ibm.com> for webcolage."""

    google_images_url = ''.join(["http://images.google.com/images",
                                 "?site=images",   # photos
                                 "&btnG=Search",   # graphics
                                 "&safe=off",      # no screening
                                 "&imgsafe=off",
                                 "&q="])
 

    page = random.randrange(10) + 1
    num = 20;     # 20 images per page
    search_url = google_images_url + randomWord.randomWord()
    if page > 1:
        search_url += "&start=%d&num=%d" % (page * num, num)	# page number and images per page

    subpages = pickFromSearchEngine(search_url)
    candidates = []
    urlre = re.compile(r'^/imgres\?imgurl=(.*?)\&imgrefurl=(.*?)\&')
    for x in subpages:
        # All pics start with this
        if x.find('imgres?imgurl') == -1:
            continue
        # skip google builtins
        if x.find('google.com') != -1:
            continue
        m = urlre.match(x)
        if m == None:
            continue
        image = urlUnquote(m.group(1))
        url = urlUnquote(m.group(2))
        candidates.append((image, url))
        log.debug("candidate %s from %s" % (image, url))

    return candidates


def getRandomImagealtavista():
    """Pick images by feeding random words into Alta Vista Image Search.

    From webcollage by jwz."""
    altavista_images_url = ''.join(["http://www.altavista.com/cgi-bin/query",
                                     "?ipht=1",       # photos
                                     "&igrph=1",      # graphics
                                     "&iclr=1",       # color
                                     "&ibw=1",        # b&w
                                     "&micat=1",      # no partner sites
                                     "&imgset=1",     # no partner sites
                                     "&stype=simage", # do image search
                                     "&mmW=1",        # unknown, but required
                                     "&q="])

    # TODO: hack arround altavista adult filter
    words = randomWord.randomWords(15)
    page = random.randrange(10) + 1
    search_url = altavista_images_url + '%20'.join(['"%s"' % (x.replace(' ', '%20')) for x in words])

    if page > 1:
        search_url += "&pgno=%d&stq=%d" % (page, (page-1) * 10)

    subpages = pickFromSearchEngine(search_url)
    # we use a dictionary here to get rid of dupes
    candidates = {}
    # altavista is encoding their URLs now.
    urlre = re.compile(r'^/r\?ck_sm=[a-zA-Z0-9]+\&ref=[a-zA-Z0-9]+.*\&r=(.*)')
    framere = re.compile(r'.+&url=([^&]+)&.+&src=(http[^&]+)&stq=\d+')
    imgre = re.compile(r'.*&src=(http.*)&stq=.*')
    for x in subpages:
        m = urlre.match(x)
        if m == None:
            continue
        url = urlUnquote(m.group(1))
        #  skip non-HTTP or relative URLs
        if url.find('http://') != 0:
            log.debug("no http:// url with candidate %s" % (url))
            continue
        m = framere.match(url)
        if m == None:
            log.debug("no imagematch with candidate %s (%s)" % (url, x))
            continue
        url = urlUnquote(m.group(1))
        image = urlUnquote(m.group(2))
        # skip altavista builtins
        if url.find('altavista.com') != -1 \
           or url.find('doubleclick.net') != -1 \
           or url.find('clicktomarket.com') != -1 \
           or url.find('viewimages.com') != -1 \
           or url.find('gettyimages.com') != -1:
            log.debug("despammed candidate %s" % (url))
            continue
        
        candidates[(image, url)] = 1
        log.debug("candidate %s - %s" % (image, url))

    return candidates.keys()


if __name__ == '__main__':
    print getRandomImagealtavista()
    #print getRandomImagegoogle()
    #print getRandomURLaltavistanews()
    #print getRandomURLyahoonews()
    #print getRandomURLlycos()
    #print getRandomURLhotbot()
    #print getRandomURLaltavista()
    #print getRandomURLyahoo()    
    #print getRandomURLdmoz()

