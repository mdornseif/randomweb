import random

# #!/usr/bin/perl -w
# #
# # webcollage, Copyright (c) 1999-2001 by Jamie Zawinski <jwz@jwz.org>
# # This program decorates the screen with random images from the web.
# # One satisfied customer described it as "a nonstop pop culture brainbath."
# #
# # Permission to use, copy, modify, distribute, and sell this software and its
# # documentation for any purpose is hereby granted without fee, provided that
# # the above copyright notice appear in all copies and that both that
# # copyright notice and this permission notice appear in supporting
# # documentation.  No representations are made about the suitability of this
# # software for any purpose.  It is provided "as is" without express or
# # implied warranty.
# 
# # To run this as a display mode with xscreensaver, add this to `programs':
# #
# #   default-n:  webcollage -root                                        \n\
# #   default-n:  webcollage -root -filter 'vidwhacker -stdin -stdout'    \n\
# 
# 
# require 5;
# use strict;
# 
# # We can't "use diagnostics" here, because that library malfunctions if
# # you signal and catch alarms: it says "Uncaught exception from user code"
# # and exits, even though I damned well AM catching it!
# #use diagnostics;
# 
# 
# use Socket;
# require Time::Local;
# require POSIX;
# use Fcntl ':flock'; # import LOCK_* constants
# use POSIX qw(strftime);
# 
# 
# my $progname = $0; $progname =~ s@.*/@@g;
# my $version = q{ $Revision: 1.1 $ }; $version =~ s/^[^0-9]+([0-9.]+).*$/$1/;
# my $copyright = "WebCollage $version, Copyright (c) 1999-2001" .
#     " Jamie Zawinski <jwz\@jwz.org>\n" .
#     "            http://www.jwz.org/xscreensaver/\n";
# 
# 
# 
# my @search_methods = (  30, "imagevista", \&pick_from_alta_vista_images,
#                         28, "altavista",  \&pick_from_alta_vista_text,
#                         18, "yahoorand",  \&pick_from_yahoo_random_link,
#                         14, "googleimgs", \&pick_from_google_images,
#                          2, "yahoonews",  \&pick_from_yahoo_news_text,
#                          8, "lycos",      \&pick_from_lycos_text,
# 
#                      # Hotbot gives me "no matches" just about every time.
#                      # Then I try the same URL again, and it works.  I guess
#                      # it caches searches, and webcollage always busts its
#                      # cache and time out?  Or it just sucks.
#                      #   0, "hotbot",     \&pick_from_hotbot_text,
#                       );
# 
# #@search_methods=(100, "googleimgs",\&pick_from_google_images);
# 
# # programs we can use to write to the root window (tried in ascending order.)
# #
# my @root_displayers = (
#   "xloadimage -quiet -onroot -center -border black",
#   "xli        -quiet -onroot -center -border black",
#   "xv         -root -quit -viewonly +noresetroot -rmode 5" .
#   "           -rfg black -rbg black",
#   "chbg       -once -xscreensaver",
# 
# # this lame program wasn't built with vroot.h:
# # "xsri       -scale -keep-aspect -center-horizontal -center-vertical",
# );
# 
# 
# # Some sites need cookies to work properly.   These are they.
# #
# my %cookies = (
#   "www.altavista.com"  =>  "AV_ALL=1",   # request uncensored searches
#   "web.altavista.com"  =>  "AV_ALL=1",
# 
#                                          # log in as "cipherpunk"
#   "www.nytimes.com"    =>  'NYT-S=18cHMIlJOn2Y1bu5xvEG3Ufuk6E1oJ.' .
#                            'FMxWaQV0igaB5Yi/Q/guDnLeoL.pe7i1oakSb' .
#                            '/VqfdUdb2Uo27Vzt1jmPn3cpYRlTw9',
# );
# 
# 
# # Some sites have  managed to poison the search engines.  These are they.
# # (We auto-detect sites that have poisoned the search engines via excessive
# # keywords or dictionary words,  but these are ones that slip through
# # anyway.)
# #
# # This can contain full host names, or 2 or 3 component domains.
# #
# my %poisoners = (
#   "die.net"                 => 1,  # 'l33t h4ck3r d00dz.
#   "genforum.genealogy.com"  => 1,  # Cluttering altavista with human names.
#   "rootsweb.com"            => 1,  # Cluttering altavista with human names.
#   "akamai.net"              => 1,  # Lots of sites have their images on Akamai.
#                                    # But those are pretty much all banners.
#                                    # Since Akamai is super-expensive, let's
#                                    # go out on a limb and assume that all of
#                                    # their customers are rich-and-boring.
#   "bartleby.com"            => 1,  # Dictionary, cluttering altavista.
#   "encyclopedia.com"        => 1,  # Dictionary, cluttering altavista.
#   "onlinedictionary.datasegment.com" => 1,  # Dictionary, cluttering altavista.
# );
# 
# 
# # When verbosity is turned on, we warn about sites that we seem to be hitting
# # a lot: usually this means some new poisoner has made it into the search
# # engines.  But sometimes, the warning is just because that site has a lot
# # of stuff on it.  So these are the sites that are immune to the "frequent
# # site" diagnostic message.
# #
# my %warningless_sites = (
#   "home.earthlink.net"      => 1,  # Lots of home pages here.
#   "www.geocities.com"       => 1,
#   "www.angelfire.com"       => 1,
#   "members.aol.com"         => 1,
# 
#   "yimg.com"                => 1,  # This is where dailynews.yahoo.com stores
#   "eimg.com"                => 1,  # its images, so pick_from_yahoo_news_text()
#                                    # hits this every time.
# );
# 
# 
# ##############################################################################
# #
# # Various global flags set by command line parameters, or computed
# #
# ##############################################################################
# 
# 
# my $current_state = "???";      # for diagnostics
# my $load_method;
# my $last_search;
# my $image_succeeded = -1;
# my $suppress_audit = 0;
# 
# my $verbose_imgmap = 0;         # print out rectangles and URLs only (stdout)
# my $verbose_warnings = 0;       # print out warnings when things go wrong
# my $verbose_load = 0;           # diagnostics about loading of URLs
# my $verbose_filter = 0;         # diagnostics about page selection/rejection
# my $verbose_net = 0;            # diagnostics about network I/O
# my $verbose_pbm = 0;            # diagnostics about PBM pipelines
# my $verbose_http = 0;           # diagnostics about all HTTP activity
# my $verbose_exec = 0;           # diagnostics about executing programs
# 
# my $report_performance_interval = 60 * 15;  # print some stats every 15 minutes
# 
# my $http_proxy = undef;
# my $http_timeout = 30;
# my $cvt_timeout = 10;
# 
# my $min_width = 50;
# my $min_height = 50;
# my $min_ratio = 1/5;
# 
# my $min_gif_area = (120 * 120);
# 
# 
# my $no_output_p = 0;
# my $urls_only_p = 0;
# 
# my $wordlist;
# 
# my %rejected_urls;
# my @tripwire_words = ("aberrate", "abode", "amorphous", "antioch",
#                       "arrhenius", "arteriole", "blanket", "brainchild",
#                       "burdensome", "carnival", "cherub", "chord", "clever",
#                       "dedicate", "dilogarithm", "dolan", "dryden",
#                       "eggplant");
# 
# 
# ##############################################################################
# #
# # Retrieving URLs
# #
# ##############################################################################
# 
# # returns three values: the HTTP response line; the document headers;
# # and the document body.
# #
# sub get_document_1 {
#   my ( $url, $referer, $timeout ) = @_;
# 
#   if (!defined($timeout)) { $timeout = $http_timeout; }
#   if ($timeout > $http_timeout) { $timeout = $http_timeout; }
# 
#   if ($timeout <= 0) {
#     LOG (($verbose_net || $verbose_load), "timed out for $url");
#     return ();
#   }
# 
#   LOG ($verbose_net, "get_document_1 $url " . ($referer ? $referer : ""));
# 
#   if (! ($url =~ m@^http://@i)) {
#     LOG ($verbose_net, "not an HTTP URL: $url");
#     return ();
#   }
# 
#   my ($url_proto, $dummy, $serverstring, $path) = split(/\//, $url, 4);
#   $path = "" unless $path;
# 
#   my ($them,$port) = split(/:/, $serverstring);
#   $port = 80 unless $port;
# 
#   my $them2 = $them;
#   my $port2 = $port;
#   if ($http_proxy) {
#     $serverstring = $http_proxy if $http_proxy;
#     ($them2,$port2) = split(/:/, $serverstring);
#     $port2 = 80 unless $port2;
#   }
# 
#   my ($remote, $iaddr, $paddr, $proto, $line);
#   $remote = $them2;
#   if ($port2 =~ /\D/) { $port2 = getservbyname($port2, 'tcp') }
#   if (!$port2) {
#     LOG (($verbose_net || $verbose_load), "unrecognised port in $url");
#     return ();
#   }
#   $iaddr   = inet_aton($remote);
#   if (!$iaddr) {
#     LOG (($verbose_net || $verbose_load), "host not found: $remote");
#     return ();
#   }
#   $paddr   = sockaddr_in($port2, $iaddr);
# 
# 
#   my $head = "";
#   my $body = "";
# 
#   @_ =
#     eval {
#       local $SIG{ALRM} = sub {
#         LOG (($verbose_net || $verbose_load), "timed out ($timeout) for $url");
#         die "alarm\n";
#       };
#       alarm $timeout;
# 
#       $proto   = getprotobyname('tcp');
#       if (!socket(S, PF_INET, SOCK_STREAM, $proto)) {
#         LOG (($verbose_net || $verbose_load), "socket: $!");
#         return ();
#       }
#       if (!connect(S, $paddr)) {
#         LOG (($verbose_net || $verbose_load), "connect($serverstring): $!");
#         return ();
#       }
# 
#       select(S); $| = 1; select(STDOUT);
# 
#       my $cookie = $cookies{$them};
# 
#       my $user_agent = "$progname/$version";
#       if ($url =~ m@^http://www\.altavista\.com/@) {
#         # block this, you turkeys.
#         $user_agent = "Mozilla/4.76 [en] (X11; U; Linux 2.2.16-22 i686; Nav)";
#       }
# 
#       my $hdrs = "GET " . ($http_proxy ? $url : "/$path") . " HTTP/1.0\r\n" .
#                  "Host: $them\r\n" .
#                  "User-Agent: $user_agent\r\n";
#       if ($referer) {
#         $hdrs .= "Referer: $referer\r\n";
#       }
#       if ($cookie) {
#         my @cc = split(/\r?\n/, $cookie);
#         $hdrs .= "Cookie: " . join('; ', @cc) . "\r\n";
#       }
#       $hdrs .= "\r\n";
# 
#       foreach (split('\r?\n', $hdrs)) {
#         LOG ($verbose_http, "  ==> $_");
#       }
#       print S $hdrs;
#       my $http = <S>;
# 
#       $_  = $http;
#       s/[\r\n]+$//s;
#       LOG ($verbose_http, "  <== $_");
# 
#       while (<S>) {
#         $head .= $_;
#         s/[\r\n]+$//s;
#         last if m@^$@;
#         LOG ($verbose_http, "  <== $_");
# 
#         if (m@^Set-cookie:\s*([^;\r\n]+)@i) {
#           set_cookie($them, $1)
#         }
#       }
# 
#       my $lines = 0;
#       while (<S>) {
#         $body .= $_;
#         $lines++;
#       }
# 
#       LOG ($verbose_http,
#            "  <== [ body ]: $lines lines, " . length($body) . " bytes");
# 
#       close S;
# 
#       if (!$http) {
#         LOG (($verbose_net || $verbose_load), "null response: $url");
#         return ();
#       }
# 
#       return ( $http, $head, $body );
#     };
#   die if ($@ && $@ ne "alarm\n");       # propagate errors
#   if ($@) {
#     # timed out
#     $head = undef;
#     $body = undef;
#     $suppress_audit = 1;
#     return ();
#   } else {
#     # didn't
#     alarm 0;
#     return @_;
#   }
# }
# 
# 
# # returns two values: the document headers; and the document body.
# # if the given URL did a redirect, returns the redirected-to document.
# #
# sub get_document {
#   my ( $url, $referer, $timeout ) = @_;
#   my $start = time;
# 
#   my $orig_url = $url;
#   my $loop_count = 0;
#   my $max_loop_count = 4;
# 
#   do {
#     if (defined($timeout) && $timeout <= 0) {
#       LOG (($verbose_net || $verbose_load), "timed out for $url");
#       $suppress_audit = 1;
#       return ();
#     }
# 
#     my ( $http, $head, $body ) = get_document_1 ($url, $referer, $timeout);
# 
#     if (defined ($timeout)) {
#       my $now = time;
#       my $elapsed = $now - $start;
#       $timeout -= $elapsed;
#       $start = $now;
#     }
# 
#     return () unless $http; # error message already printed
# 
#     $http =~ s/[\r\n]+$//s;
# 
#     if ( $http =~ m@^HTTP/[0-9.]+ 30[123]@ ) {
#       $_ = $head;
#       my ( $location ) = m@^location:[ \t]*(.*)$@im;
#       if ( $location ) {
#         $location =~ s/[\r\n]$//;
# 
#         LOG ($verbose_net, "redirect from $url to $location");
#         $referer = $url;
#         $url = $location;
# 
#         if ($url =~ m@^/@) {
#           $referer =~ m@^(http://[^/]+)@i;
#           $url = $1 . $url;
#         } elsif (! ($url =~ m@^[a-z]+:@i)) {
#           $_ = $referer;
#           s@[^/]+$@@g if m@^http://[^/]+/@i;
#           $_ .= "/" if m@^http://[^/]+$@i;
#           $url = $_ . $url;
#         }
# 
#       } else {
#         LOG ($verbose_net, "no Location with \"$http\"");
#         return ( $url, $body );
#       }
# 
#       if ($loop_count++ > $max_loop_count) {
#         LOG ($verbose_net,
#              "too many redirects ($max_loop_count) from $orig_url");
#         $body = undef;
#         return ();
#       }
# 
#     } elsif ( $http =~ m@^HTTP/[0-9.]+ ([4-9][0-9][0-9].*)$@ ) {
# 
#       LOG (($verbose_net || $verbose_load), "failed: $1 ($url)");
# 
#       # http errors -- return nothing.
#       $body = undef;
#       return ();
# 
#     } elsif (!$body) {
# 
#       LOG (($verbose_net || $verbose_load), "document contains no data: $url");
#       return ();
# 
#     } else {
# 
#       # ok!
#       return ( $url, $body );
#     }
# 
#   } while (1);
# }
# 
# # If we already have a cookie defined for this site, and the site is trying
# # to overwrite that very same cookie, let it do so.  This is because nytimes
# # expires its cookies - it lets you upgrade to a new cookie without logging
# # in again, but you have to present the old cookie to get the new cookie.
# # So, by doing this, the built-in cypherpunks cookie will never go "stale".
# #
# sub set_cookie {
#   my ($host, $cookie) = @_;
#   my $oc = $cookies{$host};
#   return unless $oc;
#   $_ = $oc;
#   my ($oc_name, $oc_value) = m@^([^= \t\r\n]+)=(.*)$@;
#   $_ = $cookie;
#   my ($nc_name, $nc_value) = m@^([^= \t\r\n]+)=(.*)$@;
# 
#   if ($oc_name eq $nc_name &&
#       $oc_value ne $nc_value) {
#     $cookies{$host} = $cookie;
#     LOG ($verbose_net, "overwrote ${host}'s $oc_name cookie");
#   }
# }
# 
# 
# ############################################################################
# #
# # Extracting image URLs from HTML
# #
# ############################################################################
# 
# # given a URL and the body text at that URL, selects and returns a random
# # image from it.  returns () if no suitable images found.
# #
# sub pick_image_from_body {
#   my ( $url, $body ) = @_;
# 
#   my $base = $url;
#   $_ = $url;
# 
#   # if there's at least one slash after the host, take off the last
#   # pathname component
#   if ( m@^http://[^/]+/@io ) {
#     $base =~ s@[^/]+$@@go;
#   }
# 
#   # if there are no slashes after the host at all, put one on the end.
#   if ( m@^http://[^/]+$@io ) {
#     $base .= "/";
#   }
# 
#   $_ = $body;
# 
#   # strip out newlines, compress whitespace
#   s/[\r\n\t ]+/ /go;
# 
#   # nuke comments
#   s/<!--.*?-->//go;
# 
# 
#   # There are certain web sites that list huge numbers of dictionary
#   # words in their bodies or in their <META NAME=KEYWORDS> tags (surprise!
#   # Porn sites tend not to be reputable!)
#   #
#   # I do not want webcollage to filter on content: I want it to select
#   # randomly from the set of images on the web.  All the logic here for
#   # rejecting some images is really a set of heuristics for rejecting
#   # images that are not really images: for rejecting *text* that is in
#   # GIF/JPEG form.  I don't want text, I want pictures, and I want the
#   # content of the pictures to be randomly selected from among all the
#   # available content.
#   #
#   # So, filtering out "dirty" pictures by looking for "dirty" keywords
#   # would be wrong: dirty pictures exist, like it or not, so webcollage
#   # should be able to select them.
#   #
#   # However, picking a random URL is a hard thing to do.  The mechanism I'm
#   # using is to search for a selection of random words.  This is not
#   # perfect, but works ok most of the time.  The way it breaks down is when
#   # some URLs get precedence because their pages list *every word* as
#   # related -- those URLs come up more often than others.
#   #
#   # So, after we've retrieved a URL, if it has too many keywords, reject
#   # it.  We reject it not on the basis of what those keywords are, but on
#   # the basis that by having so many, the page has gotten an unfair
#   # advantage against our randomizer.
#   #
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
# 
# 
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
# ############################################################################
# #
# # Subroutines for getting pages and images out of search engines
# #
# ############################################################################
# 
# 
# sub pick_dictionary {
#   my @dicts = ("/usr/dict/words",
#                "/usr/share/dict/words",
#                "/usr/share/lib/dict/words");
#   foreach my $f (@dicts) {
#     if (-f $f) {
#       $wordlist = $f;
#       last;
#     }
#   }
#   error ("$dicts[0] does not exist") unless defined($wordlist);
# }
# 
# # returns a random word from the dictionary
# #
# sub random_word {
#     my $word = 0;
#     if (open (IN, "<$wordlist")) {
#         my $size = (stat(IN))[7];
#         my $pos = rand $size;
#         if (seek (IN, $pos, 0)) {
#             $word = <IN>;   # toss partial line
#             $word = <IN>;   # keep next line
#         }
#         if (!$word) {
#           seek( IN, 0, 0 );
#           $word = <IN>;
#         }
#         close (IN);
#     }
# 
#     return 0 if (!$word);
# 
#     $word =~ s/^[ \t\n\r]+//;
#     $word =~ s/[ \t\n\r]+$//;
#     $word =~ s/ys$/y/;
#     $word =~ s/ally$//;
#     $word =~ s/ly$//;
#     $word =~ s/ies$/y/;
#     $word =~ s/ally$/al/;
#     $word =~ s/izes$/ize/;
#     $word =~ tr/A-Z/a-z/;
# 
#     if ( $word =~ s/[ \t\n\r]/\+/g ) {  # convert intra-word spaces to "+".
#       $word = "\%22$word\%22";          # And put quotes (%22) around it.
#     }
# 
#     return $word;
# }
# 
# sub random_words {
#   return (random_word . "%20" .
#           random_word . "%20" .
#           random_word . "%20" .
#           random_word . "%20" .
#           random_word);
# }
# 
# 
# sub url_quote {
#   my ($s) = @_;
#   $s =~ s|([^-a-zA-Z0-9.\@/_\r\n])|sprintf("%%%02X", ord($1))|ge;
#   return $s;
# }
# 
# sub url_unquote {
#   my ($s) = @_;
#   $s =~ s/[+]/ /g;
#   $s =~ s/%([a-z0-9]{2})/chr(hex($1))/ige;
#   return $s;
# }
# 
# 
# # Loads the given URL (a search on some search engine) and returns:
# # - the total number of hits the search engine claimed it had;
# # - a list of URLs from the page that the search engine returned;
# # Note that this list contains all kinds of internal search engine
# # junk URLs too -- caller must prune them.
# #
# sub pick_from_search_engine {
#   my ( $timeout, $search_url, $words ) = @_;
# 
#   $_ = $words;
#   s/%20/ /g;
# 
#   print STDERR "\n\n" if ($verbose_load);
# 
#   LOG ($verbose_load, "words: $_");
#   LOG ($verbose_load, "URL: $search_url");
# 
#   $last_search = $search_url;   # for warnings
# 
#   my $start = time;
#   my ( $base, $body ) = get_document ($search_url, undef, $timeout);
#   if (defined ($timeout)) {
#     $timeout -= (time - $start);
#     if ($timeout <= 0) {
#       $body = undef;
#       LOG (($verbose_net || $verbose_load),
#            "timed out (late) for $search_url");
#       $suppress_audit = 1;
#       return ();
#     }
#   }
# 
#   return () if (! $body);
# 
# 
#   my @subpages;
# 
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
# 
# 
#   my $length = length($body);
#   my $href_count = 0;
# 
#   $_ = $body;
# 
#   s/[\r\n\t ]+/ /g;
# 
# 
#   s/(<A )/\n$1/gi;
#   foreach (split(/\n/)) {
#     $href_count++;
#     my ($u) = m@<A\s.*\bHREF\s*=\s*([^>]+)>@i;
#     next unless $u;
# 
#     if ($u =~ m/^\"([^\"]*)\"/) { $u = $1; }   # quoted string
#     elsif ($u =~ m/^([^\s]*)\s/) { $u = $1; }  # or token
# 
#     if ( $rejected_urls{$u} ) {
#       LOG ($verbose_filter, "  pre-rejecting candidate: $u");
#       next;
#     }
# 
#     LOG ($verbose_http, "    HREF: $u");
# 
#     $subpages[++$#subpages] = $u;
#   }
# 
#   if ( $#subpages < 0 ) {
#     LOG ($verbose_filter,
#          "found nothing on $base ($length bytes, $href_count links).");
#     return ();
#   }
# 
#   LOG ($verbose_filter, "" . $#subpages+1 . " links on $search_url");
# 
#   return ($search_count, @subpages);
# }
# 
# 
# sub depoison {
#   my (@urls) = @_;
#   my @urls2 = ();
#   foreach (@urls) {
#     my ($h) = m@^http://([^/: \t\r\n]+)@i;
# 
#     next unless defined($h);
# 
#     if ($poisoners{$h}) {
#       LOG (($verbose_filter), "  rejecting poisoner: $_");
#       next;
#     }
#     if ($h =~ m@([^.]+\.[^.]+\.[^.]+)$@ &&
#         $poisoners{$1}) {
#       LOG (($verbose_filter), "  rejecting poisoner: $_");
#       next;
#     }
#     if ($h =~ m@([^.]+\.[^.]+)$@ &&
#         $poisoners{$1}) {
#       LOG (($verbose_filter), "  rejecting poisoner: $_");
#       next;
#     }
# 
#     push @urls2, $_;
#   }
#   return @urls2;
# }
# 
# 
# # given a list of URLs, picks one at random; loads it; and returns a
# # random image from it.
# # returns the url of the page loaded; the url of the image chosen;
# # and a debugging description string.
def pick_image_from_pages(base, timeout, urllist):
    # my ($base, $total_hit_count, $unfiltered_link_count, $timeout, @pages) = @_;
    
    #   @pages = depoison (@pages);
    if len(page) == 0:
        return
    page = random.choice(pages)
    (base2, body2) = get_document(page, base, timeout)

    img = pick_image_from_body (base2, body)

    return (base2, img)

