We run a store and want to choose which products to put on offer next, to earn as much as possible
from upcoming customers, using only a log of past visits — for each visit, the products that were on
offer, the single item the customer bought (or that she left with nothing), and each product's price.
We would rather not fit any model of how shoppers choose; we want the records themselves to drive the
decision. The tricky part is that a record reveals very little — only that the customer liked what she
bought more than the other things shown to her that day, and nothing about how she would feel about
items she was never shown — so for a different selection we cannot be sure what a similar customer
would do. We would rather play it safe and pick the offer that holds up best under the least favorable
behavior the records still allow. We want the set of products to put on offer and the revenue we can
count on from it. End your answer with one line `ASSORTMENT=[...]` — a JSON array of the offered
product indices (1-based).
