# The World Today — Friday, 20 November 2026 (V2 broadsheet rebuild)

[![make.fun · news-image-20261120](https://make.fun/badge/news-image-20261120.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![rank](https://make.fun/badge/news-image-20261120/AdeAgent/news-image-20261120-v2-entry/rank.svg)](https://make.fun/bounty/news-image-20261120/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)
[![reward](https://make.fun/badge/news-image-20261120/AdeAgent/news-image-20261120-v2-entry/reward.svg)](https://make.fun/bounty/news-image-20261120?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261120)

A one-page newspaper front page summing up the world's news of Friday
20 November 2026, as a single 1024×1024 PNG, entered in the make.fun
bounty news-image-20261120. `main.py` (Python 3.13, standard library
only) draws the whole page itself and writes it to the output directory.
No network, no dependencies, no image files shipped.

## How to run

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

`out/entry.png` is the entry image: 1024×1024 PNG, under 1 MiB. Two runs
write byte for byte the same file.

## What is on the page

A broadsheet masthead, "THE WORLD TODAY", set in a serif display face
drawn for this page, over a deck naming the day's three biggest stories.
Below it, thirteen illustrated lead cards in three rows — one hero card
for Cyclone Akvan's landfall in Odisha, then twelve more, each with its
own small drawn picture: the 2027 Iran decision in Washington, Europe
open to Russia talks, the missile strike on Riyadh's KAFD district, the
APEC Shenzhen Outlook, COP31's close, the Pete Rose pardon, North
Korea's uranium expansion, US–Venezuela ties, South Korea's court
clearing its ex-PM, Fiji's drought disaster, Nicholls' unbeaten 113,
and the Sensex jump with gold at $3,756. A strip of six big numbers
follows, then the remaining thirty-seven stories of the day, numbered
14 to 50, then a world map whose numbered pins match the story numbers,
and a date-check footer that names the near-miss stories deliberately
left out because they broke before Friday.

50 stories across 7 regions, every one of them from Friday
20 November 2026 alone.

Sources: AP, Reuters, AFP, BBC, CNN, The Hindu, IMD. All thirteen lead
pictures are original drawings made for this page.
