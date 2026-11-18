# PromoFinder AI — short walkthrough

**Opening:** PromoFinder turns timestamped screenplay text into a ranked set of promo moments for an editor to review.

**Input:** It reads the provided TXT scripts, parses scenes and timestamped dialogue or action into stable block IDs, and preserves the original text.

**Generation:** A configurable model suggests at most one promo per episode using only those block IDs. If no suitable moment exists, it can say so. The pipeline supports up to two corrections when validation finds a problem.

**Validation:** Python resolves IDs to original timecodes, checks segment order and duration, and keeps each promo within its episode. A separate model checks the hook, cliffhanger, standalone clarity and match to the excerpt.

**Ranking:** Another configurable model scores validated promos. Python calculates the weighted score out of 100, sorts results, and exports the top K.

**Outputs and limits:** Results, failures, raw responses, and run reports are saved as JSON, CSV and SQLite. These are timestamp recommendations, not rendered clips. Human review is recommended before publishing.

**Close:** The modular setup keeps model choice separate from the workflow, so compatible API endpoints can be configured without changing validation or ranking logic.
