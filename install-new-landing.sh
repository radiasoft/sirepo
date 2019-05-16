#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
n=$PWD/sirepo/package_data/static/en

# the news is old so we aren't going to display anything for now
echo '[]' > "$n/news/article-index.json"

perl -w -pi - "$n"/{*.html,js/*.js,css/*.css} <<'EOF'
use strict;
our($launch, $learn, $hide_next_article);
# relocate to /en
m{bootstrapcdn.com/} || s{(?=/((css|img|js|news|video|static)/|[a-z-]+.html))}{/en};
# remove comments: unnecessary and top of file should be <!DOCTYPE
m{<!-- *(BEGIN|END)} && ($_ = '');

# All Radiasoft
s{Radiasoft}{RadiaSoft}g;

s{cloud(..8209.|-)based}{<span style="white-space: nowrap">cloud&ndash;based</span>};
s{#8209}{ndash}g;

# these could be included statically, since that would be not found but
# that's ok for testing. You can hover and see the URL is correct
s{(?<=href=")#(?=">elegant</a>)}{/en/particle-accelerators.html};
s{(?<=href=")#(?=">RsVND</a>)}{/old#/warpvnd};
s{(?<=href=")#(?=">SRW</a>)}{/en/xray-beamlines.html};
s{(?<=href=")#(?=">Synergia</a>)}{/old#/synergia};
s{(?<=href=")#(?=">Warp</a>)}{/old#/warppba};
s{(?<=href=")#(?=">Zgoubi</a>)}{/old#/zgoubi};

s{(?<=href=")https://sirepo.com}{/}g;

# shadow doesn't work for now so we are not showing
m{">Shadow3</a>} && ($_ = '');

# home page could be explicit in the source
s{(?<=href=")#(?=">RadiaSoft Home</a>)}{http://radiasoft.net};
# we want a referrer from sirepo.com to radiasoft.net
m{http://radiasoft.net} && s{ noreferrer}{};

# note target blank and subject
s{(?<=href=")#(?=">Contact Us</a>)}{mailto:support\@sirepo.com?subject=Web+Contact" target="_blank};

# touch-icon-iphone does not exist
s{/en/static/img/touch-icon-iphone.png}{/static/img/favicon.png};

# favicon has background which doesn't look good in browers; use existing
s{/en(?=/static/img/favicon)}{};

s{(?<=/xray-beamlines/discover-..jpg" alt=")Particle Accelerator}{X-ray Beamline};

# terms is Terms Of Service
s{Terms and Conditions}{Terms of Service};

# no comma after CO and U.S.A  would have a period after A, US would
# be sufficient but we aren't consistent (not used elsewhere) so remove
s{CO, 80301 U.S.A}{CO 80301};

# All these links could be fixed
if (m{>Particle Accelerators<}) {
    $launch = '/elegant';
    $learn = '/en/particle-accelerators.html';
}

# Sometimes it is X-ray Beamlines and other times X-Ray Beamlines
# so need to search case-insensitive. Need to be consistent on naming.
elsif (m{>X-ray Beamlines<}i) {
    $launch = '/srw';
    $learn = '/en/xray-beamlines.html';
}
elsif (m{>Include Particle Spin<}) {
    $launch = '/zgoubi';
    $learn = undef;
}
elsif (m{>Plasma Accelerators<}) {
    $launch = '/warppba';
    $learn = undef;
}
elsif (m{>Include Electron Cooling<}) {
    $launch = '/jspec';
    $learn = undef;
}
elsif (m{>Vacuum Nanoelectronic Devices<}) {
    $launch = '/warpvnd';
    $learn = undef;
}
elsif (m{>Include Space Charge<}) {
    $launch = '/synergia';
    $learn = undef;
    $hide_next_article = 1;
}
elsif ($hide_next_article && m{<article}) {
    # Hide Ray Tracing (shadow)
    s{(?<=<article)}{ style="display: none"};
    $hide_next_article = 0;
}
elsif (m{hover-green full-width.*<span>(\w+)}) {
    my($u) = $1 eq 'Bunch' ? 'bunchComp+-+fourDipoleCSR'
        : $1 eq 'Compact' ? 'Compact+Storage+Ring'
        : $1 eq 'Spear' ? 'SPEAR3'
        : die("unknown example: $1");
    s{#}{/find-by-name/elegant/default/$u};
}
m{>Learn More<} && s{#}{$learn};
m{>(Launch|Simulate Now)<} && s{#}{$launch};
EOF
