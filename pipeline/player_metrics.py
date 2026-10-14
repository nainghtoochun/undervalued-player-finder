"""Per-90 player metrics for the season.

TODO week 2
1. Minutes played per player per match from lineups + substitution events
   (sb.lineups gives positions with from/to times in recent statsbombpy versions).
2. npxG per 90 = sum of our xG on non-penalty shots / minutes * 90.
3. xA per 90 = xG of shots that came straight from the player's pass (pass_assisted_shot_id).
4. xT per 90 from successful passes and carries, using pipeline.xt_model.action_xt.
5. Keep players with MIN_MINUTES or more and assign a position group (GK, DEF, MID, FWD).
"""