# ############################################################################
# #
# # Pick images by feeding random words into Alta Vista Image Search
# #
# ############################################################################
# 
# 
# my $alta_vista_images_url = "http://www.altavista.com/cgi-bin/query" .
#                             "?ipht=1" .       # photos
#                             "&igrph=1" .      # graphics
#                             "&iclr=1" .       # color
#                             "&ibw=1" .        # b&w
#                             "&micat=1" .      # no partner sites
#                             "&imgset=1" .     # no partner sites
#                             "&stype=simage" . # do image search
#                             "&mmW=1" .        # unknown, but required
#                             "&q=";
# 
# # imagevista
# sub pick_from_alta_vista_images {
#   my ( $timeout ) = @_;
# 
#   my $words = random_words;
#   my $page = (int(rand(9)) + 1);
#   my $search_url = $alta_vista_images_url . $words;
# 
#   if ($page > 1) {
#     $search_url .= "&pgno=" . $page;		# page number
#     $search_url .= "&stq=" . (($page-1) * 12);  # first hit result on page
#   }
# 
#   my ($search_hit_count, @subpages) =
#     pick_from_search_engine ($timeout, $search_url, $words);
# 
#   my @candidates = ();
#   foreach my $u (@subpages) {
# 
#     # altavista is encoding their URLs now.
#     next unless ($u =~
#     m@^/r\?ck_sm=[a-zA-Z0-9]+\&ref=[a-zA-Z0-9]+(\&uid=[a-zA-Z0-9]+)?\&r=(.*)@);
#     $u = url_unquote($2);
# 
#     next unless ($u =~ m@^http://@i);    #  skip non-HTTP or relative URLs
#     next if ($u =~ m@[/.]altavista\.com\b@i);     # skip altavista builtins
#     next if ($u =~ m@[/.]doubleclick\.net\b@i);   # you cretins
#     next if ($u =~ m@[/.]clicktomarket\.com\b@i); # more cretins
# 
#     next if ($u =~ m@[/.]viewimages\.com\b@i);    # stacked deck
#     next if ($u =~ m@[/.]gettyimages\.com\b@i);
# 
#     LOG ($verbose_filter, "  candidate: $u");
#     push @candidates, $u;
#   }
# 
#   return pick_image_from_pages ($search_url, $search_hit_count, $#subpages+1,
#                                 $timeout, @candidates);
# }
# 
# 
# 
# ############################################################################
# #
# # Pick images by feeding random words into Google Image Search
# # By Charles Gales <gales@us.ibm.com>
# #
# ############################################################################
# 
# 
# my $google_images_url =     "http://images.google.com/images" .
#                             "?site=images" .  # photos
#                             "&btnG=Search" .  # graphics
#                             "&safe=off" .     # no screening
#                             "&imgsafe=off" .
#                             "&q=";
# 
# # googleimgs
# sub pick_from_google_images {
#   my ( $timeout ) = @_;
# 
#   my $words = random_word;   # only one word for Google
#   my $page = (int(rand(9)) + 1);
#   my $num = 20;     # 20 images per page
#   my $search_url = $google_images_url . $words;
# 
#   if ($page > 1) {
#     $search_url .= "&start=" . $page*$num;	# page number
#     $search_url .= "&num="   . $num;            #images per page
#   }
# 
#   my ($search_hit_count, @subpages) =
#     pick_from_search_engine ($timeout, $search_url, $words);
# 
#   my @candidates = ();
#   foreach my $u (@subpages) {
#     next unless ($u =~ m@imgres\?imgurl@i);    #  All pics start with this
#     next if ($u =~ m@[/.]google\.com\b@i);     # skip google builtins
# 
#     if ($u =~ m@^/imgres\?imgurl=(.*?)\&imgrefurl=(.*?)\&@) {
#       my $urlf = $2;
#       LOG ($verbose_filter, "  candidate: $urlf");
#       push @candidates, $urlf;
#     }
#   }
# 
#   return pick_image_from_pages ($search_url, $search_hit_count, $#subpages+1,
#                                 $timeout, @candidates);
# }
# 
# 
# 
# ############################################################################
# #
# # Pick images by feeding random words into Alta Vista Text Search
# #
# ############################################################################
# 
# 
# my $alta_vista_url_1 = "http://www.altavista.com/cgi-bin/query?pg=q" .
#                        "&text=yes&kl=XX&stype=stext&q=";
# my $alta_vista_url_2 = "http://www.altavista.com/sites/search/web?pg=q" .
#                        "&kl=XX&search=Search&q=";
# 
# my $alta_vista_url = $alta_vista_url_2;
# 
# # altavista
# sub pick_from_alta_vista_text {
#   my ( $timeout ) = @_;
# 
#   my $words = random_words;
#   my $page = (int(rand(9)) + 1);
#   my $search_url = $alta_vista_url . $words;
# 
#   if ($page > 1) {
#     $search_url .= "&pgno=" . $page;
#     $search_url .= "&stq=" . (($page-1) * 10);
#   }
# 
#   my ($search_hit_count, @subpages) =
#     pick_from_search_engine ($timeout, $search_url, $words);
# 
#   my @candidates = ();
#   foreach my $u (@subpages) {
# 
#     # Those altavista fuckers are playing really nasty redirection games
#     # these days: the filter your clicks through their site, but use
#     # onMouseOver to make it look like they're not!  Well, it makes it
#     # easier for us to identify search results...
#     #
#     next unless ($u =~
#       m@^/r\?ck_sm=[a-zA-Z0-9]+\&ref=[a-zA-Z0-9]+\&uid=[a-zA-Z0-9]+\&r=(.*)@);
#     $u = url_unquote($1);
# 
#     LOG ($verbose_filter, "  candidate: $u");
#     push @candidates, $u;
#   }
# 
#   return pick_image_from_pages ($search_url, $search_hit_count, $#subpages+1,
#                                 $timeout, @candidates);
# }
# 
# 
# 
# ############################################################################
# #
# # Pick images by feeding random words into Hotbot
# #
# ############################################################################
# 
# my $hotbot_search_url = "http://hotbot.lycos.com/" .
#                         "?SM=SC" .
#                         "&DV=0" .
#                         "&LG=any" .
#                         "&FVI=1" .
#                         "&DC=100" .
#                         "&DE=0" .
#                         "&SQ=1" .
#                         "&TR=13" .
#                         "&AM1=MC" .
#                         "&MT=";
# 
# sub pick_from_hotbot_text {
#   my ( $timeout ) = @_;
# 
#   my $words = random_words;
#   my $search_url = $hotbot_search_url . $words;
# 
#   my ($search_hit_count, @subpages) =
#     pick_from_search_engine ($timeout, $search_url, $words);
# 
#   my @candidates = ();
#   foreach my $u (@subpages) {
# 
#     # Hotbot plays redirection games too
#     next unless ($u =~ m@^/director.asp\?target=([^&]+)@);
#     $u = url_decode($1);
# 
#     LOG ($verbose_filter, "  candidate: $u");
#     push @candidates, $u;
#   }
# 
#   return pick_image_from_pages ($search_url, $search_hit_count, $#subpages+1,
#                                 $timeout, @candidates);
# }
# 
# 
# 
# ############################################################################
# #
# # Pick images by feeding random words into Lycos
# #
# ############################################################################
# 
# my $lycos_search_url = "http://lycospro.lycos.com/srchpro/" .
#                        "?lpv=1" .
#                        "&t=any" .
#                        "&query=";
# 
# sub pick_from_lycos_text {
#   my ( $timeout ) = @_;
# 
#   my $words = random_words;
#   my $start = int(rand(8)) * 10 + 1;
#   my $search_url = $lycos_search_url . $words . "&start=$start";
# 
#   my ($search_hit_count, @subpages) =
#     pick_from_search_engine ($timeout, $search_url, $words);
# 
#   my @candidates = ();
#   foreach my $u (@subpages) {
# 
#     # Lycos plays exact the same redirection game as hotbot.
#     # Note that "id=0" is used for internal advertising links,
#     # and 1+ are used for  search results.
#     next unless ($u =~ m@^http://click.hotbot.com/director.asp\?id=[1-9]\d*&target=([^&]+)@);
#     $u = url_decode($1);
# 
#     LOG ($verbose_filter, "  candidate: $u");
#     push @candidates, $u;
#   }
# 
#   return pick_image_from_pages ($search_url, $search_hit_count, $#subpages+1,
#                                 $timeout, @candidates);
# }
# 
# 
# 
# ############################################################################
# #
# # Pick images by feeding random words into news.yahoo.com
# #
# ############################################################################
# 
# my $yahoo_news_url = "http://search.news.yahoo.com/search/news_photos?" .
#                      "&z=&n=100&o=o&2=&3=&p=";
# 
# # yahoonews
# sub pick_from_yahoo_news_text {
#   my ( $timeout ) = @_;
# 
#   my $words = random_words;
#   my $search_url = $yahoo_news_url . $words;
# 
#   my ($search_hit_count, @subpages) =
#     pick_from_search_engine ($timeout, $search_url, $words);
# 
#   my @candidates = ();
#   foreach my $u (@subpages) {
#     # only accept URLs on Yahoo's news site
#     next unless ($u =~ m@^http://dailynews.yahoo.com/@i);
# 
#     LOG ($verbose_filter, "  candidate: $u");
#     push @candidates, $u;
#   }
# 
#   return pick_image_from_pages ($search_url, $search_hit_count, $#subpages+1,
#                                 $timeout, @candidates);
# }
# 
# 
# 
# 
# ############################################################################
# #
# # Pick a random image in a random way
# #
# ############################################################################
# 
# 
# # Picks a random image on a random page, and returns two URLs:
# # the page containing the image, and the image.
# # Returns () if nothing found this time.
# # Uses the url-randomizer 1 time in 5, else the image randomizer.
# #
# 
# sub pick_image {
#   my ( $timeout ) = @_;
# 
#   $current_state = "select";
#   $load_method = "none";
# 
#   my $n = int(rand(100));
#   my $fn = undef;
#   my $total = 0;
#   my @rest = @search_methods;
# 
#   while (@rest) {
#     my $pct  = shift @rest;
#     my $name = shift @rest;
#     my $tfn  = shift @rest;
#     $total += $pct;
#     if ($total > $n && !defined($fn)) {
#       $fn = $tfn;
#       $current_state = $name;
#       $load_method = $current_state;
#     }
#   }
# 
#   if ($total != 100) {
#     error ("internal error: \@search_methods totals to $total%!");
#   }
# 
#   record_attempt ($current_state);
#   return $fn->($timeout);
# }
# 
# 
# 
# ############################################################################
# #
# # Statistics and logging
# #
# ############################################################################
# 
# sub timestr {
#   return strftime ("%H:%M:%S: ", localtime);
# }
# 
# sub blurb {
#   return "$progname: " . timestr() . "$current_state: ";
# }
# 
# sub error {
#   my ($err) = @_;
#   print STDERR blurb() . "$err\n";
#   exit 1;
# }
# 
# 
# my $lastlog = "";
# 
# sub clearlog {
#   $lastlog = "";
# }
# 
# sub showlog {
#   my $head = "$progname: DEBUG: ";
#   foreach (split (/\n/, $lastlog)) {
#     print STDERR "$head$_\n";
#   }
#   $lastlog = "";
# }
# 
# sub LOG {
#   my ($print, $msg) = @_;
#   my $blurb = timestr() . "$current_state: ";
#   $lastlog .= "$blurb$msg\n";
#   print STDERR "$progname: $blurb$msg\n" if $print;
# }
# 
# 
# my %stats_attempts;
# my %stats_successes;
# my %stats_elapsed;
# 
# my $last_state = undef;
# sub record_attempt {
#   my ($name) = @_;
# 
#   if ($last_state) {
#     record_failure($last_state) unless ($image_succeeded > 0);
#   }
#   $last_state = $name;
# 
#   clearlog();
#   report_performance();
# 
#   start_timer($name);
#   $image_succeeded = 0;
#   $suppress_audit = 0;
# }
# 
# sub record_success {
#   my ($name, $url, $base) = @_;
#   if (defined($stats_successes{$name})) {
#     $stats_successes{$name}++;
#   } else {
#     $stats_successes{$name} = 1;
#   }
# 
#   stop_timer ($name, 1);
#   my $o = $current_state;
#   $current_state = $name;
#   save_recent_url ($url, $base);
#   $current_state = $o;
#   $image_succeeded = 1;
#   clearlog();
# }
# 
# 
# sub record_failure {
#   my ($name) = @_;
# 
#   return if $image_succeeded;
# 
#   stop_timer ($name, 0);
#   if ($verbose_load && !$verbose_exec) {
# 
#     if ($suppress_audit) {
#       print STDERR "$progname: " . timestr() . "(audit log suppressed)\n";
#       return;
#     }
# 
#     my $o = $current_state;
#     $current_state = "DEBUG";
# 
#     my $line =  "#" x 78;
#     print STDERR "\n\n\n";
#     print STDERR ("#" x 78) . "\n";
#     print STDERR blurb() . "failed to get an image.  Full audit log:\n";
#     print STDERR "\n";
#     showlog();
#     print STDERR ("-" x 78) . "\n";
#     print STDERR "\n\n";
# 
#     $current_state = $o;
#   }
#   $image_succeeded = 0;
# }
# 
# 
# 
# sub stats_of {
#   my ($name) = @_;
#   my $i = $stats_successes{$name};
#   my $j = $stats_attempts{$name};
#   $i = 0 unless $i;
#   $j = 0 unless $j;
#   return "" . ($j ? int($i * 100 / $j) : "0") . "%";
# }
# 
# 
# my $current_start_time = 0;
# 
# sub start_timer {
#   my ($name) = @_;
#   $current_start_time = time;
# 
#   if (defined($stats_attempts{$name})) {
#     $stats_attempts{$name}++;
#   } else {
#     $stats_attempts{$name} = 1;
#   }
#   if (!defined($stats_elapsed{$name})) {
#     $stats_elapsed{$name} = 0;
#   }
# }
# 
# sub stop_timer {
#   my ($name, $success) = @_;
#   $stats_elapsed{$name} += time - $current_start_time;
# }
# 
# 
# my $last_report_time = 0;
# sub report_performance {
# 
#   return unless $verbose_warnings;
# 
#   my $now = time;
#   return unless ($now >= $last_report_time + $report_performance_interval);
#   my $ot = $last_report_time;
#   $last_report_time = $now;
# 
#   return if ($ot == 0);
# 
#   my $blurb = "$progname: " . timestr();
# 
#   print STDERR "\n";
#   print STDERR "${blurb}Current standings:\n";
# 
#   foreach my $name (sort keys (%stats_attempts)) {
#     my $try = $stats_attempts{$name};
#     my $suc = $stats_successes{$name} || 0;
#     my $pct = int($suc * 100 / $try);
#     my $secs = $stats_elapsed{$name};
#     my $secs_link = int($secs / $try);
#     print STDERR sprintf ("$blurb   %-12s %4s (%d/%d);\t %2d secs/link\n",
#                           "$name:", "$pct%", $suc, $try, $secs_link);
#   }
# }
# 
# 
# 
# my $max_recent_images = 400;
# my $max_recent_sites  = 20;
# my @recent_images = ();
# my @recent_sites = ();
# 
# sub save_recent_url {
#   my ($url, $base) = @_;
# 
#   return unless ($verbose_warnings);
# 
#   $_ = $url;
#   my ($site) = m@^http://([^ \t\n\r/:]+)@;
# 
#   my $done = 0;
#   foreach (@recent_images) {
#     if ($_ eq $url) {
#       print STDERR blurb() . "WARNING: recently-duplicated image: $url" .
#         " (on $base via $last_search)\n";
#       $done = 1;
#       last;
#     }
#   }
# 
#   # suppress "duplicate site" warning via %warningless_sites.
#   #
#   if ($warningless_sites{$site}) {
#     $done = 1;
#   } elsif ($site =~ m@([^.]+\.[^.]+\.[^.]+)$@ &&
#            $warningless_sites{$1}) {
#     $done = 1;
#   } elsif ($site =~ m@([^.]+\.[^.]+)$@ &&
#            $warningless_sites{$1}) {
#     $done = 1;
#   }
# 
#   if (!$done) {
#     foreach (@recent_sites) {
#       if ($_ eq $site) {
#         print STDERR blurb() . "WARNING: recently-duplicated site: $site" .
#         " ($url on $base via $last_search)\n";
#         last;
#       }
#     }
#   }
# 
#   push @recent_images, $url;
#   push @recent_sites,  $site;
#   shift @recent_images if ($#recent_images >= $max_recent_images);
#   shift @recent_sites  if ($#recent_sites  >= $max_recent_sites);
# }
# 
# 
# 
# ##############################################################################
# #
# # other utilities
# #
# ##############################################################################
# 
# # Does %-decoding.
# #
# sub url_decode {
#   ($_) = @_;
#   tr/+/ /;
#   s/%([a-fA-F0-9][a-fA-F0-9])/pack("C", hex($1))/eg;
#   return $_;
# }
# 
# 
# # Given the raw body of a GIF document, returns the dimensions of the image.
# #
# sub gif_size {
#   my ($body) = @_;
#   my $type = substr($body, 0, 6);
#   my $s;
#   return () unless ($type =~ /GIF8[7,9]a/);
#   $s = substr ($body, 6, 10);
#   my ($a,$b,$c,$d) = unpack ("C"x4, $s);
#   return (($b<<8|$a), ($d<<8|$c));
# }
# 
# # Given the raw body of a JPEG document, returns the dimensions of the image.
# #
# sub jpeg_size {
#   my ($body) = @_;
#   my $i = 0;
#   my $L = length($body);
# 
#   my $c1 = substr($body, $i, 1); $i++;
#   my $c2 = substr($body, $i, 1); $i++;
#   return () unless (ord($c1) == 0xFF && ord($c2) == 0xD8);
# 
#   my $ch = "0";
#   while (ord($ch) != 0xDA && $i < $L) {
#     # Find next marker, beginning with 0xFF.
#     while (ord($ch) != 0xFF) {
#       $ch = substr($body, $i, 1); $i++;
#     }
#     # markers can be padded with any number of 0xFF.
#     while (ord($ch) == 0xFF) {
#       $ch = substr($body, $i, 1); $i++;
#     }
# 
#     # $ch contains the value of the marker.
#     my $marker = ord($ch);
# 
#     if (($marker >= 0xC0) &&
#         ($marker <= 0xCF) &&
#         ($marker != 0xC4) &&
#         ($marker != 0xCC)) {  # it's a SOFn marker
#       $i += 3;
#       my $s = substr($body, $i, 4); $i += 4;
#       my ($a,$b,$c,$d) = unpack("C"x4, $s);
#       return (($c<<8|$d), ($a<<8|$b));
# 
#     } else {
#       # We must skip variables, since FFs in variable names aren't
#       # valid JPEG markers.
#       my $s = substr($body, $i, 2); $i += 2;
#       my ($c1, $c2) = unpack ("C"x2, $s);
#       my $length = ($c1 << 8) | $c2;
#       return () if ($length < 2);
#       $i += $length-2;
#     }
#   }
#   return ();
# }
# 
# # Given the raw body of a GIF or JPEG document, returns the dimensions of
# # the image.
# #
# sub image_size {
#   my ($body) = @_;
#   my ($w, $h) = gif_size ($body);
#   if ($w && $h) { return ($w, $h); }
#   return jpeg_size ($body);
# }
# 
# 
# # returns the full path of the named program, or undef.
# #
# sub which {
#   my ($prog) = @_;
#   foreach (split (/:/, $ENV{PATH})) {
#     if (-x "$_/$prog") {
#       return $prog;
#     }
#   }
#   return undef;
# }
# 
# 
# # Like rand(), but chooses numbers with a bell curve distribution.
# sub bellrand {
#   ($_) = @_;
#   $_ = 1.0 unless defined($_);
#   $_ /= 3.0;
#   return (rand($_) + rand($_) + rand($_));
# }
# 
# 
# ##############################################################################
# #
# # Generating a list of urls only
# #
# ##############################################################################
# 
# sub url_only_output {
#   do {
#     my ($base, $img) = pick_image;
#     if ($img) {
#       $base =~ s/ /%20/g;
#       $img  =~ s/ /%20/g;
#       print "$img $base\n";
#     }
#   } while (1);
# }
# 
# ##############################################################################
# #
# # Running as an xscreensaver module
# #
# ##############################################################################
# 
# my $image_ppm   = ($ENV{TMPDIR} ? $ENV{TMPDIR} : "/tmp") . "/webcollage." . $$;
# my $image_tmp1  = $image_ppm . "-1";
# my $image_tmp2  = $image_ppm . "-2";
# 
# my $filter_cmd = undef;
# my $post_filter_cmd = undef;
# my $background = undef;
# 
# my $img_width;            # size of the image being generated.
# my $img_height;
# 
# my $delay = 0;
# 
# 
# sub x_cleanup {
#   my ($sig) = @_;
#   print STDERR blurb() . "caught signal $sig.\n" if ($verbose_exec);
#   unlink $image_ppm, $image_tmp1, $image_tmp2;
#   exit 1;
# }
# 
# 
# # Like system, but prints status about exit codes, and kills this process
# # with whatever signal killed the sub-process, if any.
# #
# sub nontrapping_system {
#   $! = 0;
# 
#   $_ = join(" ", @_);
#   s/\"[^\"]+\"/\"...\"/g;
# 
#   LOG ($verbose_exec, "executing \"$_\"");
# 
#   my $rc = system @_;
# 
#   if ($rc == 0) {
#     LOG ($verbose_exec, "subproc exited normally.");
#   } elsif (($rc & 0xff) == 0) {
#     $rc >>= 8;
#     LOG ($verbose_exec, "subproc exited with status $rc.");
#   } else {
#     if ($rc & 0x80) {
#       LOG ($verbose_exec, "subproc dumped core.");
#       $rc &= ~0x80;
#     }
#     LOG ($verbose_exec, "subproc died with signal $rc.");
#     # die that way ourselves.
#     kill $rc, $$;
#   }
# 
#   return $rc;
# }
# 
# 
# # Given the URL of a GIF or JPEG image, and the body of that image, writes a
# # PPM to the given output file.  Returns the width/height of the image if
# # successful.
# #
# sub image_to_pnm {
#   my ($url, $body, $output) = @_;
#   my ($cmd, $cmd2, $w, $h);
# 
#   if ((@_ = gif_size ($body))) {
#     ($w, $h) = @_;
#     $cmd = "giftopnm";
#   } elsif ((@_ = jpeg_size ($body))) {
#     ($w, $h) = @_;
#     $cmd = "djpeg";
#   } else {
#     LOG (($verbose_pbm || $verbose_load),
#          "not a GIF or JPG" .
#          (($body =~ m@<(base|html|head|body|script|table|a href)>@i)
#           ? " (looks like HTML)" : "") .
#          ": $url");
#     $suppress_audit = 1;
#     return ();
#   }
# 
#   $cmd2 = "exec $cmd";        # yes, this really is necessary.  if we don't
#                               # do this, the process doesn't die properly.
#   if (!$verbose_pbm) {
#     #
#     # We get a "giftopnm: got a 'Application Extension' extension"
#     # warning any time it's an animgif.
#     #
#     # Note that "giftopnm: EOF / read error on image data" is not
#     # always a fatal error -- sometimes the image looks fine anyway.
#     #
#     $cmd2 .= " 2>/dev/null";
#   }
# 
#   # There exist corrupted GIF and JPEG files that can make giftopnm and
#   # djpeg lose their minds and go into a loop.  So this gives those programs
#   # a small timeout -- if they don't complete in time, kill them.
#   #
#   my $pid;
#   @_ = eval {
#     my $timed_out;
# 
#     local $SIG{ALRM}  = sub {
#       LOG ($verbose_pbm,
#            "timed out ($cvt_timeout) for $cmd on \"$url\" in pid $pid");
#       kill ('TERM', $pid) if ($pid);
#       $timed_out = 1;
#       $body = undef;
#     };
# 
#     if (($pid = open(PIPE, "| $cmd2 > $output"))) {
#       $timed_out = 0;
#       alarm $cvt_timeout;
#       print PIPE $body;
#       $body = undef;
#       close PIPE;
# 
#       LOG ($verbose_exec, "awaiting $pid");
#       waitpid ($pid, 0);
#       LOG ($verbose_exec, "$pid completed");
# 
#       my $size = (stat($output))[7];
#       $size = -1 unless defined($size);
#       if ($size < 5) {
#         LOG ($verbose_pbm, "$cmd on ${w}x$h \"$url\" failed ($size bytes)");
#         return ();
#       }
# 
#       LOG ($verbose_pbm, "created ${w}x$h $output ($cmd)");
#       return ($w, $h);
#     } else {
#       print STDERR blurb() . "$cmd failed: $!\n";
#       return ();
#     }
#   };
#   die if ($@ && $@ ne "alarm\n");       # propagate errors
#   if ($@) {
#     # timed out
#     $body = undef;
#     return ();
#   } else {
#     # didn't
#     alarm 0;
#     $body = undef;
#     return @_;
#   }
# }
# 
# sub pick_root_displayer {
#   my @names = ();
# 
#   foreach my $cmd (@root_displayers) {
#     $_ = $cmd;
#     my ($name) = m/^([^ ]+)/;
#     push @names, "\"$name\"";
#     LOG ($verbose_exec, "looking for $name...");
#     foreach my $dir (split (/:/, $ENV{PATH})) {
#       LOG ($verbose_exec, "  checking $dir/$name");
#       return $cmd if (-x "$dir/$name");
#     }
#   }
# 
#   $names[$#names] = "or " . $names[$#names];
#   error "none of: " . join (", ", @names) . " were found on \$PATH.";
# }
# 
# 
# my $ppm_to_root_window_cmd = undef;
# 
# 
# sub x_or_pbm_output {
# 
#   # make sure the various programs we execute exist, right up front.
#   #
#   foreach ("ppmmake", "giftopnm", "djpeg", "pnmpaste", "pnmscale", "pnmcut") {
#     which ($_) || error "$_ not found on \$PATH.";
#   }
# 
#   # find a root-window displayer program.
#   #
#   $ppm_to_root_window_cmd = pick_root_displayer();
# 
# 
#   $SIG{HUP}  = \&x_cleanup;
#   $SIG{INT}  = \&x_cleanup;
#   $SIG{QUIT} = \&x_cleanup;
#   $SIG{ABRT} = \&x_cleanup;
#   $SIG{KILL} = \&x_cleanup;
#   $SIG{TERM} = \&x_cleanup;
# 
#   # Need this so that if giftopnm dies, we don't die.
#   $SIG{PIPE} = 'IGNORE';
# 
#   if (!$img_width || !$img_height) {
#     $_ = "xdpyinfo";
#     which ($_) || error "$_ not found on \$PATH.";
#     $_ = `$_`;
#     ($img_width, $img_height) = m/dimensions: *(\d+)x(\d+) /;
#     if (!defined($img_height)) {
#       error "xdpyinfo failed.";
#     }
#   }
# 
#   my $bgcolor = "#000000";
#   my $bgimage = undef;
# 
#   if ($background) {
#     if ($background =~ m/^\#[0-9a-f]+$/i) {
#       $bgcolor = $background;
# 
#     } elsif (-r $background) {
#       $bgimage = $background;
# 
#     } elsif (! $background =~ m@^[-a-z0-9 ]+$@i) {
#       error "not a color or readable file: $background";
# 
#     } else {
#       # default to assuming it's a color
#       $bgcolor = $background;
#     }
#   }
# 
#   # Create the sold-colored base image.
#   #
#   $_ = "ppmmake '$bgcolor' $img_width $img_height";
#   LOG ($verbose_pbm, "creating base image: $_");
#   nontrapping_system "$_ > $image_ppm";
# 
#   # Paste the default background image in the middle of it.
#   #
#   if ($bgimage) {
#     my ($iw, $ih);
# 
#     my $body = "";
#     local *IMG;
#     open(IMG, "<$bgimage") || error "couldn't open $bgimage: $!";
#     my $cmd;
#     while (<IMG>) { $body .= $_; }
#     close (IMG);
# 
#     if ((@_ = gif_size ($body))) {
#       ($iw, $ih) = @_;
#       $cmd = "giftopnm |";
# 
#     } elsif ((@_ = jpeg_size ($body))) {
#       ($iw, $ih) = @_;
#       $cmd = "djpeg |";
# 
#     } elsif ($body =~ m/^P\d\n(\d+) (\d+)\n/) {
#       $iw = $1;
#       $ih = $2;
#       $cmd = "";
# 
#     } else {
#       error "$bgimage is not a GIF, JPEG, or PPM.";
#     }
# 
#     my $x = int (($img_width  - $iw) / 2);
#     my $y = int (($img_height - $ih) / 2);
#     LOG ($verbose_pbm,
#          "pasting $bgimage (${iw}x$ih) into base image at $x,$y");
# 
#     $cmd .= "pnmpaste - $x $y $image_ppm > $image_tmp1";
#     open (IMG, "| $cmd") || error "running $cmd: $!";
#     print IMG $body;
#     $body = undef;
#     close (IMG);
#     LOG ($verbose_exec, "subproc exited normally.");
#     rename ($image_tmp1, $image_ppm) ||
#       error "renaming $image_tmp1 to $image_ppm: $!";
#   }
# 
#   clearlog();
# 
#   while (1) {
#     my ($base, $img) = pick_image();
#     my $source = $current_state;
#     $current_state = "loadimage";
#     if ($img) {
#       my ($headers, $body) = get_document ($img, $base);
#       if ($body) {
#         paste_image ($base, $img, $body, $source);
#         $body = undef;
#       }
#     }
#     $current_state = "idle";
#     $load_method = "none";
# 
#     unlink $image_tmp1, $image_tmp2;
#     sleep $delay;
#   }
# }
# 
# sub paste_image {
#   my ($base, $img, $body, $source) = @_;
# 
#   $current_state = "paste";
# 
#   $suppress_audit = 0;
# 
#   LOG ($verbose_pbm, "got $img (" . length($body) . ")");
# 
#   my ($iw, $ih) = image_to_pnm ($img, $body, $image_tmp1);
#   $body = undef;
#   if (!$iw || !$ih) {
#     LOG ($verbose_pbm, "unable to make PBM from $img");
#     return 0;
#   }
# 
#   record_success ($load_method, $img, $base);
# 
# 
#   my $ow = $iw;  # used only for error messages
#   my $oh = $ih;
# 
#   # don't just tack this onto the front of the pipeline -- we want it to
#   # be able to change the size of the input image.
#   #
#   if ($filter_cmd) {
#     LOG ($verbose_pbm, "running $filter_cmd");
# 
#     my $rc = nontrapping_system "($filter_cmd) < $image_tmp1 >$image_tmp2";
#     if ($rc != 0) {
#       LOG(($verbose_pbm || $verbose_load), "failed command: \"$filter_cmd\"");
#       LOG(($verbose_pbm || $verbose_load), "failed URL: \"$img\" (${ow}x$oh)");
#       return;
#     }
#     rename ($image_tmp2, $image_tmp1);
# 
#     # re-get the width/height in case the filter resized it.
#     local *IMG;
#     open(IMG, "<$image_tmp1") || return 0;
#     $_ = <IMG>;
#     $_ = <IMG>;
#     ($iw, $ih) = m/^(\d+) (\d+)$/;
#     close (IMG);
#     return 0 unless ($iw && $ih);
#   }
# 
#   my $target_w = $img_width;
#   my $target_h = $img_height;
# 
#   my $cmd = "";
# 
# 
#   # Usually scale the image to fit on the screen -- but sometimes scale it
#   # to fit on half or a quarter of the screen.  Note that we don't merely
#   # scale it to fit, we instead cut it in half until it fits -- that should
#   # give a wider distribution of sizes.
#   #
#   if (rand() < 0.3) { $target_w /= 2; $target_h /= 2; }
#   if (rand() < 0.3) { $target_w /= 2; $target_h /= 2; }
# 
#   if ($iw > $target_w || $ih > $target_h) {
#     while ($iw > $target_w ||
#            $ih > $target_h) {
#       $iw = int($iw / 2);
#       $ih = int($ih / 2);
#     }
#     if ($iw <= 10 || $ih <= 10) {
#       LOG ($verbose_pbm, "scaling to ${iw}x$ih would have been bogus.");
#       return 0;
#     }
# 
#     LOG ($verbose_pbm, "scaling to ${iw}x$ih");
# 
#     $cmd .= " | pnmscale -xsize $iw -ysize $ih";
#   }
# 
# 
#   my $src = $image_tmp1;
# 
#   my $crop_x = 0;     # the sub-rectangle of the image
#   my $crop_y = 0;     # that we will actually paste.
#   my $crop_w = $iw;
#   my $crop_h = $ih;
# 
#   # The chance that we will randomly crop out a section of an image starts
#   # out fairly low, but goes up for images that are very large, or images
#   # that have ratios that make them look like banners (we try to avoid
#   # banner images entirely, but they slip through when the IMG tags didn't
#   # have WIDTH and HEIGHT specified.)
#   #
#   my $crop_chance = 0.2;
#   if ($iw > $img_width * 0.4 || $ih > $img_height * 0.4) {
#     $crop_chance += 0.2;
#   }
#   if ($iw > $img_width * 0.7 || $ih > $img_height * 0.7) {
#     $crop_chance += 0.2;
#   }
#   if ($min_ratio && ($iw * $min_ratio) > $ih) {
#     $crop_chance += 0.7;
#   }
# 
#   if ($crop_chance > 0.1) {
#     LOG ($verbose_pbm, "crop chance: $crop_chance");
#   }
# 
#   if (rand() < $crop_chance) {
# 
#     my $ow = $crop_w;
#     my $oh = $crop_h;
# 
#     if ($crop_w > $min_width) {
#       # if it's a banner, select the width linearly.
#       # otherwise, select a bell.
#       my $r = (($min_ratio && ($iw * $min_ratio) > $ih)
#                ? rand()
#                : bellrand());
#       $crop_w = $min_width + int ($r * ($crop_w - $min_width));
#       $crop_x = int (rand() * ($ow - $crop_w));
#     }
#     if ($crop_h > $min_height) {
#       # height always selects as a bell.
#       $crop_h = $min_height + int (bellrand() * ($crop_h - $min_height));
#       $crop_y = int (rand() * ($oh - $crop_h));
#     }
# 
#     if ($crop_x != 0   || $crop_y != 0 ||
#         $crop_w != $iw || $crop_h != $ih) {
#       LOG ($verbose_pbm,
#            "randomly cropping to ${crop_w}x$crop_h \@ $crop_x,$crop_y");
#     }
#   }
# 
#   # Where the image should logically land -- this might be negative.
#   #
#   my $x = int((rand() * ($img_width  + $crop_w/2)) - $crop_w*3/4);
#   my $y = int((rand() * ($img_height + $crop_h/2)) - $crop_h*3/4);
# 
#   # if we have chosen to paste the image outside of the rectangle of the
#   # screen, then we need to crop it.
#   #
#   if ($x < 0 ||
#       $y < 0 ||
#       $x + $crop_w > $img_width ||
#       $y + $crop_h > $img_height) {
# 
#     LOG ($verbose_pbm,
#          "cropping for effective paste of ${crop_w}x$crop_h \@ $x,$y");
# 
#     if ($x < 0) { $crop_x -= $x; $crop_w += $x; $x = 0; }
#     if ($y < 0) { $crop_y -= $y; $crop_h += $y; $y = 0; }
# 
#     if ($x + $crop_w >= $img_width)  { $crop_w = $img_width  - $x - 1; }
#     if ($y + $crop_h >= $img_height) { $crop_h = $img_height - $y - 1; }
#   }
# 
#   # If any cropping needs to happen, add pnmcut.
#   #
#   if ($crop_x != 0   || $crop_y != 0 ||
#         $crop_w != $iw || $crop_h != $ih) {
#     $iw = $crop_w;
#     $ih = $crop_h;
#     $cmd .= " | pnmcut $crop_x $crop_y $iw $ih";
#     LOG ($verbose_pbm, "cropping to ${crop_w}x$crop_h \@ $crop_x,$crop_y");
#   }
# 
#   LOG ($verbose_pbm, "pasting ${iw}x$ih \@ $x,$y in $image_ppm");
# 
#   $cmd .= " | pnmpaste - $x $y $image_ppm";
# 
#   $cmd =~ s@^ *\| *@@;
# 
#   $_ = "($cmd)";
#   $_ .= " < $image_tmp1 > $image_tmp2";
# 
#   if ($verbose_pbm) {
#     $_ = "($_) 2>&1 | sed s'/^/" . blurb() . "/'";
#   } else {
#     $_ .= " 2> /dev/null";
#   }
#   my $rc = nontrapping_system ($_);
# 
#   if ($rc != 0) {
#     LOG (($verbose_pbm || $verbose_load), "failed command: \"$cmd\"");
#     LOG (($verbose_pbm || $verbose_load), "failed URL: \"$img\" (${ow}x$oh)");
#     return;
#   }
# 
#   rename ($image_tmp2, $image_ppm) || return;
# 
#   my $target = "$image_ppm";
# 
#   # don't just tack this onto the end of the pipeline -- we don't want it
#   # to end up in $image_ppm, because we don't want the results to be
#   # cumulative.
#   #
#   if ($post_filter_cmd) {
#     $target = $image_tmp1;
#     $rc = nontrapping_system "($post_filter_cmd) < $image_ppm > $target";
#     if ($rc != 0) {
#       LOG ($verbose_pbm, "filter failed: \"$post_filter_cmd\"\n");
#       return;
#     }
#   }
# 
#   if (!$no_output_p) {
#     my $tsize = (stat($target))[7];
#     if ($tsize > 200) {
#       $cmd = "$ppm_to_root_window_cmd $target";
# 
#       # xv seems to hate being killed.  it tends to forget to clean
#       # up after itself, and leaves windows around and colors allocated.
#       # I had this same problem with vidwhacker, and I'm not entirely
#       # sure what I did to fix it.  But, let's try this: launch xv
#       # in the background, so that killing this process doesn't kill it.
#       # it will die of its own accord soon enough.  So this means we
#       # start pumping bits to the root window in parallel with starting
#       # the next network retrieval, which is probably a better thing
#       # to do anyway.
#       #
#       $cmd .= " &";
# 
#       $rc = nontrapping_system ($cmd);
# 
#       if ($rc != 0) {
#         LOG (($verbose_pbm || $verbose_load), "display failed: \"$cmd\"");
#         return;
#       }
# 
#     } else {
#       LOG ($verbose_pbm, "$target size is $tsize");
#     }
#   }
# 
#   $source .= "-" . stats_of($source);
#   print STDOUT "image: ${iw}x${ih} @ $x,$y $base $source\n"
#     if ($verbose_imgmap);
# 
#   clearlog();
# 
#   return 1;
# }
# 
# 
# sub main {
#   $| = 1;
#   srand(time ^ $$);
# 
#   my $verbose = 0;
#   my $dict;
# 
#   $current_state = "init";
#   $load_method = "none";
# 
#   my $root_p = 0;
# 
#   # historical suckage: the environment variable name is lower case.
#   $http_proxy = $ENV{http_proxy} || $ENV{HTTP_PROXY};
# 
#   while ($_ = $ARGV[0]) {
#     shift @ARGV;
#     if ($_ eq "-display" ||
#         $_ eq "-displ" ||
#         $_ eq "-disp" ||
#         $_ eq "-dis" ||
#         $_ eq "-dpy" ||
#         $_ eq "-d") {
#       $ENV{DISPLAY} = shift @ARGV;
#     } elsif ($_ eq "-root") {
#       $root_p = 1;
#     } elsif ($_ eq "-no-output") {
#       $no_output_p = 1;
#     } elsif ($_ eq "-urls-only") {
#       $urls_only_p = 1;
#       $no_output_p = 1;
#     } elsif ($_ eq "-verbose") {
#       $verbose++;
#     } elsif (m/^-v+$/) {
#       $verbose += length($_)-1;
#     } elsif ($_ eq "-delay") {
#       $delay = shift @ARGV;
#     } elsif ($_ eq "-timeout") {
#       $http_timeout = shift @ARGV;
#     } elsif ($_ eq "-filter") {
#       $filter_cmd = shift @ARGV;
#     } elsif ($_ eq "-filter2") {
#       $post_filter_cmd = shift @ARGV;
#     } elsif ($_ eq "-background" || $_ eq "-bg") {
#       $background = shift @ARGV;
#     } elsif ($_ eq "-size") {
#       $_ = shift @ARGV;
#       if (m@^(\d+)x(\d+)$@) {
#         $img_width = $1;
#         $img_height = $2;
#       } else {
#         error "argument to \"-size\" must be of the form \"640x400\"";
#       }
#     } elsif ($_ eq "-proxy" || $_ eq "-http-proxy") {
#       $http_proxy = shift @ARGV;
#     } elsif ($_ eq "-dictionary" || $_ eq "-dict") {
#       $dict = shift @ARGV;
#     } else {
#       print STDERR "$copyright\nusage: $progname [-root]" .
#                  " [-display dpy] [-root] [-verbose] [-timeout secs]\n" .
#                  "\t\t  [-delay secs] [-filter cmd] [-filter2 cmd]\n" .
#                  "\t\t  [-dictionary dictionary-file]\n" .
#                  "\t\t  [-http-proxy host[:port]]\n";
#       exit 1;
#     }
#   }
# 
#   if ($http_proxy && $http_proxy eq "") {
#     $http_proxy = undef;
#   }
#   if ($http_proxy && $http_proxy =~ m@^http://([^/]*)/?$@ ) {
#     # historical suckage: allow "http://host:port" as well as "host:port".
#     $http_proxy = $1;
#   }
# 
#   if (!$root_p && !$no_output_p) {
#     print STDERR $copyright;
#     error "the -root argument is mandatory (for now.)";
#   }
# 
#   if (!$no_output_p && !$ENV{DISPLAY}) {
#     error "\$DISPLAY is not set.";
#   }
# 
# 
#   if ($verbose == 1) {
#     $verbose_imgmap   = 1;
#     $verbose_warnings = 1;
# 
#   } elsif ($verbose == 2) {
#     $verbose_imgmap   = 1;
#     $verbose_warnings = 1;
#     $verbose_load     = 1;
# 
#   } elsif ($verbose == 3) {
#     $verbose_imgmap   = 1;
#     $verbose_warnings = 1;
#     $verbose_load     = 1;
#     $verbose_filter   = 1;
# 
#   } elsif ($verbose == 4) {
#     $verbose_imgmap   = 1;
#     $verbose_warnings = 1;
#     $verbose_load     = 1;
#     $verbose_filter   = 1;
#     $verbose_net      = 1;
# 
#   } elsif ($verbose == 5) {
#     $verbose_imgmap   = 1;
#     $verbose_warnings = 1;
#     $verbose_load     = 1;
#     $verbose_filter   = 1;
#     $verbose_net      = 1;
#     $verbose_pbm      = 1;
# 
#   } elsif ($verbose == 6) {
#     $verbose_imgmap   = 1;
#     $verbose_warnings = 1;
#     $verbose_load     = 1;
#     $verbose_filter   = 1;
#     $verbose_net      = 1;
#     $verbose_pbm      = 1;
#     $verbose_http     = 1;
# 
#   } elsif ($verbose >= 7) {
#     $verbose_imgmap   = 1;
#     $verbose_warnings = 1;
#     $verbose_load     = 1;
#     $verbose_filter   = 1;
#     $verbose_net      = 1;
#     $verbose_pbm      = 1;
#     $verbose_http     = 1;
#     $verbose_exec     = 1;
#   }
# 
#   if ($dict) {
#     error ("$dict does not exist") unless (-f $dict);
#     $wordlist = $dict;
#   } else {
#     pick_dictionary();
#   }
# 
#   if ($urls_only_p) {
#     url_only_output;
#   } else {
#     x_or_pbm_output;
#   }
# }
# 
# main;
# exit (0);
