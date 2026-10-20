# Week 4 Recap: Ship it

**Dates** Oct 19, 2026 (planned for Nov 3 to Nov 9, done early)
**Status** Built and tested. Goes live once GitHub Pages is switched on.

## Week 4 in plain words
Weeks 1 to 3 built the engine. Week 4 built the showroom.

- **An API.** A small web server (FastAPI) that answers questions like "give me the top 10 bargains under 25" straight from the Postgres database.
- **A website.** Four pages. Home shows the headline result and the bargain list. Explorer lets you filter every player and see them on a price vs fair value chart. Each player gets his own page with his value over time and how he compares with others in his position. Method explains the approach and its limits.
- **Free hosting.** The website is published on GitHub Pages every time you push. It reads small data files instead of a live database, so it is free, loads instantly and never "falls asleep".
- **More tests.** 10 new tests check the API against a real Postgres database. GitHub now also builds the website on every push.

## What I finished
- [x] API endpoints: `/players`, `/players/{id}`, `/bargains`, `/summary`, `/health`
- [x] Export step that writes the website's data files
- [x] Website pages: Home, Explorer, Player, Method (light and dark mode, works on phones)
- [x] CI runs Python tests against Postgres and builds the website
- [x] Deploy workflow for GitHub Pages
- [ ] Switch on GitHub Pages and check the live link
- [ ] Add a short demo GIF to the README

## Numbers
| | |
| --- | --- |
| Tests | 34 passing (10 new for the API) |
| Website size | about 200 KB of code plus 300 KB of data, compressed |
| Pages | 4, plus one page for each of 1,352 players |

## What went wrong and how we fixed it
| # | Problem | What happened | Fix | Lesson |
| --- | --- | --- | --- | --- |
| 1 | `npm install` failed in my workspace | The shared folder could not hold the shortcut files npm makes | Built the website in a separate folder and copied only the source code back | Keep generated folders like node_modules out of synced folders |
| 2 | Chart years were off by one | Dates were shown in the browser's time zone, so 1 Jan 2014 became 31 Dec 2013 | Show dates in UTC | Time zones bite every developer at least once |
| 3 | The site showed "-0%" and "+47% more" | Rounding and an extra plus sign in a sentence | Small fixes to the number formatter | Read your own page like a visitor would |
| 4 | Tests could have wiped the real database | API tests need a database | Tests use a separate `upf_test` database and never touch `upf` | Keep test data and real data apart |

## Things I learned
- How to build a REST API with FastAPI and test it against a real database
- How to safely use user input in SQL (fixed sort list, named parameters)
- How React, TypeScript, Tailwind and Recharts fit together
- Static site vs live server, and why static is the better choice here
- How GitHub Actions can build and publish a website

## Interview story from this week
"I first planned to host the API and database on free cloud servers. Then I realised the data is one finished season, so a live database only adds a 30 second cold start for recruiters. I published a static site that loads instantly, and kept the API and Postgres for the full local stack, tested in CI."

## Honest check (added after week 4)
A question I asked myself: "Is my model real, or am I fooling myself?" So I rebuilt it without xG, xA and xT and ran the same backtest. It found bargains just as well. Most of the +47% comes from spotting players who were cheap for their age, position and minutes. The advanced stats still help. They explain prices better, and among players who looked equally cheap, the ones with better xG, xA and xT gained about 10% more. I rewrote the headline on the README and the website to say exactly that.

**Interview story.** "My first headline said advanced stats found bargains. I tested it by removing them, and the result barely changed. So I rewrote the claim to match the evidence, and found the smaller effect the stats really do have. A random list scored +1%, so the method itself holds up."

## Next up (polish, Dec 20 to Jan 4)
- [ ] Short blog post from `docs/findings.md`, shared on LinkedIn
- [ ] Resume bullet with the real numbers
- [ ] Ask two friends to use the site and fix what confuses them
