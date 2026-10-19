# Week 3 Recap: Market values and backtest

**Dates** Oct 14, 2026 (planned for Oct 27 to Nov 2, done early)
**Status** Done. 24 tests pass.

## Week 3 in plain words
Weeks 1 and 2 measured how good each player was. Week 3 asked the money question: **who was cheap for how good he was, and did the market catch up?**

- **Price tags.** We downloaded Transfermarkt's market values, the best public estimate of what each player is worth.
- **Joining two worlds.** StatsBomb calls him "Jorge Resurrección Merodio". Transfermarkt calls him "Koke". We matched names inside each club, used the nicknames StatsBomb keeps in its lineups, and used minutes played to break ties. 99.9% of regular players matched.
- **A fair price for everyone.** A model learned how price depends on stats, age, position and league, then gave every player a "fair price". It never saw the player's own price while doing this, so it could not cheat.
- **The value gap.** Fair price far above market price means "looks cheap".
- **The test.** We jumped two years ahead. Did the cheap-looking players' prices rise? Yes. The top 50 rose about 47% more than similar players.
- **A real database.** Everything now loads into Postgres, ready for the website in week 4.

## What I finished
- [x] Downloaded Transfermarkt data
- [x] Matched players between the two sources (99.9% of regulars)
- [x] Built the fair value model with cross validation
- [x] Ran the 2016 to 2018 backtest
- [x] Loaded everything into Postgres
- [x] Added 9 tests for matching and the backtest

## Results
| | Top 50 flagged | Everyone else |
| --- | --- | --- |
| Median value change, 2016 to 2018 | +21% | -17% |
| Share whose value rose | 54% | 35% |

**After age, position, league and starting price, flagged players gained 47% more** (95% range +19% to +81%). The shorter the list, the stronger the effect: top 25 +73%, top 100 +25%.

**Best hits.** Luis Alberto went from EUR 4m to EUR 35m. Roberto Inglese went from EUR 1m to EUR 10m. Cristiano Piccini went from EUR 0.7m to EUR 7.5m.

## What went wrong and how we fixed it
| # | Problem | What happened | Fix | Lesson |
| --- | --- | --- | --- | --- |
| 1 | My workspace could not download Transfermarkt data | The host is blocked from the cloud | You downloaded it on your laptop and I copied it over | Split work by who can reach what |
| 2 | The download script did nothing on the first try | Your laptop still had the old empty file | I saved it again and checked its size | Verify the file actually changed |
| 3 | AC Milan and Inter Milan got swapped | Once "AC" is removed, the names look the same | Pair clubs by shared players, not just names | Use the strongest evidence you have |
| 4 | Marseille and Caen split in two | StatsBomb spells them two ways | One name per team id | Join on ids, not names, whenever you can |
| 5 | Spanish and Brazilian players did not match | Legal names vs the names fans use ("Koke", "Nolito", "Pepe") | Fetched nicknames from 209 StatsBomb lineups | Find the field that bridges both sources |
| 6 | Relegated players looked like bargains | Their clubs went down, so the market priced them lower for a good reason | Added a "relegated" flag to the model | Ask why the market disagrees before calling it wrong |
| 7 | Postgres rejected the dates | They were text, and Postgres wants real dates | Converted them before loading | Databases are strict about types, which is a good thing |

## Things I learned
- How to join two datasets that have no shared id
- Why out-of-fold predictions matter (a model must not see the answer it is scoring)
- How a backtest works, and why you control for things that would happen anyway (young cheap players rise)
- How to load data into Postgres in one safe transaction

## Interview story from this week
"My model said AC Milan's players played for Inter, because the club names look alike once you strip 'AC'. I fixed it by pairing clubs on shared players instead. Squads never look alike. That one change also exposed a second bug, where StatsBomb spells Marseille two ways."

## Honest limits
- Transfermarkt values are estimates, not real fees.
- Some of the rise may be noisy prices bouncing back.
- The signal is strong at the top of the list, weak across everyone.

## Next up (Week 4, Nov 3 to Nov 9)
- [ ] Finish the API endpoints
- [ ] Build the three pages (Home, Explorer, Player)
- [ ] Deploy the database, API and website
- [ ] Write the README with the live link and a demo GIF
